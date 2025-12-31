"""
Vedic Debate CLI - Agentic AI System
Separate from main RAG CLI to avoid breaking standard functionality

Runs debates between Griffith (literal) and Sharma (philosophical) agents
to recover original Rishi intent through dialectical synthesis.
"""

import os
import sys
import argparse
import re

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from helper import logger
from cli_run import build_index_and_retriever
from src.utils.debate_agents import create_debate_orchestrator


def parse_verse_reference(verse_reference: str):
    """Parse verse reference string into components.

    Args:
        verse_reference: String like "RV 2.33", "RV 2.33.8", etc.

    Returns:
        tuple: (mandala, sukta, verse_num, original_text) or None if invalid
        verse_num will be None for complete hymn references
    """
    match = re.match(r'(RV|YV)\s*(\d+)\.(\d+)(?:\.(\d+))?', verse_reference.upper())
    if match:
        veda, mandala, sukta, verse_num = match.groups()
        return (
            int(mandala),
            int(sukta),
            int(verse_num) if verse_num else None,
            verse_reference
        )
    return None


def auto_retrieve_both_translations(retriever, verse_reference: str):
    """Auto-retrieve verse text from BOTH Griffith and Sharma translations.

    This allows each agent to debate their own translator's version of the verse,
    rather than both debating the same text.

    Returns:
        tuple: (griffith_text, sharma_text) or (None, None) if retrieval fails
    """
    try:
        # Parse verse reference to extract book, hymn, and optional verse numbers
        # Examples: "RV 2.33", "RV 2.33.8", "RV 10.85.12", "YV 40.1"
        match = re.match(r'(RV|YV)\s*(\d+)\.(\d+)(?:\.(\d+))?', verse_reference.upper())

        specific_verse = None
        if match:
            veda, book, hymn, verse_num = match.groups()
            specific_verse = int(verse_num) if verse_num else None

            # Format as Griffith uses: [02-033] for RV Book 2, Hymn 33
            griffith_hymn_id = f"[{int(book):02d}-{int(hymn):03d}]"

            # Convert hymn number to Roman numerals for better matching
            roman_numerals = {
                1: "I", 2: "II", 3: "III", 4: "IV", 5: "V",
                6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X",
                11: "XI", 12: "XII", 13: "XIII", 14: "XIV", 15: "XV",
                16: "XVI", 17: "XVII", 18: "XVIII", 19: "XIX", 20: "XX",
                21: "XXI", 22: "XXII", 23: "XXIII", 24: "XXIV", 25: "XXV",
                26: "XXVI", 27: "XXVII", 28: "XXVIII", 29: "XXIX", 30: "XXX",
                31: "XXXI", 32: "XXXII", 33: "XXXIII", 34: "XXXIV", 35: "XXXV",
                40: "XL", 50: "L", 60: "LX", 70: "LXX", 80: "LXXX", 90: "XC", 100: "C"
            }
            hymn_roman = roman_numerals.get(int(hymn), str(hymn))

            # Search with EXACT patterns used in documents
            # Griffith: [02-033] HYMN XXXIII
            # Sharma: MANDAL - 2 / SUKTA - 33
            query = f"{griffith_hymn_id} HYMN {hymn_roman} MANDAL {int(book)} SUKTA {int(hymn)}"
            logger.info(f"Searching: Griffith={griffith_hymn_id} HYMN {hymn_roman}, Sharma=MANDAL-{book}/SUKTA-{hymn}")
        else:
            # Fallback to generic search
            query = f"{verse_reference} hymn verse translation"
            griffith_hymn_id = None

        docs = retriever.invoke(query)

        if not docs:
            return None, None

        # Separate docs by translator
        griffith_docs = [d for d in docs if 'griffith' in d.metadata.get('filename', '').lower()]
        sharma_docs = [d for d in docs if 'sharma' in d.metadata.get('filename', '').lower()]

        # Filter out index/metadata pages (look for actual verse content)
        def is_likely_verse_content(text):
            """Check if text looks like actual verse content, not index/metadata."""
            text_lower = text.lower()
            # Exclude common index/metadata patterns
            if any(pattern in text_lower for pattern in ['page', 'index', 'contents', '---', '***']):
                return False
            # Look for verse-like content (has words, not just numbers/symbols)
            word_count = len([w for w in text.split() if w.isalpha() and len(w) > 2])
            return word_count > 10  # At least 10 real words

        def matches_hymn_id(text, hymn_id):
            """Check if text contains the specific hymn ID."""
            if not hymn_id:
                return True
            return hymn_id in text

        # Find best match from Griffith - collect ALL verses from the hymn
        # Note: Griffith chunks are structured as:
        #   Chunk N: [02-033] HYMN XXXIII (header only)
        #   Chunk N+1: Actual verses (no hymn ID)
        #   Chunk N+2: More verses
        #   Chunk N+3: [02-034] HYMN XXXIV (next hymn)
        griffith_text = None
        if griffith_docs:
            if griffith_hymn_id:
                # Strategy: Find the header chunk, then collect all subsequent chunks
                # until we hit the next hymn header

                # First, try to find in retrieved docs
                exact_matches = [doc for doc in griffith_docs if matches_hymn_id(doc.page_content, griffith_hymn_id)]

                if exact_matches:
                    logger.info(f"Found {len(exact_matches)} Griffith docs with {griffith_hymn_id} header")

                    # Load full corpus to get sequential chunks
                    import pickle
                    corpus_file = 'vector_store/ancient_history/docs_chunks.pkl'
                    try:
                        with open(corpus_file, 'rb') as f:
                            all_docs = pickle.load(f)

                        # Find Griffith RV docs
                        griffith_all = [d for d in all_docs if 'griffith' in d.metadata.get('filename', '').lower() and 'rigveda' in d.metadata.get('filename', '').lower()]

                        # Find the header chunk index
                        header_idx = None
                        for i, doc in enumerate(griffith_all):
                            if griffith_hymn_id in doc.page_content:
                                header_idx = i
                                break

                        if header_idx is not None:
                            # Collect this chunk and all following until next hymn
                            veda, book, hymn, verse_num = match.groups()
                            next_hymn_id = f"[{int(book):02d}-{int(hymn) + 1:03d}]"

                            collected_chunks = []
                            # Collect ALL chunks until next hymn (no arbitrary limit)
                            for i in range(header_idx, len(griffith_all)):
                                chunk_text = griffith_all[i].page_content

                                # Stop if we hit the next hymn
                                if i > header_idx and next_hymn_id in chunk_text:
                                    break

                                # Skip if it's just a header with no content
                                if len(chunk_text.strip()) > 150 or i == header_idx:
                                    collected_chunks.append(chunk_text)

                            if collected_chunks:
                                # Join ALL collected chunks (no limit)
                                griffith_text = '\n\n'.join(collected_chunks)
                                logger.info(f"✓ Collected {len(collected_chunks)} sequential Griffith chunks for complete hymn ({len(griffith_text)} chars)")
                    except Exception as e:
                        logger.warning(f"Could not load corpus for sequential chunks: {e}")
                        # Fallback to single chunk
                        griffith_text = exact_matches[0].page_content[:800].strip()

            # Fallback: any verse-like content
            if not griffith_text:
                for doc in griffith_docs[:5]:
                    if is_likely_verse_content(doc.page_content):
                        griffith_text = doc.page_content[:500].strip()
                        break

            # Last resort
            if not griffith_text and griffith_docs:
                griffith_text = griffith_docs[0].page_content[:500].strip()        # Find best match from Sharma - collect ALL verses from the sukta
        sharma_text = None
        if sharma_docs:
            # Sharma uses format: "MANDAL - 2 / SUKTA - 33"
            if match:
                veda, book, hymn, verse_num = match.groups()
                current_sukta = f"MANDAL - {int(book)} / SUKTA - {int(hymn)}"
                next_sukta = f"MANDAL - {int(book)} / SUKTA - {int(hymn) + 1}"

                # Find all docs that belong to current sukta (before next sukta starts)
                current_sukta_docs = []
                for doc in sharma_docs:
                    content = doc.page_content.upper()
                    # Include if it has current sukta pattern
                    if current_sukta.upper() in content:
                        # Exclude if it also has next sukta (means it's a transition chunk)
                        if next_sukta.upper() not in content:
                            # Skip introduction/copyright text
                            if 'arjuna stood before' not in doc.page_content.lower() and 'all rights reserved' not in doc.page_content.lower():
                                current_sukta_docs.append(doc)

                logger.info(f"Found {len(current_sukta_docs)} Sharma docs for {current_sukta}")

                if current_sukta_docs:
                    # Concatenate all verses from this sukta
                    # Sort by chunk index if available in metadata
                    try:
                        current_sukta_docs.sort(key=lambda d: d.metadata.get('chunk_index', 0))
                    except:
                        pass

                    # Combine all chunks, limiting total size
                    combined_text = []
                    total_chars = 0
                    max_chars = 2000  # Get more text for complete sukta

                    for doc in current_sukta_docs:
                        text = doc.page_content.strip()
                        if is_likely_verse_content(text):
                            # Remove duplicate sukta headers if present
                            if combined_text and current_sukta in text:
                                # Skip the header part if already included
                                lines = text.split('\n')
                                text = '\n'.join([l for l in lines if current_sukta not in l.upper()])

                            if total_chars + len(text) <= max_chars:
                                combined_text.append(text)
                                total_chars += len(text)
                            else:
                                # Add partial text to reach max
                                remaining = max_chars - total_chars
                                if remaining > 100:  # Only add if meaningful amount left
                                    combined_text.append(text[:remaining] + "...")
                                break

                    if combined_text:
                        sharma_text = '\n\n'.join(combined_text)
                        logger.info(f"✓ Combined {len(current_sukta_docs)} Sharma chunks ({total_chars} chars) for complete sukta")

            # Fallback: skip introduction text
            if not sharma_text:
                for doc in sharma_docs[:10]:
                    content = doc.page_content
                    # Skip the introduction/preface text
                    if 'arjuna stood before' in content.lower() or 'all rights reserved' in content.lower():
                        continue
                    if is_likely_verse_content(content):
                        sharma_text = content[:500].strip()
                        logger.info(f"Found Sharma text (avoiding introduction)")
                        break

            # Fallback if nothing found
            if not sharma_text and sharma_docs:
                for doc in sharma_docs[:5]:
                    if is_likely_verse_content(doc.page_content):
                        sharma_text = doc.page_content[:500].strip()
                        break

        # Extract specific verse if verse number was provided
        if specific_verse and (griffith_text or sharma_text):
            logger.info(f"Extracting specific verse {specific_verse} from Griffith (Sharma will use full sukta)")

            if griffith_text:
                extracted = extract_specific_verse_griffith(griffith_text, specific_verse)
                if extracted:
                    griffith_text = extracted
                    logger.info(f"✓ Extracted Griffith verse {specific_verse} ({len(griffith_text)} chars)")
                else:
                    logger.warning(f"Could not extract verse {specific_verse} from Griffith text, using full hymn")

            # NOTE: Sharma doesn't have explicit verse numbers, so we keep the full sukta
            # The Sharma agent will interpret the philosophical meaning corresponding to
            # the Griffith verse by reading the full context
            if sharma_text:
                logger.info(f"ℹ Sharma text: keeping full sukta (no verse numbers in Sharma's translation)")

        return griffith_text, sharma_text

    except Exception as e:
        logger.warning(f"Failed to auto-retrieve verse texts: {e}")
        return None, None


