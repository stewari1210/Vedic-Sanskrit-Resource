#!/usr/bin/env python3
"""
Extract proper nouns from Brahmanas corpus (Satapatha Brahmana).

This script analyzes the Satapatha Brahmana texts to identify proper nouns
(names of people, places, tribes, deities, etc.) and their frequencies.
"""

import os
import re
import json
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Set, Tuple

# Import proper noun variants for cross-referencing
try:
    with open('proper_noun_variants.json', 'r', encoding='utf-8') as f:
        EXISTING_VARIANTS = json.load(f)
except FileNotFoundError:
    EXISTING_VARIANTS = {}

def get_brahmana_files() -> List[Path]:
    """Get all Brahmanas text files."""
    brahmana_files = []
    base_dir = Path("local_store/ancient_history")

    # Find all satapatha brahmana parts
    for part_dir in base_dir.glob("satapatha_brahmana_part_*"):
        if part_dir.is_dir():
            md_file = part_dir / f"{part_dir.name}.md"
            if md_file.exists():
                brahmana_files.append(md_file)

    return sorted(brahmana_files)

def extract_proper_nouns_from_text(text: str) -> Dict[str, int]:
    """Extract potential proper nouns from text using heuristics."""
    proper_nouns = Counter()

    # Common Vedic proper noun patterns
    # Names of sages, kings, tribes, places, deities

    # Pattern 1: Capitalized words at start of sentences or after punctuation
    capitalized_pattern = r'(?:^|(?<=[.!?]\s))([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
    for match in re.finditer(capitalized_pattern, text, re.MULTILINE):
        noun = match.group(1).strip()
        if len(noun.split()) <= 3:  # Limit to 1-3 words
            proper_nouns[noun] += 1

    # Pattern 2: Names with specific Vedic patterns
    vedic_patterns = [
        r'\b([A-Z][a-z]+(?:-[A-Z][a-z]+)+)\b',  # Compound names like Madhyandina
        r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b',  # Multi-word names
    ]

    for pattern in vedic_patterns:
        for match in re.finditer(pattern, text):
            noun = match.group(1).strip()
            if len(noun) > 2 and not noun.isupper():  # Avoid abbreviations
                proper_nouns[noun] += 1

    # Pattern 3: Known Vedic names and terms
    known_names = [
        'Indra', 'Agni', 'Soma', 'Varuna', 'Vishnu', 'Rudra', 'Brahma', 'Prajapati',
        'Vasishtha', 'Vashishta', 'Vasistha', 'Vishwamitra', 'Visvamitra',
        'Kashyapa', 'Kasyapa', 'Atri', 'Bharadvaja', 'Gautama', 'Jamadagni',
        'Kanva', 'Angiras', 'Bhrigu', 'Chyavana', 'Dadhyanch', 'Gotama',
        'Sudas', 'Divodasa', 'Trasadasyu', 'Pururavas', 'Yayati', 'Nahusha',
        'Bharatas', 'Bharata', 'Kurus', 'Panchalas', 'Turvashas', 'Krivis',
        'Srinjayas', 'Somakas', 'Keshins', 'Trtsus', 'Tritsu', 'Pakthas',
        'Alinas', 'Bhalanas', 'Sivas', 'Visanins', 'Anu', 'Druhyu', 'Yaksus',
        'Matsyas', 'Gandharvas', 'Apsaras', 'Asuras', 'Danavas', 'Daityas',
        'Ganga', 'Yamuna', 'Saraswati', 'Sindhu', 'Vipas', 'Sutudri',
        'Parushni', 'Asikni', 'Marudvridha', 'Arjikiya', 'Sushoma',
        'Madhyandina', 'Kanva', 'Taittiriya', 'Kathaka', 'Kapishthala',
        'Maithrayani', 'Varaha', 'Satyayana', 'Saunaka', 'Sakala',
        'Baskala', 'Asvalayana', 'Sankhayana', 'Latayayana', 'Drashtara',
        'Apastamba', 'Hiranyakesin', 'Baudhayana', 'Vaikhanasa'
    ]

    for name in known_names:
        count = len(re.findall(r'\b' + re.escape(name) + r'\b', text, re.IGNORECASE))
        if count > 0:
            proper_nouns[name] += count

    return dict(proper_nouns)

