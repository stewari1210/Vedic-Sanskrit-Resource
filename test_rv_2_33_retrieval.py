"""
Test retrieval for RV 2.33 (Rudra hymn)
"""
import sys
import os
import re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.cli_run import build_index_and_retriever
from helper import logger

def parse_verse_reference(verse_reference):
    """Parse verse reference to extract formatted hymn ID"""
    match = re.match(r'(RV|YV)\s*(\d+)\.(\d+)', verse_reference.upper())

    if match:
        veda, book, hymn = match.groups()
        # Format as Griffith uses: [02-033] for RV Book 2, Hymn 33
        griffith_hymn_id = f"[{int(book):02d}-{int(hymn):03d}]"
        return griffith_hymn_id
    return None

def test_retrieval(verse_ref="RV 2.33"):
    print(f"\n{'='*80}")
    print(f"Testing retrieval for: {verse_ref}")
    print(f"{'='*80}\n")

    # Parse to get hymn ID
    hymn_id = parse_verse_reference(verse_ref)
    print(f"Expected Griffith hymn ID: {hymn_id}")
    print(f"This should match '[02-033]' for RV Book 2, Hymn 33 (Rudra)\n")

    # Build index
    print("Building retriever...")
    vec_db, docs, retriever = build_index_and_retriever(force=False)

    # Test different queries
    queries = [
        f"{hymn_id} HYMN {verse_ref}",
        f"{verse_ref} hymn verse translation",
        f"RV 2 33 Rudra",
        f"Book 2 Hymn 33",
    ]

    for i, query in enumerate(queries, 1):
        print(f"\n{'='*80}")
        print(f"Query {i}: {query}")
        print(f"{'='*80}")

        docs = retriever.invoke(query)

        # Show top 3 results from each translator
        griffith_docs = [d for d in docs if 'griffith' in d.metadata.get('filename', '').lower()]
        sharma_docs = [d for d in docs if 'sharma' in d.metadata.get('filename', '').lower()]

        print(f"\n🔵 Top 3 Griffith results:")
        for j, doc in enumerate(griffith_docs[:3], 1):
            preview = doc.page_content[:150].replace('\n', ' ')
            print(f"  {j}. {preview}...")

        print(f"\n🟢 Top 3 Sharma results:")
        for j, doc in enumerate(sharma_docs[:3], 1):
            preview = doc.page_content[:150].replace('\n', ' ')
            print(f"  {j}. {preview}...")

if __name__ == "__main__":
    test_retrieval("RV 2.33")
