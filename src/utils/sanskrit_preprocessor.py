"""
Sanskrit Text Preprocessing Module

Handles Sanskrit-specific text processing including:
1. Word tokenization (using indic-nlp-library)
2. Diacritic normalization
3. Inflection handling (nominative stem extraction)
4. Transliteration support (IAST ↔ Devanagari)

This module is integrated into the RAG pipeline to improve retrieval of
inflected Sanskrit words (e.g., Sudas vs. Sudasah, Sudasam, Sudasya).
"""

import logging
import unicodedata
from typing import List, Optional

logger = logging.getLogger(__name__)

# Try to import indic-nlp-library components
try:
    from indic_nlp.tokenize import word_tokenize
    from indic_nlp.normalize import IndicNormalize
    INDIC_NLP_AVAILABLE = True
    logger.info("✓ indic-nlp-library components available")
except ImportError as e:
    INDIC_NLP_AVAILABLE = False
    logger.warning(f"⚠️  indic-nlp-library not available: {e}")
    logger.info("   Install with: pip install indic-nlp-library")

# Try to import transliteration support
try:
    from indic_transliteration import sanscript
    TRANSLITERATION_AVAILABLE = True
except ImportError:
    TRANSLITERATION_AVAILABLE = False
    logger.warning("⚠️  indic-transliteration not available for transliteration support")


