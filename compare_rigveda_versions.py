#!/usr/bin/env python3
"""
Compare Sharma's parsed English Rigveda with Griffith's Rigveda.

Purpose:
- Validate parsing quality by comparing structure and content
- Both should have same number of Mandalas (10) and Suktas/Hymns (1028)
- Extract proper nouns and compare coverage
"""

import re
from pathlib import Path
from collections import Counter
import sys


def count_hymns_sharma(file_path):
    """Count Mandalas and Suktas in Sharma's version."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all Mandala/Sukta markers
    suktas = re.findall(r'Mandala (\d+)/Sukta (\d+)', content)

    # Count by Mandala
    mandala_counts = Counter()
    for mandala, sukta in suktas:
        mandala_counts[int(mandala)] += 1

    return suktas, mandala_counts


def count_hymns_griffith(file_path):
    """Count Hymns in Griffith's version."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all HYMN markers - Griffith uses format like "HYMN I.", "HYMN II.", etc.
    hymns = re.findall(r'HYMN [IVXLC]+\.', content)

    # Find Mandala markers - Griffith uses "BOOK" or "MANDAL"
    books = re.findall(r'(?:BOOK|MANDAL)\s*[\-\s]*(\d+)', content, re.IGNORECASE)

    return hymns, books


def extract_proper_nouns(text, min_length=4, min_freq=3):
    """Extract likely proper nouns from text.

    Proper nouns are typically:
    - Capitalized words (except sentence starts)
    - Not common English words
    - Appear multiple times
    """
    # Common English words to exclude
    common_words = {
        'The', 'This', 'That', 'These', 'Those', 'When', 'Where', 'What',
        'Who', 'Which', 'How', 'May', 'Let', 'Come', 'Give', 'Bring',
        'Lord', 'God', 'Gods', 'Goddess', 'Divine', 'Holy', 'Sacred',
        'Great', 'Mighty', 'Strong', 'Wise', 'Fair', 'Bright', 'Golden',
        'Father', 'Mother', 'Son', 'Brother', 'Sister', 'Child',
        'King', 'Queen', 'Prince', 'Hero', 'Sage', 'Bull', 'Cow',
        'Heaven', 'Earth', 'Sky', 'Sun', 'Moon', 'Dawn', 'Night',
        'Fire', 'Water', 'Wind', 'Light', 'Dark'
    }

    # Find capitalized words (not at sentence start)
    # Pattern: not after period/newline, then capitalized word
    words = re.findall(r'(?<![.\n])\s+([A-Z][a-z]{' + str(min_length-1) + ',})', text)

    # Count frequencies
    word_freq = Counter(words)

    # Filter by frequency and exclude common words
    proper_nouns = {
        word: count
        for word, count in word_freq.items()
        if count >= min_freq and word not in common_words
    }

    return proper_nouns


def compare_proper_nouns(sharma_nouns, griffith_nouns):
    """Compare proper nouns between the two versions."""
    sharma_set = set(sharma_nouns.keys())
    griffith_set = set(griffith_nouns.keys())

    # Common nouns
    common = sharma_set & griffith_set

    # Unique to each
    sharma_only = sharma_set - griffith_set
    griffith_only = griffith_set - sharma_set

    # Calculate overlap percentage
    total_unique = len(sharma_set | griffith_set)
    overlap_pct = (len(common) / total_unique * 100) if total_unique > 0 else 0

    return {
        'common': common,
        'sharma_only': sharma_only,
        'griffith_only': griffith_only,
        'overlap_percent': overlap_pct
    }


