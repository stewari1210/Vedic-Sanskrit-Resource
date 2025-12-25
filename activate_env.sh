#!/bin/bash
# RAG Chatbot Environment Activation Script
# This ensures the correct Python environment is used

echo "========================================"
echo "RAG Chatbot Environment Setup"
echo "========================================"

# Completely reset PATH to avoid Intel binaries
export PATH="/Users/shivendratewari/miniforge-arm64/envs/rag-py311/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Disable all Python version managers
unset PYENV_VERSION
unset PYENV_ROOT
unset PYENV_SHELL
unset PYTHONPATH

# Set conda environment variables
export CONDA_DEFAULT_ENV="rag-py311"
export CONDA_PREFIX="/Users/shivendratewari/miniforge-arm64/envs/rag-py311"

# Verify
echo "✓ Python environment configured"
echo "  Python: $(which python)"
echo "  Version: $(python --version)"
echo "  Architecture: $(python -c 'import platform; print(platform.machine())')"
echo ""
echo "Testing PyMuPDF import..."
if python -c "import pymupdf; print(f'  ✓ PyMuPDF {pymupdf.__version__} loaded successfully')" 2>/dev/null; then
    echo ""
else
    echo "  ✗ PyMuPDF failed to load - architecture issue"
    exit 1
fi

echo "Ready to run! Use:"
echo "  python src/cli_run.py --pdf griffith.pdf"
echo "Or:"
echo "  ./run_rag.sh --pdf griffith.pdf"
echo "========================================"
