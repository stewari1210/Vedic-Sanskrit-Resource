#!/usr/bin/env python3
"""
Enrich Rigveda metadata with Sanskrit preprocessing tag
"""
import json
import os
from pathlib import Path

local_store = Path("/Users/shivendratewari/github/Vedic-Sanskrit-Tutor/local_store/ancient_history")

print("\n" + "=" * 90)
print("✨ ENRICHING RIGVEDA METADATA WITH SANSKRIT TAG")
print("=" * 90)

# Get all rigveda metadata files
rigveda_files = sorted(local_store.glob("r*/r*_metadata.json"))

print(f"\nFound {len(rigveda_files)} Rigveda metadata files")

for metadata_file in rigveda_files:
    print(f"\n📝 Processing: {metadata_file.parent.name}/")
    
    # Read metadata
    with open(metadata_file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    # Add enrichment fields
    original_preprocessing = metadata.get('preprocessing', 'none')
    original_source_type = metadata.get('source_type', 'none')
    
    metadata['preprocessing'] = 'sanskrit'
    metadata['source_type'] = 'vedic_text'
    
    # Write back
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"   ✅ preprocessing: {original_preprocessing} → sanskrit")
    print(f"   ✅ source_type: {original_source_type} → vedic_text")
    print(f"   ✅ Saved: {metadata_file}")

print("\n" + "=" * 90)
print(f"✨ Enriched {len(rigveda_files)} Rigveda metadata files")
print("=" * 90 + "\n")
