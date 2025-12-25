# Local RAG Chatbot with PDF Ingestion (CLI Version)

## Overview

This project implements a command-line interface (CLI) for a local Retrieval-Augmented Generation (RAG) chatbot that ingests PDF documents, extracts their content and metadata, and uses Langchain and LangGraph to create a conversational AI. The chatbot allows users to ask questions about the content of the ingested PDFs and receive relevant answers through an interactive terminal-based interface.

**Note:** This is a CLI-specific adaptation of the original Streamlit-based RAG chatbot developed by [Srinivas Laxminarayan](mailto:srini.lax86@gmail.com). This version removes the web frontend and focuses on a streamlined command-line experience.

## Key Features

-   **Command-Line Interface:** Simple CLI-based interaction for processing PDFs and querying documents
-   **PDF Ingestion:** Processes PDF documents to extract text content and metadata
-   **Markdown Conversion:** Converts PDF content to Markdown format for easier processing
-   **Metadata Extraction:** Extracts relevant metadata from PDFs to enhance the retrieval process
-   **Local RAG Implementation:** Utilizes a local RAG setup, ensuring data privacy and control
-   **Langchain Integration:** Leverages Langchain for document loading, text splitting, and vectorstore management
-   **LangGraph Implementation:** Employs LangGraph to orchestrate the RAG pipeline and manage conversation flow
-   **Chat History:** Maintains chat history for contextual conversations
-   **Session Management:** Automatic cleanup of temporary files and session data

## File Structure

The project structure is organized as follows:

-   `src/`: Contains the source code for the chatbot.
    -   `cli_run.py`: Main CLI script for processing PDFs and running the interactive question-answering loop
    -   `helper.py`: Initializes logging and defines project paths
    -   `config.py`: Configuration settings for local folders, collection names, and vector database
    -   `settings.py`: Application settings and environment configuration
    -   `utils/`: Contains utility modules
        -   `file_ops.py`: Implements file loading and saving operations
        -   `index_files.py`: Loads documents and their metadata, creates vector stores
        -   `process_files.py`: Processes uploaded PDFs, extracts text and metadata
        -   `final_block_rag.py`: Defines data structures for graph state and LangGraph application
        -   `structure_output.py`: Defines the structure for citation objects
        -   `retriever.py`: Implements document retrieval logic
        -   `vector_store.py`: Vector store management
        -   `prompts.py`: Prompt templates for the LLM
-   `local_store/`: Local storage for processed documents and metadata
-   `vector_store/`: Qdrant vector database storage
-   `README.md`: This file, providing an overview of the project
-   `requirements.txt`: Python package dependencies
-   `pyproject.toml`: Project metadata and dependencies
-   `.gitignore`: Specifies intentionally untracked files that Git should ignore

## Modules Description

-   **`cli_run.py`**: Main entry point for the CLI application. Handles PDF processing, vector store creation, and runs an interactive REPL for querying documents. Includes session cleanup functionality for managing temporary files.

-   **`helper.py`**: Initializes the logger and defines important project paths, such as the project root directory. Also appends the project root and parent directories to the system path.

-   **`config.py`**: Contains configuration constants for local folders, collection names, and vector database settings.

-   **`settings.py`**: Manages application settings and environment variables, including API keys and model configurations.

-   **`utils/file_ops.py`**: Provides utility functions for loading and saving text files, ensuring UTF-8 encoding.

-   **`utils/index_files.py`**: Provides the `load_documents_with_metadata` function, which loads markdown files and their metadata from a specified folder structure, creating Langchain `Document` objects. Also includes `create_qdrant_vector_store` for vector database initialization.

-   **`utils/process_files.py`**: Core function `process_uploaded_pdfs` that converts PDF files to markdown, extracts metadata, and saves the results. Uses PDF extraction library to convert PDFs.

-   **`utils/final_block_rag.py`**: Defines the `GraphState` TypedDict, which represents the state of the LangGraph graph, including the question, enhanced question, chat history, documents, and answer. Also contains the LangGraph application logic.

-   **`utils/structure_output.py`**: Defines the `Citation` Pydantic model for structuring citation information, including document name, number, and page numbers.

-   **`utils/retriever.py`**: Implements document retrieval logic using Qdrant vector store and optional BM25 retrieval.

-   **`utils/vector_store.py`**: Manages vector store operations and interactions with Qdrant.

-   **`utils/prompts.py`**: Contains prompt templates used for LLM interactions.

## Setup and Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd RAG-CHATBOT-CLI-Version-2
    ```

2.  **Install dependencies:**

    Using `uv` (recommended):
    ```bash
    uv sync
    ```
    This will automatically set up a virtual environment under `.venv`.

    Alternatively, using `pip`:
    ```bash
    pip install -r requirements.txt
    ```

    Or install from `pyproject.toml`:
    ```bash
    pip install -e .
    ```

3.  **Environment Configuration:**

    Create a `.env` file in the project root with your API keys:

    ```properties
    # Google / Gemini embeddings key
    GEMINI_API_KEY=your_gemini_api_key_here

    # Groq API key and model (used for generation)
    GROQ_API_KEY=your_groq_api_key_here
    MODEL=meta-llama/llama-4-maverick-17b-128e-instruct

    # Embedding model (Gemini embeddings example)
    EMBED_MODEL=gemini-embedding-001

    # Optional: override evaluator model (defaults to MODEL if unset)
    # EVAL_MODEL=meta-llama/llama-4-maverick-17b-128e-instruct
    ```

    You will need to create accounts with:
    - [Groq](https://groq.com/) for LLM generation
    - [Google AI Studio](https://makersuite.google.com/) for Gemini embeddings

## Usage

### Running the CLI

**IMPORTANT:** This project uses the `rag-py311` conda environment. You have several options to run it:

#### Option 1: Use the Launcher Script (Recommended)

```bash
./run_rag.sh --pdf path/to/your_document.pdf
```

The `run_rag.sh` script automatically uses the correct Python environment.

#### Option 2: Activate Environment First

```bash
# Activate the environment
source activate_env.sh

