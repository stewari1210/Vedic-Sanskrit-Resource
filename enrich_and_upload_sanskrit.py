#!/usr/bin/env python3
"""
Enrich metadata for Sanskrit texts in local_store and append to Qdrant Cloud.
This script:
1. Adds 'preprocessing': 'sanskrit' to metadata for Shatapatha Brahmana and Atharvaveda
2. Appends these documents to Qdrant Cloud
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def detect_sanskrit_content(text: str) -> bool:
    """
    Detect if text contains Sanskrit content (Devanagari or IAST transliteration).
    """
    # Devanagari range: U+0900 to U+097F
    devanagari_chars = sum(1 for c in text if '\u0900' <= c <= '\u097F')
    
    # IAST markers (common Sanskrit diacritics)
    iast_markers = {'ā', 'ī', 'ū', 'ṛ', 'ṝ', 'ḷ', 'ṅ', 'ñ', 'ṇ', 'ś', 'ṣ', 'ṃ', 'ḥ', 'ṭ', 'ḍ'}
    iast_count = sum(1 for c in text if c in iast_markers)
    
    # If we have significant Sanskrit markers, it's Sanskrit
    return (devanagari_chars > 100) or (iast_count > 10)

def enrich_metadata_for_sanskrit(metadata_file: str, content_file: str):
    """
    Add 'preprocessing': 'sanskrit' to metadata if content is Sanskrit.
    """
    print(f"\n📝 Processing: {metadata_file}")
    
    try:
        # Read content
        with open(content_file, 'r', encoding='utf-8') as f:
            content = f.read(5000)  # Read first 5000 chars for detection
        
        # Detect Sanskrit
        is_sanskrit = detect_sanskrit_content(content)
        
        # Read metadata
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Add preprocessing if Sanskrit
        if is_sanskrit:
            metadata['preprocessing'] = 'sanskrit'
            metadata['source_type'] = 'vedic_text'
            print(f"  ✅ Sanskrit detected! Added preprocessing='sanskrit'")
        else:
            print(f"  ⚠️  No Sanskrit detected")
        
        # Write back
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        return True
    
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def enrich_local_store_sanskrit():
    """
    Enrich metadata for Shatapatha Brahmana and Atharvaveda in local_store.
    """
    local_store = Path("local_store/ancient_history")
    
    # Files to enrich
    files_to_enrich = [
        ("Shatapatha_Brahmana_I/Shatapatha_Brahmana_I_metadata.json", 
         "Shatapatha_Brahmana_I/Shatapatha_Brahmana_I.md"),
        ("atharvaveda_complete/atharvaveda_complete_metadata.json",
         "atharvaveda_complete/atharvaveda_complete.md"),
    ]
    
    print("=" * 70)
    print("🔄 ENRICHING METADATA FOR SANSKRIT TEXTS")
    print("=" * 70)
    
    success_count = 0
    for metadata_rel, content_rel in files_to_enrich:
        metadata_path = local_store / metadata_rel
        content_path = local_store / content_rel
        
        if metadata_path.exists() and content_path.exists():
            if enrich_metadata_for_sanskrit(str(metadata_path), str(content_path)):
                success_count += 1
        else:
            print(f"⚠️  Files not found:")
            print(f"   Metadata: {metadata_path}")
            print(f"   Content: {content_path}")
    
    print(f"\n✅ Enriched {success_count} metadata files with Sanskrit preprocessing tag")
    return success_count > 0

def append_to_qdrant_cloud():
    """
    Append the Sanskrit documents to Qdrant Cloud.
    """
    print("\n" + "=" * 70)
    print("🚀 APPENDING DOCUMENTS TO QDRANT CLOUD")
    print("=" * 70)
    
    try:
        from src.utils.index_files import create_qdrant_vector_store
        
        print("\n📤 Creating/updating Qdrant vector store with enriched documents...")
        
        # This will load all documents from local_store (including the newly indexed ones)
        # and append them to Qdrant Cloud
        vector_store, chunks = create_qdrant_vector_store(force_recreate=False, local_only=False)
        
        print(f"\n✅ Successfully updated Qdrant Cloud!")
        print(f"📊 Processed {len(chunks)} chunks")
        
        return True
    
    except Exception as e:
        print(f"\n❌ Error appending to Qdrant Cloud: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Step 1: Enrich metadata
    enriched = enrich_local_store_sanskrit()
    
    if enriched:
        # Step 2: Append to Qdrant Cloud
        append_to_qdrant_cloud()
    else:
        print("\n⚠️  Skipping Qdrant upload due to metadata enrichment issues")
