#!/bin/bash
# Run the Vedic Sanskrit Learning Agent

cd "$(dirname "$0")"

# Activate conda environment if needed
# conda activate rag-py311

# Run the tutor
python src/vedic_sanskrit_tutor.py "$@"
