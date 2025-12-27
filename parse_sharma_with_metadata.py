#!/usr/bin/env python3
"""
Parse Sharma's Rigveda/Yajurveda to extract English-only with metadata.

Enhanced parser that:
1. Filters out Devanagari and Transliteration
2. Extracts proper nouns from transliteration lines
3. Adds extracted names as metadata to English sections
4. Preserves all important information while keeping text clean
"""

import re
import sys
from pathlib import Path
from collections import defaultdict


def is_devanagari_line(line):
    """Check if line contains Devanagari script."""
    if not line:
        return False
    # Check for Devanagari Unicode range (U+0900 to U+097F)
    devanagari_chars = sum(1 for char in line if '\u0900' <= char <= '\u097F')
    # If more than 20% of characters are Devanagari, consider it a Devanagari line
    return devanagari_chars > len(line) * 0.2


def is_metadata_line(line):
    """Check if line is metadata (Mandala, Sukta, Rshi, Devata, etc.).

    Updated to handle ALL format variations discovered:
    - Rigveda: Mandala X/Sukta Y (with variations)
    - Yajurveda: N. (Devata, Rshi) format
    - OCR errors: MandalalbX/Sukta Y or Mandalal0/Sukta Y
    - Capital K: Mandala X/SuKta Y
    - Typo: Mandala X/Suktal
    """
    line = line.strip()
    metadata_patterns = [
        # Rigveda patterns
        r'^Mandala\s*\d+',                           # Standard with space
        r'^Mandala\d+',                              # No space (Mandala7, Mandala10)
        r'^Mandalal\d+',                             # OCR error (Mandalal10)
        r'^Mandalal0',                               # OCR error (Mandalal0 for Mandala 10)
        r'^MANDAL\s*-?\s*\d+',                       # Uppercase variant
        r'^Sukta\s+\d+',                             # Sukta header
        r'^SuKta\s+\d+',                             # Capital K variant
        r'^Suktal\s*$',                              # Typo: Suktal (means Sukta 1)
        r'^SUKTA\s*-?\s*\d+',                        # Uppercase
        r'^Mandala\s*\d+/Sukta[-\s]+\d+',           # Standard full format
        r'^Mandala\d+/Sukta\s+\d+',                 # No space after Mandala
        r'^Mandalal\d+/Sukta\s+\d+',                # OCR error format
        r'^Mandalal0/Sukta\s+\d+',                  # OCR error for Mandala 10
        r'^Mandala\s*\d+/Sukta-\d+',                # Hyphen variant
        r'^Mandala\s*\d+/SuKta\s+\d+',              # Capital K variant
        r'^Mandala\s*\d+/Suktal\s*$',               # Typo variant

        # Yajurveda patterns
        r'^\d+[\.\s|—]+\([^)]*Devata[^)]*Rshi[^)]*\)',  # Yajurveda: N. or N.| or N.— (Devata, Rshi)
        r'^\([^)]*Devata[^)]*Rshi[^)]*\)',              # Yajurveda: (Devata, Rshi) without number
        r'^\d+\.\s*\([^)]*Rshi[^)]*\)',                 # Yajurveda: N. (Rshi info)

        # General patterns
        r'^\d+\.\s*Rshi',
        r'^\d+\.\s*Devata',
        r'^\d+\.\s*Chanda',
        r'^Rshi\s*:',
        r'^Devata\s*:',
        r'^Chanda\s*:',
    ]
    return any(re.match(pattern, line, re.IGNORECASE) for pattern in metadata_patterns)


