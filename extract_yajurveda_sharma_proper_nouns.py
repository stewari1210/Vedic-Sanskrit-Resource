#!/usr/bin/env python3
"""
Extract proper nouns from Sharma/Tulsi Ram's Yajurveda translation
and identify geographical/location-specific terms.
"""

import re
from collections import Counter
import os

def extract_proper_nouns(markdown_file_path):
    """Extract and analyze proper nouns from the Yajurveda markdown."""

    print("=" * 70)
    print("EXTRACTING PROPER NOUNS FROM SHARMA'S YAJURVEDA")
    print("=" * 70)
    print()

    # Check if file exists
    if not os.path.exists(markdown_file_path):
        print(f"❌ Error: File not found: {markdown_file_path}")
        return

    # Read the markdown file
    with open(markdown_file_path, 'r', encoding='utf-8') as f:
        text = f.read()

    print(f"📄 Total text length: {len(text):,} characters")
    print()

    # Pattern to match capitalized words (proper nouns)
    # Matches single capitalized word or multi-word proper nouns
    pattern = r'\b[A-Z][a-z]*(?:[A-Z][a-z]*)*\b'

    # Find all matches
    proper_nouns = re.findall(pattern, text)

    # Count occurrences
    noun_counts = Counter(proper_nouns)

    # Common words to filter out (not proper nouns)
    common_words = {
        'The', 'This', 'That', 'These', 'Those', 'And', 'But', 'Or', 'For', 'With',
        'From', 'To', 'In', 'On', 'At', 'By', 'As', 'Of', 'A', 'An',
        'He', 'She', 'It', 'They', 'We', 'You', 'I', 'Me', 'Him', 'Her',
        'His', 'Their', 'Our', 'Your', 'My', 'Its',
        'God', 'Lord', 'Gods', 'Hymn', 'Verse', 'Book', 'Text', 'Page',
        'May', 'Let', 'Shall', 'Will', 'Can', 'Must', 'Should', 'Would',
        'All', 'Some', 'Many', 'Few', 'Each', 'Every', 'Both', 'Either',
        'Neither', 'None', 'One', 'Two', 'Three', 'Four', 'Five',
        'Now', 'Then', 'When', 'Where', 'Why', 'How', 'What', 'Which', 'Who',
        'Yes', 'No', 'Not', 'Never', 'Always', 'Often', 'Sometimes'
    }

    # Filter: exclude common words, require at least 5 occurrences, and exclude single letters
    filtered_nouns = {k: v for k, v in noun_counts.items()
                      if k not in common_words and v >= 5 and len(k) > 1}

    # Sort by frequency
    sorted_nouns = sorted(filtered_nouns.items(), key=lambda x: x[1], reverse=True)

    print(f"✅ Total unique proper nouns (≥5 occurrences): {len(sorted_nouns)}")
    print()

    # Display top 100
    print("Top 100 proper nouns in Sharma's Yajurveda:")
    print()
    print(f"{'Rank':<7}{'Proper Noun':<30}{'Occurrences':<12}")
    print("=" * 50)

    for i, (noun, count) in enumerate(sorted_nouns[:100], 1):
        print(f"{i:<7}{noun:<30}{count:<12}")

    # Save full list to file
    output_file = 'proper_nouns_yajurveda_sharma.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("Proper Nouns in Sharma's Yajurveda (≥5 occurrences)\n")
        f.write(f"Total: {len(sorted_nouns)}\n")
        f.write("=" * 60 + "\n\n")
        for noun, count in sorted_nouns:
            f.write(f"{noun}: {count}\n")

    print()
    print(f"✅ Full list saved to: {output_file}")
    print()

    # Geographical/location analysis
    print("=" * 70)
    print("IDENTIFYING GEOGRAPHICAL/LOCATION-SPECIFIC PROPER NOUNS")
    print("=" * 70)
    print()

    # Known geographical terms from Rigveda (rivers, mountains, regions, tribes)
    rigveda_locations = {
        'Sarasvati', 'Sindhu', 'Indus', 'Ganga', 'Yamuna', 'Sutudri', 'Vipas',
        'Parushni', 'Asikni', 'Vitasta', 'Arjikiya', 'Susoma',
        'Himalaya', 'Mujavat', 'Trikakubh',
        'Bharata', 'Puru', 'Turvasas', 'Yadu', 'Anu', 'Druhyu',
        'Pakthas', 'Bhalanas', 'Alinas', 'Vishanins', 'Sivas',
        'Tritsu', 'Simyus', 'Ikshvaku',
        'Kurukshetra', 'Sapta', 'Sindhu'
    }

    # Terms that might indicate geographical references
    geo_indicators = [
        'river', 'mountain', 'hill', 'land', 'region', 'country',
        'tribe', 'people', 'folk', 'nation', 'kingdom',
        'east', 'west', 'north', 'south', 'beyond', 'across'
    ]

    # Find proper nouns that appear in geographical contexts
    geographical_nouns = []

    for noun, count in sorted_nouns:
        # Check if it's a known location from Rigveda
        if noun in rigveda_locations:
            geographical_nouns.append((noun, count, "Known location from Rigveda"))
            continue

        # Search for contexts where this noun appears with geographical indicators
        contexts = []
        pattern = rf'\b{re.escape(noun)}\b.{{0,100}}'  # noun + 100 chars context
        matches = re.finditer(pattern, text, re.IGNORECASE)

        for match in matches:
            context = match.group().lower()
            for indicator in geo_indicators:
                if indicator in context:
                    contexts.append(context[:50])
                    break

        if contexts:
            geographical_nouns.append((noun, count, f"Context: {len(contexts)} geographical refs"))

    print(f"✅ Found {len(geographical_nouns)} geographical proper nouns:")
    print()
    print(f"{'Proper Noun':<30}{'Count':<11}{'Note':<40}")
    print("=" * 80)

    for noun, count, note in geographical_nouns[:100]:  # Show top 100
        print(f"{noun:<30}{count:<11}{note:<40}")

    # Save geographical nouns
    geo_output_file = 'geographical_nouns_yajurveda_sharma.txt'
    with open(geo_output_file, 'w', encoding='utf-8') as f:
        f.write("Geographical Proper Nouns in Sharma's Yajurveda\n")
        f.write(f"Total: {len(geographical_nouns)}\n")
        f.write("=" * 60 + "\n\n")
        for noun, count, note in geographical_nouns:
            f.write(f"{noun} (count: {count}) - {note}\n")

    print()
    print(f"✅ Geographical nouns saved to: {geo_output_file}")
    print()
    print("=" * 70)
    print("ANALYSIS COMPLETE!")
    print("=" * 70)


if __name__ == "__main__":
    # Path to the Yajurveda markdown file
    markdown_path = "local_store/ancient_history/yajurveda-sharma/yajurveda-sharma.md"
    extract_proper_nouns(markdown_path)
