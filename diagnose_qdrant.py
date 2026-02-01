#!/usr/bin/env python3
"""
Diagnostic script to verify Qdrant connection and collection contents.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

from src.config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME
from src.helper import logger

def diagnose_qdrant_connection():
    """Diagnose Qdrant connection and verify collection contents."""
    
    print("\n" + "=" * 70)
    print("🔍 QDRANT CONNECTION DIAGNOSTICS")
    print("=" * 70)
    
    # 1. Check configuration
    print("\n1️⃣  Configuration Check:")
    print(f"   QDRANT_URL: {QDRANT_URL}")
    print(f"   QDRANT_API_KEY: {'✅ SET' if QDRANT_API_KEY else '❌ NOT SET'}")
    print(f"   COLLECTION_NAME: {COLLECTION_NAME}")
    
    if not QDRANT_URL or not QDRANT_API_KEY:
        print("   ❌ Qdrant Cloud not configured! Using local store instead.")
        return False
    
    # 2. Connect to Qdrant
    print("\n2️⃣  Connecting to Qdrant Cloud...")
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(url=str(QDRANT_URL), api_key=str(QDRANT_API_KEY))
        print(f"   ✅ Connected successfully")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False
    
    # 3. Check collection exists
    print(f"\n3️⃣  Checking collection '{COLLECTION_NAME}'...")
    try:
        collection_info = client.get_collection(str(COLLECTION_NAME))
        print(f"   ✅ Collection exists")
        print(f"      - Total points: {collection_info.points_count}")
    except Exception as e:
        print(f"   ❌ Collection not found: {e}")
        return False
    
    # 4. Sample points from collection
    print(f"\n4️⃣  Sampling points from collection...")
    try:
        points, _ = client.scroll(str(COLLECTION_NAME), limit=5)
        print(f"   ✅ Retrieved {len(points)} sample points")
        
        for i, point in enumerate(points[:3], 1):
            payload = point.payload or {}
            text_preview = payload.get('text', '')[:100] if payload.get('text') else 'N/A'
            source = payload.get('source', 'unknown')
            print(f"      Point {i}: source='{source}', text_preview='{text_preview}...'")
    except Exception as e:
        print(f"   ❌ Error sampling points: {e}")
    
    # 5. Search for Pancavamsa content
    print(f"\n5️⃣  Searching for Pancavamsa content...")
    try:
        # First, let's check if we can access documents with embeddings
        from langchain_qdrant import QdrantVectorStore
        from src.settings import Settings
        
        vector_store = QdrantVectorStore(
            client=client,
            collection_name=str(COLLECTION_NAME),
            embedding=Settings.get_embed_model(),  # type: ignore
        )
        
        # Search for Pancavamsa-related content
        results = vector_store.similarity_search("Pancavamsa Brahmana fire ritual", k=5)
        
        if results:
            print(f"   ✅ Found {len(results)} matching documents")
            for i, doc in enumerate(results, 1):
                metadata = doc.metadata or {}
                source = metadata.get('source', 'unknown')
                text_preview = doc.page_content[:80] if doc.page_content else 'N/A'
                print(f"      Result {i}: source='{source}'")
                print(f"                 text='{text_preview}...'")
        else:
            print(f"   ⚠️  No Pancavamsa results found for query")
            
            # Try a simpler search
            print(f"      Trying broader search...")
            results = vector_store.similarity_search("fire ritual ceremony", k=3)
            if results:
                print(f"      Found {len(results)} results for 'fire ritual ceremony':")
                for result in results:
                    source = result.metadata.get('source', 'unknown') if result.metadata else 'unknown'
                    print(f"        - {source}: {result.page_content[:60]}...")
    
    except Exception as e:
        print(f"   ❌ Error searching collection: {e}")
        import traceback
        traceback.print_exc()
    
    # 6. Count points by source
    print(f"\n6️⃣  Analyzing collection composition...")
    try:
        # Scroll through all points and count by source
        source_counts = {}
        offset = None
        total_processed = 0
        
        while True:
            points, next_offset = client.scroll(str(COLLECTION_NAME), limit=1000, offset=offset)
            if not points:
                break
            
            for point in points:
                payload = point.payload or {}
                source = payload.get('source', 'unknown')
                source_counts[source] = source_counts.get(source, 0) + 1
                total_processed += 1
            
            if next_offset is None:
                break
            offset = next_offset
        
        print(f"   ✅ Analyzed {total_processed} points")
        print(f"      Sources breakdown:")
        for source in sorted(source_counts.keys()):
            count = source_counts[source]
            percentage = 100 * count / total_processed
            print(f"        - {source}: {count:,} points ({percentage:.1f}%)")
        
        # Check for PB (Pancavamsa) content
        pb_count = sum(count for source, count in source_counts.items() if 'pancavamsa' in source.lower() or 'pb' in source.lower())
        if pb_count > 0:
            print(f"      ✅ Found {pb_count:,} Pancavamsa points!")
        else:
            print(f"      ⚠️  No Pancavamsa sources detected in metadata")
    
    except Exception as e:
        print(f"   ❌ Error analyzing collection: {e}")
    
    print("\n" + "=" * 70)
    return True


if __name__ == "__main__":
    try:
        success = diagnose_qdrant_connection()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
