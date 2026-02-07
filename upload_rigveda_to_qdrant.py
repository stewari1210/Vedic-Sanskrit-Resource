#!/usr/bin/env python3
"""
Upload enriched Rigveda documents to Qdrant Cloud
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from langchain_community.vectorstores import Qdrant
from langchain_core.documents import Document
from src.utils.index_files import chunk_doc
from src.config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME
from src.settings import Settings
from qdrant_client import QdrantClient
import json

load_dotenv()

print("\n" + "=" * 90)
print("📤 UPLOADING ENRICHED RIGVEDA DOCUMENTS TO QDRANT CLOUD")
print("=" * 90)

# Load Rigveda documents with enriched metadata
local_store = Path("/Users/shivendratewari/github/Vedic-Sanskrit-Tutor/local_store/ancient_history")
rigveda_folders = sorted([d for d in local_store.glob("r??") if d.is_dir()])

print(f"\n📂 Loading {len(rigveda_folders)} Rigveda documents...")

documents = []
for folder in rigveda_folders:
    md_file = folder / f"{folder.name}.md"
    meta_file = folder / f"{folder.name}_metadata.json"
    
    if not md_file.exists() or not meta_file.exists():
        print(f"⚠️  Skipping {folder.name}: missing files")
        continue
    
    # Read content
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Read metadata
    with open(meta_file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    # Create document
    doc = Document(page_content=content, metadata=metadata)
    documents.append(doc)
    
    preprocessing = metadata.get('preprocessing', 'none')
    print(f"   ✅ {folder.name}: {metadata.get('title', 'Unknown')} (preprocessing={preprocessing})")

print(f"\n✅ Loaded {len(documents)} Rigveda documents")

# Chunk documents
print(f"\n✂️  Chunking documents...")
chunks = chunk_doc(documents)
print(f"✅ Created {len(chunks)} chunks")

# Initialize Qdrant Cloud client
print(f"\n🔌 Connecting to Qdrant Cloud...")
client = QdrantClient(
    url=str(QDRANT_URL),
    api_key=str(QDRANT_API_KEY)
)
collection_info = client.get_collection(str(COLLECTION_NAME))
print(f"✅ Connected. Current points: {collection_info.points_count:,}")

# Upload to Qdrant Cloud
print(f"\n📤 Uploading {len(chunks):,} enriched chunks...")
print(f"   Collection: {COLLECTION_NAME}")

try:
    vector_store = Qdrant.from_documents(
        documents=chunks,
        embedding=Settings.get_embed_model(),
        url=str(QDRANT_URL),
        api_key=str(QDRANT_API_KEY),
        collection_name=str(COLLECTION_NAME),
        force_recreate=False,
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
print("✨ Rigveda upload complete!")
print("=" * 90 + "\n")
