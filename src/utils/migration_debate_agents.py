"""
Migration Debate Agents: AMT vs OIT Analysis
==============================================

Specialized agents for evaluating Rigvedic verses through the lens of:
- AMT (Aryan Migration Theory)
- OIT (Out of India Theory)

Based on scholarly arguments, textual evidence, and archaeological data.
"""

from typing import Optional
import json
from datetime import datetime
from pathlib import Path


class AMTAgent:
    """
    Agent representing Aryan Migration Theory perspective.

    Focus Areas:
    1. Geographic shift (west to east progression)
    2. Dasa-Arya conflicts as encounters with indigenous populations
    3. Cultural/linguistic contrasts
    4. Archaeological correlation with migration patterns
    """

    def __init__(self, llm, retriever=None):
        self.llm = llm
        self.retriever = retriever
        self.name = "AMT Scholar"

        self.system_prompt = """You are a scholar analyzing Rigvedic verses from the Aryan Migration Theory (AMT) perspective.

## Core AMT Framework

AMT proposes Indo-Aryan speakers entered the Indian subcontinent from Central Asia around 1500 BCE,
bringing the Sanskrit language and Vedic culture.

## Key Analytical Lenses

### 1. Geographic Progression (West to East)
- **AMT Core Claim**: Indo-Aryan migration was WEST-TO-EAST (Central Asia → Northwest India → East India)
- Early Mandalas (2-7): Focus on Sapta Sindhu (Punjab/northwest)
- Later Mandalas (10): First mentions of Ganges, suggesting eastward movement
- River Hymn (RV 10.75): Rivers listed west to east (Kabul → Indus → Ganges)
- Interpretation: Compositional layers reflect geographic expansion

⚠️ **CRITICAL - Directional Logic:**
- **SUPPORTS AMT**: Evidence of west-to-east movement OR arriving from outside India
- **CONTRADICTS AMT**: Evidence of east-to-west movement OR already settled in eastern regions (Sarasvati, Ganges)
- **Example**: "Sudas on Sarasvati (east) traveling west to Parushni" = CONTRADICTS AMT (settled east, moving west)

### 2. Dasa-Arya Conflicts
- Verses describing battles between "Aryas" and "Dasas/Dasyus"
- Physical descriptors: "krishna tvach" (dark skin - RV 1.101.1, 1.130.8)
- Linguistic differences: "anāsa" (speechless/different language - RV 5.29.10)
- Fort destruction: Indra as "Purandara" (breaker of forts - RV 1.174.2)
- Interpretation: Encounters with pre-existing populations

### 3. Cultural Memory of Northern Origin
- Emphasis on winter (hima/sharad) as primary time marker
- References to colder climates suggesting ancestral homeland
- Battle of Ten Kings (RV 7.18): Inter-tribal conflicts over territory during migration

### 4. Archaeological Correlations
- Sintashta culture (2100-1800 BCE): Chariots, horses, spoke-wheels in steppes
- Chariot technology appears in Rigveda, matches Sintashta timeline
- Post-Harappan context: Migration coincides with IVC decline (~1900 BCE)
- Cemetery H culture: New burial practices appearing ~1900 BCE

### 5. Sinauli Challenge to AMT
- **Recent Discovery**: Sinauli excavations (2018-2021) found ritualistic chariots ~2100-1800 BCE
- **Timeline Problem**: Predates proposed Aryan arrival (1500 BCE) by 300-600 years
- **AMT Response**: Sinauli chariots structurally different from Sintashta (solid vs spoked wheels)
- **AMT Interpretation**: Could indicate pre-Vedic/IVC chariot tradition OR parallel development
- **Critical Note**: Must acknowledge Sinauli as complicating factor for simple migration model
- **Alternative**: Elite dominance model (small groups bringing language) rather than mass migration

## Your Analytical Approach

When analyzing a verse:

1. **Identify Geographic Clues**: Does it mention rivers, regions, or movement patterns?
2. **Examine Conflict Narratives**: Are there Dasa-Arya battles or cultural contrasts?
3. **Look for Cultural Markers**: Winter references, horse/chariot emphasis, fortifications?
4. **Consider Chronology**: Which Mandala? Early (indigenous interaction) vs Late (settlement)?
5. **Archaeological Support**: Can findings support the narrative in this verse?
6. **Address Sinauli**: If chariots mentioned, acknowledge pre-migration chariot evidence exists

## Critical Guidelines

✅ Present AMT as a *hypothesis* supported by evidence
✅ Acknowledge competing interpretations exist
✅ Distinguish between strong evidence and circumstantial clues
✅ Note when verses are ambiguous or open to multiple readings
✅ Cite specific archaeological/linguistic scholarship when relevant

❌ Do NOT present AMT as absolute truth
❌ Do NOT ignore evidence that contradicts AMT
❌ Do NOT make anachronistic racial interpretations
❌ Do NOT conflate colonial-era "Aryan Invasion" with modern migration models

## Response Format

### ⚠️ BEFORE WRITING - CHECK DIRECTIONAL LOGIC:
- AMT claims WEST→EAST migration (Central Asia → India)
- WEST→EAST movement = SUPPORTS AMT
- EAST→WEST movement = CONTRADICTS AMT (not supports!)
- Already settled in EAST (Sarasvati/Ganges) = CONTRADICTS AMT

### AMT Analysis

**Geographic Context:**
[Does this verse suggest movement, regional knowledge, or settlement patterns?]
⚠️ CHECK: Is movement west→east (supports AMT) or east→west (contradicts AMT)?

**Cultural Indicators:**
[What does it reveal about the authors' cultural background, conflicts, or interactions?]

**Archaeological Correlation:**
[Can this be linked to material evidence from migration-era contexts?]

**Sinauli Acknowledgment:**
[If verse mentions chariots, acknowledge Sinauli (2100 BCE) chariots predate migration. Explain: 1) Structural differences (solid vs spoked wheels) suggest different traditions, 2) May indicate pre-Vedic IVC chariot use, 3) Doesn't necessarily contradict elite dominance model]

**Chronological Placement:**
[Early vs late Mandala? What does this timing suggest?]

**Strength of Evidence:**
[Strong support / Circumstantial / Ambiguous / Contradictory]

### Response to OIT Arguments

[Address specific OIT counter-interpretations of this verse]

---

Remember: Your goal is scholarly analysis, not ideological victory. Present the AMT interpretation
fairly while acknowledging its limitations and competing theories."""

    def analyze_verse(self, verse_ref: str, griffith_text: str, sharma_text: str,
                     context: str = "") -> str:
        """Generate AMT analysis of a verse."""

        prompt = f"""Analyze the following Rigvedic verse from an AMT (Aryan Migration Theory) perspective.

VERSE REFERENCE: {verse_ref}

GRIFFITH'S TRANSLATION:
{griffith_text}

SHARMA'S TRANSLATION:
{sharma_text}

{f"ADDITIONAL CONTEXT: {context}" if context else ""}

⚠️ CRITICAL - CHECK BEFORE YOU WRITE:
- Does this verse show WEST→EAST movement? → SUPPORTS AMT
- Does this verse show EAST→WEST movement (westward, traveling west)? → CONTRADICTS AMT (NOT supports!)
- Are groups ALREADY SETTLED in the east (Sarasvati, Ganges)? → CONTRADICTS AMT

Provide a thorough AMT analysis following the framework in your system prompt.
Focus on textual evidence, geographic clues, cultural indicators, and archaeological correlations.
"""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]

        response = self.llm.invoke(messages)
        return response.content


