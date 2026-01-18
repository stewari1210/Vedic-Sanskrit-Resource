#!/usr/bin/env python3
"""
Vedic Sanskrit Learning Agent

An interactive tutor for learning Vedic Sanskrit, leveraging the existing RAG system
with Rigveda and Yajurveda texts. Designed for learners who:
- Have basic Sanskrit background (school-level)
- Are native Hindi speakers
- Want to read and understand Vedic texts

Features:
1. Grammar refresher (Sandhi, Vibhakti, Dhatu)
2. Vocabulary building with Hindi translations
3. Verse translation practice
4. Pronunciation and transliteration
5. Progressive difficulty levels
"""

import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import sys
# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import random
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from src.helper import project_root, logger
from src.config import LOCAL_FOLDER, COLLECTION_NAME, VECTORDB_FOLDER
from src.utils.index_files import create_qdrant_vector_store
from src.utils.retriever import create_retriever
from src.utils.final_block_rag import create_langgraph_app, run_rag_with_langgraph

from langchain_community.chat_models import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.settings import OLLAMA_BASE_URL, OLLAMA_MODEL, GEMINI_MODEL, Settings


# Learning Modules
MODULES = {
    "1": "Grammar Basics (Sandhi, Vibhakti, Dhatu)",
    "2": "Vocabulary Building (Common Vedic Words)",
    "3": "Verse Translation Practice",
    "4": "Pronunciation & Transliteration",
    "5": "Quiz Mode (Test Your Knowledge)",
    "6": "Free Conversation (Ask Anything)"
}


