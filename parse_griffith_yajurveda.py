#!/usr/bin/env python3
"""
Parser for Griffith's Yajurveda translation - extracts proper nouns and adds metadata.
Griffith's Yajurveda format is more prose-like with verse numbers.
"""

import re
from collections import defaultdict, Counter

# Comprehensive proper noun patterns (same as Rigveda + Yajurveda specific)
PROPER_NOUN_PATTERNS = {
    # Deities
    'deities': [
        'Indra', 'Agni', 'Soma', 'Varuna', 'Mitra', 'Surya', 'Usas', 'Rudra',
        'Vishnu', 'Visnu', 'Pushan', 'Pusan', 'Vayu', 'Vata', 'Maruts', 'Asvins',
        'Aśvins', 'Rbhus', 'Rsis', 'Vasus', 'Adityas', 'Angirases',
        'Brhaspati', 'Brihaspati', 'Tvastar', 'Tvashtar', 'Savitar', 'Savitri',
        'Prajapati', 'Yama', 'Parjanya', 'Aryaman', 'Bhaga', 'Daksa',
        'Aditi', 'Sarasvati', 'Saraswati', 'Ila', 'Bharati', 'Sinivali',
        'Dyaus', 'Prthivi', 'Prithivi', 'Vrtra', 'Vṛtra', 'Ahi',
        'Gandharva', 'Apsaras', 'Apsarases', 'Raksasas', 'Asura', 'Asuras',
        'Dasa', 'Dasyu', 'Dasyus', 'Dawn', 'Sun', 'Moon'
    ],

    # Sages/Rishis
    'sages': [
        'Vasistha', 'Vasishtha', 'Vasisṭha', 'Visvamitra', 'Viśvāmitra', 'Vishvamitra',
        'Bharadvaja', 'Bharadvāja', 'Bharadvija', 'Atri', 'Gotama', 'Gautama',
        'Kasyapa', 'Kashyapa', 'Kaśyapa', 'Kanva', 'Kāṇva', 'Grtsamada', 'Gṛtsamada',
        'Angirasa', 'Aṅgirasa', 'Agastya', 'Jamadagni', 'Jāmadagni',
        'Kutsa', 'Trasadasyu', 'Trāsadasyu', 'Kakshivat', 'Kakṣīvat',
        'Rjrasva', 'Rijrāśva', 'Dirghatamas', 'Dīrghatamas', 'Nodhas', 'Nodha',
        'Upastutas', 'Vrstihavya', 'Vṛṣṭihavya', 'Medhatithi', 'Medhātithi',
        'Yajnavalkya', 'Yājñavalkya', 'Yagnavalkya',
        'Nahusa', 'Nahuṣa', 'Navagvas', 'Navagva', 'Rbhuksan', 'Ṛbhukṣan',
        'Rsi', 'Ṛṣi', 'Rsis', 'Ṛṣis'
    ],

    # Kings and Heroes
    'kings_heroes': [
        'Sudas', 'Sudāsa', 'Sudāsas', 'Divodasa', 'Divódāsa', 'Pijavana',
        'Trasadasyu', 'Purukutsa', 'Mudgala', 'Mudgalani', 'Mudgalāni',
        'Prthu', 'Pṛthu', 'Prithu', 'Nahusa', 'Kavi', 'Turvasa', 'Turvaśa',
        'Druhyu', 'Anu', 'Yadu', 'Parikshit', 'Parīkṣit', 'Janamejaya'
    ],

    # Tribes and Clans
    'tribes': [
        'Bharatas', 'Bharata', 'Purus', 'Puru', 'Trtsus', 'Tṛtsus', 'Tritsu',
        'Turvasas', 'Turvaśas', 'Druhyus', 'Yadus', 'Anus',
        'Pakthas', 'Bhalanas', 'Alinas', 'Sivas', 'Visanins', 'Viṣāṇins',
        'Bharadvaja', 'Kurus', 'Panchalas', 'Pañcālas', 'Srñjayas', 'Śṛñjayas',
        'Ikshvaku', 'Ikṣvāku', 'Nahusa', 'Aila', 'Kanva'
    ],

    # Places and Rivers
    'places': [
        'Sindhu', 'Sarasvati', 'Sarasvatī', 'Ganga', 'Gaṅgā', 'Yamuna', 'Yamunā',
        'Rasa', 'Kubha', 'Krumu', 'Gomati', 'Parushni', 'Paruṣṇī',
        'Sarayu', 'Vipas', 'Vipāś', 'Sutudri', 'Śutudrī'
    ],

    # Special concepts
    'concepts': [
        'Rathantara', 'Brhat', 'Bṛhat', 'Gayatri', 'Gāyatrī', 'Tristup', 'Triṣṭup',
        'Jagati', 'Jāgatī', 'Viraj', 'Virāj', 'Anustup', 'Anuṣṭup', 'Usnig', 'Uṣṇig',
        'Yajus', 'Saman', 'Sāman', 'Uktha', 'Mantra', 'Veda', 'Soma',
        'Brahman', 'Brahmana'
    ]
}

# Flatten all proper nouns
ALL_PROPER_NOUNS = set()
for category, nouns in PROPER_NOUN_PATTERNS.items():
    ALL_PROPER_NOUNS.update(nouns)


