import streamlit as st
from utils.process_files import process_uploaded_pdfs
from utils.index_files import create_qdrant_vector_store
from utils.final_block_rag import create_langgraph_app, run_rag_with_langgraph
from utils.retriever import create_retriever

import os
import io
import shutil
import glob
from helper import project_root, logger
from config import LOCAL_FOLDER, COLLECTION_NAME, VECTORDB_FOLDER
import json

# do streamlit front end for simplicity, that passes on uploaded documents to backend for vector store.
# also passes on user query to rag handler and gets back response, and provides saving options.


def display_chat(history):
    """
    Displays the chat history in the Streamlit app, handling structured assistant output.
    """
    for entry in history:
        if entry["role"] == "user":
            with st.chat_message("user"):
                st.write(entry["content"])

        elif entry["role"] == "assistant":
            with st.chat_message("assistant"):
                # Handle both dict and string content
                content = entry["content"]

                # If content is a dict, extract answer
                if isinstance(content, dict):
                    answer_text = content.get("answer", str(content))
                else:
                    # If content is a string, use it directly
                    answer_text = str(content)

                # Display the main answer
                st.write(answer_text)

                # Only try to get confidence and citations if content is a dict
                if isinstance(content, dict):
                    # Get confidence score, defaulting to None if not present
                    confidence_score = (
                        content.get("confidence", {}).get("confidence_score")
                    )

                    # Check if confidence score exists and display it
                    if confidence_score is not None:
                        if confidence_score < 0:
                            confidence_score = 0
                        # Use markdown with HTML to float the text to the right and make it smaller
                        st.markdown(
                            f"""
                            <div style="text-align: right; font-size: 0.8em; color: gray;">
                                Confidence: {confidence_score}%
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    # Consolidate and display the citations
                    if content.get("citations", None):
                        # Use a dictionary to group citations by document name only
                        consolidated_citations = {}

                        # Store a mapping of doc_name to a sample doc_num for display
                        doc_num_map = {}

                        for citation in content["citations"]:
                            doc_name = citation["document_name"]
                            doc_num = citation["document_number"]

                            if doc_name not in consolidated_citations:
                                consolidated_citations[doc_name] = []
                                doc_num_map[doc_name] = (
                                    doc_num  # Store the number for later display
                                )

                            consolidated_citations[doc_name].extend(
                                citation["page_numbers"]
                            )

                        with st.expander("References"):
                            # Iterate through the consolidated dictionary
                            for doc_name, page_numbers in consolidated_citations.items():
                                # Remove duplicates and sort the page numbers
                                unique_pages = sorted(set(page_numbers))
                                page_str = ", ".join(map(str, unique_pages))

                                # Get the document number from our map
                                doc_num = doc_num_map.get(doc_name, "N/A")

                                st.markdown(f"[{doc_num}] {doc_name}, Pages: {page_str}\n")


def convert_to_markdown(history):
    markdown_text = ""
    for entry in history:
        if entry["role"] == "user":
            markdown_text += f"**User:** {entry['content']}\n"

        elif entry["role"] == "assistant":
            markdown_text += (
                f"**Assistant:**\n  **Response :** {entry['content']['answer']}"
            )

            # Consolidate citations
            if entry["content"].get("citations", None):
                # Use a dictionary to group citations by document name only
                consolidated_citations = {}

                # Store a mapping of doc_name to a sample doc_num for display
                doc_num_map = {}

                for citation in entry["content"]["citations"]:
                    doc_name = citation["document_name"]
                    doc_num = citation["document_number"]

                    if doc_name not in consolidated_citations:
                        consolidated_citations[doc_name] = []
                        doc_num_map[doc_name] = (
                            doc_num  # Store the number for later display
                        )

                    consolidated_citations[doc_name].extend(citation["page_numbers"])

                markdown_text += "\n  **Ref:**"
                for doc_name, page_numbers in consolidated_citations.items():
                    # Remove duplicates and sort the page numbers
                    unique_pages = sorted(set(page_numbers))
                    page_str = ", ".join(map(str, unique_pages))

                    # Get the document number from our map
                    doc_num = doc_num_map.get(doc_name, "N/A")
                    markdown_text += f"[{doc_num}] {doc_name}, Pages: {page_str}\n"

        markdown_text += "\n"

    return markdown_text


def get_user_input():
    """Gets user input from the Streamlit input box."""
    return st.chat_input("Enter your message here...")


def initialize():
    if "start_flag" not in st.session_state:
        st.session_state.start_flag = False
    # Initialize chat history in session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "system", "content": "Please answer any question respectfully"}
        ]
    if "vector_store" not in st.session_state:
        st.session_state.vector_store = None
        st.session_state.document_chunks = None

    st.session_state.is_follow_up = False
    st.session_state.reset_history = False
    st.session_state.markdown_file = ""

    if "rag_app" not in st.session_state:
        st.session_state["rag_app"] = None

    if "retriever" not in st.session_state:
        st.session_state["retriever"] = None

    if "debug_mode" not in st.session_state:
        st.session_state["debug_mode"] = False


# A function to handle the user's query
def handle_query_and_run_rag(query):
    # Check if the vector store and chunks are in session state

    if "rag_app" in st.session_state and query is not None:
        app = st.session_state.rag_app
        graph_state = {
            "question": query,
            "chat_history": st.session_state["chat_history"],
            "documents": st.session_state["document_chunks"],
            "answer": "",
            "enhanced_question": "",
            "is_follow_up": st.session_state["is_follow_up"],
            "reset_history": st.session_state["reset_history"],
            "regeneration_count": 0,  # Initialize regeneration counter (matches cli_run.py)
            "debug": st.session_state.get("debug_mode", False),  # Pass debug flag
        }
        # Pass the components to the RAG function
        result = run_rag_with_langgraph(graph_state, app)
        if type(result) is not dict:
            result = json.loads(result)
        return result
    else:
        st.warning("Please create the vector store first by clicking the button.")


@st.cache_data
def cached_process_files(uploaded_files):
    """
    A wrapper function that calls the backend function and is
    decorated with st.cache_data.
    """
    # Extract the file content (bytes) from the UploadedFile objects

    file_path = os.path.join(project_root, LOCAL_FOLDER, COLLECTION_NAME)
    os.makedirs(file_path, exist_ok=True)
    file_paths = [None] * len(uploaded_files)
    for i, file in enumerate(uploaded_files):
        file_bytes = file.getvalue()
        file_paths[i] = file_path + os.sep + file.name
        with open(file_paths[i], "wb") as f:
            f.write(file_bytes)

    # Pass the content to the backend function
    return process_uploaded_pdfs(file_paths, extract_metadata=True)


def get_available_txt_files():
    """Get list of .txt files in the project root directory."""
    txt_files = glob.glob(os.path.join(project_root, "*.txt"))
    # Filter out requirements files
    txt_files = [f for f in txt_files if "requirements" not in os.path.basename(f).lower()]
    return sorted([os.path.basename(f) for f in txt_files])


def check_qdrant_lock():
    """Check if Qdrant database is locked by another process."""
    vector_store_path = os.path.join(project_root, VECTORDB_FOLDER)

    # Check for common Qdrant lock indicators
    lock_files = [
        os.path.join(vector_store_path, ".qdrant-lock"),
        os.path.join(vector_store_path, "storage", ".qdrant-lock"),
    ]

    for lock_file in lock_files:
        if os.path.exists(lock_file):
            return True

    return False


def cleanup_qdrant_locks():
    """Remove Qdrant lock files and optionally kill stale processes."""
    vector_store_path = os.path.join(project_root, VECTORDB_FOLDER)

    # Remove lock files
    lock_files = [
        os.path.join(vector_store_path, ".qdrant-lock"),
        os.path.join(vector_store_path, "storage", ".qdrant-lock"),
    ]

    removed_count = 0
    for lock_file in lock_files:
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
                logger.info(f"Removed lock file: {lock_file}")
                removed_count += 1
            except Exception as e:
                logger.error(f"Failed to remove lock file {lock_file}: {e}")

    return removed_count


def force_cleanup_vector_store():
    """Force cleanup of vector store directory."""
    vector_store_path = os.path.join(project_root, VECTORDB_FOLDER)

    if os.path.exists(vector_store_path):
        try:
            shutil.rmtree(vector_store_path)
            logger.info(f"Removed entire vector store: {vector_store_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove vector store: {e}")
            return False
    return True


def prepare_selected_files(selected_files):
    """Copy selected .txt files to LOCAL_FOLDER/COLLECTION_NAME for processing.

    Args:
        selected_files: List of filenames (basenames) to process

    Returns:
        List of destination file paths
    """
    target_folder = os.path.join(project_root, LOCAL_FOLDER, COLLECTION_NAME)
    os.makedirs(target_folder, exist_ok=True)

    dest_paths = []
    for filename in selected_files:
        source_path = os.path.join(project_root, filename)
        if not os.path.isfile(source_path):
            st.error(f"File not found: {filename}")
            continue

        dest_path = os.path.join(target_folder, filename)
        shutil.copy2(source_path, dest_path)
        logger.info(f"Copied {filename} to {dest_path}")
        dest_paths.append(dest_path)

    return dest_paths


def main():
    with st.sidebar:
        st.header("📚 Document Selection")

        # Tab for choosing between uploading or selecting existing files
        tab1, tab2 = st.tabs(["Upload Files", "Select Existing Files"])

        with tab1:
            st.subheader("Upload PDFs or TXT files")
            uploaded_files = st.file_uploader(
                "Choose files to upload",
                type=["pdf", "txt"],
                accept_multiple_files=True,
                key="file_uploader"
            )

            if uploaded_files:
                st.success(f"Successfully uploaded {len(uploaded_files)} file(s).")

                with st.spinner("Processing files..."):
                    documents = cached_process_files(uploaded_files)

                st.write("---")
                st.subheader("📚 Index Documents")

                if documents:
                    st.write(f"Ingested {len(documents)} document(s).")
                    st.info("The documents are now ready to index.")
                else:
                    st.warning("No documents were extracted from the uploaded files.")

        with tab2:
            st.subheader("Select from existing .txt files")
            available_files = get_available_txt_files()

            if available_files:
                selected_files = st.multiselect(
                    "Choose .txt files to process:",
                    options=available_files,
                    default=None,
                    help="Select Rigveda, Yajurveda or other text files from the project",
                    key="txt_file_selector"
                )

                if selected_files:
                    st.success(f"Selected {len(selected_files)} file(s).")

                    if st.button("Process Selected Files", key="process_txt_btn"):
                        with st.spinner(f"Processing {len(selected_files)} file(s)..."):
                            dest_paths = prepare_selected_files(selected_files)
                            if dest_paths:
                                process_uploaded_pdfs(dest_paths, extract_metadata=True)
                                st.success(f"✓ Processed {len(dest_paths)} file(s)")
                                st.info("Files are ready to index.")
                            else:
                                st.error("Failed to prepare files for processing")
            else:
                st.warning("No .txt files found in the project root directory.")

    st.title("RAG Chatbot")

    # Debug mode toggle and cleanup buttons in main area
    col1, col2, col3 = st.columns([2, 1, 1])
    with col2:
        debug_mode = st.checkbox("Debug Mode", value=st.session_state.get("debug_mode", False), key="debug_toggle")
        st.session_state["debug_mode"] = debug_mode

    with col3:
        if st.button("🗑️ Cleanup", help="Remove vector store locks and force cleanup"):
            with st.spinner("Cleaning up..."):
                # First try to remove just lock files
                removed = cleanup_qdrant_locks()
                if removed > 0:
                    st.success(f"Removed {removed} lock file(s)")

                # If still locked or user wants full cleanup, remove entire vector store
                if check_qdrant_lock() or st.session_state.get("force_cleanup", False):
                    if force_cleanup_vector_store():
                        st.success("✓ Vector store cleaned up")
                        # Clear session state
                        st.session_state["vector_store"] = None
                        st.session_state["document_chunks"] = None
                        st.session_state["retriever"] = None
                        st.session_state["rag_app"] = None
                    else:
                        st.error("Failed to cleanup vector store")
                else:
                    st.info("No locks found")

    # Check for Qdrant lock before allowing index creation
    vector_store_path = os.path.join(project_root, VECTORDB_FOLDER, COLLECTION_NAME)
    vector_store_exists = os.path.exists(vector_store_path) and os.path.isdir(vector_store_path)

    # Check if processed files exist
    processed_folder = os.path.join(project_root, LOCAL_FOLDER, COLLECTION_NAME)
    processed_files_exist = os.path.exists(processed_folder) and len(os.listdir(processed_folder)) > 0 if os.path.exists(processed_folder) else False

    if check_qdrant_lock():
        st.warning("⚠️ Qdrant database is locked. Click 'Cleanup' button to resolve.")

    # Show index status
    if vector_store_exists:
        st.info("ℹ️ Vector store already exists. Click 'Load Index' to use it or 'Rebuild Index' to recreate.")
    elif processed_files_exist:
        st.info("ℹ️ Processed files found. Click 'Create Index' to build the vector store.")
    else:
        st.warning("⚠️ No processed files found. Please upload or select files first.")

    # Buttons: Load existing or Rebuild (if exists), or Create (if doesn't exist)
    if vector_store_exists:
        col_load, col_rebuild = st.columns(2)

        with col_load:
            load_button = st.button("📂 Load Index", help="Load existing vector store")

        with col_rebuild:
            rebuild_button = st.button("🔄 Rebuild Index", disabled=not processed_files_exist, help="Force rebuild vector store from scratch")

        create_button = False
    else:
        load_button = False
        rebuild_button = False
        create_button = st.button("🔨 Create Index", disabled=not processed_files_exist, help="Build vector store from processed files")

    # Load existing index
    if load_button:
        if check_qdrant_lock():
            st.error("❌ Cannot load index: Qdrant database is locked by another process")
            st.info("💡 Click the 'Cleanup' button above to resolve this issue")
        else:
            try:
                with st.spinner("Loading existing vector store..."):
                    # Load existing index without forcing recreation
                    vec_db, docs = create_qdrant_vector_store(force_recreate=False)
                    st.session_state["vector_store"] = vec_db
                    st.session_state["document_chunks"] = docs
                    st.success("✓ Index loaded successfully")

                with st.spinner("Creating retriever..."):
                    st.session_state.retriever = create_retriever(vec_db, docs)
                    st.success("✓ Retriever created")

                with st.spinner("Setting up RAG pipeline..."):
                    st.session_state.rag_app = create_langgraph_app(st.session_state.retriever)
                    st.success("✓ RAG setup complete")
            except RuntimeError as e:
                if "already accessed" in str(e):
                    st.error("❌ Qdrant lock error detected. Click 'Cleanup' and try again.")
                else:
                    st.error(f"❌ Error: {str(e)}")
            except Exception as e:
                st.error(f"❌ Unexpected error: {str(e)}")
                logger.exception("Error during index loading")

    # Rebuild index from scratch
    if rebuild_button:
        # Check for locks before creating index
        if check_qdrant_lock():
            st.error("❌ Cannot create index: Qdrant database is locked by another process")
            st.info("💡 Click the 'Cleanup' button above to resolve this issue")
        else:
            try:
                with st.spinner("Rebuilding vector store from scratch..."):
                    # Force recreation by passing True
                    vec_db, docs = create_qdrant_vector_store(force_recreate=True)
                    st.session_state["vector_store"] = vec_db
                    st.session_state["document_chunks"] = docs
                    st.success("✓ Index rebuilt successfully")

                with st.spinner("Creating retriever..."):
                    st.session_state.retriever = create_retriever(vec_db, docs)
                    st.success("✓ Retriever created")

                with st.spinner("Setting up RAG pipeline..."):
                    st.session_state.rag_app = create_langgraph_app(st.session_state.retriever)
                    st.success("✓ RAG setup complete")
            except RuntimeError as e:
                if "already accessed" in str(e):
                    st.error("❌ Qdrant lock error detected. Click 'Cleanup' and try again.")
                else:
                    st.error(f"❌ Error: {str(e)}")
            except Exception as e:
                st.error(f"❌ Unexpected error: {str(e)}")
                logger.exception("Error during index rebuild")

    # Create new index (first time)
    if create_button:
        if check_qdrant_lock():
            st.error("❌ Cannot create index: Qdrant database is locked by another process")
            st.info("💡 Click the 'Cleanup' button above to resolve this issue")
        else:
            try:
                with st.spinner("Creating vector store for the first time..."):
                    # Create new index
                    vec_db, docs = create_qdrant_vector_store(force_recreate=True)
                    st.session_state["vector_store"] = vec_db
                    st.session_state["document_chunks"] = docs
                    st.success("✓ Index created successfully")

                with st.spinner("Creating retriever..."):
                    st.session_state.retriever = create_retriever(vec_db, docs)
                    st.success("✓ Retriever created")

                with st.spinner("Setting up RAG pipeline..."):
                    st.session_state.rag_app = create_langgraph_app(st.session_state.retriever)
                    st.success("✓ RAG setup complete")
            except RuntimeError as e:
                if "already accessed" in str(e):
                    st.error("❌ Qdrant lock error detected. Click 'Cleanup' and try again.")
                else:
                    st.error(f"❌ Error: {str(e)}")
            except Exception as e:
                st.error(f"❌ Unexpected error: {str(e)}")
                logger.exception("Error during index creation")

    # Get user input
    user_input = get_user_input()

    if "chat_history" not in st.session_state:
        initialize()

    if user_input and user_input.lower() not in {"exit", "quit"}:
        st.session_state.start_flag = True
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        result = handle_query_and_run_rag(user_input)

        # Extract answer and debug info
        if isinstance(result, dict) and "answer" in result:
            # Result is the full dict from RAG pipeline
            answer_content = result

            # Show debug info if enabled
            if st.session_state.get("debug_mode", False) and "evaluation" in result:
                with st.expander("🔍 Debug Information", expanded=False):
                    eval_data = result["evaluation"]
                    st.markdown(f"**Confidence Score:** {eval_data.get('confidence_score', 'N/A')}%")
                    st.markdown(f"**Reasoning:** {eval_data.get('reasoning', 'N/A')}")
                    st.markdown(f"**Decision:** {eval_data.get('decision', 'N/A')}")

                    if "enhanced_question" in result and result["enhanced_question"]:
                        st.markdown(f"**Enhanced Question:** {result['enhanced_question']}")

                    if "regeneration_count" in result:
                        st.markdown(f"**Regeneration Count:** {result['regeneration_count']}")
        else:
            # Fallback: wrap in dict format expected by display_chat
            answer_content = {"answer": str(result)}

        # Update session state with the new full conversation
        st.session_state.chat_history.append({"role": "assistant", "content": answer_content})
    elif (
        st.session_state.start_flag
        and user_input
        and user_input.lower() in {"exit", "quit"}
    ):
        print(
            f"Inside the else block: Flag: {st.session_state.start_flag}, user question: {user_input}"
        )
        if user_input is not None:
            st.session_state.chat_history.append(
                {"role": "user", "content": user_input}
            )
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": {"answer": "Thanks for chatting, Have a great day."},
                }
            )

        markdown_text = convert_to_markdown(st.session_state.chat_history)

        # Convert to bytes
        markdown_bytes = markdown_text.strip().encode()

        # Create a BytesIO object
        markdown_file = io.BytesIO(markdown_bytes)

        st.session_state.markdown_file = markdown_file  # store to use later

        st.session_state.start_flag = False

    display_chat(st.session_state.chat_history)
    if st.session_state.markdown_file != "":
        st.download_button(
            label="Download Chat History",
            data=st.session_state.markdown_file,
            file_name="chat_history.md",
            mime="text/markdown",
            key="download_button",
            on_click=initialize(),
        )


if __name__ == "__main__":
    main()
