# 🕉️ Vedic Sanskrit Tutor - Streamlit Web Interface

A beautiful, interactive web interface for learning Vedic Sanskrit with proper **Devanagari font rendering** and AI-powered guidance.

## ✨ Features

### 📖 **Proper Devanagari Display**
- Uses Google's Noto Serif Devanagari font for beautiful rendering
- Large, clear Sanskrit text display
- Proper line spacing for complex characters
- Supports both Devanagari input and display

### 🎓 **Six Learning Modules**

1. **📖 Grammar Basics (व्याकरण)**
   - Sandhi rules with examples
   - Vibhakti (case endings) tables
   - Dhatu (verb roots) conjugations
   - Interactive lessons in Devanagari

2. **📚 Vocabulary Builder (शब्दकोश)**
   - Themed word lists (देवता, यज्ञ, प्रकृति)
   - Devanagari + IAST + Hindi meanings
   - Examples from actual Vedic verses
   - Progress tracking

3. **🔤 Verse Translation (अनुवाद)**
   - Practice with famous verses (RV 1.1.1, Gayatri)
   - Step-by-step translation guide
   - Word-by-word breakdown
   - Sandhi analysis
   - Cultural context

4. **🗣️ Pronunciation (उच्चारण)**
   - Devanagari ↔ IAST conversion
   - Pronunciation guides
   - Vowel length teaching
   - Tips for Hindi speakers
   - Practice with common words

5. **🎯 Quiz Mode (परीक्षा)**
   - Interactive multiple-choice questions
   - Adaptive difficulty (Beginner/Intermediate/Advanced)
   - Detailed answer explanations
   - Score tracking
   - Progress visualization

6. **💬 Free Chat (बातचीत)**
   - Ask anything about Sanskrit
   - Type in English, Hindi, or Devanagari
   - AI-powered responses with RAG
   - Chat history maintained
   - Context-aware conversations

### 🎨 **Beautiful UI/UX**
- Clean, modern interface
- Color-coded sections
- Responsive layout
- Progress tracking dashboard
- Quick reference sidebar
- Mobile-friendly design

### 🧠 **Smart RAG Integration**
- Searches 18,215+ chunks from Rigveda & Yajurveda
- Hybrid retrieval (BM25 + semantic)
- Context-aware teaching
- Examples from actual Vedic corpus

### ⚙️ **Flexible Model Support**
- **Ollama**: llama3.1:8b, phi3.5:mini, phi3:mini, llama3.2:3b, etc.
- **Gemini**: Google's Gemini model
- Easy model switching via UI
- Recommendations for fast models

## 🚀 Quick Start

### 1. Install Dependencies

Make sure you have Streamlit installed:
```bash
conda activate rag-py311
pip install streamlit
```

### 2. Launch the Web Interface

**Easy way (recommended):**
```bash
./run_sanskrit_tutor_web.sh
```

**Or manually:**
```bash
conda activate rag-py311
streamlit run src/sanskrit_tutor_frontend.py --server.port 8502
```

### 3. Initialize the Tutor

1. Open your browser to: `http://localhost:8502`
2. In the **sidebar**, choose your LLM provider and model
3. Click **🚀 Initialize Tutor**
4. Wait for corpus to load (~18,215 chunks)
5. Start learning! 📚

## 📚 Usage Guide

### Getting Started

1. **Home Page** - Overview and introduction
2. **Settings (Sidebar)** - Choose model and initialize
3. **Choose Module** - Select from 6 learning modes
4. **Start Learning!** - Interactive lessons begin

### Learning Path (Recommended)

**Week 1: Foundation**
- Start with **Grammar Basics** → Sandhi rules
- Practice **Pronunciation** → Common words (अग्नि, इन्द्र, etc.)
- Build **Vocabulary** → Deities (देवता)

**Week 2: Building Skills**
- **Grammar** → Vibhakti (case endings)
- **Vocabulary** → Ritual terms (यज्ञ)
- **Translation** → Try RV 1.1.1 (Agni hymn)

**Week 3: Practice**
- **Grammar** → Dhatu (verb roots)
- **Translation** → Gayatri Mantra (RV 3.62.10)
- **Quiz Mode** → Test your knowledge

**Week 4+: Mastery**
- **Free Chat** → Ask specific questions
- **Translation** → Custom verses
- **Quiz** → Advanced level

### Tips for Effective Learning

**✅ DO:**
- Initialize tutor once at the start
- Try all modules to find your preference
- Type in Devanagari if your keyboard supports it
- Use Hindi explanations if you're a native speaker
- Take quizzes to test understanding
- Revisit grammar when translating is hard

**❌ DON'T:**
- Skip pronunciation - it's foundational!
- Rush through translations - take it slow
- Avoid grammar - it's essential
- Ignore the quiz scores - they track progress

## ⚡ Model Recommendations

### For Speed (phi3.5:mini) ⚡
```
Best balance of speed and quality
~60 tokens/sec
Perfect for interactive learning
```

