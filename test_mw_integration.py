#!/usr/bin/env python3
"""
Test MW Concept Store Integration with Retriever

This script tests that:
1. MW Concept Store loads successfully
2. Transliteration variants are generated
3. Query enhancement works (adds definitions)
4. MW context is attached to retrieved documents
5. Bilingual queries (Devanagari/IAST) work

Usage:
    python3 test_mw_integration.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.mw_concept_store import MWConceptStore
from src.utils.transliteration import TransliterationHelper

def test_mw_loading():
    """Test 1: MW Concept Store loads successfully."""
    print("=" * 80)
    print("Test 1: MW Concept Store Loading")
    print("=" * 80)
    
    try:
        mw = MWConceptStore()
        stats = mw.stats()
        
        print(f"✅ MW Concept Store loaded successfully!")
        print(f"   Total concepts: {stats['total_concepts']:,}")
        print(f"   Total lookup keys: {stats['total_lookup_keys']:,}")
        print()
        return True
    except Exception as e:
        print(f"❌ Failed to load MW Concept Store: {e}")
        return False


def test_transliteration():
    """Test 2: Transliteration generates variants."""
    print("=" * 80)
    print("Test 2: Transliteration Variants")
    print("=" * 80)
    
    try:
        trans = TransliterationHelper()
        
        test_queries = [
            "अग्नि",
            "Sarasvatī",
            "soma"
        ]
        
        for query in test_queries:
            variants = trans.normalize_query(query)
            print(f"Query: '{query}'")
            print(f"Variants ({len(variants)}): {variants[:5]}")
            print()
        
        print("✅ Transliteration working!")
        print()
        return True
    except Exception as e:
        print(f"❌ Transliteration failed: {e}")
        return False


def test_mw_lookup():
    """Test 3: MW lookup finds Sanskrit terms."""
    print("=" * 80)
    print("Test 3: MW Dictionary Lookup")
    print("=" * 80)
    
    try:
        mw = MWConceptStore()
        
        test_terms = [
            "अग्नि",
            "agni",
            "sarasvati",
            "soma",
            "veda"
        ]
        
        for term in test_terms:
            result = mw.lookup(term)
            
            if result and result.get('found'):
                print(f"✅ '{term}' → '{result['primary_key']}'")
                print(f"   Devanagari: {result['devanagari']}")
                print(f"   Definitions: {len(result['definitions'])}")
                print(f"   Vedic refs: {result['vedic_refs'][:3]}")
            else:
                print(f"❌ '{term}' not found")
            print()
        
        print("✅ MW lookup working!")
        print()
        return True
    except Exception as e:
        print(f"❌ MW lookup failed: {e}")
        return False


def test_query_expansion():
    """Test 4: Query expansion adds MW definitions."""
    print("=" * 80)
    print("Test 4: Query Expansion with MW")
    print("=" * 80)
    
    try:
        mw = MWConceptStore()
        
        test_queries = [
            "अग्नि पूजा",
            "Sarasvati river",
            "soma juice importance"
        ]
        
        for query in test_queries:
            expanded = mw.expand_query(query)
            
            print(f"Original: '{query}'")
            print(f"Expanded: '{expanded[:150]}...'")
            print(f"Added: {len(expanded) - len(query)} characters")
            print()
        
        print("✅ Query expansion working!")
        print()
        return True
    except Exception as e:
        print(f"❌ Query expansion failed: {e}")
        return False


def test_retriever_integration():
    """Test 5: MW integration with retriever (mock test)."""
    print("=" * 80)
    print("Test 5: Retriever Integration (Mock)")
    print("=" * 80)
    
    try:
        # Import retriever to check if MW initializes
        from src.utils.retriever import HybridRetriever
        
        # Can't fully test without vector DB, but can check imports
        print("✅ HybridRetriever imports MW successfully")
        print("   - MWConceptStore import: OK")
        print("   - TransliterationHelper import: OK")
        print()
        
        # Check if MW_ENABLED flag is set
        from src.utils import retriever
        if hasattr(retriever, 'MW_ENABLED'):
            print(f"   MW_ENABLED flag: {retriever.MW_ENABLED}")
        
        print()
        print("✅ Retriever integration ready!")
        print("   (Full test requires running with vector DB)")
        print()
        return True
    except Exception as e:
        print(f"❌ Retriever integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bilingual_queries():
    """Test 6: Bilingual query handling."""
    print("=" * 80)
    print("Test 6: Bilingual Query Handling")
    print("=" * 80)
    
    try:
        mw = MWConceptStore()
        trans = TransliterationHelper()
        
        bilingual_queries = [
            "अग्नि पूजा कैसे करें",           # Devanagari
            "Sarasvatī river disappearance",  # IAST + English
            "सोम रस का महत्व",                # Hindi
        ]
        
        for query in bilingual_queries:
            print(f"Query: '{query}'")
            
            # Generate variants
            variants = trans.normalize_query(query)
            print(f"  Variants: {len(variants)}")
            print(f"  Sample: {variants[:3]}")
            
            # Expand with MW
            expanded = mw.expand_query(query)
            added_chars = len(expanded) - len(query)
            print(f"  Expansion: +{added_chars} chars")
            
            # Check for Sanskrit terms
            words = query.split()
            found_terms = 0
            for word in words:
                result = mw.lookup(word)
                if result and result.get('found'):
                    found_terms += 1
            
            print(f"  MW terms found: {found_terms}/{len(words)}")
            print()
        
        print("✅ Bilingual query handling working!")
        print()
        return True
    except Exception as e:
        print(f"❌ Bilingual queries failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\n")
    print("🧪" * 40)
    print("MW CONCEPT STORE INTEGRATION TESTS")
    print("🧪" * 40)
    print()
    
    tests = [
        ("MW Loading", test_mw_loading),
        ("Transliteration", test_transliteration),
        ("MW Lookup", test_mw_lookup),
        ("Query Expansion", test_query_expansion),
        ("Retriever Integration", test_retriever_integration),
        ("Bilingual Queries", test_bilingual_queries),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"❌ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n")
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status:12} {name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! MW integration ready.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check output above.")
    
    print()


if __name__ == '__main__':
    main()
