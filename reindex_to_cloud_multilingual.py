#!/usr/bin/env python3
"""
Re-index corpus DIRECTLY to Qdrant Cloud with multilingual embeddings (768-dim).

This script bypasses local indexing and uploads directly to Qdrant Cloud,
avoiding the 20,000 point limit of local mode.

Usage:
    python reindex_to_cloud_multilingual.py
"""

import os
import sys
import pickle
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

print("🌍 RE-INDEXING DIRECTLY TO QDRANT CLOUD (768-dim)")
print("=" * 70)
print(f"Model: paraphrase-multilingual-mpnet-base-v2")
print(f"Dimensions: 768 (same as existing collection)")
print(f"Languages: Hindi, Sanskrit, Devanagari, 50+ languages")
print(f"Target: Qdrant Cloud (bypassing local 20K limit)")
print("=" * 70)

# Import after path setup
from src.config import VECTORDB_FOLDER, COLLECTION_NAME, QDRANT_URL, QDRANT_API_KEY
from src.utils.index_files import load_documents_with_metadata, chunk_doc
from src.settings import Settings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from langchain_qdrant import QdrantVectorStore

# Verify cloud credentials
if not QDRANT_URL or not QDRANT_API_KEY:
    print("\n❌ ERROR: QDRANT_URL and QDRANT_API_KEY must be set in .env")
    print("   Cannot proceed without cloud credentials.")
    sys.exit(1)

print(f"\n✅ Cloud credentials found")
print(f"   URL: {QDRANT_URL[:50]}...")

# Step 1: Load documents
print(f"\n1️⃣  Loading documents from local_store/...")
documents = load_documents_with_metadata('local_store')

print(f"\n📊 Documents loaded: {len(documents)}")
for i, doc in enumerate(documents, 1):
    title = doc.metadata.get('title', 'Unknown')
    size = len(doc.page_content)
    print(f"   {i:2d}. {title[:55]:<55} ({size:>8,} chars)")

# Step 2: Chunk documents
print(f"\n2️⃣  Chunking documents...")
chunks = chunk_doc(documents)
print(f"   Total chunks: {len(chunks):,}")

# Save chunks for reference
chunks_file = Path(VECTORDB_FOLDER) / f"{COLLECTION_NAME}_chunks.pkl"
chunks_file.parent.mkdir(parents=True, exist_ok=True)
with open(chunks_file, "wb") as f:
    pickle.dump(chunks, f)
print(f"   Saved chunks to: {chunks_file}")

# Step 3: Connect to Qdrant Cloud and recreate collection
print(f"\n3️⃣  Connecting to Qdrant Cloud...")
client = QdrantClient(url=str(QDRANT_URL), api_key=str(QDRANT_API_KEY))

# Check if collection exists and delete it
try:
    collection_info = client.get_collection(COLLECTION_NAME)
    print(f"   ✅ Found existing collection '{COLLECTION_NAME}'")
    print(f"      Current points: {collection_info.points_count:,}")
    
    print(f"\n   🔄 Deleting old collection...")
    client.delete_collection(COLLECTION_NAME)
    print(f"   ✅ Deleted")
    
except Exception as e:
    print(f"   ℹ️  Collection doesn't exist (will create new)")

# Create fresh collection with multilingual embeddings
print(f"\n   🆕 Creating fresh collection with 768-dim vectors...")
try:
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=768,  # paraphrase-multilingual-mpnet-base-v2
            distance=Distance.COSINE,
        ),
    )
    print(f"   ✅ Collection '{COLLECTION_NAME}' created")
except Exception as e:
    print(f"   ❌ Error creating collection: {e}")
    sys.exit(1)

# Step 4: Generate embeddings and upload
print(f"\n4️⃣  Generating embeddings and uploading to cloud...")
print(f"   This will take 10-15 minutes for {len(chunks):,} chunks")
print(f"   Embedding model: paraphrase-multilingual-mpnet-base-v2 (768-dim)")
print()

try:
    # Initialize embedding model
    embed_model = Settings.get_embed_model()
    
    # Create vector store (this will generate embeddings and upload)
    # force_recreate=False because we already recreated the collection above
    vector_store = QdrantVectorStore.from_documents(
        documents=chunks,
        embedding=embed_model,
        url=str(QDRANT_URL),
        api_key=str(QDRANT_API_KEY),
        collection_name=str(COLLECTION_NAME),
        force_recreate=False,  # Already recreated above
        prefer_grpc=False,
    )
    
    print(f"\n✅ SUCCESS: Uploaded {len(chunks):,} chunks to Qdrant Cloud!")
    
except Exception as e:
    print(f"\n❌ ERROR during upload: {e}")
    print(f"\nPartial progress may have been saved to cloud.")
    sys.exit(1)

# Step 5: Verify upload
print(f"\n5️⃣  Verifying upload...")
try:
    final_info = client.get_collection(COLLECTION_NAME)
    print(f"   ✅ Collection '{COLLECTION_NAME}'")
    print(f"      Total points: {final_info.points_count:,}")
    print(f"      Vector dimensions: {final_info.config.params.vectors.size}")
    
    # Show statistics by source
    print(f"\n📊 Chunks by document:")
    from collections import Counter
    titles = [chunk.metadata.get('title', 'Unknown') for chunk in chunks]
    title_counts = Counter(titles)
    for title, count in sorted(title_counts.items(), key=lambda x: -x[1])[:15]:
        pct = 100 * count / len(chunks)
        print(f"      {title[:50]:<50} {count:>6,} ({pct:>5.1f}%)")
    
except Exception as e:
    print(f"   ⚠️  Could not verify: {e}")

print("\n" + "=" * 70)
print(f"✅ RE-INDEXING COMPLETE!")
print(f"\nNext step: Test bilingual queries in Streamlit")
print(f"   Command: bash run_sanskrit_tutor_web.sh")
print("=" * 70)
