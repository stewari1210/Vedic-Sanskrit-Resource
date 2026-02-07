#!/usr/bin/env python3
"""
Get full metadata from Qdrant
"""
import os
import json
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

collection_name = os.getenv("COLLECTION_NAME", "ancient_history")

# Get one point to see full structure
points, _ = client.scroll(
    collection_name=collection_name,
    offset=0,
    limit=1,
    with_payload=True,
    with_vectors=False
)

point = points[0]
print("\n" + "=" * 90)
print("📌 SAMPLE POINT STRUCTURE")
print("=" * 90)
print(f"\nPoint ID: {point.id}")
if point.payload:
    print(f"\nPayload keys: {list(point.payload.keys())}")
    print(f"\nFull metadata dict:")
    print(json.dumps(point.payload.get('metadata', {}), indent=2, ensure_ascii=False)[:1000])
else:
    print("\n⚠️ No payload found!")

# Now scan through and find unique documents
print("\n" + "=" * 90)
print("📚 SCANNING ALL DOCUMENTS")
print("=" * 90)

unique_docs = {}
offset = 0
batch_size = 1000
total_points = 0

while True:
    points, next_offset = client.scroll(
        collection_name=collection_name,
        offset=offset,
        limit=batch_size,
        with_payload=True,
        with_vectors=False
    )
    
    if not points:
        break
    
    for point in points:
        total_points += 1
        if not point.payload:
            continue
        metadata = point.payload.get('metadata', {})
        title = metadata.get('title', 'Unknown')
        source = metadata.get('source', 'unknown')
        preprocessing = metadata.get('preprocessing', 'none')
        
        doc_key = (title, source)
        if doc_key not in unique_docs:
            unique_docs[doc_key] = {
                'count': 0,
                'preprocessing': preprocessing,
                'metadata': metadata
            }
        unique_docs[doc_key]['count'] += 1
    
    offset = next_offset
    if offset is None or not points:
        break

print(f"\n✅ Scanned {total_points:,} total chunks")
print(f"\n📖 Unique documents found: {len(unique_docs)}")
print("\n" + "-" * 90)

for idx, ((title, source), doc_info) in enumerate(sorted(unique_docs.items(), key=lambda x: x[1]['count'], reverse=True), 1):
    count = doc_info['count']
    pct = (count / total_points * 100) if total_points > 0 else 0
    preprocessing = doc_info['preprocessing']
    
    print(f"\n{idx}. {title}")
    print(f"   Source: {source}")
    print(f"   Chunks: {count:,} ({pct:.1f}%)")
    print(f"   Preprocessing: {preprocessing}")
    
    # Show some metadata fields
    meta = doc_info['metadata']
    if 'author' in meta:
        print(f"   Author: {meta['author']}")
    if 'language' in meta:
        print(f"   Language: {meta['language']}")

print("\n" + "=" * 90)
