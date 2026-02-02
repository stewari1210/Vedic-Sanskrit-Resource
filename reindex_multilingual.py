#!/usr/bin/env python3
"""
Re-index corpus with multilingual embeddings (768-dim).

This script forces local re-indexing using the new multilingual model
(paraphrase-multilingual-mpnet-base-v2) configured in src/settings.py.

Usage:
    python3 reindex_multilingual.py
"""

import os
import sys
import shutil
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

print("🌍 RE-INDEXING WITH MULTILINGUAL EMBEDDINGS (768-dim)")
print("=" * 70)
print(f"Model: paraphrase-multilingual-mpnet-base-v2")
print(f"Dimensions: 768 (same as current Qdrant collection)")
print(f"Languages: Hindi, Sanskrit, Devanagari, 50+ languages")
print("=" * 70)

# Import after path setup
from src.config import VECTORDB_FOLDER, COLLECTION_NAME
from src.utils.index_files import create_qdrant_vector_store

# Step 1: Remove old local index
local_index_path = Path(VECTORDB_FOLDER) / COLLECTION_NAME
chunks_file = Path(VECTORDB_FOLDER) / f"{COLLECTION_NAME}_chunks.pkl"

print(f"\n1️⃣  Removing old local index...")
if local_index_path.exists():
    shutil.rmtree(local_index_path)
    print(f"   ✅ Deleted: {local_index_path}")
else:
    print(f"   ℹ️  No existing index found at {local_index_path}")

if chunks_file.exists():
    os.remove(chunks_file)
    print(f"   ✅ Deleted: {chunks_file}")

# Step 2: Force local indexing (not cloud) to generate new embeddings
print(f"\n2️⃣  Re-indexing locally with multilingual embeddings...")
print(f"   This will take 7-12 minutes (26,921 chunks, 7.2 MB corpus)")
print(f"   Embedding model: paraphrase-multilingual-mpnet-base-v2 (768-dim)")
print()

# Temporarily disable cloud to force local indexing
original_url = os.getenv('QDRANT_URL', '')
original_key = os.getenv('QDRANT_API_KEY', '')
os.environ['QDRANT_URL'] = ''
os.environ['QDRANT_API_KEY'] = ''

try:
    # Force reload config to pick up disabled cloud credentials
    for mod in list(sys.modules.keys()):
        if 'src.' in mod:
            del sys.modules[mod]
    
    from src.utils.index_files import create_qdrant_vector_store
    
    # Create local index with new multilingual embeddings
    vector_store, docs = create_qdrant_vector_store(force_recreate=True)
    
    print(f"\n✅ Local re-indexing complete!")
    print(f"   Total chunks: {len(docs)}")
    print(f"   Vector store: {VECTORDB_FOLDER}/{COLLECTION_NAME}")
    
finally:
    # Restore original cloud credentials
    if original_url:
        os.environ['QDRANT_URL'] = original_url
    if original_key:
        os.environ['QDRANT_API_KEY'] = original_key

# Step 3: Show statistics
print(f"\n3️⃣  Index statistics:")
sources = {}
for doc in docs:
    title = doc.metadata.get('title', 'Unknown')
    sources[title] = sources.get(title, 0) + 1

print(f"\n   Top sources:")
for title in sorted(sources.keys(), key=lambda x: -sources[x])[:10]:
    count = sources[title]
    pct = 100 * count / len(docs)
    print(f"      {title[:50]:<50} {count:>6} ({pct:>5.1f}%)")

# Check Pancavamsa
pb_chunks = [d for d in docs if 'pancavamsa' in (d.metadata.get('title', '') or '').lower() 
             or 'pancavimsa' in (d.metadata.get('title', '') or '').lower()]
print(f"\n   Pancavamsa Brahmana chunks: {len(pb_chunks)}")

print("\n" + "=" * 70)
print(f"✅ SUCCESS: Local index created with multilingual embeddings!")
print(f"\nNext step: Upload to Qdrant Cloud")
print(f"   Command: python3 upload_vector_to_Qdrant_improved.py \\")
print(f"               --collection {COLLECTION_NAME} \\")
print(f"               --recreate false")
print("=" * 70)