def extract_specific_verse_griffith(full_text: str, verse_num: int) -> str:
    """Extract a specific verse from Griffith's complete hymn text.

    Griffith format: "8 To him the strong, great, tawny, fair-complexioned..."
    Verses may be continuous on the same line.
    """
    try:
        # Find verse using regex - look for the verse number followed by text
        # Pattern matches: "8 To him..." capturing everything until the next verse number
        pattern = rf'(\s|^){verse_num}[\s\.]([A-Z][^0-9]+?)(?=\s+{verse_num + 1}[\s\.]|#|$)'

        match = re.search(pattern, full_text, re.DOTALL)
        if match:
            verse_text = f"{verse_num} {match.group(2).strip()}"

            # Include hymn header for context
            header_match = re.search(r'\[[\d-]+\]\s*HYMN\s+[IVXLCDM]+[^\n]*', full_text)
            if header_match:
                return f"{header_match.group()}\n\n{verse_text}"
            return verse_text

        return None
    except Exception as e:
        logger.warning(f"Error extracting Griffith verse {verse_num}: {e}")
        return None


def extract_specific_verse_sharma(full_text: str, verse_num: int) -> str:
    """Extract a specific verse from Sharma's complete sukta text.

    Sharma format has [Names: ...] markers and verse numbers are less consistent.
    We'll try to extract based on section breaks.
    """
    try:
        # Sharma text often has multiple [Names: ...] sections
        # Try to split by these markers and get the verse_num-th section
        sections = re.split(r'\[Names:', full_text)

        if len(sections) > verse_num:
            # Get the target section
            verse_text = '[Names:' + sections[verse_num]
            # Clean up - take until next [Names: or end
            verse_text = verse_text.strip()

            # Include MANDAL/SUKTA header for context
            header_match = re.search(r'MANDAL\s*-\s*\d+\s*/\s*SUKTA\s*-\s*\d+', full_text)
            if header_match:
                return f"{header_match.group()}\n\n{verse_text}"
            return verse_text

        # Fallback: try to find verse number patterns in Sharma text
        # Sometimes Sharma uses numbers too
        lines = full_text.split('\n')
        verse_lines = []
        in_target_verse = False
        next_verse_num = verse_num + 1

        for line in lines:
            if re.search(rf'\b{verse_num}\b', line) and not in_target_verse:
                in_target_verse = True
                verse_lines.append(line)
            elif in_target_verse:
                if re.search(rf'\b{next_verse_num}\b', line) or '[Names:' in line:
                    break
                verse_lines.append(line)

        if verse_lines:
            return '\n'.join(verse_lines).strip()

        return None
    except Exception as e:
        logger.warning(f"Error extracting Sharma verse {verse_num}: {e}")
        return None


