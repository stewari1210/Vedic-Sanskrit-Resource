#!/usr/bin/env python3
"""
Parse Sharma's Veda translations to extract English-only text.

Sharma's format has 3 layers per verse:
1. Devanagari Sanskrit: त्वे ह यत्पितरज्चिन्न इन्द्र...
2. Transliterated Sanskrit: Tve ha yat pitarascinna indra...
3. English Translation: When Indra, generous ruler...

This script extracts ONLY the English translations, discarding Sanskrit and transliteration.
"""

import re
import sys
from pathlib import Path


def is_devanagari_line(line):
    """Check if line contains Devanagari script."""
    # Devanagari Unicode range: U+0900 to U+097F
    devanagari_pattern = re.compile(r'[\u0900-\u097F]')
    return bool(devanagari_pattern.search(line))


def is_transliteration_line(line):
    """Check if line is Roman transliteration of Sanskrit.

    Characteristics:
    - Starts with capital letter or number
    - Contains Sanskrit-style words (long vowels, consonant clusters)
    - Often has hyphens connecting syllables
    - May end with period
    - Usually ALL CAPS or mixed case with Sanskrit conventions
    - May start with verse number (digit + space + transliteration)
    """
    line = line.strip()
    if not line:
        return False

    # Check if line starts with a verse number (digit + space + transliteration)
    # Example: "2 Tyurartham na nyartham parusnim-asuscaneda-"
    if re.match(r'^\d+\s+[A-Z]', line):
        # This is verse number + content, check the content part
        content = re.sub(r'^\d+\s+', '', line)
        # If content has Sanskrit characteristics, it's transliteration
        if re.search(r'[aeiou]{2}', content) or content.count('-') >= 2:
            return True

    # Skip if it's clearly English prose (has common English words)
    common_english_words = [
        'the', 'and', 'of', 'to', 'in', 'with', 'for', 'is', 'are', 'was', 'were',
        'that', 'this', 'which', 'who', 'when', 'where', 'what', 'how', 'from', 'by'
    ]
    line_lower = line.lower()
    if any(f' {word} ' in f' {line_lower} ' for word in common_english_words):
        return False

    # Transliteration patterns:
    # 1. Contains many hyphens (syllable breaks)
    # 2. Contains repeating vowel patterns (aa, ii, uu, etc.) from long vowels
    # 3. Has Sanskrit-style consonant clusters (bhr, shr, etc.)
    # 4. Very long words without spaces (Sanskrit compounds)
    # 5. Short formal sentence ending with period (likely continuation of transliteration)
    # 6. Sanskrit phonetic patterns (dh, yan/yam endings)
    # 7. Sanskrit name patterns (ends with 'a' or 'ah' after consonants)
    transliteration_indicators = [
        line.count('-') >= 3,  # Multiple hyphens
        line.count('-') >= 1 and line.endswith('.'),  # Any hyphens + ends with period
        bool(re.search(r'\b[A-Z][a-z]+[aeiou]{2}', line)),  # Long vowels (aa, ii, etc.)
        bool(re.search(r'[bdfghjklmnprstvwy]{2,3}', line.lower())),  # Consonant clusters
        line.endswith('.') and line[0].isupper() and len(line.split()) <= 8,  # Short formal sentences
        bool(re.search(r'[a-z]{15,}', line)),  # Very long words (compounds)
        bool(re.search(r'\b[a-z]+dh[a-z]+', line.lower())),  # Sanskrit 'dh' sound
        bool(re.search(r'\b[a-z]+ya[nm]\b', line.lower())),  # Sanskrit endings (yan, yam, yana, etc.)
        bool(re.search(r'\b[a-z]+t[vw]am\b', line.lower())),  # Sanskrit tvam/tvam pattern
        bool(re.search(r'\b[Ss]udasa?\b|\b[Ii]ndrah?\b|\bindra[^c]', line)),  # Known Sanskrit names
        len(line.split()) <= 10 and not any(x in line.lower() for x in [' of ', ' the ', ' and ', ' that ']),  # Short without common English
    ]

    # If 2 or more indicators match, likely transliteration
    return sum(transliteration_indicators) >= 2