def main():
    print("=" * 70)
    print("RIGVEDA COMPARISON: Sharma's English vs Griffith")
    print("=" * 70)
    print()

    # File paths
    sharma_file = Path('rigveda-sharma_english_with_metadata.txt')
    griffith_file = Path('local_store/ancient_history/griffith-rigveda/griffith-rigveda.md')

    if not sharma_file.exists():
        print(f"❌ Sharma file not found: {sharma_file}")
        return 1

    if not griffith_file.exists():
        print(f"❌ Griffith file not found: {griffith_file}")
        return 1

    # 1. Compare Structure
    print("📊 STRUCTURE COMPARISON")
    print("-" * 70)

    # Sharma structure
    print("\n📖 Sharma's English version:")
    sharma_suktas, sharma_mandala_counts = count_hymns_sharma(sharma_file)
    print(f"  Total Suktas found: {len(sharma_suktas)}")
    print(f"  Mandalas: {len(sharma_mandala_counts)}")
    print(f"  Breakdown by Mandala:")
    for mandala in sorted(sharma_mandala_counts.keys()):
        print(f"    Mandala {mandala}: {sharma_mandala_counts[mandala]} Suktas")

    # Griffith structure
    print("\n📖 Griffith's version:")
    griffith_hymns, griffith_books = count_hymns_griffith(griffith_file)
    print(f"  Total HYMNs found: {len(griffith_hymns)}")
    print(f"  Books/Mandalas mentioned: {len(set(griffith_books))}")

    # Expected: Rigveda has 1028 hymns across 10 Mandalas
    print("\n✅ Expected: 1028 hymns across 10 Mandalas")

    # Check if counts match
    if len(sharma_suktas) >= 970:  # Allow some tolerance
        print(f"✅ Sharma: Good coverage ({len(sharma_suktas)} Suktas)")
    else:
        print(f"⚠️  Sharma: Incomplete ({len(sharma_suktas)} Suktas, expected ~1028)")

    if len(griffith_hymns) >= 970:
        print(f"✅ Griffith: Good coverage ({len(griffith_hymns)} Hymns)")
    else:
        print(f"⚠️  Griffith: Incomplete ({len(griffith_hymns)} Hymns, expected ~1028)")

    # 2. Compare Content Quality
    print("\n\n📝 CONTENT QUALITY COMPARISON")
    print("-" * 70)

    print("\n🔍 Extracting proper nouns from Sharma's English version...")
    with open(sharma_file, 'r', encoding='utf-8') as f:
        sharma_text = f.read()
    sharma_nouns = extract_proper_nouns(sharma_text)
    print(f"  Found {len(sharma_nouns)} proper nouns")
    print(f"  Top 10: {', '.join(list(sharma_nouns.keys())[:10])}")

    print("\n🔍 Extracting proper nouns from Griffith's version...")
    with open(griffith_file, 'r', encoding='utf-8') as f:
        griffith_text = f.read()
    griffith_nouns = extract_proper_nouns(griffith_text)
    print(f"  Found {len(griffith_nouns)} proper nouns")
    print(f"  Top 10: {', '.join(list(griffith_nouns.keys())[:10])}")

    # Compare
    print("\n\n🔄 NOUN OVERLAP ANALYSIS")
    print("-" * 70)

    comparison = compare_proper_nouns(sharma_nouns, griffith_nouns)

    print(f"\nCommon proper nouns: {len(comparison['common'])}")
    print(f"Only in Sharma: {len(comparison['sharma_only'])}")
    print(f"Only in Griffith: {len(comparison['griffith_only'])}")
    print(f"\n📊 Overlap: {comparison['overlap_percent']:.1f}%")

    # Quality assessment
    if comparison['overlap_percent'] >= 50:
        print("\n✅ EXCELLENT: High overlap suggests parsing preserved content well")
    elif comparison['overlap_percent'] >= 30:
        print("\n✓ GOOD: Moderate overlap, translations differ but core content similar")
    else:
        print("\n⚠️  LOW: Significant differences, may need parser refinement")

    # Show some common names
    print("\n\nCommon deities/names found in both versions:")
    common_sorted = sorted(comparison['common'],
                          key=lambda x: sharma_nouns[x] + griffith_nouns.get(x, 0),
                          reverse=True)
    for noun in common_sorted[:20]:
        print(f"  • {noun}: Sharma({sharma_nouns[noun]}), Griffith({griffith_nouns.get(noun, 0)})")

    # Show key differences
    print("\n\nKey names only in Sharma (may be transliteration variants):")
    sharma_sorted = sorted(comparison['sharma_only'],
                          key=lambda x: sharma_nouns[x],
                          reverse=True)
    for noun in sharma_sorted[:15]:
        print(f"  • {noun} ({sharma_nouns[noun]} times)")

    print("\n\nKey names only in Griffith:")
    griffith_sorted = sorted(comparison['griffith_only'],
                            key=lambda x: griffith_nouns[x],
                            reverse=True)
    for noun in griffith_sorted[:15]:
        print(f"  • {noun} ({griffith_nouns[noun]} times)")

    # 3. Specific test: Check for "Sudas"/"Sudasa"
    print("\n\n🔍 SPECIFIC TEST: Sudas/Sudasa mentions")
    print("-" * 70)

    sudas_sharma = sharma_text.count('Sudas') + sharma_text.count('Sudasa')
    sudas_griffith = griffith_text.count('Sudas') + griffith_text.count('Sudasa')

    print(f"Sharma mentions: {sudas_sharma}")
    print(f"Griffith mentions: {sudas_griffith}")

    if sudas_sharma > 0 and sudas_griffith > 0:
        print("✅ Both versions contain references to Sudas/Sudasa")
    elif sudas_sharma > 0:
        print("⚠️  Only Sharma contains Sudas/Sudasa (check Griffith extraction)")
    else:
        print("⚠️  Name not found prominently in either version")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"✓ Sharma parsed version has {len(sharma_suktas)} Suktas across {len(sharma_mandala_counts)} Mandalas")
    print(f"✓ Griffith version has {len(griffith_hymns)} Hymns")
    print(f"✓ Proper noun overlap: {comparison['overlap_percent']:.1f}%")
    print(f"✓ Parsing quality: {'EXCELLENT' if comparison['overlap_percent'] >= 50 else 'GOOD' if comparison['overlap_percent'] >= 30 else 'NEEDS REVIEW'}")
    print()

    return 0


if __name__ == '__main__':
    sys.exit(main())
