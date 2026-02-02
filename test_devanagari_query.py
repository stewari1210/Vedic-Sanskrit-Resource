#!/usr/bin/env python3
"""
Quick test for Devanagari query handling
"""

import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from src.utils.transliteration import TransliterationHelper
from src.utils.mw_concept_store import MWConceptStore

print("=" * 80)
print("DEVANAGARI QUERY TEST")
print("=" * 80)

# Test Devanagari query
query = "सरस्वती विनाशन के बारे में बताइए"
print(f"\nOriginal Query: {query}")

# Check Devanagari detection
is_devanagari = any('\u0900' <= char <= '\u097F' for char in query)
print(f"Is Devanagari: {is_devanagari}")

# Test transliteration
trans_helper = TransliterationHelper()
variants = trans_helper.normalize_query(query)

print(f"\nTransliteration Variants ({len(variants)}):")
for i, variant in enumerate(variants, 1):
    print(f"  {i}. {variant}")

# Test MW lookup with IAST variants
mw_store = MWConceptStore()

print("\nMW Dictionary Lookups:")
for variant in variants[:3]:
    words = variant.split()
    for word in words:
        if len(word) >= 3:
            result = mw_store.lookup(word)
            if result and result.get('found'):
                print(f"  ✅ '{word}' → '{result['primary_key']}'")
                defs = result.get('definitions', [])
                if defs:
                    print(f"     Definition: {defs[0][:100]}...")
                vedic_refs = result.get('vedic_refs', [])
                if vedic_refs:
                    print(f"     Vedic refs: {vedic_refs[:3]}")

print("\n" + "=" * 80)
print("EXPECTED BEHAVIOR:")
print("=" * 80)
print("""
1. ✅ Devanagari detected
2. ✅ Transliteration variants generated (IAST, lowercase, etc.)
3. ✅ MW lookup uses IAST variants (not Devanagari)
4. ✅ Finds 'sarasvati' and 'vinasana' in MW dictionary
5. ✅ Semantic search uses all variants in parallel
6. ✅ BM25 preserves Devanagari (won't match English corpus, but won't break)

Result: Semantic search with IAST variants will find English/IAST corpus content
""")
