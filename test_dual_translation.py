"""
Test script to verify dual-translation debate system
Tests that Griffith and Sharma agents debate their own respective translations
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.cli_run import auto_retrieve_both_translations, build_index_and_retriever

def test_dual_translation_retrieval():
    """Test that we can retrieve both Griffith and Sharma translations"""

    print("=" * 80)
    print("Testing Dual-Translation Retrieval System")
    print("=" * 80)

    # Build retriever
    print("\n📚 Building retriever...")
    vec_db, docs, retriever = build_index_and_retriever()

    # Test verses
    test_verses = [
        "RV 10.85.12",  # Three-wheeled chariot
        "RV 1.32.1",    # Indra-Vritra
        "RV 10.129.1",  # Nasadiya Sukta
    ]

    for verse_ref in test_verses:
        print("\n" + "=" * 80)
        print(f"Testing: {verse_ref}")
        print("=" * 80)

        griffith_text, sharma_text = auto_retrieve_both_translations(retriever, verse_ref)

        if griffith_text:
            print("\n✅ GRIFFITH'S TRANSLATION:")
            print(f"{griffith_text[:300]}...")
        else:
            print("\n❌ Griffith translation NOT found")

        if sharma_text:
            print("\n✅ SHARMA'S TRANSLATION:")
            print(f"{sharma_text[:300]}...")
        else:
            print("\n❌ Sharma translation NOT found")

        if griffith_text and sharma_text:
            # Check if translations are different
            if griffith_text != sharma_text:
                print("\n✅ Translations are DIFFERENT (as expected)")
            else:
                print("\n⚠️  Translations are IDENTICAL (unexpected)")

        print("\n" + "-" * 80)

if __name__ == "__main__":
    test_dual_translation_retrieval()
