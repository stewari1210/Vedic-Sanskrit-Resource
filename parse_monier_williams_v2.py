"""
Improved Monier-Williams Parser - Version 2
Focus on high-quality Sanskrit→English and English→Sanskrit mappings
"""
import re
import json
from collections import defaultdict
from typing import Dict, List, Set

def parse_dictionary_line(line: str) -> tuple:
    """
    Parse a single dictionary entry line
    Returns (sanskrit_word, english_meanings) or (None, None) if not a valid entry
    """
    # Skip empty lines or lines that are too short
    if not line or len(line) < 10:
        return None, None

    # Look for patterns like:
    # "payas, n. milk, water"
    # "dugdha, mfn. milked; (am), n. milk"
    # "icchati, desires, wants"

    # Pattern 1: word, grammatical_marker. definition
    pattern1 = r'^([a-zA-Z\-āīūṛṝḷḹēōṃḥśṣṇṅñṭḍ]+),\s+(m\.|f\.|n\.|mfn\.|ind\.|adj\.|adv\.)\s+(.+)'
    match = re.match(pattern1, line)

    if match:
        sanskrit = match.group(1).strip()
        grammar = match.group(2).strip()
        definition = match.group(3).strip()

        # Extract clean English meanings
        # Remove references like "RV.", "AV.", "MBh.", etc.
        definition = re.sub(r'\b(RV|AV|VS|TS|SBr|MBh|BhP|Pan|Mn)\b\.?', '', definition)

        # Extract meanings before semicolons or parentheses
        meanings = re.split(r'[;()]', definition)[0].strip()

        # Split on commas
        meaning_list = [m.strip() for m in meanings.split(',')]

        # Filter out empty or too long meanings
        meaning_list = [m for m in meaning_list if m and len(m.split()) <= 4]

        return sanskrit, meaning_list

    return None, None

def build_bidirectional_dict(filepath: str) -> tuple:
    """
    Build both Sanskrit→English and English→Sanskrit dictionaries
    """
    skt_to_eng = defaultdict(set)
    eng_to_skt = defaultdict(set)

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            sanskrit, meanings = parse_dictionary_line(line)

            if sanskrit and meanings:
                for meaning in meanings:
                    # Clean the meaning
                    meaning = meaning.lower().strip()

                    # Skip if looks like metadata or too technical
                    if any(skip in meaning for skip in ['cf.', 'see', 'fr.', 'n. of', 'pr. n.']):
                        continue

                    # Skip single letters or numbers
                    if len(meaning) < 3 or meaning.isdigit():
                        continue

                    # Add to both dictionaries
                    skt_to_eng[sanskrit].add(meaning)
                    eng_to_skt[meaning].add(sanskrit)

    return skt_to_eng, eng_to_skt