def analyze_brahmana_proper_nouns():
    """Analyze proper nouns across all Brahmanas texts."""
    print("🔍 Analyzing Brahmanas corpus for proper nouns...")

    brahmana_files = get_brahmana_files()
    print(f"Found {len(brahmana_files)} Brahmanas files")

    all_proper_nouns = Counter()
    file_stats = {}

    for file_path in brahmana_files:
        print(f"Processing {file_path.name}...")

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Clean up OCR artifacts and formatting
            content = re.sub(r'\n+', ' ', content)  # Replace multiple newlines with spaces
            content = re.sub(r'\s+', ' ', content)  # Normalize whitespace

            file_nouns = extract_proper_nouns_from_text(content)
            all_proper_nouns.update(file_nouns)

            file_stats[file_path.name] = {
                'total_nouns': len(file_nouns),
                'total_occurrences': sum(file_nouns.values()),
                'top_nouns': dict(sorted(file_nouns.items(), key=lambda x: x[1], reverse=True)[:10])
            }

        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            continue

    return dict(all_proper_nouns), file_stats

def filter_significant_nouns(nouns: Dict[str, int], min_occurrences: int = 2) -> Dict[str, int]:
    """Filter nouns to keep only significant ones."""
    # Remove very common words that might be misidentified
    common_words = {
        'The', 'And', 'But', 'For', 'Are', 'But', 'Not', 'All', 'Can', 'Her', 'Was', 'One', 'Our', 'Had', 'Its',
        'Book', 'Part', 'Chapter', 'Section', 'Verse', 'Hymn', 'Sutra', 'Brahmana', 'Upanishad',
        'First', 'Second', 'Third', 'Fourth', 'Fifth', 'Sixth', 'Seventh', 'Eighth', 'Ninth', 'Tenth'
    }

    filtered = {}
    for noun, count in nouns.items():
        if count >= min_occurrences and noun not in common_words and len(noun) > 2:
            # Additional filtering: must contain at least one letter
            if re.search(r'[a-zA-Z]', noun):
                filtered[noun] = count

    return filtered