class VedicSanskritTutor:
    """Interactive Vedic Sanskrit learning assistant."""

    def __init__(self, rag_app, retriever, llm_provider="ollama", model_name="llama3.1:8b"):
        self.rag_app = rag_app
        self.retriever = retriever
        self.chat_history = []

        # Initialize LLM for teaching
        if llm_provider == "gemini":
            self.llm = ChatGoogleGenerativeAI(
                model=GEMINI_MODEL,
                temperature=0.7,
                timeout=180
            )
        else:
            self.llm = ChatOllama(
                base_url=OLLAMA_BASE_URL,
                model=model_name,  # Use the specified model
                temperature=0.7,
                timeout=180,
                num_predict=2048
            )

        self.user_level = "beginner"  # beginner, intermediate, advanced
        self.learned_words = set()

    def get_system_prompt(self, mode: str) -> str:
        """Get system prompt based on learning mode."""
        base = """You are a patient and knowledgeable Vedic Sanskrit tutor. Your student:
- Has studied Sanskrit in school but forgotten most of it
- Is a native Hindi speaker (use Hindi when helpful)
- Wants to read and understand Vedic texts (Rigveda, Yajurveda)

Teaching principles:
- Start simple, build gradually
- Use Hindi for explanations when it helps
- Connect to familiar Hindi words
- Provide examples from the Vedic corpus
- Be encouraging and patient
"""

        mode_specific = {
            "grammar": """
Focus on Vedic Sanskrit grammar:
1. Sandhi rules (explain with examples)
2. Vibhakti (case endings) - show patterns
3. Dhatu (verb roots) - common ones first
4. Provide mnemonic devices
5. Compare with Hindi when useful
""",
            "vocabulary": """
Teach Vedic Sanskrit vocabulary:
1. Start with common words in Vedas
2. Give Hindi/English meanings
3. Show usage in actual verses
4. Group by themes (देवता, यज्ञ, प्रकृति)
5. Create word families (धातु → शब्द)
""",
            "translation": """
Guide verse translation:
1. Break down the verse word-by-word
2. Identify sandhi, parse compounds
3. Explain grammatical forms
4. Provide word-for-word translation
5. Then give natural Hindi/English translation
6. Discuss cultural/philosophical context
""",
            "pronunciation": """
Teach Vedic pronunciation:
1. Explain IAST to Devanagari mapping
2. Show proper vowel lengths (ā, ī, ū)
3. Teach anusvāra, visarga rules
4. Accent marks in Vedic (udātta, anudātta)
5. Practice with actual mantras
""",
            "quiz": """
Quiz the student (adaptive difficulty):
1. Ask clear questions (multiple choice or fill-in-blank)
2. Provide hints if they struggle
3. Explain the answer thoroughly
4. Track progress, adjust difficulty
5. Be encouraging!
""",
            "conversation": """
Have a natural conversation about Sanskrit:
1. Answer any questions they have
2. Explain concepts thoroughly
3. Provide relevant examples from texts
4. Suggest learning paths
5. Be supportive and motivating
"""
        }

        return base + mode_specific.get(mode, mode_specific["conversation"])

    def grammar_lesson(self):
        """Interactive grammar lesson."""
        print("\n" + "="*60)
        print("📚 GRAMMAR REFRESHER")
        print("="*60)
        print("\nChoose a topic:")
        print("1. Sandhi (संधि) - Euphonic combinations")
        print("2. Vibhakti (विभक्ति) - Case endings")
        print("3. Dhatu (धातु) - Verb roots")
        print("4. All topics")

        choice = input("\nYour choice (1-4): ").strip()

        topics = {
            "1": "Teach me Sandhi rules in Vedic Sanskrit, with examples from Rigveda",
            "2": "Explain Vibhakti (case endings) in Sanskrit, compare with Hindi",
            "3": "Teach common Dhatu (verb roots) in Vedic Sanskrit",
            "4": "Give me a comprehensive grammar refresher covering Sandhi, Vibhakti, and Dhatu"
        }

        query = topics.get(choice, topics["4"])
        return self._ask_tutor(query, mode="grammar")

    def vocabulary_builder(self):
        """Build vocabulary with examples from corpus."""
        print("\n" + "="*60)
        print("📖 VOCABULARY BUILDER")
        print("="*60)
        print("\nChoose a category:")
        print("1. देवता (Deities) - Agni, Indra, Soma, etc.")
        print("2. यज्ञ (Ritual terms)")
        print("3. प्रकृति (Nature) - Rivers, mountains, seasons")
        print("4. Common verbs and adjectives")

        choice = input("\nYour choice (1-4): ").strip()

        topics = {
            "1": "Teach me vocabulary related to Vedic deities (देवता) with examples from Rigveda",
            "2": "Teach me vocabulary related to Vedic rituals (यज्ञ) with Hindi meanings",
            "3": "Teach me vocabulary related to nature (प्रकृति) - rivers, mountains, seasons",
            "4": "Teach me 10 common Vedic Sanskrit verbs and adjectives with usage examples"
        }

        query = topics.get(choice, topics["4"])
        return self._ask_tutor(query, mode="vocabulary")

    def translation_practice(self):
        """Practice translating verses."""
        print("\n" + "="*60)
        print("🔤 VERSE TRANSLATION PRACTICE")
        print("="*60)

        # Suggest some beginner-friendly verses
        print("\nSuggested verses for beginners:")
        print("1. RV 1.1.1 (Agni invocation - very famous)")
        print("2. RV 3.62.10 (Gayatri Mantra)")
        print("3. RV 10.90 (Purusha Sukta)")
        print("4. Enter your own verse reference")

        choice = input("\nYour choice (1-4): ").strip()

        if choice == "4":
            verse_ref = input("Enter verse reference (e.g., RV 1.32.1): ").strip()
        else:
            verses = {
                "1": "RV 1.1.1",
                "2": "RV 3.62.10",
                "3": "RV 10.90"
            }
            verse_ref = verses.get(choice, "RV 1.1.1")

        query = f"Help me translate {verse_ref}. Show the original Sanskrit, break it down word-by-word, explain grammar, and provide Hindi and English translations."
        return self._ask_tutor(query, mode="translation")

    def pronunciation_practice(self):
        """Practice pronunciation and transliteration."""
        print("\n" + "="*60)
        print("🗣️ PRONUNCIATION & TRANSLITERATION")
        print("="*60)

        word = input("\nEnter a Sanskrit word (Devanagari or IAST): ").strip()

        if not word:
            word = "अग्नि"  # Default example

        query = f"Teach me the correct pronunciation of '{word}'. Show both Devanagari and IAST, explain vowel lengths, and provide pronunciation tips."
        return self._ask_tutor(query, mode="pronunciation")

    def quiz_mode(self):
        """Interactive quiz."""
        print("\n" + "="*60)
        print("🎯 QUIZ MODE")
        print("="*60)
        print("\nChoose difficulty:")
        print("1. Beginner")
        print("2. Intermediate")
        print("3. Advanced")

        choice = input("\nYour choice (1-3): ").strip()

        levels = {
            "1": "beginner",
            "2": "intermediate",
            "3": "advanced"
        }

        level = levels.get(choice, "beginner")

        query = f"Give me a {level}-level Sanskrit quiz question. Make it multiple choice or fill-in-the-blank. Cover grammar, vocabulary, or translation."
        return self._ask_tutor(query, mode="quiz")

    def _ask_tutor(self, query: str, mode: str = "conversation") -> str:
        """Ask the tutor a question using RAG."""
        system_prompt = self.get_system_prompt(mode)

        # Use RAG to get relevant context from Vedic texts
        graph_state = {
            "question": query,
            "chat_history": self.chat_history,
            "documents": [],
            "answer": "",
            "enhanced_question": "",
            "is_follow_up": False,
            "reset_history": False,
            "regeneration_count": 0,
            "debug": False
        }

        try:
            result = run_rag_with_langgraph(graph_state, self.rag_app)

            if isinstance(result, dict):
                answer = result.get("answer", "")

                # Enhance with LLM for teaching
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=f"Context from Vedic texts:\n{answer}\n\nStudent's question: {query}\n\nProvide a clear, pedagogical explanation:")
                ]

                enhanced_answer = Settings.invoke_llm(self.llm, messages).content

                # Update chat history
                self.chat_history.append(HumanMessage(content=query))
                self.chat_history.append(HumanMessage(content=enhanced_answer))

                return enhanced_answer
            else:
                return str(result)

        except Exception as e:
            logger.error(f"Error in tutor: {e}")
            return f"Sorry, I encountered an error: {e}"

    def free_conversation(self):
        """Free-form conversation mode."""
        print("\n" + "="*60)
        print("💬 FREE CONVERSATION")
        print("="*60)
        print("Ask me anything about Vedic Sanskrit! (Type 'back' to return to menu)")

        while True:
            query = input("\n👤 You: ").strip()

            if query.lower() in ["back", "menu", "exit"]:
                break

            if not query:
                continue

            response = self._ask_tutor(query, mode="conversation")
            print(f"\n🧑‍🏫 Tutor: {response}")


