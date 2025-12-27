"""Simple CLI to process one or more documents (PDFs and TXT files), build the index and ask questions.

Usage:
  - Edit HARDCODED_FILES below to point to your file(s), OR
  - Run with --file /path/to/file1.pdf --file /path/to/file2.txt to override
  - Run with --files /path/to/file1.pdf /path/to/file2.txt (space-separated)

Supported formats: PDF, TXT

This script will:
  1. Copy all files into the project's LOCAL_FOLDER/COLLECTION_NAME directory.
  2. Call `process_uploaded_pdfs` to convert them to markdown and extract metadata.
     - PDFs: Extract text using PDF extractor
     - TXT: Convert directly to markdown format
  3. Create a unified Qdrant vector store and retriever (all documents in one collection).
  4. Start a simple REPL to ask questions against the indexed documents.

Each document maintains its source metadata (filename) so you can identify which
file each answer came from.

Note: the processing function deletes the copied files after processing (same behavior
as the Streamlit frontend). If you want to keep the originals, point to different
source locations when overriding with --file.
"""
import argparse
import os
import shutil
import json
import glob
import logging

from helper import project_root, logger
from config import LOCAL_FOLDER, COLLECTION_NAME, VECTORDB_FOLDER
from utils.process_files import process_uploaded_pdfs
from utils.index_files import create_qdrant_vector_store
from utils.retriever import create_retriever
from utils.final_block_rag import create_langgraph_app, run_rag_with_langgraph


# Change this to your preferred default file(s) (absolute or relative to project root).
# Example single PDF: [os.path.join(project_root, "examples", "my_doc.pdf")]
# Example multiple files: [
#     os.path.join(project_root, "rigveda-griffith.pdf"),
#     os.path.join(project_root, "yajurveda-griffith.txt"),
# ]
HARDCODED_FILES = [os.path.join(project_root, "sample.pdf")]


def restore_info_logging():
    """Restore INFO level logging for troubleshooting after an error."""
    logging.getLogger().setLevel(logging.INFO)
    for name in logging.root.manager.loggerDict:
        logging.getLogger(name).setLevel(logging.INFO)
    logger.info("⚠️  Error detected - INFO logging re-enabled for troubleshooting")


def cleanup_temp_folders():
    """Clean up temporary vector_store_tmp_* folders."""
    pattern = os.path.join(project_root, "vector_store_tmp_*")
    temp_folders = glob.glob(pattern)

    if temp_folders:
        logger.info(f"Cleaning up {len(temp_folders)} temporary folder(s)...")
        for folder in temp_folders:
            try:
                shutil.rmtree(folder)
                logger.info(f"Removed temporary folder: {folder}")
            except Exception as e:
                logger.warning(f"Failed to remove {folder}: {e}")
    else:
        logger.info("No temporary folders to clean up.")


def cleanup_session_folders():
    """Clean up session-specific folders: local_store and vector_store."""
    folders_to_clean = [
        os.path.join(project_root, LOCAL_FOLDER),
        os.path.join(project_root, VECTORDB_FOLDER),
    ]

    for folder in folders_to_clean:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
                logger.info(f"Removed session folder: {folder}")
                print(f"✓ Deleted: {folder}")
            except Exception as e:
                logger.error(f"Failed to remove {folder}: {e}")
                print(f"✗ Failed to delete {folder}: {e}")
        else:
            logger.info(f"Folder does not exist: {folder}")


