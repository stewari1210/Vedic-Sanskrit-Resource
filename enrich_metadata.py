#!/usr/bin/env python3
"""
Add custom metadata fields to local_store metadata files for better retrieval.
This ensures that Sanskrit texts have the 'preprocessing' and 'source' fields
in their _metadata.json files, so they get properly indexed in Qdrant Cloud.
"""
import json
import os
from pathlib import Path
from typing import Dict, Any
import sys

sys.path.insert(0, str(Path(__file__).parent))
from src.helper import logger

def add_metadata_fields_to_rigveda():
    """Add Sanskrit preprocessing metadata to Rigveda files."""
    rigveda_path = Path("local_store/ancient_history")
    
    for metadata_file in rigveda_path.glob("r*/r*_metadata.json"):
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Check if already has our custom fields
        if 'preprocessing' in metadata and 'source' in metadata:
            logger.info(f"✓ Already updated: {metadata_file}")
            continue
        
        # Add custom fields
        metadata['preprocessing'] = 'sanskrit'  # Mark as Sanskrit for prioritization
        metadata['source'] = f"Rigveda Mandala {metadata.get('title', '').split()[-1]}"
        metadata['source_type'] = 'veda'  # For easy filtering
        
        # Preserve keywords if they exist
        if 'keywords' not in metadata:
            metadata['keywords'] = ['veda', 'rigveda', 'sanskrit', 'hymn', 'vedic']
        else:
            # Ensure 'sanskrit' keyword is present
            if isinstance(metadata['keywords'], list) and 'sanskrit' not in metadata['keywords']:
                metadata['keywords'].append('sanskrit')
        
        # Save updated metadata
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Updated: {metadata_file}")
        logger.info(f"   - Added preprocessing: {metadata['preprocessing']}")
        logger.info(f"   - Added source: {metadata['source']}")

def add_metadata_fields_to_other_texts():
    """Add appropriate metadata fields to other Vedic texts."""
    local_store_path = Path("local_store")
    
    category_mapping = {
        'satapatha_brahmana': {
            'preprocessing': 'sanskrit',
            'source_type': 'brahmana',
            'keywords_add': ['brahmana', 'sanskrit', 'vedic'],
        },
        'pancavamsa_brahmana': {
            'preprocessing': 'sanskrit',
            'source_type': 'brahmana',
            'keywords_add': ['brahmana', 'pancavamsa', 'sanskrit', 'vedic'],
        },
        'yajurveda': {
            'preprocessing': 'sanskrit',
            'source_type': 'veda',
            'keywords_add': ['veda', 'yajurveda', 'sanskrit', 'vedic'],
        },
        'ramayana': {
            'preprocessing': 'sanskrit',
            'source_type': 'epic',
            'keywords_add': ['ramayana', 'sanskrit', 'epic', 'valmiki'],
        },
    }
    
    for metadata_file in local_store_path.glob("*/**/*_metadata.json"):
        filename = metadata_file.name
        
        # Skip Rigveda (already handled)
        if 'r0' in filename:
            continue
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Check if already has our custom fields
        if 'preprocessing' in metadata:
            logger.info(f"✓ Already has preprocessing: {filename}")
            continue
        
        # Find matching category
        matched = False
        for category, fields in category_mapping.items():
            if category.replace('_', '').lower() in filename.replace('_', '').lower():
                logger.info(f"✅ Matched category: {category} for {filename}")
                
                # Add fields
                metadata['preprocessing'] = fields['preprocessing']
                metadata['source_type'] = fields['source_type']
                
                # Add keywords
                if 'keywords' not in metadata:
                    metadata['keywords'] = fields['keywords_add']
                else:
                    if isinstance(metadata['keywords'], list):
                        for kw in fields['keywords_add']:
                            if kw not in metadata['keywords']:
                                metadata['keywords'].append(kw)
                
                # Save updated metadata
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                
                logger.info(f"   - Added preprocessing: {fields['preprocessing']}")
                logger.info(f"   - Added source_type: {fields['source_type']}")
                
                matched = True
                break
        
        if not matched:
            logger.warning(f"⚠️  Could not categorize: {filename}")

def main():
    logger.info("=" * 60)
    logger.info("Adding custom metadata fields to local_store metadata files")
    logger.info("=" * 60)
    logger.info("")
    
    logger.info("Processing Rigveda files...")
    add_metadata_fields_to_rigveda()
    
    logger.info("")
    logger.info("Processing other Vedic texts...")
    add_metadata_fields_to_other_texts()
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("✅ Metadata enrichment complete!")
    logger.info("=" * 60)
    logger.info("")
    logger.info("📌 Next steps:")
    logger.info("   1. Delete Qdrant Cloud collection: src/utils/cleanup_and_reupload_qdrant.py")
    logger.info("   2. Re-index with force_recreate=True to upload enriched metadata")
    logger.info("   3. Test with: python test_sudas_query.py")

if __name__ == "__main__":
    main()
