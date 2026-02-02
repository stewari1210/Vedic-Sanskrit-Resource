"""
Transliteration utilities for Sanskrit/Hindi text processing.

Provides bidirectional conversion between Devanagari and IAST (International Alphabet of Sanskrit Transliteration).
This enables the RAG to match user queries in Devanagari with corpus text in IAST.

Example:
    User types: "सरस्वती" (Devanagari)
    System searches: ["सरस्वती", "Sarasvatī", "sarasvati"]
    Matches: Griffith text with "Sarasvatī" in IAST
"""

from indic_transliteration import sanscript
from typing import List, Set
import re
from src.helper import logger


class TransliterationHelper:
    """Helper class for Sanskrit/Hindi transliteration."""
    
    # Common Sanskrit/Hindi characters
    DEVANAGARI_RANGE = range(0x0900, 0x097F)
    IAST_DIACRITICS = set('āīūṛṝḷḹēōṃḥṅñṭḍṇśṣ')
    
    @staticmethod
    def contains_devanagari(text: str) -> bool:
        """Check if text contains Devanagari script."""
        return any(ord(char) in TransliterationHelper.DEVANAGARI_RANGE for char in text)
    
    @staticmethod
    def contains_iast(text: str) -> bool:
        """Check if text contains IAST diacritics."""
        return any(char in TransliterationHelper.IAST_DIACRITICS for char in text)
    
    @staticmethod
    def to_iast(text: str) -> str:
        """
        Convert Devanagari to IAST.
        
        Args:
            text: Text in Devanagari script
            
        Returns:
            Text in IAST (International Alphabet of Sanskrit Transliteration)
            
        Example:
            >>> to_iast("सरस्वती")
            'sarasvatī'
        """
        if not TransliterationHelper.contains_devanagari(text):
            return text
        
        try:
            return sanscript.transliterate(text, sanscript.DEVANAGARI, sanscript.IAST)
        except Exception as e:
            logger.warning(f"Failed to transliterate to IAST: {text}. Error: {e}")
            return text
    
    @staticmethod
    def to_devanagari(text: str) -> str:
        """
        Convert IAST to Devanagari.
        
        Args:
            text: Text in IAST
            
        Returns:
            Text in Devanagari script
            
        Example:
            >>> to_devanagari("sarasvatī")
            'सरस्वती'
        """
        if TransliterationHelper.contains_devanagari(text):
            return text
        
        try:
            return sanscript.transliterate(text, sanscript.IAST, sanscript.DEVANAGARI)
        except Exception as e:
            logger.warning(f"Failed to transliterate to Devanagari: {text}. Error: {e}")
            return text
    
    @staticmethod
    def normalize_query(query: str) -> List[str]:
        """
        Generate all transliteration variants of a query.
        
        This enables the RAG to search across multiple script representations
        of the same word, bridging the gap between Devanagari texts and IAST texts.
        
        Args:
            query: User query in any script
            
        Returns:
            List of query variants in different scripts and cases
            
        Example:
            >>> normalize_query("सरस्वती")
            ['सरस्वती', 'sarasvatī', 'Sarasvatī', 'sarasvati', 'Sarasvati']
            
            >>> normalize_query("Agni")
            ['Agni', 'agni', 'अग्नि']
        """
        variants: Set[str] = {query}  # Always include original
        
        # If Devanagari, add IAST variants
        if TransliterationHelper.contains_devanagari(query):
            iast = TransliterationHelper.to_iast(query)
            variants.add(iast)
            variants.add(iast.lower())
            variants.add(iast.capitalize())
            
            # Also add ASCII-only version (without diacritics)
            ascii_version = TransliterationHelper.remove_diacritics(iast)
            variants.add(ascii_version)
            variants.add(ascii_version.lower())
            variants.add(ascii_version.capitalize())
        
        # If IAST (has diacritics), add Devanagari
        elif TransliterationHelper.contains_iast(query):
            deva = TransliterationHelper.to_devanagari(query)
            variants.add(deva)
            
            # Also add case variants
            variants.add(query.lower())
            variants.add(query.capitalize())
            
            # Add ASCII version
            ascii_version = TransliterationHelper.remove_diacritics(query)
            variants.add(ascii_version)
            variants.add(ascii_version.lower())
        
        # If ASCII (no special chars), add both IAST and Devanagari attempts
        else:
            # Try converting as IAST
            try:
                deva = TransliterationHelper.to_devanagari(query)
                if deva != query:
                    variants.add(deva)
            except:
                pass
            
            # Add case variants
            variants.add(query.lower())
            variants.add(query.capitalize())
        
        # Remove empty strings and return as list
        return sorted([v for v in variants if v.strip()], key=len, reverse=True)
    
    @staticmethod
    def remove_diacritics(text: str) -> str:
        """
        Remove IAST diacritics to create ASCII-only version.
        
        Args:
            text: Text with IAST diacritics
            
        Returns:
            ASCII-only text
            
        Example:
            >>> remove_diacritics("sarasvatī")
            'sarasvati'
        """
        # Map IAST characters to ASCII equivalents
        diacritic_map = {
            'ā': 'a', 'ī': 'i', 'ū': 'u',
            'ṛ': 'r', 'ṝ': 'r', 'ḷ': 'l', 'ḹ': 'l',
            'ē': 'e', 'ō': 'o',
            'ṃ': 'm', 'ḥ': 'h',
            'ṅ': 'n', 'ñ': 'n', 'ṇ': 'n',
            'ṭ': 't', 'ḍ': 'd',
            'ś': 's', 'ṣ': 's'
        }
        
        result = text
        for iast_char, ascii_char in diacritic_map.items():
            result = result.replace(iast_char, ascii_char)
            result = result.replace(iast_char.upper(), ascii_char.upper())
        
        return result
    
    @staticmethod
    def expand_query_with_transliterations(query: str) -> str:
        """
        Expand a query to include all transliteration variants.
        
        Useful for keyword search (BM25) where we want to match
        any script variant of the query.
        
        Args:
            query: Original query
            
        Returns:
            Expanded query with all variants separated by OR
            
        Example:
            >>> expand_query_with_transliterations("सरस्वती नदी")
            'सरस्वती sarasvatī Sarasvatī sarasvati नदी nadī Nadī nadi'
        """
        words = query.split()
        expanded_words = []
        
        for word in words:
            variants = TransliterationHelper.normalize_query(word)
            expanded_words.extend(variants)
        
        return ' '.join(expanded_words)


# Convenience functions for easy import
def normalize_query(query: str) -> List[str]:
    """Generate all transliteration variants of a query."""
    return TransliterationHelper.normalize_query(query)


def to_iast(text: str) -> str:
    """Convert Devanagari to IAST."""
    return TransliterationHelper.to_iast(text)


def to_devanagari(text: str) -> str:
    """Convert IAST to Devanagari."""
    return TransliterationHelper.to_devanagari(text)


def expand_query(query: str) -> str:
    """Expand query with all transliteration variants."""
    return TransliterationHelper.expand_query_with_transliterations(query)


# Test function
if __name__ == "__main__":
    # Test cases
    test_cases = [
        "सरस्वती",  # Devanagari
        "Sarasvatī",  # IAST
        "Agni",  # ASCII
        "अग्नि",  # Devanagari
        "Indra",  # ASCII
        "वेद",  # Devanagari
    ]
    
    print("Testing Transliteration Layer")
    print("=" * 70)
    
    for test in test_cases:
        print(f"\nOriginal: {test}")
        variants = normalize_query(test)
        print(f"Variants: {variants}")
        print(f"Expanded: {expand_query(test)}")
