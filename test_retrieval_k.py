#!/usr/bin/env python3
"""Test script to verify RETRIEVAL_K=15 improvement for Rigveda retrieval."""

import os
import sys

# Set RETRIEVAL_K BEFORE importing any modules
os.environ['RETRIEVAL_K'] = '15'

from src.config import RETRIEVAL_K
print(f"✅ RETRIEVAL_K = {RETRIEVAL_K}")

from src.utils.agentic_rag import get_shared_retriever

retriever = get_shared_retriever()
print(f"Retriever k = {retriever.k}\n")

# Test query
results = retriever.invoke("Who is Sudas in Rigveda?")

print(f'\n✅ Retrieved {len(results)} documents\n')
rigveda_count = 0
for i, doc in enumerate(results[:20], 1):
    title = doc.metadata.get('title', 'Unknown')[:70]
    source = doc.metadata.get('source', 'unknown')
    
    # Count Rigveda
    if 'rigveda' in title.lower() or 'rigveda' in source.lower():
        rigveda_count += 1
        marker = "⭐ RIGVEDA"
    else:
        marker = "         "
    
    print(f'{i:2d}. {marker} {title}')

print(f'\n📊 Summary: {rigveda_count} Rigveda documents in top {len(results)}')
