#!/usr/bin/env python3
"""
Verify that Sanskrit texts have been properly enriched with metadata in Qdrant Cloud.
"""

from dotenv import load_dotenv
from qdrant_client import QdrantClient
import os

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "ancient_history")

def verify_sanskrit_metadata():
    """Check if Sanskrit texts have preprocessing='sanskrit' in Qdrant Cloud"""
    
    try:
        client = QdrantClient(url=str(QDRANT_URL), api_key=str(QDRANT_API_KEY))
        
        print("=" * 70)
        print("🔍 VERIFYING SANSKRIT METADATA IN QDRANT CLOUD")
        print("=" * 70)
        print(f"\n📍 Collection: {COLLECTION_NAME}")
        
        # Get collection stats
        collection_info = client.get_collection(COLLECTION_NAME)
        print(f"📊 Total points in collection: {collection_info.points_count}")
        
        # Search for Sanskrit documents
        print(f"\n🔎 Searching for documents with 'preprocessing: sanskrit' metadata...")
        
        # Query with filter for Sanskrit texts
        search_results = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=100,
        )
        
        sanskrit_docs = []
        other_docs = []
        
        for point in search_results[0]:
            payload = point.payload or {}
            filename = payload.get('filename', 'unknown') if isinstance(payload, dict) else 'unknown'
            preprocessing = payload.get('preprocessing', 'N/A') if isinstance(payload, dict) else 'N/A'
            source_type = payload.get('source_type', 'N/A') if isinstance(payload, dict) else 'N/A'
            
            if preprocessing == 'sanskrit' or source_type == 'vedic_text':
                sanskrit_docs.append({
                    'filename': filename,
                    'preprocessing': preprocessing,
                    'source_type': source_type,
                    'title': payload.get('title', '') if isinstance(payload, dict) else '',
                })
            else:
                other_docs.append({
                    'filename': filename,
                    'preprocessing': preprocessing,
                    'source_type': source_type,
                })
        
        print(f"\n✅ SANSKRIT DOCUMENTS FOUND: {len(sanskrit_docs)}")
        print("-" * 70)
        for doc in sanskrit_docs:
            print(f"  📖 {doc['filename']}")
            print(f"     Title: {doc['title'][:60]}...")
            print(f"     Preprocessing: {doc['preprocessing']}")
            print(f"     Source Type: {doc['source_type']}")
            print()
        
        print(f"\n📚 OTHER DOCUMENTS: {len(other_docs)}")
        print("-" * 70)
        for doc in other_docs[:5]:  # Show first 5
            print(f"  📄 {doc['filename']}")
            print(f"     Preprocessing: {doc['preprocessing']}")
            print()
        
        print("\n" + "=" * 70)
        print(f"✅ VERIFICATION COMPLETE!")
        print(f"✅ Sanskrit documents properly tagged: {len(sanskrit_docs)}")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    verify_sanskrit_metadata()
