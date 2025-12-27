#!/usr/bin/env python3
"""
Parser for Griffith's Rigveda translation - extracts proper nouns and adds metadata.
Griffith's format includes:
- Hymn headers: [10-102] HYMN CII. Indra.
- Numbered verses: 1. FOR thee may Indra...
- Page markers: ## Page 478 <478>
- Historical references and literal translations
"""

import re
from collections import defaultdict, Counter

# Comprehensive proper noun patterns
PROPER_NOUN_PATTERNS = {
    # Deities - exact matches
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

    # Sages/Rishis - spelling variants
    'sages': [
        'Vasistha', 'Vasishtha', 'Vasisṭha', 'Visvamitra', 'Viśvāmitra', 'Vishvamitra',
        'Bharadvaja', 'Bharadvāja', 'Bharadvija', 'Atri', 'Gotama', 'Gautama',
        'Kasyapa', 'Kashyapa', 'Kaśyapa', 'Kanva', 'Kāṇva', 'Grtsamada', 'Gṛtsamada',
        'Angirasa', 'Aṅgirasa', 'Agastya', 'Jamadagni', 'Jāmadagni',
        'Kutsa', 'Trasadasyu', 'Trāsadasyu', 'Kakshivat', 'Kakṣīvat',
        'Rjrasva', 'Rijrāśva', 'Dirghatamas', 'Dīrghatamas', 'Nodhas', 'Nodha',
        'Upastutas', 'Vrstihavya', 'Vṛṣṭihavya', 'Medhatithi', 'Medhātithi',
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

    # Special concepts (when capitalized in Griffith)
    'concepts': [
        'Rathantara', 'Brhat', 'Bṛhat', 'Gayatri', 'Gāyatrī', 'Tristup', 'Triṣṭup',
        'Jagati', 'Jāgatī', 'Viraj', 'Virāj', 'Anustup', 'Anuṣṭup', 'Usnig', 'Uṣṇig',
        'Yajus', 'Saman', 'Sāman', 'Uktha', 'Mantra', 'Veda', 'Soma'
    ]
}

# Flatten all proper nouns for quick lookup
ALL_PROPER_NOUNS = set()
for category, nouns in PROPER_NOUN_PATTERNS.items():
    ALL_PROPER_NOUNS.update(nouns)


def is_hymn_header(line):
    """Check if line is a hymn header like [10-102] HYMN CII. Indra."""
    return bool(re.match(r'\[\d+-\d+\]\s+HYMN\s+[IVXLCDM]+\.', line))


def is_page_marker(line):
    """Check if line is a page marker like ## Page 478 <478>"""
    return bool(re.match(r'^##\s+Page\s+\d+', line))


def extract_proper_nouns_from_text(text):
    """Extract proper nouns from text using word boundary matching."""
    found_nouns = set()

    # Use word boundaries to match complete words only
    words = re.findall(r'\b[A-Z][a-zāīūṛṣṭḍṅñṃḥśṇ]*\b', text)

    for word in words:
        # Check exact match first
        if word in ALL_PROPER_NOUNS:
            found_nouns.add(word)
            continue

        # Check case-insensitive match for variants
        word_lower = word.lower()
        for proper_noun in ALL_PROPER_NOUNS:
            if proper_noun.lower() == word_lower:
                found_nouns.add(proper_noun)
                break

    return sorted(found_nouns)


def parse_griffith_rigveda(input_file, output_file):
    """
    Parse Griffith's Rigveda and add proper noun metadata with source tags.
    """
    print("=" * 70)
    print("PARSING GRIFFITH'S RIGVEDA WITH METADATA EXTRACTION")
    print("=" * 70)

    # Read entire file and split on hymn markers
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"\nFile size: {len(content):,} characters")

    # Split content into lines manually (file has no line terminators)
    # Split on hymn markers first, then process
    lines = []
    current_line = ''
    for char in content:
        if char == '\n':
            if current_line:
                lines.append(current_line)
            current_line = ''
        else:
            current_line += char
    if current_line:
        lines.append(current_line)

    # If still only one line, try splitting on common markers
    if len(lines) <= 1:
        print("  File has no newlines - splitting on hymn markers...")
        # Split on hymn markers like [10-102] HYMN
        parts = re.split(r'(\[\d+-\d+\]\s+HYMN\s+[IVXLCDM]+\.)', content)
        lines = []
        for part in parts:
            if part.strip():
                lines.append(part.strip())

    total_lines = len(lines)
    print(f"Total segments to process: {total_lines:,}")    # Parse into hymns
    hymns = []
    current_hymn = None
    current_text = []
    hymn_count = 0

    for line in lines:
        line = line.strip()

        if not line:
            if current_text:
                current_text.append('')
            continue

        # Check for hymn header
        if is_hymn_header(line):
            # Save previous hymn
            if current_hymn and current_text:
                hymns.append({
                    'header': current_hymn,
                    'text': '\n'.join(current_text)
                })

            current_hymn = line
            current_text = []
            hymn_count += 1
            continue

        # Skip page markers
        if is_page_marker(line):
            continue

        # Accumulate text
        if current_hymn:
            current_text.append(line)

    # Save last hymn
    if current_hymn and current_text:
        hymns.append({
            'header': current_hymn,
            'text': '\n'.join(current_text)
        })

    print(f"\nFound {len(hymns)} hymns")

    # Process each hymn and add metadata
    output_lines = []
    total_proper_nouns = 0
    proper_noun_counter = Counter()
    hymns_with_metadata = 0

    print("\nProcessing hymns and extracting proper nouns...")

    for i, hymn in enumerate(hymns, 1):
        if i % 100 == 0:
            print(f"  Processed {i}/{len(hymns)} hymns...")

        header = hymn['header']
        text = hymn['text']

        # Extract proper nouns from entire hymn
        proper_nouns = extract_proper_nouns_from_text(header + ' ' + text)

        # Write hymn header
        output_lines.append(header)
        output_lines.append('')

        # Add metadata line with source tag if proper nouns found
        if proper_nouns:
            metadata_line = f"[Names (Griffith-Rigveda): {', '.join(proper_nouns)}]"
            output_lines.append(metadata_line)
            output_lines.append('')
            hymns_with_metadata += 1
            total_proper_nouns += len(proper_nouns)
            proper_noun_counter.update(proper_nouns)

        # Add hymn text
        output_lines.append(text)
        output_lines.append('')
        output_lines.append('-' * 70)
        output_lines.append('')

    # Write output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))

    # Statistics
    print("\n" + "=" * 70)
    print("PARSING COMPLETE")
    print("=" * 70)
    print(f"\nTotal hymns: {len(hymns)}")
    print(f"Hymns with metadata: {hymns_with_metadata}")
    print(f"Total proper nouns extracted: {total_proper_nouns}")
    print(f"Unique proper nouns: {len(proper_noun_counter)}")

    print("\n\nTop 20 Most Frequent Proper Nouns:")
    print("-" * 50)
    for noun, count in proper_noun_counter.most_common(20):
        print(f"  {noun:25} {count:>5} occurrences")

    # Check for key entities
    print("\n\nKey Historical Entities (if found):")
    print("-" * 50)
    key_entities = ['Bharatas', 'Bharata', 'Purus', 'Puru', 'Sudas', 'Vasistha',
                    'Vasishtha', 'Mudgala', 'Trtsus', 'Divodasa']
    for entity in key_entities:
        if entity in proper_noun_counter:
            print(f"  {entity:25} {proper_noun_counter[entity]:>5} occurrences")

    print(f"\nOutput written to: {output_file}")
    print("=" * 70)

    return {
        'total_hymns': len(hymns),
        'hymns_with_metadata': hymns_with_metadata,
        'total_proper_nouns': total_proper_nouns,
        'unique_proper_nouns': len(proper_noun_counter),
        'top_nouns': proper_noun_counter.most_common(20)
    }


if __name__ == '__main__':
    input_file = '/Users/shivendratewari/github/RAG-CHATBOT-CLI-Version/local_store/ancient_history/griffith-rigveda/griffith-rigveda.md'
    output_file = '/Users/shivendratewari/github/RAG-CHATBOT-CLI-Version/griffith-rigveda_COMPLETE_english_with_metadata.txt'

    stats = parse_griffith_rigveda(input_file, output_file)
