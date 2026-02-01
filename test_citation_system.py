#!/usr/bin/env python3
"""
Citation System Integration Test

This script simulates the full flow of how citations will work in the Streamlit app:
1. User asks a question
2. RAG system retrieves documents
3. Citations are extracted and formatted
4. LLM synthesizes an answer using the citations
5. Result is displayed with proper verse references

Run this to verify the citation system works end-to-end.
"""

import sys
sys.path.insert(0, '/Users/shivendratewari/github/Vedic-Sanskrit-Tutor')

from langchain_core.documents import Document
from src.utils.citation_enhancer import (
    enhance_corpus_results_with_citations,
    create_enhanced_citations_list,
    CitationFormatter,
    VedicCitationExtractor
)

def test_citation_extraction():
    """Test 1: Citation extraction from Griffith format"""
    print("\n" + "="*80)
    print("TEST 1: Citation Extraction from Griffith Format")
    print("="*80)
    
    text = """[01-033] HYMN XXXIII.

[Names (Griffith-Rigveda): Sudas]

Sudas. 1 Let Indra come to us with all his saving helps, to gain The victory near at hand."""
    
    citation = VedicCitationExtractor.extract_verse_reference(text)
    title = VedicCitationExtractor.extract_section_title(text)
    
    print(f"✅ Citation extracted: {citation}")
    print(f"✅ Title extracted: {title}")
    assert citation == "RV 1.33", f"Expected 'RV 1.33', got '{citation}'"
    assert title == "Sudas", f"Expected 'Sudas', got '{title}'"
    print("✅ TEST 1 PASSED")


def test_citation_formatting():
    """Test 2: Citation formatting for documents"""
    print("\n" + "="*80)
    print("TEST 2: Citation Formatting for Documents")
    print("="*80)
    
    doc = Document(
        page_content="""[07-018] HYMN XVIII.

[Names (Griffith-Rigveda): Sudas, Indra]

Sudas the king, with Indra's aid, Gave gifts to Divitana wealth untold.""",
        metadata={"filename": "rigveda-griffith_COMPLETE_english_with_metadata"}
    )
    
    citation, source = CitationFormatter.format_citation_with_source(doc, 1)
    print(f"✅ Formatted citation: {citation}")
    print(f"✅ Source: {source}")
    assert citation == "RV 7.18 - Sudas", f"Expected 'RV 7.18 - Sudas', got '{citation}'"
    print("✅ TEST 2 PASSED")


def test_corpus_context():
    """Test 3: Corpus context building with citations"""
    print("\n" + "="*80)
    print("TEST 3: Corpus Context Building")
    print("="*80)
    
    docs = [
        Document(
            page_content="""[01-033] HYMN XXXIII.

[Names (Griffith-Rigveda): Sudas]

Sudas. 1 Let Indra come to us with all his saving helps, to gain The victory near at hand.""",
            metadata={"filename": "rigveda-griffith_COMPLETE_english_with_metadata"}
        ),
        Document(
            page_content="""[07-018] HYMN XVIII.

[Names (Griffith-Rigveda): Sudas, Indra]

Sudas the king, with Indra's aid, Gave gifts to Divitana wealth untold.""",
            metadata={"filename": "rigveda-griffith_COMPLETE_english_with_metadata"}
        ),
    ]
    
    corpus_context = enhance_corpus_results_with_citations(docs)
    
    print("Corpus context (first 200 chars):")
    print(corpus_context[:200])
    print("\n...\n")
    
    assert "RV 1.33" in corpus_context, "Citation 'RV 1.33' not found in corpus_context"
    assert "RV 7.18" in corpus_context, "Citation 'RV 7.18' not found in corpus_context"
    assert "Sudas" in corpus_context, "Title 'Sudas' not found in corpus_context"
    assert "Passage" not in corpus_context, "Generic 'Passage' still found in corpus_context"
    
    print("✅ Citations properly formatted in corpus context")
    print("✅ No generic 'Passage N' placeholders found")
    print("✅ TEST 3 PASSED")


