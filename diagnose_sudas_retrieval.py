#!/usr/bin/env python
"""Diagnose what documents Qdrant Cloud returns for Sudas query."""

import logging
from src.utils.agentic_rag import run_agentic_rag

logging.basicConfig(level=logging.INFO, format='%(message)s')

query = "Who is the father of Sudas?"
print(f"\n🔍 Retrieving documents from Qdrant Cloud for: {query}\n")

result = run_agentic_rag(query, input_language="English")

print(f"\n{'='*80}")
print(f"RETRIEVED DOCUMENT CONTENTS")
print(f"{'='*80}\n")

corpus_examples = result.get('corpus_examples', [])
print(f"Retrieved {len(corpus_examples)} documents:\n")

for i, doc in enumerate(corpus_examples[:5]):
    print(f"\n{'─'*80}")
    print(f"📄 Document {i+1}:")
    print(f"   Title: {doc.metadata.get('title', 'N/A')}")
    print(f"   Filename: {doc.metadata.get('filename', 'N/A')}")
    print(f"   Creator: {doc.metadata.get('creator', 'N/A')}")
    print(f"   Content preview (first 300 chars):")
    print(f"   {repr(doc.page_content[:300])}")
    
    # Check if contains genealogical info
    content_lower = doc.page_content.lower()
    if 'divodasa' in content_lower or 'divodāsa' in content_lower:
        print(f"   ✅ CONTAINS 'Divodasa' - GENEALOGICAL INFO")
    elif 'father' in content_lower or 'pitr' in content_lower:
        print(f"   ⚠️ CONTAINS 'father' keyword")
    else:
        print(f"   ❌ NO genealogical info found")

print(f"\n{'='*80}")
print(f"FINAL ANSWER")
print(f"{'='*80}")
print(result['answer']['answer'][:500])
