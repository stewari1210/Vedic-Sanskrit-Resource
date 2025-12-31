# Vedic Agent Debate System

**Dialectical AI System for Vedic Translation Analysis**

A sophisticated debate system that uses AI agents representing different Vedic translation philosophies (Griffith's literal/historical vs Sharma's philosophical/spiritual) to converge on the original intent of Vedic hymns through dialectical synthesis.

---

## 🎯 Overview

This system implements a **thesis-antithesis-synthesis** debate framework where:

1. **Griffith Agent** (Thesis): Provides literal/historical interpretation
2. **Sharma Agent** (Antithesis): Provides philosophical/spiritual interpretation
3. **Synthesis**: Neutral analysis combining both views to recover the Rishi's original intent

### Why This Approach?

Vedic texts contain **multi-layered meanings**:
- **Literal Layer**: Historical events, natural phenomena, ritual practices
- **Symbolic Layer**: Spiritual truths, yogic concepts, metaphysical principles

A single translation philosophy misses half the picture. By holding both perspectives in dialectical tension, we can approximate what the ancient Rishis actually intended.

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone <repo-url>
cd RAG-CHATBOT-CLI-Version

# Switch to vedic-agent branch
git checkout vedic-agent

# Install dependencies
pip install -r requirements.txt

# Configure Python environment
# (System will prompt if needed)
```

### Basic Usage

**Complete Hymn Debate:**
```bash
python debate_cli.py --hymn "RV 2.33" --rounds 2
```

**Specific Verse Debate:**
```bash
python debate_cli.py --verse "RV 2.33.8" --sharma-text "Your Sharma translation here..." --rounds 2
```

**Interactive Mode:**
```bash
python debate_cli.py
```

---

## 📖 Usage Guide

### Two Debate Modes

#### 1. **`--hymn` / `--sukta` Mode** (Complete Hymn/Sukta)

Auto-retrieves **complete** hymn from both Griffith AND Sharma translations.

```bash
# Full hymn debate with 3 rounds
python debate_cli.py --hymn "RV 2.33" --rounds 3

# Same with --sukta alias
python debate_cli.py --sukta "RV 10.129" --rounds 2
```

**Use when:**
- You want holistic interpretation of entire hymn
- Both translators' complete versions are needed
- Analyzing thematic patterns across verses

#### 2. **`--verse` Mode** (Specific Verse)

Extracts **specific verse** from Griffith, prompts for Sharma text (since Sharma lacks verse numbers).

```bash
# Interactive (prompts for Sharma text)
python debate_cli.py --verse "RV 2.33.8" --rounds 2

# With Sharma text provided
python debate_cli.py --verse "RV 2.33.8" \
  --sharma-text "O Rudra, divine physician..." \
  --rounds 2
