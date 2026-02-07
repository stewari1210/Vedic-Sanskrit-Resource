#!/usr/bin/env python3
"""
Upload enriched Sanskrit documents directly to Qdrant Cloud with full metadata preservation
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from langchain_community.vectorstores import Qdrant
from src.utils.index_files import load_documents_with_metadata, chunk_doc
from src.config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME, LOCAL_FOLDER
from src.settings import Settings
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance

load_dotenv()

print("\n" + "=" * 90)
print("📤 UPLOADING ENRICHED SANSKRIT DOCUMENTS TO QDRANT CLOUD")
print("=" * 90)

# Initialize Qdrant Cloud client
print("\n🔌 Connecting to Qdrant Cloud...")
client = QdrantClient(
    url=str(QDRANT_URL),
    api_key=str(QDRANT_API_KEY)
)
print("✅ Connected to Qdrant Cloud")

# Check if collection exists
try:
    collection_info = client.get_collection(str(COLLECTION_NAME))
    print(f"\n📍 Collection '{COLLECTION_NAME}' exists")
    print(f"   Status: {collection_info.status}")
    print(f"   Current points: {collection_info.points_count:,}")
except Exception as e:
    print(f"⚠️  Collection '{COLLECTION_NAME}' not found: {e}")
    print("   Will be created automatically")

# Load documents with metadata from local_store
print("\n📂 Loading documents from local_store...")
documents = load_documents_with_metadata(str(LOCAL_FOLDER))
print(f"✅ Loaded {len(documents)} documents")

# Show what we're loading
print("\n📚 Documents being uploaded:")
print("-" * 90)
unique_docs = {}
for doc in documents:
    meta = doc.metadata
    title = meta.get('title', 'Unknown')
    filename = meta.get('filename', 'unknown')
    preprocessing = meta.get('preprocessing', 'none')
    
    doc_key = (title, filename)
    if doc_key not in unique_docs:
        unique_docs[doc_key] = {
            'count': 0,
            'preprocessing': preprocessing,
            'metadata': meta
        }
    unique_docs[doc_key]['count'] += 1

for idx, ((title, filename), doc_info) in enumerate(sorted(unique_docs.items(), key=lambda x: x[1]['count'], reverse=True), 1):
    preprocessing = doc_info['preprocessing']
    count = doc_info['count']
    mark = "✨" if preprocessing == "sanskrit" else "  "
    print(f"{mark} {idx}. {title[:50]:50} ({count:4} docs, preprocessing={preprocessing})")

# Chunk documents
print("\n✂️  Chunking documents...")
chunks = chunk_doc(documents)
print(f"✅ Created {len(chunks)} chunks")

# Upload to Qdrant Cloud
print("\n📤 Uploading to Qdrant Cloud...")
print(f"   Collection: {COLLECTION_NAME}")
print(f"   Total chunks: {len(chunks):,}")

try:
    vector_store = Qdrant.from_documents(
        documents=chunks,
        embedding=Settings.get_embed_model() or None,
        url=str(QDRANT_URL),
        api_key=str(QDRANT_API_KEY),
        collection_name=str(COLLECTION_NAME),
        force_recreate=False,  # Don't delete existing data
        prefer_grpc=False
    )
    print("✅ Successfully uploaded to Qdrant Cloud!")
    
    # Verify upload
    collection_info = client.get_collection(str(COLLECTION_NAME))
    print(f"\n✅ Verification:")
    print(f"   Total chunks in collection: {collection_info.points_count:,}")
    print(f"   Collection status: {collection_info.status}")
    
except Exception as e:
    print(f"❌ Failed to upload: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 90)
print("✨ Upload complete!")
print("=" * 90 + "\n")
