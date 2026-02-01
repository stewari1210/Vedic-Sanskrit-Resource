#!/usr/bin/env python3
"""
Add metadata to existing Pancavamsa chunks in Qdrant Cloud.
This reads the local metadata file and updates the cloud chunks without re-indexing.
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

QDRANT_URL = os.getenv('QDRANT_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'ancient_history')

# Path to Pancavamsa metadata
PB_METADATA_FILE = "local_store/prose_vedas/pancavamsa_brahmana/pancavamsa_brahmana_metadata.json"

print("🔧 ADDING METADATA TO PANCAVAMSA CHUNKS")
print("=" * 70)

# Load the metadata
print(f"\n1️⃣  Loading Pancavamsa metadata from {PB_METADATA_FILE}...")
with open(PB_METADATA_FILE, 'r', encoding='utf-8') as f:
    pb_metadata = json.load(f)

print(f"   Title: {pb_metadata.get('title', 'N/A')}")
print(f"   Translator: {pb_metadata.get('translator', 'N/A')}")
print(f"   Year: {pb_metadata.get('publication_date', 'N/A')}")

# Connect to cloud
print(f"\n2️⃣  Connecting to Qdrant Cloud...")
client = QdrantClient(url=str(QDRANT_URL), api_key=str(QDRANT_API_KEY))
info = client.get_collection(COLLECTION_NAME)
print(f"   Collection: {COLLECTION_NAME}")
print(f"   Total points: {info.points_count}")

# Find chunks with empty metadata (likely Pancavamsa)
print(f"\n3️⃣  Finding chunks without metadata...")
offset = None
empty_metadata_ids = []
checked = 0

while True:
    points, next_offset = client.scroll(COLLECTION_NAME, limit=500, offset=offset, with_payload=True)
    if not points:
        break
    
    for point in points:
        payload = point.payload or {}
        metadata = payload.get('metadata', {})
        
        # If metadata is empty or has no title, it's likely a Pancavamsa chunk
        if not metadata or (isinstance(metadata, dict) and not metadata.get('title')):
            empty_metadata_ids.append(point.id)
        
        checked += 1
    
    if next_offset is None:
        break
    offset = next_offset

print(f"   Checked: {checked} points")
print(f"   Found: {len(empty_metadata_ids)} chunks without metadata")

if not empty_metadata_ids:
    print("\n   ⚠️  No empty-metadata chunks found. All chunks already have metadata!")
    exit(0)

# Update these chunks with Pancavamsa metadata
print(f"\n4️⃣  Updating {len(empty_metadata_ids)} chunks with Pancavamsa metadata...")

# We need to read the chunks, add metadata, and update
batch_size = 100
updated_count = 0

for i in range(0, len(empty_metadata_ids), batch_size):
    batch_ids = empty_metadata_ids[i:i+batch_size]
    
    # Fetch these points
    points = client.retrieve(
        collection_name=COLLECTION_NAME,
        ids=batch_ids,
        with_payload=True,
        with_vectors=True
    )
    
    # Update payloads with metadata
    updated_points = []
    for point in points:
        payload = point.payload or {}
        
        # Add metadata to payload
        payload['metadata'] = pb_metadata
        
        updated_points.append({
            "id": point.id,
            "vector": {"embedding": point.vector} if isinstance(point.vector, list) else point.vector,
            "payload": payload
        })
    
    # Upsert back
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=updated_points
    )
    
    updated_count += len(updated_points)
    
    if (i // batch_size + 1) % 10 == 0:
        print(f"   Progress: {updated_count}/{len(empty_metadata_ids)} chunks updated")

print(f"   ✅ Updated {updated_count} chunks")

# Verify
print(f"\n5️⃣  Verifying update...")
sample_points = client.retrieve(
    collection_name=COLLECTION_NAME,
    ids=empty_metadata_ids[:3],
    with_payload=True
)

for i, point in enumerate(sample_points, 1):
    payload = point.payload or {}
    metadata = payload.get('metadata', {})
    title = metadata.get('title', 'N/A') if isinstance(metadata, dict) else 'N/A'
    print(f"   Sample {i}: Title = '{title}'")

print("\n" + "=" * 70)
print("✅ Metadata update complete!")
print(f"   {updated_count} Pancavamsa chunks now have proper metadata")