```

**Use when:**
- Focused analysis of single verse
- Comparing specific translation choices
- Sharma verse numbers unavailable (system handles this)

### Options

```bash
--hymn / --sukta      Complete hymn reference (e.g., "RV 2.33")
--verse               Specific verse (e.g., "RV 2.33.8")
--sharma-text         Sharma translation (for --verse mode)
--griffith-text       Override Griffith auto-retrieval
--rounds N            Number of debate rounds (default: 2)
--force               Force rebuild vector store
--quiet               Suppress INFO logs
```

---

## 🤖 Agent Roles

### Griffith Agent (Literal/Historical)

**Philosophy:**
- Deities = natural phenomena (Indra = storm, Agni = fire)
- Battles = REAL tribal warfare
- Chariots, weapons = LITERAL material culture
- Focus on archaeological evidence (Harappan, Sinauli ~2100 BCE)

**Approach:**
- Material/physical interpretation
- Historical context (tribes, rituals, warfare)
- Archaeological correlations
- Linguistic analysis

**Critical Guidelines:**
- Present evidence neutrally without assuming origins
- Distinguish facts (Sinauli chariots exist) from theories (their origin)
- Avoid presenting contested theories (Aryan Migration, OIT) as facts
- Acknowledge when evidence is ambiguous

### Sharma Agent (Philosophical/Spiritual)

**Philosophy:**
- Deities = cosmic principles and inner forces
- Battles = METAPHORS for spiritual struggles
- Material elements = yogic concepts (fire = illumination)
- Focus on Upanishadic wisdom, Vedanta, yogic practices

**Approach:**
- Symbolic/metaphorical interpretation
- Inner spiritual significance
- Connection to Upanishads and later philosophy
- Yogic/meditative context

**Debate Style:**
- Reveals deeper symbolic meanings
- Shows how literal readings miss spiritual truths
- Challenges materialist reductionism

### Synthesis (Neutral Scholar)

**Goal:** Identify **original Rishi intent** by integrating both views

**Considers:**
1. Literal Layer: Historical/material inspiration
2. Symbolic Layer: Spiritual truths encoded
3. Dual Intent: Could both be meant simultaneously?
4. Cultural Context: How did ancients understand multiple layers?
5. Translation Differences: What do they reveal?

**Output:**
- Balanced analysis combining both perspectives
- Identifies complementary (not contradictory) elements
- Proposes full intent (literal + symbolic)

---

## 🔍 Example: RV 2.33 (Rudra Hymn)

### Verse 8: "To him the strong, great, tawny, fair-complexioned, I utter forth a mighty hymn of praises..."

**Griffith's Interpretation:**
- "Tawny" = physical description of deity
- "Strong" = powerful storm god
- "Hymn" = ritual performance with chanting
- Archaeological: Ritual practices confirmed in Harappan sites

**Sharma's Interpretation:**
- "Tawny" = golden spiritual radiance
- "Strong" = power of divine consciousness
- "Hymn" = inner meditation, not just external ritual
- Connection: Upanishadic concept of Self as divine physician

**Synthesis:**
Original Rishi likely intended BOTH:
1. Literal: Powerful deity associated with storms and healing
2. Symbolic: Transformative power of divine consciousness
3. Ancient listeners understood both layers simultaneously
4. Multi-layered meaning was intentional, not accidental

---

## 🏗️ Technical Architecture

### Components

```
debate_cli.py                    # Main CLI interface
src/utils/debate_agents.py       # Agent implementations
src/cli_run.py                   # Vector store & retriever
src/utils/retriever.py          # Hybrid retrieval (BM25 + semantic)
src/utils/vector_store.py       # Qdrant vector database
```

### Retrieval Strategy

**Complete Hymn Retrieval:**
1. Parse verse reference (e.g., RV 2.33)
2. Format Griffith pattern: `[02-033] HYMN XXXIII`
3. Format Sharma pattern: `MANDAL - 2 / SUKTA - 33`
4. Retrieve using hybrid search (BM25 + semantic)
5. Collect sequential chunks until next hymn

**Verse Extraction (Griffith):**
```python
# Pattern: "8 To him the strong..."
# Extracts from "8 " until "9 " (next verse)
pattern = rf'(\s|^){verse_num}[\s\.]([A-Z][^0-9]+?)(?=\s+{verse_num + 1}[\s\.]|#|$)'
```

**Sharma Limitation:**
- Sharma's translation lacks explicit verse numbers
- Uses `[Names: ...]` section markers instead
- For `--verse` mode: User must provide Sharma text manually

### Vector Store

- **Engine**: Qdrant (local persistent storage)
- **Embeddings**: sentence-transformers/all-mpnet-base-v2
- **Size**: 18,215 chunks (Griffith: 4,456, Sharma: 13,759)
- **Retrieval**: Hybrid (BM25 30% + Semantic 70%), k=10

### LLM Configuration

- **Default**: Ollama llama3.1:8b (local inference)
- **Evaluation**: Google Gemini 2.5-flash-lite
- **Configurable**: See `src/settings.py`

---

## 📊 Output Format

### Debate Structure

```
================================================================================
📖 VERSE: RV 2.33
================================================================================

🔵 GRIFFITH'S TRANSLATION:
[Complete Griffith hymn text]

🟢 SHARMA'S TRANSLATION:
[Complete Sharma sukta text]

================================================================================

🎯 ROUND 1: Initial Interpretations