def run_interactive_debate(retriever):
    """Run interactive debate mode with user input."""
    print("\n" + "=" * 80)
    print("🔥 VEDIC VERSE DEBATE MODE 🔥")
    print("=" * 80)
    print("Griffith Agent: Literal/Historical interpretation")
    print("Sharma Agent:   Philosophical/Spiritual interpretation")
    print("=" * 80)
    print("\nEnter verse details (type 'exit' or 'quit' to stop)\n")

    # Create orchestrator - no retriever needed, uses pre-fetched texts
    orchestrator = create_debate_orchestrator()

    while True:
        try:
            # Get verse reference
            verse_ref = input("Verse Reference (e.g., RV 1.32, YV 40.1): ").strip()
            if not verse_ref:
                continue
            if verse_ref.lower() in {"exit", "quit"}:
                print("\nExiting debate mode.")
                break

            # Get verse text options
            print("\nVerse Text Options:")
            print("  1) Press Enter to AUTO-RETRIEVE both translations (Griffith + Sharma)")
            print("  2) Type 'manual' to provide your own text")
            print("  3) Paste verse text now (both agents will use same text)\n")

            choice = input("Your choice: ").strip().lower()

            verse_text = None
            griffith_text = None
            sharma_text = None

            if choice == "" or choice == "1":
                # Auto-retrieve both translations
                print("🔍 Auto-retrieving translations from both Griffith and Sharma...")
                griffith_text, sharma_text = auto_retrieve_both_translations(retriever, verse_ref)

                if griffith_text and sharma_text:
                    print("\n✓ Found Griffith's translation:")
                    print(f"  {griffith_text[:150]}...")
                    print("\n✓ Found Sharma's translation:")
                    print(f"  {sharma_text[:150]}...")
                    print("\n⚠️  Please verify these are the correct verses!")
                    confirm = input("Continue with these texts? (y/n): ").strip().lower()
                    if confirm not in ['y', 'yes']:
                        print("Please try again or provide text manually.\n")
                        continue
                elif griffith_text or sharma_text:
                    print("⚠️  Could only find one translation. Both agents will use it.")
                    verse_text = griffith_text or sharma_text
                    griffith_text = None
                    sharma_text = None
                else:
                    print("⚠️  Could not auto-retrieve verse texts. Please enter manually.")
                    continue

            elif choice == "manual" or choice == "2":
                # Manual input
                print("Enter verse text (press Enter twice when done):")
                lines = []
                while True:
                    line = input()
                    if line == "":
                        break
                    lines.append(line)
                verse_text = "\n".join(lines).strip()
                if not verse_text:
                    print("⚠️  No text provided. Please try again.")
                    continue

            else:
                # User pasted text directly
                verse_text = choice

            # Get number of rounds
            rounds_input = input("\nNumber of debate rounds (default: 2): ").strip()
            num_rounds = int(rounds_input) if rounds_input else 2

            print("\n" + "=" * 80)
            print(f"🎭 Starting debate on {verse_ref}")
            print("=" * 80 + "\n")

            # Run the debate
            result = orchestrator.run_debate(
                verse_reference=verse_ref,
                verse_text=verse_text,
                griffith_text=griffith_text,
                sharma_text=sharma_text,
                num_rounds=num_rounds
            )

            # Display final synthesis
            print("\n" + "=" * 80)
            print("✅ DEBATE COMPLETED")
            print("=" * 80)
            print(f"\nVerse: {verse_ref}")
            print(f"Rounds: {num_rounds * 2}")
            print(f"\n📊 FINAL SYNTHESIS:")
            print("=" * 80)
            print(result.get('synthesis', 'No synthesis available'))
            print("=" * 80)

            # Save debate
            if 'debate_file' in result:
                print(f"\n💾 Debate transcript saved to: {result['debate_file']}")

            print("\n")

        except KeyboardInterrupt:
            print("\n\nExiting debate mode.")
            break
        except Exception as e:
            logger.error(f"Error in debate: {e}")
            print(f"\n❌ Error: {e}\n")
            continue