def extract_proper_nouns_from_transliteration(line):
    """Extract likely proper nouns from transliteration line.

    In Sanskrit transliteration, proper nouns are typically:
    - Capitalized words
    - Known deity/person names (with various case endings)
    - Not common function words
    """
    # Common Sanskrit function words to exclude
    function_words = {
        'the', 'and', 'of', 'to', 'in', 'with', 'for', 'is', 'are', 'was', 'were',
        'that', 'this', 'which', 'who', 'when', 'where', 'what', 'how', 'from', 'by',
        'ca', 'va', 'iva', 'na', 'ma', 'hi', 'tu', 'api', 'eva', 'atha', 'yat', 'kim',
        'pra', 'anu', 'sam', 'abhi', 'adhi', 'upa',  # Sanskrit particles and prefixes
    }

    # Known important names to always extract (with common case endings)
    important_names = [
        'indra', 'agni', 'soma', 'varuna', 'mitra', 'vayu', 'surya', 'usas',
        'marut', 'aditya', 'ashvin', 'rbhu', 'rudra', 'vishnu', 'pusan',
        'sarasvati', 'aditi', 'prithvi', 'dyaus', 'parjanya',
        'sudas', 'bharata', 'tritsu', 'puru', 'turvas', 'yadu', 'anu',
        'vasishtha', 'vishvamitra', 'atri', 'bharadvaja', 'angiras',
        'kutsa', 'divodasa', 'trasadasyu', 'purukutsa'
    ]

    proper_nouns = []

    # 1. Extract capitalized words
    cap_words = re.findall(r'\b([A-Z][a-z]{3,})\b', line)
    for word in cap_words:
        if word.lower() not in function_words and len(word) >= 4:
            proper_nouns.append(word)

    # 2. Search for known important names (case-insensitive, with various endings)
    line_lower = line.lower()
    for name in important_names:
        # Match the name with common Sanskrit case endings
        # More flexible pattern to catch compounds like "sudastaraya" too
        pattern = rf'\b({name}(?:[a-z]{{0,10}})?)\b'
        matches = re.findall(pattern, line_lower)
        for match in matches:
            # Only keep if it starts with the name and is reasonable length
            if match.startswith(name) and len(match) <= len(name) + 10:
                # Capitalize first letter for consistency
                capitalized = match.capitalize()
                # Avoid duplicates
                if not any(n.lower() == capitalized.lower() for n in proper_nouns):
                    proper_nouns.append(capitalized)
                proper_nouns.append(capitalized)

    # Remove duplicates while preserving order
    seen = set()
    unique_nouns = []
    for noun in proper_nouns:
        # Normalize similar variants (e.g., Sudasa, Sudas, Sudasah -> Sudasa)
        base_form = noun
        # Strip common endings for deduplication
        for ending in ['h', 's', 'm', 'n', 'e', 'ya', 'aya', 'sya', 'ena']:
            if noun.lower().endswith(ending) and len(noun) > len(ending) + 3:
                potential_base = noun[:-len(ending)]
                # Check if this base already exists
                if any(existing.lower().startswith(potential_base.lower()) for existing in seen):
                    base_form = potential_base
                    break

        if base_form.lower() not in seen:
            seen.add(base_form.lower())
            unique_nouns.append(base_form)

    return unique_nouns
def is_transliteration_line(line):
    """Check if line is Roman transliteration of Sanskrit.

    Returns: (is_transliteration, proper_nouns)
    """
    line = line.strip()
    if not line:
        return False, []

    # Check if line starts with a verse number (digit + space + transliteration)
    if re.match(r'^\d+\s+[A-Z]', line):
        content = re.sub(r'^\d+\s+', '', line)
        if re.search(r'[aeiou]{2}', content) or content.count('-') >= 2:
            proper_nouns = extract_proper_nouns_from_transliteration(line)
            return True, proper_nouns

    # Skip if it's clearly English prose (has common English words)
    common_english_words = [
        'the', 'and', 'of', 'to', 'in', 'with', 'for', 'is', 'are', 'was', 'were',
        'that', 'this', 'which', 'who', 'when', 'where', 'what', 'how', 'from', 'by'
    ]
    line_lower = line.lower()
    if any(f' {word} ' in f' {line_lower} ' for word in common_english_words):
        return False, []

    # Transliteration patterns
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

    is_trans = sum(transliteration_indicators) >= 2
    proper_nouns = extract_proper_nouns_from_transliteration(line) if is_trans else []

    return is_trans, proper_nouns


