# Vedic Debate CLI - Separate Agentic System

## Why Separate?

The debate system is kept separate from `cli_run.py` to avoid breaking the standard RAG functionality. This way:
- ✅ Standard RAG queries remain unchanged
- ✅ Debate system can evolve independently
- ✅ Each CLI has focused, specific purpose

---

## Quick Start

### Interactive Mode (Recommended)
```bash
python debate_cli.py
```

Then follow the prompts:
1. Enter verse reference (e.g., `RV 2.33`)
2. Choose auto-retrieval (press Enter)
3. Verify the retrieved texts
4. Specify number of rounds
5. Watch the debate unfold!

### Command-Line Mode
```bash
# Auto-retrieve both translations
python debate_cli.py --verse "RV 2.33" --rounds 2

# With manual text
python debate_cli.py --verse "RV 1.32" --verse-text "Indra slew Vritra..." --rounds 3

# Quiet mode (less logging)
python debate_cli.py --verse "RV 10.129" --quiet
```

---

## What It Does

**Dual-Translation Debates:**
- Griffith Agent gets Griffith's English translation
- Sharma Agent gets Sharma's English translation
- They debate **their own translator's interpretations**
- Synthesis identifies original Rishi intent

**Example: RV 2.33 (Rudra Hymn)**
```bash
python debate_cli.py --verse "RV 2.33" --rounds 2
```

Output:
```
🔵 GRIFFITH'S TRANSLATION:
[02-033] HYMN XXXIII [Maruts, Rudra]
The Maruts, fierce warriors...

🟢 SHARMA'S TRANSLATION:
MANDAL - 2 / SUKTA - 33
The divine forces represented as Maruts...

[Agents debate literal vs spiritual interpretations]

📊 SYNTHESIS:
The Rishi intended both: literal storm deities
AND spiritual forces of transformation...
```

---

## Command Reference

```bash
# Interactive
python debate_cli.py

# Single debate
python debate_cli.py --verse "RV 2.33" --rounds 2

# With manual text
python debate_cli.py --verse "RV 1.32" \
  --verse-text "Your verse here..." \
  --rounds 3

# Quiet mode
python debate_cli.py --verse "RV 10.129" --quiet

# Force rebuild index
python debate_cli.py --force
```

---

## Options

| Argument | Description | Default |
|----------|-------------|---------|
| `--verse` | Verse reference (e.g., RV 2.33) | Interactive mode |
| `--verse-text` | Manual verse text (optional) | Auto-retrieve |
| `--rounds` | Number of debate rounds | 2 |
| `--quiet` | Suppress INFO logs | False |
| `--force` | Rebuild vector store | False |

---

## How Retrieval Works

### Auto-Retrieval Algorithm

1. **Parse verse reference:** `RV 2.33` → Book 2, Hymn 33
2. **Format for Griffith:** `[02-033]` + Roman numerals `HYMN XXXIII`
3. **Format for Sharma:** `MANDAL - 2 / SUKTA - 33`
4. **Search query:** `[02-033] HYMN XXXIII MANDAL 2 SUKTA 33`
5. **Filter results:**
   - Exact pattern match for Griffith `[02-033]`
   - Exact pattern match for Sharma `MANDAL - 2 / SUKTA - 33`
6. **Verify content:** Skip index pages, require 10+ real words
7. **Return:** (griffith_text, sharma_text)

### Why This Works

**Problem:** Generic searches like "RV 2.33" match random pages with "233"

**Solution:** Search with exact document patterns:
- Griffith uses `[02-033] HYMN XXXIII`
- Sharma uses `MANDAL - 2 / SUKTA - 33`
- These are unique identifiers that avoid false matches

---

## Troubleshooting

### "Could not find verse texts"
- Try different verse format: `RV 2.33` vs `RV 2.33.1`
- Use interactive mode and verify retrieved text
- Provide manual `--verse-text` if auto-retrieval fails

### "Wrong hymn retrieved"
- Check the preview - does it mention correct deities?
- For RV 2.33, should mention "Rudra" or "Maruts"
- Answer 'n' to reject and try again

### "Both agents debating same text"
- This means only one translation was found
- System will warn you: "Could only find one translation"
- Both agents will use that translation (still works, just less revealing)

---

## Examples

### Famous Verses

**RV 1.32 (Indra-Vritra)**
```bash
python debate_cli.py --verse "RV 1.32" --rounds 2
```
- Griffith: Literal battle between Indra and serpent Vritra
- Sharma: Inner spiritual struggle, awakening of consciousness

**RV 10.129 (Nasadiya Sukta - Creation Hymn)**
```bash
python debate_cli.py --verse "RV 10.129" --rounds 3
```
- Griffith: Cosmological speculation about universe origin
- Sharma: Meditation on the unknowable absolute reality

**RV 10.90 (Purusha Sukta)**
```bash
python debate_cli.py --verse "RV 10.90" --rounds 2
```
- Griffith: Sacrifice of cosmic man creating social order
- Sharma: Manifestation of universal consciousness

**RV 2.33 (Rudra Hymn)**
```bash
python debate_cli.py --verse "RV 2.33" --rounds 2
```
- Griffith: Storm god Rudra and Marut warriors, tribal warfare
- Sharma: Divine transformative forces, spiritual awakening

---

## Saved Debates

Debates are automatically saved to:
```
debates/debate_RV_2_33_20251230_213000.json
```

View with:
```bash
cat debates/debate_RV_2_33_*.json | jq .
```

---

## Comparison with cli_run.py

| Feature | `cli_run.py` (RAG) | `debate_cli.py` (Agents) |
|---------|-------------------|-------------------------|
| **Purpose** | Standard Q&A retrieval | Dialectical debate synthesis |
| **Agents** | None (direct retrieval) | Griffith + Sharma agents |
| **Output** | Direct answer | Multi-round debate + synthesis |
| **Translations** | Single best match | Both translations separately |
| **Use Case** | Quick lookups | Deep analysis, intent recovery |

---

## Future Enhancements

Potential improvements:
1. Add `--griffith-text` and `--sharma-text` CLI arguments
2. Side-by-side diff display of translation differences
3. Translation quality metrics (word choice analysis)
4. Verse database for 100% reliable retrieval
5. Multi-agent synthesis (add neutral third agent)

---

## Technical Details

**Files:**
- `debate_cli.py` - Main CLI script (this file)
- `src/utils/debate_agents.py` - Agent implementations
- `src/utils/retriever.py` - Hybrid BM25 + semantic search
- `debates/` - Saved debate transcripts (JSON)

**Key Functions:**
- `auto_retrieve_both_translations()` - Find both translations
- `run_interactive_debate()` - Interactive mode with prompts
- `run_single_debate()` - Non-interactive single debate
- `DebateOrchestrator.run_debate()` - Multi-round debate logic

---

## Credits

This system implements a dialectical approach to Vedic interpretation:
- **Thesis:** Griffith's literal/historical reading
- **Antithesis:** Sharma's philosophical/spiritual reading
- **Synthesis:** Convergence on original Rishi intent

By letting each agent debate their own translator's English, we reveal both:
1. How translation choices reflect interpretation
2. How literal and symbolic layers coexist

**Goal:** Recover the multi-layered meaning the Rishis encoded in Sanskrit verses.

---

## Support

For issues or questions:
1. Check if vector store is built: `ls vector_store/ancient_history/`
2. Try `--force` to rebuild index
3. Use `--quiet` to reduce log noise
4. Test with famous verses first (RV 1.32, 10.129, 10.90)

**Happy Debating! May both literal and symbolic truths emerge!** 🎭✨
