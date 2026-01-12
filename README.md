# 🕉️ Vedic Sanskrit Tutor

## Overview

An AI-powered learning platform for studying Vedic Sanskrit with interactive features including grammar lessons, vocabulary building, verse translation, pronunciation guides with audio, and intelligent conversation powered by RAG (Retrieval-Augmented Generation).

Built on top of a sophisticated RAG architecture using Langchain and LangGraph, this tutor provides contextual answers from the Rigveda and Yajurveda corpus, making ancient Sanskrit texts accessible to modern learners.

**Perfect for:**
- 📖 Students who studied Sanskrit in school but need a refresher
- 🇮🇳 Native Hindi speakers wanting to understand Vedic texts
- 📜 Anyone interested in reading the Rigveda and Yajurveda
- 🎓 Self-learners exploring ancient Indian literature

## ✨ Key Features

### 🎯 Learning Modules
-   **📚 Grammar Basics** - Master Sandhi rules, Vibhakti (case endings), and Dhatu (verb roots)
-   **📖 Vocabulary Builder** - Learn themed word lists (Deities, Rituals, Nature, Verbs)
-   **🔤 Verse Translation** - Practice with authentic Rigveda verses (RV 1.1.1, Gayatri Mantra, etc.)
-   **🗣️ Pronunciation Guide** - Hear correct pronunciation with Google Text-to-Speech
-   **🎯 Interactive Quizzes** - Test your knowledge with adaptive difficulty
-   **💬 Free Conversation** - Ask any Sanskrit question and get RAG-powered answers

### 🚀 Technical Features
-   **Dual Interface:** Beautiful Streamlit web app + command-line tool
-   **Audio Pronunciation:** Native Devanagari text-to-speech using gTTS
-   **RAG-Powered Answers:** Retrieves relevant context from Rigveda & Yajurveda corpus
-   **Hybrid Search:** Combines BM25 keyword search with semantic vector search
-   **Local LLMs:** Supports Ollama (llama3.1:8b, phi3.5:mini, qwen2.5:32b)
-   **Beautiful Typography:** Proper Devanagari font rendering (Noto Serif/Sans Devanagari)
-   **Smart Lock Management:** Automatic cleanup of Qdrant database locks
-   **Chat History:** Maintains context across conversation turns
-   **⚡ Multi-GPU Parallelization:** Optimized for 10-core/10-GPU systems (see [PARALLELIZATION.md](PARALLELIZATION.md))
    -   **4 GPUs** for QA model (llama3.1:8b)
    -   **6 GPUs** for evaluation model (qwen2.5:32b)
    -   **Parallel retrieval** (semantic + keyword simultaneously)
    -   **Batch embeddings** (32 documents at once on GPU)
    -   **~3x faster** than single-GPU setup (~11s → ~3.5s per query)

## 📁 Project Structure

```
RAG-CHATBOT-CLI-Version/
├── src/
│   ├── vedic_sanskrit_tutor.py      # CLI version of the tutor
│   ├── sanskrit_tutor_frontend.py   # Streamlit web interface
│   ├── cli_run.py                   # Original RAG CLI
│   ├── helper.py                    # Logging and project paths
│   ├── config.py                    # Configuration settings
│   ├── settings.py                  # LLM and embeddings config
│   └── utils/
│       ├── file_ops.py              # File operations
│       ├── index_files.py           # Document loading and vector store
│       ├── process_files.py         # PDF processing
│       ├── final_block_rag.py       # LangGraph RAG pipeline
│       ├── retriever.py             # Hybrid retriever (BM25 + semantic)
│       ├── vector_store.py          # Qdrant vector store management
│       └── prompts.py               # LLM prompt templates
├── local_store/
│   └── ancient_history/             # Rigveda & Yajurveda corpus
│       ├── rigveda-griffith_COMPLETE_english_with_metadata/
│       ├── rigveda-sharma_COMPLETE_english_with_metadata/
│       ├── yajurveda-griffith_COMPLETE_english_with_metadata/
│       └── yajurveda-sharma_COMPLETE_english_with_metadata/
├── vector_store/                    # Qdrant vector database
├── run_sanskrit_tutor.sh            # Launch CLI tutor
├── run_sanskrit_tutor_web.sh        # Launch Streamlit app
├── test_tts.py                      # Audio pronunciation test
├── SANSKRIT_TUTOR_README.md         # CLI documentation
├── SANSKRIT_TUTOR_WEB_README.md     # Web interface guide
├── AUDIO_PRONUNCIATION_GUIDE.md     # TTS feature docs
└── FAST_MODELS_GUIDE.md             # Model comparison
```

## 🎓 Core Modules

### Sanskrit Tutor Applications

-   **`vedic_sanskrit_tutor.py`**: Command-line Sanskrit learning tool with interactive REPL. Choose from 6 learning modes (grammar, vocabulary, translation, pronunciation, quiz, conversation) and get RAG-powered answers from the Vedic corpus.