def main():
    parser = argparse.ArgumentParser(description="Vedic Sanskrit Learning Agent")
    parser.add_argument("--llm", choices=["ollama", "gemini"], default="ollama",
                       help="LLM provider for teaching (default: ollama)")
    parser.add_argument("--model", type=str, default="llama3.1:8b",
                       help="Ollama model to use (default: llama3.1:8b). Try phi3.5:mini for faster responses!")
    args = parser.parse_args()

    print("\n" + "🕉️ "*20)
    print("    VEDIC SANSKRIT LEARNING AGENT")
    print("    नमस्ते! Welcome to your personalized Sanskrit tutor")
    print("🕉️ "*20)

    # Check if vector store exists
    vec_store_path = os.path.join(project_root, VECTORDB_FOLDER, COLLECTION_NAME)
    if not os.path.exists(vec_store_path):
        print("\n⚠️  Vector store not found. Please run cli_run.py first to index your texts.")
        return

    print("\n📚 Loading Vedic texts corpus...")
    try:
        vec_db, docs = create_qdrant_vector_store(force_recreate=False)
        retriever = create_retriever(vec_db, docs)
        rag_app = create_langgraph_app(retriever)
        print("✓ Corpus loaded successfully!")
    except Exception as e:
        logger.error(f"Failed to load corpus: {e}")
        print(f"❌ Error loading corpus: {e}")
        return

    # Initialize tutor
    tutor = VedicSanskritTutor(
        rag_app,
        retriever,
        llm_provider=args.llm,
        model_name=args.model if args.llm == "ollama" else None
    )

    if args.llm == "ollama":
        print(f"\n🤖 Using Ollama ({args.model}) as your tutor")
    else:
        print(f"\n🤖 Using {args.llm.upper()} as your tutor")

    print("\nWhat would you like to learn today?")

    while True:
        print("\n" + "="*60)
        print("LEARNING MODULES")
        print("="*60)
        for key, value in MODULES.items():
            print(f"{key}. {value}")
        print("0. Exit")

        choice = input("\nChoose a module (0-6): ").strip()

        if choice == "0":
            print("\n🙏 धन्यवाद! Keep practicing! शुभम् भवतु।")
            break
        elif choice == "1":
            tutor.grammar_lesson()
        elif choice == "2":
            tutor.vocabulary_builder()
        elif choice == "3":
            tutor.translation_practice()
        elif choice == "4":
            tutor.pronunciation_practice()
        elif choice == "5":
            tutor.quiz_mode()
        elif choice == "6":
            tutor.free_conversation()
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
