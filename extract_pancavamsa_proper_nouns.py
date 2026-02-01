#!/usr/bin/env python3
"""
Extract proper nouns from the Pancavamsa Brahmana text.
Identifies deity names, sage names, ritual names, and geographic locations.
"""

import re
import json
from collections import Counter
from pathlib import Path

def extract_proper_nouns_from_pancavamsa(text_file: str) -> dict:
    """
    Extract proper nouns from Pancavamsa Brahmana.
    
    Returns dictionary with categorized proper nouns.
    """
    with open(text_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    proper_nouns = {
        'deity_names': [],
        'sage_names': [],
        'ritual_names': [],
        'location_names': [],
        'sakha_names': [],
        'uncategorized': []
    }
    
    # Pattern 1: Deity names (typically capitalized, often appear with 'god')
    deity_pattern = r'\b([A-Z][a-z]+(?:\s+(?:god|God|Deva|Devata|Lord))?)\b'
    
    # Pattern 2: Sanskrit proper nouns in parentheses or transliteration
    sanskrit_pattern = r'\(([A-Z][a-zā-ū]*(?:\s+[A-Z][a-zā-ū]*)*)\)'
    
    # Extract candidates from specific contexts
    lines = content.split('\n')
    
    deity_candidates = set()
    sage_candidates = set()
    ritual_candidates = set()
    location_candidates = set()
    
    # Known deity names in Vedic texts
    known_deities = {
        'Agni', 'Indra', 'Soma', 'Yama', 'Varuna', 'Mitra', 'Aditya',
        'Surya', 'Chandra', 'Rudra', 'Vishnu', 'Brahma', 'Shiva', 'Devi',
        'Saraswati', 'Lakshmi', 'Parvati', 'Uma', 'Marut', 'Vata', 'Parjanya',
        'Pushan', 'Savitri', 'Aryaman', 'Bhaga', 'Tvashtar', 'Dhvani', 'Ashvins'
    }
    
    # Known sage names
    known_sages = {
        'Atharvan', 'Angiras', 'Bhrigu', 'Vasishtha', 'Vamadeva', 'Visvamitra',
        'Kanva', 'Gritsamada', 'Paijavana', 'Apastamba', 'Baudhayana', 'Hiranyakeshin',
        'Katyayana', 'Manava', 'Gobhila', 'Drahoma', 'Asvalayana', 'Paraskara'
    }
    
    # Known ritual names
    known_rituals = {
        'Agnihotra', 'Darshapurnamasa', 'Caturmasya', 'Pasubandhа', 'Pravargya',
        'Upasad', 'Soma', 'Sautramani', 'Atyagniṣtoma', 'Ukthya', 'Shodasin',
        'Aptoryama', 'Atiratra', 'Vājapeya', 'Rājasuya', 'Aśvamedha'
    }
    
    # Extract from text
    for line in lines:
        # Look for capitalized words
        words = re.findall(r'\b[A-Z][a-z]+(?:[a-z]+)?\b', line)
        for word in words:
            if word in known_deities:
                deity_candidates.add(word)
            elif word in known_sages:
                sage_candidates.add(word)
            elif word in known_rituals:
                ritual_candidates.add(word)
        
        # Look for Sanskrit transliteration patterns
        sanskrit_matches = re.findall(r'\(([A-Za-zāēīōū\s]+)\)', line)
        for match in sanskrit_matches:
            if match and len(match) > 2:
                if any(d in match for d in known_deities):
                    deity_candidates.add(match.strip())
                elif any(s in match for s in known_sages):
                    sage_candidates.add(match.strip())
        
        # Geographic references
        if 'River' in line or 'region' in line or 'country' in line:
            geo_words = re.findall(r'\b([A-Z][a-z]+(?:[a-z]+)?)\b', line)
            location_candidates.update(geo_words)
    
    # Convert to lists
    proper_nouns['deity_names'] = sorted(list(deity_candidates))
    proper_nouns['sage_names'] = sorted(list(sage_candidates))
    proper_nouns['ritual_names'] = sorted(list(ritual_candidates))
    
    # Additional extraction: Look for patterns with specific markers
    for line in lines:
        # Ritual names often follow specific patterns
        if 'sacrifice' in line.lower() or 'ritual' in line.lower():
            matches = re.findall(r'\b([A-Z][a-zā-ū]+(?:[a-zā-ū]*)?)\b', line)
            ritual_candidates.update(m for m in matches if len(m) > 3)
    
    return proper_nouns


def extract_section_proper_nouns(text_file: str) -> dict:
    """
    Extract proper nouns organized by section/chapter.
    """
    with open(text_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    sections = {}
    current_section = "Introduction"
    current_nouns = set()
    
    for line in lines:
        # Check for chapter/section markers
        if 'CHAPTER' in line.upper() or 'BOOK' in line.upper():
            if current_section and current_nouns:
                sections[current_section] = sorted(list(current_nouns))
            current_section = line.strip()[:80]  # Truncate for readability
            current_nouns = set()
        
        # Extract capitalized words as potential proper nouns
        words = re.findall(r'\b[A-Z][a-z]{2,}(?:[a-z]+)?\b', line)
        current_nouns.update(words)
    
    # Add final section
    if current_section and current_nouns:
        sections[current_section] = sorted(list(current_nouns))
    
    return sections


def main():
    """Main extraction function."""
    text_file = "local_store/prose_vedas/pancavamsa_brahmana/pancavamsa_brahmana.txt"
    
    if not Path(text_file).exists():
        print(f"❌ Text file not found: {text_file}")
        return
    
    print("🔍 Extracting proper nouns from Pancavamsa Brahmana...")
    print()
    
    # Method 1: Direct categorization
    proper_nouns = extract_proper_nouns_from_pancavamsa(text_file)
    
    print("📌 CATEGORIZED PROPER NOUNS:")
    print("=" * 50)
    
    for category, nouns in proper_nouns.items():
        if nouns:
            print(f"\n{category.replace('_', ' ').title()}:")
            print(f"  Count: {len(nouns)}")
            print(f"  Examples: {', '.join(sorted(set(nouns))[:10])}")
    
    # Method 2: Extract by section
    print("\n\n📑 PROPER NOUNS BY SECTION:")
    print("=" * 50)
    
    section_nouns = extract_section_proper_nouns(text_file)
    
    print(f"\nTotal sections identified: {len(section_nouns)}")
    print("\nFirst 5 sections with noun counts:")
    for i, (section, nouns) in enumerate(list(section_nouns.items())[:5]):
        print(f"  {i+1}. {section}: {len(nouns)} unique nouns")
        print(f"     Examples: {', '.join(sorted(set(nouns))[:5])}")
    
    # Save extracted nouns to JSON
    output_file = "pancavamsa_brahmana_proper_nouns.json"
    
    output = {
        "source": "Pancavamsa Brahmana",
        "translator": "W. Caland",
        "publication_date": 1931,
        "extraction_date": "2026-01-31",
        "categorized_nouns": proper_nouns,
        "section_statistics": {
            "total_sections": len(section_nouns),
            "sections": list(section_nouns.keys())[:10] if section_nouns else []
        },
        "notes": "Preliminary extraction. Requires manual review and categorization for accurate integration into proper noun variants database."
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n\n✅ Extraction complete!")
    print(f"📄 Results saved to: {output_file}")
    print(f"\nTotal entries extracted: {sum(len(v) for v in proper_nouns.values())}")


if __name__ == "__main__":
    main()
