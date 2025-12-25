#!/bin/bash
# RAG Chatbot Launcher
# Automatically uses the correct Python environment

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Use the explicit Python path from rag-py311 environment
PYTHON_BIN="/Users/shivendratewari/miniforge-arm64/envs/rag-py311/bin/python"

# Check if Python exists
if [ ! -f "$PYTHON_BIN" ]; then
    echo "❌ Error: rag-py311 environment not found at $PYTHON_BIN"
    echo "Please ensure the conda environment is installed."
    exit 1
fi

# Run the RAG chatbot with all provided arguments
cd "$SCRIPT_DIR"
exec "$PYTHON_BIN" src/cli_run.py "$@"