class SanskritPreprocessor:
    """
    Preprocesses Sanskrit text for better RAG retrieval.
    
    Key features:
    - Tokenizes Sanskrit text into words using indic-nlp-library
    - Normalizes Devanagari diacritics and combining marks
    - Extracts noun stems (handles inflections like case endings)
    - Supports transliteration for cross-script matching
    """
    
    def __init__(self):
        """Initialize the preprocessor."""
        self.has_indic_nlp = INDIC_NLP_AVAILABLE
        self.has_transliteration = TRANSLITERATION_AVAILABLE
        
        if self.has_indic_nlp:
            try:
                self.normalizer = IndicNormalize(lang='san')  # Sanskrit normalization
            except Exception as e:
                logger.warning(f"Could not initialize IndicNormalize: {e}")
                self.normalizer = None
        else:
            self.normalizer = None
    
    def is_sanskrit(self, text: str) -> bool:
        """Detect if text contains Sanskrit (Devanagari script)."""
        # Devanagari script range: U+0900 to U+097F
        return any('\u0900' <= c <= '\u097F' for c in text)
    
    def remove_diacritics(self, text: str) -> str:
        """
        Remove Devanagari diacritical marks (matras, anusvaara, visarga, etc).
        
        This helps match "Sudas" with "Sudasah" by removing the case-marking diacritics.
        """
        # Devanagari diacritical marks and modifiers
        diacritic_ranges = [
            (0x0900, 0x0903),  # Anusvara, visarga, candrabindu
            (0x093C, 0x094D),  # Nukta, virama (word-internal)
            (0x0951, 0x0954),  # Stress marks (vedic)
        ]
        
        # Devanagari vowel diacritics (matras) that should be removed for normalization
        diacritics = {
            '\u093E',  # ा (aa)
            '\u093F',  # ि (i)
            '\u0940',  # ी (ii)
            '\u0941',  # ु (u)
            '\u0942',  # ू (uu)
            '\u0943',  # ृ (ri)
            '\u0944',  # ॄ (rii)
            '\u0947',  # े (e)
            '\u0948',  # ै (ai)
            '\u0949',  # ो (o)
            '\u094A',  # ौ (au)
        }
        
        result = []
        for char in text:
            code = ord(char)
            # Skip if in diacritic ranges or is a vowel diacritic
            if char not in diacritics:
                skip = False
                for start, end in diacritic_ranges:
                    if start <= code <= end:
                        skip = True
                        break
                if not skip:
                    result.append(char)
        
        return ''.join(result)
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize Sanskrit text using indic-nlp if available.
        
        Handles combining marks, canonicalization, and script normalization.
        """
        if self.has_indic_nlp and self.normalizer:
            try:
                # Apply indic-nlp normalization
                normalized = self.normalizer.normalize(text)
                # Additionally remove combining diacritics for base form matching
                normalized = self.remove_diacritics(normalized)
                return normalized
            except Exception as e:
                logger.debug(f"indic-nlp normalization failed: {e}. Using fallback.")
                return self.remove_diacritics(text)
        else:
            # Fallback: use diacritic removal
            return self.remove_diacritics(text)
    
    def tokenize(self, text: str, language: str = 'san') -> List[str]:
        """
        Tokenize Sanskrit text into words.
        
        Uses indic-nlp-library for proper Sanskrit word segmentation.
        Falls back to space/punctuation splitting if indic-nlp unavailable.
        
        Args:
            text: Sanskrit text to tokenize
            language: Language code ('san' for Sanskrit)
        
        Returns:
            List of tokens/words
        """
        if not text.strip():
            return []
        
        if self.has_indic_nlp:
            try:
                tokens = word_tokenize(text, lang=language)
                # Filter empty tokens
                return [t for t in tokens if t.strip()]
            except Exception as e:
                logger.debug(f"indic-nlp tokenization failed: {e}. Using fallback.")
                return self._fallback_tokenize(text)
        else:
            return self._fallback_tokenize(text)
    
    def _fallback_tokenize(self, text: str) -> List[str]:
        """
        Fallback tokenization when indic-nlp unavailable.
        
        Splits on whitespace and common punctuation.
        """
        import re
        # Split on whitespace and punctuation
        tokens = re.split(r'[\s।॥\-,\.;:!?]+', text)
        return [t for t in tokens if t.strip()]
    
    def extract_noun_stems(self, tokens: List[str]) -> List[str]:
        """
        Extract noun stems from inflected forms.
        
        Handles common Sanskrit noun case endings to extract the base form.
        This allows "Sudasah" (nominative singular with visarga) and "Sudasam"
        (accusative) to match to the same "Sudas" stem.
        
        Common noun endings (simplified):
        - -ah/-am (nominative/accusative)
        - -asya (genitive)
        - -aya/-at (dative/locative)
        - -ena (instrumental)
        
        Args:
            tokens: List of Sanskrit words
        
        Returns:
            List of stems (or original words if no clear stem found)
        """
        stems = []
        
        # Common Sanskrit noun endings (non-exhaustive)
        # This is a simplified approach; full morphological analysis would be more complex
        noun_endings = [
            'ah', 'am', 'a',      # Nominative/accusative variants
            'asya', 'aya', 'at',  # Genitive/dative/locative
            'ena', 'enas',        # Instrumental
            'e', 'au', 'as',      # Dual/plural variants
        ]
        
        for token in tokens:
            # Skip very short tokens (likely particles)
            if len(token) <= 2:
                stems.append(token)
                continue
            
            # Try to strip common endings
            found_stem = False
            for ending in sorted(noun_endings, key=len, reverse=True):  # Try longer endings first
                if token.lower().endswith(ending):
                    stem = token[:-len(ending)]
                    if len(stem) > 2:  # Only keep if stem is meaningful
                        stems.append(stem)
                        found_stem = True
                        break
            
            if not found_stem:
                stems.append(token)
        
        return stems
    
    def preprocess(self, text: str, extract_stems: bool = True) -> str:
        """
        Complete preprocessing pipeline for Sanskrit text.
        
        Steps:
        1. Normalize Devanagari diacritics
        2. Tokenize into words
        3. Extract noun stems (if enabled)
        4. Rejoin with spaces
        
        Args:
            text: Input Sanskrit text
            extract_stems: Whether to extract noun stems (default: True)
        
        Returns:
            Preprocessed text as space-separated tokens/stems
        """
        if not text or not text.strip():
            return ""
        
        # Step 1: Normalize
        normalized = self.normalize_text(text)
        
        # Step 2: Tokenize
        tokens = self.tokenize(normalized)
        
        # Step 3: Extract stems if requested and text is Sanskrit
        if extract_stems and self.is_sanskrit(text):
            tokens = self.extract_noun_stems(tokens)
        
        # Step 4: Rejoin
        return ' '.join(tokens)
    
    def preprocess_for_embedding(self, text: str) -> str:
        """
        Preprocess text specifically for embedding (chunking + tokenization).
        
        This is lighter than full preprocessing - focuses on normalization
        and tokenization without aggressive stem extraction.
        
        Used when creating embeddings from chunks.
        """
        if not text or not text.strip():
            return ""
        
        # Only normalize and tokenize, don't aggressively extract stems
        # This preserves more semantic information for embeddings
        normalized = self.normalize_text(text)
        tokens = self.tokenize(normalized)
        return ' '.join(tokens)
    
    def preprocess_query(self, query: str) -> str:
        """
        Preprocess search queries for Sanskrit.
        
        For queries, we extract stems more aggressively to match
        inflected forms in the indexed documents.
        
        Example:
            Query "Sudas" should match "Sudasah", "Sudasam", "Sudasya"
        
        Args:
            query: User's search query
        
        Returns:
            Preprocessed query with stem extraction
        """
        if not query or not query.strip():
            return ""
        
        # Normalize first
        normalized = self.normalize_text(query)
        
        # Tokenize
        tokens = self.tokenize(normalized)
        
        # Extract stems aggressively for better matching
        stems = self.extract_noun_stems(tokens)
        
        return ' '.join(stems)


# Global preprocessor instance
_preprocessor: Optional[SanskritPreprocessor] = None


def get_sanskrit_preprocessor() -> SanskritPreprocessor:
    """Get or create the global Sanskrit preprocessor instance."""
    global _preprocessor
    if _preprocessor is None:
        _preprocessor = SanskritPreprocessor()
    return _preprocessor


def preprocess_chunk(text: str) -> str:
    """
    Preprocess a chunk for embedding.
    
    This is called during indexing to normalize Sanskrit text before embedding.
    """
    preprocessor = get_sanskrit_preprocessor()
    return preprocessor.preprocess_for_embedding(text)


def preprocess_query(query: str) -> str:
    """
    Preprocess a user query for retrieval.
    
    This is called during retrieval to normalize the search query.
    """
    preprocessor = get_sanskrit_preprocessor()
    return preprocessor.preprocess_query(query)
