#!/usr/bin/env python3
"""
Test script for Ramayana citation enhancement.
"""

from src.utils.citation_enhancer import VedicCitationExtractor, CitationFormatter
from langchain_core.documents import Document


def test_ramayana_citations():
    """Test Ramayana citation patterns."""
    
    print("=" * 60)
    print("Testing Ramayana Citation Enhancement")
    print("=" * 60)
    print()
    
    # Test Case 1: Book + Canto + Verse
    print("Test 1: Book + Canto + Verse")
    chunk1 = """
# Book I.

## Canto I. Nárad.

OM.

To sainted Nárad, prince of those
Whose lore in words of wisdom flows.

[002] The good Válmíki, first and best
Of hermit saints, these words addressed:
"""
    
    citation1 = VedicCitationExtractor.extract_verse_reference(chunk1)
    print(f"  Input: Book I, Canto I, Verse [002]")
    print(f"  Output: {citation1}")
    print(f"  Expected: Ramayana Book 1, Canto 1, Verse 2")
    print(f"  ✓ PASS" if citation1 == "Ramayana Book 1, Canto 1, Verse 2" else f"  ✗ FAIL")
    print()
    
    # Test Case 2: Canto only (later in text)
    print("Test 2: Canto only")
    chunk2 = """
## Canto CXXX. The Consecration.

The people gathered round to see
The final ceremony and decree.
"""
    
    citation2 = VedicCitationExtractor.extract_verse_reference(chunk2)
    print(f"  Input: Canto CXXX")
    print(f"  Output: {citation2}")
    print(f"  Expected: Ramayana Canto 130")
    print(f"  ✓ PASS" if citation2 == "Ramayana Canto 130" else f"  ✗ FAIL")
    print()
    
    # Test Case 3: Verse only (mid-canto chunk)
    print("Test 3: Verse only")
    chunk3 = """
And then the mighty hero spoke,
His words like thunder when he woke.

[123] "O noble friends, hear what I say,
And follow me without delay."
"""
    
    citation3 = VedicCitationExtractor.extract_verse_reference(chunk3)
    print(f"  Input: Verse [123]")
    print(f"  Output: {citation3}")
    print(f"  Expected: Ramayana Verse 123")
    print(f"  ✓ PASS" if citation3 == "Ramayana Verse 123" else f"  ✗ FAIL")
    print()
    
    # Test Case 4: Book + Canto (no verse marker)
    print("Test 4: Book + Canto (no verse)")
    chunk4 = """
# Book I.

## Canto V. Ayodhyá.

The glorious city stood supreme,
Like heaven itself, a golden dream.
"""
    
    citation4 = VedicCitationExtractor.extract_verse_reference(chunk4)
    print(f"  Input: Book I, Canto V")
    print(f"  Output: {citation4}")
    print(f"  Expected: Ramayana Book 1, Canto 5")
    print(f"  ✓ PASS" if citation4 == "Ramayana Book 1, Canto 5" else f"  ✗ FAIL")
    print()
    
    # Test Case 5: Using CitationFormatter with Document
    print("Test 5: Full CitationFormatter with Document")
    doc = Document(
        page_content=chunk1,
        metadata={"title": "Ramayana - Griffith Translation"}
    )
    
    formatted_citation, section_title = CitationFormatter.format_citation_with_source(doc, passage_number=1)
    print(f"  Input: Document with Book I, Canto I, Verse [002]")
    print(f"  Output: {formatted_citation}")
    print(f"  Expected to contain: 'Ramayana Book 1, Canto 1, Verse 2'")
    print(f"  ✓ PASS" if "Ramayana Book 1, Canto 1, Verse 2" in formatted_citation else f"  ✗ FAIL")
    print()
    
    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    test_ramayana_citations()
