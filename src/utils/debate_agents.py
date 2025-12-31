"""
Vedic Translation Debate System
Two agents debate verse interpretations: Griffith (literal) vs Sharma (philosophical)
Goal: Converge on original intent through dialectical synthesis
"""

from typing import List, Dict, Any, Optional, Literal
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from helper import logger
from settings import Settings


class GriffithAgent:
    """
    Represents Griffith's literal/historical approach to Vedic translation
    - Focuses on material culture, historical events, tribal warfare
    - Treats deities as personifications of natural forces
    - Emphasizes archaeological and linguistic evidence

    NOTE: Retriever removed - agents now work with pre-fetched complete hymns/suktas
    from auto_retrieve_both_translations() in debate_cli.py
    """

    def __init__(self):
        self.llm = Settings.llm
        self.approach = "literal-historical"

        self.system_prompt = """
You are Ralph T.H. Griffith's translation philosophy embodied as an AI agent.

YOUR APPROACH:
- LITERAL interpretation of Vedic verses
- Historical and materialist lens
- Deities represent natural phenomena (Indra = storm god, Agni = fire)
- Battles and conflicts are REAL tribal warfare (Battle of Ten Kings)
- Chariots, weapons, cattle raids are LITERAL events
- Focus on archaeological evidence (Harappan sites, Sinauli chariots ~2100 BCE, material culture)
- Consider linguistic and comparative evidence without assuming migration theories

CRITICAL GUIDELINES:
- Present archaeological evidence neutrally without assuming origins
- Distinguish between established facts (Sinauli chariots exist) vs theories (their origin)
- Avoid presenting contested theories (Aryan Migration, Out of India) as established facts
- Focus on what the verses DESCRIBE rather than who wrote them or where they came from

DEBATE STYLE:
- Cite specific verses with historical context
- Reference material culture evidence from excavations
- Ground interpretations in linguistics and comparative mythology
- Challenge mystical interpretations with practical evidence
- Acknowledge when evidence is ambiguous or contested

When presented with a verse, provide YOUR literal/historical interpretation based on evidence.
"""

    def interpret_verse(self, verse_reference: str, verse_text: str) -> str:
        """Provide Griffith-style literal interpretation using the provided complete hymn text"""

        prompt = f"""{self.system_prompt}

VERSE REFERENCE: {verse_reference}

COMPLETE HYMN TEXT (Griffith's Translation):
{verse_text}

Provide your LITERAL/HISTORICAL interpretation of this hymn.
Focus on:
1. Material/physical meaning of the verses (weapons, chariots, rituals as real objects/events)
2. Historical context (tribes, battles, rituals, natural phenomena)
3. Archaeological evidence (Harappan sites, Sinauli excavations, material culture finds)
4. Linguistic analysis of key terms and comparative mythology

IMPORTANT: Base interpretations on archaeological EVIDENCE, not origin theories.
For example: "Chariots are mentioned - Sinauli excavations (~2100 BCE) confirm ritualistic chariot use in the Indian subcontinent"
NOT: "Chariots indicate Indo-Aryan migration from Central Asia"

Format:
### Griffith's Literal Interpretation
[Your interpretation]

### Historical Context
[Relevant historical background]

### Material Evidence
[Archaeological/linguistic support - focus on what's found, not assumptions about origins]
"""

        response = self.llm.invoke(prompt)
        return response.content


