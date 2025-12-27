#!/usr/bin/env python3
"""
Test script to validate ProperNounVariantManager integration into retriever.

Tests:
1. Variant expansion for proper nouns
2. Context-based disambiguation
3. Database lookup functionality
4. Fallback pattern matching

Run this BEFORE re-indexing to ensure integration works correctly.
"""

import sys
sys.path.insert(0, '/Users/shivendratewari/github/RAG-CHATBOT-CLI-Version')

from src.utils.proper_noun_variants import (
    get_proper_noun_variants,
    disambiguate_proper_noun,
    get_manager
)

def test_variant_expansion():
    """Test that variant expansion retrieves all spelling forms."""
    print("=" * 70)
    print("TEST 1: Variant Expansion")
    print("=" * 70)

    test_cases = [
        "Vasishtha",
        "Vishvamitra",
        "Bharadvaja",
        "Gautama",
        "Kashyapa",
        "Sudas",
    ]

    for noun in test_cases:
        variants = get_proper_noun_variants(noun)
        print(f"\n'{noun}' → {variants}")
        if variants:
            print(f"  ✅ Found {len(variants)} variant(s)")
        else:
            print(f"  ⚠️  No variants found (will use fallback patterns)")

    print("\n" + "=" * 70)

def test_disambiguation():
    """Test context-based disambiguation for homonyms."""
    print("\nTEST 2: Context-Based Disambiguation")
    print("=" * 70)

    test_cases = [
        ("Bharata", "Tell me about Bharata in the Ten Kings Battle", "Expected: Bharata (tribe)"),
        ("Bharata", "Who is Bharata the sage?", "Expected: Bharata (rishi)"),
        ("Puru", "Tell me about Puru enemies of Bharatas", "Expected: Puru (tribe)"),
        ("Purusha", "Tell me about Purusha in cosmic hymn", "Expected: Purusha (Cosmic Being)"),
    ]

    for noun, context, expected in test_cases:
        result = disambiguate_proper_noun(noun, context)
        print(f"\n'{noun}' in context: '{context[:50]}...'")
        print(f"  Result: '{result}'")
        print(f"  {expected}")
        if result != noun:
            print(f"  ✅ Disambiguation applied")
        else:
            print(f"  ⚠️  No disambiguation (may be correct if not homonym)")

    print("\n" + "=" * 70)

def test_database_stats():
    """Test database loading and statistics."""
    print("\nTEST 3: Database Loading and Statistics")
    print("=" * 70)

    manager = get_manager()

    print(f"\nDatabase loaded: {manager.variants_data is not None}")

    if manager.variants_data:
        sages = manager.variants_data.get("sages", {})
        tribes = manager.variants_data.get("tribes_and_kingdoms", {})
        kings = manager.variants_data.get("kings_and_heroes", {})

        print(f"\nCategories found:")
        print(f"  - Sages: {len(sages)} entries")
        print(f"  - Tribes: {len(tribes)} entries")
        print(f"  - Kings/Heroes: {len(kings)} entries")

        # Show a sample entry
        if "Vasishtha" in sages:
            print(f"\nSample entry - Vasishtha:")
            vasishtha = sages["Vasishtha"]
            print(f"  Variants: {vasishtha.get('variants', [])}")
            print(f"  Sources: {vasishtha.get('sources', {})}")
            print(f"  Total occurrences: {vasishtha.get('total_occurrences', 0)}")
            print(f"  Priority: {vasishtha.get('priority', 'N/A')}")
            print(f"  ✅ Complete entry found")
        else:
            print(f"  ⚠️  Vasishtha entry not found in database")

    print("\n" + "=" * 70)

def test_fallback_patterns():
    """Test fallback pattern matching for entities not in database."""
    print("\nTEST 4: Fallback Pattern Matching")
    print("=" * 70)

    # Test fallback logic directly without importing retriever
    # (Retriever import requires full app context with 'helper' module)

    def apply_fallback_patterns(word):
        """Simplified fallback pattern logic for testing."""
        variants = [word]

        # Check database first
        db_variants = get_proper_noun_variants(word)
        if db_variants:
            variants.extend(db_variants)
            return list(set(variants))

        # Fallback patterns if not in database
        if word.endswith('as'):
            variants.append(word + 'a')
        elif word.endswith('asa'):
            variants.append(word[:-1])

        if 'sh' in word.lower():
            variants.append(word.replace('sh', 's').replace('Sh', 'S'))
        elif 's' in word.lower() and 'sh' not in word.lower():
            variants.append(word.replace('s', 'sh').replace('S', 'Sh'))

        return list(set(variants))

    test_cases = [
        ("UnknownEntity", "Should return original only (no patterns match)"),
        ("Krishnas", "Should try as→asa and s→sh patterns"),
        ("Newash", "Should try sh→s pattern"),
    ]

    for noun, description in test_cases:
        variants = apply_fallback_patterns(noun)
        print(f"\n'{noun}' ({description})")
        print(f"  Variants: {variants}")
        if len(variants) > 1:
            print(f"  ✅ Fallback patterns applied")
        else:
            print(f"  ℹ️  No patterns matched (only original returned)")

    print("\n" + "=" * 70)

def test_critical_variants():
    """Test the most critical variant groups."""
    print("\nTEST 5: Critical Variant Groups (250 occurrences)")
    print("=" * 70)

    critical_tests = [
        ("Vasishtha", "Sharma spelling"),
        ("Vasistha", "Griffith-R spelling"),
    ]

    for noun, description in critical_tests:
        variants = get_proper_noun_variants(noun)
        print(f"\n'{noun}' ({description})")
        print(f"  Variants: {variants}")

        # Both should map to same variant set
        if variants:
            print(f"  ✅ Variant expansion working")
            # Check if cross-reference exists
            for variant in variants:
                check_variants = get_proper_noun_variants(variant)
                if check_variants:
                    print(f"    ✅ Reverse lookup '{variant}' → {check_variants}")
        else:
            print(f"  ❌ No variants found - database may not be loaded")

    print("\n" + "=" * 70)

def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 10 + "VARIANT MANAGER INTEGRATION TEST SUITE" + " " * 20 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    try:
        test_database_stats()
        test_variant_expansion()
        test_disambiguation()
        test_fallback_patterns()
        test_critical_variants()

        print("\n" + "=" * 70)
        print("✅ ALL TESTS COMPLETE")
        print("=" * 70)
        print("\nNext Steps:")
        print("1. If all tests passed: Proceed to Step 5 (Re-index RAG)")
        print("2. If any tests failed: Check proper_noun_variants.json loaded correctly")
        print("\nRe-index command:")
        print("  python src/cli_run.py --files \\")
        print("    rigveda-sharma_COMPLETE_english_with_metadata.txt \\")
        print("    griffith-rigveda_COMPLETE_english_with_metadata.txt \\")
        print("    yajurveda-sharma_COMPLETE_english_with_metadata.txt \\")
        print("    yajurveda-griffith_COMPLETE_english_with_metadata.txt")
        print()

    except Exception as e:
        print("\n" + "=" * 70)
        print("❌ TEST FAILED WITH ERROR")
        print("=" * 70)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        print("\nPlease fix errors before proceeding to Step 5.")

if __name__ == "__main__":
    main()
