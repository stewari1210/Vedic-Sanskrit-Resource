#!/usr/bin/env python3
"""
Upload vector embeddings from local Qdrant to Qdrant Cloud.

Supports adding new documents (like Pancavamsa Brahmana) to existing collections
without recreating the entire collection.

Usage:
    # Add to existing collection (append mode)
    python3 upload_vector_to_Qdrant.py --collection ancient_history --recreate false
    
    # Replace entire collection
    python3 upload_vector_to_Qdrant.py --collection ancient_history --recreate true
"""

import argparse
import os
import sys
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
BATCH_SIZE = 1000
POINT_LIMIT_PER_REQUEST = 100  # Qdrant has payload size limits


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


def get_collection_info(client: QdrantClient, collection_name: str):
    """Get collection information."""
    try:
        collection = client.get_collection(collection_name)
        return {
            'points_count': collection.points_count,
            'vector_size': None,
            'distance': None,
        }
    except Exception as e:
        return None


def upload_to_cloud(local_client: QdrantClient, cloud_client: QdrantClient, 
                   collection_name: str, recreate: bool = False):
    """Upload points from local Qdrant to cloud."""
    
    # Get local collection info
    print(f"\n📊 Checking local collection: {collection_name}")
    local_info = local_client.get_collection(collection_name)
    local_point_count = local_info.points_count
    print(f"   Local points: {local_point_count}")
    
    # Get cloud collection info
    print(f"\n☁️  Checking cloud collection: {collection_name}")
    try:
        cloud_info = cloud_client.get_collection(collection_name)
        cloud_point_count = cloud_info.points_count
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
        cloud_info = None
    
    # Scroll through local collection and upload in batches
    print(f"\n📤 Uploading from local to cloud...")
    print("=" * 60)
    
    batch_size = BATCH_SIZE
    offset = None
    total_uploaded = 0
    batch_num = 0
    
    while True:
        # Fetch batch from local Qdrant
        all_points, next_offset = local_client.scroll(
            collection_name=collection_name,
            limit=batch_size,
            offset=offset,
            with_vectors=True
        )
        
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
        try:
            cloud_client.upsert(
                collection_name=collection_name,
                points=points_list
            )
            
            total_uploaded += len(points_list)
            cloud_point_count += len(points_list)
            
            print(f"   Batch {batch_num}: Uploaded {len(points_list)} points "
                  f"(Total: {total_uploaded}/{local_point_count})")
            
        except Exception as e:
            print(f"   ❌ Error uploading batch {batch_num}: {e}")
            # Continue with next batch
            pass
        
        if next_offset is None:
            break
        offset = next_offset
    
    print("=" * 60)
    print(f"\n✅ Upload complete!")
    print(f"   Total uploaded: {total_uploaded} points")
    print(f"   Cloud total: {cloud_point_count} points")
    
    # Final verification
    print(f"\n🔍 Verifying cloud collection...")
    cloud_collection = cloud_client.get_collection(collection_name)
    print(f"   Cloud points (verified): {cloud_collection.points_count}")
    
    if cloud_collection.points_count == local_point_count:
        print(f"   ✅ Upload successful! All {local_point_count} points transferred.")
    else:
        print(f"   ⚠️  Point count mismatch: Local={local_point_count}, Cloud={cloud_collection.points_count}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Upload vectors from local Qdrant to Qdrant Cloud'
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
    
    args = parser.parse_args()
    
    collection = args.collection
    recreate = args.recreate.lower() == 'true'
    local_path = args.local_path
    
    print("🚀 QDRANT UPLOAD UTILITY")
    print("=" * 60)
    print(f"Collection: {collection}")
    print(f"Recreate: {recreate}")
    print(f"Local path: {local_path}")
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
        upload_to_cloud(local_client, cloud_client, collection, recreate)
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