--------------------------------------------------------------------------------
GRIFFITH AGENT (Literal-Historical)

### Griffith's Literal Interpretation
[Material/physical analysis]

### Historical Context
[Archaeological correlations]

### Material Evidence
[Linguistic/cultural support]

--------------------------------------------------------------------------------
SHARMA AGENT (Philosophical-Spiritual)

### Sharma's Philosophical Interpretation
[Symbolic/spiritual analysis]

### Spiritual Symbolism
[Deeper meanings]

### Response to Literal View
[Why literal reading is incomplete]

================================================================================
🔄 ROUND 2: Rebuttals
[Agents respond to each other's arguments]

================================================================================
🎓 SYNTHESIS: Original Intent Analysis

### Original Intent (Synthesis)
[Balanced integration of both views]

### Complementary Elements
- Literal truth: [from Griffith]
- Symbolic truth: [from Sharma]

### Conclusion
[What the Rishi most likely meant]
```

### Debate Files

Saved to `debates/` directory:
```
debates/debate_RV_2_33_20251231_120345.json
```

Contains:
- Full transcript of all rounds
- Verse reference and texts
- Synthesis conclusion
- Metadata (timestamp, rounds, etc.)

---

## 🎓 Academic Integrity

### Archaeological Neutrality

This system has been carefully designed to avoid embedding controversial theories as facts:

**❌ What We DON'T Do:**
- Present Aryan Migration Theory as established fact
- Assume Sintashta origin for Vedic chariots
- Use outdated colonial-era scholarship uncritically
- Ignore recent archaeological findings (Sinauli, Rakhigarhi, etc.)

**✅ What We DO:**
- Present archaeological evidence neutrally
- Distinguish between established facts and contested theories
- Acknowledge ambiguity where it exists
- Focus on what verses DESCRIBE rather than who wrote them
- Reference current evidence (Sinauli chariots ~2100 BCE, etc.)

### Example

**AVOID:**
> "Chariots prove Indo-Aryan migration from Sintashta culture around 1500 BCE"

**PREFER:**
> "Chariots are described as ritual objects. Sinauli excavations (~2100 BCE) confirm ritualistic chariot use in the Indian subcontinent during this period. The origin and diffusion of chariot technology remains debated among scholars."

---

## 🔬 Research Applications

### Use Cases

1. **Translation Studies**: Compare how philosophical lens affects translation choices
2. **Hermeneutics**: Study multi-layered meaning in ancient texts
3. **Vedic Research**: Explore original intent through dialectical analysis
4. **Comparative Religion**: Analyze literal vs symbolic interpretation patterns
5. **AI Ethics**: Examine how to build unbiased scholarly AI systems

### Benefits

- **Reduces Confirmation Bias**: Forces consideration of opposing views
- **Reveals Translation Choices**: Shows how translator philosophy shapes word selection
- **Recovers Lost Meaning**: Multi-perspective analysis approximates original intent
- **Educational**: Demonstrates complexity of Vedic interpretation
- **Transparent**: All prompts and logic visible for academic scrutiny

---

## 🛠️ Development

### Project Structure

```
RAG-CHATBOT-CLI-Version/
├── debate_cli.py                      # Vedic debate CLI
├── src/
│   ├── cli_run.py                     # Standard RAG CLI (untouched)
│   ├── utils/
│   │   ├── debate_agents.py           # Agent implementations
│   │   ├── retriever.py               # Hybrid retrieval
│   │   ├── vector_store.py            # Qdrant integration
│   │   └── process_files.py           # Document processing
│   └── settings.py                    # Configuration
├── vector_store/                      # Qdrant database
│   └── ancient_history/
│       ├── docs_chunks.pkl            # Pickled document chunks
│       └── [qdrant files]
├── debates/                           # Saved debate transcripts
└── local_store/                       # Source documents
    └── ancient_history/
        ├── griffith/
        │   └── griffith.md            # Griffith Rigveda
        └── sharma/
            └── sharma_rigveda.md      # Sharma Rigveda
```

### Key Design Decisions

1. **Separate CLI**: `debate_cli.py` isolated from `cli_run.py` to avoid breaking standard RAG
2. **No Retriever in Agents**: Agents work with pre-fetched complete hymns, preventing retrieval pollution
3. **Dual Translation**: Each agent gets their own translator's version
4. **Sequential Chunk Collection**: Overcomes vector retrieval ranking issues
5. **Archaeological Neutrality**: Explicitly avoids embedding contested theories

### Testing

```bash
# Test complete hymn retrieval
python -c "
import sys
sys.path.insert(0, 'src')
from debate_cli import auto_retrieve_both_translations
from cli_run import build_index_and_retriever

vec_db, docs, retriever = build_index_and_retriever(force=False)
g, s = auto_retrieve_both_translations(retriever, 'RV 2.33')
print(f'Griffith: {len(g)} chars, Sharma: {len(s)} chars')
"

# Test verse extraction
python -c "
from debate_cli import extract_specific_verse_griffith
sample = '7 Where is... 8 To him the strong, great, tawny... 9 With firm limbs...'
result = extract_specific_verse_griffith(sample, 8)
print(result)
"

# Run full debate test
python debate_cli.py --hymn "RV 2.33" --rounds 1
```

---

## 📝 Version History

### vedic-agent Branch (December 2025)

**Major Features:**
- ✅ Dual-translation debate system
- ✅ Complete hymn/sukta retrieval
- ✅ Specific verse extraction (Griffith)
- ✅ Archaeological neutrality
- ✅ Separate CLI (`debate_cli.py`)
- ✅ Dialectical synthesis
- ✅ Debate transcript saving

**Key Fixes:**
- Removed Aryan Migration Theory bias
- Added Sinauli evidence (2100 BCE chariots)
- Fixed sequential chunk collection for Griffith
- Removed retriever calls from agents
- Implemented proper verse extraction regex

**Files Added:**
- `debate_cli.py` - Main debate interface
- `src/utils/debate_agents.py` - Agent implementations
- `VEDIC_AGENT_README.md` - This file

**Files Modified:**
- `src/cli_run.py` - Added export functions for debate system

---

## 🤝 Contributing

### Guidelines

1. **Archaeological Neutrality**: Never embed contested theories as facts
2. **Evidence-Based**: Always cite sources for archaeological claims
3. **Transparency**: Keep prompts visible and documented
4. **Testing**: Test with multiple hymns before committing
5. **Documentation**: Update README with new features

### Future Enhancements

- [ ] Add more translators (Wilson, Müller, etc.)
- [ ] Implement Sanskrit word-by-word analysis
- [ ] Add cross-references to other Vedic texts
- [ ] Integrate Upanishadic commentary
- [ ] Build web interface
- [ ] Add citation tracking for archaeological claims
- [ ] Implement debate visualization

---

## 📚 References

### Archaeological Sources

- **Sinauli Excavations (2018-2021)**: Ritualistic chariots dated ~2100 BCE
- **Harappan Sites**: Material culture evidence for ritual practices
- **Rakhigarhi DNA Studies**: Recent genomic analysis

### Translation Sources

- **Griffith, Ralph T.H.**: *The Hymns of the Rigveda* (1889-1892)
- **Sharma, Pt. Ramgovind Trivedi**: *Rigveda Samhita* (Hindi with philosophical commentary)

### Methodology

- **Dialectical Method**: Hegel's thesis-antithesis-synthesis
- **Hermeneutics**: Multi-layered textual interpretation
- **Comparative Mythology**: Cross-cultural deity analysis

---

## 📄 License

[Your license here]

---

## 👤 Contact

[Your contact information]

---

## 🙏 Acknowledgments

- Ralph T.H. Griffith for literal translation foundation
- Pt. Ramgovind Trivedi Sharma for philosophical insights
- Archaeological teams at Sinauli, Rakhigarhi, and Harappan sites
- Open source community (Qdrant, LangChain, Ollama, sentence-transformers)

---

**Built with the belief that ancient wisdom deserves rigorous, unbiased, multi-perspective analysis.**

*"Truth is one; sages call it by various names"* - Rigveda 1.164.46