def categorize_brahmana_nouns(nouns: Dict[str, int]) -> Dict[str, Dict[str, int]]:
    """Categorize nouns by type (sages, tribes, deities, etc.)."""
    categories = {
        'sages_rishis': {},
        'kings_rulers': {},
        'tribes_peoples': {},
        'deities': {},
        'places_rivers': {},
        'schools_traditions': {},
        'other': {}
    }

    # Sage/Rishi indicators
    sage_indicators = ['rishi', 'sage', 'priest', 'seer', ' rsi', 'muni']
    known_sages = [
        'Vasishtha', 'Vasistha', 'Vashishta', 'Vishwamitra', 'Visvamitra', 'Kashyapa', 'Kasyapa',
        'Atri', 'Bharadvaja', 'Gautama', 'Jamadagni', 'Kanva', 'Angiras', 'Bhrigu', 'Chyavana',
        'Dadhyanch', 'Gotama', 'Agastya', 'Agasti', 'Grtsamada', 'Yajnavalkya', 'Yama', 'Sanatkumara'
    ]

    # King/Ruler indicators
    king_indicators = ['king', 'ruler', 'prince', 'chieftain', 'sovereign']
    known_kings = [
        'Sudas', 'Divodasa', 'Trasadasyu', 'Kurusravana', 'Pakasthaman', 'Pururavas',
        'Yayati', 'Nahusha', 'Mudgala', 'Pratardana', 'Janamejaya', 'Parikshit'
    ]

    # Tribe indicators
    tribe_indicators = ['tribe', 'people', 'clan', 'folk', 'race', 'nation']
    known_tribes = [
        'Bharatas', 'Bharata', 'Kurus', 'Panchalas', 'Turvashas', 'Krivis', 'Srinjayas',
        'Somakas', 'Keshins', 'Trtsus', 'Tritsu', 'Pakthas', 'Alinas', 'Bhalanas',
        'Sivas', 'Visanins', 'Anu', 'Druhyu', 'Matsyas', 'Yaksus'
    ]

    # Deity indicators
    deity_indicators = ['god', 'goddess', 'deva', 'devi', 'divine']
    known_deities = [
        'Indra', 'Agni', 'Soma', 'Varuna', 'Vishnu', 'Rudra', 'Brahma', 'Prajapati',
        'Savitr', 'Pushan', 'Bhaga', 'Aryaman', 'Mitra', 'Aditi', 'Ushas', 'Ashvins',
        'Maruts', 'Vayu', 'Parjanya', 'Apam', 'Napat', 'Vishwakarma', 'Tvastr',
        'Dadhikra', 'Ahi', 'Vrtra', 'Vala', 'Namuchi', 'Sushna', 'Kuyava'
    ]

    # Place/River indicators
    place_indicators = ['river', 'mountain', 'place', 'region', 'land', 'country']
    known_places = [
        'Ganga', 'Yamuna', 'Saraswati', 'Sindhu', 'Vipas', 'Sutudri', 'Parushni',
        'Asikni', 'Marudvridha', 'Arjikiya', 'Sushoma', 'Kurukshetra', 'Himavant',
        'Meru', 'Mandara', 'Uttarakuru', 'Bharatavarsa'
    ]

    # School/Tradition indicators
    school_indicators = ['school', 'tradition', 'recension', 'shakha', 'branch']
    known_schools = [
        'Madhyandina', 'Kanva', 'Taittiriya', 'Kathaka', 'Kapishthala', 'Maithrayani',
        'Varaha', 'Satyayana', 'Saunaka', 'Sakala', 'Baskala', 'Asvalayana',
        'Sankhayana', 'Latayayana', 'Drashtara', 'Apastamba', 'Hiranyakesin',
        'Baudhayana', 'Vaikhanasa'
    ]

    for noun, count in nouns.items():
        noun_lower = noun.lower()

        # Check categories
        if any(sage in noun_lower for sage in sage_indicators) or noun in known_sages:
            categories['sages_rishis'][noun] = count
        elif any(king in noun_lower for king in king_indicators) or noun in known_kings:
            categories['kings_rulers'][noun] = count
        elif any(tribe in noun_lower for tribe in tribe_indicators) or noun in known_tribes:
            categories['tribes_peoples'][noun] = count
        elif any(deity in noun_lower for deity in deity_indicators) or noun in known_deities:
            categories['deities'][noun] = count
        elif any(place in noun_lower for place in place_indicators) or noun in known_places:
            categories['places_rivers'][noun] = count
        elif any(school in noun_lower for school in school_indicators) or noun in known_schools:
            categories['schools_traditions'][noun] = count
        else:
            categories['other'][noun] = count

    return categories

def save_brahmana_proper_nouns():
    """Extract and save Brahmanas proper nouns."""
    print("📚 Extracting proper nouns from Brahmanas corpus...")

    # Analyze all texts
    all_nouns, file_stats = analyze_brahmana_proper_nouns()

    # Filter significant nouns
    significant_nouns = filter_significant_nouns(all_nouns, min_occurrences=2)

    # Categorize nouns
    categorized_nouns = categorize_brahmana_nouns(significant_nouns)

    # Save results
    output_data = {
        "metadata": {
            "corpus": "Satapatha Brahmana (Complete)",
            "parts": 5,
            "total_files": len(file_stats),
            "extraction_date": "2025-01-25",
            "method": "Heuristic pattern matching + known name recognition",
            "min_occurrences": 2
        },
        "file_statistics": file_stats,
        "categories": categorized_nouns,
        "summary": {
            "total_unique_nouns": len(significant_nouns),
            "total_occurrences": sum(significant_nouns.values()),
            "categories_count": {cat: len(nouns) for cat, nouns in categorized_nouns.items()}
        }
    }

    # Save to JSON
    output_file = "proper_nouns_brahmanas.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved {len(significant_nouns)} proper nouns to {output_file}")

    # Print summary
    print("\n📊 Summary:")
    print(f"Total unique nouns: {len(significant_nouns)}")
    print(f"Total occurrences: {sum(significant_nouns.values())}")
    print("\nBy category:")
    for cat, nouns in categorized_nouns.items():
        if nouns:
            print(f"  {cat}: {len(nouns)} nouns")

    # Show top nouns
    print("\n🔝 Top 20 proper nouns:")
    top_nouns = sorted(significant_nouns.items(), key=lambda x: x[1], reverse=True)[:20]
    for noun, count in top_nouns:
        print(f"  {noun}: {count}")

if __name__ == "__main__":
    save_brahmana_proper_nouns()