#!/usr/bin/env python3
"""
Simple document retrieval from Qdrant Cloud
"""
import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from collections import defaultdict

load_dotenv()

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

print("\n" + "=" * 90)
print("📚 QDRANT CLOUD DOCUMENTS")
print("=" * 90)

collection_name = os.getenv("COLLECTION_NAME", "ancient_history")
collection_info = client.get_collection(collection_name)

print(f"\n📊 Collection: {collection_name}")
print(f"   Total chunks: {collection_info.points_count:,}")
print(f"   Status: {collection_info.status} ✅")

# Get a sample of documents
print(f"\n📖 Retrieving document sample...")
points, _ = client.scroll(
    collection_name=collection_name,
    offset=0,
    limit=1000,
    with_payload=True,
    with_vectors=False
)

# Track unique documents
docs_by_title = defaultdict(int)
docs_by_source = defaultdict(int)
sanskrit_count = 0
total_chunks = 0

for point in points:
    if point.payload:
        title = point.payload.get("title", "Unknown")
        source = point.payload.get("source", "unknown")
        preprocessing = point.payload.get("preprocessing", "none")
        
        docs_by_title[title] += 1
        docs_by_source[source] += 1
        total_chunks += 1
        
        if preprocessing == "sanskrit":
            sanskrit_count += 1

print(f"\n✅ Sample retrieved: {total_chunks} chunks from first batch")

print(f"\n📚 DOCUMENTS (by title):")
print("-" * 90)
for idx, (title, count) in enumerate(sorted(docs_by_title.items(), key=lambda x: x[1], reverse=True), 1):
    pct = (count / total_chunks * 100) if total_chunks > 0 else 0
    print(f"{idx}. {title[:60]:60} {count:6,} chunks ({pct:5.1f}%)")

print(f"\n📚 DOCUMENTS (by source):")
print("-" * 90)
for idx, (source, count) in enumerate(sorted(docs_by_source.items(), key=lambda x: x[1], reverse=True), 1):
    pct = (count / total_chunks * 100) if total_chunks > 0 else 0
    print(f"{idx}. {source[:40]:40} {count:6,} chunks ({pct:5.1f}%)")

print(f"\n" + "=" * 90)
print(f"✨ Sanskrit-preprocessed chunks: {sanskrit_count:,}")
print(f"📊 Total chunks in sample: {total_chunks:,}")
print(f"📈 Full collection size: {collection_info.points_count:,} chunks")
print("=" * 90 + "\n")