def load_basic_lexicon():
    """Load the manual BASIC_LEXICON for comparison and extension"""
    basic = {
        "milk": ["payas", "payaḥ", "kṣīra", "dugdha", "दुग्ध", "पयस्"],
        "water": ["ap", "āpaḥ", "udaka", "jala", "अपः", "जल", "उदक"],
        "want": ["√iṣ", "icchāmi", "इच्छामि"],
        "give": ["√dā", "dadāti", "dehi", "दत्त", "ददाति"],
        "I": ["aham", "अहम्"],
        "you": ["tvam", "त्वम्", "bhavān", "भवान्"],
        "food": ["anna", "अन्न", "āhāra", "आहार", "bhojana", "भोजन"],
        "good": ["sundara", "सुन्दर", "śubha", "शुभ", "uttama", "उत्तम"],
        "morning": ["prātaḥ", "प्रातः", "uṣas", "उषस्"],
        "evening": ["sāyam", "सायम्"],
        "day": ["dina", "दिन", "ahar", "अहर्"],
        "night": ["rātri", "रात्रि", "niśā", "निशा"],
        "sun": ["sūrya", "सूर्य", "ravi", "रवि"],
        "moon": ["candra", "चन्द्र", "soma", "सोम"],
        "fire": ["agni", "अग्नि"],
        "earth": ["pṛthivī", "पृथिवी", "bhūmi", "भूमि"],
        "sky": ["ākāśa", "आकाश", "dyaus", "द्यौस्"],
        "wind": ["vāyu", "वायु", "vāta", "वात"],
        "king": ["rājan", "राजन्", "nṛpati", "नृपति"],
        "priest": ["brāhmaṇa", "ब्राह्मण"],
        "god": ["deva", "देव"],
        "man": ["puruṣa", "पुरुष", "nara", "नर"],
        "woman": ["strī", "स्त्री", "nārī", "नारी"],
        "son": ["putra", "पुत्र"],
        "daughter": ["duhitṛ", "दुहितृ", "putrī", "पुत्री"],
        "father": ["pitṛ", "पितृ"],
        "mother": ["mātṛ", "मातृ"],
        "brother": ["bhrātṛ", "भ्रातृ"],
        "sister": ["svasṛ", "स्वसृ", "bhaginī", "भगिनी"],
        "cow": ["go", "गो", "dhenu", "धेनु"],
        "horse": ["aśva", "अश्व"],
        "tree": ["vṛkṣa", "वृक्ष", "taru", "तरु"],
        "river": ["nadī", "नदी"],
        "mountain": ["parvata", "पर्वत", "giri", "गिरि"],
        "house": ["gṛha", "गृह", "sadma", "सद्मा"],
        "city": ["nagara", "नगर", "pura", "पुर"],
        "one": ["eka", "एक"],
        "two": ["dvi", "द्वि", "dva", "द्व"],
        "three": ["tri", "त्रि"],
        "four": ["catur", "चतुर्"],
        "five": ["pañca", "पञ्च"],
        "ten": ["daśa", "दश"],
        "hundred": ["śata", "शत"],
        "thousand": ["sahasra", "सहस्र"],
    }
    return basic

def merge_with_basic_lexicon(eng_to_skt: Dict[str, Set[str]]) -> Dict[str, List[str]]:
    """Merge parsed dictionary with manually curated BASIC_LEXICON"""
    basic = load_basic_lexicon()
    merged = defaultdict(set)

    # Start with parsed dictionary
    for eng, skts in eng_to_skt.items():
        merged[eng].update(skts)

    # Add/override with basic lexicon (higher quality)
    for eng, skts in basic.items():
        merged[eng].update(skts)

    # Convert to sorted lists
    result = {eng: sorted(list(skts)) for eng, skts in merged.items()}
    return result

def save_dictionary(data: Dict[str, List[str]], filepath: str):
    """Save dictionary to JSON"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)

def main():
    print("Monier-Williams Dictionary Parser v2")
    print("=" * 70)

    # Parse dictionary
    print("\n1. Parsing dictionary file...")
    skt_to_eng, eng_to_skt = build_bidirectional_dict('monier_williams_dictionary.txt')

    print(f"   Sanskrit→English entries: {len(skt_to_eng)}")
    print(f"   English→Sanskrit entries: {len(eng_to_skt)}")

    # Merge with basic lexicon
    print("\n2. Merging with curated BASIC_LEXICON...")
    merged = merge_with_basic_lexicon(eng_to_skt)
    print(f"   Total English terms: {len(merged)}")

    # Save
    print("\n3. Saving dictionaries...")
    save_dictionary(merged, 'sanskrit_dictionary.json')
    print("   ✓ Saved: sanskrit_dictionary.json")

    # Test common words
    print("\n4. Testing common words:")
    print("-" * 70)
    test_words = ['milk', 'water', 'want', 'give', 'good', 'morning',
                  'food', 'drink', 'fire', 'sun', 'king', 'father']

    for word in test_words:
        if word in merged:
            skts = merged[word]
            print(f"   {word:12} → {', '.join(skts[:5])}{'...' if len(skts) > 5 else ''}")
        else:
            print(f"   {word:12} → (not found)")

    print("\n" + "=" * 70)
    print("✓ Dictionary ready for agentic RAG integration!")
    print(f"✓ {len(merged)} English→Sanskrit mappings available")

if __name__ == '__main__':
    main()
