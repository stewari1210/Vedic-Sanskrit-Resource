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
-   **💬 Free Conversation** - Ask any Sanskrit question and get intelligent, context-aware answers

### 🌍 Bilingual Support (NEW!)
-   **🔤 Multilingual Embeddings:** Supports Hindi, Sanskrit, Devanagari, and English queries
    -   Model: `paraphrase-multilingual-mpnet-base-v2` (768-dim)
    -   Native understanding of Devanagari script (no transliteration needed for search)
    -   Cross-lingual retrieval: Query in Hindi → get Sanskrit results
-   **📖 Monier-Williams Integration:** 176,146 Sanskrit dictionary concepts with 522,880 lookup keys
    -   Automatic query enhancement with dictionary definitions
    -   Vedic references displayed in UI
    -   O(1) lookup performance (108 MB concept store)
-   **✍️ Transliteration Layer:** Automatic Devanagari ↔ IAST conversion
    -   Generates query variants for comprehensive search
    -   Supports mixed-script queries (e.g., "soma रस का महत्व")
    -   Library: `indic-transliteration`

### 🤖 Agentic RAG System
-   **🧠 Multi-Agent Intelligence:** Automatically classifies queries into 3 types:
    -   **Construction Queries** - "Translate I love you" → Dictionary → Grammar → Corpus → Synthesis
    -   **Grammar Queries** - "Explain declension" → Grammar Rules → Examples → Explanation
    -   **Factual Queries** - "Who is Indra?" → Corpus Search → RAG Answer
-   **📚 Dictionary Integration:** Query enhancement with Monier-Williams definitions
-   **📖 Grammar Integration:** Macdonell's Vedic Grammar rules for accurate constructions
-   **🔍 Brahmana Context:** Satapatha + Pancavimsa Brahmanas for ritual and philosophical context
-   **🔗 Tool Orchestration:** Agent decides which tools to use based on query complexity
-   **✨ Pedagogical Output:** Word-by-word breakdowns with Devanagari + IAST transliteration

