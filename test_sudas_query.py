#!/usr/bin/env python
"""Test the agentic RAG directly."""

import logging
from src.utils.agentic_rag import run_agentic_rag

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(name)s: %(message)s')

query = "Who is the father of Sudas?"
print(f"\n🔍 Query: {query}\n")

result = run_agentic_rag(query, input_language="English")

print(f"\n{'='*80}")
print(f"RESPONSE")
print(f"{'='*80}")
print(result)
