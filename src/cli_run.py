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
import os
# CRITICAL: Set this BEFORE any HuggingFace/transformers imports (including transitive imports via helper/settings)
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import argparse
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
from utils.debate_agents import create_debate_orchestrator


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


def run_repl(retriever, debug=False):
    app = create_langgraph_app(retriever)
    print("\nReady. Enter questions (type 'exit' or 'quit' to stop).\n")
    if debug:
        print("🔍 DEBUG MODE: Detailed retrieval info will be shown\n")

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
            "debug": debug,  # Pass debug flag to RAG pipeline
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

            # Show debug info if enabled
            if debug and "evaluation" in result:
                eval_data = result["evaluation"]
                print(f"\n📊 Confidence: {eval_data.get('confidence_score', 'N/A')}%")
                if "reasoning" in eval_data:
                    print(f"💭 Reasoning: {eval_data['reasoning']}")
                if "documents" in result:
                    print(f"📄 Retrieved {len(result['documents'])} documents")
                print()

            # If the answer is a structured object with 'answer' text inside
            if isinstance(answer, dict):
                print(answer.get("answer", "(no answer returned)"))
            else:
                print(answer)
        else:
            print(result)


def auto_retrieve_both_translations(retriever, verse_reference: str):
    """Auto-retrieve verse text from BOTH Griffith and Sharma translations.

    This allows each agent to debate their own translator's version of the verse,
    rather than both debating the same text.

    Returns:
        tuple: (griffith_text, sharma_text) or (None, None) if retrieval fails
    """
    try:
        # Parse verse reference to extract book and hymn numbers
        # Examples: "RV 2.33", "RV 10.85.12", "YV 40.1"
        import re
        match = re.match(r'(RV|YV)\s*(\d+)\.(\d+)', verse_reference.upper())

        if match:
            veda, book, hymn = match.groups()
            # Format as Griffith uses: [02-033] for RV Book 2, Hymn 33
            griffith_hymn_id = f"[{int(book):02d}-{int(hymn):03d}]"

            # Use descriptive terms that appear in the actual hymns
            # This helps semantic search while avoiding the "233" number collision
            query = f"Book {int(book)} Hymn {int(hymn)} Mandala {int(book)} Sukta {int(hymn)}"
            logger.info(f"Searching for: Griffith {griffith_hymn_id}, Sharma MANDAL-{book}/SUKTA-{hymn}")
        else:
            # Fallback to generic search
            query = f"{verse_reference} hymn verse translation"
            griffith_hymn_id = None

        docs = retriever.invoke(query)

        if not docs:
            return None, None

        # Separate docs by translator
        griffith_docs = [d for d in docs if 'griffith' in d.metadata.get('filename', '').lower()]
        sharma_docs = [d for d in docs if 'sharma' in d.metadata.get('filename', '').lower()]

        # Filter out index/metadata pages (look for actual verse content)
        def is_likely_verse_content(text):
            """Check if text looks like actual verse content, not index/metadata."""
            text_lower = text.lower()
            # Exclude common index/metadata patterns
            if any(pattern in text_lower for pattern in ['page', 'index', 'contents', '---', '***']):
                return False
            # Look for verse-like content (has words, not just numbers/symbols)
            word_count = len([w for w in text.split() if w.isalpha() and len(w) > 2])
            return word_count > 10  # At least 10 real words

        def matches_hymn_id(text, hymn_id):
            """Check if text contains the specific hymn ID."""
            if not hymn_id:
                return True
            return hymn_id in text

        # Find best match from Griffith - prioritize correct hymn ID
        griffith_text = None
        if griffith_docs:
            # First try: exact hymn ID match (search ALL docs, not just top 10)
            if griffith_hymn_id:
                exact_matches = [doc for doc in griffith_docs if matches_hymn_id(doc.page_content, griffith_hymn_id)]
                logger.info(f"Found {len(exact_matches)} Griffith docs matching {griffith_hymn_id}")

                for doc in exact_matches:
                    if is_likely_verse_content(doc.page_content):
                        griffith_text = doc.page_content[:800].strip()  # Get more text
                        logger.info(f"✓ Found Griffith text with hymn ID {griffith_hymn_id}")
                        break

                # If exact matches exist but all are metadata, take the first one anyway
                if not griffith_text and exact_matches:
                    griffith_text = exact_matches[0].page_content[:800].strip()
                    logger.warning(f"Using Griffith match {griffith_hymn_id} despite low verse quality")

            # Fallback: any verse-like content
            if not griffith_text:
                for doc in griffith_docs[:5]:
                    if is_likely_verse_content(doc.page_content):
                        griffith_text = doc.page_content[:500].strip()
                        break

            # Last resort
            if not griffith_text and griffith_docs:
                griffith_text = griffith_docs[0].page_content[:500].strip()

        # Find best match from Sharma - look for MANDAL/SUKTA pattern
        sharma_text = None
        if sharma_docs:
            # Sharma uses format: "MANDAL - 2 / SUKTA - 33"
            if match:
                veda, book, hymn = match.groups()
                sharma_pattern = f"MANDAL - {int(book)} / SUKTA - {int(hymn)}"
                exact_matches = [doc for doc in sharma_docs if sharma_pattern.upper() in doc.page_content.upper()]
                logger.info(f"Found {len(exact_matches)} Sharma docs matching {sharma_pattern}")

                for doc in exact_matches:
                    content = doc.page_content
                    # Skip the introduction/preface text
                    if 'arjuna stood before' in content.lower() or 'all rights reserved' in content.lower():
                        continue
                    if is_likely_verse_content(content):
                        sharma_text = content[:800].strip()
                        logger.info(f"✓ Found Sharma text with pattern {sharma_pattern}")
                        break

                # Take first exact match even if not ideal verse content
                if not sharma_text and exact_matches:
                    for doc in exact_matches:
                        content = doc.page_content
                        if 'arjuna stood before' not in content.lower():
                            sharma_text = content[:800].strip()
                            logger.warning(f"Using Sharma match {sharma_pattern} despite low verse quality")
                            break

            # Fallback: skip introduction text
            if not sharma_text:
                for doc in sharma_docs[:10]:
                    content = doc.page_content
                    # Skip the introduction/preface text
                    if 'arjuna stood before' in content.lower() or 'all rights reserved' in content.lower():
                        continue
                    if is_likely_verse_content(content):
                        sharma_text = content[:500].strip()
                        logger.info(f"Found Sharma text (avoiding introduction)")
                        break
                    break

            # Fallback if nothing found
            if not sharma_text and sharma_docs:
                for doc in sharma_docs[:5]:
                    if is_likely_verse_content(doc.page_content):
                        sharma_text = doc.page_content[:500].strip()
                        break

        return griffith_text, sharma_text

    except Exception as e:
        logger.warning(f"Failed to auto-retrieve verse texts: {e}")
        return None, None


