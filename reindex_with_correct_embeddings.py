#!/usr/bin/env python3
"""
Re-index all documents with the CORRECT embedding model (all-mpnet-base-v2).

This script:
1. Deletes the existing Qdrant collection (has wrong multilingual embeddings)
2. Re-indexes all documents from local_store with all-mpnet-base-v2
3. Uploads to Qdrant Cloud

IMPORTANT: This will restore your RAG to working condition!
"""

import os
import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.helper import logger
from src.config import COLLECTION_NAME, QDRANT_URL, QDRANT_API_KEY
from qdrant_client import QdrantClient

print("=" * 80)
print("RE-INDEXING WITH CORRECT EMBEDDINGS (all-mpnet-base-v2)")
print("=" * 80)
print()
print("This will:")
print("  1. Delete existing Qdrant collection (wrong embeddings)")
print("  2. Re-index all documents with all-mpnet-base-v2")
print("  3. Upload to Qdrant Cloud")
print()
print("⚠️  This will take ~5-10 minutes")
print()

response = input("Continue? (yes/no): ").strip().lower()
if response != 'yes':
    print("Aborted.")
    sys.exit(0)

print("\n" + "=" * 80)
print("STEP 1: Deleting old collection from Qdrant Cloud")
print("=" * 80)

try:
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    
    # Check if collection exists
    collections = client.get_collections().collections
    collection_names = [c.name for c in collections]
    
    if COLLECTION_NAME in collection_names:
        print(f"✓ Found collection: {COLLECTION_NAME}")
        client.delete_collection(COLLECTION_NAME)
        print(f"✓ Deleted collection: {COLLECTION_NAME}")
    else:
        print(f"ℹ️  Collection {COLLECTION_NAME} not found (already deleted or never existed)")
    
except Exception as e:
    logger.error(f"Error deleting collection: {e}")
    print(f"✗ Error: {e}")
    sys.exit(1)

print("\n" + "=" * 80)
print("STEP 2: Re-indexing documents with all-mpnet-base-v2")
print("=" * 80)
print()
print("Loading documents from local_store...")

from src.utils.index_files import create_qdrant_vector_store

try:
    vec_db, docs = create_qdrant_vector_store(force_recreate=True)
    print(f"\n✅ SUCCESS! Indexed {len(docs)} documents")
    print(f"   Collection: {COLLECTION_NAME}")
    print(f"   Embedding model: all-mpnet-base-v2 (768-dim)")
    print(f"   Location: Qdrant Cloud")
    
except Exception as e:
    logger.error(f"Error during indexing: {e}")
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("DONE! Your RAG should now work correctly.")
print("=" * 80)
print()
print("Test with: python3 test_retrieval_k.py")
print()