def parse_sharma_to_english_with_metadata(input_file, output_file=None, verify_mode=False):
    """Parse Sharma's text to English with proper noun metadata.

    Args:
        input_file: Path to input file
        output_file: Path to output file (default: input_english.txt)
        verify_mode: If True, save discarded lines to separate file

    Returns:
        dict with statistics
    """
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"❌ Error: File not found: {input_file}")
        return None

    if output_file is None:
        output_file = input_path.parent / f"{input_path.stem}_english_with_metadata.txt"

    output_path = Path(output_file)

    print("=" * 70)
    print(f"PARSING SHARMA'S TRANSLATION TO ENGLISH WITH METADATA")
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
        'proper_nouns_extracted': 0,
        'metadata_additions': 0,
    }

    english_lines = []
    discarded_lines = [] if verify_mode else None

    # Buffer for collecting proper nouns from transliteration
    pending_proper_nouns = []
    current_sukta = None
    sukta_proper_nouns = defaultdict(set)  # Track nouns per Sukta to avoid repetition

    with open(input_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            stats['total_lines'] += 1
            stripped = line.strip()

            # Skip empty lines
            if not stripped:
                stats['empty_lines'] += 1
                english_lines.append('')  # Preserve paragraph breaks
                continue

            # Check for Sukta marker to track context
            sukta_match = re.match(r'Mandala\s+(\d+)/Sukta\s+(\d+)', stripped)
            if sukta_match:
                current_sukta = f"{sukta_match.group(1)}-{sukta_match.group(2)}"

            # Check line type
            if is_devanagari_line(stripped):
                stats['devanagari_lines'] += 1
                if verify_mode:
                    discarded_lines.append(f"[DEVANAGARI {line_num}] {stripped[:100]}")
                continue

            if is_metadata_line(stripped):
                stats['metadata_lines'] += 1
                # Add any pending proper nouns before metadata
                if pending_proper_nouns:
                    # Filter out nouns already seen in this Sukta
                    new_nouns = [n for n in pending_proper_nouns if n not in sukta_proper_nouns[current_sukta]]
                    if new_nouns:
                        metadata_line = f"[Names: {', '.join(new_nouns)}]"
                        english_lines.append(metadata_line)
                        stats['metadata_additions'] += 1
                        # Mark these as seen for this Sukta
                        sukta_proper_nouns[current_sukta].update(new_nouns)
                    pending_proper_nouns = []

                english_lines.append(stripped)
                continue

            # Check if it's transliteration
            is_trans, proper_nouns = is_transliteration_line(stripped)
            if is_trans:
                stats['transliteration_lines'] += 1
                if verify_mode:
                    discarded_lines.append(f"[TRANSLITERATION {line_num}] {stripped[:100]}")

                # Collect proper nouns
                if proper_nouns:
                    pending_proper_nouns.extend(proper_nouns)
                    stats['proper_nouns_extracted'] += len(proper_nouns)
                continue

            # It's an English line
            stats['english_lines'] += 1

            # If we have pending proper nouns, add them as metadata before this English line
            if pending_proper_nouns:
                # Filter out nouns already seen in this Sukta
                new_nouns = [n for n in pending_proper_nouns if n not in sukta_proper_nouns[current_sukta]]
                if new_nouns:
                    metadata_line = f"[Names: {', '.join(new_nouns)}]"
                    english_lines.append(metadata_line)
                    stats['metadata_additions'] += 1
                    # Mark these as seen for this Sukta
                    sukta_proper_nouns[current_sukta].update(new_nouns)
                pending_proper_nouns = []

            english_lines.append(stripped)

    # Write English-only output with metadata
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(english_lines))

    # Write discarded lines if in verify mode
    if verify_mode and discarded_lines:
        discard_path = output_path.parent / f"{output_path.stem}_discarded.txt"
        with open(discard_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(discarded_lines))
        print(f"🔍 Discarded lines saved to: {discard_path}")

    print("✅ Parsing complete!")
    print()

    # Print statistics
    input_size = input_path.stat().st_size
    output_size = output_path.stat().st_size
    reduction = (1 - output_size / input_size) * 100

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
    print(f"Proper nouns extracted from transliteration: {stats['proper_nouns_extracted']:,}")
    print(f"Metadata lines added:                        {stats['metadata_additions']:,}")
    print()
    print(f"Input size:  {input_size:,} bytes ({input_size/1024/1024:.2f} MB)")
    print(f"Output size: {output_size:,} bytes ({output_size/1024/1024:.2f} MB)")
    print(f"Reduction:   {reduction:.1f}% smaller")
    print("=" * 70)

    return stats


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Parse Sharma\'s Vedic translations to English-only with metadata',
        epilog='''
Examples:
  # Parse Rigveda with metadata
  python parse_sharma_with_metadata.py rigveda-sharma.txt

  # Parse with verification mode (saves discarded lines)
  python parse_sharma_with_metadata.py rigveda-sharma.txt --verify

  # Parse Yajurveda
  python parse_sharma_with_metadata.py yajurveda-sharma.txt --verify
        '''
    )

    parser.add_argument('input_file', help='Input file (Sharma\'s translation)')
    parser.add_argument('--output', '-o', help='Output file (default: input_english_with_metadata.txt)')
    parser.add_argument('--verify', action='store_true', help='Save discarded lines for verification')

    args = parser.parse_args()

    result = parse_sharma_to_english_with_metadata(
        args.input_file,
        args.output,
        args.verify
    )

    return 0 if result else 1


if __name__ == '__main__':
    sys.exit(main())
