#!/usr/bin/env python3
"""
Improved Qdrant upload with retry logic and batch recovery.

Handles timeouts and network issues gracefully.
"""

import argparse
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

# Load environment variables
load_dotenv()

# Configuration from .env
QDRANT_URL = os.getenv('QDRANT_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
LOCAL_VECTORDB = os.getenv('VECTORDB_FOLDER', 'vector_store')
COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'ancient_history')

# Batch configuration
BATCH_SIZE = 500  # Reduced from 1000 to avoid timeout
RETRY_COUNT = 3
RETRY_DELAY = 5  # seconds


def get_local_client(vectordb_path=None):
    """Connect to local Qdrant instance."""
    if vectordb_path is None:
        vectordb_path = LOCAL_VECTORDB
    
    if not Path(vectordb_path).exists():
        print(f"❌ Local vector database not found: {vectordb_path}")
        sys.exit(1)
    
    print(f"📍 Connecting to local Qdrant: {vectordb_path}")
    return QdrantClient(path=vectordb_path)


def get_cloud_client(url=None, api_key=None):
    """Connect to Qdrant Cloud."""
    if url is None:
        url = QDRANT_URL
    if api_key is None:
        api_key = QDRANT_API_KEY
    
    if not url or not api_key:
        print("❌ QDRANT_URL and QDRANT_API_KEY must be set in .env")
        sys.exit(1)
    
    print(f"☁️  Connecting to Qdrant Cloud: {url}")
    return QdrantClient(url=url, api_key=api_key)


def upload_to_cloud(local_client: QdrantClient, cloud_client: QdrantClient, 
                   collection_name: str, recreate: bool = False):
    """Upload points from local Qdrant to cloud with retry logic."""
    
    # Get local collection info
    print(f"\n📊 Checking local collection: {collection_name}")
    local_info = local_client.get_collection(collection_name)
    local_point_count = local_info.points_count or 0
    print(f"   Local points: {local_point_count}")
    
    # Get cloud collection info
    print(f"\n☁️  Checking cloud collection: {collection_name}")
    try:
        cloud_info = cloud_client.get_collection(collection_name)
        cloud_point_count = cloud_info.points_count or 0
        print(f"   Existing cloud points: {cloud_point_count}")
        
        if recreate:
            print(f"   🔄 Recreating collection (--recreate true)")
            cloud_client.delete_collection(collection_name)
            cloud_point_count = 0
        else:
            print(f"   ➕ Appending to collection (--recreate false)")
    except:
        print(f"   Collection does not exist, creating new one")
        cloud_point_count = 0
    
    # Scroll through local collection and upload in batches with retry
    print(f"\n📤 Uploading from local to cloud...")
    print("=" * 60)
    
    batch_size = BATCH_SIZE
    offset = None
    total_uploaded = 0
    batch_num = 0
    failed_batches = []
    cloud_point_count = 0  # Initialize here
    
    while True:
        # Fetch batch from local Qdrant
        try:
            all_points, next_offset = local_client.scroll(
                collection_name=collection_name,
                limit=batch_size,
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
            # Handle vector format - check if it's a dict or array
            if isinstance(point.vector, dict):
                vector_data = point.vector
            else:
                # Convert array to named vector if needed
                vector_data = {"embedding": point.vector} if isinstance(point.vector, list) else point.vector
            
            points_list.append({
                "id": point.id,
                "vector": vector_data,
                "payload": point.payload
            })
        
        # Upload batch to cloud with retry logic
        retry_attempts = 0
        uploaded = False
        
        while retry_attempts < RETRY_COUNT and not uploaded:
            try:
                cloud_client.upsert(
                    collection_name=collection_name,
                    points=points_list
                )
                
                total_uploaded += len(points_list)
                cloud_point_count += len(points_list)
                
                print(f"   ✅ Batch {batch_num}: Uploaded {len(points_list)} points "
                      f"(Total: {total_uploaded}/{local_point_count})")
                
                uploaded = True
                
            except Exception as e:
                retry_attempts += 1
                error_msg = str(e)
                
                if retry_attempts < RETRY_COUNT:
                    print(f"   ⚠️  Batch {batch_num}: Error (attempt {retry_attempts}/{RETRY_COUNT}): {error_msg}")
                    print(f"      Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"   ❌ Batch {batch_num}: Failed after {RETRY_COUNT} attempts")
                    print(f"      Error: {error_msg}")
                    failed_batches.append({
                        'batch': batch_num,
                        'offset': offset,
                        'points': len(points_list),
                        'error': error_msg
                    })
        
        if next_offset is None:
            break
        offset = next_offset
    
    print("=" * 60)
    print(f"\n📊 UPLOAD SUMMARY")
    print(f"   Total uploaded: {total_uploaded}/{local_point_count} points")
    print(f"   Failed batches: {len(failed_batches)}")
    
    if failed_batches:
        print(f"\n❌ Failed Batches Details:")
        for fb in failed_batches:
            print(f"   Batch {fb['batch']}: {fb['points']} points - {fb['error']}")
    
    # Final verification
    print(f"\n🔍 Verifying cloud collection...")
    try:
        cloud_collection = cloud_client.get_collection(collection_name)
        final_point_count = cloud_collection.points_count or 0
        print(f"   Cloud points (verified): {final_point_count}")
        
        if final_point_count >= local_point_count:
            print(f"   ✅ Upload successful! All {local_point_count} points transferred.")
            return True
        else:
            print(f"   ⚠️  Point count mismatch: Local={local_point_count}, Cloud={cloud_collection.points_count}")
            if failed_batches:
                print(f"      Note: {len(failed_batches)} batches failed. Consider retrying with --resume-from-batch flag.")
            return False
    except Exception as e:
        print(f"   ❌ Verification failed: {e}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Upload vectors from local Qdrant to Qdrant Cloud (with retry logic)'
    )
    parser.add_argument(
        '--collection',
        default=COLLECTION_NAME,
        help=f'Collection name (default: {COLLECTION_NAME})'
    )
    parser.add_argument(
        '--recreate',
        default='false',
        choices=['true', 'false'],
        help='Recreate collection (delete existing) or append (default: false)'
    )
    parser.add_argument(
        '--local-path',
        default=LOCAL_VECTORDB,
        help=f'Local Qdrant path (default: {LOCAL_VECTORDB})'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=BATCH_SIZE,
        help=f'Batch size (default: {BATCH_SIZE})'
    )
    parser.add_argument(
        '--retry-count',
        type=int,
        default=RETRY_COUNT,
        help=f'Retry attempts per batch (default: {RETRY_COUNT})'
    )
    
    args = parser.parse_args()
    
    collection = args.collection
    recreate = args.recreate.lower() == 'true'
    local_path = args.local_path
    
    print("🚀 QDRANT UPLOAD UTILITY (WITH RETRY LOGIC)")
    print("=" * 60)
    print(f"Collection: {collection}")
    print(f"Recreate: {recreate}")
    print(f"Local path: {local_path}")
    print(f"Batch size: {args.batch_size}")
    print(f"Retry count: {args.retry_count}")
    print("=" * 60)
    
    # Initialize clients
    try:
        local_client = get_local_client(local_path)
        cloud_client = get_cloud_client()
    except Exception as e:
        print(f"❌ Connection error: {e}")
        sys.exit(1)
    
    # Upload
    try:
        success = upload_to_cloud(local_client, cloud_client, collection, recreate)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
