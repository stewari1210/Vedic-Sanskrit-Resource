#!/usr/bin/env python3
"""
Improved parser: Extract English + preserve transliteration lines with proper nouns.

Strategy:
- Extract all English translations (as before)
- Keep transliteration lines that contain important proper nouns
- These lines help RAG find specific names even when English is descriptive
"""

import re
from pathlib import Path


# Important Vedic proper nouns to preserve in transliteration
IMPORTANT_NAMES = {
    # Kings and heroes
    'Sudas', 'Sudasa', 'Sudase', 'Sudasam',
    'Trasadasyu', 'Divodasa', 'Purukutsa', 'Kutsa',
    'Atithigva', 'Pratardana', 'Rijisvan',

    # Sages (Rishis)
    'Vasishtha', 'Vasistha', 'Visvamitra', 'Vishvamitra',
    'Bharadvaja', 'Atri', 'Kanva', 'Gritsamada',
    'Vamadeva', 'Gotama', 'Angirasa', 'Bhrgu',

    # Tribes and peoples
    'Bharata', 'Puru', 'Tritsu', 'Turv', 'Yadu',
    'Anu', 'Druhyu', 'Paijavana',

    # Rivers
    'Sarasvati', 'Saraswati', 'Sindhu', 'Ganga', 'Yamuna',
    'Parusni', 'Vipas', 'Sutudri',

    # Demons/Enemies
    'Vrtra', 'Vala', 'Susna', 'Dhuni', 'Cumuri',
    'Pipru', 'Namuci', 'Sambara',

    # Places
    'Kurukshetra', 'Hariyupiya',
}


def is_devanagari_line(line):
    """Check if line contains Devanagari script."""
    devanagari_pattern = re.compile(r'[\u0900-\u097F]')
    return bool(devanagari_pattern.search(line))


def contains_important_name(line, names_set):
    """Check if line contains any important proper noun."""
    line_lower = line.lower()
    for name in names_set:
        # Case-insensitive match
        if name.lower() in line_lower:
            return True
    return False


def is_transliteration_line(line):
    """Check if line is Roman transliteration of Sanskrit."""
    line = line.strip()
    if not line:
        return False

    # Check for verse number pattern
    if re.match(r'^\d+\s+[A-Z]', line):
        content = re.sub(r'^\d+\s+', '', line)
        if re.search(r'[aeiou]{2}', content) or content.count('-') >= 2:
            return True

    # Skip if clearly English
    common_english = [
        'the', 'and', 'of', 'to', 'in', 'with', 'for', 'is', 'are', 'was', 'were',
        'that', 'this', 'which', 'who', 'when', 'where', 'what', 'how', 'from', 'by'
    ]
    line_lower = line.lower()
    if any(f' {word} ' in f' {line_lower} ' for word in common_english):
        return False

    # Transliteration indicators
    indicators = [
        line.count('-') >= 3,
        line.count('-') >= 1 and line.endswith('.'),
        bool(re.search(r'\b[A-Z][a-z]+[aeiou]{2}', line)),
        bool(re.search(r'[bdfghjklmnprstvwy]{2,3}', line.lower())),
        line.endswith('.') and line[0].isupper() and len(line.split()) <= 8,
        bool(re.search(r'[a-z]{15,}', line)),
        bool(re.search(r'\b[a-z]+dh[a-z]+', line.lower())),
        bool(re.search(r'\b[a-z]+ya[nm]\b', line.lower())),
        bool(re.search(r'\b[a-z]+t[vw]am\b', line.lower())),
        bool(re.search(r'\b[Ss]udasa?\b|\b[Ii]ndrah?\b|\bindra[^c]', line)),
        len(line.split()) <= 10 and not any(x in line.lower() for x in [' of ', ' the ', ' and ', ' that ']),
    ]

    return sum(indicators) >= 2


def is_metadata_line(line):
    """Check if line is metadata."""
    line = line.strip()
    metadata_patterns = [
        r'^Mandala\s+\d+',
        r'^MANDAL\s*-?\s*\d+',
        r'^Sukta\s+\d+',
        r'^SUKTA\s*-?\s*\d+',
        r'Devata',
        r'Rshi',
        r'^\d+\s+[A-Z]+VEDA',
        r'^Page\s+\d+',
    ]
    return any(re.search(pattern, line, re.IGNORECASE) for pattern in metadata_patterns)


