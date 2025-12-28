#!/bin/bash
# RAG Chatbot Launcher
# Automatically uses the correct Python environment
#
# Usage Examples:
# 1. Run with all 4 Vedic translations:
#    ./run_rag.sh --files rigveda-sharma_COMPLETE_english_with_metadata.txt \
#                          griffith-rigveda_COMPLETE_english_with_metadata.txt \
#                          yajurveda-sharma_COMPLETE_english_with_metadata.txt \
#                          yajurveda-griffith_COMPLETE_english_with_metadata.txt
#
# 2. Skip cleanup prompt (use existing indexed data):
#    ./run_rag.sh --no-cleanup-prompt --files rigveda-sharma_COMPLETE_english_with_metadata.txt
#
# 3. Combine options:
#    ./run_rag.sh --no-cleanup-prompt --files rigveda-sharma_COMPLETE_english_with_metadata.txt \
#                                              griffith-rigveda_COMPLETE_english_with_metadata.txt

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
