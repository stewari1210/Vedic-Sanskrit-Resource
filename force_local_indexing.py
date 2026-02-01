#!/usr/bin/env python3
"""
Force local indexing of all documents including Pancavamsa.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(".").absolute()))

print("🔄 FORCE LOCAL INDEXING WITH PANCAVAMSA")
print("=" * 70)

# Temporarily unset cloud credentials to force local indexing
os.environ['QDRANT_URL'] = ''
os.environ['QDRANT_API_KEY'] = ''

# Force reload of config
for mod in list(sys.modules.keys()):
    if 'src.' in mod:
        del sys.modules[mod]

from src.utils.index_files import create_qdrant_vector_store

print("\n1️⃣  Indexing locally (forcing local storage)...")
vector_store, docs = create_qdrant_vector_store(force_recreate=True)

print(f"\n✅ Local indexing complete!")
print(f"   Total chunks: {len(docs)}")

# Check if Pancavamsa is now indexed
print(f"\n2️⃣  Verifying Pancavamsa in index...")
pb_chunks = [d for d in docs if 'pancavamsa' in (d.metadata.get('title', '') or '').lower() or 'pancavimsa' in (d.metadata.get('title', '') or '').lower()]

print(f"   Pancavamsa chunks found: {len(pb_chunks)}")
if pb_chunks:
    print(f"   First PB chunk title: {pb_chunks[0].metadata.get('title', 'N/A')}")

print(f"\n3️⃣  Summary by source:")
sources = {}
for doc in docs:
    title = doc.metadata.get('title', 'Unknown')
    sources[title] = sources.get(title, 0) + 1

for title in sorted(sources.keys(), key=lambda x: -sources[x])[:15]:
    count = sources[title]
    pct = 100 * count / len(docs)
    print(f"      {title[:45]:<45} {count:>6} ({pct:>5.1f}%)")

print("\n" + "=" * 70)
print(f"✅ Local indexing complete!")