-   **`sanskrit_tutor_frontend.py`**: Beautiful Streamlit web interface with proper Devanagari fonts, audio pronunciation, and interactive learning modules. Features automatic Qdrant lock cleanup and session state management.

### RAG Pipeline Components

-   **`final_block_rag.py`**: Orchestrates the LangGraph RAG pipeline with multi-step flow:
    1. Check if query is follow-up question
    2. Correct grammar if needed
    3. Retrieve and rerank documents
    4. Generate answer with LLM
    5. Evaluate confidence score
    6. Iterate or complete based on confidence

-   **`retriever.py`**: Implements hybrid retrieval combining:
    - BM25 keyword search (30% weight)
    - Semantic vector search via Qdrant (70% weight)
    - Proper noun expansion for Sanskrit names
    - Returns top-k merged results

-   **`index_files.py`**: Loads markdown documents with metadata from `local_store/`, creates Qdrant vector store with sentence-transformers embeddings (all-mpnet-base-v2).

### Utility Components

-   **`helper.py`**: Initializes structured logging and defines project paths.

-   **`config.py`**: Configuration constants for folders, collections, and vector database.

-   **`settings.py`**: Manages LLM providers (Ollama/Groq/Gemini), embeddings models, and evaluation LLM configuration.

-   **`prompts.py`**: Pedagogical prompt templates optimized for Sanskrit teaching with Hindi explanations.

## 🚀 Quick Start

### Prerequisites

-   Python 3.11+
-   Ollama (for local LLMs)
-   Conda or virtual environment manager

### 1. Clone and Install

```bash
git clone https://github.com/stewari1210/Vedic-Sanskrit-Tutor.git
cd Vedic-Sanskrit-Tutor

# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

### 2. Install Ollama Models

```bash
# Install required models
ollama pull llama3.1:8b          # Main QA model
ollama pull qwen2.5:32b          # Evaluation model
ollama pull phi3.5:mini          # Fast alternative

# Verify installation
ollama list
```

### 3. Configure Environment

Create a `.env` file (or copy from `env.template`):

```bash
# LLM Configuration
LLM_PROVIDER=ollama              # Options: ollama, gemini, groq
OLLAMA_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://localhost:11434

# Evaluation LLM
EVAL_LLM_PROVIDER=ollama         # Recommended: unlimited local evaluation
OLLAMA_EVAL_MODEL=qwen2.5:32b

# Embeddings
EMBEDDING_PROVIDER=local         # Uses sentence-transformers/all-mpnet-base-v2
RATE_LIMIT_EMBEDDINGS=50         # Requests per minute

# Optional: API Keys (if using cloud providers)
# GEMINI_API_KEY=your_key_here
# GROQ_API_KEY=your_key_here
```

### 4. Launch the Tutor

**Option A: Streamlit Web Interface (Recommended)**
```bash
./run_sanskrit_tutor_web.sh
# Opens at http://localhost:8502
```

**Option B: Command-Line Interface**
```bash
./run_sanskrit_tutor.sh
# Or directly:
python src/vedic_sanskrit_tutor.py
```

## 📚 Usage Guide

### Web Interface (Streamlit)

1. **Initialize the Tutor**
   - Select LLM model from sidebar (llama3.1:8b recommended)
   - Click "Initialize Tutor" button
   - Wait for vector store to load

2. **Choose Learning Module**
   - 📖 Grammar Basics - Select topic (Sandhi/Vibhakti/Dhatu)
   - 📚 Vocabulary - Choose theme (Deities/Rituals/Nature)
   - 🔤 Translation - Practice with Rigveda verses
   - 🗣️ Pronunciation - Type word, hear audio
   - 🎯 Quiz - Test knowledge with adaptive questions
   - 💬 Free Chat - Ask any Sanskrit question

3. **Features**
   - Click 🔊 to hear pronunciations
   - View chat history in conversation
   - Switch models anytime from sidebar
   - Clean database locks with sidebar button

### Command-Line Interface

```bash
python src/vedic_sanskrit_tutor.py

# Choose mode:
# 1 = Grammar Basics
# 2 = Vocabulary Building
# 3 = Verse Translation
# 4 = Pronunciation Guide
# 5 = Quiz Mode
# 6 = Free Conversation
# 7 = Exit

