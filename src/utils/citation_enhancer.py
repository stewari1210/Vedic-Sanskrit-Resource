#!/usr/bin/env python3
"""
Citation Enhancement System for Vedic Texts

This module provides intelligent citation extraction from Vedic texts, converting
generic "Passage N" citations to specific verse references like "RV 1.1.1" or
"YV 3.45" that can be directly mapped to the source documents.

Key Features:
- Extracts verse/hymn numbers from text headers and structure
- Maps chunks back to original hymn/sutra references
- Provides verifiable citations with translatable identifiers
- Supports multiple Vedic text formats
"""

import re
from typing import Dict, List, Optional, Tuple
from langchain_core.documents import Document


class VedicCitationExtractor:
    """Extract and map Vedic text citations to specific hymns/verses."""

    # Regex patterns for different Vedic text formats
    PATTERNS = {
        'rigveda_hymn': r'(?:Hymn|RV|Rigveda)\s+(\d+)\.(\d+)(?:\.(\d+))?',  # RV 1.1 or RV 1.1.1
        'yajurveda_verse': r'(?:YV|Yajurveda|Verse)\s+(\d+)\.(\d+)',  # YV 1.1
        'brahmana_reference': r'(?:Satapatha|SB|Brahmana)\s+(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?',  # SB 1.1.1 or SB 1.1.1.1
        'mantra_number': r'(?:Mantra|Sukta|Adhyaya)\s+(\d+)',  # Generic mantra reference
        'heading_pattern': r'^#+\s*(?:Hymn|Verse|Sutra|Section|Book|Mandala)\s+(\d+)(?:[:\-]\s*(.+))?',  # # Hymn 1: Title
        'book_canto_pattern': r'(?:Book|Canto|Adhyaya)\s+([IVX]+|\d+)',  # Book I or Book 1
    }

    @staticmethod
    def extract_verse_reference(text: str) -> Optional[str]:
        """
        Extract verse reference from text content.

        Args:
            text: Document text to search for citations

        Returns:
            Citation string like "RV 1.1.1" or None if not found
        """
        # Try each pattern
        for pattern_name, pattern in VedicCitationExtractor.PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return VedicCitationExtractor._format_citation(pattern_name, match)

        return None

    @staticmethod
    def _format_citation(pattern_name: str, match) -> str:
        """Format matched groups into proper citation format."""
        if pattern_name == 'rigveda_hymn':
            mandala, sukta, verse = match.groups()
            verse_part = f".{verse}" if verse else ""
            return f"RV {mandala}.{sukta}{verse_part}"

        elif pattern_name == 'yajurveda_verse':
            adhyaya, verse = match.groups()
            return f"YV {adhyaya}.{verse}"

        elif pattern_name == 'brahmana_reference':
            parts = match.groups()
            adhyaya, kanda, pada = parts[0], parts[1], parts[2]
            prapatha = f".{parts[3]}" if parts[3] else ""
            return f"SB {adhyaya}.{kanda}.{pada}{prapatha}"

        elif pattern_name == 'heading_pattern':
            number, title = match.groups()
            title_part = f" ({title})" if title else ""
            return f"Hymn {number}{title_part}"

        elif pattern_name == 'book_canto_pattern':
            book_num = match.group(1)
            return f"Book {book_num}"

        return "Unknown Reference"

    @staticmethod
    def extract_from_metadata(metadata: Dict) -> Optional[str]:
        """
        Extract citation from document metadata.

        Args:
            metadata: Document metadata dict

        Returns:
            Citation string or None
        """
        # Check for stored verse reference
        if 'verse_reference' in metadata:
            return metadata['verse_reference']

        if 'hymn_number' in metadata:
            hymn = metadata['hymn_number']
            mandala = metadata.get('mandala', '?')
            return f"RV {mandala}.{hymn}"

        if 'verse_number' in metadata:
            verse = metadata['verse_number']
            adhyaya = metadata.get('adhyaya', '?')
            return f"YV {adhyaya}.{verse}"

        return None

    @staticmethod
    def extract_section_title(text: str) -> Optional[str]:
        """
        Extract section/hymn title from text.

        Examples:
            "# Hymn 1: Invocation to Agni" → "Invocation to Agni"
            "## The Battle of Ten Kings" → "The Battle of Ten Kings"
        """
        title_match = re.search(r'^#+\s*(?:Hymn|Verse|Sutra|Section)?\s*[\d:]*\s*(.+?)$',
                               text, re.MULTILINE | re.IGNORECASE)
        if title_match:
            return title_match.group(1).strip()

        return None


