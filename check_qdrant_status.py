#!/usr/bin/env python3
"""
Check Qdrant Cloud status and document counts
"""
import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

collection_name = os.getenv("COLLECTION_NAME", "ancient_history")

print("\n" + "=" * 90)
print("📊 QDRANT CLOUD STATUS")
print("=" * 90)

collection_info = client.get_collection(collection_name)

print(f"\n📍 Collection: {collection_name}")
print(f"   Status: {collection_info.status} ✅")
print(f"   Total points: {collection_info.points_count:,}")
print(f"   Vector dimension: {collection_info.config.params.vectors.size if hasattr(collection_info.config.params, 'vectors') else 'N/A'}")

# Check timestamps to see if recent uploads happened
print(f"\n   Points count: {collection_info.points_count:,}")

# Scroll to get unique documents by title
print("\n📚 Scanning documents...")
points, _ = client.scroll(
    collection_name=collection_name,
    offset=0,
    limit=100,
    with_payload=True,
    with_vectors=False
)

titles_found = set()
preprocessing_tags = {}

for point in points:
    if point.payload:
        metadata = point.payload.get('metadata', {})
        title = metadata.get('title', 'Unknown')
        preprocessing = metadata.get('preprocessing', 'none')
        titles_found.add(title)
        preprocessing_tags[title] = preprocessing

print(f"\n✅ Found {len(titles_found)} unique documents in sample of 100 chunks:")
for title in sorted(titles_found):
    preprocessing = preprocessing_tags.get(title, 'none')
    mark = "✨" if preprocessing == "sanskrit" else "  "
    print(f"   {mark} {title[:70]}")

print("\n" + "=" * 90)