def run_debate_mode(retriever):
    """Run debate between Griffith (literal) and Sharma (philosophical) agents."""
    print("\n" + "=" * 80)
    print("🔥 VEDIC VERSE DEBATE MODE 🔥")
    print("=" * 80)
    print("Griffith Agent: Literal/Historical interpretation")
    print("Sharma Agent:   Philosophical/Spiritual interpretation")
    print("=" * 80)
    print("\nEnter verse details (type 'exit' or 'quit' to stop)\n")

    orchestrator = create_debate_orchestrator(griffith_retriever=retriever)

    while True:
        try:
            # Get verse reference
            verse_ref = input("Verse Reference (e.g., RV 1.32, YV 40.1): ").strip()
            if not verse_ref:
                continue
            if verse_ref.lower() in {"exit", "quit"}:
                print("\nExiting debate mode.")
                break

            # Get verse text (optional - can be auto-retrieved)
            print("Verse Text Options:")
            print("  1) Press Enter to AUTO-RETRIEVE both translations (Griffith + Sharma)")
            print("  2) Type 'manual' to provide your own text")
            print("  3) Paste verse text now (both agents will use same text)\n")

            choice = input("Your choice: ").strip().lower()

            verse_text = None
            griffith_text = None
            sharma_text = None

            if choice == "" or choice == "1":
                # Auto-retrieve both translations
                print("🔍 Auto-retrieving translations from both Griffith and Sharma...")
                griffith_text, sharma_text = auto_retrieve_both_translations(retriever, verse_ref)

                if griffith_text and sharma_text:
                    print("\n✓ Found Griffith's translation:")
                    print(f"  {griffith_text[:150]}...")
                    print("\n✓ Found Sharma's translation:")
                    print(f"  {sharma_text[:150]}...")
                    print("\n⚠️  Please verify these are the correct verses!")
                    confirm = input("Continue with these texts? (y/n): ").strip().lower()
                    if confirm not in ['y', 'yes']:
                        print("Please try again or provide text manually.\n")
                        continue
                elif griffith_text or sharma_text:
                    print("⚠️  Could only find one translation. Both agents will use it.")
                    verse_text = griffith_text or sharma_text
                    griffith_text = None
                    sharma_text = None
                else:
                    print("⚠️  Could not auto-retrieve verse texts. Please enter manually.")
                    continue

            elif choice == "manual" or choice == "2":
                # Manual input
                print("Enter verse text (press Enter twice when done):")
                lines = []
                while True:
                    line = input()
                    if line == "":
                        break
                    lines.append(line)
                verse_text = "\n".join(lines).strip()
                if not verse_text:
                    print("⚠️  No text provided. Please try again.")
                    continue

            else:
                # User pasted text directly
                verse_text = choice            # Get number of rounds
            rounds_input = input("Number of debate rounds (default: 2): ").strip()
            num_rounds = int(rounds_input) if rounds_input else 2

            print("\n" + "=" * 80)
            print(f"🎭 Starting debate on {verse_ref}")
            print("=" * 80 + "\n")

            # Run the debate
            result = orchestrator.run_debate(
                verse_reference=verse_ref,
                verse_text=verse_text,
                griffith_text=griffith_text,
                sharma_text=sharma_text,
                num_rounds=num_rounds
            )

            print("\n" + "=" * 80)
            print("✅ DEBATE COMPLETED")
            print("=" * 80)
            print(f"\nVerse: {verse_ref}")
            print(f"Rounds: {len(result['debate_transcript'])}")
            print(f"\n📊 FINAL SYNTHESIS:")
            print("=" * 80)
            print(result['synthesis'])
            print("=" * 80 + "\n")

        except (EOFError, KeyboardInterrupt):
            print("\n\nExiting debate mode.")
            break
        except ValueError as e:
            print(f"⚠️  Invalid input: {e}\n")
            continue
        except Exception as e:
            logger.exception("Error during debate")
            print(f"⚠️  Error: {e}\n")
            continue


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

  # Start interactive debate mode (Griffith vs Sharma)
  python src/cli_run.py --debate --no-cleanup-prompt

  # Run debate with auto-retrieved verse text (NEW - verse text optional!)
  python src/cli_run.py --debate --no-cleanup-prompt --verse "RV 1.32" --rounds 2

  # Run debate with manual verse text
  python src/cli_run.py --debate --no-cleanup-prompt --verse "RV 1.32" --verse-text "Indra slew Vritra..." --rounds 3
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
        "--debug",
        action="store_true",
        help="Show detailed retrieval info: query processing, document previews, confidence scores, and evaluation reasoning",
    )
    parser.add_argument(
        "--debate",
        action="store_true",
        help="Start debate mode: Griffith (literal) vs Sharma (philosophical) interpretation of Vedic verses",
    )
    parser.add_argument(
        "--verse",
        type=str,
        help="Verse reference for debate mode (e.g., 'RV 1.32'). Use with --debate flag.",
    )
    parser.add_argument(
        "--verse-text",
        type=str,
        help="Verse text for debate mode (OPTIONAL - will auto-retrieve from corpus if omitted). Use with --debate and --verse flags.",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=2,
        help="Number of debate rounds (default: 2). Use with --debate flag.",
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

    # Check if vector store already exists
    vec_store_path = os.path.join(project_root, VECTORDB_FOLDER, COLLECTION_NAME)
    vector_store_exists = os.path.exists(vec_store_path) and os.path.isdir(vec_store_path)

    # Skip file processing if vector store exists and we're not forcing reindex
    if vector_store_exists and not args.force:
        logger.info("Vector store already exists. Skipping file processing.")
        logger.info("Use --force flag to rebuild the index from scratch.")
    else:
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

    # Run debate mode or regular REPL
    if args.debate:
        if args.verse:
            # Non-interactive mode: single debate
            verse_text = args.verse_text
            griffith_text = None
            sharma_text = None

            # Auto-retrieve verse texts if not provided
            if not verse_text:
                print(f"🔍 Auto-retrieving translations for {args.verse}...")
                griffith_text, sharma_text = auto_retrieve_both_translations(retriever, args.verse)

                if not griffith_text and not sharma_text:
                    print(f"❌ Could not find verse texts for {args.verse}")
                    print("Please provide --verse-text or use interactive mode.")
                    return

                if griffith_text and sharma_text:
                    print(f"✓ Found Griffith: {griffith_text[:100]}...")
                    print(f"✓ Found Sharma: {sharma_text[:100]}...\n")
                else:
                    # Only one found - both agents will use it
                    verse_text = griffith_text or sharma_text
                    griffith_text = None
                    sharma_text = None
                    print(f"✓ Found: {verse_text[:100]}...\n")

            print("\n" + "=" * 80)
            print(f"🎭 Running debate on {args.verse}")
            print("=" * 80 + "\n")

            orchestrator = create_debate_orchestrator(griffith_retriever=retriever)
            result = orchestrator.run_debate(
                verse_reference=args.verse,
                verse_text=verse_text,
                griffith_text=griffith_text,
                sharma_text=sharma_text,
                num_rounds=args.rounds
            )

            print("\n" + "=" * 80)
            print("✅ DEBATE COMPLETED")
            print("=" * 80)
            print(f"\nVerse: {args.verse}")
            print(f"Rounds: {len(result['debate_transcript'])}")
            print(f"\n📊 FINAL SYNTHESIS:")
            print("=" * 80)
            print(result['synthesis'])
            print("=" * 80 + "\n")
        else:
            # Interactive mode: multiple debates
            run_debate_mode(retriever)
    else:
        run_repl(retriever, debug=args.debug)


if __name__ == "__main__":
    main()