def run_hymn_debate(retriever, hymn_ref: str, griffith_override: str = None,
                    sharma_override: str = None, num_rounds: int = 2):
    """
    Run debate on complete hymn/sukta.
    Auto-retrieves full text from both Griffith and Sharma translations.
    """
    print(f"\n{'='*80}")
    print(f"🎭 COMPLETE HYMN/SUKTA DEBATE MODE")
    print(f"{'='*80}\n")

    griffith_text = griffith_override
    sharma_text = sharma_override

    # Auto-retrieve if not provided
    if not griffith_text or not sharma_text:
        print(f"🔍 Auto-retrieving complete hymn/sukta for {hymn_ref}...")
        auto_griffith, auto_sharma = auto_retrieve_both_translations(retriever, hymn_ref)

        if not griffith_text:
            griffith_text = auto_griffith
        if not sharma_text:
            sharma_text = auto_sharma

        if not griffith_text and not sharma_text:
            print(f"❌ Could not find hymn/sukta texts for {hymn_ref}")
            return

        if griffith_text:
            print(f"✓ Found Griffith: {len(griffith_text)} chars")
        if sharma_text:
            print(f"✓ Found Sharma: {len(sharma_text)} chars")
        print()

    # Run debate
    orchestrator = create_debate_orchestrator()
    result = orchestrator.run_debate(
        verse_reference=hymn_ref,
        griffith_text=griffith_text,
        sharma_text=sharma_text,
        num_rounds=num_rounds
    )

    print(f"\n{'='*80}")
    print("✅ DEBATE COMPLETED")
    print(f"{'='*80}")
    print(f"\nHymn/Sukta: {hymn_ref}")
    print(f"Rounds: {num_rounds * 2}")
    print(f"\n📊 FINAL SYNTHESIS:")
    print("-" * 80)
    print(result.get('synthesis', 'No synthesis available'))
    print()