# Then run the chatbot
python src/cli_run.py --pdf path/to/your_document.pdf
```

#### Option 3: Use Explicit Python Path

```bash
/Users/shivendratewari/miniforge-arm64/envs/rag-py311/bin/python src/cli_run.py --pdf path/to/your_document.pdf
```

### Interactive Session

1.  **Process a PDF and start the interactive session:**

    ```bash
    ./run_rag.sh --pdf path/to/your_document.pdf
    ```

2.  **Session cleanup prompt:**

    When you start the CLI, you'll be prompted to clean up existing session data:
    - Answer `y` to delete `local_store/` and `vector_store/` folders (fresh start)
    - Answer `n` to keep existing session data

3.  **Ask questions:**

    Once the PDF is processed and indexed, you'll enter an interactive REPL where you can type questions about the document. The chatbot will retrieve relevant context and generate answers.

4.  **Exit:**

    Type `exit` or `quit` to stop the session. Temporary folders will be automatically cleaned up.

### CLI Options

```bash
./run_rag.sh --pdf /path/to/document.pdf
# Or:
python src/cli_run.py --pdf /path/to/document.pdf [OPTIONS]
```

Available options:
- `--pdf PATH`: Path to the PDF file to process (required or uses hardcoded default)
- `--no-cleanup-prompt`: Skip the session cleanup prompt and keep existing data
- `--force`: Force clean reindex by deleting the vector store before processing

### Examples

```bash
# Basic usage with cleanup prompt
python src/cli_run.py --pdf research_paper.pdf

# Skip cleanup prompt (keep existing data)
python src/cli_run.py --pdf research_paper.pdf --no-cleanup-prompt

# Force fresh reindex
python src/cli_run.py --pdf research_paper.pdf --force
```

## Advanced Usage

### Using a Specific Python Environment

If you're using conda or another environment manager:

```bash
# Create environment (optional)
conda create -n rag-py311 python=3.11 -y
conda activate rag-py311

# Install dependencies
pip install -r requirements.txt

# Run the CLI
python src/cli_run.py --pdf path/to/your_doc.pdf
```

### Session Management

The CLI provides automatic cleanup features:

- **On Startup**: Interactive prompt to delete session-specific folders (`local_store/` and `vector_store/`) before processing a new PDF
  - Use `--no-cleanup-prompt` flag to skip this prompt

- **On Exit**: Automatically deletes all temporary `vector_store_tmp_*` folders created during the session

### Troubleshooting

- **Authentication/Permission errors**: Verify your API keys (GEMINI_API_KEY, GROQ_API_KEY) in the `.env` file
- **Vector store locked**: If another process has the vector store open, you may see an `AlreadyLocked` error. The CLI will automatically create a temporary store as fallback
- **PDF processing issues**: Ensure `pymupdf` is installed in your environment

### Optional Dependencies

- **BM25 retriever**: Install `rank_bm25` to enable BM25-based retrieval:
  ```bash
  pip install rank_bm25
  ```

- **Better PDF layout**: Consider installing `pymupdf_layout`:
  ```bash
  pip install pymupdf_layout
  ```

## Dependencies

-   [Langchain](https://www.langchain.com/): Framework for developing applications powered by language models
-   [LangGraph](https://python.langchain.com/docs/langgraph): Library for building LLM-powered graphs
-   [Qdrant](https://qdrant.tech/): Vector database for similarity search
-   [Pymupdf](https://pymupdf.readthedocs.io/en/latest/): Library to programmatically access and manipulate PDF documents
-   [Pydantic](https://docs.pydantic.dev/): Data validation and settings management using Python type annotations
-   [Groq](https://groq.com/): Fast LLM inference API
-   [Google Gemini](https://ai.google.dev/): Embedding models for document vectorization

## Project Notes

- The local Qdrant store is created under `vector_store/`. For concurrent access from multiple processes, consider running a Qdrant server (Docker or cloud) instead of the local on-disk store.
- Consider pinning and freezing your environment once stable (use `pip freeze > requirements-frozen.txt`)
- Processed documents are stored in `local_store/` with their metadata
- Vector embeddings are stored in `vector_store/` for quick retrieval

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues to suggest improvements or report bugs.

## Credits

This CLI version is adapted from the original Streamlit-based RAG chatbot developed by **Srinivas Laxminarayan** (srini.lax86@gmail.com). The current version has been modified to provide a streamlined command-line interface, removing the web frontend dependencies while maintaining the core RAG functionality.

## License

[Private License]