def prompt_cleanup_session():
    """Prompt user to clean up session folders before starting."""
    print("\n" + "=" * 60)
    print("SESSION CLEANUP OPTIONS")
    print("=" * 60)
    print(f"The following folders contain session-specific data:")
    print(f"  • {LOCAL_FOLDER}/")
    print(f"  • {VECTORDB_FOLDER}/")
    print()

    while True:
        response = input("Delete these folders before starting? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            cleanup_session_folders()
            print()
            return True
        elif response in ['n', 'no']:
            print("Keeping existing session data.\n")
            return False
        else:
            print("Please enter 'y' or 'n'")


def prepare_and_process(file_paths: list):
    """Copy files (PDFs/TXT) into LOCAL_FOLDER/COLLECTION_NAME and call processing.

    Args:
        file_paths: List of paths to files (PDF or TXT) to process
    """
    target_folder = os.path.join(project_root, LOCAL_FOLDER, COLLECTION_NAME)
    os.makedirs(target_folder, exist_ok=True)

    dest_paths = []
    for file_path in file_paths:
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        dest_path = os.path.join(target_folder, os.path.basename(file_path))
        # copy the file so process_uploaded_pdfs behaves like the frontend
        shutil.copy2(file_path, dest_path)
        logger.info(f"Copied file to {dest_path}")
        dest_paths.append(dest_path)

    # process all copied files at once (this removes files after processing)
    logger.info(f"Processing {len(dest_paths)} file(s)...")
    process_uploaded_pdfs(dest_paths, extract_metadata=True)
    logger.info(f"Successfully processed {len(dest_paths)} file(s)")
def build_index_and_retriever(force: bool = False):
    """Create Qdrant vector store and retriever from processed docs.

    If `force` is True, remove any existing vector store directory and
    the chunks file so indexing starts from a clean state.
    """
    # Remove previous vector store and chunks file if forcing a clean index
    if force:
        vec_store_path = os.path.join(project_root, VECTORDB_FOLDER, COLLECTION_NAME)
        chunks_file = os.path.join(vec_store_path, "docs_chunks.pkl")
        try:
            if os.path.isdir(vec_store_path):
                shutil.rmtree(vec_store_path)
                logger.info("Removed existing vector store at %s", vec_store_path)
        except Exception:
            logger.exception("Failed to remove existing vector store %s", vec_store_path)

        try:
            # If chunks file existed elsewhere, attempt deletion as well
            if os.path.isfile(chunks_file):
                os.remove(chunks_file)
                logger.info("Removed existing chunks file %s", chunks_file)
        except Exception:
            logger.exception("Failed to remove chunks file %s", chunks_file)

    vec_db, docs = create_qdrant_vector_store(force_recreate=force)
    retriever = create_retriever(vec_db, docs)
    return vec_db, docs, retriever


def run_repl(retriever):
    app = create_langgraph_app(retriever)
    print("\nReady. Enter questions (type 'exit' or 'quit' to stop).\n")

    # Initialize chat history outside the loop to persist across questions
    chat_history = []

    while True:
        try:
            question = input("Q> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            cleanup_temp_folders()
            break
        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            print("Goodbye.")
            cleanup_temp_folders()
            break

        graph_state = {
            "question": question,
            "chat_history": chat_history,  # Use persistent chat history
            "documents": [],
            "answer": "",
            "enhanced_question": "",
            "is_follow_up": False,
            "reset_history": False,
            "regeneration_count": 0,  # Initialize regeneration counter
        }

        result = run_rag_with_langgraph(graph_state, app)

        # Update the persistent chat history with the result
        if result and "chat_history" in result:
            chat_history = result["chat_history"]

        if isinstance(result, str):
            # sometimes returns serialized JSON
            try:
                parsed = json.loads(result)
            except Exception:
                print(result)
                continue
            result = parsed

        # result expected to be a dict with "answer"
        if isinstance(result, dict):
            answer = result.get("answer")
            # If the answer is a structured object with 'answer' text inside
            if isinstance(answer, dict):
                print(answer.get("answer", "(no answer returned)"))
            else:
                print(answer)
        else:
            print(result)


def main():
    parser = argparse.ArgumentParser(
        description="Process one or more documents (PDFs or TXT files) and query them via CLI",
        epilog="""
Examples:
  # Process single PDF
  python src/cli_run.py --file rigveda.pdf

  # Process single TXT file
  python src/cli_run.py --file yajurveda.txt

  # Process multiple files (option 1: multiple --file flags)
  python src/cli_run.py --file rigveda.pdf --file yajurveda.txt

  # Process multiple files (option 2: --files with space-separated list)
  python src/cli_run.py --files rigveda.pdf yajurveda.txt

  # Force reindex with multiple files
  python src/cli_run.py --files rigveda.pdf yajurveda.txt --force

  # Mix PDFs and TXT files
  python src/cli_run.py --files doc1.pdf doc2.txt doc3.pdf
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--file",
        type=str,
        action='append',
        dest='file_list',
        help="Path to file (PDF or TXT) - can be used multiple times: --file file1.pdf --file file2.txt"
    )
    parser.add_argument(
        "--files",
        type=str,
        nargs='+',
        help="Space-separated list of file paths (PDFs or TXT) - alternative to multiple --file flags"
    )
    # Keep --pdf and --pdfs for backward compatibility
    parser.add_argument(
        "--pdf",
        type=str,
        action='append',
        dest='pdf_list',
        help="Path to PDF (can be used multiple times: --pdf file1.pdf --pdf file2.pdf)"
    )
    parser.add_argument(
        "--pdfs",
        type=str,
        nargs='+',
        help="Space-separated list of PDF paths (alternative to multiple --pdf flags)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force clean reindex: delete any existing vector store and chunks before indexing",
    )
    parser.add_argument(
        "--no-cleanup-prompt",
        action="store_true",
        help="Skip the session cleanup prompt and keep existing data",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress INFO logs (only show warnings and errors). Automatically disabled if errors occur.",
    )
    args = parser.parse_args()

    # Collect all file paths from --file/--files and --pdf/--pdfs arguments (backward compatibility)
    file_paths = []
    if args.file_list:
        file_paths.extend(args.file_list)
    if args.files:
        file_paths.extend(args.files)
    if args.pdf_list:
        file_paths.extend(args.pdf_list)
    if args.pdfs:
        file_paths.extend(args.pdfs)

    # If no files specified via arguments, use hardcoded defaults
    if not file_paths:
        file_paths = HARDCODED_FILES

    # Convert relative paths to absolute paths
    absolute_file_paths = []
    for file_path in file_paths:
        if not os.path.isabs(file_path):
            # make relative paths relative to project root
            file_path = os.path.join(project_root, file_path)
        absolute_file_paths.append(file_path)

    logger.info(f"Will process {len(absolute_file_paths)} file(s): {[os.path.basename(p) for p in absolute_file_paths]}")

    # Set logging level based on --quiet flag
    if args.quiet:
        import logging
        # Set root logger to WARNING
        logging.getLogger().setLevel(logging.WARNING)
        # Set all currently configured loggers to WARNING
        for name in logging.root.manager.loggerDict:
            logging.getLogger(name).setLevel(logging.WARNING)
        # Specifically target common loggers
        for logger_name in ['helper', 'config', 'settings', 'cli_run', 'index_files',
                           'retriever', 'final_block_rag', 'process_files', 'sentence_transformers',
                           'transformers', 'qdrant_client', 'httpx', 'httpcore']:
            logging.getLogger(logger_name).setLevel(logging.WARNING)

    # Prompt for session cleanup unless --no-cleanup-prompt is specified
    if not args.no_cleanup_prompt:
        prompt_cleanup_session()

    try:
        prepare_and_process(absolute_file_paths)
    except Exception as e:
        # Re-enable INFO logging on error for troubleshooting
        if args.quiet:
            restore_info_logging()
        logger.error(f"Failed to prepare/process file(s): {e}")
        print(f"Error: {e}")
        return

    try:
        vec_db, docs, retriever = build_index_and_retriever(force=args.force)
    except Exception as e:
        # Re-enable INFO logging on error for troubleshooting
        if args.quiet:
            restore_info_logging()
        # Log full traceback to help debug where the error originates
        logger.exception("Failed to build index/retriever")
        import traceback

        traceback.print_exc()
        print(f"Indexing error: {e}")
        return

    run_repl(retriever)


if __name__ == "__main__":
    main()
