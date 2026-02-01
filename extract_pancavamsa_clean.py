#!/usr/bin/env python3
"""
Extract proper nouns from Pancavamsa Brahmana and integrate with existing variants.
"""

import json
import re
from pathlib import Path
from collections import defaultdict

# Known Vedic entities that should be in proper nouns database
VEDIC_DEITIES = {
    'Agni', 'Indra', 'Soma', 'Yama', 'Varuna', 'Mitra', 'Aditya',
    'Surya', 'Chandra', 'Rudra', 'Vishnu', 'Brahma', 'Shiva', 'Devi',
    'Saraswati', 'Lakshmi', 'Parvati', 'Uma', 'Marut', 'Vata', 'Parjanya',
    'Pushan', 'Savitri', 'Aryaman', 'Bhaga', 'Tvashtar', 'Ashvins',
    'Vyu', 'Prithvi', 'Dyaus', 'Ushhas', 'Ratri', 'Purusha', 'Prajapati',
    'Brihaspati', 'Brahmanaspati', 'Ribhus', 'Maruts', 'Adityas'
}

VEDIC_SAGES = {
    'Atharvan', 'Angiras', 'Bhrigu', 'Vasishtha', 'Vamadeva', 'Visvamitra',
    'Kanva', 'Gritsamada', 'Paijavana', 'Apastamba', 'Baudhayana', 'Hiranyakeshin',
    'Katyayana', 'Manava', 'Gobhila', 'Drahoma', 'Asvalayana', 'Paraskara',
    'Bodhyana', 'Aswalayana', 'Sankhayana', 'Latyayana', 'Drahoma', 'Jasthakauthuma'
}

VEDIC_SCHOOLS = {
    'Kauthuma', 'Ranayaniyas', 'Jaiminlya', 'Sakalya', 'Ranayaniya',
    'Jaiminiya', 'Taittiriya', 'Katha', 'Maitrayani', 'Caraka'
}

VEDIC_RITUALS = {
    'Agnihotra', 'Darshapurnamasa', 'Caturmasya', 'Pasabandhа', 'Pravargya',
    'Upasad', 'Soma', 'Sautramani', 'Atyagniṣtoma', 'Ukthya', 'Shodasin',
    'Aptoryama', 'Atiratra', 'Vājapeya', 'Rājasuya', 'Aśvamedha',
    'Sattra', 'Samvatsara', 'Ekaha', 'Ahina'
}

VEDIC_LOCATIONS = {
    'Kurukshetra', 'Ayodhya', 'Mathura', 'Indraprastha', 'Ujjain',
    'Kashi', 'Varanasi', 'Gaya', 'Prayag', 'Yamuna', 'Ganga', 'Saraswati'
}


def extract_clean_proper_nouns(text_file: str) -> dict:
    """Extract proper nouns from Pancavamsa with better filtering."""
    
    with open(text_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Remove common OCR artifacts and headers
    lines = content.split('\n')
    cleaned_lines = []
    for line in lines:
        # Skip table of contents, page markers, and noise
        if any(skip in line for skip in ['page', 'TABLE OF CONTENTS', 'CONTENTS', 
                                          'BIBLIOTHECA', 'Work No.', 'Printed at',
                                          'Published by', 'DLI', '©']):
            continue
        cleaned_lines.append(line)
    
    content = '\n'.join(cleaned_lines)
    
    # Find proper nouns in specific contexts
    extracted = {
        'deities': set(),
        'sages': set(),
        'schools': set(),
        'rituals': set(),
        'locations': set(),
        'other_proper_nouns': set()
    }
    
    # Look for names near specific markers
    
    # 1. Deity references (often near "god", "deva", "lord")
    deity_contexts = re.findall(
        r'\b(' + '|'.join(re.escape(d) for d in VEDIC_DEITIES) + r')\b',
        content, re.IGNORECASE
    )
    extracted['deities'].update(deity_contexts)
    
    # 2. Sage references (often near "rishi", "sage", "seer")
    sage_contexts = re.findall(
        r'\b(' + '|'.join(re.escape(s) for s in VEDIC_SAGES) + r')\b',
        content, re.IGNORECASE
    )
    extracted['sages'].update(sage_contexts)
    
    # 3. School references
    school_contexts = re.findall(
        r'\b(' + '|'.join(re.escape(s) for s in VEDIC_SCHOOLS) + r')\b',
        content, re.IGNORECASE
    )
    extracted['schools'].update(school_contexts)
    
    # 4. Ritual references
    ritual_contexts = re.findall(
        r'\b(' + '|'.join(re.escape(r) for r in VEDIC_RITUALS) + r')\b',
        content, re.IGNORECASE
    )
    extracted['rituals'].update(ritual_contexts)
    
    # 5. Location references
    location_contexts = re.findall(
        r'\b(' + '|'.join(re.escape(l) for l in VEDIC_LOCATIONS) + r')\b',
        content, re.IGNORECASE
    )
    extracted['locations'].update(location_contexts)
    
    # Convert sets to sorted lists for JSON serialization
    result = {}
    for category, items in extracted.items():
        result[category] = sorted(list(items))
    
    return result


def load_existing_proper_nouns(json_file: str) -> dict:
    """Load existing proper noun variants database."""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}


