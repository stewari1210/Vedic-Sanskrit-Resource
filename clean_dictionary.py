#!/usr/bin/env python3
"""
Clean the Sanskrit dictionary by:
1. Removing entries with OCR errors (special chars, very short words)
2. Adding high-quality curated entries for common words
3. Fixing known incorrect entries
"""

import json
import re

# Load existing dictionary
with open('sanskrit_dictionary.json', 'r', encoding='utf-8') as f:
    original_dict = json.load(f)

print(f"Original dictionary: {len(original_dict)} entries")

# High-quality curated entries (override any existing bad entries)
CURATED_ENTRIES = {
    # Emotions and relationships
    "love": ["preman", "prema", "प्रेम", "sneha", "स्नेह", "prīti", "प्रीति", "anurāga", "अनुराग"],
    "like": ["prīyate", "प्रीयते", "rocate", "रोचते", "iṣṭa", "इष्ट"],
    "friend": ["mitra", "मित्र", "sakhā", "सखा", "bandhu", "बन्धु"],
    "mother": ["mātṛ", "मातृ", "ambā", "अम्बा", "jananī", "जननी"],
    "father": ["pitṛ", "पितृ", "pitā", "पिता", "tāta", "तात"],
    "son": ["putra", "पुत्र", "suta", "सुत"],
    "daughter": ["putrī", "पुत्री", "sutā", "सुता", "duhitṛ", "दुहितृ"],
    "brother": ["bhrātṛ", "भ्रातृ", "bhrātā", "भ्राता"],
    "sister": ["svasṛ", "स्वसृ", "svasā", "स्वसा", "bhaginī", "भगिनी"],

    # Common verbs
    "want": ["icchāmi", "इच्छामि", "kāṅkṣāmi", "काङ्क्षामि", "iṣ", "इष्"],
    "give": ["dadāmi", "ददामि", "yacchāmi", "यच्छामि", "dā", "दा"],
    "go": ["gacchāmi", "गच्छामि", "yāmi", "यामि", "gam", "गम्"],
    "come": ["āgacchāmi", "आगच्छामि", "āyāmi", "आयामि"],
    "see": ["paśyāmi", "पश्यामि", "dṛś", "दृश्", "īkṣe", "ईक्षे"],
    "hear": ["śṛṇomi", "शृणोमि", "śru", "श्रु"],
    "speak": ["vadāmi", "वदामि", "vad", "वद्", "kathayāmi", "कथयामि"],
    "know": ["jānāmi", "जानामि", "jñā", "ज्ञा", "vid", "विद्"],
    "think": ["cintayāmi", "चिन्तयामि", "manye", "मन्ये", "man", "मन्"],
    "do": ["karomi", "करोमि", "kṛ", "कृ"],
    "make": ["karomi", "करोमि", "kṛ", "कृ"],
    "eat": ["khādāmi", "खादामि", "bhakṣayāmi", "भक्षयामि", "ad", "अद्"],
    "drink": ["pibāmi", "पिबामि", "pā", "पा"],
    "sleep": ["svapāmi", "स्वपामि", "svap", "स्वप्"],

    # Common nouns
    "water": ["jala", "जल", "āpaḥ", "आपः", "udaka", "उदक", "toya", "तोय"],
    "milk": ["dugdha", "दुग्ध", "kṣīra", "क्षीर", "payas", "पयस्"],
    "food": ["anna", "अन्न", "bhojana", "भोजन", "āhāra", "आहार"],
    "bread": ["piṣṭaka", "पिष्टक", "roṭikā", "रोटिका"],
    "rice": ["vrīhi", "व्रीहि", "taṇḍula", "तण्डुल", "odana", "ओदन"],
    "fire": ["agni", "अग्नि", "vahni", "वह्नि", "pāvaka", "पावक"],
    "earth": ["pṛthivī", "पृथिवी", "bhūmi", "भूमि", "dharā", "धरा"],
    "sky": ["ākāśa", "आकाश", "gagana", "गगन", "vyoman", "व्योमन्"],
    "sun": ["sūrya", "सूर्य", "āditya", "आदित्य", "ravi", "रवि"],
    "moon": ["candra", "चन्द्र", "śaśin", "शशिन्", "soma", "सोम"],
    "house": ["gṛha", "गृह", "veśman", "वेश्मन्", "sadana", "सदन"],
    "tree": ["vṛkṣa", "वृक्ष", "taru", "तरु", "pādapa", "पादप"],

    # Greetings and common phrases
    "hello": ["namaste", "नमस्ते", "namaskāra", "नमस्कार"],
    "good": ["śubha", "शुभ", "sat", "सत्", "sādhu", "साधु"],
    "morning": ["prātaḥ", "प्रातः", "uṣas", "उषस्"],
    "night": ["rātri", "रात्रि", "niśā", "निशा"],
    "day": ["dina", "दिन", "divasa", "दिवस", "vāra", "वार"],
    "time": ["kāla", "काल", "samaya", "समय"],
    "place": ["deśa", "देश", "sthāna", "स्थान"],

    # Pronouns
    "i": ["aham", "अहम्"],
    "you": ["tvam", "त्वम्", "bhavān", "भवान्"],
    "he": ["saḥ", "सः", "eṣaḥ", "एषः"],
    "she": ["sā", "सा", "eṣā", "एषा"],
    "we": ["vayam", "वयम्"],
    "they": ["te", "ते"],

    # Numbers
    "one": ["eka", "एक"],
    "two": ["dvi", "द्वि", "dvau", "द्वौ"],
    "three": ["tri", "त्रि", "trayaḥ", "त्रयः"],
    "four": ["catur", "चतुर्", "catvāraḥ", "चत्वारः"],
    "five": ["pañca", "पञ्च"],
    "ten": ["daśa", "दश"],
}