def run_verse_debate(retriever, verse_ref: str, sharma_text: str = None,
                    griffith_override: str = None, num_rounds: int = 2):
    """
    Run debate on specific verse.
    Extracts specific verse from Griffith, requires Sharma text from user.
    """
    print(f"\n{'='*80}")
    print(f"🎯 SPECIFIC VERSE DEBATE MODE")
    print(f"{'='*80}\n")

    # Parse verse reference to check if it has a verse number
    match = re.match(r'(RV|YV)\s*(\d+)\.(\d+)(?:\.(\d+))?', verse_ref.upper())
    if not match:
        print(f"❌ Invalid verse reference: {verse_ref}")
        print("Expected format: RV 2.33.8 (book.hymn.verse)")
        return

    veda, book, hymn, verse_num = match.groups()
    if not verse_num:
        print(f"❌ No verse number specified in {verse_ref}")
        print("Use --hymn for complete hymn/sukta, or specify verse like: RV 2.33.8")
        return

    # Extract specific verse from Griffith
    griffith_text = griffith_override
    if not griffith_text:
        print(f"🔍 Extracting verse {verse_num} from Griffith's {veda} {book}.{hymn}...")
        full_hymn, _ = auto_retrieve_both_translations(retriever, f"{veda} {book}.{hymn}")

        if full_hymn:
            griffith_text = extract_specific_verse_griffith(full_hymn, int(verse_num))
            if griffith_text:
                print(f"✓ Extracted Griffith verse {verse_num} ({len(griffith_text)} chars)")
            else:
                print(f"❌ Could not extract verse {verse_num} from Griffith")
                return
        else:
            print(f"❌ Could not retrieve Griffith hymn for {veda} {book}.{hymn}")
            return

    # Get Sharma text
    if not sharma_text:
        print(f"\n⚠️  Sharma's translation does not have explicit verse numbers.")
        print(f"Please provide the corresponding Sharma text for verse {verse_num}:")
        print(f"(You can find it in Sharma's MANDAL-{book}/SUKTA-{hymn})")
        print()
        sharma_text = input("Sharma text: ").strip()

        if not sharma_text:
            print("❌ Sharma text required for verse debate. Exiting.")
            return

    print(f"\n{'='*80}")
    print(f"🎭 Running debate on {verse_ref}")
    print(f"{'='*80}\n")

    # Run debate
    orchestrator = create_debate_orchestrator()
    result = orchestrator.run_debate(
        verse_reference=verse_ref,
        griffith_text=griffith_text,
        sharma_text=sharma_text,
        num_rounds=num_rounds
    )

    print(f"\n{'='*80}")
    print("✅ DEBATE COMPLETED")
    print(f"{'='*80}")
    print(f"\nVerse: {verse_ref}")
    print(f"Rounds: {num_rounds * 2}")
    print(f"\n📊 FINAL SYNTHESIS:")
    print("-" * 80)
    print(result.get('synthesis', 'No synthesis available'))
    print()