# Type your questions and get RAG-powered answers
# Type 'quit' or 'exit' to return to menu
```

## 🎯 Example Interactions

**Grammar Query:**
```
You: Teach me Sandhi rules with examples from Rigveda
Tutor: [Retrieves relevant verses and explains vowel/consonant Sandhi with Devanagari examples]
```

**Vocabulary:**
```
You: What are the Sanskrit names for major Vedic deities?
Tutor: [Lists Agni, Indra, Varuna, etc. with meanings from corpus]
```

**Translation:**
```
You: Translate अग्निमीळे पुरोहितं
Tutor: [Provides word-by-word analysis and full translation from RV 1.1.1]
```

**Pronunciation:**
```
You: How do I pronounce यज्ञ?
Tutor: [Generates audio via gTTS, provides IAST transliteration: yajña]
```

## ⚙️ Configuration Options

### LLM Providers

**Ollama (Recommended - Unlimited Local)**
```bash
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.1:8b        # Or phi3.5:mini for speed
OLLAMA_BASE_URL=http://localhost:11434
```

**Groq (Fast Cloud - Rate Limited)**
```bash
LLM_PROVIDER=groq
GROQ_API_KEY=your_key
GROQ_MODEL=llama-3.3-70b-versatile
```

**Gemini (Google - API Key Required)**
```bash
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-2.0-flash-exp
```

### Embeddings Models

**Local (Recommended)**
```bash
EMBEDDING_PROVIDER=local
# Uses: sentence-transformers/all-mpnet-base-v2
```

**Gemini (Cloud)**
```bash
EMBEDDING_PROVIDER=gemini
GEMINI_EMBED_MODEL=text-embedding-004
```

## 🔧 Troubleshooting

### Qdrant Lock Error
```
RuntimeError: Storage folder vector_store is already accessed by another instance
```

**Solution:** The web interface now auto-cleans locks! Or manually:
```bash
find vector_store -name ".qdrant-lock" -delete
```

### Audio Not Playing
- Ensure `gTTS` is installed: `pip install gtts`
- Check internet connection (gTTS uses Google servers)
- Try refreshing browser page

### LLM Model Not Found
```bash
# Pull missing model
ollama pull llama3.1:8b

# Verify it's available
ollama list
```

### Rate Limit Error (Groq)
```
Rate limit reached: 100,000 tokens per day
```

**Solution:** Switch to Ollama in `.env`:
```bash
EVAL_LLM_PROVIDER=ollama
OLLAMA_EVAL_MODEL=qwen2.5:32b
```

## 📖 Documentation Files

- **`SANSKRIT_TUTOR_WEB_README.md`** - Complete web interface guide
- **`SANSKRIT_TUTOR_README.md`** - CLI usage instructions
- **`AUDIO_PRONUNCIATION_GUIDE.md`** - TTS feature documentation
- **`FAST_MODELS_GUIDE.md`** - Model performance comparison

## 🛣️ Roadmap & Known Limitations

### Current Corpus Limitation

The tutor is trained on **poetic/liturgical texts** (Rigveda & Yajurveda), which are excellent for:
- ✅ Reading and understanding Vedic hymns
- ✅ Learning ritual vocabulary
- ✅ Poetic verse translation

But struggle with:
- ❌ Conversational Sanskrit ("I want milk")
- ❌ Everyday sentence construction
- ❌ Modern Sanskrit prose

### Planned Improvements

**Phase 1: Grammar Foundation (Priority)**
- [ ] Add Macdonell's Vedic Grammar for Students
- [ ] Add Macdonell's Vedic Reader (30 analyzed hymns)
- [ ] Add Whitney's Sanskrit Grammar

**Phase 2: Prose Texts**
- [ ] Add Shatapatha Brahmana (narrative prose)
- [ ] Add Aitareya Brahmana (subject-object-verb structures)

**Phase 3: Dictionaries**
- [ ] Monier-Williams Sanskrit-English Dictionary
- [ ] Grassmann's Wörterbuch zum Rig-veda

**Phase 4: Features**
- [ ] Spaced repetition flashcards
- [ ] Progress tracking across sessions
- [ ] Export chat history as PDF
- [ ] Dark mode theme
- [ ] Devanagari typing practice

## 🤝 Contributing

Contributions welcome! Priority areas:
1. Adding pedagogical grammar texts to corpus
2. Improving conversational Sanskrit handling
3. Adding more interactive quizzes
4. UI/UX improvements for web interface

## 📜 License

MIT License - See LICENSE file

## 🙏 Acknowledgments

- **RAG Architecture**: Based on Langchain and LangGraph frameworks
- **Corpus**: Griffith and Sharma translations of Rigveda & Yajurveda
- **Fonts**: Google Noto Devanagari fonts
- **TTS**: Google Text-to-Speech (gTTS)
- **LLMs**: Meta (Llama), Alibaba (Qwen), Microsoft (Phi)

## 📧 Contact

For questions or feedback:
- GitHub Issues: [Vedic-Sanskrit-Tutor/issues](https://github.com/stewari1210/Vedic-Sanskrit-Tutor/issues)
- Repository: [github.com/stewari1210/Vedic-Sanskrit-Tutor](https://github.com/stewari1210/Vedic-Sanskrit-Tutor)

---

**स्वाध्यायान्मा प्रमदः** *(Never neglect your study)*
— Taittiriya Upanishad
