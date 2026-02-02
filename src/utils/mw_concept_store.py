"""
Monier-Williams Concept Store Integration for RAG

This module provides fast lookup of Sanskrit terms in the MW dictionary
to enhance RAG queries with:
1. Exact word definitions
2. IAST/Devanagari transliteration variants
3. Vedic text references
4. Related terms and semantic context

Usage:
    from src.utils.mw_concept_store import MWConceptStore
    
    mw = MWConceptStore()
    result = mw.lookup("सरस्वती")
    print(result['definitions'])
    print(result['vedic_refs'])
    
    # Expand query with MW context
    expanded = mw.expand_query("अग्नि पूजा")
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from indic_transliteration import sanscript
import re


class MWConceptStore:
    """
    Monier-Williams dictionary concept store for RAG query enhancement.
    
    Provides fast lookup of Sanskrit terms with definitions, references,
    and transliteration variants to bridge script/language gaps.
    """
    
    def __init__(self, concept_store_path: str = "monier_williams_concept_store.json"):
        """
        Initialize MW concept store.
        
        Args:
            concept_store_path: Path to the JSON concept store file
        """
        self.concept_store_path = Path(concept_store_path)
        self.concepts = {}
        self.lookup_index = {}
        self.metadata = {}
        
        self._load()
    
    def _load(self):
        """Load concept store from JSON file."""
        if not self.concept_store_path.exists():
            print(f"⚠️  MW concept store not found at {self.concept_store_path}")
            print("   Run: python3 parse_monier_williams_concept_store.py")
            return
        
        print(f"📖 Loading MW concept store from {self.concept_store_path}...")
        with open(self.concept_store_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.metadata = data.get('metadata', {})
        self.concepts = data.get('concept_store', {})
        self.lookup_index = data.get('lookup_index', {})
        
        print(f"✅ Loaded {len(self.concepts):,} concepts with {len(self.lookup_index):,} lookup keys")
    
    def normalize_query_term(self, term: str) -> str:
        """
        Normalize a query term for MW lookup.
        Removes diacritics, accents, and standardizes.
        
        Args:
            term: Sanskrit term (IAST or Devanagari)
            
        Returns:
            Normalized term for lookup
        """
        # Remove Vedic accents (/, -, \)
        term = re.sub(r'[/\\-]', '', term)
        # Remove punctuation
        term = re.sub(r'[।॥.,;:!?]', '', term)
        # Lowercase
        term = term.lower().strip()
        return term
    
    def lookup(self, query: str) -> Optional[Dict]:
        """
        Look up a Sanskrit term in the MW concept store.
        
        Args:
            query: Sanskrit term in Devanagari, IAST, or romanized form
            
        Returns:
            Dictionary with:
                - found: bool (whether term was found)
                - query: original query
                - normalized: normalized form used for lookup
                - primary_key: MW dictionary primary key
                - devanagari: Devanagari form
                - iast_variants: list of IAST variants
                - definitions: list of definition strings
                - vedic_refs: list of Vedic text references
                - related_terms: list of related Sanskrit terms
        """
        if not self.concepts:
            return self._empty_result(query)
        
        # Normalize query
        normalized = self.normalize_query_term(query)
        
        # Try direct lookup
        primary_key = self.lookup_index.get(normalized)
        
        if not primary_key:
            # Try with transliteration if Devanagari
            if self._is_devanagari(query):
                iast = self._to_iast(query)
                normalized_iast = self.normalize_query_term(iast)
                primary_key = self.lookup_index.get(normalized_iast)
        
        if not primary_key:
            return self._empty_result(query, normalized)
        
        # Get concept entry
        entry = self.concepts.get(primary_key, {})
        
        return {
            'found': True,
            'query': query,
            'normalized': normalized,
            'primary_key': primary_key,
            'devanagari': entry.get('devanagari', ''),
            'iast_variants': entry.get('iast_variants', [])[:10],
            'headwords': entry.get('headwords', [])[:10],
            'definitions': entry.get('definitions', [])[:5],
            'vedic_refs': entry.get('vedic_refs', [])[:10],
            'record_ids': entry.get('record_ids', [])
        }
    
    def _empty_result(self, query: str, normalized: str = "") -> Dict:
        """Return empty result for term not found."""
        return {
            'found': False,
            'query': query,
            'normalized': normalized,
            'primary_key': None,
            'devanagari': '',
            'iast_variants': [],
            'headwords': [],
            'definitions': [],
            'vedic_refs': [],
            'record_ids': []
        }
    
    def expand_query(self, query: str, max_terms: int = 3) -> str:
        """
        Expand query with MW definitions and related terms.
        
        Args:
            query: Original user query (may contain multiple words)
            max_terms: Maximum number of terms to look up
            
        Returns:
            Expanded query string with definitions and context
        """
        if not self.concepts:
            return query
        
        # Split query into words
        words = re.split(r'\s+', query)
        
        expansions = []
        terms_processed = 0
        
        for word in words:
            if terms_processed >= max_terms:
                break
            
            # Skip very short words
            if len(word) < 3:
                continue
            
            # Look up in MW
            result = self.lookup(word)
            
            if result['found']:
                terms_processed += 1
                
                # Add first definition
                if result['definitions']:
                    first_def = result['definitions'][0]
                    # Extract key terms from definition (simple extraction)
                    key_terms = self._extract_key_terms(first_def)
                    expansions.extend(key_terms[:2])
                
                # Add IAST variants
                expansions.extend(result['iast_variants'][:2])
        
        # Combine original query with expansions
        if expansions:
            unique_expansions = list(dict.fromkeys(expansions))  # Remove duplicates
            expansion_str = ' '.join(unique_expansions[:5])
            return f"{query} {expansion_str}"
        
        return query
    
    def _extract_key_terms(self, definition: str) -> List[str]:
        """
        Extract key terms from a definition string.
        Simple heuristic: words longer than 4 chars, excluding common words.
        """
        # Remove references and XML-like tags
        definition = re.sub(r'<[^>]+>', '', definition)
        definition = re.sub(r'\([^)]+\)', '', definition)
        
        # Split into words
        words = re.findall(r'\b[a-zA-Z]{5,}\b', definition)
        
        # Common words to skip
        stop_words = {'which', 'there', 'their', 'about', 'other', 'being', 'having', 'called', 'often'}
        
        key_terms = [w for w in words if w.lower() not in stop_words]
        return key_terms[:5]
    
    def get_vedic_context(self, query: str) -> Dict[str, List[str]]:
        """
        Get Vedic text references for query terms.
        
        Args:
            query: Sanskrit query
            
        Returns:
            Dictionary mapping terms to their Vedic references
        """
        words = re.split(r'\s+', query)
        vedic_context = {}
        
        for word in words:
            if len(word) < 3:
                continue
            
            result = self.lookup(word)
            if result['found'] and result['vedic_refs']:
                vedic_context[word] = result['vedic_refs']
        
        return vedic_context
    
    def get_all_variants(self, term: str) -> Set[str]:
        """
        Get all transliteration variants for a term.
        
        Args:
            term: Sanskrit term
            
        Returns:
            Set of all IAST, Devanagari, and romanized variants
        """
        result = self.lookup(term)
        
        if not result['found']:
            return {term}
        
        variants = set()
        variants.add(term)
        variants.add(result['devanagari'])
        variants.update(result['iast_variants'])
        variants.update(result['headwords'])
        
        # Remove empty strings
        variants = {v for v in variants if v}
        
        return variants
    
    def batch_lookup(self, terms: List[str]) -> List[Dict]:
        """
        Look up multiple terms at once.
        
        Args:
            terms: List of Sanskrit terms
            
        Returns:
            List of lookup results
        """
        return [self.lookup(term) for term in terms]
    
    @staticmethod
    def _is_devanagari(text: str) -> bool:
        """Check if text contains Devanagari script."""
        return bool(re.search(r'[\u0900-\u097F]', text))
    
    @staticmethod
    def _to_iast(text: str) -> str:
        """Convert Devanagari to IAST."""
        try:
            return sanscript.transliterate(text, sanscript.DEVANAGARI, sanscript.IAST)
        except:
            return text
    
    def stats(self) -> Dict:
        """Return statistics about the concept store."""
        return {
            'total_concepts': len(self.concepts),
            'total_lookup_keys': len(self.lookup_index),
            'metadata': self.metadata
        }


# Convenience function for quick lookups
def lookup_mw(term: str, concept_store_path: str = "monier_williams_concept_store.json") -> Dict:
    """
    Quick lookup function for MW dictionary.
    
    Args:
        term: Sanskrit term to look up
        concept_store_path: Path to concept store JSON
        
    Returns:
        MW lookup result dictionary
    """
    mw = MWConceptStore(concept_store_path)
    return mw.lookup(term)


if __name__ == '__main__':
    # Test the concept store
    print("=" * 70)
    print("Testing MW Concept Store")
    print("=" * 70)
    
    mw = MWConceptStore()
    
    # Test queries
    test_queries = [
        'अग्नि',
        'sarasvati',
        'सरस्वती',
        'veda',
        'rigveda',
        'soma'
    ]
    
    for query in test_queries:
        print(f"\n{'='*70}")
        print(f"Query: '{query}'")
        print("=" * 70)
        
        result = mw.lookup(query)
        
        if result['found']:
            print(f"✅ Found: {result['primary_key']}")
            print(f"   Devanagari: {result['devanagari']}")
            print(f"   IAST variants: {result['iast_variants'][:5]}")
            print(f"   Definitions ({len(result['definitions'])} total):")
            for i, defn in enumerate(result['definitions'][:2], 1):
                print(f"      {i}. {defn[:150]}...")
            print(f"   Vedic refs: {result['vedic_refs'][:5]}")
            
            # Test expansion
            expanded = mw.expand_query(query)
            print(f"\n   Expanded query: {expanded[:200]}...")
        else:
            print(f"❌ Not found")
    
    print("\n" + "=" * 70)
    print("Stats:")
    print("=" * 70)
    print(json.dumps(mw.stats(), indent=2))
