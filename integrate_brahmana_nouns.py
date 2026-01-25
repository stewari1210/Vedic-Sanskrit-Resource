#!/usr/bin/env python3
"""
Integrate Brahmanas proper nouns into the main proper_noun_variants.json file.

This script takes the extracted Brahmanas proper nouns and adds them to the
existing proper_noun_variants.json file with Brahmanas source information.
"""

import json
from typing import Dict, List, Set

def load_brahmana_nouns() -> Dict:
    """Load the extracted Brahmanas proper nouns."""
    try:
        with open('proper_nouns_brahmanas.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ proper_nouns_brahmanas.json not found. Run extract_brahmana_proper_nouns.py first.")
        return {}

def load_existing_variants() -> Dict:
    """Load the existing proper noun variants."""
    try:
        with open('proper_noun_variants.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ proper_noun_variants.json not found.")
        return {}

def filter_meaningful_nouns(brahmana_data: Dict) -> Dict[str, Dict]:
    """Filter out false positives and keep only meaningful Vedic proper nouns."""
    categories = brahmana_data.get('categories', {})

    # Define known Vedic proper nouns to keep
    meaningful_nouns = {}

    # Sages and Rishis
    sages = ['Kanva', 'Kasyapa', 'Atri', 'Gautama', 'Angiras', 'Gotama']
    for sage in sages:
        if sage in categories.get('sages_rishis', {}):
            meaningful_nouns[sage] = {
                'category': 'sages',
                'occurrences': categories['sages_rishis'][sage],
                'source': 'Satapatha-Brahmana'
            }

    # Kings and Rulers
    kings = ['Pururavas']
    for king in kings:
        if king in categories.get('kings_rulers', {}):
            meaningful_nouns[king] = {
                'category': 'kings_and_heroes',
                'occurrences': categories['kings_rulers'][king],
                'source': 'Satapatha-Brahmana'
            }

    # Tribes and Peoples
    tribes = ['Bharata', 'Kurus', 'Krivis', 'Anu']
    for tribe in tribes:
        if tribe in categories.get('tribes_peoples', {}):
            meaningful_nouns[tribe] = {
                'category': 'tribes_and_kingdoms',
                'occurrences': categories['tribes_peoples'][tribe],
                'source': 'Satapatha-Brahmana'
            }

    # Deities
    deities = ['Agni', 'Indra', 'Soma', 'Rudra', 'Varuna', 'Vishnu', 'Brahma', 'Savitr', 'Mitra', 'Vayu', 'Pushan', 'Bhaga']
    for deity in deities:
        if deity in categories.get('deities', {}):
            meaningful_nouns[deity] = {
                'category': 'deities',
                'occurrences': categories['deities'][deity],
                'source': 'Satapatha-Brahmana'
            }

    # Places and Rivers
    places = ['Yamuna', 'Sindhu']
    for place in places:
        if place in categories.get('places_rivers', {}):
            meaningful_nouns[place] = {
                'category': 'rivers_and_geography',
                'occurrences': categories['places_rivers'][place],
                'source': 'Satapatha-Brahmana'
            }

    # Schools and Traditions
    schools = ['Madhyandina', 'Taittiriya', 'Apastamba', 'Baudhayana']
    for school in schools:
        if school in categories.get('schools_traditions', {}):
            meaningful_nouns[school] = {
                'category': 'schools_traditions',
                'occurrences': categories['schools_traditions'][school],
                'source': 'Satapatha-Brahmana'
            }

    return meaningful_nouns

def integrate_brahmana_nouns(existing_variants: Dict, brahmana_nouns: Dict) -> Dict:
    """Integrate Brahmanas nouns into the existing variants structure."""
    updated_variants = existing_variants.copy()

    # Update the last_updated timestamp
    updated_variants["_last_updated"] = "2025-01-25"

    # Add Brahmanas to sources
    current_sources = updated_variants.get("_sources", "")
    if "Satapatha-Brahmana" not in current_sources:
        if current_sources:
            updated_variants["_sources"] = current_sources + " + Satapatha-Brahmana"
        else:
            updated_variants["_sources"] = "Satapatha-Brahmana"

    for noun_name, noun_data in brahmana_nouns.items():
        category = noun_data['category']
        occurrences = noun_data['occurrences']
        source = noun_data['source']

        # Check if this noun already exists in the variants
        if category in updated_variants and noun_name in updated_variants[category]:
            # Noun exists, update sources and occurrences
            existing_entry = updated_variants[category][noun_name]

            # Handle sources field - can be dict or list
            sources = existing_entry.get('sources', {})
            if isinstance(sources, dict):
                # Dict format: add/update count
                if source not in sources:
                    sources[source] = occurrences
                    existing_entry['total_occurrences'] = existing_entry.get('total_occurrences', 0) + occurrences
                elif sources[source] < occurrences:
                    # Update if new count is higher
                    existing_entry['total_occurrences'] = existing_entry.get('total_occurrences', 0) + (occurrences - sources[source])
                    sources[source] = occurrences
            elif isinstance(sources, list):
                # List format: append if not present
                if source not in sources:
                    sources.append(source)
                    existing_entry['total_occurrences'] = existing_entry.get('total_occurrences', 0) + occurrences

            # Update priority if needed (Brahmanas might have different priority)
            if existing_entry.get('priority') == 'LOW' and occurrences > 5:
                existing_entry['priority'] = 'MEDIUM'

        else:
            # New noun, create entry
            if category not in updated_variants:
                updated_variants[category] = {}

            # Create new entry based on category
            if category == 'sages':
                updated_variants[category][noun_name] = {
                    "variants": [noun_name],  # Could add variants later
                    "role": "Sage (Rshi)",
                    "sources": {source: occurrences},
                    "total_occurrences": occurrences,
                    "priority": "MEDIUM" if occurrences > 10 else "LOW"
                }
            elif category == 'kings_and_heroes':
                updated_variants[category][noun_name] = {
                    "canonical": noun_name,
                    "variants": [noun_name],
                    "role": "King/Hero",
                    "sources": {source: occurrences},
                    "total_occurrences": occurrences,
                    "priority": "MEDIUM" if occurrences > 5 else "LOW"
                }
            elif category == 'tribes_and_kingdoms':
                updated_variants[category][noun_name] = {
                    "canonical": noun_name,
                    "variants": [noun_name],
                    "role": "Tribe/Kingdom",
                    "sources": {source: occurrences},
                    "total_occurrences": occurrences,
                    "priority": "MEDIUM" if occurrences > 10 else "LOW"
                }
            elif category == 'deities':
                updated_variants[category][noun_name] = {
                    "variants": [noun_name],
                    "role": "Deity",
                    "sources": {source: occurrences},
                    "total_occurrences": occurrences,
                    "priority": "HIGH" if occurrences > 100 else "MEDIUM"
                }
            elif category == 'rivers_and_geography':
                updated_variants[category][noun_name] = {
                    "canonical": noun_name,
                    "variants": [noun_name],
                    "role": "River/Geographical Feature",
                    "sources": {source: occurrences},
                    "total_occurrences": occurrences,
                    "priority": "MEDIUM" if occurrences > 5 else "LOW"
                }
            elif category == 'schools_traditions':
                updated_variants[category][noun_name] = {
                    "canonical": noun_name,
                    "variants": [noun_name],
                    "role": "Vedic School/Tradition",
                    "sources": {source: occurrences},
                    "total_occurrences": occurrences,
                    "priority": "MEDIUM"
                }

    return updated_variants

def main():
    """Main integration function."""
    print("🔄 Integrating Brahmanas proper nouns into variants database...")

    # Load data
    brahmana_data = load_brahmana_nouns()
    if not brahmana_data:
        return

    existing_variants = load_existing_variants()
    if not existing_variants:
        return

    # Filter meaningful nouns
    meaningful_nouns = filter_meaningful_nouns(brahmana_data)
    print(f"📋 Found {len(meaningful_nouns)} meaningful proper nouns from Brahmanas")

    # Show what we're adding
    print("\n📚 Brahmanas proper nouns to integrate:")
    for noun, data in meaningful_nouns.items():
        print(f"  {noun} ({data['category']}): {data['occurrences']} occurrences")

    # Integrate into existing variants
    updated_variants = integrate_brahmana_nouns(existing_variants, meaningful_nouns)

    # Save updated variants
    with open('proper_noun_variants.json', 'w', encoding='utf-8') as f:
        json.dump(updated_variants, f, indent=2, ensure_ascii=False)

    print("✅ Successfully integrated Brahmanas proper nouns into proper_noun_variants.json")

    # Show summary of changes
    print("\n📊 Integration Summary:")
    print(f"  Original entries: {len(existing_variants) - 1} categories")  # -1 for metadata
    print(f"  Added/Updated: {len(meaningful_nouns)} proper nouns")
    print(f"  New source: Satapatha-Brahmana")

if __name__ == "__main__":
    main()