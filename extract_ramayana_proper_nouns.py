#!/usr/bin/env python3
"""
Extract proper nouns from Griffith Ramayana text and integrate into proper_noun_variants.json
"""

import json
import re
from collections import defaultdict
from pathlib import Path

def extract_proper_nouns_from_ramayana():
    """Extract proper nouns from Ramayana text with frequency counts."""

    # Read the Ramayana text
    ramayana_file = Path("local_store/ancient_history/griffith-ramayana/griffith-ramayana.md")

    with open(ramayana_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove Gutenberg header/footer and table of contents
    # Find the start of actual content
    start_marker = "***START OF THE PROJECT GUTENBERG EBOOK"
    if start_marker in content:
        content = content.split(start_marker, 1)[1]

    # Remove Gutenberg license text at the end
    end_marker = "*** END OF THE PROJECT GUTENBERG EBOOK"
    if end_marker in content:
        content = content.split(end_marker, 1)[0]

    # Remove table of contents and headers
    lines = content.split('\n')
    filtered_lines = []
    skip_section = False

    for line in lines:
        # Skip Gutenberg metadata
        if any(phrase in line.lower() for phrase in [
            'project gutenberg', 'ebook', 'release date', 'language',
            'translated by', 'ralph t. griffith', 'contents', 'canto'
        ]):
            continue

        # Skip very short lines that are likely headers
        if len(line.strip()) < 20 and not line.strip().endswith('.'):
            continue

        filtered_lines.append(line)

    content = '\n'.join(filtered_lines)

    # Extract potential proper nouns using regex patterns
    # Look for capitalized words that could be proper nouns
    proper_noun_pattern = r'\b[A-Z][a-zA-Z\'\-]+(?:\s+[A-Z][a-zA-Z\'\-]+)*\b'

    words = re.findall(proper_noun_pattern, content)

    # Count frequencies
    word_counts = defaultdict(int)
    for word in words:
        # Clean up the word
        word = word.strip()
        if len(word) > 2:  # Skip very short words
            word_counts[word] += 1

    return word_counts

def categorize_proper_nouns(word_counts):
    """Categorize proper nouns based on their likely type."""

    categories = {
        'sages': [],
        'kings_and_heroes': [],
        'deities': [],
        'tribes_and_kingdoms': [],
        'rivers_and_geography': [],
        'schools_traditions': []
    }

    # Known proper nouns from Ramayana context
    sages = [
        'Vasishtha', 'Visvamitra', 'Vasistha', 'Visvamitra', 'Agastya', 'Atri',
        'Bhrigu', 'Chyavana', 'Durvasa', 'Gautama', 'Jamadagni', 'Kashyapa',
        'Markandeya', 'Narada', 'Parasara', 'Pulastya', 'Valmiki', 'Vamadeva',
        'Vishwamitra', 'Yajnavalkya'
    ]

    kings_heroes = [
        'Rama', 'Lakshmana', 'Bharata', 'Shatrughna', 'Hanuman', 'Sugriva',
        'Vibhishana', 'Dasaratha', 'Janaka', 'Ravana', 'Kumbhakarna', 'Indrajit',
        'Khara', 'Dushana', 'Surpanakha', 'Sita', 'Kaikeyi', 'Sumitra', 'Kaushalya'
    ]

    deities = [
        'Brahma', 'Vishnu', 'Shiva', 'Indra', 'Agni', 'Varuna', 'Yama', 'Kubera',
        'Surya', 'Chandra', 'Lakshmi', 'Saraswati', 'Durga', 'Ganesh', 'Kartikeya',
        'Hanuman'  # Hanuman is both hero and deity
    ]

    tribes_kingdoms = [
        'Ayodhya', 'Mithila', 'Lanka', 'Kishkindha', 'Kosala', 'Videha',
        'Ikshvaku', 'Raghu', 'Solar', 'Lunar'
    ]

    rivers_geography = [
        'Ganges', 'Yamuna', 'Saraswati', 'Godavari', 'Narmada', 'Sindhu',
        'Gangá', 'Yamuná', 'Sarasvatí'
    ]

    schools_traditions = [
        'Veda', 'Rigveda', 'Yajurveda', 'Samaveda', 'Atharvaveda', 'Brahmin',
        'Kshatriya', 'Vaishya', 'Shudra', 'Sannyasa'
    ]

    # Categorize words based on frequency and known lists
    for word, count in word_counts.items():
        # Skip common English words that might be capitalized
        if word.lower() in ['the', 'and', 'but', 'for', 'nor', 'yet', 'so', 'a', 'an',
                           'this', 'that', 'these', 'those', 'i', 'me', 'my', 'myself',
                           'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours',
                           'he', 'him', 'his', 'himself', 'she', 'her', 'hers', 'it',
                           'its', 'itself', 'they', 'them', 'their', 'theirs', 'what',
                           'which', 'who', 'whom', 'whose', 'this', 'that', 'these',
                           'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been',
                           'being', 'have', 'has', 'had', 'having', 'do', 'does',
                           'did', 'doing', 'will', 'would', 'could', 'should', 'may',
                           'might', 'must', 'shall', 'can', 'let', 'here', 'there',
                           'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each',
                           'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
                           'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very']:
            continue

        # Skip if frequency is too low (likely not a proper noun)
        if count < 3:
            continue

        # Categorize based on known lists and context
        categorized = False

        if word in sages or 'rishi' in word.lower() or 'sage' in word.lower():
            categories['sages'].append((word, count))
            categorized = True
        elif word in kings_heroes or 'prince' in word.lower() or 'king' in word.lower():
            categories['kings_and_heroes'].append((word, count))
            categorized = True
        elif word in deities or 'deva' in word.lower() or 'god' in word.lower():
            categories['deities'].append((word, count))
            categorized = True
        elif word in tribes_kingdoms or 'kingdom' in word.lower() or 'tribe' in word.lower():
            categories['tribes_and_kingdoms'].append((word, count))
            categorized = True
        elif word in rivers_geography or 'river' in word.lower() or 'mountain' in word.lower():
            categories['rivers_and_geography'].append((word, count))
            categorized = True
        elif word in schools_traditions or 'veda' in word.lower() or 'brahmin' in word.lower():
            categories['schools_traditions'].append((word, count))
            categorized = True

        # If not categorized but appears frequently, add to kings_and_heroes as default
        if not categorized and count > 10:
            categories['kings_and_heroes'].append((word, count))

    return categories

def integrate_ramayana_nouns():
    """Integrate Ramayana proper nouns into the variants database."""

    print("🔄 Extracting proper nouns from Ramayana...")

    # Extract proper nouns
    word_counts = extract_proper_nouns_from_ramayana()
    print(f"📋 Found {len(word_counts)} potential proper nouns")

    # Categorize them
    categorized_nouns = categorize_proper_nouns(word_counts)

    # Count meaningful nouns
    meaningful_count = sum(len(nouns) for nouns in categorized_nouns.values())
    print(f"📋 Found {meaningful_count} meaningful proper nouns")

    # Load existing variants
    with open('proper_noun_variants.json', 'r', encoding='utf-8') as f:
        existing_variants = json.load(f)

    print("\n📚 Ramayana proper nouns to integrate:")

    source = "Griffith-Ramayana"
    integrated_count = 0

    for category, nouns in categorized_nouns.items():
        if not nouns:
            continue

        print(f"\n{category.replace('_', ' ').title()}:")
        for noun_name, occurrences in nouns:
            print(f"  {noun_name}: {occurrences} occurrences")

            # Check if category exists
            if category not in existing_variants:
                existing_variants[category] = {}

            # Check if noun exists
            if noun_name in existing_variants[category]:
                # Update existing entry
                existing_entry = existing_variants[category][noun_name]

                # Handle sources field - can be dict or list
                sources = existing_entry.get('sources', {})
                if isinstance(sources, dict):
                    if source not in sources:
                        sources[source] = occurrences
                        existing_entry['total_occurrences'] = existing_entry.get('total_occurrences', 0) + occurrences
                    elif sources[source] < occurrences:
                        existing_entry['total_occurrences'] = existing_entry.get('total_occurrences', 0) + (occurrences - sources[source])
                        sources[source] = occurrences
                elif isinstance(sources, list):
                    if source not in sources:
                        sources.append(source)
                        existing_entry['total_occurrences'] = existing_entry.get('total_occurrences', 0) + occurrences

                # Update priority if needed
                if existing_entry.get('priority') == 'LOW' and occurrences > 5:
                    existing_entry['priority'] = 'MEDIUM'

            else:
                # Create new entry
                existing_variants[category][noun_name] = {
                    "variants": [noun_name],  # Basic variant list
                    "role": f"From Ramayana epic",
                    "sources": {
                        source: occurrences
                    },
                    "total_occurrences": occurrences,
                    "priority": "MEDIUM" if occurrences > 10 else "LOW"
                }

            integrated_count += 1

    # Update metadata
    existing_variants["_sources"] = existing_variants.get("_sources", "") + " + Griffith-Ramayana"
    existing_variants["_last_updated"] = "2025-01-25"

    # Save updated variants
    with open('proper_noun_variants.json', 'w', encoding='utf-8') as f:
        json.dump(existing_variants, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Successfully integrated {integrated_count} Ramayana proper nouns into proper_noun_variants.json")
    print(f"📊 Updated sources to include: {existing_variants['_sources']}")

if __name__ == "__main__":
    integrate_ramayana_nouns()
