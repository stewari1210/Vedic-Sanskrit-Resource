#!/bin/bash

# Run the Vedic Sanskrit Tutor Streamlit Frontend

# Activate conda environment
source ~/miniforge-arm64/etc/profile.d/conda.sh
conda activate vedic-tutor

# Set environment variable for tokenizers
export TOKENIZERS_PARALLELISM=false

# Run Streamlit app
streamlit run src/sanskrit_tutor_frontend.py \
    --server.port 8502 \
    --server.headless true \
    --browser.gatherUsageStats false

# Note: Uses port 8502 to avoid conflict with main RAG frontend (8501)