class SharmaAgent:
    """
    Represents Sharma's philosophical/spiritual approach to Vedic translation
    - Focuses on inner spiritual meaning
    - Treats deities as psychological/cosmic principles
    - Emphasizes metaphysical and yogic interpretations

    NOTE: Retriever removed - agents now work with pre-fetched complete hymns/suktas
    from auto_retrieve_both_translations() in debate_cli.py
    """

    def __init__(self):
        self.llm = Settings.llm
        self.approach = "philosophical-spiritual"

        self.system_prompt = """
You are Pt. Ramgovind Trivedi Sharma's translation philosophy embodied as an AI agent.

YOUR APPROACH:
- PHILOSOPHICAL/SPIRITUAL interpretation of Vedic verses
- Inner psychological and metaphysical lens
- Deities represent cosmic principles and inner spiritual forces
- Battles are METAPHORS for spiritual struggles (ego vs higher self)
- Material elements symbolize yogic concepts (fire = spiritual illumination)
- Focus on Upanishadic wisdom, Vedanta philosophy, yogic practices

DEBATE STYLE:
- Reveal deeper symbolic meanings
- Connect to Upanishads and later philosophical developments
- Show how literal readings miss spiritual truths
- Reference yogic and meditative interpretations

When presented with a verse, provide YOUR philosophical/spiritual interpretation.
"""

    def interpret_verse(self, verse_reference: str, verse_text: str,
                       griffith_interpretation: Optional[str] = None) -> str:
        """Provide Sharma-style philosophical interpretation using the provided complete sukta text"""

        opposing_view = ""
        if griffith_interpretation:
            opposing_view = f"""
GRIFFITH'S LITERAL INTERPRETATION (which you should challenge):
{griffith_interpretation[:800]}...
"""

        prompt = f"""{self.system_prompt}

VERSE REFERENCE: {verse_reference}

COMPLETE SUKTA TEXT (Sharma's Translation):
{verse_text}

{opposing_view}

Provide your PHILOSOPHICAL/SPIRITUAL interpretation of this sukta.
Focus on:
1. Symbolic/metaphorical meaning of the verses
2. Inner spiritual significance
3. Connection to Upanishadic wisdom and Vedanta philosophy
4. Yogic/meditative interpretation

If Griffith's literal view is provided, explain what deeper spiritual truth it misses.

Format:
### Sharma's Philosophical Interpretation
[Your interpretation]

### Spiritual Symbolism
[Deeper meanings]

### Response to Literal View
[Why literal reading is incomplete]
"""

        response = self.llm.invoke(prompt)
        return response.content