def is_metadata_line(line):
    """Check if line is metadata (Mandala, Sukta, Rshi, Devata, etc.)."""
    line = line.strip()
    metadata_patterns = [
        r'^Mandala\s+\d+',
        r'^MANDAL\s*-?\s*\d+',
        r'^Sukta\s+\d+',
        r'^SUKTA\s*-?\s*\d+',
        r'Rshi$',
        r'Devata',
        r'^\d+\.\s*[A-Z]',  # Numbered sections
        r'^CHAPTER\s+\d+',
        r'All rights reserved',
        r'©\s*Dr\.',
    ]
    return any(re.search(pattern, line, re.IGNORECASE) for pattern in metadata_patterns)


def parse_sharma_to_english(input_file, output_file=None, verify_mode=False):
    """Parse Sharma's Veda translation and extract only English text.

    Args:
        input_file: Path to Sharma's translation TXT file
        output_file: Path to save English-only output (default: input_english.txt)
        verify_mode: If True, also save discarded lines for verification

    Returns:
        dict with statistics
    """
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"❌ Error: File not found: {input_file}")
        return None

    if output_file is None:
        output_file = input_path.parent / f"{input_path.stem}_english.txt"

    output_path = Path(output_file)

    print("=" * 70)
    print(f"PARSING SHARMA'S TRANSLATION TO ENGLISH-ONLY")
    print("=" * 70)
    print(f"📄 Input: {input_file}")
    print(f"📝 Output: {output_file}")
    print()

    # Statistics
    stats = {
        'total_lines': 0,
        'devanagari_lines': 0,
        'transliteration_lines': 0,
        'english_lines': 0,
        'metadata_lines': 0,
        'empty_lines': 0,
    }

    english_lines = []
    discarded_lines = [] if verify_mode else None

    with open(input_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            stats['total_lines'] += 1

            # Strip whitespace but keep the line structure
            stripped = line.strip()

            # Skip empty lines
            if not stripped:
                stats['empty_lines'] += 1
                english_lines.append('')  # Preserve paragraph breaks
                continue

            # Check line type
            if is_devanagari_line(stripped):
                stats['devanagari_lines'] += 1
                if verify_mode:
                    discarded_lines.append(f"[DEVANAGARI {line_num}] {stripped[:100]}")
                continue

            if is_metadata_line(stripped):
                stats['metadata_lines'] += 1
                # Keep metadata as it provides context
                english_lines.append(stripped)
                continue

            if is_transliteration_line(stripped):
                stats['transliteration_lines'] += 1
                if verify_mode:
                    discarded_lines.append(f"[TRANSLITERATION {line_num}] {stripped[:100]}")
                continue

            # If none of the above, assume it's English translation
            stats['english_lines'] += 1
            english_lines.append(stripped)

    # Write English-only output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(english_lines))

    # Write discarded lines for verification if requested
    if verify_mode and discarded_lines:
        discard_file = output_path.parent / f"{output_path.stem}_discarded.txt"
        with open(discard_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(discarded_lines))
        print(f"🔍 Discarded lines saved to: {discard_file}")

    # Print statistics
    print("✅ Parsing complete!")
    print()
    print("=" * 70)
    print("STATISTICS")
    print("=" * 70)
    print(f"Total lines:           {stats['total_lines']:,}")
    print(f"  - English:           {stats['english_lines']:,} ({stats['english_lines']/stats['total_lines']*100:.1f}%)")
    print(f"  - Devanagari:        {stats['devanagari_lines']:,} ({stats['devanagari_lines']/stats['total_lines']*100:.1f}%)")
    print(f"  - Transliteration:   {stats['transliteration_lines']:,} ({stats['transliteration_lines']/stats['total_lines']*100:.1f}%)")
    print(f"  - Metadata:          {stats['metadata_lines']:,} ({stats['metadata_lines']/stats['total_lines']*100:.1f}%)")
    print(f"  - Empty:             {stats['empty_lines']:,} ({stats['empty_lines']/stats['total_lines']*100:.1f}%)")
    print()

    # Calculate compression ratio
    input_size = input_path.stat().st_size
    output_size = output_path.stat().st_size
    compression_ratio = (1 - output_size / input_size) * 100

    print(f"Input size:  {input_size:,} bytes ({input_size/1024/1024:.2f} MB)")
    print(f"Output size: {output_size:,} bytes ({output_size/1024/1024:.2f} MB)")
    print(f"Reduction:   {compression_ratio:.1f}% smaller")
    print("=" * 70)

    return stats


def verify_against_griffith(sharma_english_file, griffith_file):
    """Compare parsed Sharma English with Griffith to verify parsing quality.

    This helps ensure we didn't accidentally discard English text.
    """
    print()
    print("=" * 70)
    print("VERIFICATION AGAINST GRIFFITH")
    print("=" * 70)

    # Read both files
    with open(sharma_english_file, 'r', encoding='utf-8') as f:
        sharma_lines = [l.strip() for l in f if l.strip()]

    with open(griffith_file, 'r', encoding='utf-8') as f:
        griffith_lines = [l.strip() for l in f if l.strip()]

    print(f"Sharma (English-only):  {len(sharma_lines):,} non-empty lines")
    print(f"Griffith (Original):    {len(griffith_lines):,} non-empty lines")
    print()

    # Sample comparison: check if similar proper nouns appear
    import re

    def extract_proper_nouns(lines):
        nouns = set()
        for line in lines:
            # Find capitalized words (proper nouns)
            words = re.findall(r'\b[A-Z][a-z]+\b', line)
            nouns.update(words)
        return nouns

    sharma_nouns = extract_proper_nouns(sharma_lines[:1000])  # Sample first 1000 lines
    griffith_nouns = extract_proper_nouns(griffith_lines[:1000])

    common_nouns = sharma_nouns & griffith_nouns
    overlap_percent = len(common_nouns) / len(sharma_nouns | griffith_nouns) * 100

    print(f"Proper nouns in Sharma:   {len(sharma_nouns)}")
    print(f"Proper nouns in Griffith: {len(griffith_nouns)}")
    print(f"Common proper nouns:      {len(common_nouns)} ({overlap_percent:.1f}% overlap)")
    print()
    print("Sample common proper nouns:", sorted(list(common_nouns))[:20])
    print()

    if overlap_percent > 50:
        print("✅ Good overlap! Parsing likely successful.")
    elif overlap_percent > 30:
        print("⚠️  Moderate overlap. Review discarded lines.")
    else:
        print("❌ Low overlap. Parsing may need adjustment.")

    print("=" * 70)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Parse Sharma's Veda translations to extract English-only text",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse Rigveda
  python parse_sharma_to_english.py rigveda-sharma.txt

  # Parse with verification mode (saves discarded lines)
  python parse_sharma_to_english.py rigveda-sharma.txt --verify

  # Parse and compare with Griffith
  python parse_sharma_to_english.py rigveda-sharma.txt --compare griffith-rigveda.txt

  # Parse Yajurveda
  python parse_sharma_to_english.py yajurveda-sharma.txt --verify
        """
    )

    parser.add_argument('input_file', help='Sharma translation TXT file')
    parser.add_argument('-o', '--output', help='Output file (default: input_english.txt)')
    parser.add_argument('-v', '--verify', action='store_true',
                       help='Save discarded lines for manual verification')
    parser.add_argument('-c', '--compare', metavar='GRIFFITH_FILE',
                       help='Compare with Griffith translation for verification')

    args = parser.parse_args()

    # Parse Sharma to English
    stats = parse_sharma_to_english(args.input_file, args.output, args.verify)

    if stats is None:
        sys.exit(1)

    # Verify against Griffith if requested
    if args.compare:
        output_file = args.output or Path(args.input_file).parent / f"{Path(args.input_file).stem}_english.txt"
        verify_against_griffith(output_file, args.compare)
