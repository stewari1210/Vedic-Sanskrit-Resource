#!/usr/bin/env python3
"""Extract proper nouns from Yajurveda markdown file."""

import re
from collections import Counter
import os

def extract_proper_nouns_from_yajurveda():
    """Extract and analyze proper nouns from Yajurveda."""

    # Path to the Yajurveda markdown file
    md_file = 'local_store/ancient_history/yajurveda-griffith/yajurveda-griffith.md'

    if not os.path.exists(md_file):
        print(f"❌ File not found: {md_file}")
        print("Please wait for processing to complete or check the path.")
        return

    print("=" * 70)
    print("EXTRACTING PROPER NOUNS FROM GRIFFITH'S WHITE YAJURVEDA")
    print("=" * 70)

    # Read the markdown file
    with open(md_file, 'r', encoding='utf-8') as f:
        text = f.read()

    print(f"\n📄 Total text length: {len(text):,} characters\n")

    # Extract proper nouns (capitalized words)
    proper_noun_pattern = r'\b[A-Z][a-z]*(?:[A-Z][a-z]*)*\b'
    proper_nouns = re.findall(proper_noun_pattern, text)

    # Count occurrences
    noun_counts = Counter(proper_nouns)

    # Filter out common words
    common_words = {
        'The', 'And', 'In', 'To', 'Of', 'For', 'With', 'By', 'From', 'On', 'At',
        'This', 'That', 'These', 'Those', 'He', 'She', 'It', 'We', 'They', 'Thou',
        'Thee', 'Thy', 'Thine', 'His', 'Her', 'Hers', 'Their', 'Theirs', 'All',
        'Be', 'Is', 'Are', 'Was', 'Were', 'Been', 'Being', 'Have', 'Has', 'Had',
        'Do', 'Does', 'Did', 'Will', 'Would', 'Shall', 'Should', 'May', 'Might',
        'Can', 'Could', 'Must', 'Ought', 'Let', 'But', 'Or', 'As', 'If', 'When',
        'Where', 'Why', 'How', 'What', 'Which', 'Who', 'Whom', 'Whose', 'A', 'An',
        'HYMN', 'Hymn', 'Book', 'Chapter', 'Verse', 'Page', 'Lord', 'God', 'Gods',
        'O', 'Ye', 'My', 'Me', 'I', 'Our', 'Us', 'Your', 'You', 'Him', 'Some',
        'Such', 'So', 'Not', 'Now', 'Then', 'Here', 'There', 'Thus', 'Yet', 'Still',
        'BOOK', 'Book', 'Contents', 'CONTENTS'
    }

    # Filter and get proper nouns with at least 5 occurrences
    # Also filter out single-letter words (like 'R', 'S', etc.)
    filtered_nouns = {k: v for k, v in noun_counts.items()
                      if k not in common_words and v >= 5 and len(k) > 1}

    # Sort by frequency
    sorted_nouns = sorted(filtered_nouns.items(), key=lambda x: x[1], reverse=True)

    print(f"✅ Total unique proper nouns (≥5 occurrences): {len(sorted_nouns)}\n")
    print(f"Top 100 proper nouns in Yajurveda:\n")
    print(f"{'Rank':<6} {'Proper Noun':<30} {'Occurrences':<12}")
    print("=" * 50)

    for i, (noun, count) in enumerate(sorted_nouns[:100], 1):
        print(f"{i:<6} {noun:<30} {count:<12}")

    # Save full list
    output_file = 'proper_nouns_yajurveda.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Proper Nouns in Griffith's White Yajurveda (≥5 occurrences)\n")
        f.write(f"Total: {len(sorted_nouns)}\n")
        f.write("=" * 60 + "\n\n")
        for noun, count in sorted_nouns:
            f.write(f"{noun}: {count}\n")

    print(f"\n✅ Full list saved to: {output_file}")

    # Identify geographical/location-specific proper nouns
    print("\n" + "=" * 70)
    print("IDENTIFYING GEOGRAPHICAL/LOCATION-SPECIFIC PROPER NOUNS")
    print("=" * 70)

    # Keywords that suggest geographical terms
    geo_keywords = ['river', 'mountain', 'hill', 'region', 'land', 'place',
                   'city', 'town', 'village', 'bank', 'shore', 'dwell', 'lived']

    # Common geographical terms from Rigveda analysis
    known_locations = [
        'Sarasvati', 'Sindhu', 'Indus', 'Rasa', 'Yamuna', 'Ganga',
        'Vipas', 'Parushni', 'Sutudri', 'Arjikiya', 'Susoma',
        'Mujavat', 'Himavat', 'Trikakud'
    ]

    # Find geographical proper nouns
    geographical_nouns = []
    for noun, count in sorted_nouns:
        if noun in known_locations:
            geographical_nouns.append((noun, count, 'Known location from Rigveda'))

    # Search for context around other proper nouns
    for noun, count in sorted_nouns[:200]:  # Check top 200
        if noun not in known_locations and noun not in [g[0] for g in geographical_nouns]:
            # Search for geographical context
            pattern = rf'\b{noun}\b.{{0,50}}(?:{"|".join(geo_keywords)})'
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                geographical_nouns.append((noun, count, f'Context: {len(matches)} geographical refs'))

    if geographical_nouns:
        print(f"\n✅ Found {len(geographical_nouns)} geographical proper nouns:\n")
        print(f"{'Proper Noun':<30} {'Count':<10} {'Note':<40}")
        print("=" * 80)
        for noun, count, note in sorted(geographical_nouns, key=lambda x: x[1], reverse=True):
            print(f"{noun:<30} {count:<10} {note:<40}")
    else:
        print("\n⚠️  No obvious geographical proper nouns found in top entries")

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE!")
    print("=" * 70)

if __name__ == "__main__":
    extract_proper_nouns_from_yajurveda()
