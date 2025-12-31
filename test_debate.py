#!/usr/bin/env python3
"""
Test Vedic Translation Debate System
Griffith (Literal) vs Sharma (Philosophical)
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from helper import logger
from utils.index_files import create_qdrant_vector_store
from utils.retriever import create_retriever
from utils.debate_agents import create_debate_orchestrator


def test_debate():
    """Test debate with a classic verse that has both literal and symbolic meaning"""

    print("\n" + "="*80)
    print("VEDIC TRANSLATION DEBATE SYSTEM - PROOF OF CONCEPT")
    print("="*80)
    print("\nGriffith (Literal-Historical) vs Sharma (Philosophical-Spiritual)")
    print("Goal: Converge on original Rishi intent through dialectical synthesis\n")
    print("="*80 + "\n")

    # Create vector store and retriever from existing Griffith data
    print("📚 Loading Griffith translation corpus...\n")
    vec_db, docs = create_qdrant_vector_store(force_recreate=False)
    retriever = create_retriever(vec_db, docs)

    # Create debate orchestrator
    orchestrator = create_debate_orchestrator(griffith_retriever=retriever)

    # Example verse: Indra slaying Vritra (classic literal vs symbolic debate)
    verse_reference = "RV 1.32"
    verse_text = """
Indra slew Vritra, the dragon lying on the mountain.
With his thunderbolt he split the clouds and released the waters.
The serpent lay coiled around the mountains, blocking the streams.
Mighty Indra struck him down and the rivers flowed free to the ocean.
"""

    # Run debate
    result = orchestrator.run_debate(
        verse_reference=verse_reference,
        verse_text=verse_text,
        num_rounds=2  # Thesis, Antithesis, + 1 rebuttal round
    )

    print("\n" + "="*80)
    print("✅ DEBATE COMPLETED")
    print("="*80)
    print(f"\nVerse: {result['verse_reference']}")
    print(f"Rounds: {len(result['debate_transcript'])}")
    print("\nSynthesis has been generated showing original Rishi intent.")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    test_debate()
