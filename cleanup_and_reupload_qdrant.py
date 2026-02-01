#!/usr/bin/env python3
"""
Delete empty-metadata chunks and re-upload with proper metadata.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env from correct location
load_dotenv(Path(__file__).parent / ".env")

QDRANT_URL = os.getenv('QDRANT_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')

def delete_and_reupload():
    """Delete old empty chunks and re-upload with metadata."""
    
    from qdrant_client import QdrantClient
    
    print("🔄 DELETE EMPTY CHUNKS AND RE-UPLOAD WITH METADATA")
    print("=" * 70)
    
    # Connect to cloud
    print("\n1️⃣  Connecting to Qdrant Cloud...")
    client = QdrantClient(url=str(QDRANT_URL), api_key=str(QDRANT_API_KEY))
    info = client.get_collection("ancient_history")
    print(f"   Current points: {info.points_count:,}")
    
    # Find points without metadata
    print("\n2️⃣  Scanning for empty-metadata chunks...")
    offset = None
    empty_ids = []
    checked = 0
    
    while True:
        points, next_offset = client.scroll("ancient_history", limit=500, offset=offset, with_payload=True)
        if not points:
            break
        
        for point in points:
            payload = point.payload or {}
            # If payload is empty or missing page_content, it's likely an empty chunk
            if not payload or ('page_content' not in payload and 'metadata' not in payload):
                empty_ids.append(point.id)
            checked += 1
        
        if next_offset is None:
            break
        offset = next_offset
    
    print(f"   Checked: {checked} points")
    print(f"   Found: {len(empty_ids)} empty-metadata chunks")
    
    # Delete in batches
    if empty_ids:
        print(f"\n3️⃣  Deleting {len(empty_ids)} empty chunks...")
        
        batch_size = 1000
        for i in range(0, len(empty_ids), batch_size):
            batch = empty_ids[i:i+batch_size]
            print(f"   Deleting batch {i//batch_size + 1}: {len(batch)} points...")
            
            from qdrant_client.models import PointIdsList
            client.delete(
                collection_name="ancient_history",
                points_selector=PointIdsList(points=batch)
            )
        
        info = client.get_collection("ancient_history")
        print(f"\n   ✅ After deletion: {info.points_count:,} points")
    
    # Now re-upload from local with metadata
    print(f"\n4️⃣  Re-uploading local vectors WITH metadata...")
    
    local_client = QdrantClient(path="vector_store")
    local_info = local_client.get_collection("ancient_history")
    print(f"   Local points to upload: {local_info.points_count:,}")
    
    # Upload in batches with metadata
    offset = None
    batch_num = 0
    total_uploaded = 0
    
    while True:
        all_points, next_offset = local_client.scroll(
            collection_name="ancient_history",
            limit=200,
            offset=offset,
            with_vectors=True,
            with_payload=True
        )
        
        if not all_points:
            break
        
        batch_num += 1
        
        # Prepare for upload
        points_to_upload = []
        for point in all_points:
            points_to_upload.append({
                "id": point.id,
                "vector": {"embedding": point.vector} if isinstance(point.vector, list) else point.vector,
                "payload": point.payload or {}
            })
        
        # Upload
        try:
            client.upsert(
                collection_name="ancient_history",
                points=points_to_upload
            )
            total_uploaded += len(points_to_upload)
            
            if batch_num % 10 == 0:
                print(f"   Batch {batch_num}: {total_uploaded:,}/{local_info.points_count:,} uploaded")
        
        except Exception as e:
            print(f"   ❌ Batch {batch_num} error: {e}")
        
        if next_offset is None:
            break
        offset = next_offset
    
    print(f"   ✅ Uploaded: {total_uploaded:,} points with metadata")
    
    # Verify
    print(f"\n5️⃣  Verifying...")
    info = client.get_collection("ancient_history")
    print(f"   Final cloud points: {info.points_count:,}")
    
    # Check a sample
    sample, _ = client.scroll("ancient_history", limit=3, with_payload=True)
    metadata_found = 0
    for point in sample:
        if point.payload and ('page_content' in point.payload or 'metadata' in point.payload):
            metadata_found += 1
    
    print(f"   Metadata in sample: {metadata_found}/3 points")
    
    print("\n" + "=" * 70)
    return metadata_found > 0


if __name__ == "__main__":
    try:
        success = delete_and_reupload()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Operation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