### For Quality (llama3.1:8b) 🎯
```
Most detailed explanations
~25 tokens/sec
Better for complex translations
```

### For Very Fast Responses (llama3.2:3b) 🚀
```
Very quick responses
~70 tokens/sec
Good for quick lookups
```

See `FAST_MODELS_GUIDE.md` for detailed comparisons!

## 🎨 Devanagari Display Features

### Font Rendering
- **Primary Font**: Noto Serif Devanagari (Google Fonts)
- **Size**: Large, readable text (1.5-2em)
- **Color**: Warm brown (#8B4513) for authenticity
- **Line Height**: 1.8-2.0 for complex characters

### Input Support
The web interface accepts:
- ✅ English questions
- ✅ Hindi questions
- ✅ Devanagari input (if your OS keyboard supports it)
- ✅ IAST transliteration

### Display Formats
- Verses shown in **Devanagari first**
- IAST transliteration below
- Hindi meanings when relevant
- Color-coded sections for clarity

## 🔧 Technical Details

### Architecture
```
User Input → Streamlit UI
    ↓
RAG Query → LangGraph Workflow
    ↓
Hybrid Retrieval (BM25 + Qdrant)
    ↓
Context from 18,215 Vedic chunks
    ↓
LLM Enhancement (Ollama/Gemini)
    ↓
Formatted Response with Devanagari
```

### Session State
- Chat history (last 10 messages)
- Learned words tracking
- Quiz scores
- Current module
- Initialized status

### Ports
- **Sanskrit Tutor Web**: `localhost:8502`
- **Main RAG Frontend**: `localhost:8501` (if running)

## 🆚 Web vs CLI Comparison

| Feature | Web Interface | CLI Version |
|---------|--------------|-------------|
| **Devanagari Display** | ✅ Beautiful fonts | ⚠️ Terminal dependent |
| **Input Method** | ✅ Type/paste easily | ⚠️ Encoding issues |
| **Navigation** | ✅ Point & click | ⌨️ Text menus |
| **Progress Tracking** | ✅ Visual dashboard | ❌ None |
| **Quiz Mode** | ✅ Interactive | ⚠️ Basic |
| **Chat History** | ✅ Scrollable | ⚠️ Limited |
| **Model Selection** | ✅ UI dropdown | 🎛️ Command flag |
| **Accessibility** | ✅ Very easy | 🤓 For developers |

**Recommendation**: Use **Web Interface** for learning, CLI for automation/scripting.

## 🐛 Troubleshooting

### "Module not found" errors
```bash
# Make sure Streamlit is installed
pip install streamlit

# Check all dependencies
pip install -r requirements.txt
```

### Devanagari not displaying correctly
- Make sure you're using a modern browser (Chrome, Firefox, Safari)
- Check if Noto fonts loaded (inspect browser console)
- Try refreshing the page

### "Corpus not loading"
```bash
# Check if vector store exists
ls -la vector_store/

# Recreate if needed (via main frontend or CLI)
python src/cli_run.py
```

### Port already in use
```bash
# Use a different port
streamlit run src/sanskrit_tutor_frontend.py --server.port 8503
```

### Slow responses
- Try a smaller/faster model (phi3.5:mini, llama3.2:3b)
- See `FAST_MODELS_GUIDE.md` for optimization tips
- Check if other resource-heavy apps are running

## 📖 Additional Resources

- **CLI Version**: `src/vedic_sanskrit_tutor.py` - Command-line interface
- **Model Guide**: `FAST_MODELS_GUIDE.md` - Choose the right model
- **Main RAG Frontend**: `src/frontend.py` - Document Q&A interface

## 🎯 Learning Goals

By completing all modules, you will be able to:
- ✅ Read Devanagari script fluently
- ✅ Recognize common Vedic vocabulary (100+ words)
- ✅ Apply Sandhi rules to split compounds
- ✅ Identify case endings (Vibhakti)
- ✅ Translate simple Vedic verses with guidance
- ✅ Pronounce mantras correctly
- ✅ Understand cultural/philosophical context

## 🙏 Learning Mindset

> "अभ्यासेन तु कौन्तेय वैराग्येण च गृह्यते"
> *Through practice (abhyāsa) and detachment, it is grasped*
>
> — Bhagavad Gita 6.35

**Key Principles:**
- **Daily Practice** - Even 15 minutes helps
- **Patience** - Sanskrit takes time to master
- **Curiosity** - Ask questions freely
- **Repetition** - Review vocabulary regularly
- **Context** - Understand the culture behind the language

## 🤝 Contributing

Ideas for improvements:
- [ ] Audio pronunciation (TTS for mantras)
- [ ] Spaced repetition flashcards
- [ ] Saved progress across sessions
- [ ] Devanagari typing practice
- [ ] More quiz question types
- [ ] Export study notes as PDF
- [ ] Dark mode theme

## 📝 License

Same as main RAG-CHATBOT-CLI-Version project.

---

**नमस्ते! Happy Learning! 🕉️**

*Built with ❤️ for Sanskrit learners everywhere*
