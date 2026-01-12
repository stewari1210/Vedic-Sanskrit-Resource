#!/usr/bin/env python3
"""
Test the Agentic RAG system for Sanskrit construction.
This demonstrates the 3-step thinking loop: Dictionary → Grammar → Corpus
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from utils.agentic_rag import run_agentic_rag
from helper import logger

def test_agentic_rag():
    """Test the agentic RAG with construction queries."""

    print("=" * 80)
    print("AGENTIC RAG TEST - Sanskrit Construction")
    print("=" * 80)
    print()

    test_queries = [
        "How do I say 'I want milk' in Sanskrit?",
        "Translate 'give me water' to Vedic Sanskrit",
        "What is 'good morning' in Sanskrit?"
    ]

    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"QUERY: {query}")
        print(f"{'='*80}\n")

        try:
            result = run_agentic_rag(query)

            print("\n--- AGENT'S THINKING PROCESS ---")
            print(f"Query Type: {result.get('query_type', 'unknown')}")
            print(f"Words to Translate: {result.get('english_words', [])}")
            print(f"\nDictionary Lookup Results:")
            for word, translations in result.get('sanskrit_words', {}).items():
                print(f"  {word} → {translations}")

            print(f"\nGrammar Rules Retrieved: {len(result.get('grammar_rules', []))}")
            print(f"Corpus Examples Retrieved: {len(result.get('corpus_examples', []))}")

            print("\n--- FINAL CONSTRUCTION ---")
            answer = result.get('answer', {}).get('answer', 'No answer generated')
            print(answer)

            print("\n" + "="*80 + "\n")

        except Exception as e:
            logger.error(f"Error testing query '{query}': {e}")
            import traceback
            traceback.print_exc()

    print("\n✅ Agentic RAG test complete!")
    print("\nKEY DIFFERENCES FROM NAIVE RAG:")
    print("1. ✅ Multi-step reasoning: Dictionary → Grammar → Corpus")
    print("2. ✅ Tool-based approach: Agent decides what information to gather")
    print("3. ✅ Semantic gap bridged: English words translated to Sanskrit before search")
    print("4. ✅ Synthesis: Combines information from multiple sources")
    print("\nVS NAIVE RAG (single retrieval pass with no word-level translation)")


if __name__ == "__main__":
    test_agentic_rag()
