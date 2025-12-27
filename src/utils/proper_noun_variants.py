"""
Proper Noun Variant Management for Cross-Translation Normalization

Handles spelling variations, homonyms, and semantic disambiguation across:
- Rigveda (Sharma)
- Yajurveda (Sharma)
- Yajurveda (Griffith)

Usage:
    variants = get_proper_noun_variants("Kashyapa")
    # Returns: ["Kashyapa", "Kasyapa", "Kāśyapa", "Kashyap"]

    disambiguation = disambiguate_proper_noun("Bharata", context="battle")
    # Returns: Bharata (tribe), not Bharata (sage)
"""

import json
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ProperNounVariantManager:
    """Manages proper noun variants and disambiguation across Vedic translations."""

    def __init__(self, variants_file: str = "proper_noun_variants.json"):
        """Initialize with variants database."""
        self.variants_file = Path(variants_file)
        self.variants_data = self._load_variants()
        self._build_lookup_tables()

    def _load_variants(self) -> Dict:
        """Load variants from JSON file."""
        if not self.variants_file.exists():
            logger.warning(f"Variants file not found: {self.variants_file}")
            return {}

        try:
            with open(self.variants_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading variants file: {e}")
            return {}

    def _build_lookup_tables(self):
        """Build reverse lookup tables for fast variant resolution."""
        # Variant → Canonical mapping
        self.variant_to_canonical = {}

        # Process all categories
        for category in ['sages', 'tribes_and_kingdoms', 'kings_and_heroes', 'deities']:
            if category not in self.variants_data:
                continue

            for canonical, data in self.variants_data[category].items():
                # Map canonical name to itself
                self.variant_to_canonical[canonical.lower()] = canonical

                # Map all variants to canonical
                if 'variants' in data:
                    for variant in data['variants']:
                        self.variant_to_canonical[variant.lower()] = canonical

        logger.info(f"Built lookup table with {len(self.variant_to_canonical)} variant mappings")

    def get_variants(self, proper_noun: str) -> List[str]:
        """Get all spelling variants for a proper noun.

        Args:
            proper_noun: The proper noun to look up

        Returns:
            List of all variants including the canonical form

        Example:
            >>> manager.get_variants("Kashyapa")
            ["Kashyapa", "Kasyapa", "Kāśyapa", "Kashyap"]
        """
        # Normalize input
        normalized = proper_noun.strip()
        canonical = self.variant_to_canonical.get(normalized.lower(), normalized)

        # Find all variants for this canonical form
        variants = [canonical]  # Always include canonical

        # Search all categories
        for category in ['sages', 'tribes_and_kingdoms', 'kings_and_heroes', 'deities']:
            if category not in self.variants_data:
                continue

            if canonical in self.variants_data[category]:
                data = self.variants_data[category][canonical]
                if 'variants' in data:
                    variants.extend(data['variants'])

        # Deduplicate and return
        return list(set(variants))

    def get_context(self, proper_noun: str) -> Optional[Dict]:
        """Get contextual information about a proper noun.

        Returns role, context, sources, and other metadata.
        """
        normalized = proper_noun.strip()
        canonical = self.variant_to_canonical.get(normalized.lower(), normalized)

        # Search all categories
        for category in ['sages', 'tribes_and_kingdoms', 'kings_and_heroes', 'deities']:
            if category not in self.variants_data:
                continue

            if canonical in self.variants_data[category]:
                data = self.variants_data[category][canonical].copy()
                data['category'] = category
                data['canonical'] = canonical
                return data

        return None

    def disambiguate(self, proper_noun: str, context: str = "") -> Tuple[str, str]:
        """Disambiguate homonyms based on context.

        Args:
            proper_noun: The proper noun that might be ambiguous
            context: Surrounding text to help disambiguate

        Returns:
            (disambiguated_form, role) tuple

        Example:
            >>> manager.disambiguate("Bharata", context="battle with Purus")
            ("Bharatas (tribe)", "Tribe")

            >>> manager.disambiguate("Bharata", context="Rshi composed hymn")
            ("Bharata (Rshi)", "Sage")
        """
        normalized = proper_noun.strip()
        context_lower = context.lower()

        # Check if this is a known homonym
        if 'homonyms' not in self.variants_data:
            return (normalized, "Unknown")

        # Check for Bharata disambiguation
        # NOTE: Bharatas were multi-faceted - both military tribe AND priestly lineage
        # Only distinguish when there's VERY specific context for individual sage "Bharata (Rshi)"
        if normalized.lower() in ['bharata', 'bharatas']:
            for entry in self.variants_data['homonyms'].get('Bharata', []):
                # Only return individual sage form if explicitly mentioned with Devavata or in Yajurveda-only context
                if 'individual sage' in entry.get('form', '').lower() or 'Rshi' in entry.get('form', ''):
                    individual_sage_hints = ['devavata', 'with devavata', 'bharata and devavata']
                    if any(hint in context_lower for hint in individual_sage_hints):
                        return (entry['form'], entry['role'])

                # Default: Return the collective tribe-priest form (covers both military and spiritual)
                # This is more historically accurate - Bharatas were BOTH warriors and singers
                if 'tribe-priest collective' in entry.get('form', '').lower() or 'Multi-faceted' in entry.get('role', ''):
                    return (entry['form'], entry['role'])

        # Check for Purusha vs Puru
        if normalized.lower() in ['puru', 'purus', 'purusha']:
            for entry in self.variants_data['homonyms'].get('Purusha_vs_Puru', []):
                tribe_hints = ['battle', 'war', 'bharata', 'defeated', 'tribe']
                if any(hint in context_lower for hint in tribe_hints):
                    if 'Puru' in entry['form'] and 'Tribe' in entry['role']:
                        return (entry['form'], entry['role'])

                philosophical_hints = ['cosmic', 'purusha', 'prakriti', 'self', 'embodied']
                if any(hint in context_lower for hint in philosophical_hints):
                    if 'Purusha' in entry['form']:
                        return (entry['form'], entry['role'])

        # Check for Prajapati
        if normalized.lower() == 'prajapati':
            for entry in self.variants_data['homonyms'].get('Prajapati', []):
                if 'devata' in context_lower or 'deity' in context_lower:
                    if 'Devata' in entry['form']:
                        return (entry['form'], entry['role'])
                if 'rshi' in context_lower or 'parameshthi' in context_lower:
                    if 'Rshi' in entry['form']:
                        return (entry['form'], entry['role'])

        # Default: return original
        return (normalized, "Unknown")

    def is_valid_proper_noun(self, word: str) -> bool:
        """Check if a word is a recognized proper noun."""
        return word.strip().lower() in self.variant_to_canonical

    def get_source_specific_forms(self, proper_noun: str, source: str) -> List[str]:
        """Get forms specific to a particular source (e.g., 'Yajurveda-Griffith').

        Useful for source-aware retrieval.
        """
        context = self.get_context(proper_noun)
        if not context or 'sources' not in context:
            return [proper_noun]

        # If this noun appears in the specified source, return variants
        if source in context['sources']:
            return self.get_variants(proper_noun)

        return [proper_noun]


# Global instance
_manager = None

def get_manager(variants_file: str = "proper_noun_variants.json") -> ProperNounVariantManager:
    """Get or create global variant manager instance."""
    global _manager
    if _manager is None:
        _manager = ProperNounVariantManager(variants_file)
    return _manager


# Convenience functions
def get_proper_noun_variants(proper_noun: str) -> List[str]:
    """Get all spelling variants for a proper noun."""
    return get_manager().get_variants(proper_noun)


def disambiguate_proper_noun(proper_noun: str, context: str = "") -> Tuple[str, str]:
    """Disambiguate homonyms based on context."""
    return get_manager().disambiguate(proper_noun, context)


def get_proper_noun_context(proper_noun: str) -> Optional[Dict]:
    """Get contextual information about a proper noun."""
    return get_manager().get_context(proper_noun)


# Example usage
if __name__ == "__main__":
    # Test the variant system
    manager = get_manager()

    print("=== Testing Variant Lookup ===")
    test_names = ["Kashyapa", "Bharata", "Sudas", "Purusha"]
    for name in test_names:
        variants = manager.get_variants(name)
        print(f"{name}: {variants}")

    print("\n=== Testing Context Lookup ===")
    for name in test_names:
        context = manager.get_context(name)
        if context:
            print(f"{name}: {context.get('role', 'Unknown')} - {context.get('context', 'No context')}")

    print("\n=== Testing Disambiguation ===")
    test_cases = [
        ("Bharata", "in the battle with Purus"),
        ("Bharata", "the Rshi composed hymns"),
        ("Purusha", "the cosmic being"),
        ("Puru", "tribe defeated by Bharatas"),
    ]
    for name, ctx in test_cases:
        disambig, role = manager.disambiguate(name, ctx)
        print(f"{name} ({ctx[:30]}...): {disambig} [{role}]")
