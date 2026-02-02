"""Test language detection in HybridRetriever"""
import os
os.chdir('/Users/shivendratewari/github/Vedic-Sanskrit-Tutor')

# Import the _is_english_query method code (standalone, no dependencies)
def _is_english_query(query: str) -> bool:
    """
    Detect if query is primarily in English (vs Sanskrit/Hindi/Devanagari).
    
    Returns:
        True if query is English, False if Sanskrit/Hindi/Devanagari
    """
    # Check for Devanagari characters
    has_devanagari = any('\u0900' <= char <= '\u097F' for char in query)
    if has_devanagari:
        return False
    
    # Check for IAST diacritics (ā, ī, ū, ṛ, ṃ, ḥ, ś, ṣ, ṭ, ḍ, ṅ, ñ)
    iast_chars = set('āīūṛṝḷḹṃḥśṣṭḍṅñ')
    has_iast = any(char in iast_chars for char in query.lower())
    if has_iast:
        return False  # Likely Sanskrit transliteration
    
    # Common English question words (strong signal)
    english_words = {'who', 'what', 'when', 'where', 'why', 'how', 'is', 'are', 'was', 'were', 
                    'the', 'a', 'an', 'in', 'on', 'at', 'of', 'for', 'to', 'from',
                    'explain', 'describe', 'tell', 'summarize', 'which', 'verses', 'talk', 'about'}
    
    words = query.lower().split()
    english_count = sum(1 for word in words if word.strip('?.,!;:') in english_words)
    
    # If >50% of words are common English words, it's an English query
    if len(words) > 0 and english_count / len(words) > 0.5:
        return True
    
    # Default: assume English for queries without Devanagari or IAST
    return True

# Test queries
test_queries = [
    "Who is Sudas?",
    "Which verses talk about birth of Rama in Ramayana?",
    "Who is Divodasa?",
    "सुदास कौन है?",  # Hindi
    "rama ke janm ke bare mein bataye?",  # Hinglish
    "अग्नि पूजा",  # Devanagari
    "Sudās ka kārya",  # IAST
]

print("=" * 80)
print("LANGUAGE DETECTION TEST")
print("=" * 80)

for query in test_queries:
    is_english = _is_english_query(query)
    print(f"\nQuery: '{query}'")
    print(f"  → is_english_query() = {is_english}")
    if is_english:
        print(f"  → ✅ Should SKIP MW expansion (English)")
    else:
        print(f"  → ❌ Should APPLY MW expansion (Sanskrit/Hindi/Devanagari)")