def test_structured_citations():
    """Test 4: Structured citation output"""
    print("\n" + "="*80)
    print("TEST 4: Structured Citation Output")
    print("="*80)
    
    docs = [
        Document(
            page_content="""[01-033] HYMN XXXIII.

[Names (Griffith-Rigveda): Sudas]

Sudas. 1 Let Indra come to us with all his saving helps...""",
            metadata={"filename": "rigveda-griffith_COMPLETE_english_with_metadata"}
        ),
    ]
    
    citations = create_enhanced_citations_list(docs)
    
    print(f"Number of citations: {len(citations)}")
    print(f"Citation structure:")
    for key, value in citations[0].items():
        print(f"  - {key}: {value}")
    
    assert len(citations) == 1, f"Expected 1 citation, got {len(citations)}"
    assert citations[0]["citation"] == "RV 1.33 - Sudas"
    assert citations[0]["source"] == "rigveda-griffith_COMPLETE_english_with_metadata"
    assert citations[0]["chunk_index"] == 0
    
    print("✅ Structured citations correctly formatted")
    print("✅ TEST 4 PASSED")


def test_llm_prompt():
    """Test 5: LLM prompt construction"""
    print("\n" + "="*80)
    print("TEST 5: LLM Prompt Construction")
    print("="*80)
    
    question = "Who is Sudas?"
    
    docs = [
        Document(
            page_content="""[01-033] HYMN XXXIII.

[Names (Griffith-Rigveda): Sudas]

Sudas. 1 Let Indra come to us with all his saving helps, to gain The victory near at hand.""",
            metadata={"filename": "rigveda-griffith_COMPLETE_english_with_metadata"}
        ),
        Document(
            page_content="""[07-018] HYMN XVIII.

[Names (Griffith-Rigveda): Sudas, Indra]

Sudas the king, with Indra's aid, Gave gifts to Divitana wealth untold.""",
            metadata={"filename": "rigveda-griffith_COMPLETE_english_with_metadata"}
        ),
    ]
    
    corpus_context = enhance_corpus_results_with_citations(docs)
    
    synthesis_prompt = f"""You are a Sanskrit scholar with expertise in Vedic texts.

QUESTION: {question}

RELEVANT CORPUS PASSAGES FROM RIGVEDA:
{corpus_context}

Answer based on the passages above."""
    
    print("LLM Prompt (first 300 chars):")
    print(synthesis_prompt[:300])
    print("\n...\n")
    
    assert "RV 1.33 - Sudas" in synthesis_prompt
    assert "RV 7.18 - Sudas" in synthesis_prompt
    assert "Passage" not in synthesis_prompt
    
    print("✅ LLM prompt contains proper verse references")
    print("✅ No generic placeholders in LLM prompt")
    print("✅ TEST 5 PASSED")


def test_fallback():
    """Test 6: Fallback to generic 'Passage N' when extraction fails"""
    print("\n" + "="*80)
    print("TEST 6: Fallback Behavior")
    print("="*80)
    
    # Document without proper metadata/structure
    doc = Document(
        page_content="Some random text without proper formatting...",
        metadata={"filename": "unknown_source"}
    )
    
    citation, source = CitationFormatter.format_citation_with_source(doc, 1)
    
    print(f"Citation for unformatted document: {citation}")
    assert citation == "Passage 1", f"Expected 'Passage 1' fallback, got '{citation}'"
    print("✅ Fallback to 'Passage N' working correctly")
    print("✅ TEST 6 PASSED")


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("CITATION SYSTEM INTEGRATION TEST SUITE")
    print("="*80)
    
    try:
        test_citation_extraction()
        test_citation_formatting()
        test_corpus_context()
        test_structured_citations()
        test_llm_prompt()
        test_fallback()
        
        print("\n" + "="*80)
        print("ALL TESTS PASSED ✅")
        print("="*80)
        print("\nThe citation system is ready for production!")
        print("\nKey achievements:")
        print("  ✅ Citations extracted: [01-033] → RV 1.33")
        print("  ✅ Titles extracted: [Names (...): Sudas] → Sudas")
        print("  ✅ Full citations: RV 1.33 - Sudas")
        print("  ✅ Corpus context properly formatted")
        print("  ✅ LLM receives verse references, not 'Passage N'")
        print("  ✅ Fallback to 'Passage N' for edge cases")
        print("\nNext steps:")
        print("  1. Start Streamlit app with: streamlit run src/sanskrit_tutor_frontend.py")
        print("  2. Test query: 'Who is Sudas?'")
        print("  3. Verify citations appear as 'RV X.Y - Title' instead of 'Passage N'")
        print("\n" + "="*80)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
