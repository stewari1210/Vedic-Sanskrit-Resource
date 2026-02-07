#!/usr/bin/env python3
"""
Retrieve and display all documents from Qdrant Cloud vector store.
Shows document details, metadata, and statistics.
"""

from dotenv import load_dotenv
from qdrant_client import QdrantClient
import os
import json
from collections import defaultdict

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "ancient_history")

def retrieve_qdrant_documents():
    """Retrieve and display all documents from Qdrant Cloud"""
    
    try:
        client = QdrantClient(url=str(QDRANT_URL), api_key=str(QDRANT_API_KEY))
        
        print("=" * 90)
        print("📚 QDRANT CLOUD DOCUMENT RETRIEVAL")
        print("=" * 90)
        print(f"\n📍 Collection: {COLLECTION_NAME}")
        print(f"🔗 URL: {QDRANT_URL}")
        
        # Get collection stats
        collection_info = client.get_collection(COLLECTION_NAME)
        print(f"\n📊 COLLECTION STATISTICS")
        print("-" * 90)
        print(f"  Total Points (Chunks): {collection_info.points_count:,}")
        # Extract vector dimension safely
        try:
            vectors_config = collection_info.config.params.vectors
            if isinstance(vectors_config, dict):
                # Get the first vector config if it's a dict
                first_vector = next(iter(vectors_config.values())) if vectors_config else None
                vector_size = first_vector.size if first_vector and hasattr(first_vector, 'size') else 768
            else:
                vector_size = vectors_config.size if hasattr(vectors_config, 'size') else 768
            print(f"  Vector Dimension: {vector_size}")
        except:
            print(f"  Vector Dimension: 768 (default)")
        print(f"  Collection Status: {collection_info.status}")
        
        # Retrieve all points with pagination
        print(f"\n📖 RETRIEVING DOCUMENTS...")
        all_points = []
        offset = 0
        batch_size = 1000
        
        while True:
            print(f"  Fetching batch (offset: {offset}, size: {batch_size})...", end=" ", flush=True)
            try:
                points, next_offset = client.scroll(
                    collection_name=COLLECTION_NAME,
                    offset=offset,
                    limit=batch_size,
                    with_payload=True,
                    with_vectors=False  # Don't retrieve vectors, just payloads
                )
                
                all_points.extend(points)
                print(f"✓ Got {len(points)} points")
                
                if next_offset is None or len(points) < batch_size:
                    break
                offset = next_offset
            except Exception as e:
                print(f"✗ Error: {e}")
                break
        
        print(f"\n✅ Retrieved {len(all_points)} total chunks/points")
        
        # Extract unique documents
        documents = {}
        doc_stats = {}
        
        for point in all_points:
            payload = point.payload or {}
            
            if isinstance(payload, dict):
                filename = payload.get("filename", "unknown")
                
                if filename not in documents:
                    documents[filename] = {
                        "title": payload.get("title", "N/A"),
                        "author": payload.get("author", []),
                        "source": payload.get("source", "N/A"),
                        "pages": payload.get("pages", 0),
                        "preprocessing": payload.get("preprocessing", "none"),
                        "source_type": payload.get("source_type", "N/A"),
                        "year": payload.get("year", ""),
                        "subject": payload.get("subject", ""),
                        "keywords": payload.get("keywords", []),
                    }
                
                if filename not in doc_stats:
                    doc_stats[filename] = {"count": 0, "metadata": documents[filename]}
                doc_stats[filename]["count"] += 1
        
        # Display documents
        print("\n" + "=" * 90)
        print("📚 DOCUMENTS IN QDRANT CLOUD")
        print("=" * 90)
        
        sorted_docs = sorted(doc_stats.items(), key=lambda x: x[1]["count"] if isinstance(x[1], dict) else 0, reverse=True)
        
        for idx, (filename, stats) in enumerate(sorted_docs, 1):
            if not isinstance(stats, dict):
                continue
            metadata = stats.get("metadata", {})
            chunk_count = stats.get("count", 0)
            
            print(f"\n{idx}. {filename}")
            print("-" * 90)
            print(f"   📖 Title: {metadata['title']}")
            
            if metadata['author']:
                authors = metadata['author'] if isinstance(metadata['author'], list) else [metadata['author']]
                authors = [a for a in authors if a]  # Filter empty strings
                if authors:
                    print(f"   👤 Author(s): {', '.join(authors[:3])}")
            
            if metadata['source']:
                print(f"   📄 Source: {metadata['source']}")
            
            print(f"   📊 Chunks: {chunk_count:,}")
            print(f"   📄 Pages: {metadata['pages']}")
            
            if metadata['preprocessing'] != "none":
                print(f"   🔧 Preprocessing: {metadata['preprocessing']} ✨")
            
            if metadata['source_type'] != "N/A":
                print(f"   🏷️  Source Type: {metadata['source_type']}")
            
            if metadata['year']:
                print(f"   📅 Year: {metadata['year']}")
            
            if metadata['subject']:
                print(f"   📌 Subject: {metadata['subject'][:80]}")
        
        # Summary statistics
        print("\n" + "=" * 90)
        print("📊 SUMMARY STATISTICS")
        print("=" * 90)
        
        total_chunks = sum(int(stats.get("count", 0)) for stats in doc_stats.values() if isinstance(stats, dict))
        total_docs = len(documents)
        sanskrit_docs = sum(1 for meta in documents.values() if meta.get("preprocessing") == "sanskrit")
        
        print(f"\nTotal Documents: {total_docs}")
        print(f"Total Chunks: {total_chunks:,}")
        print(f"Sanskrit Documents: {sanskrit_docs} ✨")
        
        # Document type breakdown
        doc_types = defaultdict(int)
        for meta in documents.values():
            doc_type = meta.get("source_type", "unknown")
            doc_types[doc_type] += 1
        
        print(f"\nDocument Types:")
        for doc_type, count in sorted(doc_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {doc_type}: {count}")
        
        # Preprocessing breakdown
        preprocessing_types = defaultdict(int)
        for meta in documents.values():
            prep = meta.get("preprocessing", "none")
            preprocessing_types[prep] += 1
        
        print(f"\nPreprocessing Types:")
        for prep, count in sorted(preprocessing_types.items(), key=lambda x: x[1], reverse=True):
            if prep == "none":
                print(f"  • No preprocessing: {count}")
            else:
                print(f"  • {prep}: {count} ✨")
        
        # Average chunks per document
        avg_chunks = total_chunks / total_docs if total_docs > 0 else 0
        print(f"\nAverage Chunks per Document: {avg_chunks:.0f}")
        
        print("\n" + "=" * 90)
        print("✅ RETRIEVAL COMPLETE")
        print("=" * 90)
        
        return documents, doc_stats
        
    except Exception as e:
        print(f"\n❌ Error retrieving documents: {e}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == "__main__":
    retrieve_qdrant_documents()