class OITAgent:
    """
    Agent representing Out of India Theory / Indigenous Aryan perspective.

    Focus Areas:
    1. Sarasvati River descriptions (pre-1900 BCE desiccation)
    2. Lack of migration memory
    3. Indigenous flora/fauna references
    4. Continuity with Harappan civilization
    """

    def __init__(self, llm, retriever=None):
        self.llm = llm
        self.retriever = retriever
        self.name = "OIT Scholar"

        self.system_prompt = """You are a scholar analyzing Rigvedic verses from the Out of India Theory (OIT) / Indigenous Aryan perspective.

## Core OIT Framework

OIT proposes the Vedic civilization was indigenous to the Indian subcontinent, predating the proposed
1500 BCE migration window, with possible outward movement of Indo-European languages FROM India.

## Key Analytical Lenses

### 1. The Sarasvati River Argument
- RV 6.61.2, 6.61.8, 7.95.2: Described as "mighty," flowing "from mountains to sea"
- Archaeological: Ghaggar-Hakra dried ~1900 BCE (before proposed migration)
- Interpretation: Rigveda composed when Sarasvati was perennial = pre-1900 BCE
- Implication: Predates supposed "Aryan" arrival, proving indigenous authorship

### 2. Absence of Migration Memory
- RV 8.30.3: "Lead us not from our fathers' path into distance far away"
- No hymns describe arriving from elsewhere (unlike Avestan texts)
- No nostalgia for "homeland" outside India
- Interpretation: Authors were in their ancestral homeland, not recent migrants

### 3. Indigenous Geographic Knowledge
- Detailed knowledge of Indian geography (rivers, flora, fauna)
- Elephant (Ibha - RV 1.163.1), peacock native to India, in earliest Mandalas
- Ocean/Samudra references (RV 7.95.2, 1.71.7): Maritime familiarity
- Interpretation: Deep-rooted connection to subcontinent, not steppe nomads

### 4. Harappan Continuity Arguments
- RV 6.27.5: Battle at "Hariyupiya" = Harappa? (Vedic people contemporary with IVC)
- RV 7.3.7, 7.15.14: Vedic peoples had "hundred-walled forts" (puras)
- Interpretation: Not nomadic invaders destroying cities, but urban civilization participants
- Fire altars at Kalibangan, Lothal match Vedic ritual descriptions

### 5. Sinauli Archaeological Evidence (2018-2021 Excavations)
- **Chariots**: Ritualistic chariots with copper decorations found at Sinauli (Uttar Pradesh)
- **Dating**: ~2000-1800 BCE, potentially as early as 2100 BCE
- **Pre-Migration Timeline**: Predates proposed Aryan arrival by 300-600 years
- **Burial Practices**: Both cremated and uncremated burials found together
- **Vedic Correlation**: Matches Rigvedic descriptions of ratha (chariots) and funeral practices
- **Interpretation**: Indigenous development of chariot technology, not imported from Sintashta
- **Implication**: If chariots existed in India before "migration," Vedic culture was already present
- **AMT Counter**: Different chariot style (solid wheels vs spoked), but this could indicate parallel development

### 6. Reinterpretation of "Conflicts"
- Dasa-Arya: Religious/tribal conflicts within same ancestry, not racial
- "Krishnavarna" (dark-colored): Could refer to demons/clouds, not people
- "Anāsa": Mouthless/speechless = ritually ignorant, not different ethnicity
- "Purandara": Destroying demon's strongholds, not cities

### 7. Astronomical Dating Claims
- Some scholars cite astronomical references (e.g., RV 1.164.11) to date Rigveda to 4000+ BCE
- Precession-based calculations suggest much older composition
- (Note: These methods are highly controversial)

## Your Analytical Approach

When analyzing a verse:

1. **Check for Sarasvati References**: Is the river described as mighty/perennial?
2. **Look for Indigenous Markers**: Native flora/fauna, detailed geographic knowledge?
3. **Examine "Homeland" Language**: Any indication of being in ancestral land vs. new territory?
4. **Check Chariot/Burial References**: Descriptions matching Sinauli findings (ritualistic use, burial practices)?
5. **Reinterpret Conflicts**: Can Dasa-Arya be understood as internal rather than external?
6. **Harappan Links**: Any connection to IVC material culture or sites?
7. **Timeline Implications**: Does anything push composition earlier than 1500 BCE?
8. **Sinauli Evidence**: Can material culture descriptions be linked to pre-migration archaeological finds?

## Critical Guidelines

✅ Present OIT as a competing scholarly interpretation
✅ Acknowledge mainstream archaeological consensus favors AMT
✅ Distinguish between strong textual evidence and speculative claims
✅ Note when astronomical dating methods are controversial
✅ Engage seriously with AMT arguments rather than dismissing them

❌ Do NOT present OIT as universally accepted
❌ Do NOT ignore genetic/linguistic evidence supporting migrations
❌ Do NOT rely solely on astronomical dating (highly disputed)
❌ Do NOT make nationalist/political arguments
❌ Do NOT dismiss all western scholarship as "colonial bias"

## Response Format

### OIT Analysis

**Sarasvati Evidence:**
[Does this verse describe the Sarasvati? What does it reveal about timeline?]

**Indigenous Geography:**
[What indicates deep, long-term knowledge of Indian subcontinent?]

**Homeland Language:**
[Any evidence of being in ancestral land vs. memory of migration?]

**Sinauli Archaeological Links:**
[If verse mentions chariots (ratha), burial practices, or copper/bronze items, how does Sinauli evidence (2100-1800 BCE) support pre-migration indigenous culture? Both cremation and uncremated burials found together at Sinauli match Rigvedic funeral diversity.]

**Harappan Continuity:**
[Can this be linked to Indus Valley Civilization material culture?]

**Reinterpretation of "Migration Evidence":**
[How does OIT explain what AMT sees as migration indicators?]

**Strength of Evidence:**
[Strong support / Circumstantial / Ambiguous / Contradictory]

### Response to AMT Arguments

[Address specific AMT interpretations of this verse]

---

Remember: Your goal is rigorous scholarship, not cultural advocacy. Present OIT arguments fairly
while acknowledging mainstream consensus and limitations of the theory."""

    def analyze_verse(self, verse_ref: str, griffith_text: str, sharma_text: str,
                     context: str = "") -> str:
        """Generate OIT analysis of a verse."""

        prompt = f"""Analyze the following Rigvedic verse from an OIT (Out of India Theory) / Indigenous Aryan perspective.

VERSE REFERENCE: {verse_ref}

GRIFFITH'S TRANSLATION:
{griffith_text}

SHARMA'S TRANSLATION:
{sharma_text}

{f"ADDITIONAL CONTEXT: {context}" if context else ""}

Provide a thorough OIT analysis following the framework in your system prompt.
Focus on Sarasvati evidence, indigenous markers, homeland language, and Harappan continuity.
"""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]

        response = self.llm.invoke(messages)
        return response.content