def parse_sharma_hybrid(input_file, output_file, verify_mode=False):
    """Parse Sharma's translation: Extract English + keep name-bearing transliterations."""

    input_path = Path(input_file)
    if not input_path.exists():
        print(f"❌ Error: File not found: {input_file}")
        return None

    if output_file is None:
        output_file = input_path.parent / f"{input_path.stem}_hybrid.txt"

    output_path = Path(output_file)

    print("=" * 70)
    print("HYBRID PARSING: English + Name-Bearing Transliterations")
    print("=" * 70)
    print(f"📄 Input: {input_file}")
    print(f"📝 Output: {output_file}")
    print()

    # Statistics
    stats = {
        'total_lines': 0,
        'devanagari_lines': 0,
        'transliteration_lines': 0,
        'transliteration_with_names': 0,
        'english_lines': 0,
        'metadata_lines': 0,
        'empty_lines': 0,
    }

    output_lines = []
    discarded_lines = [] if verify_mode else None

    with open(input_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            stats['total_lines'] += 1
            stripped = line.strip()

            if not stripped:
                stats['empty_lines'] += 1
                output_lines.append('')
                continue

            # Check line type
            if is_devanagari_line(stripped):
                stats['devanagari_lines'] += 1
                if verify_mode:
                    discarded_lines.append(f"[DEVANAGARI {line_num}] {stripped[:100]}")
                continue

            if is_metadata_line(stripped):
                stats['metadata_lines'] += 1
                output_lines.append(stripped)
                continue

            if is_transliteration_line(stripped):
                stats['transliteration_lines'] += 1

                # Check if it contains important names
                if contains_important_name(stripped, IMPORTANT_NAMES):
                    stats['transliteration_with_names'] += 1
                    output_lines.append(stripped)
                    print(f"  ✓ Preserved: {stripped[:80]}...")
                else:
                    if verify_mode:
                        discarded_lines.append(f"[TRANSLITERATION {line_num}] {stripped[:100]}")
                continue

            # Otherwise, assume English
            stats['english_lines'] += 1
            output_lines.append(stripped)

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))

    # Write discarded if verify mode
    if verify_mode and discarded_lines:
        discard_path = output_path.parent / f"{output_path.stem}_discarded.txt"
        with open(discard_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(discarded_lines))
        print(f"\n🔍 Discarded lines saved to: {discard_path}")

    print("\n✅ Parsing complete!")

    # Print statistics
    input_size = input_path.stat().st_size
    output_size = output_path.stat().st_size

    print("\n" + "=" * 70)
    print("STATISTICS")
    print("=" * 70)
    print(f"Total lines:           {stats['total_lines']:,}")
    print(f"  - English:           {stats['english_lines']:,} ({stats['english_lines']/stats['total_lines']*100:.1f}%)")
    print(f"  - Devanagari:        {stats['devanagari_lines']:,} ({stats['devanagari_lines']/stats['total_lines']*100:.1f}%)")
    print(f"  - Transliteration:   {stats['transliteration_lines']:,} ({stats['transliteration_lines']/stats['total_lines']*100:.1f}%)")
    print(f"    • With names:      {stats['transliteration_with_names']:,} (PRESERVED)")
    print(f"    • Without names:   {stats['transliteration_lines'] - stats['transliteration_with_names']:,} (filtered)")
    print(f"  - Metadata:          {stats['metadata_lines']:,} ({stats['metadata_lines']/stats['total_lines']*100:.1f}%)")
    print(f"  - Empty:             {stats['empty_lines']:,} ({stats['empty_lines']/stats['total_lines']*100:.1f}%)")
    print()
    print(f"Input size:  {input_size:,} bytes ({input_size/1024/1024:.2f} MB)")
    print(f"Output size: {output_size:,} bytes ({output_size/1024/1024:.2f} MB)")
    print(f"Reduction:   {(1 - output_size/input_size)*100:.1f}% smaller")
    print("=" * 70)

    return stats


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Parse Sharma Rigveda: Extract English + preserve name-bearing transliterations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python parse_sharma_hybrid.py rigveda-sharma.txt
  python parse_sharma_hybrid.py rigveda-sharma.txt --verify
  python parse_sharma_hybrid.py rigveda-sharma.txt -o rigveda_clean.txt
        """
    )

    parser.add_argument('input_file', help='Input file (Sharma Rigveda/Yajurveda)')
    parser.add_argument('-o', '--output', dest='output_file',
                       help='Output file (default: input_hybrid.txt)')
    parser.add_argument('--verify', action='store_true',
                       help='Save discarded lines for verification')

    args = parser.parse_args()

    parse_sharma_hybrid(args.input_file, args.output_file, args.verify)


if __name__ == '__main__':
    main()
