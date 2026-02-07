#!/usr/bin/env python3
"""
Diagnostic script to check what metadata is actually stored in Qdrant Cloud.
"""
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

from qdrant_client import QdrantClient
from src.config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME
from src.helper import logger

def check_qdrant_cloud_metadata():
    """Check what metadata fields are stored in Qdrant Cloud."""
    
    if not QDRANT_URL or not QDRANT_API_KEY:
        logger.error("❌ Qdrant Cloud credentials not configured. Cannot check cloud metadata.")
        return
    
    logger.info(f"🔗 Connecting to Qdrant Cloud: {QDRANT_URL}")
    client = QdrantClient(url=str(QDRANT_URL), api_key=str(QDRANT_API_KEY))
    
    try:
        # Get collection info
        collection_info = client.get_collection(COLLECTION_NAME)
        logger.info(f"✅ Collection '{COLLECTION_NAME}' found")
        logger.info(f"   Points count: {collection_info.points_count}")
        logger.info(f"   Vector size: {collection_info.config.params.vectors.size}")
        
        # Scroll through first 10 points to examine payload structure
        logger.info(f"\n📋 Examining first 10 points' payloads:")
        offset = 0
        limit = 10
        
        points, _ = client.scroll(COLLECTION_NAME, limit=limit, offset=offset)
        
        if not points:
            logger.warning("⚠️  No points found in collection")
            return
        
        logger.info(f"Retrieved {len(points)} points\n")
        
        for i, point in enumerate(points):
            logger.info(f"Point {i+1} (ID: {point.id}):")
            
            if point.payload:
                logger.info(f"   Payload keys: {list(point.payload.keys())}")
                
                # Log each metadata field
                for key, value in point.payload.items():
                    if isinstance(value, str):
                        # Truncate long strings
                        display_value = value[:100] + "..." if len(value) > 100 else value
                        logger.info(f"     - {key}: {display_value}")
                    elif isinstance(value, dict):
                        logger.info(f"     - {key}: dict with keys {list(value.keys())}")
                        # Show nested metadata fields
                        for nested_key, nested_val in value.items():
                            if isinstance(nested_val, str):
                                nested_display = nested_val[:60] + "..." if len(nested_val) > 60 else nested_val
                                logger.info(f"       - {nested_key}: {nested_display}")
                            elif isinstance(nested_val, list):
                                logger.info(f"       - {nested_key}: [{len(nested_val)} items]")
                            else:
                                logger.info(f"       - {nested_key}: {nested_val}")
                    elif isinstance(value, (int, float, bool)):
                        logger.info(f"     - {key}: {value}")
                    elif isinstance(value, list):
                        logger.info(f"     - {key}: [{len(value)} items]")
                    else:
                        logger.info(f"     - {key}: {type(value).__name__}")
            else:
                logger.warning("   No payload")
            
            logger.info("")
        
        # Check for specific metadata fields
        logger.info("🔍 Searching for genealogical metadata across all points...")
        
        # Sample some points to see the full payload
        logger.info("\n📄 Sample payload (first point):")
        if points and points[0].payload:
            logger.info(json.dumps(points[0].payload, indent=2, default=str)[:500])
        
    except Exception as e:
        logger.error(f"❌ Error checking Qdrant Cloud: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_qdrant_cloud_metadata()