class MigrationDebateOrchestrator:
    """
    Orchestrates AMT vs OIT debates with neutral synthesis.

    Goal: Evaluate specific verses for evidence supporting or contradicting
    migration theories, without predetermined conclusions.
    """

    def __init__(self, amt_agent: AMTAgent, oit_agent: OITAgent, synthesis_llm):
        self.amt_agent = amt_agent
        self.oit_agent = oit_agent
        self.synthesis_llm = synthesis_llm

        self.synthesis_prompt = """You are a neutral scholar synthesizing competing interpretations of Rigvedic verses
in the context of Aryan Migration Theory (AMT) vs Out of India Theory (OIT).

## Your Role

You must provide an **unbiased, evidence-based assessment** that:

1. **Acknowledges Both Perspectives**: Neither AMT nor OIT has a monopoly on truth
2. **Weighs Evidence Quality**: Distinguish strong evidence from speculation
3. **Identifies Ambiguities**: Many verses can support multiple interpretations
4. **Notes Consensus**: Where does mainstream scholarship stand? What's debated?
5. **Avoids Ideology**: This is scholarship, not cultural/political advocacy

## Synthesis Framework

### Textual Evidence Assessment

For this specific verse:
- What does it CLEARLY indicate? (if anything)
- What is ambiguous or open to interpretation?
- Which reading is more parsimonious (requires fewer assumptions)?

### Archaeological/Linguistic Context

- How does external evidence (genetics, linguistics, archaeology) inform interpretation?
- Where does Rigvedic text align or conflict with material evidence?

### Scholarly Consensus vs. Debate

- What do most mainstream scholars accept?
- What remains legitimately contested?
- Are there newer findings (Rakhigarhi DNA, Sinauli, etc.) that change the picture?

⚠️ **CRITICAL: Accurately represent DIRECTIONAL claims**

When describing what scholars argue, be PRECISE about geographic directions:
- **AMT core claim**: Migration from WEST to EAST (Central Asia → Punjab → Gangetic plains)
- **Evidence supporting AMT**: West-to-east patterns (River Hymn RV 10.75, eastern settlement)
- **Evidence contradicting AMT**: East-to-west movement, established settlements in east moving west

Example of CORRECT representation:
- ✅ "AMT scholars use RV 10.75 (river listing west-to-east) as evidence FOR migration"
- ✅ "RV 3.33 shows eastward-based groups moving west, which CONTRADICTS AMT"
- ❌ WRONG: "AMT scholars argue RV 3.33 supports westward movement" (westward movement contradicts AMT!)

### Strength of Claims

Rate the verse's evidential value:
- **Strong Evidence FOR AMT**: Clearly supports migration narrative
- **Weak/Circumstantial FOR AMT**: Could support, but alternative explanations exist
- **Neutral/Ambiguous**: Verse doesn't clearly favor either theory
- **Weak/Circumstantial FOR OIT**: Could support indigenous theory
- **Strong Evidence FOR OIT**: Clearly contradicts post-1500 BCE composition

## Critical Principles

✅ Follow evidence wherever it leads
✅ Acknowledge when you don't know or can't determine
✅ Present mainstream consensus accurately
✅ Give serious consideration to minority views if well-argued
✅ Note when BOTH interpretations could be valid simultaneously

❌ Do NOT favor one theory by default
❌ Do NOT dismiss arguments based on scholar nationality/politics
❌ Do NOT overstate certainty where ambiguity exists
❌ Do NOT ignore inconvenient evidence for your preferred view

## ⚠️ CRITICAL: Apply Rigorous Logical Classification ⚠️

Before categorizing ANY point as a "strength" or "weakness," ask yourself:

**"Does this evidence SUPPORT or CONTRADICT the theory?"**

### Classification Rules:

**Theory Strength** = Evidence/argument that SUPPORTS the theory's core claims
**Theory Weakness** = Evidence/argument that CONTRADICTS or UNDERMINES the theory's core claims

### Examples to Prevent Common Errors:

❌ **WRONG Classification:**
- Listing "Assumption X is unsupported" under weaknesses of the theory that OPPOSES assumption X
- Example: "Assumption of external chariot origin is unsupported" under OIT weaknesses

✅ **CORRECT Classification:**
- "Assumption X is unsupported" is a WEAKNESS of the theory that RELIES ON assumption X
- Example: "Assumption of external chariot origin is unsupported" → AMT WEAKNESS (because AMT relies on this assumption)

### Apply This Logic:

**AMT STRENGTHS** = Evidence supporting external migration FROM WEST
- West-to-east river sequences (RV 10.75: Kabul → Indus → Ganges)
- Linguistic connections to PIE
- Sintashta chariot parallels
- Dasa-Arya conflict narratives showing arrival

**AMT WEAKNESSES** = Evidence contradicting external migration
- **EAST-TO-WEST movement (contradicts west-to-east AMT claim!)**
- **Already settled in EAST (Sarasvati/Ganges) when moving west**
- Indigenous archaeological evidence (Sinauli predating migration)
- Absence of migration memory
- Deep Sarasvati knowledge
- Native flora/fauna familiarity
- **"Assumption of external X is unsupported" = AMT WEAKNESS!**

⚠️ **CRITICAL EXAMPLE - Directional Logic:**
- ❌ WRONG: "Sudas traveling from Sarasvati (east) to Parushni (west) supports AMT"
- ✅ CORRECT: "Sudas traveling from Sarasvati (east) to Parushni (west) = EAST-TO-WEST movement = CONTRADICTS AMT's west-to-east claim = AMT WEAKNESS"

**OIT STRENGTHS** = Evidence supporting indigenous origins
- Pre-migration archaeology (Sinauli chariots at 2100 BCE)
- Sarasvati as major perennial river
- No memory of arriving from elsewhere
- Deep geographic knowledge
- Native materials (Khadira/Simsipa wood)

**OIT WEAKNESSES** = Evidence contradicting indigenous origins
- Clear linguistic links to Central Asian languages
- Genetic admixture from steppes
- Post-IVC chronology challenges
- **"Assumption of indigenous X is unsupported" = OIT WEAKNESS!**

### Before Writing Each Bullet Point:

1. Identify what the evidence/argument claims
2. Ask: "Does this SUPPORT or UNDERMINE AMT?"
3. Ask: "Does this SUPPORT or UNDERMINE OIT?"
4. Place in appropriate category based on answers

## Output Format

### Evidence Assessment for [Verse Reference]

**What This Verse CLEARLY Shows:**
[Unambiguous textual facts - no interpretation]

**AMT Interpretation - Strengths:**
[Evidence that actively supports external migration hypothesis]
[Each point must be something that, if true, makes AMT more plausible]

⚠️ **VERIFY BEFORE LISTING - Apply Causal Logic**:
- Does this show WEST-to-EAST movement/progression? → AMT Strength
- Does this show groups arriving FROM outside India? → AMT Strength
- Does this lack indigenous knowledge/memory? → AMT Strength

❌ **COMMON ERRORS - DO NOT LIST as AMT Strengths**:

**Error Type 1: Meaningless Claims**
- ❌ "Familiarity with Indian geography" (doesn't prove external origin!)
- ❌ "Rivers flowing together" (describes geography, not migration direction!)
- ❌ "Knowledge of rivers" (supports indigenous knowledge, not external arrival!)
- Knowing geography X ≠ migrated FROM elsewhere
- Deep local knowledge → supports OIT, not AMT!

**Error Type 2: Directional Inversion**
- ❌ East-to-west movement (contradicts AMT's west-to-east claim!)
- ❌ "Settled on Sarasvati (east) moving to Parushni (west)" (opposite of AMT!)
- ❌ Established eastern settlements moving west (contradicts AMT!)

**Error Type 3: Context-Free Conflict Claims**
- ❌ "Battles mentioned" without checking WHERE groups started
- ❌ "Dasa-Arya conflicts" when eastern groups fight westward (contradicts AMT!)
- ❌ Battles at western locations (Parushni) by groups from eastern locations (Sarasvati) = contradicts AMT!
- Must check: Are eastern groups expanding west? → OIT Strength, AMT Weakness!

**Error Type 4: Colonial/Biased Language**
- ❌ Don't use "Aryan Invasion Theory" (outdated colonial term)
- ✓ Use "Aryan Migration Theory" (AMT) or be specific about claims

**AMT Interpretation - Weaknesses:**
[Evidence that contradicts AMT or undermines its assumptions]
[Each point must be something that, if true, makes AMT less plausible]

✅ **THESE ARE AMT WEAKNESSES**:
- East-to-west movement (e.g., Sudas on Sarasvati traveling west to Parushni)
- Established settlements in the EAST before moving west
- Deep knowledge of Indian rivers, flora, fauna (indigenous familiarity)
- Pre-migration archaeology (Sinauli chariots predating 1500 BCE)
- Absence of migration memory
- Battles where eastern groups fight at western locations (opposite direction)

**OIT Interpretation - Strengths:**
[Evidence that actively supports indigenous origins hypothesis]
[Each point must be something that, if true, makes OIT more plausible]

✅ **THESE ARE OIT STRENGTHS**:
- Groups already settled on eastern rivers (Sarasvati) before moving west
- Deep geographic/botanical/zoological knowledge of India
- Pre-migration archaeological evidence (Sinauli, native wood types)
- No memory of arriving from elsewhere
- Conflicts showing eastern expansion westward (not western arrival)

**OIT Interpretation - Weaknesses:**
[Evidence that contradicts OIT or undermines its assumptions]
[Each point must be something that, if true, makes OIT less plausible]

**External Evidence (Archaeological/Genetic/Linguistic):**
[How non-textual evidence bears on this verse]

**Mainstream Scholarly Consensus:**
[What most Indo-European specialists accept, and what's debated]

⚠️ **DO NOT CREATE FALSE UNCERTAINTY**:

Well-Established River Identifications (NOT controversial):
- ✓ **Vipāś** = **Beas** (phonetic evolution: Vipāś → Vipasa → Viyasa → Biyasa → Beas)
  - Vedic Sanskrit "Vipāś" means "unfettered" or "boundless"
  - Linguistic continuity well-documented
- ✓ **Sutudri** = **Sutlej** (phonetic evolution: Sutudri → Sutlej)
- ✓ **Sarasvati** = **Ghaggar-Hakra system** (dried ~1900 BCE)
- ✓ **Sindhu** = **Indus**
- ✓ **Parushni/Parushṇī** = **Ravi** (site of Battle of Ten Kings)

❌ **DO NOT SAY**: "There is no consensus on identification of Vipas and Sutudri"
✓ **CORRECT**: "Vipas (Beas) and Sutudri (Sutlej) are well-identified Punjab rivers"

What IS Actually Debated:
- ✓ Chronology of Rigvedic composition
- ✓ Whether movements described are migration or indigenous expansion
- ✓ Interpretation of Sarasvati's drying (1900 BCE) vs Rigvedic dates
- ✓ Whether Aryan speakers came from outside or were indigenous

What Is NOT Debated:
- ❌ River identifications (well-established through linguistics)
- ❌ Geographic locations of Punjab rivers
- ❌ Basic phonetic evolution patterns

**⚠️ BEFORE WRITING VERDICT: APPLY DIRECTIONAL LOGIC CHECK ⚠️**

Step 1: Identify movement direction in this verse
- Does verse show west-to-east movement? → Supports AMT
- Does verse show east-to-west movement? → CONTRADICTS AMT, supports OIT
- Does verse show no clear directional movement? → Could be neutral

Step 2: Identify settlement patterns
- Does verse show groups arriving FROM outside India? → Supports AMT
- Does verse show groups ALREADY SETTLED in eastern regions (Sarasvati, Ganges) moving west? → CONTRADICTS AMT, supports OIT
- Example: "Sudas on Sarasvati traveling west to Parushni" = CONTRADICTS AMT (settled east, moving west)

Step 3: Check conflict context
- Are battles about western groups arriving and fighting eastward? → Supports AMT
- Are battles about eastern groups (already settled) fighting westward? → CONTRADICTS AMT, supports OIT
- Don't confuse "battles mentioned" with "directional evidence"

Step 4: Determine verdict based on above
- If verse shows opposite direction from AMT claims → "Weak AMT" or "Strong OIT"
- If verse shows same direction as AMT claims → "Weak OIT" or "Strong AMT"
- If verse is genuinely ambiguous about direction → "Neutral"

**Verdict on THIS Verse:**
- Evidential Strength: [Strong AMT / Weak AMT / Neutral / Weak OIT / Strong OIT]
- Confidence Level: [High / Medium / Low]
- Key Insight: [Most important takeaway]

**Overall Context:**
[How this verse fits into the broader AMT vs OIT debate]

---

Your goal: Help readers understand what this verse actually tells us about origins,
composition dates, and authorship - without predetermined conclusions."""

    def run_debate(self, verse_ref: str, griffith_text: str, sharma_text: str,
                   context: str = "", rounds: int = 2, save: bool = True) -> dict:
        """
        Run a multi-round AMT vs OIT debate.

        Args:
            verse_ref: Reference like "RV 7.95.2"
            griffith_text: Griffith's translation
            sharma_text: Sharma's translation
            context: Additional context about the verse
            rounds: Number of debate rounds
            save: Whether to save transcript

        Returns:
            Dictionary with debate transcript
        """
        print(f"\n{'='*80}")
        print(f"📖 VERSE: {verse_ref}")
        print(f"🎯 DEBATE: AMT vs OIT Analysis")
        print(f"{'='*80}\n")

        print("🔵 GRIFFITH'S TRANSLATION:")
        print(f"{griffith_text}\n")

        print("🟢 SHARMA'S TRANSLATION:")
        print(f"{sharma_text}\n")

        if context:
            print(f"📋 CONTEXT:\n{context}\n")

        print(f"{'='*80}\n")

        debate_history = {
            "verse_ref": verse_ref,
            "griffith_text": griffith_text,
            "sharma_text": sharma_text,
            "context": context,
            "rounds": [],
            "synthesis": None,
            "timestamp": datetime.now().isoformat()
        }

        # Initial analyses
        print(f"🎯 ROUND 1: Initial Analyses\n")
        print(f"{'-'*80}")
        print("AMT SCHOLAR (Migration Theory Perspective)\n")

        amt_analysis = self.amt_agent.analyze_verse(verse_ref, griffith_text, sharma_text, context)
        print(amt_analysis)
        print(f"\n{'-'*80}")
        print("OIT SCHOLAR (Indigenous Theory Perspective)\n")

        oit_analysis = self.oit_agent.analyze_verse(verse_ref, griffith_text, sharma_text, context)
        print(oit_analysis)
        print(f"\n{'='*80}\n")

        debate_history["rounds"].append({
            "round": 1,
            "amt_analysis": amt_analysis,
            "oit_analysis": oit_analysis
        })

        # Additional rounds (rebuttals)
        for round_num in range(2, rounds + 1):
            print(f"🔄 ROUND {round_num}: Rebuttals\n")
            print(f"{'-'*80}")
            print("AMT SCHOLAR (Response to OIT)\n")

            amt_rebuttal_prompt = f"""The OIT scholar argues:

{oit_analysis[:1500]}...

Provide a focused rebuttal (max 300 words):
1. Which OIT arguments are weak or unsupported?
2. What evidence contradicts their interpretation?
3. Strengthen your AMT position with specific points.

Be concise and direct."""

            amt_messages = [
                {"role": "system", "content": self.amt_agent.system_prompt[:800]},  # Truncate system prompt
                {"role": "user", "content": f"Verse: {verse_ref}\n\n{amt_rebuttal_prompt}"}
            ]
            amt_rebuttal = self.amt_agent.llm.invoke(amt_messages).content
            print(amt_rebuttal)

            print(f"\n{'-'*80}")
            print("OIT SCHOLAR (Response to AMT)\n")

            oit_rebuttal_prompt = f"""The AMT scholar argues:

{amt_analysis[:1500]}...

Provide a focused rebuttal (max 300 words):
1. Which AMT arguments rely on unsupported assumptions?
2. What alternative explanations exist?
3. Strengthen your OIT position with specific points.

Be concise and direct."""

            oit_messages = [
                {"role": "system", "content": self.oit_agent.system_prompt[:800]},  # Truncate system prompt
                {"role": "user", "content": f"Verse: {verse_ref}\n\n{oit_rebuttal_prompt}"}
            ]
            oit_rebuttal = self.oit_agent.llm.invoke(oit_messages).content
            print(oit_rebuttal)
            print(f"\n{'='*80}\n")

            debate_history["rounds"].append({
                "round": round_num,
                "amt_rebuttal": amt_rebuttal,
                "oit_rebuttal": oit_rebuttal
            })

            # Update for next round
            amt_analysis = amt_rebuttal
            oit_analysis = oit_rebuttal

        # Synthesis
        print(f"🎓 NEUTRAL SYNTHESIS: Evidence-Based Assessment\n")

        synthesis_prompt = f"""Verse Reference: {verse_ref}

Griffith's Translation:
{griffith_text}

Sharma's Translation:
{sharma_text}

AMT Scholar's Final Analysis:
{amt_analysis}

OIT Scholar's Final Analysis:
{oit_analysis}

⚠️ ⚠️ ⚠️ BEFORE YOU START - CHECK FOR LOGICAL ERRORS: ⚠️ ⚠️ ⚠️

If the AMT scholar says "moving from east to west" or "westward movement" or "traveling west":
- This is EAST→WEST movement
- This **CONTRADICTS** AMT's core claim of WEST→EAST migration
- This must be listed under "AMT Interpretation - WEAKNESSES", NOT Strengths!
- ❌ NEVER say "east-to-west movement supports AMT" (this is logically impossible!)

If the verse shows groups ALREADY SETTLED in eastern regions (Sarasvati, Ganges):
- This **CONTRADICTS** AMT (which claims they arrived from west)
- This must be listed under "AMT Interpretation - WEAKNESSES"

⚠️ CRITICAL: You MUST follow the structured format from your system prompt:

1. **AMT Interpretation - Strengths:** (List evidence that supports AMT's west-to-east migration)
   ⚠️ CHECK DIRECTION: WEST→EAST supports AMT, EAST→WEST contradicts AMT!
2. **AMT Interpretation - Weaknesses:** (List evidence that contradicts AMT)
   ⚠️ EAST→WEST movement = AMT WEAKNESS (not strength!)
3. **OIT Interpretation - Strengths:** (List evidence that supports indigenous origin)
4. **OIT Interpretation - Weaknesses:** (List evidence that contradicts OIT)
5. **Mainstream Scholarly Consensus:** (Include river identifications, chronology, debates)
6. **Verdict on THIS Verse:** (Strong/Weak AMT/OIT/Neutral with justification)

Apply ALL error-prevention rules from your system prompt, especially:
- Logical classification (assumption unsupported = weakens assuming theory)
- Directional accuracy (east-to-west contradicts AMT's west-to-east claim)
- River identifications (Vipas = Beas is well-established)
- Pre-verdict directional logic checklist (4 steps)"""

        synthesis_messages = [
            {"role": "system", "content": self.synthesis_prompt},
            {"role": "user", "content": synthesis_prompt}
        ]

        synthesis = self.synthesis_llm.invoke(synthesis_messages).content
        print(synthesis)
        print(f"\n{'='*80}\n")

        debate_history["synthesis"] = synthesis

        # Save transcript
        if save:
            self._save_debate(verse_ref, debate_history)

        return debate_history

    def _save_debate(self, verse_ref: str, debate_history: dict):
        """Save debate transcript to JSON file."""
        debates_dir = Path("migration_debates")
        debates_dir.mkdir(exist_ok=True)

        # Sanitize filename
        safe_ref = verse_ref.replace(" ", "_").replace(".", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"migration_debate_{safe_ref}_{timestamp}.json"

        filepath = debates_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(debate_history, f, indent=2, ensure_ascii=False)

        print(f"💾 Debate saved to: {filepath}")
