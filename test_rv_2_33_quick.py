"""Quick test of RV 2.33 retrieval with improved filtering"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.cli_run import build_index_and_retriever, auto_retrieve_both_translations

print("\n" + "="*80)
print("Testing RV 2.33 (Rudra Hymn) Retrieval")
print("="*80 + "\n")

# Build retriever
vec_db, docs, retriever = build_index_and_retriever(force=False)

# Test retrieval
griffith_text, sharma_text = auto_retrieve_both_translations(retriever, "RV 2.33")

print("🔵 GRIFFITH'S TRANSLATION:")
print("-" * 80)
if griffith_text:
    print(griffith_text[:300])
    if "[02-033]" in griffith_text:
        print("\n✅ CORRECT! Found [02-033] (Hymn 33)")
    else:
        print("\n❌ WRONG! Does not contain [02-033]")
else:
    print("❌ NOT FOUND")

print("\n" + "="*80)
print("\n🟢 SHARMA'S TRANSLATION:")
print("-" * 80)
if sharma_text:
    print(sharma_text[:300])
    if "MANDAL - 2 / SUKTA - 33" in sharma_text.upper():
        print("\n✅ CORRECT! Found MANDAL - 2 / SUKTA - 33")
    else:
        print("\n❌ WRONG! Does not contain MANDAL - 2 / SUKTA - 33")
else:
    print("❌ NOT FOUND")

print("\n" + "="*80)
