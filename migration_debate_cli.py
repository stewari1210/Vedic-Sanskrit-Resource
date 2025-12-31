#!/usr/bin/env env python
"""
Migration Debate CLI
====================

Evaluate Rigvedic verses for evidence supporting or contradicting:
- AMT (Aryan Migration Theory)
- OIT (Out of India Theory)

Usage:
    python migration_debate_cli.py --verse "RV 7.95.2"
    python migration_debate_cli.py --verse "RV 10.75.5" --rounds 3
    python migration_debate_cli.py --interactive
"""

import sys
import os
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cli_run import build_index_and_retriever
from utils.migration_debate_agents import AMTAgent, OITAgent, MigrationDebateOrchestrator
from debate_cli import (
    auto_retrieve_both_translations,
    extract_specific_verse_griffith,
    parse_verse_reference
)
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from config import GEMINI_API_KEY, GEMINI_MODEL, OLLAMA_MODEL, OLLAMA_BASE_URL, MODEL_SPECS


def create_llm(use_google: bool = False):
    """Create LLM instance."""
    if use_google and GEMINI_API_KEY:
        return ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            google_api_key=GEMINI_API_KEY,
            temperature=0.3,
            timeout=180  # 3 minute timeout
        )
    else:
        return ChatOllama(
            base_url=OLLAMA_BASE_URL,
            model=OLLAMA_MODEL,
            temperature=MODEL_SPECS.get("temperature", 0.7),
            timeout=180,  # 3 minute timeout
            num_ctx=4096  # Limit context window to prevent huge prompts
        )


def run_migration_debate(verse_ref: str, griffith_text: str = None, sharma_text: str = None,
                        context: str = "", rounds: int = 2, use_google: bool = False,
                        retriever=None):
    """
    Run AMT vs OIT debate on a specific verse.

    Args:
        verse_ref: Verse reference (e.g., "RV 7.95.2")
        griffith_text: Griffith translation (if None, will auto-retrieve)
        sharma_text: Sharma translation (if None, will auto-retrieve)
        context: Additional scholarly context
        rounds: Number of debate rounds
        use_google: Whether to use Google Gemini for evaluation
        retriever: Pre-built retriever (optional, for interactive mode)
    """
    print("\n🔍 Initializing Migration Debate System...")
    print(f"📖 Target Verse: {verse_ref}")
    print(f"🤖 LLM: {'Google Gemini' if use_google else 'Ollama ' + OLLAMA_MODEL}")
    print(f"🔄 Rounds: {rounds}\n")

    # Build retriever if needed
    if not griffith_text or not sharma_text:
        if retriever is None:
            print("📚 Building vector store and retriever...")
            vec_db, docs, retriever = build_index_and_retriever(force=False)
        else:
            print("📚 Using existing retriever...")

        # Try to retrieve both translations
        print(f"🔎 Auto-retrieving translations for {verse_ref}...")

        # Check if it's a complete hymn or specific verse
        parsed = parse_verse_reference(verse_ref)
        if parsed and len(parsed) == 4:  # Specific verse (mandala, sukta, verse, ref_text)
            mandala, sukta, verse_num, _ = parsed

            # For specific verse, retrieve complete hymn first
            hymn_ref = f"RV {mandala}.{sukta}"
            auto_griffith, auto_sharma = auto_retrieve_both_translations(retriever, hymn_ref)

            if auto_griffith and not griffith_text:
                # Extract specific verse from Griffith
                extracted = extract_specific_verse_griffith(auto_griffith, verse_num)
                if extracted:
                    griffith_text = extracted
                    print(f"✅ Extracted Griffith verse {verse_num}")
                else:
                    griffith_text = auto_griffith
                    print(f"⚠️  Could not extract specific verse, using complete hymn")

            if auto_sharma and not sharma_text:
                # Sharma doesn't have verse numbers - prompt user or use full sukta
                print(f"⚠️  Sharma translation lacks verse numbers.")
                print(f"📝 Using complete sukta. For specific verse, provide via --sharma-text\n")
                sharma_text = auto_sharma
        else:
            # Complete hymn/sukta
            auto_griffith, auto_sharma = auto_retrieve_both_translations(retriever, verse_ref)
            if not griffith_text:
                griffith_text = auto_griffith
            if not sharma_text:
                sharma_text = auto_sharma

        if not griffith_text or not sharma_text:
            print(f"❌ ERROR: Could not retrieve translations for {verse_ref}")
            print(f"   Griffith: {'✓' if griffith_text else '✗'}")
            print(f"   Sharma: {'✓' if sharma_text else '✗'}")
            return

    # Create agents
    llm = create_llm(use_google)
    synthesis_llm = create_llm(True) if use_google else llm  # Use Google for synthesis if available

    amt_agent = AMTAgent(llm)
    oit_agent = OITAgent(llm)
    orchestrator = MigrationDebateOrchestrator(amt_agent, oit_agent, synthesis_llm)

    # Run debate
    debate_history = orchestrator.run_debate(
        verse_ref=verse_ref,
        griffith_text=griffith_text,
        sharma_text=sharma_text,
        context=context,
        rounds=rounds,
        save=True
    )

    print(f"\n✅ Migration debate complete!")
    print(f"📊 Analyzed: {verse_ref}")
    print(f"💾 Transcript saved to: migration_debates/")


