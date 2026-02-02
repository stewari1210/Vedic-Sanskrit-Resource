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


# Page configuration with Devanagari font support
st.set_page_config(
    page_title="🕉️ Vedic Sanskrit Resource",
    page_icon="🕉️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Devanagari fonts and styling
st.markdown("""
<style>
    /* Import Noto Sans Devanagari font */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;700&family=Noto+Serif+Devanagari:wght@400;700&display=swap');

    /* Devanagari text styling */
    .devanagari {
        font-family: 'Noto Serif Devanagari', serif;
        font-size: 1.5em;
        line-height: 1.8;
        color: #8B4513;
    }

    .devanagari-large {
        font-family: 'Noto Serif Devanagari', serif;
        font-size: 2em;
        line-height: 2;
        color: #8B4513;
        font-weight: 700;
    }

    /* Sanskrit transliteration */
    .sanskrit-iast {
        font-family: 'Times New Roman', serif;
        font-style: italic;
        color: #2F4F4F;
    }

    /* Module cards */
    .module-card {
        background: linear-gradient(135deg, #FFF8DC 0%, #F0E68C 100%);
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #FF6347;
        margin: 10px 0;
    }

    /* Lesson container */
    .lesson-container {
        background: #FFFAF0;
        padding: 20px;
        border-radius: 10px;
        border: 2px solid #DEB887;
        color: #000000;
    }

    .lesson-container h3, .lesson-container h4, .lesson-container p, .lesson-container li {
        color: #000000 !important;
    }

    /* Quiz card */
    .quiz-card {
        background: #F0FFF0;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #32CD32;
    }

    /* Progress bar custom */
    .progress-text {
        font-family: 'Noto Sans Devanagari', sans-serif;
        font-size: 0.9em;
        color: #696969;
    }

    /* Chat messages */
    .student-message {
        background: #E6F3FF;
        padding: 10px;
        border-radius: 8px;
        margin: 5px 0;
        color: #000000;
    }

    .tutor-message {
        background: #FFF5E6;
        padding: 10px;
        border-radius: 8px;
        margin: 5px 0;
        color: #000000;
    }

    /* Hide streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
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

    def ask_tutor(self, query: str, mode: str = "conversation") -> str:
        """Query the resource using Agentic RAG."""
        system_prompt = self.get_system_prompt(mode)

        try:
            # Use Agentic RAG system
            with st.spinner("🤖 Agent analyzing your question..."):
                logger.info(f"[FRONTEND] Processing query with Agentic RAG: {query}")
                result = run_agentic_rag(query)
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

            # Update chat history
            st.session_state.chat_history.append({"role": "user", "content": query})
            st.session_state.chat_history.append({"role": "assistant", "content": answer_text})

            return answer_text

        except Exception as e:
            logger.error(f"Error in resource: {e}")
            import traceback
            traceback.print_exc()
            return f"Sorry, I encountered an error: {e}"

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

            if st.button("🚀 Initialize Resource", key="init_button"):
                if self.setup_tutor(llm_provider, model_name):
                    st.success("✓ Resource ready!")
                    st.rerun()

            if st.session_state.initialized:
                st.success(f"✓ Using: {st.session_state.model_name}")

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
                    "🎯 Quiz Mode",
                    "💬 Chat Mode"
                ],
                key="module_selector"
            )

            st.session_state.current_module = module

            # Progress tracking
            st.markdown("---")
            st.subheader("📊 Progress")
            if st.session_state.learned_words:
                st.metric("Words Learned", len(st.session_state.learned_words))

            if st.session_state.quiz_score["total"] > 0:
                accuracy = (st.session_state.quiz_score["correct"] / st.session_state.quiz_score["total"]) * 100
                st.metric("Quiz Accuracy", f"{accuracy:.0f}%")
                st.progress(accuracy / 100)

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

    def render_home(self):
        """Render home page."""
        st.title("🕉️ Vedic Sanskrit Resource")

        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown("## स्वागतम्! Welcome!")

            st.markdown("""
            <div class="lesson-container">
            <h3>Your Vedic Sanskrit Resource 🤖</h3>
            <p>Access and understand Vedic texts with AI-powered agentic reasoning.</p>

            <h4>🧠 Agentic RAG System:</h4>
            <ul>
                <li>� <b>Multi-Step Reasoning</b> - Agent thinks through problems step-by-step</li>
                <li>📖 <b>Dictionary Lookup</b> - 19,000+ Sanskrit-English word mappings</li>
                <li>� <b>Grammar Analysis</b> - Retrieves declension and conjugation rules</li>
                <li>� <b>Corpus Examples</b> - Finds usage patterns from Rigveda & Yajurveda</li>
                <li>🎯 <b>Synthesis</b> - Combines all sources for accurate constructions</li>
            </ul>

            <h4>Perfect For:</h4>
            <ul>
                <li>✨ <b>"How do I say X in Sanskrit?"</b> - Construction queries</li>
                <li>📖 <b>Vocabulary & Grammar</b> - Learn word-by-word</li>
                <li>� <b>Verse Translation</b> - Understand Vedic texts</li>
                <li>💬 <b>Free Q&A</b> - Ask anything about Sanskrit!</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("### 🎓 Designed For:")
            st.info("""
            - 📖 Students who want to construct Sanskrit sentences
            - 🔤 Learners needing word-level translation and grammar
            - 📜 Anyone reading Rigveda and Yajurveda texts
            - 🧠 Those who want to see the AI's thinking process
            """)

        with col2:
            st.markdown("### 🕉️ Sample Verse")
            self.render_devanagari("अग्निमीळे पुरोहितं यज्ञस्य देवमृत्विजम्", large=True)
            st.markdown("*agnimīḷe purohitaṃ yajñasya devamṛtvijam*")
            st.caption("RV 1.1.1 - First verse of Rigveda")

            st.markdown("---")
            st.markdown("### 🚀 Get Started")
            st.markdown("""
            1. Click **Initialize Resource** in sidebar
            2. Choose a learning module
            3. Start learning!
            """)

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
            query = f"Help me translate {verse_ref}. Show: 1) Original in Devanagari, 2) Word-by-word breakdown with sandhi, 3) Grammar analysis, 4) Hindi translation, 5) English translation, 6) Context."

            with st.container():
                response = self.ask_tutor(query, mode="translation")
                st.markdown(f'<div class="lesson-container">{response}</div>', unsafe_allow_html=True)

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
        """Render free conversation module."""
        st.title("💬 Chat Mode (बातचीत)")

        st.markdown("Ask me anything about Vedic Sanskrit, Vedas, and Ramayana!")

        # Display chat history
        for msg in st.session_state.chat_history[-10:]:
            if msg["role"] == "user":
                st.markdown(f'<div class="student-message">👤 <b>You:</b> {msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="tutor-message">🧑‍🏫 <b>Resource:</b> {msg["content"]}</div>', unsafe_allow_html=True)

        # Chat input
        user_input = st.text_area(
            "Your question:",
            placeholder="Type in English, Hindi, or Devanagari...",
            key="chat_input"
        )

        if st.button("📨 Send", key="send_chat") and user_input:
            # Get response from tutor
            response = self.ask_tutor(user_input, mode="conversation")

            # Chat history is already updated in ask_tutor()
            # Just rerun to display it in the history above
            st.rerun()

    def run(self):
        """Main application loop."""
        self.render_sidebar()

        if not st.session_state.initialized:
            self.render_home()
            st.warning("👆 Please initialize the resource using the sidebar to start learning!")
            return

        # Route to appropriate module
        module = st.session_state.current_module

        if module == "🏠 Home":
            self.render_home()
        elif module == "📖 Grammar Basics":
            self.render_grammar_module()
        elif module == "📚 Vocabulary Builder":
            self.render_vocabulary_module()
        elif module == "🔤 Verse Translation":
            self.render_translation_module()
        elif module == "🗣️ Pronunciation":
            self.render_pronunciation_module()
        elif module == "🎯 Quiz Mode":
            self.render_quiz_module()
        elif module == "💬 Chat Mode":
            self.render_chat_module()


def main():
    app = SanskritTutorApp()
    app.run()


if __name__ == "__main__":
    main()
