"""
Streamlit Frontend for Vedic Sanskrit Learning Agent

A beautiful web interface for learning Vedic Sanskrit with:
- Proper Devanagari font rendering
- Interactive lessons and exercises
- Progress tracking
- Flashcard mode
- Quiz system
"""

import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from typing import Dict, List, Optional
import json
from datetime import datetime
import tempfile
import base64
import subprocess
from pathlib import Path
import time
import glob

from src.helper import project_root, logger
from src.config import LOCAL_FOLDER, COLLECTION_NAME, VECTORDB_FOLDER
from src.utils.index_files import create_qdrant_vector_store
from src.utils.agentic_rag import run_agentic_rag, set_shared_vector_store

from langchain_community.chat_models import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from src.settings import OLLAMA_BASE_URL, OLLAMA_MODEL, GEMINI_MODEL
from src.config import GROQ_API_KEY
from src.utils.sanskrit_translator import get_translator


# Page configuration with Devanagari font support
st.set_page_config(
    page_title="🕉️ Vedic Sanskrit Resource",
    page_icon="🕉️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Theme: warm saffron & parchment, mobile-first ──────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;600;700&family=Noto+Serif+Devanagari:wght@400;500;700&family=Marcellus&family=EB+Garamond:ital@0;1&display=swap');

    :root {
        --saffron: #E07A1F;
        --saffron-deep: #C75B12;
        --maroon: #7A2E1E;
        --gold: #C8962B;
        --parchment: #FBF3E2;
        --parchment-2: #F6E8CE;
        --ink: #3A2A1E;
        --ink-soft: #6B5742;
    }

    /* Page canvas — soft parchment wash */
    .stApp {
        background:
            radial-gradient(1200px 500px at 50% -200px, #FFF7E8 0%, rgba(255,247,232,0) 70%),
            linear-gradient(180deg, #FBF3E2 0%, #F7ECD6 100%);
    }

    /* Headings in a refined display serif */
    h1, h2, h3, h4 { font-family: 'Marcellus', 'EB Garamond', serif !important; color: var(--maroon) !important; letter-spacing: .3px; }

    /* Devanagari */
    .devanagari { font-family: 'Noto Serif Devanagari', serif; font-size: 1.5em; line-height: 1.8; color: var(--maroon); }
    .devanagari-large { font-family: 'Noto Serif Devanagari', serif; font-size: 2em; line-height: 2; color: var(--maroon); font-weight: 700; }
    .sanskrit-iast { font-family: 'EB Garamond', serif; font-style: italic; color: var(--ink-soft); }

    /* ── Hero verse band ── */
    .hero {
        position: relative;
        text-align: center;
        padding: 30px 22px 26px;
        margin: 4px 0 10px;
        background: linear-gradient(180deg, #FFFDF8 0%, var(--parchment) 100%);
        border: 1px solid #EAD7B0;
        border-radius: 18px;
        box-shadow: 0 10px 30px rgba(122,46,30,.08), inset 0 1px 0 #FFFFFF;
        overflow: hidden;
    }
    .hero::before { content: "🕉️"; position: absolute; font-size: 9rem; opacity: .05; top: -18px; right: 8px; transform: rotate(8deg); }
    .hero-eyebrow { font-family:'Marcellus',serif; text-transform: uppercase; letter-spacing: 3px; font-size: .72rem; color: var(--saffron-deep); margin-bottom: 10px; }
    .hero-verse {
        font-family: 'Noto Serif Devanagari', serif; font-weight: 700;
        font-size: clamp(1.5rem, 5.2vw, 2.8rem); line-height: 1.55; color: var(--maroon);
        margin: 2px auto 12px; max-width: 22ch;
    }
    .hero-rule { width: 120px; height: 2px; margin: 0 auto 12px; background: linear-gradient(90deg, transparent, var(--gold), transparent); }
    .hero-iast { font-family: 'EB Garamond', serif; font-style: italic; font-size: clamp(.95rem, 2.6vw, 1.15rem); color: var(--ink-soft); }
    .hero-cite { font-family: 'Marcellus', serif; font-size: .8rem; letter-spacing: 1px; color: var(--saffron-deep); margin-top: 6px; }

    /* ── Parchment content cards ── */
    .lesson-container, .panel {
        background: #FFFDF8; padding: 22px 24px; border-radius: 14px;
        border: 1px solid #EAD7B0; border-left: 5px solid var(--saffron);
        box-shadow: 0 6px 18px rgba(122,46,30,.06); color: var(--ink); margin: 6px 0 14px;
    }
    .lesson-container h3, .lesson-container h4, .lesson-container p, .lesson-container li,
    .panel h3, .panel h4, .panel p, .panel li { color: var(--ink) !important; }
    .lesson-container ul { margin: 6px 0 0; padding-left: 1.1em; }
    .lesson-container li { margin: 7px 0; line-height: 1.5; }

    /* Section eyebrow label */
    .eyebrow { font-family:'Marcellus',serif; text-transform: uppercase; letter-spacing: 2.5px;
        font-size: .74rem; color: var(--saffron-deep); margin: 4px 0 8px; }

    /* ── Corpus cards ── */
    .corpus-group { font-family:'Marcellus',serif; color: var(--maroon); font-size: .82rem;
        letter-spacing: 1.5px; text-transform: uppercase; margin: 12px 0 6px; }
    .corpus-card {
        display: flex; align-items: baseline; gap: 10px; background: var(--parchment);
        border: 1px solid #EAD7B0; border-radius: 10px; padding: 9px 13px; margin: 7px 0;
    }
    .corpus-card .abbr { font-family:'Marcellus',serif; font-weight: 700; color: var(--saffron-deep);
        min-width: 46px; font-size: .95rem; }
    .corpus-card .name { color: var(--ink); font-size: .92rem; }
    .corpus-card .name small { color: var(--ink-soft); }

    /* "Designed for" chips */
    .designed-for .row { display: flex; gap: 11px; align-items: flex-start; margin: 11px 0; }
    .designed-for .ic { font-size: 1.25rem; line-height: 1.3; }
    .designed-for .tx { color: var(--ink); line-height: 1.45; }

    /* Module / quiz / chat */
    .module-card { background: linear-gradient(135deg, #FFF8DC 0%, #F3E2B8 100%); padding: 20px;
        border-radius: 12px; border-left: 5px solid var(--saffron); margin: 10px 0; }
    .quiz-card { background: #FBF3E2; padding: 15px; border-radius: 10px; border-left: 4px solid var(--gold); }
    .progress-text { font-family: 'Noto Sans Devanagari', sans-serif; font-size: .9em; color: var(--ink-soft); }
    .student-message { background: #FDEBD3; padding: 12px 15px; border-radius: 12px 12px 12px 4px;
        margin: 8px 0; color: var(--ink); border: 1px solid #F0D9B5; }
    .tutor-message { background: #FFFDF8; padding: 12px 15px; border-radius: 12px 12px 4px 12px;
        margin: 8px 0; color: var(--ink); border: 1px solid #EAD7B0; border-left: 4px solid var(--saffron); }

    /* Subtle footer note */
    .getstarted-note { text-align: center; color: var(--ink-soft); font-size: .86rem;
        font-style: italic; margin: 10px auto 4px; max-width: 60ch; }

    /* Buy Me a Coffee button */
    .bmc-btn { display: block; text-align: center; text-decoration: none;
        margin: 8px auto; max-width: 240px; background: #FFDD00; color: #3A2A1E !important;
        font-family: 'Marcellus', serif; font-weight: 600; letter-spacing: .3px;
        padding: 10px 16px; border-radius: 12px; border: 1px solid #E6C200;
        box-shadow: 0 2px 6px rgba(122,46,30,.12); transition: background .15s, transform .15s; }
    .bmc-btn:hover { background: #FFE74D; transform: translateY(-1px); }

    /* Buttons → saffron */
    .stButton > button { border: 1px solid #E6C98F !important; background: #FFFDF8 !important;
        color: var(--maroon) !important; border-radius: 10px !important; font-size: .9rem; }
    .stButton > button:hover { border-color: var(--saffron) !important; background: var(--parchment) !important; }

    /* ── Widget text: force dark ink regardless of OS dark-mode ── */
    /* Input labels */
    .stTextInput label, .stTextArea label, .stSelectbox label,
    .stNumberInput label, .stSlider label, .stRadio label,
    .stCheckbox label, .stMultiSelect label {
        color: var(--ink) !important;
    }
    /* Input field text & placeholder */
    .stTextInput input, .stTextArea textarea {
        color: var(--ink) !important;
        background-color: #FFFDF8 !important;
        border: 1px solid #EAD7B0 !important;
    }
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {
        color: var(--ink-soft) !important;
        opacity: 1 !important;
    }
    /* Spinner */
    .stSpinner p, [data-testid="stSpinner"] p { color: var(--ink) !important; }
    /* General markdown / text in containers */
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stMarkdownContainer"] strong,
    [data-testid="stMarkdownContainer"] em { color: var(--ink) !important; }
    /* Expander header */
    .streamlit-expanderHeader { color: var(--ink) !important; }
    /* Selectbox & multiselect text */
    .stSelectbox div[data-baseweb="select"] span,
    .stMultiSelect div[data-baseweb="select"] span { color: var(--ink) !important; }

    /* Hide streamlit branding */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}

    /* ── Mobile ── */
    @media (max-width: 640px) {
        .hero { padding: 22px 14px 20px; border-radius: 14px; }
        .hero::before { font-size: 6rem; }
        .hero-verse { max-width: 100%; }
        .lesson-container, .panel { padding: 16px 16px; }
        .block-container { padding-left: .8rem !important; padding-right: .8rem !important; }
    }
</style>
""", unsafe_allow_html=True)


class SanskritTutorApp:
    """Streamlit-based Vedic Sanskrit resource application."""

    def __init__(self):
        self.initialize_session_state()

    def initialize_session_state(self):
        """Initialize session state variables."""
        if 'initialized' not in st.session_state:
            st.session_state.initialized = False
            st.session_state.vec_db = None
            st.session_state.docs = None
            st.session_state.llm = None
            st.session_state.chat_history = []
            st.session_state.current_module = None
            st.session_state.learned_words = []
            st.session_state.quiz_score = {"correct": 0, "total": 0}
            st.session_state.model_name = "llama3.1:8b"
            st.session_state.llm_provider = "gemini"
            st.session_state.audio_cache = {}  # Cache audio files
            st.session_state.input_language = "English"  # ✅ NEW: Language preference
            st.session_state.last_translations = {}  # ✅ NEW: Store translations

    def text_to_speech(self, text: str, lang: str = 'hi') -> Optional[bytes]:
        """
        Convert text to speech and return audio bytes.

        Args:
            text: Text to convert (Devanagari or transliteration)
            lang: Language code ('hi' for Hindi/Sanskrit, 'en' for English)

        Returns:
            Audio bytes or None if failed
        """
        # Check cache first
        cache_key = f"{text}_{lang}"
        if cache_key in st.session_state.audio_cache:
            return st.session_state.audio_cache[cache_key]

        try:
            from gtts import gTTS
            import io

            # Validate text
            if not text or not text.strip():
                st.warning("⚠️ No text provided for pronunciation")
                return None

            # Generate speech with error handling
            # For Sanskrit, use Hindi (hi) which handles Devanagari well
            try:
                tts = gTTS(text=text, lang=lang, slow=True)  # slow=True for clearer pronunciation

                # Save to BytesIO instead of file
                audio_fp = io.BytesIO()
                tts.write_to_fp(audio_fp)
                audio_fp.seek(0)
                audio_bytes = audio_fp.read()

                # Verify we got audio data
                if len(audio_bytes) == 0:
                    st.error("❌ Audio generation returned empty data")
                    return None

                # Verify it's valid MP3 (check for ID3 tag or MP3 sync bits)
                # MP3 files typically start with 'ID3' or 0xFF 0xFB (MP3 sync)
                if len(audio_bytes) < 3:
                    st.error("❌ Audio data too small")
                    return None

                # Log first few bytes for debugging
                logger.info(f"Audio generated: {len(audio_bytes)} bytes, header: {audio_bytes[:4].hex()}")

                # Cache the bytes
                st.session_state.audio_cache[cache_key] = audio_bytes
                return audio_bytes

            except Exception as tts_error:
                # Handle specific gTTS errors
                error_msg = str(tts_error)
                if "Connection" in error_msg or "timeout" in error_msg.lower():
                    st.error("❌ Network error: Cannot reach Google TTS servers. Check your internet connection.")
                elif "language" in error_msg.lower():
                    st.error(f"❌ Language '{lang}' not supported by gTTS")
                else:
                    st.error(f"❌ TTS generation failed: {error_msg}")
                return None

        except ImportError:
            st.warning("⚠️ gTTS not installed. Run: `pip install gtts` to enable audio pronunciation.")
            return None
        except Exception as e:
            logger.error(f"Unexpected TTS error: {e}", exc_info=True)
            st.error(f"❌ Unexpected error: {e}")
            return None

    def play_audio(self, audio_data: bytes, label: str = "🔊 Listen"):
        """
        Display audio player in Streamlit.

        Args:
            audio_data: Audio bytes to play
            label: Button/player label
        """
        if not audio_data:
            st.warning("⚠️ No audio data to play")
            return

        try:
            # Validate audio data
            if len(audio_data) == 0:
                st.error("❌ Audio data is empty")
                logger.error("Audio data is empty")
                return

            # Check data type
            if not isinstance(audio_data, bytes):
                st.error(f"❌ Audio data has wrong type: {type(audio_data)}")
                logger.error(f"Wrong audio data type: {type(audio_data)}")
                return

            # Display audio player
            # Streamlit audio expects bytes-like object
            st.audio(audio_data, format='audio/mpeg')

            # Optional: Show debug info in expander
            with st.expander("🔧 Audio Info (debug)"):
                st.text(f"Size: {len(audio_data):,} bytes")
                st.text(f"Format: MP3")
                st.text(f"Generated by: Google TTS (gTTS)")
                st.text(f"Type: {type(audio_data)}")
                # Show first few bytes as hex for debugging
                st.text(f"Header: {audio_data[:16].hex() if len(audio_data) >= 16 else 'N/A'}")

        except Exception as e:
            logger.error(f"Error playing audio: {e}", exc_info=True)
            st.error(f"❌ Could not play audio: {type(e).__name__}: {e}")

    def check_qdrant_lock(self) -> bool:
        """Check if Qdrant database is locked."""
        import glob
        lock_files = glob.glob(str(Path(VECTORDB_FOLDER) / "**" / ".qdrant-lock"), recursive=True)
        return len(lock_files) > 0

    def cleanup_qdrant_locks(self) -> bool:
        """Remove Qdrant lock files."""
        import glob
        import shutil

        try:
            lock_files = glob.glob(str(Path(VECTORDB_FOLDER) / "**" / ".qdrant-lock"), recursive=True)
            for lock_file in lock_files:
                try:
                    Path(lock_file).unlink()
                    logger.info(f"Removed lock file: {lock_file}")
                except Exception as e:
                    logger.error(f"Failed to remove lock {lock_file}: {e}")
                    return False
            return True
        except Exception as e:
            logger.error(f"Error cleaning locks: {e}")
            return False

    def setup_tutor(self, llm_provider: str, model_name: str):
        """Initialize the RAG system and LLM."""
        if st.session_state.initialized:
            return True

        try:
            # Check for Qdrant lock before attempting to initialize
            if self.check_qdrant_lock():
                st.info("🔧 Found stale Qdrant locks. Cleaning up automatically...")

                # Automatically clean locks
                if self.cleanup_qdrant_locks():
                    st.success("✓ Locks cleaned successfully! Proceeding with initialization...")
                    time.sleep(0.5)  # Brief pause to ensure cleanup completes
                else:
                    st.error("❌ Failed to clean locks automatically.")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🔧 Try manual cleanup", key="manual_cleanup"):
                            if self.cleanup_qdrant_locks():
                                st.success("✓ Locks cleaned! Click 'Initialize Resource' again.")
                                st.rerun()
                            else:
                                st.error("Failed to clean locks. Try restarting your system.")
                    with col2:
                        st.info("💡 **Or**: Close other instances using the vector store (CLI, other Streamlit apps)")

                return False

            with st.spinner("📚 Loading Vedic texts corpus..."):
                vec_db, docs = create_qdrant_vector_store(force_recreate=False)
                # Store vector DB for agentic RAG access
                st.session_state.vec_db = vec_db
                st.session_state.docs = docs

                # CRITICAL: Set shared vector store for agentic RAG tools
                set_shared_vector_store(vec_db, docs)
                logger.info("[FRONTEND] Shared vector store configured for agentic RAG")

            with st.spinner("🤖 Initializing AI resource..."):
                if llm_provider == "gemini":
                    llm = ChatGoogleGenerativeAI(
                        model=GEMINI_MODEL,
                        temperature=0.7,
                        timeout=180
                    )
                elif llm_provider == "groq":
                    if not GROQ_API_KEY:
                        st.error("❌ GROQ_API_KEY not found in environment variables!")
                        return False
                    llm = ChatGroq(
                        api_key=GROQ_API_KEY,
                        model=model_name,
                        temperature=0.7,
                        timeout=180
                    )
                else:  # ollama
                    llm = ChatOllama(
                        base_url=OLLAMA_BASE_URL,
                        model=model_name,
                        temperature=0.7,
                        timeout=180,
                        num_predict=2048
                    )

                st.session_state.llm = llm
                st.session_state.model_name = model_name
                st.session_state.llm_provider = llm_provider
                st.session_state.initialized = True

            return True

        except RuntimeError as e:
            # Catch the specific Qdrant lock error
            if "already accessed" in str(e):
                st.error("❌ Qdrant database is locked!")
                st.warning("⚠️ Another instance is using the vector store.")

                if st.button("🔧 Try to clean locks", key="cleanup_on_error"):
                    if self.cleanup_qdrant_locks():
                        st.success("✓ Locks cleaned! Refresh the page and try again.")
                    else:
                        st.error("Could not clean locks. Please close other instances or restart.")

                st.info("💡 **Solutions:**\n" +
                       "1. Close the CLI version if running\n" +
                       "2. Close other Streamlit tabs\n" +
                       "3. Click the cleanup button above\n" +
                       "4. Refresh this page (Ctrl+R or Cmd+R)")
            else:
                st.error(f"❌ Error initializing resource: {e}")

            logger.exception("Failed to initialize resource")
            return False

        except Exception as e:
            st.error(f"❌ Error initializing resource: {e}")
            logger.exception("Failed to initialize resource")
            return False

    def get_system_prompt(self, mode: str) -> str:
        """Get system prompt based on learning mode."""
        base = """You are a knowledgeable Vedic Sanskrit resource. Your user:
- Has studied Sanskrit in school but forgotten most of it
- Is a native Hindi speaker (use Hindi when helpful)
- Wants to read and understand Vedic texts (Rigveda, Yajurveda)

Resource principles:
- Start simple, build gradually
- Use both Devanagari (देवनागरी) and IAST transliteration
- Use Hindi for explanations when it helps
- Connect to familiar Hindi words
- Provide examples from the Vedic corpus
- Be encouraging and patient
- Format Devanagari clearly for web display
"""

        mode_specific = {
            "grammar": """
Focus on Vedic Sanskrit grammar:
1. Sandhi rules (संधि) - explain with examples in Devanagari
2. Vibhakti (विभक्ति) - case endings with tables
3. Dhatu (धातु) - verb roots with conjugations
4. Provide mnemonic devices
5. Compare with Hindi when useful
""",
            "vocabulary": """
Teach Vedic Sanskrit vocabulary:
1. Present words in Devanagari first, then IAST
2. Give Hindi and English meanings
3. Show usage in actual verses
4. Group by themes (देवता, यज्ञ, प्रकृति)
5. Create word families (धातु → शब्द)
6. Add pronunciation tips
""",
            "translation": """
Guide verse translation step-by-step:
1. Show verse in Devanagari
2. Break down word-by-word with sandhi analysis
3. Identify grammatical forms
4. Provide word-for-word translation
5. Give natural Hindi/English translation
6. Discuss cultural/philosophical context
""",
            "pronunciation": """
Teach Vedic pronunciation:
1. Show Devanagari clearly
2. Provide IAST transliteration
3. Explain vowel lengths (ā, ī, ū)
4. Teach anusvāra (ं), visarga (ः) rules
5. Accent marks in Vedic (udātta, anudātta)
6. Practice with mantras
""",
            "quiz": """
Create engaging quiz questions:
1. Use both Devanagari and transliteration
2. Multiple choice or fill-in-the-blank
3. Provide hints if needed
4. Explain answers thoroughly
5. Be encouraging!
""",
            "conversation": """
Have natural conversation about Sanskrit:
1. Answer questions clearly
2. Use Devanagari when appropriate
3. Provide relevant examples
4. Suggest learning paths
5. Be supportive
"""
        }

        return base + mode_specific.get(mode, mode_specific["conversation"])

    def ask_tutor(self, query: str, mode: str = "conversation",
                  pinned_verse: dict = None) -> str:
        """Query the resource using Agentic RAG with language preference.

        pinned_verse: when a caller (e.g. the Verse Translation module) already has
        the resolved verse, it passes it directly. That routes through the
        pinned-verse interpretation branch — so the English instruction is NOT
        treated as a phrase to translate.
        """
        system_prompt = self.get_system_prompt(mode)

        try:
            # Use Agentic RAG system with language preference
            with st.spinner("🤖 Agent analyzing your question..."):
                logger.info(f"[FRONTEND] Processing query with Agentic RAG: {query}")
                logger.info(f"[FRONTEND] Input language: {st.session_state.input_language}")

                # ── Verse grounding for the Home conversation ──────────────────
                # If a pinned verse wasn't supplied by the caller and we're in the
                # Home chat, auto-detect a citation in the query and pin it
                # (remembered across follow-ups). Gated on a citation being present,
                # so ordinary semantic-search queries are completely unaffected.
                if pinned_verse is None and mode == "conversation":
                    found = self._lookup_verse_text(query)
                    if found:
                        pinned_verse = found
                        st.session_state.pinned_verse = found
                        logger.info(f"[FRONTEND] Pinned verse {found['citation']} for grounding")
                    else:
                        prev = st.session_state.get("pinned_verse")
                        if prev and self._is_verse_followup(query):
                            pinned_verse = prev  # carry the same verse into a follow-up
                        else:
                            st.session_state.pinned_verse = None  # topic changed → unpin

                # ✅ Pass language preference (+ optional pinned verse) to RAG
                result = run_agentic_rag(
                    query,
                    input_language=st.session_state.input_language,
                    pinned_verse=pinned_verse,
                )
                
                logger.info(f"[FRONTEND] Agentic RAG returned result type: {type(result)}")
                logger.info(f"[FRONTEND] Result keys: {result.keys() if isinstance(result, dict) else 'not a dict'}")

            # Extract answer from agentic result
            if isinstance(result, dict):
                answer = result.get("answer", {})
                logger.info(f"[FRONTEND] Answer field type: {type(answer)}, value: {answer}")

                if isinstance(answer, dict):
                    answer_text = answer.get("answer", "No answer generated")
                    logger.info(f"[FRONTEND] Extracted answer_text: {answer_text[:100] if answer_text else 'EMPTY'}")
                else:
                    answer_text = str(answer)
                    logger.info(f"[FRONTEND] Answer is not dict, converted to str: {answer_text[:100]}")

                # CHECK FOR MW CONTEXT from retriever
                # Retrieved documents may have MW dictionary context attached
                retrieved_docs = result.get("retrieved_documents", [])
                mw_context_found = None
                
                if retrieved_docs and len(retrieved_docs) > 0:
                    # Check if first document has MW context
                    first_doc = retrieved_docs[0]
                    if hasattr(first_doc, 'metadata') and 'mw_context' in first_doc.metadata:
                        mw_context_found = first_doc.metadata['mw_context']
                        logger.info(f"[FRONTEND] Found MW context in documents: {len(mw_context_found)} entries")

                # Display MW Dictionary Context (if available)
                if mw_context_found and len(mw_context_found) > 0:
                    with st.expander("📖 Sanskrit Dictionary (Monier-Williams)", expanded=False):
                        st.markdown("**Found Sanskrit terms in your query:**")
                        
                        for mw_entry in mw_context_found[:3]:  # Show top 3 entries
                            primary_key = mw_entry.get('primary_key', 'unknown')
                            devanagari = mw_entry.get('devanagari', '')
                            definitions = mw_entry.get('definitions', [])
                            vedic_refs = mw_entry.get('vedic_refs', [])
                            
                            # Display term
                            st.markdown(f"**{primary_key}** ({devanagari})")
                            
                            # Display first definition
                            if definitions and len(definitions) > 0:
                                first_def = definitions[0]
                                # Clean up definition (remove metadata)
                                if len(first_def) > 200:
                                    first_def = first_def[:200] + "..."
                                st.markdown(f"  {first_def}")
                            
                            # Display Vedic references
                            if vedic_refs and len(vedic_refs) > 0:
                                refs_str = ', '.join(vedic_refs[:5])
                                st.caption(f"  📚 References: {refs_str}")
                            
                            st.markdown("---")

                # Display agent insights
                query_type = result.get("query_type", "unknown")
                english_words = result.get("english_words", [])
                sanskrit_words = result.get("sanskrit_words", {})

                # Display agent insights (existing code)

                # Display agent insights
                if query_type == "construction" and (english_words or sanskrit_words):
                    with st.expander("🔍 Agent's Thinking Process", expanded=False):
                        st.markdown(f"**Query Type:** {query_type}")
                        if english_words:
                            st.markdown(f"**Words to translate:** {', '.join(english_words)}")
                        if sanskrit_words:
                            st.markdown("**Dictionary Lookups:**")
                            for eng, skts in sanskrit_words.items():
                                if skts:
                                    st.markdown(f"  • {eng} → {', '.join(skts[:3])}")

                        grammar_count = len(result.get("grammar_rules", []))
                        corpus_count = len(result.get("corpus_examples", []))
                        st.markdown(f"**Retrieved:** {grammar_count} grammar rules, {corpus_count} corpus examples")
            else:
                answer_text = str(result)

            # Update chat history ONLY for the home conversation.
            # Module modes (translation, grammar, vocabulary, pronunciation, quiz)
            # render their own output and must not leak into the home chatbox.
            if mode == "conversation":
                st.session_state.chat_history.append({"role": "user", "content": query})
                st.session_state.chat_history.append({"role": "assistant", "content": answer_text})

            return answer_text

        except Exception as e:
            logger.error(f"Error in resource: {e}")
            import traceback
            traceback.print_exc()
            return f"Sorry, I encountered an error: {e}"

    def _make_export_data(self, question: str, answer: str):
        """Build (md_bytes, docx_bytes_or_None) for a single Q+A pair."""
        date_str = datetime.now().strftime('%Y-%m-%d')
        md = (
            f"# Vedic Sanskrit Resource — Response\n\n"
            f"**Question:** {question}\n\n"
            f"---\n\n"
            f"{answer}\n\n"
            f"---\n*Exported from Vedic Sanskrit Resource · {date_str}*\n"
        )
        md_bytes = md.encode('utf-8')

        docx_bytes = None
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                md_path = os.path.join(tmpdir, 'export.md')
                docx_path = os.path.join(tmpdir, 'export.docx')
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(md)
                result = subprocess.run(
                    ['pandoc', '-f', 'markdown', '-t', 'docx',
                     '-o', docx_path, md_path],
                    capture_output=True, timeout=30
                )
                if result.returncode == 0 and os.path.exists(docx_path):
                    with open(docx_path, 'rb') as f:
                        docx_bytes = f.read()
        except Exception:
            pass

        return md_bytes, docx_bytes

    def _render_answer_export(self, question: str, answer: str, key_suffix: str):
        """Render per-answer MD (and optional DOCX) download buttons."""
        md_bytes, docx_bytes = self._make_export_data(question, answer)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        btn_cols = st.columns([6, 1, 1] if docx_bytes else [6, 1])
        with btn_cols[1]:
            st.download_button(
                label="⬇️ .md",
                data=md_bytes,
                file_name=f"vedic_{ts}.md",
                mime="text/markdown",
                key=f"export_md_{key_suffix}",
                use_container_width=True,
            )
        if docx_bytes:
            with btn_cols[2]:
                st.download_button(
                    label="⬇️ .docx",
                    data=docx_bytes,
                    file_name=f"vedic_{ts}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"export_docx_{key_suffix}",
                    use_container_width=True,
                )

    def render_devanagari(self, text: str, large: bool = False):
        """Render text with Devanagari font."""
        css_class = "devanagari-large" if large else "devanagari"
        st.markdown(f'<div class="{css_class}">{text}</div>', unsafe_allow_html=True)

    def render_sidebar(self):
        """Render the sidebar with settings and navigation."""
        with st.sidebar:
            st.title("🕉️ Vedic Sanskrit Resource")
            st.markdown("### नमस्ते! Welcome")

            # Model selection
            st.markdown("---")
            st.subheader("⚙️ Settings")

            llm_provider = st.selectbox(
                "LLM Provider",
                ["gemini", "ollama", "groq"],
                key="llm_provider_select"
            )

            # Provider info
            if llm_provider == "groq":
                st.info("💡 Groq: Fast cloud API, requires GROQ_API_KEY")
            elif llm_provider == "gemini":
                st.info("💡 Gemini: Google's model, requires GEMINI_API_KEY")
            else:
                st.info("💡 Ollama: Local models, requires Ollama running")

            if llm_provider == "ollama":
                model_name = st.selectbox(
                    "Ollama Model",
                    ["llama3.1:8b", "phi3.5:mini", "phi3:mini", "llama3.2:3b", "llama3.2:1b", "gemma2:2b"],
                    help="Smaller models are faster. phi3.5:mini recommended!"
                )
            elif llm_provider == "groq":
                model_name = st.selectbox(
                    "Groq Model",
                    ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"],
                    help="Fast cloud-based models. llama-3.1-8b-instant recommended!"
                )
            else:
                model_name = GEMINI_MODEL

            # AUTO-INITIALIZE on first page load (one attempt; the button
            # below remains as a manual retry if it fails)
            if (not st.session_state.initialized
                    and not st.session_state.get("auto_init_attempted")):
                st.session_state.auto_init_attempted = True
                if self.setup_tutor(llm_provider, model_name):
                    st.success("✓ Resource ready!")
                    st.rerun()

            if st.button("🚀 Initialize Resource", key="init_button"):
                if self.setup_tutor(llm_provider, model_name):
                    st.success("✓ Resource ready!")
                    st.rerun()

            if st.session_state.initialized:
                st.success(f"✓ Using: {st.session_state.model_name}")

            # Language preference (compact, always visible)
            st.markdown("---")
            input_language = st.radio(
                "🌐 Query language",
                ["English", "Devanagari"],
                horizontal=True,
                key="input_lang_radio"
            )
            st.session_state.input_language = input_language

            # Qdrant lock cleanup utility
            if not st.session_state.initialized:
                st.markdown("---")
                st.caption("**Having issues?**")
                if st.button("🗑️ Clean Qdrant Locks", key="sidebar_cleanup"):
                    with st.spinner("Cleaning locks..."):
                        if self.cleanup_qdrant_locks():
                            st.success("✓ Locks cleaned!")
                            st.info("Now click 'Initialize Resource' above")
                        else:
                            st.error("Could not clean locks")

            # Navigation
            st.markdown("---")
            st.subheader("📚 Learning Modules")

            module = st.radio(
                "Choose a module:",
                [
                    "🏠 Home",
                    "📖 Grammar Basics",
                    "📚 Vocabulary Builder",
                    "🔤 Verse Translation",
                    "🗣️ Pronunciation",
                ],
                index=0,  # default to Home
                key="module_selector"
            )

            st.session_state.current_module = module

            # Quick reference
            st.markdown("---")
            st.markdown("### 🔤 Quick Reference")
            with st.expander("Devanagari Vowels"):
                st.markdown("""
                **स्वर (Svara - Vowels)**

                अ आ इ ई उ ऊ
                ऋ ॠ ऌ ए ऐ ओ औ
                """)

            with st.expander("Common Sandhi"):
                st.markdown("""
                **संधि Rules**

                - अ + अ = आ
                - अ + इ = ए
                - अ + उ = ओ
                """)

            # Support the project
            st.markdown("---")
            st.markdown(
                '<a href="https://www.buymeacoffee.com/shiv.tewari" target="_blank" '
                'class="bmc-btn">☕ Buy me a Soma (coffee)</a>',
                unsafe_allow_html=True,
            )
            st.caption("This is a personally-funded research preview — support keeps it running. 🙏")
            _vc = st.session_state.get("visit_count")
            if _vc:
                st.caption(f"🪔 {_vc:,} visits and counting")

    def render_home(self):
        """Render home page."""
        # ── Hero: the opening verse of the Rigveda as a headline ──────────────
        st.markdown("""
        <div class="hero">
            <div class="hero-eyebrow">🕉️ Vedic Sanskrit Resource</div>
            <div class="hero-verse">अग्निमीळे पुरोहितं यज्ञस्य देवमृत्विजम्</div>
            <div class="hero-rule"></div>
            <div class="hero-iast">agnimīḷe purohitaṃ yajñasya devam ṛtvijam</div>
            <div class="hero-cite">RV 1.1.1 · the first words of the Ṛgveda</div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown("""
            <div class="lesson-container">
            <div class="eyebrow">Why this project exists</div>
            <p>
            The primary Vedic corpus — the <b>Ṛgveda</b>, the <b>Atharvaveda (Śaunaka)</b>, both
            Yajurveda saṃhitās (<b>Vājasaneyi / Śukla</b> and <b>Taittirīya / Kṛṣṇa</b>), and the
            <b>Aitareya</b>, <b>Pañcaviṃśa</b>, and <b>Śatapatha Brāhmaṇas</b> — holds thousands of
            years of cosmological, historical, and ritual knowledge, locked inside dense Sanskrit
            scholarship that is hard to query, cross-reference, or reason over without years of
            specialist training.
            </p>
            <p>
            Existing English translations reflect the interpretive biases of nineteenth- and twentieth-century
            scholars, or any other translator-bias. This system <b>neutralises translator bias</b> by working directly from the original
            Sanskrit and using an LLM to generate translations grounded in Vedic grammar texts
            (Macdonell, Monier-Williams) rather than inheriting prior translators' readings.
            It makes the corpus queryable in plain English or Devanagari, with answers cited to source passages. It's backed by a dynamic Knowledge Graph that parses relationships, lineages, and geography across the corpus (Ṛgveda, Atharvaveda, both Yajurveda saṃhitās, and the Brāhmaṇas). The graph self-builds with use — so the more you search, the smarter it gets; 
                        e.g., the RAG learnt from the corpus that Trasadasyu was an Ikshvaku King, despite Puranas are not in the corpus.
            </p>

            <h4>🧠 How it works</h4>
            <ul>
                <li>📜 <b>Multi-corpus RAG</b> — searches the Ṛgveda (all 10 maṇḍalas), Atharvaveda,
                    both Yajurveda saṃhitās (VS, TS), and the AB, PB &amp; SB Brāhmaṇas simultaneously</li>
                <li>🕸️ <b>Self-building Knowledge Graph</b> — every query extracts kinship, lineage, geographic, and
                    social-role facts into a growing graph; later queries benefit from prior ones</li>
                <li>📖 <b>Monier-Williams integration</b> — 176 000+ Sanskrit concepts looked up in real time</li>
                <li>🔤 <b>Devanagari-aware retrieval</b> — queries transliterate automatically to find Sanskrit terms
                    even when you type in English</li>
                <li>🎯 <b>Agentic multi-step reasoning</b> — the system plans, retrieves, synthesises, and cites</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            # ── "Designed for" — in the slot the sample verse used to occupy ──
            st.markdown("""
            <div class="panel designed-for">
            <div class="eyebrow">🎓 Designed for</div>
            <div class="row"><div class="ic">📜</div><div class="tx">Scholars and students of Vedic literature</div></div>
            <div class="row"><div class="ic">🔤</div><div class="tx">Anyone curious about Vedic history, genealogy, and geography</div></div>
            <div class="row"><div class="ic">🧠</div><div class="tx">Researchers who want cited, corpus-grounded answers — not Wikipedia summaries</div></div>
            </div>
            """, unsafe_allow_html=True)

            # ── Complete corpus list (all indexed texts) ──
            st.markdown("""
            <div class="panel">
            <div class="eyebrow">📚 The corpus</div>
            <div class="corpus-group">Saṃhitās</div>
            <div class="corpus-card"><span class="abbr">RV</span><span class="name">Ṛgveda <small>· all 10 maṇḍalas</small></span></div>
            <div class="corpus-card"><span class="abbr">AVŚ</span><span class="name">Atharvaveda <small>· Śaunaka, 20 kāṇḍas</small></span></div>
            <div class="corpus-card"><span class="abbr">VS</span><span class="name">Vājasaneyi <small>· Śukla Yajurveda</small></span></div>
            <div class="corpus-card"><span class="abbr">TS</span><span class="name">Taittirīya <small>· Kṛṣṇa Yajurveda, 7 kāṇḍas</small></span></div>
            <div class="corpus-group">Brāhmaṇas</div>
            <div class="corpus-card"><span class="abbr">AB</span><span class="name">Aitareya <small>· complete</small></span></div>
            <div class="corpus-card"><span class="abbr">PB</span><span class="name">Pañcaviṃśa <small>· complete</small></span></div>
            <div class="corpus-card"><span class="abbr">SB</span><span class="name">Śatapatha <small>· Mādhyandina</small></span></div>
            </div>
            """, unsafe_allow_html=True)

        # ── Full-width chat section ────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 💬 Research the corpus")

        # Example question buttons — clicking one fires it immediately
        if st.session_state.initialized:
            st.markdown("**Try an example:**")
            example_cols = st.columns(4)
            example_questions = [
                "Who is Sudas?",
                "How does the flow of Sarasvati compare between early to later Vedic periods?",
                "What dynasty does Trasadasyu belong to?",
                "What type of houses are described in the corpus?",
            ]
            for col, q in zip(example_cols, example_questions):
                with col:
                    if st.button(q, key=f"ex_{hash(q)}", use_container_width=True):
                        self.ask_tutor(q, mode="conversation")
                        st.rerun()

        # Conversation history
        if st.session_state.chat_history:
            st.markdown("#### 📜 Conversation")
            history_slice = st.session_state.chat_history[-10:]
            for i, msg in enumerate(history_slice):
                if msg["role"] == "user":
                    st.markdown(
                        f'<div class="student-message">👤 <b>You:</b> {msg["content"]}</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f'<div class="tutor-message">🧑‍🏫 <b>Resource:</b> {msg["content"]}</div>',
                        unsafe_allow_html=True
                    )
                    # Per-answer export buttons
                    preceding_q = next(
                        (history_slice[j]["content"] for j in range(i - 1, -1, -1)
                         if history_slice[j]["role"] == "user"),
                        ""
                    )
                    self._render_answer_export(preceding_q, msg["content"], f"home_{i}")

        # Input row
        placeholder_text = (
            "Type your question in English…"
            if st.session_state.input_language == "English"
            else "देवनागरी में प्रश्न लिखें…"
        )
        user_input = st.text_area(
            "Your question:",
            placeholder=placeholder_text,
            key="chat_input",
            height=90
        )

        col_send, col_clear = st.columns([2, 1])

        with col_send:
            if st.button("📨 Send", key="send_chat", use_container_width=True):
                if user_input and st.session_state.initialized:
                    self.ask_tutor(user_input, mode="conversation")
                    st.rerun()
                elif not st.session_state.initialized:
                    st.warning("⚠️ Initialize the resource first (sidebar).")
                else:
                    st.warning("⚠️ Please type a question first.")

        with col_clear:
            if st.button("🗑️ Clear", key="clear_chat", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()

        # ── Subtle getting-started note (kept at the bottom, out of the way) ──
        st.markdown(
            '<div class="getstarted-note">🚀 By default Gemini LLM loads automatically — just type a question above. '
            'Use the sidebar only to switch the model (Ollama, Groq) or change the query language.</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            '<a href="https://www.buymeacoffee.com/shiv.tewari" target="_blank" '
            'class="bmc-btn">☕ Buy me a Soma (coffee)</a>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="getstarted-note">A personally-funded research preview — '
            'if it helps your study, a coffee keeps the servers and APIs running. 🙏</div>',
            unsafe_allow_html=True
        )

    def render_grammar_module(self):
        """Render grammar learning module."""
        st.title("📖 Grammar Basics (व्याकरण)")

        topic = st.selectbox(
            "Choose a topic:",
            ["Sandhi (संधि)", "Vibhakti (विभक्ति)", "Dhatu (धातु)", "All Topics"]
        )

        if st.button("📚 Start Lesson", key="grammar_btn"):
            queries = {
                "Sandhi (संधि)": "Teach me Sandhi (संधि) rules in Vedic Sanskrit with examples from Rigveda. Show rules in Devanagari and explain in Hindi when helpful.",
                "Vibhakti (विभक्ति)": "Explain Vibhakti (विभक्ति) case endings in Sanskrit. Show a table with Devanagari examples and compare with Hindi.",
                "Dhatu (धातु)": "Teach common Dhatu (धातु) verb roots in Vedic Sanskrit with conjugation examples in Devanagari.",
                "All Topics": "Give me a comprehensive grammar refresher covering Sandhi, Vibhakti, and Dhatu with Devanagari examples."
            }

            with st.container():
                response = self.ask_tutor(queries[topic], mode="grammar")
                st.markdown(f'<div class="tutor-message">{response}</div>', unsafe_allow_html=True)

    def render_vocabulary_module(self):
        """Render vocabulary building module."""
        st.title("📚 Vocabulary Builder (शब्दकोश)")

        category = st.selectbox(
            "Choose a category:",
            ["देवता (Deities)", "यज्ञ (Ritual)", "प्रकृति (Nature)", "Common Verbs & Adjectives"]
        )

        if st.button("📖 Learn Words", key="vocab_btn"):
            queries = {
                "देवता (Deities)": "Teach me vocabulary for Vedic deities (देवता) like Agni, Indra, Soma. Show words in Devanagari with Hindi and English meanings.",
                "यज्ञ (Ritual)": "Teach me Vedic ritual vocabulary (यज्ञ) with Devanagari, IAST, and Hindi meanings.",
                "प्रकृति (Nature)": "Teach me nature vocabulary (प्रकृति) - rivers, mountains, seasons - in Devanagari with examples from Vedas.",
                "Common Verbs & Adjectives": "Teach me 10 common Vedic Sanskrit verbs and adjectives in Devanagari with usage examples."
            }

            with st.container():
                response = self.ask_tutor(queries[category], mode="vocabulary")
                st.markdown(f'<div class="tutor-message">{response}</div>', unsafe_allow_html=True)

                # Extract words (simple parsing)
                if "learned" not in st.session_state:
                    st.session_state.learned_words.extend([category])

    # (corpus prefix in the danda, detection regex, local_store file, n levels)
    _NONRV_CORPORA = [
        ("AVŚ", r'\b(av[sś]?|atharva\w*)\b', "avs/avs.md", 3),
        ("VS",  r'\b(vs|vajasaneyi\w*)\b',   "yv/yv.md",  2),
        ("TS",  r'\b(ts|taittir\w*)\b',      "ts/ts.md",  4),
    ]
    _NONRV_MAX_CTX = 30   # cap section context (VS/TS sections can be large)

    def _lookup_nonrv_verse(self, verse_ref: str):
        """Resolve an AVŚ / VS / TS citation directly from its local_store file.

        Markers carry the corpus prefix and are unpadded, e.g. `॥ AVŚ 5.22.1 ॥`,
        `॥ VS 1.1 ॥`, `॥ TS 1.1.1.1 ॥`. The context group is everything sharing the
        citation prefix minus the final (verse) component — the hymn for AVŚ, the
        adhyāya for VS, the anuvāka for TS. Returns the same dict shape as the RV
        lookup, or None (so the RV path / RAG fallback runs).
        """
        import re as _re
        from src.utils.anukramani import get_hymn_anukramani
        low = verse_ref.lower().replace("ṛ", "r").replace("ś", "s")
        for prefix, pat, relpath, levels in self._NONRV_CORPORA:
            if not _re.search(pat, low):
                continue
            nums = _re.findall(r'\d+', verse_ref)
            if not (levels - 1 <= len(nums) <= levels):
                return None
            f = Path(LOCAL_FOLDER) / relpath
            if not f.exists():
                return None
            lines = f.read_text(encoding="utf-8").splitlines()
            group_path = ".".join(nums[:levels - 1])
            group_marker = f"॥ {prefix} {group_path}."
            section = [ln.strip() for ln in lines if group_marker in ln]
            if not section:
                return None
            if len(nums) == levels:
                vm = f"॥ {prefix} {'.'.join(nums)} ॥"
                focus = [ln.strip() for ln in lines if vm in ln]
                if not focus:
                    return None
                citation = f"{prefix} {'.'.join(nums)}"
            else:
                focus = section
                citation = f"{prefix} {group_path} (whole section)"
            # Cap large sections to a window around the focus verse.
            if len(section) > self._NONRV_MAX_CTX and len(nums) == levels:
                try:
                    fi = section.index(focus[0])
                except ValueError:
                    fi = 0
                lo = max(0, fi - self._NONRV_MAX_CTX // 2)
                section = section[lo:lo + self._NONRV_MAX_CTX]
            hymn_id = f"{prefix} {group_path}"
            anukr = get_hymn_anukramani(hymn_id)
            return {
                "corpus": prefix, "mandala": None, "sukta": None, "verse": None,
                "citation": citation,
                "verses": focus, "text": "\n".join(focus),
                "sukta_verses": section, "sukta_text": "\n".join(section),
                "sukta_citation": f"{prefix} {group_path} ({len(section)} verses shown)",
                "anukramani": anukr,
                "kg_entities": (anukr or {}).get("entities"),
            }
        return None

    def _lookup_verse_text(self, verse_ref: str):
        """Look up the exact Devanagari text of a Rigveda verse (or whole sūkta)
        directly from the formatted corpus in local_store.

        Returns a dict {mandala, sukta, verse, citation, verses[], text} or None
        when the reference can't be parsed / isn't a Rigveda verse present locally
        (in which case the caller falls back to ordinary RAG).
        """
        import re as _re
        # Non-RV corpora (AVŚ / VS / TS) are resolved first, from their own files.
        nonrv = self._lookup_nonrv_verse(verse_ref)
        if nonrv:
            return nonrv
        s = verse_ref.lower().replace("ṛ", "r")
        # Skip if another corpus is explicitly named — this RV branch is RV-only.
        if _re.search(r'\b(ts|vs|sb|ab|pb|av|avs|avś|taittir|vajasan|shatapatha|'
                      r'aitareya|pancavim|atharva)\b', s):
            return None
        # "Mandala 10 Sukta 60 (verse 1)"  or  "RV 10.60.1" / "10.060.01" / "RV 10.60"
        m = _re.search(r'mandal\w*\s*(\d+)[,\s]+s[uuū]kt\w*\s*(\d+)'
                       r'(?:[,\s]+(?:verse|v|mantra)?\s*(\d+))?', s)
        if not m:
            m = _re.search(r'(?:rv|rgveda|rigveda)?\s*(\d{1,2})[.\s](\d{1,3})(?:[.\s](\d{1,3}))?', s)
        if not m:
            return None
        mand, sukta = int(m.group(1)), int(m.group(2))
        verse = int(m.group(3)) if m.group(3) else None
        if not (1 <= mand <= 10):
            return None
        f = Path(LOCAL_FOLDER) / f"r{mand:02d}" / f"r{mand:02d}.md"
        if not f.exists():
            return None
        lines = f.read_text(encoding="utf-8").splitlines()
        # Always gather the FULL sūkta — interpretation needs the surrounding
        # verses (relative pronouns, named referents) to resolve name-vs-epithet.
        prefix = f"॥ {mand}.{sukta:03d}."
        sukta_lines = [ln.strip() for ln in lines if prefix in ln]
        if not sukta_lines:
            return None
        if verse is not None:
            marker = f"॥ {mand}.{sukta:03d}.{verse:02d} ॥"
            focus = [ln.strip() for ln in lines if marker in ln]
            if not focus:
                return None
        else:
            focus = sukta_lines  # the user asked for the whole sūkta
        citation = (f"RV {mand}.{sukta:03d}.{verse:02d}" if verse is not None
                    else f"RV {mand}.{sukta:03d} (whole sūkta)")
        # Attach authoritative anukramaṇī metadata (ṛṣi/patron/theme + KG entities)
        # for this hymn, if we have a curated seed entry for it.
        anukramani = kg_entities = None
        try:
            from src.utils.anukramani import get_hymn_anukramani
            anukramani = get_hymn_anukramani(f"{mand}.{sukta:03d}")
            if anukramani:
                kg_entities = anukramani.get("entities")
        except Exception:
            pass
        return {
            "mandala": mand, "sukta": sukta, "verse": verse,
            "citation": citation,
            # focus verse(s) — these keys preserve the translation module's behavior
            "verses": focus, "text": "\n".join(focus),
            # full sūkta context (used by the home-chat grounding)
            "sukta_verses": sukta_lines,
            "sukta_text": "\n".join(sukta_lines),
            "sukta_citation": f"RV {mand}.{sukta:03d} (full sūkta, {len(sukta_lines)} verses)",
            # authoritative seed grounding (anukramaṇī + KG entity facts)
            "anukramani": anukramani,
            "kg_entities": kg_entities,
        }

    @staticmethod
    def _is_verse_followup(query: str) -> bool:
        """Heuristic: does this message continue the discussion of an already-pinned
        verse (so we keep grounding it), rather than start a fresh topic?
        Conservative — only continuity cues keep the pin alive."""
        q = query.lower()
        cues = (
            "this verse", "that verse", "the verse", "this line", "that line",
            "this hymn", "that hymn", "this reading", "your reading", "your interpretation",
            "you said", "you interpret", "why do you", "why did you", "how do you",
            "justif", "differ", "instead of", "epithet", "proper noun", "not a name",
            "same verse", "translate it", "interpret it", "its meaning", "the meaning",
            "word-by-word", "word by word", "sandhi", "grammar", " it ", " its ",
        )
        return any(c in q for c in cues)

    def render_translation_module(self):
        """Render verse translation module."""
        st.title("🔤 Verse Translation (अनुवाद)")

        st.info("💡 **New!** Click audio player to hear verses pronounced correctly")

        st.markdown("### Choose a verse to translate:")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Beginner Verses:**")
            verse_ref = None

            if st.button("RV 1.1.1 (Agni Invocation)", key="rv111"):
                verse_ref = "RV 1.1.1"
                st.session_state.selected_verse = "अग्निमीळे पुरोहितं यज्ञस्य देवमृत्विजम्"
            elif st.button("RV 3.62.10 (Gayatri Mantra)", key="rv36210"):
                verse_ref = "RV 3.62.10"
                st.session_state.selected_verse = "तत्सवितुर्वरेण्यं भर्गो देवस्य धीमहि धियो यो नः प्रचोदयात्"

        with col2:
            st.markdown("**Or enter your own:**")
            custom_verse = st.text_input("Verse reference (e.g., RV 1.32.1):")
            if st.button("Translate Custom Verse", key="custom_trans"):
                verse_ref = custom_verse
                st.session_state.selected_verse = None

        if verse_ref:
            # Look the exact verse up directly from the corpus so interpretation
            # never depends on semantic retrieval surfacing it.
            verse_data = self._lookup_verse_text(verse_ref)

            pinned = None
            if verse_data:
                # The verse text, full sūkta, and anukramaṇī all travel via the
                # pinned-verse channel (pinned=verse_data) — NOT crammed into an
                # English instruction. This stops the agent from treating the
                # instruction itself as a phrase to translate. The query is a
                # short, clean format request only.
                cite = verse_data["citation"]
                pinned = verse_data
                query = (
                    f"Give a full scholarly translation and interpretation of the focus "
                    f"verse {cite}: 1) Devanagari (as given), 2) IAST, 3) word-by-word with "
                    f"sandhi, 4) grammar, 5) Hindi translation, 6) English translation, "
                    f"7) interpretive context (ṛṣi, devatā, theme)."
                )
                # Drive the audio player from the looked-up text (works for ANY verse,
                # not just the two hardcoded beginner mantras). Strip the numeric
                # ॥ N.NNN.NN ॥ end-markers so TTS doesn't read them as digits.
                import re as _re
                clean = _re.sub(r'॥\s*\d+\.\d+\.\d+\s*॥', '॥', verse_data["text"]).strip()
                st.session_state.selected_verse = clean
                st.caption(f"📖 Loaded {cite} directly from the corpus "
                           f"({len(verse_data['verses'])} verse line(s)).")
            else:
                # Not a local RV verse — fall back to ordinary RAG behaviour.
                query = (
                    f"Help me translate {verse_ref}. Show: 1) Original in Devanagari, "
                    f"2) Word-by-word breakdown with sandhi, 3) Grammar analysis, "
                    f"4) Hindi translation, 5) English translation, 6) Context."
                )

            with st.container():
                response = self.ask_tutor(query, mode="translation", pinned_verse=pinned)
                st.markdown(f'<div class="lesson-container">{response}</div>', unsafe_allow_html=True)

                # Per-translation export buttons (.md + .docx), same as the chat window
                export_label = verse_data["citation"] if verse_data else verse_ref
                self._render_answer_export(
                    f"Verse translation — {export_label}",
                    response,
                    f"trans_{abs(hash(verse_ref))}",
                )

                # If we have the verse text, provide audio
                if hasattr(st.session_state, 'selected_verse') and st.session_state.selected_verse:
                    st.markdown("---")
                    st.markdown("### 🔊 Hear the Verse")

                    col1, col2 = st.columns([2, 1])
                    with col1:
                        self.render_devanagari(st.session_state.selected_verse, large=True)
                    with col2:
                        audio_bytes = self.text_to_speech(st.session_state.selected_verse, lang='hi')
                        if audio_bytes:
                            self.play_audio(audio_bytes, label="Play Mantra")

    def render_pronunciation_module(self):
        """Render pronunciation practice module."""
        st.title("🗣️ Pronunciation (उच्चारण)")

        st.info("💡 **Tip**: Click the audio player to hear the correct pronunciation!")

        word = st.text_input(
            "Enter a Sanskrit word (Devanagari or IAST):",
            placeholder="अग्नि or agni"
        )

        if st.button("🔊 Learn Pronunciation", key="pronun_btn") and word:
            # Display the word prominently
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown("### Word to Pronounce:")
                self.render_devanagari(word, large=True)

            with col2:
                st.markdown("### 🔊 Audio:")
                # Generate and play audio
                with st.spinner("Generating audio..."):
                    audio_bytes = self.text_to_speech(word, lang='hi')

                if audio_bytes:
                    self.play_audio(audio_bytes, label="Listen to pronunciation")
                    st.caption(f"✓ Audio ready ({len(word)} characters, {len(audio_bytes)} bytes)")
                else:
                    st.warning("⚠️ Could not generate audio. Check error message above.")

            # Get teaching explanation
            query = f"Teach me the correct pronunciation of '{word}'. Show: 1) Devanagari (if not already), 2) IAST transliteration, 3) Pronunciation guide, 4) Vowel lengths, 5) Tips for Hindi speakers."

            with st.container():
                st.markdown("### 📖 Pronunciation Guide:")
                response = self.ask_tutor(query, mode="pronunciation")
                st.markdown(f'<div class="tutor-message">{response}</div>', unsafe_allow_html=True)

        # Quick practice
        st.markdown("---")
        st.markdown("### Quick Practice")

        practice_words = ["अग्नि", "इन्द्र", "सोम", "वरुण", "यज्ञ"]
        col1, col2 = st.columns([3, 1])

        with col1:
            selected_word = st.selectbox("Practice with:", practice_words)

        with col2:
            st.write("")  # Spacing
            st.write("")  # Spacing
            if st.button("🔊", key="quick_audio", help="Hear pronunciation"):
                audio_bytes = self.text_to_speech(selected_word, lang='hi')
                if audio_bytes:
                    self.play_audio(audio_bytes)

        if st.button(f"📚 Learn: {selected_word}", key="practice_pronun"):
            # Display word and audio
            col1, col2 = st.columns([2, 1])

            with col1:
                self.render_devanagari(selected_word, large=True)

            with col2:
                st.markdown("### 🔊 Audio:")
                audio_bytes = self.text_to_speech(selected_word, lang='hi')
                if audio_bytes:
                    self.play_audio(audio_bytes)

            # Get explanation
            query = f"Teach pronunciation of {selected_word} with tips for Hindi speakers."
            st.markdown("### 📖 Explanation:")
            response = self.ask_tutor(query, mode="pronunciation")
            st.markdown(f'<div class="tutor-message">{response}</div>', unsafe_allow_html=True)

    def render_quiz_module(self):
        """Render interactive quiz."""
        st.title("🎯 Quiz Mode (परीक्षा)")

        difficulty = st.select_slider(
            "Difficulty Level:",
            options=["Beginner", "Intermediate", "Advanced"]
        )

        if st.button("📝 Generate Quiz Question", key="quiz_btn"):
            query = f"Create a {difficulty.lower()}-level Sanskrit quiz question. Make it multiple choice. Include the answer explanation with Devanagari examples."

            with st.container():
                response = self.ask_tutor(query, mode="quiz")
                st.markdown(f'<div class="quiz-card">{response}</div>', unsafe_allow_html=True)

                # Simple answer tracking
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("✓ Got it right!", key="correct_ans"):
                        st.session_state.quiz_score["correct"] += 1
                        st.session_state.quiz_score["total"] += 1
                        st.success("बहुत अच्छा! (Very good!)")
                        st.rerun()

                with col2:
                    if st.button("✗ Got it wrong", key="wrong_ans"):
                        st.session_state.quiz_score["total"] += 1
                        st.info("कोई बात नहीं! (No worries!) Keep learning!")
                        st.rerun()

    def render_chat_module(self):
        """Render free conversation / Q&A module."""
        st.title("💬 Chat Mode (बातचीत)")
        st.caption(
            "Ask anything about Vedic texts. "
            "Answers are grounded in RV, SB, AB, PB, VS, and TS with citations. "
            "Query language can be changed in the sidebar."
        )

        # ── Conversation history ──────────────────────────────────────────────
        if st.session_state.chat_history:
            st.markdown("#### 📜 Conversation")
            chat_slice = st.session_state.chat_history[-10:]
            for i, msg in enumerate(chat_slice):
                if msg["role"] == "user":
                    st.markdown(
                        f'<div class="student-message">👤 <b>You:</b> {msg["content"]}</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f'<div class="tutor-message">🧑‍🏫 <b>Resource:</b> {msg["content"]}</div>',
                        unsafe_allow_html=True
                    )
                    preceding_q = next(
                        (chat_slice[j]["content"] for j in range(i - 1, -1, -1)
                         if chat_slice[j]["role"] == "user"),
                        ""
                    )
                    self._render_answer_export(preceding_q, msg["content"], f"chat_{i}")

        # ── Input area ────────────────────────────────────────────────────────
        placeholder_text = (
            "Type in English…"
            if st.session_state.input_language == "English"
            else "देवनागरी में टाइप करें…"
        )

        user_input = st.text_area(
            "Your question:",
            placeholder=placeholder_text,
            key="chat_input",
            height=100
        )

        # ── Action buttons ────────────────────────────────────────────────────
        col_send, col_clear = st.columns([2, 1])

        with col_send:
            if st.button("📨 Send", key="send_chat", use_container_width=True):
                if user_input:
                    self.ask_tutor(user_input, mode="conversation")
                    st.rerun()
                else:
                    st.warning("⚠️ Please type a question first!")

        with col_clear:
            if st.button("🗑️ Clear", key="clear_chat", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()

        # (per-answer export buttons are rendered inline above each assistant message)

    def run(self):
        """Main application loop."""
        # Count one visit per browser session (not per rerun); store for display.
        if "visit_count" not in st.session_state:
            try:
                from src.utils.visitor_counter import increment_visit_count
                st.session_state.visit_count = increment_visit_count()
            except Exception:
                st.session_state.visit_count = None

        self.render_sidebar()

        # Route to appropriate module (Home is always available, even pre-init)
        module = st.session_state.current_module

        if module == "🏠 Home":
            self.render_home()
            if not st.session_state.initialized:
                st.warning("👆 Initialize the resource in the sidebar to enable querying.")
        elif module == "📖 Grammar Basics":
            self.render_grammar_module()
        elif module == "📚 Vocabulary Builder":
            self.render_vocabulary_module()
        elif module == "🔤 Verse Translation":
            self.render_translation_module()
        elif module == "🗣️ Pronunciation":
            self.render_pronunciation_module()
        else:
            self.render_home()


def main():
    app = SanskritTutorApp()
    app.run()


if __name__ == "__main__":
    main()
