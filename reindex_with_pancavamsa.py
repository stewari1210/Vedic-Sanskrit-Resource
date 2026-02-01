#!/usr/bin/env python3
"""
Re-index all documents including Pancavamsa Brahmana with proper metadata.
"""

import os
import sys
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

print("🔄 RE-INDEXING ALL DOCUMENTS WITH PANCAVAMSA")
print("=" * 70)

from src.utils.index_files import create_qdrant_vector_store

print("\n1️⃣  Re-indexing with force_recreate=True on LOCAL store...")
print("   (This will recreate the local Qdrant collection with all docs)")

vector_store, docs = create_qdrant_vector_store(force_recreate=True)

print(f"\n✅ Local indexing complete!")
print(f"   Total documents loaded: {len(docs)}")

# Check if Pancavamsa is now indexed
print(f"\n2️⃣  Verifying Pancavamsa in index...")
pb_chunks = [d for d in docs if 'pancavamsa' in (d.metadata.get('title', '') or '').lower() or 'pancavimsa' in (d.metadata.get('title', '') or '').lower()]

print(f"   Pancavamsa chunks found: {len(pb_chunks)}")
if pb_chunks:
    print(f"   First PB chunk title: {pb_chunks[0].metadata.get('title', 'N/A')}")
    print(f"   Sample chunk (first 100 chars): {pb_chunks[0].page_content[:100]}...")

print("\n3️⃣  Summary by source:")
sources = {}
for doc in docs:
    title = doc.metadata.get('title', 'Unknown')
    sources[title] = sources.get(title, 0) + 1

for title in sorted(sources.keys(), key=lambda x: -sources[x])[:10]:
    count = sources[title]
    pct = 100 * count / len(docs)
    print(f"      {title[:50]}: {count} chunks ({pct:.1f}%)")

print("\n" + "=" * 70)
print("✅ Local re-indexing complete!")
print("   Next: Upload to Qdrant Cloud with metadata")
