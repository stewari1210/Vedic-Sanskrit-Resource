# 🎭 Debate Mode CLI Guide

## Overview
The CLI debate mode enables philosophical debates between two interpretative approaches to Vedic verses:

- **Griffith Agent**: Literal/Historical interpretation (material culture, archaeology, linguistics)
- **Sharma Agent**: Philosophical/Spiritual interpretation (yogic symbolism, Upanishadic wisdom)

## Usage

### 1. Interactive Debate Mode
Start an interactive session where you can run multiple debates:

```bash
python src/cli_run.py --debate --no-cleanup-prompt
```

You'll be prompted for:
- **Verse Reference** (e.g., `RV 1.32`, `YV 40.1`)
- **Verse Text** (press Enter twice when done)
- **Number of Rounds** (default: 2)

Type `exit` or `quit` to stop.

---

### 2. Non-Interactive Single Debate
Run a single debate from the command line:

```bash
python src/cli_run.py --debate --no-cleanup-prompt \
  --verse "RV 1.32" \
  --verse-text "Indra with his own great and deadly thunder smote into pieces Vritra..." \
  --rounds 2 \
  --quiet
```

**Parameters:**
- `--debate`: Enable debate mode
- `--verse VERSE`: Verse reference (e.g., "RV 1.32")
- `--verse-text TEXT`: The verse text to debate
- `--rounds N`: Number of debate rounds (default: 2)
- `--no-cleanup-prompt`: Skip the cleanup prompt
- `--quiet`: Suppress INFO logs (cleaner output)

---

## Output

### Console Output
The debate will print to your terminal in real-time:
1. **Griffith's Interpretation** (literal/historical)
2. **Sharma's Interpretation** (philosophical/spiritual)
3. **Rebuttals** (multiple rounds)
4. **Synthesis** (neutral analysis of original Rishi intent)

### File Output
All debates are automatically saved to:
```
debates/debate_<VERSE>_<TIMESTAMP>.json
```

Example:
```
debates/debate_RV_1_32_20251230_165127.json
```

---

## JSON Structure

```json
{
  "verse_reference": "RV 1.32",
  "verse_text": "Indra with his own great and deadly thunder...",
  "debate_transcript": [
    {
      "round": 1,
      "agent": "Griffith",
      "interpretation": "..."
    },
    {
      "round": 1,
      "agent": "Sharma",
      "interpretation": "..."
    },
    {
      "round": 2,
      "agent": "Griffith",
      "interpretation": "..."
    },
    {
      "round": 2,
      "agent": "Sharma",
      "interpretation": "..."
    }
  ],
  "synthesis": "### Original Intent (Synthesis)\n\nThe Rishi likely intended..."
}
```

---

## Examples

### Example 1: RV 1.32 (Indra vs Vritra)
```bash
python src/cli_run.py --debate --no-cleanup-prompt \
  --verse "RV 1.32" \
  --verse-text "Indra with his own great and deadly thunder smote into pieces Vritra, worst of Vritras. As trunks of trees, what time the axe hath felled them, low on the earth so lies the prostrate Dragon." \
  --rounds 2 \
  --quiet
```

**Result:**
- Griffith: Historical monsoon event, Sintashta culture archaeology
- Sharma: Spiritual ego-transcendence, kundalini awakening
- Synthesis: Dual-layer intent (both literal AND symbolic)

---

### Example 2: RV 10.129 (Nasadiya Sukta - Creation Hymn)
```bash
python src/cli_run.py --debate --no-cleanup-prompt \
  --verse "RV 10.129" \
  --verse-text "Then even nothingness was not, nor existence. There was no air then, nor the heavens beyond it..." \
  --rounds 3 \
  --quiet
```

**Result:**
- Griffith: Proto-philosophical cosmology, cultural context
- Sharma: Metaphysical inquiry, Brahman/Atman unity
- Synthesis: Original Rishi exploring both empirical and transcendent questions

---

## Tips

1. **Use `--quiet` flag** for cleaner output (only shows debate, not INFO logs)
2. **Start with 2 rounds** (initial + rebuttal) - increase for deeper analysis
3. **Interactive mode** is best for exploring multiple verses in one session
4. **Non-interactive mode** is best for automation/scripting
5. **Check `debates/` folder** for saved transcripts after each debate

---

## Troubleshooting

### "Vector store not found"
Make sure you've already indexed your Griffith translations:
```bash
python src/cli_run.py --files rigveda-griffith.pdf yajurveda-griffith.pdf
```

### "File not found: sample.pdf"
Use `--no-cleanup-prompt` flag to skip file processing if vector store exists.

### LLM not responding
Check that Ollama is running:
```bash
ollama list  # Should show llama3.1:8b
```

---

## Next Steps

- Add Sharma corpus to enable dual-retrieval debates
- Implement debate comparison (side-by-side multiple verses)
- Add export to markdown format
- Create debate analytics (track interpretation patterns)
