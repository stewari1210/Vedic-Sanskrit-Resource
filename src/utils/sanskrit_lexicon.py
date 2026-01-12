"""
Basic Sanskrit-English Lexicon for Query Enhancement
This bridges the semantic gap between Modern English queries and Vedic texts.
"""

from typing import List, Dict

# Basic lexicon - expand this with Monier-Williams dictionary later
BASIC_LEXICON: Dict[str, List[str]] = {
    # Common nouns
    "milk": ["payas", "payaḥ", "kṣīra", "dugdha", "दुग्ध", "पयस्", "क्षीर"],
    "water": ["ap", "āpaḥ", "udaka", "jala", "आप", "उदक", "जल"],
    "fire": ["agni", "vahni", "अग्नि"],
    "sun": ["sūrya", "āditya", "सूर्य", "आदित्य"],
    "moon": ["soma", "candra", "सोम", "चन्द्र"],
    "god": ["deva", "देव"],
    "king": ["rāja", "rājan", "राजन्"],
    "priest": ["hotṛ", "hotar", "ṛtvij", "होतृ", "ऋत्विज्"],
    "sacrifice": ["yajña", "यज्ञ"],
    "hymn": ["ṛc", "sūkta", "ऋच्", "सूक्त"],
    "horse": ["aśva", "अश्व"],
    "cow": ["go", "dhenu", "गो", "धेनु"],

    # Verbs (roots and common forms)
    "want": ["√iṣ", "icchāmi", "icchati", "इच्छामि", "इच्छति"],
    "desire": ["√iṣ", "kāmayate", "इच्छ", "काम"],
    "give": ["√dā", "dadāti", "dehi", "दत्त", "देहि"],
    "go": ["√gam", "gacchati", "गच्छति"],
    "come": ["√ā-gam", "āgacchati", "आगच्छति"],
    "drink": ["√pā", "pibati", "पिब"],
    "eat": ["√ad", "atti", "अत्ति"],
    "speak": ["√vac", "vakti", "वक्ति"],
    "know": ["√jñā", "jānāti", "जानाति"],
    "do": ["√kṛ", "karoti", "करोति"],
    "be": ["√as", "asti", "अस्ति"],
    "have": ["√bhū", "bhavati", "भवति"],

    # Pronouns
    "I": ["aham", "अहम्"],
    "you": ["tvam", "bhavān", "त्वम्", "भवान्"],
    "he": ["saḥ", "eṣaḥ", "सः", "एषः"],
    "she": ["sā", "eṣā", "सा", "एषा"],
    "we": ["vayam", "वयम्"],
    "they": ["te", "ete", "ते", "एते"],
    "this": ["ayam", "अयम्"],
    "that": ["saḥ", "asau", "सः", "असौ"],

    # Common adjectives
    "good": ["śubha", "sadhu", "शुभ", "साधु"],
    "bad": ["pāpa", "duṣṭa", "पाप", "दुष्ट"],
    "great": ["mahā", "महा"],
    "small": ["alpa", "kṣudra", "अल्प", "क्षुद्र"],
    "white": ["śveta", "śukla", "श्वेत", "शुक्ल"],
    "black": ["kṛṣṇa", "śyāma", "कृष्ण", "श्याम"],

    # Vedic deities (for factual queries)
    "Indra": ["indra", "śakra", "vṛtrahan", "इन्द्र", "शक्र"],
    "Agni": ["agni", "jātavedas", "वैश्वानर", "अग्नि"],
    "Varuna": ["varuṇa", "वरुण"],
    "Mitra": ["mitra", "मित्र"],
    "Soma": ["soma", "सोम"],
}


def enrich_query_with_sanskrit(query: str) -> str:
    """
    Enrich an English query with Sanskrit equivalents.

    Example:
        Input: "I want milk"
        Output: "I want milk aham icchāmi payas dugdha kṣīra"

    This helps semantic search find relevant verses even when translations
    use different vocabulary.
    """
    query_lower = query.lower()
    enrichments = []

    # Find matches in lexicon
    for english, sanskrit_terms in BASIC_LEXICON.items():
        if english in query_lower:
            # Add 2-3 most common Sanskrit terms (avoid overwhelming the query)
            enrichments.extend(sanskrit_terms[:3])

    # Append Sanskrit terms to original query
    if enrichments:
        enriched = f"{query} {' '.join(set(enrichments))}"
        return enriched

    return query


def extract_sanskrit_terms(query: str) -> List[str]:
    """
    Extract which Sanskrit terms are relevant to the query.
    Useful for targeted grammar/example retrieval.

    Returns:
        List of Sanskrit terms (roots and words) found in query context
    """
    query_lower = query.lower()
    relevant_terms = []

    for english, sanskrit_terms in BASIC_LEXICON.items():
        if english in query_lower:
            relevant_terms.extend(sanskrit_terms)

    return relevant_terms


def classify_query_type(query: str) -> str:
    """
    Classify query into: construction, grammar, or factual.
    This enables routing to specialized retrievers.

    Returns:
        "construction" | "grammar" | "factual"
    """
    query_lower = query.lower()

    # Construction indicators
    construction_patterns = [
        "how do i say", "translate to sanskrit", "what is", "in sanskrit",
        "how to say", "say in vedic", "sanskrit for", "vedic word for",
        "translate", "in devanagari", "construct"
    ]

    # Grammar indicators
    grammar_patterns = [
        "explain", "what is the rule", "how does", "why", "grammar",
        "declension", "conjugation", "sandhi", "vibhakti", "case ending",
        "verb form", "how to form"
    ]

    # Check patterns
    if any(pattern in query_lower for pattern in construction_patterns):
        return "construction"
    elif any(pattern in query_lower for pattern in grammar_patterns):
        return "grammar"
    else:
        return "factual"


# Quick lookup dictionaries for common queries
COMMON_CONSTRUCTIONS = {
    "I want milk": {
        "sanskrit": "अहम् दुग्धम् इच्छामि",
        "transliteration": "aham dugdham icchāmi",
        "breakdown": {
            "aham": "I (nominative)",
            "dugdham": "milk (accusative object)",
            "icchāmi": "I desire (√iṣ, present 1st person singular)"
        }
    },
    "give me water": {
        "sanskrit": "मह्यम् उदकम् देहि",
        "transliteration": "mahyam udakam dehi",
        "breakdown": {
            "mahyam": "to me (dative)",
            "udakam": "water (accusative)",
            "dehi": "give! (√dā, imperative 2nd person singular)"
        }
    },
    # Add more as you discover common patterns
}


def get_quick_construction(query: str) -> dict:
    """
    Check if this is a common construction we've pre-computed.
    Instant response for frequently asked questions.
    """
    query_normalized = query.lower().strip().rstrip('?').rstrip('.')
    return COMMON_CONSTRUCTIONS.get(query_normalized)
