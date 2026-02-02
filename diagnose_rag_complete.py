#!/usr/bin/env python3
"""
Complete RAG Diagnosis - Understanding why Rama, Sudas, Divodasa queries fail.

This script checks:
1. Whether content exists in local_store files
2. Whether content exists in Qdrant chunks
3. Whether HybridRetriever can find the content
4. Whether proper_noun_variants.json has the entities

NO RE-INDEXING REQUIRED.
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

print("🔍 COMPLETE RAG DIAGNOSIS")
print("=" * 80)

# Test 1: Check local_store files
print("\n📁 TEST 1: Checking local_store files for content...")
print("=" * 80)

search_terms = {
    'Rama': 'local_store/ancient_history/griffith-ramayana/griffith-ramayana.md',
    'Sudas': 'local_store/ancient_history/rigveda-griffith_COMPLETE_english_with_metadata/rigveda-griffith_COMPLETE_english_with_metadata.md',
    'Divodasa': 'local_store/ancient_history/rigveda-griffith_COMPLETE_english_with_metadata/rigveda-griffith_COMPLETE_english_with_metadata.md'
}

for term, file_path in search_terms.items():
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            count = content.lower().count(term.lower())
            print(f"✅ {term}: Found {count} mentions in {Path(file_path).name}")
            
            # Show first mention
            if count > 0:
                idx = content.lower().find(term.lower())
                snippet = content[max(0, idx-100):idx+150]
                print(f"   First mention: ...{snippet}...")
    else:
        print(f"❌ {term}: File not found: {file_path}")

# Test 2: Check proper_noun_variants.json
print("\n📚 TEST 2: Checking proper_noun_variants.json...")
print("=" * 80)

variants_file = "proper_noun_variants.json"
if os.path.exists(variants_file):
    with open(variants_file, 'r', encoding='utf-8') as f:
        variants_data = json.load(f)
    
    # Search for each term
    for term in ['Rama', 'Sudas', 'Divodasa']:
        found = False
        for category, entries in variants_data.items():
            if category.startswith('_'):
                continue
            
            if isinstance(entries, dict):
                for key, data in entries.items():
                    if term.lower() in key.lower():
                        print(f"✅ {term}: Found in '{category}' as '{key}'")
                        if isinstance(data, dict) and 'variants' in data:
                            print(f"   Variants: {data['variants'][:5]}")
                        found = True
                        break
                    
                    # Check variants too
                    if isinstance(data, dict) and 'variants' in data:
                        for variant in data['variants']:
                            if term.lower() in variant.lower():
                                print(f"✅ {term}: Found as variant of '{key}' in '{category}'")
                                found = True
                                break
            if found:
                break
        
        if not found:
            print(f"❌ {term}: NOT found in proper_noun_variants.json")
else:
    print(f"❌ proper_noun_variants.json not found!")

# Test 3: Check Qdrant for actual content
print("\n☁️  TEST 3: Checking Qdrant Cloud for content...")
print("=" * 80)

try:
    from qdrant_client import QdrantClient
    
    QDRANT_URL = os.getenv('QDRANT_URL')
    QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
    COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'ancient_history')
    
    client = QdrantClient(url=str(QDRANT_URL), api_key=str(QDRANT_API_KEY))
    
    for term in ['Rama', 'Sudas', 'Divodasa']:
        print(f"\nSearching for '{term}'...")
        
        # Scroll through and search
        offset = None
        found_count = 0
        max_check = 10000
        checked = 0
        
        while checked < max_check and found_count < 3:
            points, next_offset = client.scroll(
                COLLECTION_NAME, 
                limit=100, 
                offset=offset, 
                with_payload=True
            )
            
            if not points:
                break
            
            for point in points:
                payload = point.payload or {}
                content = payload.get('page_content', '')
                
                if term.lower() in content.lower():
                    found_count += 1
                    metadata = payload.get('metadata', {})
                    title = metadata.get('title', 'Unknown') if isinstance(metadata, dict) else 'Unknown'
                    
                    # Get snippet
                    idx = content.lower().find(term.lower())
                    snippet = content[max(0, idx-80):idx+100]
                    
                    print(f"  ✅ Found in chunk (ID: {point.id})")
                    print(f"     Title: {title}")
                    print(f"     Snippet: ...{snippet}...")
                    
                    if found_count >= 3:
                        break
                
                checked += 1
            
            if next_offset is None:
                break
            offset = next_offset
        
        if found_count == 0:
            print(f"  ❌ '{term}' NOT found in any chunks (checked {checked:,} chunks)")
        else:
            print(f"  ℹ️  Total checked: {checked:,} chunks, found: {found_count}")

except Exception as e:
    print(f"❌ Error connecting to Qdrant: {e}")

# Test 4: Test HybridRetriever
print("\n🔎 TEST 4: Testing HybridRetriever...")
print("=" * 80)

try:
    from src.utils.agentic_rag import get_shared_retriever
    
    # Get the retriever
    retriever = get_shared_retriever()
    
    for term in ['Rama', 'Sudas', 'Divodasa']:
        print(f"\nQuery: 'Who is {term}?'")
        
        try:
            results = retriever.invoke(f"Who is {term}?")
            
            if results:
                print(f"  ✅ Retrieved {len(results)} documents")
                for i, doc in enumerate(results[:3], 1):
                    metadata = doc.metadata
                    title = metadata.get('title', 'Unknown')
                    content_preview = doc.page_content[:150].replace('\n', ' ')
                    
                    # Check if term is in content
                    has_term = term.lower() in doc.page_content.lower()
                    status = "✓ HAS" if has_term else "✗ MISSING"
                    
                    print(f"    Doc {i}: [{status} '{term}'] {title}")
                    print(f"           Preview: {content_preview}...")
            else:
                print(f"  ❌ No documents retrieved!")
        
        except Exception as e:
            print(f"  ❌ Retrieval error: {e}")

except Exception as e:
    print(f"❌ Error testing retriever: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("✅ DIAGNOSIS COMPLETE!")
print("\nSUMMARY:")
print("  - If content exists in local_store but NOT in Qdrant → Need to upload")
print("  - If content exists in Qdrant but retriever fails → Query expansion issue")
print("  - If missing from proper_noun_variants.json → Add entities there")
print("  - If Qdrant chunks show wrong titles → Metadata mismatch during indexing")
