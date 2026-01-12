#!/usr/bin/env python3
"""Add common conversational words and phrases to the cleaned dictionary."""

import json

# Load existing dictionary
with open('sanskrit_dictionary_cleaned.json', 'r', encoding='utf-8') as f:
    dictionary = json.load(f)

print(f"Current dictionary size: {len(dictionary)} entries")

# Essential conversational words to add
conversational_entries = {
    "how": ["katham", "कथम्", "kena prakāreṇa", "केन प्रकारेण"],
    "are": ["asi", "असि", "stha", "स्थ"],  # 2nd person singular/plural "to be"
    "is": ["asti", "अस्ति", "bhavati", "भवति"],  # 3rd person singular "to be"
    "am": ["asmi", "अस्मि"],  # 1st person singular "to be"
    "what": ["kim", "किम्", "kaḥ", "कः"],
    "who": ["kaḥ", "कः", "kā", "का"],
    "when": ["kadā", "कदा"],
    "where": ["kutra", "कुत्र", "kva", "क्व"],
    "why": ["kasmāt", "कस्मात्", "kim artham", "किम् अर्थम्"],
    "which": ["kaḥ", "कः", "kā", "का", "kim", "किम्"],
    "yes": ["ām", "आम्", "āḥ", "आः"],
    "no": ["na", "न", "mā", "मा"],
    "please": ["kṛpayā", "कृपया", "dayā kṛtvā", "दया कृत्वा"],
    "thank": ["dhanyavādaḥ", "धन्यवादः", "anugṛhīto'smi", "अनुगृहीतोऽस्मि"],
    "thanks": ["dhanyavādaḥ", "धन्यवादः"],
    "welcome": ["svāgatam", "स्वागतम्"],
    "hello": ["namaste", "नमस्ते", "namaskaromi", "नमस्करोमि"],
    "goodbye": ["punaḥ milāmaḥ", "पुनः मिलामः", "śubham astu", "शुभम् अस्तु"],
    "do": ["karoti", "करोति", "kurvanti", "कुर्वन्ति"],
    "does": ["karoti", "करोति"],
    "did": ["akṛta", "अकृत", "akarot", "अकरोत्"],
    "can": ["śaknoti", "शक्नोति", "samarthaḥ", "समर्थः"],
    "will": ["kariṣyati", "करिष्यति", "bhaviṣyati", "भविष्यति"],
    "would": ["kariṣyat", "करिष्यत्", "abhaviṣyat", "अभविष्यत्"],
    "should": ["kartavyam", "कर्तव्यम्", "yuktam", "युक्तम्"],
    "may": ["bhavatu", "भवतु", "syāt", "स्यात्"],
    "might": ["syāt", "स्यात्"],
    "must": ["kartavyam", "कर्तव्यम्", "āvaśyakam", "आवश्यकम्"],
    "well": ["su", "सु", "sādhu", "साधु", "kuśalam", "कुशलम्"],
    "good": ["sat", "सत्", "sādhu", "साधु", "uttamam", "उत्तमम्"],
    "bad": ["pāpam", "पापम्", "aśobhanam", "अशोभनम्"],
    "very": ["ati", "अति", "bhṛśam", "भृशम्"],
    "much": ["bahu", "बहु", "prabhūtam", "प्रभूतम्"],
    "many": ["bahavaḥ", "बहवः", "anekāni", "अनेकानि"],
    "some": ["kecit", "केचित्", "katicit", "कतिचित्"],
    "all": ["sarve", "सर्वे", "viśve", "विश्वे"],
    "every": ["sarvaḥ", "सर्वः", "pratiḥ", "प्रतिः"],
    "any": ["kaścit", "कश्चित्", "kopi", "कोपि"],
    "here": ["atra", "अत्र", "iha", "इह"],
    "there": ["tatra", "तत्र"],
    "now": ["adhunā", "अधुना", "idānīm", "इदानीम्"],
    "then": ["tadā", "तदा"],
    "today": ["adya", "अद्य"],
    "tomorrow": ["śvaḥ", "श्वः"],
    "yesterday": ["hyaḥ", "ह्यः"],
    "this": ["ayam", "अयम्", "iyam", "इयम्", "idam", "इदम्"],
    "that": ["saḥ", "सः", "sā", "सा", "tat", "तत्"],
    "these": ["ete", "एते", "etāḥ", "एताः"],
    "those": ["te", "ते", "tāḥ", "ताः"],
    "more": ["adhikam", "अधिकम्", "bhūyaḥ", "भूयः"],
    "less": ["nyūnam", "न्यूनम्", "alpataram", "अल्पतरम्"],
    "fine": ["kuśalam", "कुशलम्", "sādhu", "साधु"],
    "okay": ["sampūrṇam", "सम्पूर्णम्", "asti", "अस्ति"],
    "ok": ["sampūrṇam", "सम्पूर्णम्", "asti", "अस्ति"],
}

# Add new entries (don't overwrite existing ones)
added_count = 0
updated_count = 0

for english, sanskrit_terms in conversational_entries.items():
    if english not in dictionary:
        dictionary[english] = sanskrit_terms
        added_count += 1
        print(f"✅ Added: {english} → {', '.join(sanskrit_terms[:3])}")
    else:
        # Merge with existing, keeping unique terms
        existing = set(dictionary[english])
        new_terms = set(sanskrit_terms)
        combined = list(existing | new_terms)
        if len(combined) > len(existing):
            dictionary[english] = combined
            updated_count += 1
            print(f"🔄 Updated: {english} (added {len(combined) - len(existing)} new terms)")

print(f"\n📊 Summary:")
print(f"   • Added: {added_count} new entries")
print(f"   • Updated: {updated_count} existing entries")
print(f"   • Final dictionary size: {len(dictionary)} entries")

# Save updated dictionary
with open('sanskrit_dictionary_cleaned.json', 'w', encoding='utf-8') as f:
    json.dump(dictionary, f, ensure_ascii=False, indent=2)

print(f"\n✅ Updated dictionary saved to sanskrit_dictionary_cleaned.json")