class CitationFormatter:
    """Format citations for display in RAG responses."""

    @staticmethod
    def format_citation_with_source(doc: Document, passage_number: int) -> Tuple[str, str]:
        """
        Create a formatted citation from a document.

        Args:
            doc: LangChain Document object
            passage_number: Sequential passage number for fallback

        Returns:
            Tuple of (citation_label, source_identifier)
            Example: ("RV 1.1.1", "rigveda-griffith_COMPLETE_english_with_metadata")
        """
        # Try to extract from metadata first
        citation = VedicCitationExtractor.extract_from_metadata(doc.metadata)

        # If not in metadata, try to extract from content
        if not citation:
            citation = VedicCitationExtractor.extract_verse_reference(doc.page_content[:500])

        # Extract section title
        section_title = VedicCitationExtractor.extract_section_title(doc.page_content)

        # Get source identifier
        source_identifier = doc.metadata.get('filename', 'unknown_source')

        # Format final citation
        if citation and section_title:
            citation_label = f"{citation} - {section_title}"
        elif citation:
            citation_label = citation
        else:
            citation_label = f"Passage {passage_number}"

        return citation_label, source_identifier

    @staticmethod
    def create_citation_reference(citation_label: str, source: str, chunk_index: int) -> Dict:
        """
        Create a structured citation reference.

        Returns:
            Dict with citation metadata
        """
        return {
            "citation": citation_label,
            "source": source,
            "chunk_index": chunk_index,
            "url_fragment": CitationFormatter._generate_url_fragment(citation_label)
        }

    @staticmethod
    def _generate_url_fragment(citation_label: str) -> str:
        """
        Generate URL fragment for direct linking.

        Example: "RV 1.1.1" → "rv-1-1-1"
        """
        fragment = citation_label.lower().replace(' ', '-').replace('.', '-')
        # Remove special characters except hyphens
        fragment = re.sub(r'[^a-z0-9-]', '', fragment)
        return fragment


def enhance_corpus_results_with_citations(examples: List[Document]) -> str:
    """
    Convert retrieved documents to formatted text with proper citations.

    Args:
        examples: List of retrieved Document objects

    Returns:
        Formatted string with citations instead of generic "Passage N"

    Example:
        Input:  [Document(page_content="...", metadata={"filename": "rigveda-griffith..."}), ...]
        Output: "RV 1.1.1 - Invocation to Agni:\n...\n\nRV 1.1.2 - Agni as Messenger:\n..."
    """
    char_limit = 500
    formatted_passages = []

    for i, doc in enumerate(examples):
        citation_label, source = CitationFormatter.format_citation_with_source(doc, i + 1)

        # Truncate content
        content = doc.page_content[:char_limit]

        # Create formatted passage with proper citation
        formatted_passage = f"{citation_label}:\n{content}"
        formatted_passages.append(formatted_passage)

    return "\n\n".join(formatted_passages)


def create_enhanced_citations_list(examples: List[Document]) -> List[Dict]:
    """
    Create a structured list of citations for the final answer.

    Returns:
        List of citation dictionaries with proper references
    """
    citations = []

    for i, doc in enumerate(examples):
        citation_label, source = CitationFormatter.format_citation_with_source(doc, i + 1)
        citation_ref = CitationFormatter.create_citation_reference(citation_label, source, i)
        citations.append(citation_ref)

    return citations


# Example usage for testing
if __name__ == "__main__":
    # Test document with metadata
    test_doc = Document(
        page_content="""# Hymn 1: Invocation to Agni
        
Agni, the sacred fire, is invoked at the dawn of each day. This is from RV 1.1 
and represents the opening invocation of the Rigveda...""",
        metadata={
            "filename": "rigveda-griffith_COMPLETE_english_with_metadata",
            "title": "Rigveda - Griffith Translation"
        }
    )

    citation, source = CitationFormatter.format_citation_with_source(test_doc, 1)
    print(f"Citation: {citation}")
    print(f"Source: {source}")

    # Test citation extraction
    extractor = VedicCitationExtractor()
    test_text = "This reference is from RV 1.1.1 which discusses..."
    ref = extractor.extract_verse_reference(test_text)
    print(f"Extracted: {ref}")