### 🚀 Technical Features
-   **Dual Interface:** Beautiful Streamlit web app + command-line tool
-   **Audio Pronunciation:** Native Devanagari text-to-speech using gTTS
-   **Hybrid Search:** Combines BM25 keyword search with semantic vector search
-   **Local LLMs:** Supports Ollama (llama3.1:8b, phi3.5:mini, qwen2.5:32b)
-   **Beautiful Typography:** Proper Devanagari font rendering (Noto Serif/Sans Devanagari)
-   **Smart Lock Management:** Automatic cleanup of Qdrant database locks
-   **Shared Vector Store:** Single Qdrant instance for all agentic tools (no more lock errors!)
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
│   ├── sanskrit_tutor_frontend.py   # Streamlit web interface (Agentic RAG)
│   ├── cli_run.py                   # Original RAG CLI
│   ├── helper.py                    # Logging and project paths
│   ├── config.py                    # Configuration settings
│   ├── settings.py                  # LLM and embeddings config
│   └── utils/
│       ├── agentic_rag.py           # 🆕 Multi-agent RAG system (3 query types)
│       ├── file_ops.py              # File operations
│       ├── index_files.py           # Document loading and vector store
│       ├── process_files.py         # PDF processing
│       ├── final_block_rag.py       # LangGraph RAG pipeline (legacy)
│       ├── retriever.py             # Hybrid retriever (BM25 + semantic)
│       ├── vector_store.py          # Qdrant vector store management
│       └── prompts.py               # LLM prompt templates
├── local_store/
│   ├── ancient_history/             # Complete Vedic corpus
│   │   ├── rigveda-griffith_COMPLETE_english_with_metadata/
│   │   ├── yajurveda-griffith_COMPLETE_english_with_metadata/
│   │   ├── satapatha_brahmana_part_01_books_1_2/
│   │   ├── satapatha_brahmana_part_02_books_3_4/
│   │   ├── satapatha_brahmana_part_03_books_5_6_7/
│   │   ├── satapatha_brahmana_part_04_books_8_9_10/
│   │   └── satapatha_brahmana_part_05_books_11_12_13_14/
│   ├── prose_vedas/                 # 🆕 Prose Brahmanas
│   │   └── pancavamsa_brahmana/     # Pancavimsa Brahmana (complete)
│   └── grammar_texts/               # 🆕 Grammar resources
│       ├── macdonell_vedic_grammar/ # Vedic grammar rules
│       └── monier_williams_dictionary/  # MW dictionary source files
├── monier_williams_concept_store.json  # 🆕 176K concepts, 523K lookup keys (108 MB)
├── parse_monier_williams_concept_store.py  # 🆕 MW parser for concept store
├── src/utils/
│   ├── mw_concept_store.py          # 🆕 MW integration utility for RAG
│   └── transliteration.py           # 🆕 Devanagari ↔ IAST conversion
├── demo_mw_rag_integration.py       # 🆕 Demo of MW + transliteration
├── test_mw_integration.py           # 🆕 Test suite for MW integration
├── reindex_to_cloud_multilingual.py # 🆕 Re-indexing script for multilingual embeddings
├── vector_store/                    # Qdrant vector database (~30K chunks)
├── MW_CONCEPT_STORE_IMPLEMENTATION.md  # 🆕 MW technical docs
├── MW_INTEGRATION_COMPLETE.md       # 🆕 Integration summary
├── MULTILINGUAL_REINDEXING_GUIDE.md # 🆕 Re-indexing guide
├── run_sanskrit_tutor.sh            # Launch CLI tutor
├── run_sanskrit_tutor_web.sh        # Launch Streamlit app
├── test_tts.py                      # Audio pronunciation test
├── AGENTIC_RAG_QUERY_TYPES.md       # 🆕 Query classification docs
├── DICTIONARY_CLEANING.md           # 🆕 OCR cleaning process
├── SANSKRIT_TUTOR_README.md         # CLI documentation
├── SANSKRIT_TUTOR_WEB_README.md     # Web interface guide
├── AUDIO_PRONUNCIATION_GUIDE.md     # TTS feature docs
├── PARALLELIZATION.md               # Multi-GPU optimization guide
└── FAST_MODELS_GUIDE.md             # Model comparison
```

## 🎓 Core Modules

### Sanskrit Tutor Applications

-   **`vedic_sanskrit_tutor.py`**: Command-line Sanskrit learning tool with interactive REPL. Choose from 6 learning modes (grammar, vocabulary, translation, pronunciation, quiz, conversation) and get RAG-powered answers from the Vedic corpus.

-   **`sanskrit_tutor_frontend.py`**: Beautiful Streamlit web interface with **Agentic RAG system**, proper Devanagari fonts, audio pronunciation, and interactive learning modules. Features automatic Qdrant lock cleanup and intelligent query routing.

### Agentic RAG System (NEW!)

-   **`agentic_rag.py`**: Multi-agent RAG system with intelligent query classification:
    - **3 Query Types:** Construction (translate sentences), Grammar (explain rules), Factual (answer questions)
    - **3 Specialized Tools:**
        - `dictionary_lookup()` - 10.6K+ cleaned Monier-Williams entries
        - `grammar_rules_search()` - Macdonell Vedic Grammar retrieval
        - `corpus_examples_search()` - Rigveda/Yajurveda/Brahmana examples
    - **Multi-Step Reasoning:** Agent plans which tools to use and in what order
    - **Pedagogical Synthesis:** Generates word-by-word breakdowns with grammar explanations
    - **Shared Vector Store:** Eliminates Qdrant lock errors across all tools

### RAG Pipeline Components (Legacy)

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

-   **`index_files.py`**: Loads markdown/text documents with metadata from ALL subdirectories in `local_store/`, creates Qdrant vector store with multilingual embeddings. Now supports:
    - **Rigveda** - Complete Griffith translation (1.9 MB)
    - **Yajurveda** - Complete Griffith translation (871 KB)
    - **Ramayana** - Griffith translation (2.3 MB)
    - **Macdonell Grammar** - Vedic grammar rules and tables (1.2 MB)
    - **Satapatha Brahmana** - All 14 books in 5 parts (4.3 MB)
    - **Pancavimsa Brahmana** - Complete text (1.6 MB)
    - **Embedding Model:** `paraphrase-multilingual-mpnet-base-v2` (768-dim, supports Hindi/Sanskrit/Devanagari)
    - Total: **~30,000 chunks** indexed in Qdrant Cloud

### Dictionary & Bilingual System

-   **`monier_williams_concept_store.json`**: 176,146 Sanskrit concepts with 522,880 lookup keys (108 MB)
    - Structured concept store with headwords, IAST variants, Devanagari, definitions, Vedic references
    - O(1) lookup performance for query enhancement
    - Used for bilingual query expansion and context enrichment

-   **`parse_monier_williams_concept_store.py`**: Parses 48 MB mw.txt into structured concept store

-   **`src/utils/mw_concept_store.py`**: Integration utility for RAG system
    - `MWConceptStore` class with lookup(), expand_query(), get_vedic_context()
    - Automatic transliteration and normalization
    - Batch operations for performance

-   **`src/utils/transliteration.py`**: Bidirectional Sanskrit/Hindi transliteration
    - `TransliterationHelper` class with normalize_query()
    - Devanagari ↔ IAST conversion
    - Query variant generation for comprehensive search

-   **`src/utils/retriever.py`**: Enhanced hybrid retriever with MW integration
    - Implements hybrid retrieval combining BM25 keyword search (30%) and semantic vector search (70%)
    - **NEW:** Automatic query enhancement with Monier-Williams definitions
    - **NEW:** Transliteration layer generates Devanagari/IAST variants
    - **NEW:** MW context attached to retrieved documents (displayed in UI)
    - Proper noun expansion for Sanskrit names
    - Returns top-k merged results with MW enrichment

### Legacy Dictionary Files

-   **`parse_monier_williams_v2.py`**: (Legacy) Parses 16MB dictionary into JSON (19,008 entries)

-   **`clean_dictionary.py`**: (Legacy) Cleans OCR errors from dictionary

-   **Dictionary Files:**
    - `monier_williams_dictionary.txt` - Original 16MB text
    - `sanskrit_dictionary.json` - 19,008 parsed entries (legacy)
    - `sanskrit_dictionary_cleaned.json` - 10,635 cleaned entries (legacy)

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

# Create conda environment (recommended)
conda create -n vedic-tutor python=3.11
conda activate vedic-tutor

# Install dependencies
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

# Embeddings (Multilingual Support)
EMBEDDING_PROVIDER=local-best    # Uses paraphrase-multilingual-mpnet-base-v2
EMBEDDING_DEVICE=cpu             # or 'mps' for Mac GPU, 'cuda' for NVIDIA
EMBEDDING_BATCH_SIZE=16

# Qdrant Cloud (for production deployment)
QDRANT_URL=your_qdrant_cloud_url
QDRANT_API_KEY=your_api_key
COLLECTION_NAME=ancient_history

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

### 5. Test Bilingual Queries 🌍

The system now supports **Hindi, Sanskrit, Devanagari, and mixed-script queries**:

**Devanagari Queries:**
```
सरस्वती नदी के विलुप्त होने का उल्लेख कहाँ है?
अग्नि पूजा की विधि क्या है?
सोम रस का महत्व समझाइये।
```

**IAST Transliteration:**
```
Sarasvatī river disappearance in Vedas
Explain the significance of soma in Rigveda
What are the main rituals described in Yajurveda?
```

**Mixed Script (Hindi + Sanskrit):**
```
soma रस का importance क्या है?
Agni देवता के बारे में बताओ
```

**English:**
```
Who is Indra in the Rigveda?
Explain the Gayatri Mantra
What is the meaning of dharma?
```

All queries are automatically enhanced with Monier-Williams dictionary definitions and return relevant results from the corpus.

## � Corpus Sources

The Vedic Sanskrit Tutor is built on a comprehensive corpus covering:

### 📜 Primary Vedic Texts
-   **Rigveda** - Complete Griffith translation with metadata
    - 10 Mandalas (books), 1,028 hymns, ~10,600 verses
    - Focus: Hymns to deities, cosmology, philosophy
-   **Yajurveda** - Complete Griffith translation with metadata
    - 40 chapters (adhyayas) of ritual formulas
    - Focus: Sacrificial procedures and mantras

### 📚 Grammar & Linguistic Resources
-   **Macdonell's Vedic Grammar** - Comprehensive grammatical reference
    - Phonetics, sandhi rules, declension tables
    - Conjugation patterns, verbal system
    - Accent rules, syntax, compound formation
-   **Monier-Williams Dictionary** - 10,635 cleaned entries
    - English to Sanskrit translations
    - OCR-corrected with curated common words
    - Grammatical annotations (gender, roots)

### 🕉️ Brahmana Literature
-   **Satapatha Brahmana** - Complete 14 books in 5 parts
    - Ritual explanations and procedures
    - Philosophical discussions and symbolism
    - Mythological narratives
    - Total: ~1,000 pages of prose commentary

### 📊 Corpus Statistics
-   **Total Documents:** ~20,000 markdown files
-   **Vector Database:** 19,944 chunks indexed in Qdrant
-   **Embeddings:** sentence-transformers/all-mpnet-base-v2
-   **Coverage:** Vedas, Grammar, Dictionary, Brahmanas

## �📚 Usage Guide

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

## � Corpus Statistics

**Current Qdrant Cloud Collection: `ancient_history`**

| Source | Size | Chunks | % of Corpus | Status |
|--------|------|--------|-------------|--------|
| Pancavimsa Brahmana | 1.6 MB | ~13,226 | 44% | ✅ Indexed |
| Satapatha Brahmana (5 parts) | 4.3 MB | ~10,521 | 35% | ✅ Indexed |
| Rigveda Griffith | 1.9 MB | ~3,542 | 12% | ✅ Indexed |
| Ramayana Griffith | 2.3 MB | ~1,500 | 5% | ✅ Indexed |
| Macdonell Vedic Grammar | 1.2 MB | ~800 | 3% | ✅ Indexed |
| Yajurveda Griffith | 871 KB | ~411 | 1% | ✅ Indexed |
| **Total Corpus** | **~12 MB** | **~30,000** | **100%** | ✅ Complete |

**Embeddings**: `paraphrase-multilingual-mpnet-base-v2` (768-dim)
- Supports: English, Hindi, Sanskrit, Devanagari, 50+ languages
- Vector storage: ~92 MB (768-dim × 30K points × 4 bytes)
- Distance metric: Cosine similarity

**Monier-Williams Concept Store** (separate from vector DB):
- 176,146 Sanskrit concepts
- 522,880 lookup keys
- 108 MB JSON file (not in Qdrant)
- Used for query enhancement and context enrichment

## �📖 Documentation Files

- **`MW_CONCEPT_STORE_IMPLEMENTATION.md`** - Monier-Williams integration technical docs
- **`MW_INTEGRATION_COMPLETE.md`** - Bilingual enhancement implementation summary
- **`MULTILINGUAL_REINDEXING_GUIDE.md`** - Re-indexing with multilingual embeddings
- **`DIMENSION_SOLUTION.md`** - 768-dim embedding model selection rationale
- **`SANSKRIT_TUTOR_WEB_README.md`** - Complete web interface guide
- **`SANSKRIT_TUTOR_README.md`** - CLI usage instructions
- **`AUDIO_PRONUNCIATION_GUIDE.md`** - TTS feature documentation
- **`FAST_MODELS_GUIDE.md`** - Model performance comparison
- **`AGENTIC_RAG_QUERY_TYPES.md`** - Query classification documentation
- **`PARALLELIZATION.md`** - Multi-GPU optimization guide

## 🛣️ Roadmap of Planned Development

### Completed Features ✅

**Phase 1: Grammar Foundation** (Completed 2026-01-18)
- [x] Add Macdonell's Vedic Grammar for Students
- [x] Add Macdonell's Vedic Reader (30 analyzed hymns)
- [x] Add Whitney's Sanskrit Grammar

**Phase 2: Prose Texts** (Completed 2026-01-18)
- [x] Add Satapatha Brahmana (all 14 books, narrative prose)
- [x] Add Aitareya Brahmana (subject-object-verb structures)

**Phase 3: Dictionaries** (Completed 2026-01-18)
- [x] Monier-Williams Sanskrit-English Dictionary
- [x] Grassmann's Wörterbuch zum Rig-veda

**Phase 4: Bilingual Support** (Completed 2026-02-01)
- [x] Multilingual embeddings (768-dim, supports Hindi/Sanskrit/Devanagari)
- [x] Monier-Williams concept store (176K concepts, 523K lookup keys)
- [x] Transliteration layer (Devanagari ↔ IAST)
- [x] Query enhancement with dictionary definitions
- [x] MW context display in UI
- [x] Pancavimsa Brahmana indexed (13,226 chunks)
- [x] Re-indexed corpus to Qdrant Cloud (~30,000 chunks)

### Planned Improvements

**Phase 5: Advanced Features**
- [ ] Spaced repetition flashcards
- [ ] Progress tracking across sessions
- [ ] Export chat history as PDF
- [ ] Dark mode theme
- [ ] Devanagari typing practice
- [ ] Voice input for pronunciation practice
- [ ] Sanskrit-to-English translation mode
- [ ] Verse comparison across translations

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
