#!/usr/bin/env python3
"""
Re-index Rigveda and Yajurveda to Qdrant Cloud.

This script loads the Rigveda and Yajurveda metadata files (which we just updated)
and pushes them to Qdrant Cloud, replacing the existing collection with a complete index.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.helper import logger
from src.config import LOCAL_FOLDER, COLLECTION_NAME, QDRANT_URL, QDRANT_API_KEY
from src.settings import Settings
from src.utils.index_files import load_documents_with_metadata, chunk_doc
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance
from langchain_qdrant import QdrantVectorStore

def main():
    """Main re-indexing function."""
    
    if not QDRANT_URL or not QDRANT_API_KEY:
        logger.error("QDRANT_URL and QDRANT_API_KEY must be set")
        return False
    
    logger.info(f"Starting re-indexing to Qdrant Cloud")
    logger.info(f"QDRANT_URL: {QDRANT_URL}")
    logger.info(f"COLLECTION_NAME: {COLLECTION_NAME}")
    
    # Step 1: Load documents from local_store
    logger.info("Step 1: Loading documents from local_store...")
    documents = load_documents_with_metadata(str(LOCAL_FOLDER))
    logger.info(f"Loaded {len(documents)} documents")
    
    if not documents:
        logger.error("No documents loaded!")
        return False
    
    # Verify Rigveda and Yajurveda are loaded
    titles = set()
    for doc in documents:
        title = doc.metadata.get('title', '')
        if title:
            titles.add(title)
    
    logger.info(f"Document titles found: {titles}")
    
    has_rigveda = any('Rigveda' in t for t in titles)
    has_yajurveda = any('Yajurveda' in t for t in titles)
    
    if not has_rigveda:
        logger.warning("⚠️  Rigveda not found in loaded documents!")
    else:
        logger.info("✅ Rigveda found")
    
    if not has_yajurveda:
        logger.warning("⚠️  Yajurveda not found in loaded documents!")
    else:
        logger.info("✅ Yajurveda found")
    
    # Step 2: Chunk documents
    logger.info("Step 2: Chunking documents...")
    chunks = chunk_doc(documents)
    logger.info(f"Created {len(chunks)} chunks")
    
    # Step 3: Connect to Qdrant Cloud
    logger.info("Step 3: Connecting to Qdrant Cloud...")
    client = QdrantClient(url=str(QDRANT_URL), api_key=str(QDRANT_API_KEY))
    
    # Step 4: Delete existing collection (to force complete re-index)
    logger.info(f"Step 4: Deleting existing collection '{COLLECTION_NAME}' if it exists...")
    try:
        client.delete_collection(collection_name=str(COLLECTION_NAME))
        logger.info(f"✅ Deleted collection '{COLLECTION_NAME}'")
    except Exception as e:
        logger.warning(f"Collection may not exist or deletion failed: {e}")
    
    # Step 5: Get embedding model and determine vector size
    logger.info("Step 5: Getting embedding model and vector size...")
    embed_model = Settings.get_embed_model()
    
    # Embed first chunk to get dimension
    sample_vec = embed_model.embed_documents([chunks[0].page_content])[0]
    dim = len(sample_vec)
    logger.info(f"Vector dimension: {dim}")
    
    # Step 6: Create new collection
    logger.info(f"Step 6: Creating new collection with {dim}-dimensional vectors...")
    vectors_config = VectorParams(size=dim, distance=Distance.COSINE)
    try:
        client.create_collection(
            collection_name=str(COLLECTION_NAME),
            vectors_config=vectors_config
        )
        logger.info(f"✅ Created collection '{COLLECTION_NAME}'")
    except Exception as e:
        logger.error(f"Failed to create collection: {e}")
        return False
    
    # Step 7: Add documents to Qdrant
    logger.info(f"Step 7: Adding {len(chunks)} chunks to Qdrant Cloud...")
    try:
        qdrant_store = QdrantVectorStore(
            client=client,
            collection_name=str(COLLECTION_NAME),
            embedding=embed_model
        )
        qdrant_store.add_documents(chunks)
        logger.info(f"✅ Successfully added all {len(chunks)} chunks to Qdrant Cloud")
    except Exception as e:
        logger.error(f"Failed to add documents: {e}")
        # Try to clean up
        try:
            client.delete_collection(collection_name=str(COLLECTION_NAME))
        except:
            pass
        return False
    
    # Step 8: Verify the collection
    logger.info("Step 8: Verifying collection...")
    try:
        collection_info = client.get_collection(collection_name=str(COLLECTION_NAME))
        logger.info(f"✅ Collection verified. Points: {collection_info.points_count}")
        
        # Count by title
        rigveda_count = sum(1 for c in chunks if 'Rigveda' in c.metadata.get('title', ''))
        yajurveda_count = sum(1 for c in chunks if 'Yajurveda' in c.metadata.get('title', ''))
        other_count = len(chunks) - rigveda_count - yajurveda_count
        
        logger.info(f"  • Rigveda chunks: {rigveda_count}")
        logger.info(f"  • Yajurveda chunks: {yajurveda_count}")
        logger.info(f"  • Other chunks: {other_count}")
        
    except Exception as e:
        logger.error(f"Failed to verify collection: {e}")
        return False
    
    logger.info("✅ Re-indexing complete!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