def run_single_debate(retriever, verse_ref: str, verse_text: str = None, num_rounds: int = 2):
    """Run a single debate (non-interactive mode)."""
    griffith_text = None
    sharma_text = None

    # Auto-retrieve verse texts if not provided
    if not verse_text:
        print(f"🔍 Auto-retrieving translations for {verse_ref}...")
        griffith_text, sharma_text = auto_retrieve_both_translations(retriever, verse_ref)

        if not griffith_text and not sharma_text:
            print(f"❌ Could not find verse texts for {verse_ref}")
            print("Please provide --verse-text or use interactive mode.")
            return

        if griffith_text and sharma_text:
            print(f"✓ Found Griffith: {griffith_text[:100]}...")
            print(f"✓ Found Sharma: {sharma_text[:100]}...\n")
        else:
            # Only one found - both agents will use it
            verse_text = griffith_text or sharma_text
            griffith_text = None
            sharma_text = None
            print(f"✓ Found: {verse_text[:100]}...\n")

    print("\n" + "=" * 80)
    print(f"🎭 Running debate on {verse_ref}")
    print("=" * 80 + "\n")

    # Create orchestrator - no retriever needed, uses pre-fetched texts
    orchestrator = create_debate_orchestrator()
    result = orchestrator.run_debate(
        verse_reference=verse_ref,
        verse_text=verse_text,
        griffith_text=griffith_text,
        sharma_text=sharma_text,
        num_rounds=num_rounds
    )

    print("\n" + "=" * 80)
    print("✅ DEBATE COMPLETED")
    print("=" * 80)
    print(f"\nVerse: {verse_ref}")
    print(f"Rounds: {num_rounds * 2}")
    print(f"\n📊 FINAL SYNTHESIS:")
    print("=" * 80)
    print(result.get('synthesis', 'No synthesis available'))
    print("=" * 80)

    if 'debate_file' in result:
        print(f"\n💾 Debate transcript saved to: {result['debate_file']}")


