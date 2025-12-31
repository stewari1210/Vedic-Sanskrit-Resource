# Vedic Translation Debate System - PoC Documentation

## Overview
A multi-agent system where two translation philosophies debate to converge on original Rishi intent.

## Agents

### 1. Griffith Agent (Literal-Historical)
- **Philosophy**: Materialist, historicist interpretation
- **Approach**:
  - Treats Vedic verses as describing real historical events
  - Deities = Natural phenomena (Indra = storm, Agni = fire)
  - Battles = Actual tribal warfare
  - Material culture focus (chariots, weapons, rituals)
- **Evidence Base**: Archaeological, linguistic, comparative mythology

### 2. Sharma Agent (Philosophical-Spiritual)
- **Philosophy**: Mystical, inner-meaning interpretation
- **Approach**:
  - Treats Vedic verses as spiritual allegories
  - Deities = Cosmic/psychological principles
  - Battles = Internal spiritual struggles
  - Symbolic focus (fire = illumination, water = consciousness)
- **Evidence Base**: Upanishads, Vedanta, yogic texts

## Debate Protocol

### Phase 1: Thesis & Antithesis
1. User provides verse reference + text
2. Griffith Agent interprets (literal)
3. Sharma Agent responds (philosophical), challenging literal view

### Phase 2: Rebuttals (N rounds)
4. Griffith defends literal interpretation
5. Sharma defends philosophical interpretation
6. Repeat for N rounds

### Phase 3: Synthesis
7. Neutral synthesizer analyzes BOTH views
8. Identifies original Rishi intent (likely dual-layer meaning)
9. Shows how literal + symbolic meanings complement each other

## Example Use Case

**Verse**: RV 1.32 (Indra slays Vritra)

**Griffith's View**:
- Vritra = Drought demon blocking rivers
- Indra = Storm god bringing monsoon
- Historical event: Breaking of natural dam/drought

**Sharma's View**:
- Vritra = Ego/ignorance blocking consciousness
- Indra = Higher self/spiritual power
- Yogic event: Breaking through mental obstacles

**Synthesis**:
- Original intent: BOTH layers valid
- Rishi used historical meteorological event as metaphor for spiritual awakening
- Ancient listeners understood multi-layered meaning
- Literal truth validates symbolic truth

## Architecture

```
User Query (Verse)
    ↓
┌─────────────────────────────────────┐
│   Debate Orchestrator                │
│                                      │
│  ┌──────────────┐  ┌──────────────┐│
│  │ Griffith RAG │  │ Sharma RAG   ││
│  │ (Literal)    │  │ (Spiritual)  ││
│  └───────┬──────┘  └───────┬──────┘│
│          │                 │        │
│          ▼                 ▼        │
│   Llama 3.1:8b      Llama 3.1:8b   │
│   (Literal Mode)    (Mystical Mode)│
│          │                 │        │
│          └────────┬────────┘        │
│                   ▼                 │
│            Synthesis LLM            │
│          (Neutral Analysis)         │
└─────────────────┬───────────────────┘
                  ▼
         Original Rishi Intent
```

## Current Status

✅ **Implemented**:
- Debate orchestrator with thesis-antithesis-synthesis
- Griffith agent with literal interpretation logic
- Sharma agent with philosophical interpretation logic
- Multi-round rebuttal system
- Synthesis generation
- Test script with classic example (Indra vs Vritra)

⏳ **In Progress**:
- Running first full debate test

🔮 **Future Enhancements**:
1. **Separate Sharma Corpus**: Index actual Sharma translations
2. **Branch Switching**: `--griffith` vs `--sharma` vs `--debate` CLI flags
3. **Verse Database**: Pre-indexed verse references for quick lookup
4. **Confidence Scores**: Track which interpretation has stronger textual support
5. **Citation System**: Both agents cite specific passages
6. **Convergence Detection**: Stop debate when agents reach agreement
7. **AMT Integration**: Add genetic/archaeological evidence as third perspective

## Usage

```bash
# Run debate PoC
python test_debate.py

# Future: CLI integration
python src/cli_run.py --debate --verse "RV 1.32"
```

## Key Insight

The Vedic Rishis likely intended **dual-layer meaning**:
- Surface layer: Historical/material events (for common listeners)
- Deep layer: Spiritual/yogic truths (for initiated practitioners)

This debate system helps recover BOTH layers, showing they're complementary, not contradictory.