def is_valid_sanskrit(word):
    """Check if a word looks like valid Sanskrit (not OCR noise)."""
    if not word or len(word) < 2:
        return False

    # Check for obvious OCR noise patterns
    noise_patterns = [
        r'^[-#$!&*]',  # Starts with special chars
        r'[0-9]{2,}',  # Multiple consecutive digits
        r'[A-Z]{3,}[a-z]*$',  # Multiple capital letters not in Devanagari
        r'^[^a-zA-Zāīūṛṃḥśṣṭḍṇṅñṅक-ह]+$',  # No valid letters at all
    ]

    for pattern in noise_patterns:
        if re.search(pattern, word):
            return False

    return True

def is_valid_english(word):
    """Check if an English word is valid (not OCR noise)."""
    if not word or len(word) < 2:
        return False

    # Must be mostly lowercase letters
    if not re.match(r'^[a-z][a-z\s\-\']*$', word.lower()):
        return False

    # Check for obvious noise
    if word.startswith(('#', '$', '!', '*', '&')):
        return False

    return True

def clean_sanskrit_terms(terms):
    """Filter out invalid Sanskrit terms from a list."""
    return [t for t in terms if is_valid_sanskrit(t)]

# Clean the dictionary
cleaned_dict = {}
removed_count = 0
cleaned_term_count = 0

for eng_word, sanskrit_terms in original_dict.items():
    # Skip if English word is invalid
    if not is_valid_english(eng_word):
        removed_count += 1
        continue

    # Filter Sanskrit terms
    cleaned_terms = clean_sanskrit_terms(sanskrit_terms)

    # Only keep if we have at least one valid term
    if cleaned_terms:
        cleaned_dict[eng_word] = cleaned_terms
    else:
        removed_count += 1

    cleaned_term_count += len(sanskrit_terms) - len(cleaned_terms)

print(f"Removed {removed_count} invalid English entries")
print(f"Removed {cleaned_term_count} invalid Sanskrit terms")
print(f"Cleaned dictionary: {len(cleaned_dict)} entries")

# Add/override with curated entries
print(f"\nAdding/overriding {len(CURATED_ENTRIES)} curated entries")
for eng, skt in CURATED_ENTRIES.items():
    if eng in cleaned_dict:
        print(f"  Overriding '{eng}': {cleaned_dict[eng]} → {skt}")
    else:
        print(f"  Adding '{eng}': {skt}")
    cleaned_dict[eng] = skt

# Save cleaned dictionary
with open('sanskrit_dictionary_cleaned.json', 'w', encoding='utf-8') as f:
    json.dump(cleaned_dict, f, ensure_ascii=False, indent=2)

print(f"\nSaved cleaned dictionary with {len(cleaned_dict)} entries")
print(f"File: sanskrit_dictionary_cleaned.json")

# Show some examples
print("\n=== Sample entries ===")
for word in ["love", "milk", "water", "want", "good", "mother"]:
    if word in cleaned_dict:
        print(f"{word}: {cleaned_dict[word][:5]}")