def interactive_mode():
    """Interactive mode for migration debates."""
    print("\n" + "="*80)
    print("🌍 MIGRATION DEBATE SYSTEM - Interactive Mode")
    print("="*80)
    print("\nEvaluate Rigvedic verses for AMT vs OIT evidence")
    print("\nKey Verses to Try:")
    print("  AMT Evidence:")
    print("    - RV 10.75 (River Hymn - geographic progression)")
    print("    - RV 1.101.1 (Dasa conflicts - 'krishna tvach')")
    print("    - RV 7.18 (Battle of Ten Kings)")
    print("    - RV 1.174.2 (Indra as fort-destroyer)")
    print("\n  OIT Evidence:")
    print("    - RV 7.95.2 (Sarasvati 'mighty river to sea')")
    print("    - RV 6.61.2 (Sarasvati bursting through hills)")
    print("    - RV 8.30.3 (Fathers' ancestral path)")
    print("    - RV 6.27.5 (Battle at Hariyupiya/Harappa)")
    print("    - RV 1.163.1 (Elephant - indigenous fauna)")
    print("\nType 'quit' or 'exit' to end\n")

    # Build retriever once
    print("📚 Building vector store...")
    vec_db, docs, retriever = build_index_and_retriever(force=False)
    print("✅ Ready!\n")

    while True:
        verse_ref = input("Enter verse reference (e.g., 'RV 7.95.2'): ").strip()

        if verse_ref.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Goodbye!")
            break

        if not verse_ref:
            continue

        # Optional context
        print("\nOptional: Add scholarly context (press Enter to skip)")
        context = input("Context: ").strip()

        # Optional rounds
        rounds_input = input("Number of debate rounds [2]: ").strip()
        rounds = int(rounds_input) if rounds_input.isdigit() else 2

        # Run debate
        run_migration_debate(
            verse_ref=verse_ref,
            context=context,
            rounds=rounds,
            use_google=False,
            retriever=retriever  # Pass the pre-built retriever
        )

        print("\n" + "="*80 + "\n")
        another = input("Analyze another verse? (y/n): ").strip().lower()
        if another != 'y':
            print("\n👋 Goodbye!")
            break


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate Rigvedic verses for AMT vs OIT evidence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze specific verse (auto-retrieves translations)
  python migration_debate_cli.py --verse "RV 7.95.2"

  # With multiple debate rounds
  python migration_debate_cli.py --verse "RV 10.75.5" --rounds 3

  # Provide custom translations
  python migration_debate_cli.py --verse "RV 1.101.1" \\
    --griffith-text "Indra destroyed the dark-skinned..." \\
    --sharma-text "..."

  # Add scholarly context
  python migration_debate_cli.py --verse "RV 6.27.5" \\
    --context "Possible reference to Harappa (Hariyupiya)"

  # Interactive mode
  python migration_debate_cli.py --interactive

  # Use Google Gemini for higher quality
  python migration_debate_cli.py --verse "RV 7.95.2" --google

Key Verses for Testing:
  AMT Evidence:
    RV 10.75 - River Hymn (geographic west-to-east)
    RV 1.101.1, 1.130.8 - "Dark-skinned" Dasas
    RV 7.18 - Battle of Ten Kings
    RV 5.29.10 - Anāsa (speechless) Dasyus

  OIT Evidence:
    RV 7.95.2, 6.61.2 - Mighty Sarasvati to sea
    RV 8.30.3 - Fathers' ancestral path
    RV 6.27.5 - Hariyupiya (Harappa?)
    RV 1.163.1 - Elephant (indigenous fauna)
        """
    )

    parser.add_argument(
        '--verse',
        type=str,
        help='Verse reference (e.g., "RV 7.95.2" or "RV 10.75")'
    )

    parser.add_argument(
        '--griffith-text',
        type=str,
        help='Griffith translation (overrides auto-retrieval)'
    )

    parser.add_argument(
        '--sharma-text',
        type=str,
        help='Sharma translation (overrides auto-retrieval)'
    )

    parser.add_argument(
        '--context',
        type=str,
        default="",
        help='Additional scholarly context about the verse'
    )

    parser.add_argument(
        '--rounds',
        type=int,
        default=2,
        help='Number of debate rounds (default: 2)'
    )

    parser.add_argument(
        '--google',
        action='store_true',
        help='Use Google Gemini instead of Ollama'
    )

    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Run in interactive mode'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Force rebuild vector store'
    )

    args = parser.parse_args()

    # Force rebuild if requested
    if args.force:
        print("🔄 Forcing vector store rebuild...")
        vec_db, docs, retriever = build_index_and_retriever(force=True)
        print("✅ Vector store rebuilt")

    if args.interactive:
        interactive_mode()
    elif args.verse:
        run_migration_debate(
            verse_ref=args.verse,
            griffith_text=args.griffith_text,
            sharma_text=args.sharma_text,
            context=args.context,
            rounds=args.rounds,
            use_google=args.google
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
