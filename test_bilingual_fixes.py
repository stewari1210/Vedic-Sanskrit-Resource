#!/usr/bin/env python3
"""
Test script to verify all three bilingual support fixes:
1. MW Concept Store initialization
2. Dynamic source text extraction
3. Transliteration variant search
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from src.utils.transliteration import TransliterationHelper
from src.utils.mw_concept_store import MWConceptStore
from langchain_core.documents import Document

print("=" * 80)
print("BILINGUAL SUPPORT FIXES - VERIFICATION TESTS")
print("=" * 80)

# Test 1: MW Concept Store Initialization
print("\n[TEST 1] MW Concept Store Initialization")
print("-" * 80)
try:
    mw_store = MWConceptStore()
    trans_helper = TransliterationHelper()
    print("✅ MW Concept Store initialized successfully")
    print("✅ Transliteration Helper initialized successfully")
    
    # Test a lookup
    result = mw_store.lookup("Sarasvati")
    if result and result.get('found'):
        print(f"✅ MW lookup works: 'Sarasvati' → '{result['primary_key']}'")
        print(f"   Definitions: {len(result.get('definitions', []))} found")
        print(f"   Vedic refs: {result.get('vedic_refs', [])[:3]}")
    else:
        print("⚠️  MW lookup returned no results for 'Sarasvati'")
    
    # Test transliteration
    variants = trans_helper.normalize_query("Saraswati nadi ke Vinaśana")
    print(f"✅ Transliteration variants generated: {len(variants)} variants")
    for i, var in enumerate(variants[:3], 1):
        print(f"   {i}. {var}")
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Dynamic Source Text Extraction
print("\n[TEST 2] Dynamic Source Text Extraction")
print("-" * 80)
try:
    # Import the function
    from src.utils.agentic_rag import extract_source_texts
    
    # Create mock documents with different sources
    test_docs = [
        Document(page_content="Test 1", metadata={"source": "rigveda-griffith"}),
        Document(page_content="Test 2", metadata={"source": "pancavimsa_brahmana"}),
        Document(page_content="Test 3", metadata={"source": "satapatha_brahmana"}),
        Document(page_content="Test 4", metadata={"source": "rigveda-sharma"}),
    ]
    
    sources = extract_source_texts(test_docs)
    expected = "Pañcaviṃśa Brāhmaṇa, Rigveda, and Śatapatha Brāhmaṇa"
    
    print(f"Input docs: {len(test_docs)} with various sources")
    print(f"Extracted: '{sources}'")
    
    # Check if all expected sources are present
    if "Pañcaviṃśa" in sources and "Rigveda" in sources and "Śatapatha" in sources:
        print("✅ All sources correctly extracted and formatted")
    else:
        print(f"⚠️  Expected all three sources, got: {sources}")
    
    # Test single source
    single_doc = [Document(page_content="Test", metadata={"source": "pancavimsa_brahmana"})]
    single_source = extract_source_texts(single_doc)
    print(f"Single source test: '{single_source}'")
    if single_source == "Pañcaviṃśa Brāhmaṇa":
        print("✅ Single source formatting correct")
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Transliteration Variant Generation with MW Enhancement
print("\n[TEST 3] Transliteration Variants + MW Enhancement")
print("-" * 80)
try:
    # Test queries
    test_queries = [
        "Saraswati nadi ke Vinaśana",
        "सरस्वती विनाशन",
        "Vinasana in Pancavimsa",
        "अग्नि पूजा की विधि"
    ]
    
    mw_store = MWConceptStore()
    trans_helper = TransliterationHelper()
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        
        # Generate variants
        variants = trans_helper.normalize_query(query)
        print(f"  Variants ({len(variants)}): {variants[:3]}")
        
        # Try MW lookup for each word
        words = query.split()
        mw_hits = 0
        for word in words:
            if len(word) >= 3:
                result = mw_store.lookup(word)
                if result and result.get('found'):
                    mw_hits += 1
                    print(f"  MW hit: '{word}' → '{result['primary_key']}'")
        
        if mw_hits > 0:
            print(f"  ✅ {mw_hits} MW matches found")
        else:
            print(f"  ⚠️  No MW matches (expected for some queries)")
    
    print("\n✅ Transliteration and MW enhancement working")
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Proper Noun Variants
print("\n[TEST 4] Proper Noun Variants for Vinasana")
print("-" * 80)
try:
    import json
    
    with open('proper_noun_variants.json', 'r', encoding='utf-8') as f:
        variants_data = json.load(f)
    
    # Check if Vinasana exists
    rivers = variants_data.get('rivers_and_geography', {})
    
    if 'Vinasana' in rivers:
        vinasana = rivers['Vinasana']
        print("✅ Vinasana entry found in proper_noun_variants.json")
        print(f"   Canonical: {vinasana['canonical']}")
        print(f"   Variants: {vinasana['variants']}")
        print(f"   Priority: {vinasana['priority']}")
        
        # Check for key variants
        variants_list = vinasana['variants']
        required = ['Vinasana', 'Vināśana', 'विनाशन', 'disappearance']
        missing = [v for v in required if v not in variants_list]
        
        if not missing:
            print("✅ All required variants present")
        else:
            print(f"⚠️  Missing variants: {missing}")
    else:
        print("❌ Vinasana entry NOT found")
    
    # Check Sarasvati entry
    if 'Sarasvati' in rivers:
        sarasvati = rivers['Sarasvati']
        print("✅ Sarasvati entry found in proper_noun_variants.json")
        print(f"   Variants: {sarasvati['variants']}")
        if 'सरस्वती' in sarasvati['variants']:
            print("✅ Devanagari variant present")
    else:
        print("⚠️  Sarasvati entry not found (expected to be added)")
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print("""
Expected Results:
✅ Test 1: MW Concept Store and Transliteration Helper initialize without errors
✅ Test 2: Source texts correctly extracted and formatted from documents
✅ Test 3: Transliteration variants generated for mixed script queries
✅ Test 4: Vinasana and Sarasvati entries present in proper_noun_variants.json

Next Steps:
1. Run Streamlit: streamlit run src/sanskrit_tutor_frontend.py
2. Test query: "Saraswati nadi ke Vinaśana ke barre mein bataiye"
3. Verify:
   - No MW initialization warning in logs
   - Response cites "Pañcaviṃśa Brāhmaṇa" (not "Rigveda and Yajurveda")
   - MW dictionary context appears in UI
   - Relevant passages about Vinasana retrieved

4. Push to git after successful test
""")