def create_pancavamsa_entry(extracted_nouns: dict) -> dict:
    """Create a Pancavamsa Brahmana entry for the proper nouns database."""
    return {
        "source": "Pancavamsa Brahmana",
        "translator": "W. Caland",
        "publication_date": 1931,
        "text_type": "prose_veda",
        "vedic_school": "Samaveda",
        "extracted_nouns": extracted_nouns,
        "statistics": {
            "deities": len(extracted_nouns.get('deities', [])),
            "sages": len(extracted_nouns.get('sages', [])),
            "schools": len(extracted_nouns.get('schools', [])),
            "rituals": len(extracted_nouns.get('rituals', [])),
            "locations": len(extracted_nouns.get('locations', []))
        }
    }


def main():
    """Main function."""
    text_file = "local_store/prose_vedas/pancavamsa_brahmana/pancavamsa_brahmana.txt"
    variants_db = "proper_noun_variants.json"
    
    if not Path(text_file).exists():
        print(f"❌ Text file not found: {text_file}")
        return
    
    print("🔍 Extracting Pancavamsa Brahmana proper nouns...")
    print()
    
    # Extract proper nouns
    extracted = extract_clean_proper_nouns(text_file)
    
    # Display results
    print("📌 EXTRACTED PROPER NOUNS:")
    print("=" * 60)
    
    for category, nouns in extracted.items():
        if nouns:
            print(f"\n{category.replace('_', ' ').title()}:")
            print(f"  Count: {len(nouns)}")
            if len(nouns) <= 10:
                print(f"  Items: {', '.join(nouns)}")
            else:
                print(f"  Items: {', '.join(nouns[:10])} ... and {len(nouns) - 10} more")
    
    # Create entry
    entry = create_pancavamsa_entry(extracted)
    
    # Save to new file
    output_file = "pancavamsa_brahmana_proper_nouns_extracted.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(entry, f, indent=2, ensure_ascii=False)
    
    print(f"\n\n✅ Extraction complete!")
    print(f"📄 Saved to: {output_file}")
    print("\n📊 STATISTICS:")
    print(f"  Total deities: {entry['statistics']['deities']}")
    print(f"  Total sages: {entry['statistics']['sages']}")
    print(f"  Total schools: {entry['statistics']['schools']}")
    print(f"  Total rituals: {entry['statistics']['rituals']}")
    print(f"  Total locations: {entry['statistics']['locations']}")
    
    # Load existing database
    print(f"\n\n📚 Loading existing database: {variants_db}")
    existing_db = load_existing_proper_nouns(variants_db)
    
    # Add Pancavamsa entry
    if "prose_vedas" not in existing_db:
        existing_db["prose_vedas"] = {}
    
    existing_db["prose_vedas"]["pancavamsa_brahmana"] = entry
    
    # Save updated database
    print(f"💾 Updating database with Pancavamsa entries...")
    with open(variants_db, 'w', encoding='utf-8') as f:
        json.dump(existing_db, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Database updated: {variants_db}")
    print(f"\nNext step: Review extracted proper nouns for accuracy and add custom variants")


if __name__ == "__main__":
    main()