def is_verse_marker(line):
    """Check if line is a verse marker like '1.' or '10.'"""
    return bool(re.match(r'^\d+\.\s+', line.strip()))


def is_book_header(line):
    """Check if line is a book header like 'BOOK I.' or 'CHAPTER'"""
    return bool(re.match(r'^(BOOK|CHAPTER|ADHYAYA)\s+[IVXLCDM]+', line.strip(), re.IGNORECASE))


def extract_proper_nouns_from_text(text):
    """Extract proper nouns from text."""
    found_nouns = set()

    # Use word boundaries
    words = re.findall(r'\b[A-Z][a-zāīūṛṣṭḍṅñṃḥśṇ]*\b', text)

    for word in words:
        if word in ALL_PROPER_NOUNS:
            found_nouns.add(word)
            continue

        # Case-insensitive check
        word_lower = word.lower()
        for proper_noun in ALL_PROPER_NOUNS:
            if proper_noun.lower() == word_lower:
                found_nouns.add(proper_noun)
                break

    return sorted(found_nouns)


def parse_griffith_yajurveda(input_file, output_file):
    """
    Parse Griffith's Yajurveda and add proper noun metadata with source tags.
    """
    print("=" * 70)
    print("PARSING GRIFFITH'S YAJURVEDA WITH METADATA EXTRACTION")
    print("=" * 70)

    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    total_lines = len(lines)
    print(f"\nTotal lines to process: {total_lines:,}")

    # Group into verses/sections
    verses = []
    current_verse = []
    verse_count = 0
    in_content = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Skip front matter (title page, contents, etc.)
        if not in_content:
            if 'BOOK I' in stripped or 'Adhyaya I' in stripped:
                in_content = True
            continue

        if not stripped:
            continue

        # Check for verse marker
        if is_verse_marker(stripped):
            # Save previous verse
            if current_verse:
                verses.append('\n'.join(current_verse))
            current_verse = [stripped]
            verse_count += 1
        # Check for book/chapter headers
        elif is_book_header(stripped):
            if current_verse:
                verses.append('\n'.join(current_verse))
            current_verse = [stripped]
        else:
            # Accumulate text
            if current_verse or in_content:
                current_verse.append(stripped)

    # Save last verse
    if current_verse:
        verses.append('\n'.join(current_verse))

    print(f"Found {len(verses)} verse sections")

    # Process verses and add metadata
    output_lines = []
    total_proper_nouns = 0
    proper_noun_counter = Counter()
    verses_with_metadata = 0

    print("\nProcessing verses and extracting proper nouns...")

    for i, verse_text in enumerate(verses, 1):
        if i % 100 == 0:
            print(f"  Processed {i}/{len(verses)} verses...")

        # Extract proper nouns
        proper_nouns = extract_proper_nouns_from_text(verse_text)

        # Get first line as header (verse number or section title)
        first_line = verse_text.split('\n')[0] if '\n' in verse_text else verse_text[:100]

        # Write verse header if it's a verse number
        if is_verse_marker(first_line):
            output_lines.append(first_line)
            output_lines.append('')

        # Add metadata if proper nouns found
        if proper_nouns:
            metadata_line = f"[Names (Griffith-Yajurveda): {', '.join(proper_nouns)}]"
            output_lines.append(metadata_line)
            output_lines.append('')
            verses_with_metadata += 1
            total_proper_nouns += len(proper_nouns)
            proper_noun_counter.update(proper_nouns)

        # Add verse text
        output_lines.append(verse_text)
        output_lines.append('')
        output_lines.append('-' * 70)
        output_lines.append('')

    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))

    # Statistics
    print("\n" + "=" * 70)
    print("PARSING COMPLETE")
    print("=" * 70)
    print(f"\nTotal verses: {len(verses)}")
    print(f"Verses with metadata: {verses_with_metadata}")
    print(f"Total proper nouns extracted: {total_proper_nouns}")
    print(f"Unique proper nouns: {len(proper_noun_counter)}")

    print("\n\nTop 20 Most Frequent Proper Nouns:")
    print("-" * 50)
    for noun, count in proper_noun_counter.most_common(20):
        print(f"  {noun:25} {count:>5} occurrences")

    # Check for key entities
    print("\n\nKey Historical Entities (if found):")
    print("-" * 50)
    key_entities = ['Bharatas', 'Bharata', 'Purus', 'Puru', 'Kurus', 'Panchalas',
                    'Vasistha', 'Vasishtha', 'Yajnavalkya', 'Bharadvaja']
    for entity in key_entities:
        if entity in proper_noun_counter:
            print(f"  {entity:25} {proper_noun_counter[entity]:>5} occurrences")

    print(f"\nOutput written to: {output_file}")
    print("=" * 70)

    return {
        'total_verses': len(verses),
        'verses_with_metadata': verses_with_metadata,
        'total_proper_nouns': total_proper_nouns,
        'unique_proper_nouns': len(proper_noun_counter),
        'top_nouns': proper_noun_counter.most_common(20)
    }


if __name__ == '__main__':
    input_file = '/Users/shivendratewari/github/RAG-CHATBOT-CLI-Version/yajurveda-griffith.txt'
    output_file = '/Users/shivendratewari/github/RAG-CHATBOT-CLI-Version/yajurveda-griffith_COMPLETE_english_with_metadata.txt'

    stats = parse_griffith_yajurveda(input_file, output_file)
