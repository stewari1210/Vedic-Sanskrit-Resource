# 🕉️ Vedic Sanskrit Learning Agent

An interactive AI tutor for learning Vedic Sanskrit, designed specifically for learners who:
- Have basic Sanskrit background from school (but may have forgotten most of it)
- Are native Hindi speakers
- Want to read and understand Vedic texts (Rigveda, Yajurveda)

## Features

### 📚 **Grammar Refresher**
- **Sandhi (संधि)**: Euphonic combination rules with examples from Rigveda
- **Vibhakti (विभक्ति)**: Case endings explained with Hindi comparisons
- **Dhatu (धातु)**: Common verb roots with practical usage

### 📖 **Vocabulary Builder**
- Thematic word lists:
  - देवता (Deities): Agni, Indra, Soma, Varuna, etc.
  - यज्ञ (Ritual terms): Offerings, fire, priests
  - प्रकृति (Nature): Rivers, mountains, seasons
  - Common verbs and adjectives
- Hindi translations and context
- Examples from actual Vedic verses

### 🔤 **Verse Translation Practice**
- Beginner-friendly verses (RV 1.1.1, Gayatri Mantra, etc.)
- Word-by-word breakdown
- Grammar analysis
- Cultural and philosophical context
- Hindi and English translations

### 🗣️ **Pronunciation Guide**
- Devanagari ↔ IAST transliteration
- Proper vowel lengths (ā, ī, ū)
- Anusvāra and Visarga rules
- Vedic accent marks (udātta, anudātta)
- Practice with mantras

### 🎯 **Quiz Mode**
- Adaptive difficulty (beginner, intermediate, advanced)
- Multiple choice and fill-in-the-blank
- Immediate feedback with explanations
- Progress tracking

### 💬 **Free Conversation**
- Ask any Sanskrit-related question
- Get personalized explanations
- Explore topics at your own pace

## Installation

Already included in your RAG-CHATBOT-CLI-Version project!

## Usage

### Quick Start

```bash
# Run with Ollama (default, runs locally)
python src/vedic_sanskrit_tutor.py

# Run with Gemini (uses Google's API)
python src/vedic_sanskrit_tutor.py --llm gemini

# Or use the shell script
./run_sanskrit_tutor.sh
```

### First Time Setup

Make sure you have indexed your Vedic texts:

```bash
# Index your Rigveda and Yajurveda texts
python src/cli_run.py --files rigveda-griffith_COMPLETE_english_with_metadata.txt \
                             rigveda-sharma_COMPLETE_english_with_metadata.txt \
                             yajurveda-griffith_COMPLETE_english_with_metadata.txt \
                             yajurveda-sharma_COMPLETE_english_with_metadata.txt

# Or if already indexed, just load:
python src/cli_run.py --no-cleanup-prompt
```

## Example Session

```
🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️
    VEDIC SANSKRIT LEARNING AGENT
    नमस्ते! Welcome to your personalized Sanskrit tutor
🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️ 🕉️

============================================================
LEARNING MODULES
============================================================
1. Grammar Basics (Sandhi, Vibhakti, Dhatu)
2. Vocabulary Building (Common Vedic Words)
3. Verse Translation Practice
4. Pronunciation & Transliteration
5. Quiz Mode (Test Your Knowledge)
6. Free Conversation (Ask Anything)
0. Exit

Choose a module (0-6):
```

## Learning Path Suggestions

### Week 1-2: Foundations
1. Start with **Grammar Basics** - refresh Sandhi rules
2. Practice **Pronunciation** - get comfortable with IAST
3. Build basic **Vocabulary** - deities and ritual terms
4. Try translating **RV 1.1.1** (Agni invocation)

### Week 3-4: Building Skills
1. Deeper **Grammar** - Vibhakti patterns
2. Expand **Vocabulary** - nature words and verbs
3. Translate **Gayatri Mantra** (RV 3.62.10)
4. Take beginner **Quizzes**

### Week 5-6: Advanced Practice
1. Study **Dhatu** (verb roots)
2. Translate longer verses (Purusha Sukta)
3. Take intermediate **Quizzes**
4. Use **Free Conversation** for specific questions

### Ongoing Practice
- Daily: 10 new vocabulary words
- Weekly: Translate 1-2 new verses
- Monthly: Take quiz to assess progress

## Tips for Effective Learning

### 1. **Use Hindi as a Bridge**
Since you're a native Hindi speaker, the tutor will explain Sanskrit concepts using Hindi examples. Many Sanskrit words are similar to Hindi!

Examples:
- अग्नि (agni) → आग (aag)
- जल (jala) → जल (jal)
- वृक्ष (vṛkṣa) → पेड़ (peṛ) - but "वृक्ष" also exists in Hindi

### 2. **Practice Daily**
Even 15-20 minutes daily is better than 2 hours once a week.

### 3. **Start with Familiar Verses**
If you know some mantras (Gayatri, Mahamrityunjaya), start there!

### 4. **Don't Memorize Grammar Rules Blindly**
Learn through examples from actual verses. The tutor will show you Sandhi in action!

### 5. **Use Free Conversation Mode**
Whenever confused, just ask! The AI has access to your entire Vedic corpus.

## Technical Details

### How It Works

1. **RAG-Powered**: Uses your indexed Rigveda/Yajurveda texts as knowledge base
2. **Context-Aware**: Retrieves relevant verses and examples for each lesson
3. **LLM Teaching**: Uses Ollama (llama3.1:8b) or Gemini to provide pedagogical explanations
4. **Personalized**: Adapts explanations based on your background (school Sanskrit + Hindi native)

### Requirements

- Python 3.11+
- LangChain, Qdrant, Sentence Transformers (already installed)
- Ollama with llama3.1:8b model (or Gemini API key)
- Indexed Vedic texts corpus

## Customization

### Change Teaching Style

Edit the system prompts in `vedic_sanskrit_tutor.py` to adjust:
- Difficulty level
- Amount of Hindi vs English explanation
- Focus areas (grammar vs vocabulary)

### Add More Texts

Index additional Sanskrit texts to expand the knowledge base:

```bash
python src/cli_run.py --files your_new_sanskrit_text.txt
```

## Troubleshooting

### "Vector store not found"
Run `cli_run.py` first to index your texts.

### "Ollama connection failed"
Make sure Ollama is running: `ollama serve`

### Slow responses
- Use Gemini instead: `--llm gemini`
- Or reduce `num_predict` in the code

## Future Enhancements

Planned features:
- [ ] Spaced repetition flashcards
- [ ] Progress tracking and statistics
- [ ] Audio pronunciation (TTS for mantras)
- [ ] Devanagari typing practice
- [ ] Writing exercises (compose simple sentences)
- [ ] Streamlit web UI version
- [ ] Mobile app

## Contributing

Have ideas for improving the tutor? Features you'd like to see? Let me know!

## License

Part of RAG-CHATBOT-CLI-Version project.

---

🙏 **धन्यवाद! Happy Learning! शुभम् भवतु।**

For questions or feedback, reach out through the main project repository.