def main():
    """Main entry point for debate CLI."""
    parser = argparse.ArgumentParser(
        description="Vedic Verse Debate System - Griffith vs Sharma Agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python debate_cli.py

  # Single debate with auto-retrieval
  python debate_cli.py --verse "RV 2.33" --rounds 3

Examples:
  # Interactive mode
  python debate_cli.py

  # Complete hymn/sukta debate (auto-retrieves both translators)
  python debate_cli.py --hymn "RV 2.33" --rounds 2
  python debate_cli.py --sukta "RV 10.129" --rounds 3

  # Specific verse debate (extracts Griffith verse, prompts for Sharma text)
  python debate_cli.py --verse "RV 2.33.8" --rounds 2

  # Specific verse with manual Sharma text
  python debate_cli.py --verse "RV 2.33.8" --sharma-text "O Rudra, divine physician..." --rounds 2

  # Quiet mode (less logging)
  python debate_cli.py --hymn "RV 10.129" --quiet
        """
    )

    # Mutually exclusive group for debate type
    debate_type = parser.add_mutually_exclusive_group()
    debate_type.add_argument(
        "--hymn", "--sukta",
        dest="hymn_ref",
        help="Complete hymn/sukta reference (e.g., 'RV 2.33', 'RV 10.129'). Auto-retrieves full text from both Griffith and Sharma."
    )
    debate_type.add_argument(
        "--verse",
        dest="verse_ref",
        help="Specific verse reference (e.g., 'RV 2.33.8', 'RV 1.32.5'). Extracts specific verse from Griffith; requires --sharma-text or prompts user."
    )

    parser.add_argument(
        "--sharma-text",
        help="Sharma's translation text (required for --verse, optional for --hymn to override auto-retrieval)"
    )
    parser.add_argument(
        "--griffith-text",
        help="Griffith's translation text (optional, overrides auto-retrieval)"
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=2,
        help="Number of debate rounds (default: 2)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rebuild vector store index"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress INFO logs (only show warnings and errors)"
    )

    args = parser.parse_args()

    # Set logging level
    if args.quiet:
        import logging
        logging.getLogger().setLevel(logging.WARNING)
        for name in logging.root.manager.loggerDict:
            logging.getLogger(name).setLevel(logging.WARNING)

    # Build index and retriever
    try:
        print("Building retriever...")
        vec_db, docs, retriever = build_index_and_retriever(force=args.force)
        print(f"✓ Loaded {len(docs)} documents\n")
    except Exception as e:
        logger.exception("Failed to build retriever")
        print(f"❌ Error building retriever: {e}")
        return 1

    # Determine debate mode
    if args.hymn_ref:
        # Complete hymn/sukta mode - auto-retrieve both translators
        run_hymn_debate(retriever, args.hymn_ref, args.griffith_text, args.sharma_text, args.rounds)
    elif args.verse_ref:
        # Specific verse mode - extract Griffith verse, require Sharma text
        run_verse_debate(retriever, args.verse_ref, args.sharma_text, args.griffith_text, args.rounds)
    else:
        # Interactive mode
        run_interactive_debate(retriever)

    return 0


if __name__ == "__main__":
    sys.exit(main())