class DebateOrchestrator:
    """
    Orchestrates dialectical debate between Griffith and Sharma agents
    Uses thesis-antithesis-synthesis pattern to converge on original intent

    NOTE: Agents no longer need retrievers - they work with pre-fetched complete
    hymns/suktas from auto_retrieve_both_translations() in debate_cli.py
    """

    def __init__(self):
        self.griffith_agent = GriffithAgent()
        self.sharma_agent = SharmaAgent()
        self.llm = Settings.llm

        logger.info("Initialized Debate Orchestrator: Griffith vs Sharma")
        logger.info("Agents work with pre-fetched complete hymns/suktas")

    def run_debate(self, verse_reference: str, verse_text: str = None,
                   griffith_text: str = None, sharma_text: str = None,
                   num_rounds: int = 2) -> Dict[str, Any]:
        """
        Run multi-round debate to converge on original verse intent

        Args:
            verse_reference: e.g., "RV 1.32.1"
            verse_text: The actual verse text (used if both agents debate same text)
            griffith_text: Griffith's translation (optional - for translator-specific debates)
            sharma_text: Sharma's translation (optional - for translator-specific debates)
            num_rounds: Number of debate rounds (default 2)

        Returns:
            Dict with debate transcript and synthesis
        """
        logger.info(f"Starting debate on {verse_reference}")

        # Use translator-specific texts if provided, otherwise use common text
        griffith_verse = griffith_text or verse_text
        sharma_verse = sharma_text or verse_text

        debate_transcript = []

        # Round 1: Initial interpretations (Thesis & Antithesis)
        print("\n" + "="*80)
        print(f"📖 VERSE: {verse_reference}")
        print("="*80)

        # Display the texts being debated
        if griffith_text and sharma_text and griffith_text != sharma_text:
            print("\n🔵 GRIFFITH'S TRANSLATION:")
            print(f"{griffith_verse}\n")
            print("🟢 SHARMA'S TRANSLATION:")
            print(f"{sharma_verse}\n")
        else:
            print(f"\n{verse_text}\n")
        print("="*80 + "\n")

        print("🎯 ROUND 1: Initial Interpretations\n")
        print("-"*80)
        print("GRIFFITH AGENT (Literal-Historical)\n")

        griffith_round1 = self.griffith_agent.interpret_verse(verse_reference, griffith_verse)
        print(griffith_round1)
        debate_transcript.append({
            "round": 1,
            "agent": "Griffith",
            "interpretation": griffith_round1
        })

        print("\n" + "-"*80)
        print("SHARMA AGENT (Philosophical-Spiritual)\n")

        sharma_round1 = self.sharma_agent.interpret_verse(
            verse_reference,
            sharma_verse,
            griffith_interpretation=griffith_round1
        )
        print(sharma_round1)
        debate_transcript.append({
            "round": 1,
            "agent": "Sharma",
            "interpretation": sharma_round1
        })

        # Additional rounds if requested
        for round_num in range(2, num_rounds + 1):
            print("\n" + "="*80)
            print(f"🔄 ROUND {round_num}: Rebuttals\n")

            # Griffith responds to Sharma
            print("-"*80)
            print("GRIFFITH AGENT (Rebuttal)\n")

            griffith_rebuttal_prompt = f"""
{self.griffith_agent.system_prompt}

VERSE: {verse_reference}
{griffith_verse}

SHARMA'S PHILOSOPHICAL INTERPRETATION:
{sharma_round1[:800]}

Your task: Provide a REBUTTAL defending your literal/historical interpretation.
- Address Sharma's spiritual claims
- Show why material reading is necessary
- Provide counter-evidence from archaeology/history
- Acknowledge any valid symbolic elements WITHOUT abandoning literal meaning

Be respectful but firm in defending literal historicity.
"""

            griffith_rebuttal = self.llm.invoke(griffith_rebuttal_prompt).content
            print(griffith_rebuttal)
            debate_transcript.append({
                "round": round_num,
                "agent": "Griffith",
                "interpretation": griffith_rebuttal
            })

            # Sharma responds to Griffith
            print("\n" + "-"*80)
            print("SHARMA AGENT (Rebuttal)\n")

            sharma_rebuttal_prompt = f"""
{self.sharma_agent.system_prompt}

VERSE: {verse_reference}
{sharma_verse}

GRIFFITH'S LITERAL INTERPRETATION:
{griffith_round1[:800]}

GRIFFITH'S REBUTTAL TO YOU:
{griffith_rebuttal[:500]}

Your task: Provide a REBUTTAL defending your philosophical/spiritual interpretation.
- Address Griffith's material claims
- Show why spiritual reading reveals deeper truth
- Provide evidence from Upanishads and yogic texts
- Acknowledge any valid historical elements WITHOUT abandoning symbolic meaning

Be respectful but firm in defending spiritual depth.
"""

            sharma_rebuttal = self.llm.invoke(sharma_rebuttal_prompt).content
            print(sharma_rebuttal)
            debate_transcript.append({
                "round": round_num,
                "agent": "Sharma",
                "interpretation": sharma_rebuttal
            })

        # Synthesis: Identify original intent
        print("\n" + "="*80)
        print("🎓 SYNTHESIS: Original Intent Analysis\n")

        # Use both translations in synthesis if they differ
        verse_display = verse_text
        if griffith_text and sharma_text and griffith_text != sharma_text:
            verse_display = f"""
GRIFFITH'S TRANSLATION:
{griffith_text}

SHARMA'S TRANSLATION:
{sharma_text}
"""

        synthesis_prompt = f"""
You are a neutral Vedic scholar analyzing a debate between two translation philosophies.

VERSE: {verse_reference}
{verse_display}

GRIFFITH'S LITERAL VIEW:
{griffith_round1[:600]}

SHARMA'S PHILOSOPHICAL VIEW:
{sharma_round1[:600]}

Your task: Synthesize BOTH views to identify the ORIGINAL INTENT of the verse author.

Consider:
1. **Literal Layer**: What historical/material events might have inspired this?
2. **Symbolic Layer**: What spiritual truths were being encoded?
3. **Dual Intent**: Could the Rishi have meant BOTH simultaneously?
4. **Cultural Context**: How did ancient listeners understand multi-layered meaning?
5. **Translation Differences**: If the translations differ, what does that reveal about interpretation?

Provide a balanced synthesis that:
- Acknowledges validity in BOTH interpretations
- Identifies where they complement (not contradict) each other
- Proposes the original Rishi's likely FULL intent (literal + symbolic)

Format:
### Original Intent (Synthesis)
[Your balanced analysis]

### Complementary Elements
- Literal truth: [from Griffith]
- Symbolic truth: [from Sharma]

### Conclusion
[What the Rishi most likely meant, integrating both]
"""

        synthesis = self.llm.invoke(synthesis_prompt).content
        print(synthesis)

        # Save debate results to file
        result_dict = {
            "verse_reference": verse_reference,
            "verse_text": verse_text,
            "debate_transcript": debate_transcript,
            "synthesis": synthesis
        }

        # Save to JSON file
        import json
        import os
        from datetime import datetime

        debates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "debates")
        os.makedirs(debates_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_ref = verse_reference.replace(" ", "_").replace(".", "_")
        filename = f"debate_{safe_ref}_{timestamp}.json"
        filepath = os.path.join(debates_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, indent=2, ensure_ascii=False)

        logger.info(f"Debate saved to: {filepath}")
        print(f"\n💾 Debate transcript saved to: {filepath}\n")

        return result_dict


def create_debate_orchestrator():
    """Factory function to create debate orchestrator - no retrievers needed"""
    return DebateOrchestrator()
