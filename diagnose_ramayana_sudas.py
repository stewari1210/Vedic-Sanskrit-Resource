#!/usr/bin/env python3
"""
Diagnose why RAG is not retrieving Ramayana (Rama's birth) and Rigveda entries (Sudas, Divodasa).
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

QDRANT_URL = os.getenv('QDRANT_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'ancient_history')

print("🔍 DIAGNOSING RAMAYANA AND RIGVEDA RETRIEVAL ISSUES")
print("=" * 80)

# Connect to Qdrant Cloud
print(f"\n1️⃣  Connecting to Qdrant Cloud...")
client = QdrantClient(url=str(QDRANT_URL), api_key=str(QDRANT_API_KEY))
info = client.get_collection(COLLECTION_NAME)
print(f"   Collection: {COLLECTION_NAME}")
print(f"   Total points: {info.points_count:,}")

# Sample chunks from different sources
print(f"\n2️⃣  Sampling chunks to check metadata structure...")
offset = None
source_samples = {
    'ramayana': [],
    'rigveda': [],
    'pancavamsa': [],
    'other': []
}
checked = 0
max_check = 5000  # Check first 5000 points

while checked < max_check:
    points, next_offset = client.scroll(COLLECTION_NAME, limit=100, offset=offset, with_payload=True)
    if not points:
        break
    
    for point in points:
        payload = point.payload or {}
        metadata = payload.get('metadata', {})
        page_content = payload.get('page_content', '')
        
        # Check title or content for source identification
        title = metadata.get('title', '') if isinstance(metadata, dict) else ''
        source = metadata.get('source', '') if isinstance(metadata, dict) else ''
        
        # Categorize
        if 'ramayana' in title.lower() or 'ramayana' in source.lower() or 'ramayana' in page_content.lower()[:200]:
            if len(source_samples['ramayana']) < 5:
                source_samples['ramayana'].append({
                    'id': point.id,
                    'title': title,
                    'source': source,
                    'content_preview': page_content[:150] if page_content else 'NO CONTENT',
                    'has_metadata': bool(metadata),
                    'metadata_keys': list(metadata.keys()) if isinstance(metadata, dict) else []
                })
        elif 'rigveda' in title.lower() or 'rigveda' in source.lower():
            if len(source_samples['rigveda']) < 5:
                source_samples['rigveda'].append({
                    'id': point.id,
                    'title': title,
                    'source': source,
                    'content_preview': page_content[:150] if page_content else 'NO CONTENT',
                    'has_metadata': bool(metadata),
                    'metadata_keys': list(metadata.keys()) if isinstance(metadata, dict) else []
                })
        elif 'pancavamsa' in title.lower() or 'pancavimsa' in title.lower():
            if len(source_samples['pancavamsa']) < 3:
                source_samples['pancavamsa'].append({
                    'id': point.id,
                    'title': title,
                    'source': source,
                    'content_preview': page_content[:150] if page_content else 'NO CONTENT',
                    'has_metadata': bool(metadata),
                    'metadata_keys': list(metadata.keys()) if isinstance(metadata, dict) else []
                })
        else:
            if len(source_samples['other']) < 3:
                source_samples['other'].append({
                    'id': point.id,
                    'title': title,
                    'source': source,
                    'content_preview': page_content[:100] if page_content else 'NO CONTENT',
                    'has_metadata': bool(metadata),
                    'metadata_keys': list(metadata.keys()) if isinstance(metadata, dict) else []
                })
        
        checked += 1
    
    # Break if we have enough samples
    if (len(source_samples['ramayana']) >= 5 and 
        len(source_samples['rigveda']) >= 5 and 
        len(source_samples['pancavamsa']) >= 3):
        break
    
    if next_offset is None:
        break
    offset = next_offset

print(f"   Scanned: {checked:,} points")

# Display samples
print(f"\n3️⃣  RAMAYANA CHUNKS ({len(source_samples['ramayana'])} found):")
print("=" * 80)
if source_samples['ramayana']:
    for i, sample in enumerate(source_samples['ramayana'], 1):
        print(f"\n   Sample {i}:")
        print(f"     ID: {sample['id']}")
        print(f"     Title: {sample['title']}")
        print(f"     Source: {sample['source']}")
        print(f"     Has metadata: {sample['has_metadata']}")
        print(f"     Metadata keys: {sample['metadata_keys']}")
        print(f"     Content: {sample['content_preview'][:100]}...")
else:
    print("   ❌ NO RAMAYANA CHUNKS FOUND!")

print(f"\n4️⃣  RIGVEDA CHUNKS ({len(source_samples['rigveda'])} found):")
print("=" * 80)
if source_samples['rigveda']:
    for i, sample in enumerate(source_samples['rigveda'], 1):
        print(f"\n   Sample {i}:")
        print(f"     ID: {sample['id']}")
        print(f"     Title: {sample['title']}")
        print(f"     Source: {sample['source']}")
        print(f"     Has metadata: {sample['has_metadata']}")
        print(f"     Metadata keys: {sample['metadata_keys']}")
        print(f"     Content: {sample['content_preview'][:100]}...")
else:
    print("   ❌ NO RIGVEDA CHUNKS FOUND!")

print(f"\n5️⃣  PANCAVAMSA CHUNKS ({len(source_samples['pancavamsa'])} found):")
print("=" * 80)
if source_samples['pancavamsa']:
    for i, sample in enumerate(source_samples['pancavamsa'], 1):
        print(f"\n   Sample {i}:")
        print(f"     ID: {sample['id']}")
        print(f"     Title: {sample['title']}")
        print(f"     Has metadata: {sample['has_metadata']}")
        print(f"     Metadata keys: {sample['metadata_keys']}")
        print(f"     Content: {sample['content_preview'][:100]}...")
else:
    print("   ⚠️  No Pancavamsa chunks found in sample")

# Now search specifically for content containing "Rama", "Sudas", "Divodasa"
print(f"\n6️⃣  Searching for specific content...")
print("=" * 80)

search_terms = ['Rama', 'Sudas', 'Divodasa']
for term in search_terms:
    print(f"\n   Searching for '{term}'...")
    
    # Scroll through and find mentions
    offset = None
    found_count = 0
    samples = []
    max_samples = 3
    
    while found_count < max_samples:
        points, next_offset = client.scroll(COLLECTION_NAME, limit=100, offset=offset, with_payload=True)
        if not points:
            break
        
        for point in points:
            payload = point.payload or {}
            page_content = payload.get('page_content', '')
            metadata = payload.get('metadata', {})
            
            # Case-insensitive search
            if term.lower() in page_content.lower():
                found_count += 1
                samples.append({
                    'id': point.id,
                    'title': metadata.get('title', 'N/A') if isinstance(metadata, dict) else 'N/A',
                    'content_snippet': page_content[max(0, page_content.lower().find(term.lower())-50):
                                                   page_content.lower().find(term.lower())+100]
                })
                
                if found_count >= max_samples:
                    break
        
        if next_offset is None:
            break
        offset = next_offset
    
    if samples:
        print(f"   ✅ Found {len(samples)} chunks containing '{term}':")
        for j, sample in enumerate(samples, 1):
            print(f"\n     Example {j}:")
            print(f"       ID: {sample['id']}")
            print(f"       Title: {sample['title']}")
            print(f"       Snippet: ...{sample['content_snippet']}...")
    else:
        print(f"   ❌ NO chunks found containing '{term}'")

print("\n" + "=" * 80)
print("✅ Diagnosis complete!")
print("\nNext steps:")
print("  1. If Ramayana/Rigveda chunks missing: re-index from local_store")
print("  2. If chunks exist but no metadata: run metadata attachment scripts")
print("  3. If specific terms missing: check source files for content")
