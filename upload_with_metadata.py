#!/usr/bin/env python3
"""
Enhanced Qdrant upload with metadata payloads preserved.

This script uploads vector embeddings AND their associated metadata/payloads
from the local Qdrant instance to Qdrant Cloud.
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

QDRANT_URL = os.getenv('QDRANT_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
LOCAL_VECTORDB = os.getenv('VECTORDB_FOLDER', 'vector_store')
COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'ancient_history')

BATCH_SIZE = 250  # Small batches to avoid timeouts
RETRY_COUNT = 5
RETRY_DELAY = 3


def upload_with_metadata():
    """Upload vectors with full metadata/payloads."""
    
    print("🚀 QDRANT UPLOAD WITH METADATA")
    print("=" * 70)
    
    from qdrant_client import QdrantClient
    
    # Connect to local and cloud
    print("\n1️⃣  Connecting to local Qdrant...")
    local_client = QdrantClient(path=LOCAL_VECTORDB)
    local_info = local_client.get_collection(COLLECTION_NAME)
    print(f"   ✅ Local collection: {local_info.points_count} points")
    
    print("\n2️⃣  Connecting to Qdrant Cloud...")
    cloud_client = QdrantClient(url=str(QDRANT_URL), api_key=str(QDRANT_API_KEY))
    cloud_info = cloud_client.get_collection(COLLECTION_NAME)
    print(f"   ✅ Cloud collection: {cloud_info.points_count} points")
    
    # Upload with metadata
    print(f"\n3️⃣  Uploading with metadata (batch size: {BATCH_SIZE})...")
    print("=" * 70)
    
    batch_num = 0
    total_uploaded = 0
    offset = None
    failed_batches = []
    
    while True:
        # Scroll through local points WITH payloads and vectors
        all_points, next_offset = local_client.scroll(
            collection_name=COLLECTION_NAME,
            limit=BATCH_SIZE,
            offset=offset,
            with_vectors=True,
            with_payload=True  # KEY: Include payloads!
        )
        
        if not all_points:
            break
        
        batch_num += 1
        
        # Prepare points with metadata for upload
        points_to_upload = []
        for point in all_points:
            # Ensure point has ID, vector, and payload
            points_to_upload.append({
                "id": point.id,
                "vector": point.vector if isinstance(point.vector, dict) else {"embedding": point.vector},
                "payload": point.payload or {}
            })
        
        # Try to upload with retries
        retry_attempts = 0
        uploaded = False
        
        while retry_attempts < RETRY_COUNT and not uploaded:
            try:
                cloud_client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=points_to_upload
                )
                
                total_uploaded += len(points_to_upload)
                
                print(f"   ✅ Batch {batch_num}: Uploaded {len(points_to_upload):,} points with metadata "
                      f"(Total: {total_uploaded:,}/{local_info.points_count})")
                
                uploaded = True
                
            except Exception as e:
                retry_attempts += 1
                error_msg = str(e)
                
                if retry_attempts < RETRY_COUNT:
                    print(f"   ⚠️  Batch {batch_num}: Error (attempt {retry_attempts}/{RETRY_COUNT}): {error_msg[:80]}")
                    print(f"      Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"   ❌ Batch {batch_num}: Failed after {RETRY_COUNT} attempts")
                    print(f"      Error: {error_msg[:100]}")
                    failed_batches.append(batch_num)
        
        if next_offset is None:
            break
        offset = next_offset
    
    print("=" * 70)
    print(f"\n✅ UPLOAD COMPLETE")
    print(f"   Total uploaded: {total_uploaded:,}/{local_info.points_count} points")
    print(f"   Failed batches: {len(failed_batches)}")
    
    if failed_batches:
        print(f"   Failed batch numbers: {failed_batches}")
    
    # Verify
    print(f"\n4️⃣  Verifying cloud collection...")
    cloud_info_new = cloud_client.get_collection(COLLECTION_NAME)
    print(f"   Total cloud points: {cloud_info_new.points_count:,}")
    
    # Sample a point to check metadata
    print(f"\n5️⃣  Checking metadata in uploaded points...")
    sample_points, _ = cloud_client.scroll(COLLECTION_NAME, limit=3, with_payload=True)
    
    metadata_count = 0
    for i, point in enumerate(sample_points, 1):
        payload = point.payload or {}
        has_text = 'text' in payload
        has_source = 'source' in payload
        metadata_count += 1 if (has_text or has_source) else 0
        
        print(f"   Point {i}: text={'✅' if has_text else '❌'}, source={payload.get('source', 'N/A')}")
    
    if metadata_count > 0:
        print(f"\n   ✅ Metadata successfully uploaded!")
    else:
        print(f"\n   ⚠️  Warning: Metadata not found in sample points")
        print(f"      This may indicate payloads are still missing")
    
    print("\n" + "=" * 70)
    return len(failed_batches) == 0


if __name__ == "__main__":
    try:
        success = upload_with_metadata()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
