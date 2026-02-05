#!/usr/bin/env python
"""Quick test to see what metadata is in retrieved documents."""

import sys
import logging
from src.utils.retriever import HybridRetriever

logging.basicConfig(level=logging.DEBUG, format='%(message)s')

retriever = HybridRetriever()
query = 'Who is the father of Sudas?'
print(f"\n🔍 Retrieving documents for query: {query}\n")

docs = retriever._get_relevant_documents(query)

if docs:
    print(f"\n{'='*80}")
    print(f"TOP 3 DOCUMENTS METADATA")
    print(f"{'='*80}\n")
    
    for i, doc in enumerate(docs[:3]):
        print(f"\n📄 Document {i+1}:")
        print(f"   Content preview: {doc.page_content[:100]}...")
        print(f"\n   Metadata fields:")
        for key, val in doc.metadata.items():
            val_str = str(val)[:120]
            print(f"     • {key}: {val_str}")
else:
    print("No documents retrieved!")
