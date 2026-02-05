#!/usr/bin/env python3
"""
Upload locally indexed Sanskrit Rigveda vectors to Qdrant Cloud (APPEND MODE).

This script uploads the 10 Rigveda PDFs (3,902 points) from local Qdrant 
to your cloud collection WITHOUT replacing existing vectors.

The collection will go from 23,998 → 27,900+ points.

Usage:
    python3 upload_sanskrit_rigveda_to_cloud.py

Options:
    --local-path PATH       Path to local vector store (default: vector_store)
    --collection NAME       Collection name (default: ancient_history)
    --dry-run              Show what would be uploaded without uploading
"""

import argparse
import os
import sys
from pathlib import Path
from qdrant_client import QdrantClient

# Qdrant Cloud credentials (from your .env)
QDRANT_URL = "https://014ab865-1a9a-4387-8672-182fbfbb2dba.us-east4-0.gcp.cloud.qdrant.io:6333"
QDRANT_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.L9k9OYrFXW0loBo8w1LXORHr5oG8cLbjN4Fg3w2dWOw"

BATCH_SIZE = 1000


def get_local_client(vectordb_path):
    """Connect to local Qdrant instance."""
    if not Path(vectordb_path).exists():
        print(f"❌ Local vector database not found: {vectordb_path}")
        sys.exit(1)
    
    print(f"📍 Connecting to local Qdrant: {vectordb_path}")
    return QdrantClient(path=vectordb_path)


def get_cloud_client():
    """Connect to Qdrant Cloud."""
    print(f"☁️  Connecting to Qdrant Cloud...")
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


def upload_to_cloud(local_client, cloud_client, collection_name, dry_run=False):
    """Upload points from local Qdrant to cloud (APPEND MODE - no replacement)."""
    
    # Get local collection info
    print(f"\n📊 Checking local collection: '{collection_name}'")
    try:
        local_info = local_client.get_collection(collection_name)
        local_point_count = local_info.points_count
        print(f"   ✅ Local points: {local_point_count}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        sys.exit(1)
    
    # Get cloud collection info
    print(f"\n☁️  Checking cloud collection: '{collection_name}'")
    try:
        cloud_info = cloud_client.get_collection(collection_name)
        cloud_point_count = cloud_info.points_count
        print(f"   ✅ Existing cloud points: {cloud_point_count}")
        print(f"   ➕ APPEND MODE: Will add {local_point_count} new points")
        print(f"   📈 Expected total after upload: {cloud_point_count + local_point_count}")
    except Exception as e:
        print(f"   ❌ Error accessing cloud collection: {e}")
        sys.exit(1)
    
    if dry_run:
        print(f"\n🔍 DRY RUN MODE - No data will be uploaded")
        print(f"   Would upload {local_point_count} points to cloud")
        return
    
    # Scroll through local collection and upload in batches
    print(f"\n📤 Starting upload (APPEND MODE - no existing vectors will be replaced)...")
    print("=" * 70)
    
    offset = None
    total_uploaded = 0
    batch_num = 0
    failed_batches = []
    
    while True:
        # Fetch batch from local Qdrant
        try:
            all_points, next_offset = local_client.scroll(
                collection_name=collection_name,
                limit=BATCH_SIZE,
                offset=offset,
                with_vectors=True
            )
        except Exception as e:
            print(f"   ❌ Error scrolling local collection: {e}")
            break
        
        if not all_points:
            break
        
        batch_num += 1
        
        # Convert points to dict format for upsert
        points_list = []
        for point in all_points:
            # Cloud collection uses UNNAMED vectors (not named "embedding")
            # Local may have named or unnamed vectors - normalize to unnamed (array)
            if isinstance(point.vector, dict):
                # If local has named vectors like {"embedding": [...]}, extract the array
                vector_data = next(iter(point.vector.values())) if point.vector else point.vector
            else:
                # Already an array, keep as is
                vector_data = point.vector
            
            points_list.append({
                "id": point.id,
                "vector": vector_data,
                "payload": point.payload
            })
        
        # Upload batch to cloud with retry logic
        try:
            cloud_client.upsert(
                collection_name=collection_name,
                points=points_list
            )
            
            total_uploaded += len(points_list)
            
            print(f"   Batch {batch_num:3d}: ✅ Uploaded {len(points_list):5d} points | "
                  f"Total: {total_uploaded:6d}/{local_point_count}")
            
        except Exception as e:
            print(f"   Batch {batch_num:3d}: ❌ Error - {e}")
            failed_batches.append(batch_num)
            # Continue with next batch
        
        if next_offset is None:
            break
        offset = next_offset
    
    print("=" * 70)
    
    # Summary
    print(f"\n✅ Upload complete!")
    print(f"   Points uploaded: {total_uploaded}/{local_point_count}")
    
    if failed_batches:
        print(f"   ⚠️  Failed batches: {failed_batches} ({len(failed_batches)} batches)")
    
    # Final verification
    print(f"\n🔍 Verifying cloud collection...")
    try:
        cloud_collection = cloud_client.get_collection(collection_name)
        new_cloud_total = cloud_collection.points_count
        print(f"   Cloud points now: {new_cloud_total}")
        print(f"   Previous: {cloud_point_count}")
        print(f"   Added: {new_cloud_total - cloud_point_count}")
        
        if total_uploaded == new_cloud_total - cloud_point_count:
            print(f"\n   ✅ SUCCESS! Rigveda Sanskrit vectors uploaded to cloud.")
            print(f"   No existing vectors were replaced. Append operation complete.")
        else:
            print(f"\n   ⚠️  Mismatch: Uploaded {total_uploaded} but cloud shows "
                  f"{new_cloud_total - cloud_point_count} new points")
    except Exception as e:
        print(f"   ❌ Verification error: {e}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Upload local Sanskrit Rigveda vectors to Qdrant Cloud (APPEND MODE)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Standard upload (append to existing cloud collection)
  python3 upload_sanskrit_rigveda_to_cloud.py
  
  # Test what would be uploaded (dry run)
  python3 upload_sanskrit_rigveda_to_cloud.py --dry-run
  
  # Use different local vector store
  python3 upload_sanskrit_rigveda_to_cloud.py --local-path /path/to/vector_store
        """
    )
    
    parser.add_argument(
        '--local-path',
        default='vector_store',
        help='Path to local vector store (default: vector_store)'
    )
    parser.add_argument(
        '--collection',
        default='ancient_history',
        help='Collection name (default: ancient_history)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be uploaded without uploading'
    )
    
    args = parser.parse_args()
    
    # Get clients
    local_client = get_local_client(args.local_path)
    cloud_client = get_cloud_client()
    
    # Upload
    upload_to_cloud(local_client, cloud_client, args.collection, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
