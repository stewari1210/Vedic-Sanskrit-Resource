"""
Sanskrit Translator Tool for Vedic Sanskrit Tutor

Provides utilities to translate English words to Vedic Sanskrit using:
1. Monier-Williams Concept Store (dictionary lookup)
2. Proper noun database (for person/place names)
3. Grammar rules database
"""

import json
import os
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from src.helper import logger, project_root
from src.config import LOCAL_FOLDER


class SanskritTranslator:
    """Translate English words to Vedic Sanskrit with confidence scores."""

    def __init__(self):
        """Initialize translator with concept store and proper nouns."""
        self.concept_store = self._load_concept_store()
        self.proper_nouns = self._load_proper_nouns()
        logger.info(f"✅ SanskritTranslator initialized with {len(self.concept_store)} terms")

    def _load_concept_store(self) -> Dict:
        """Load Monier-Williams concept store for word lookups."""
        try:
            concept_path = Path(project_root) / "monier_williams_concept_store.json"
            
            if not concept_path.exists():
                logger.warning(f"⚠️ Concept store not found at {concept_path}")
                return {}
            
            with open(concept_path, 'r', encoding='utf-8') as f:
                # Load only first 1000 entries for memory efficiency in demo
                data = json.load(f)
                logger.info(f"✅ Loaded concept store with {len(data)} entries")
                return data
        except Exception as e:
            logger.error(f"❌ Failed to load concept store: {e}")
            return {}

    def _load_proper_nouns(self) -> Dict[str, List[Dict]]:
        """Load proper nouns database (Rigveda-Sharma, etc.)."""
        proper_nouns = {}
        
        # Look for proper noun files in LOCAL_FOLDER
        proper_noun_files = list(Path(LOCAL_FOLDER).glob("*proper_nouns*.json"))
        
        for pn_file in proper_noun_files:
            try:
                with open(pn_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    proper_nouns.update(data)
                    logger.info(f"✅ Loaded proper nouns from {pn_file.name} ({len(data)} entries)")
            except Exception as e:
                logger.warning(f"⚠️ Could not load {pn_file.name}: {e}")
        
        return proper_nouns

    def translate_word(self, english_word: str, confidence_threshold: float = 0.6) -> List[Tuple[str, str, float]]:
        """
        Translate English word to Sanskrit.
        
        Args:
            english_word: English word to translate
            confidence_threshold: Minimum confidence score (0-1)
        
        Returns:
            List of (sanskrit_word, word_type, confidence) tuples, sorted by confidence
        """
        english_word_lower = english_word.lower().strip()
        results = []
        
        # Search in concept store
        if english_word_lower in self.concept_store:
            entry = self.concept_store[english_word_lower]
            
            # Extract Sanskrit terms
            if isinstance(entry, dict):
                if "sanskrit" in entry:
                    sanskrit_term = entry["sanskrit"]
                    word_type = entry.get("type", "noun")
                    confidence = 0.95  # High confidence from MW dictionary
                    results.append((sanskrit_term, word_type, confidence))
                
                if "synonyms" in entry:
                    for syn in entry["synonyms"]:
                        results.append((syn, entry.get("type", "noun"), 0.85))
        
        # Search in proper nouns (for person/place names)
        for pn_word, pn_data in self.proper_nouns.items():
            if english_word_lower == pn_word.lower():
                if isinstance(pn_data, dict):
                    sanskrit = pn_data.get("sanskrit", pn_word)
                    word_type = pn_data.get("type", "proper_noun")
                    confidence = 0.90
                    results.append((sanskrit, word_type, confidence))
        
        # Filter by confidence threshold and remove duplicates
        results = [(s, t, c) for s, t, c in results if c >= confidence_threshold]
        
        # Sort by confidence (descending)
        results = sorted(set(results), key=lambda x: x[2], reverse=True)
        
        return results

    def translate_query(self, english_query: str) -> Dict:
        """
        Translate English query to Sanskrit by extracting and translating key terms.
        
        Args:
            english_query: English question/query
        
        Returns:
            Dict with:
                - original: Original English query
                - translated_terms: Dict of {english_word: [(sanskrit, type, confidence), ...]}
                - suggested_sanskrit_query: Suggested pure Sanskrit version
                - proper_nouns_found: List of proper nouns found
        """
        # Simple tokenization (in production, use spaCy or NLTK)
        words = english_query.lower().split()
        
        # Filter out common English stop words
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'of', 'in', 'on', 'at', 'to', 'for',
            'and', 'or', 'but', 'with', 'from', 'by', 'as', 'that', 'this', 'these',
            'those', 'which', 'who', 'what', 'when', 'where', 'why', 'how'
        }
        
        words_to_translate = [
            w.strip('?,.:;!-') for w in words 
            if w.strip('?,.:;!-') not in stop_words and len(w.strip('?,.:;!-')) > 2
        ]
        
        translated_terms = {}
        proper_nouns_found = []
        suggested_sanskrit = []
        
        for word in words_to_translate:
            translations = self.translate_word(word)
            if translations:
                translated_terms[word] = translations
                # Use highest confidence translation
                sanskrit_word, word_type, confidence = translations[0]
                suggested_sanskrit.append(f"{sanskrit_word} ({word_type}, {confidence:.0%})")
                
                if word_type == "proper_noun":
                    proper_nouns_found.append((word, sanskrit_word))
        
        return {
            "original": english_query,
            "translated_terms": translated_terms,
            "suggested_sanskrit_query": " ".join(suggested_sanskrit) if suggested_sanskrit else None,
            "proper_nouns_found": proper_nouns_found,
            "translation_count": len(translated_terms),
        }

    def get_proper_noun_info(self, proper_noun: str) -> Optional[Dict]:
        """Get information about a proper noun (person, place, etc.)."""
        proper_noun_lower = proper_noun.lower()
        
        if proper_noun_lower in self.proper_nouns:
            return self.proper_nouns[proper_noun_lower]
        
        return None


# Singleton instance for quick access
_translator = None

def get_translator() -> SanskritTranslator:
    """Get or create singleton translator instance."""
    global _translator
    if _translator is None:
        _translator = SanskritTranslator()
    return _translator
