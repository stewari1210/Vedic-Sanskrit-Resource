# 🎭 Debate System - Usage Guide

## ✨ NEW: Dual-Translation Debates

**The system now auto-retrieves BOTH translations!**

Each agent debates their own translator's version:
- **Griffith Agent** → Griffith's English translation
- **Sharma Agent** → Sharma's English translation

This means they're debating **different English texts** of the same Sanskrit verse, making debates more authentic and revealing translation differences!

---

## 🚀 Quick Start

### Interactive Mode (Recommended)

```bash
python src/cli_run.py --debate --no-cleanup-prompt
```

When prompted:
1. Enter verse reference: `RV 10.85.12`
2. Choose option 1 (auto-retrieve both translations)
3. Verify the retrieved texts
4. Watch agents debate their respective translations!

### Command-Line Mode

```bash
python src/cli_run.py --debate --no-cleanup-prompt \
  --verse "RV 1.32.1" \
  --rounds 3
```

The system will automatically:
- Find Griffith's translation
- Find Sharma's translation
- Give each agent their own translator's text
- Run the debate with synthesis

---

## 📊 How It Works

### Old Way (Single Text) ❌
```
User provides ONE English text
  ↓
Both agents analyze SAME text
  ↓
They debate the SAME words with different philosophies
```

**Problem:** Griffith and Sharma have different English translations of the same Sanskrit. Both agents debating one translation doesn't reveal translation differences.

### New Way (Dual Translations) ✅
```
System auto-retrieves TWO translations
  ↓
Griffith Agent → Griffith's English translation
Sharma Agent → Sharma's English translation
  ↓
They debate DIFFERENT texts reflecting different interpretation choices
```

**Benefit:** Agents debate how the same Sanskrit was translated differently, revealing both philosophical AND linguistic interpretation choices!

---

## 🎯 Example: RV 10.85.12 (Three-Wheeled Chariot)

### Command:
```bash
python src/cli_run.py --debate --verse "RV 10.85.12" --rounds 2 --no-cleanup-prompt
```

### What Happens:

**1. System retrieves both translations**
```
🔍 Auto-retrieving translations for RV 10.85.12...
✓ Found Griffith: The Sun's wide-wheeled chariot rolls...
✓ Found Sharma: The solar vehicle with three wheels...
```

**2. Debate displays both**
```
📖 VERSE: RV 10.85.12
================================================================================

🔵 GRIFFITH'S TRANSLATION:
The Sun's wide-wheeled chariot rolls on three wheels...

🟢 SHARMA'S TRANSLATION:
The solar vehicle with three wheels represents...
```

**3. Each agent analyzes their own version**
- **Griffith Agent**: "The three wheels refer to actual chariot design... archaeological evidence from Sintashta..."
- **Sharma Agent**: "The three wheels symbolize three gunas (sattva, rajas, tamas)... inner journey..."

**4. Synthesis considers both translations**
> "The Rishi likely intended both meanings: a literal wedding chariot with symbolic cosmic significance. The translation differences reveal how Griffith emphasized materiality while Sharma emphasized spirituality..."

---

## 🔍 When Auto-Retrieval Works Best

✅ **Works well for:**
- Mandala 1-7 verses (better indexed)
- Famous hymns (RV 10.129, RV 10.90, RV 1.32)
- Verses with distinctive keywords
- Complete suktas (hymns) rather than single verses

⚠️ **May struggle with:**
- Very short verse fragments
- Verses from introductions/appendices
- Index pages or metadata (filtered but not perfect)
- Mandala 10 (mixed content)

---

## �️ Interactive Mode Options

When you run `python src/cli_run.py --debate`, you'll see:

```
Verse Text Options:
  1) Press Enter to AUTO-RETRIEVE both translations (Griffith + Sharma)
  2) Type 'manual' to provide your own text
  3) Paste verse text now (both agents will use same text)

Your choice:
```

### Option 1: Auto-Retrieve (Recommended)
- System finds both Griffith and Sharma translations
- Shows you previews to confirm
- Each agent gets their own translation
- **Best for exploring translation differences**

### Option 2: Manual Input
- You paste one English text
- Both agents analyze the same text
- Useful if you want to test a specific translation
- **Best for focused philosophical debate on known text**

