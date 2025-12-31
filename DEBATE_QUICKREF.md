# 🎭 Debate Mode - Quick Reference

## Command Formats

### Interactive Mode (Multiple Debates)
```bash
python src/cli_run.py --debate --no-cleanup-prompt
```

### Single Debate (Non-Interactive)
```bash
python src/cli_run.py --debate --no-cleanup-prompt \
  --verse "RV 1.32" \
  --verse-text "Full verse text here..." \
  --rounds 2 \
  --quiet
```

---

## Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `--debate` | Enable debate mode | Required |
| `--verse` | Verse reference | `"RV 1.32"`, `"YV 40.1"` |
| `--verse-text` | Full verse text | `"Indra with his own..."` |
| `--rounds` | Number of rounds | `2` (default), `3`, `4` |
| `--no-cleanup-prompt` | Skip cleanup prompt | Recommended |
| `--quiet` | Suppress INFO logs | Cleaner output |

---

## Debate Flow

1. **Griffith's Interpretation** (Literal/Historical)
2. **Sharma's Interpretation** (Philosophical/Spiritual)
3. **Round 2+ Rebuttals** (Both agents respond to each other)
4. **Synthesis** (Neutral analysis of original Rishi intent)

---

## Output Files

**Location:** `debates/debate_<VERSE>_<TIMESTAMP>.json`

**Example:** `debates/debate_RV_1_32_20251230_165127.json`

**Contents:**
- Verse reference & text
- Complete debate transcript (all rounds)
- Synthesis analysis

---

## Common Verses

```bash
# Indra vs Vritra (RV 1.32)
--verse "RV 1.32" --verse-text "Indra with his own great and deadly thunder smote into pieces Vritra..."

# Creation Hymn (RV 10.129)
--verse "RV 10.129" --verse-text "Then even nothingness was not, nor existence..."

# Purusha Sukta (RV 10.90)
--verse "RV 10.90" --verse-text "The Purusha has a thousand heads, a thousand eyes..."
```

---

## Quick Tips

✅ Use `--quiet` for cleaner output
✅ Start with 2 rounds (add more for deeper analysis)
✅ Check `debates/` folder for saved files
✅ Interactive mode best for exploring multiple verses
✅ Non-interactive mode best for scripting/automation

---

## Help
```bash
python src/cli_run.py --help
```

---

## Documentation

- **Full Guide:** `DEBATE_CLI_GUIDE.md`
- **Implementation:** `CLI_DEBATE_SUMMARY.md`
- **Architecture:** `DEBATE_SYSTEM_README.md`