### Option 3: Quick Paste
- Paste text immediately
- Both agents use same text
- Fastest option

---

## 🎓 Advanced: Manual Text for Both Agents

If auto-retrieval fails or you want to provide specific texts, you can modify the code to accept both:

```python
# In interactive mode, extend the CLI to accept:
# --griffith-text "..." --sharma-text "..."
```

*Note: This feature is not yet implemented in CLI args but available in the API*

---

## 💡 Pro Tips

1. **Start with famous verses** to test the system:
   - `RV 1.32` (Indra-Vritra battle)
   - `RV 10.129` (Nasadiya Sukta - Creation Hymn)
   - `RV 10.90` (Purusha Sukta)
   - `RV 10.85` (Wedding Hymn)

2. **Use 2-3 rounds** for depth:
   ```bash
   --rounds 3
   ```

3. **Quiet mode** for cleaner output:
   ```bash
   --quiet
   ```

4. **Check saved debates**:
   ```bash
   ls -lt debates/
   cat debates/debate_RV_10_85_*.json | jq .
   ```

5. **Compare translations side-by-side** by reading the debate JSON:
   ```bash
   cat debates/latest_debate.json | jq '.verse_text'
   ```

---

## 📋 Command Reference

### Basic Debate
```bash
python src/cli_run.py --debate --verse "RV 1.32.1" --rounds 2
```

### With Specific Text (Old Way)
```bash
python src/cli_run.py --debate \
  --verse "RV 10.85" \
  --verse-text "Three-wheeled chariot of the Sun..." \
  --rounds 2
```

### Interactive Mode
```bash
python src/cli_run.py --debate --no-cleanup-prompt
```

### Quiet Mode
```bash
python src/cli_run.py --debate --verse "RV 1.32" --quiet --no-cleanup-prompt
```

---

## 🚨 Troubleshooting

### "Could not find verse texts"
- Try a different verse reference format: `RV 1.32` vs `RV 1.32.1`
- Use interactive mode and manually paste text
- Check if verse is actually indexed: `grep "1.32" local_store/ancient_history/*/metadata.json`

### "Both agents debating same text"
- This happens if only one translation is found
- System will warn you: `⚠️  Could only find one translation`
- You can proceed or provide manual text

### "Retrieved text looks wrong"
- System shows previews - verify before confirming
- Answer `n` to reject and try again
- Use manual input if auto-retrieval is unreliable

### "Translations are identical"
- Rare but possible for very literal verses
- Check the actual text - might be index/header
- Try a different verse reference

---

## � Best Results Formula

```bash
# 1. Use auto-retrieval for dual translations
python src/cli_run.py --debate --no-cleanup-prompt

# 2. Choose famous verses first
Verse Reference: RV 10.129.1

# 3. Select option 1 (auto-retrieve)
Your choice: 1

# 4. Verify translations look correct
Continue with these texts? (y/n): y

# 5. Use 2-3 rounds for depth
Number of debate rounds: 2

# Result: High-quality debate with translation-specific insights! 🎯
```

---

## 🎯 Why This Matters

**Old approach:** Both agents debated the same English text, arguing only about *philosophical interpretation*

**New approach:** Each agent debates their own translator's English, revealing:
- How translation choices reflect interpretation
- Where translations emphasize different aspects (literal vs symbolic)
- How the same Sanskrit can validly be translated multiple ways
- Why debates between Griffith and Sharma go beyond just philosophy

**Example:**
- Griffith: "The storm-god Indra with his thunderbolt..."
- Sharma: "The Divine Power manifest as Indra consciousness..."

These are **different English words** from the **same Sanskrit**! The debate now reveals:
1. **Translation differences** (storm-god vs Divine Power)
2. **Philosophical differences** (literal deity vs abstract consciousness)
3. **Original intent synthesis** (What did the Rishi mean? Both layers!)

---

## 🎭 Conclusion

The dual-translation system makes debates **more authentic** and **more insightful** by letting each agent work with their own translator's interpretation. This better simulates the real scholarly debate between literal and philosophical approaches to Vedic translation.

**Happy Debating! May the light burst forth!** ✨
