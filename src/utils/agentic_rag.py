"""
Agentic RAG System for Sanskrit Construction
Implements Gemini's 3-step approach: Dictionary → Grammar → Corpus

Architecture:
    User Query → Agent (Planner)
                   ↓
              [Decides tools needed]
                   ↓
         Tool 1: Dictionary Lookup (Monier-Williams)
         Tool 2: Grammar Rules (Macdonell)
         Tool 3: Corpus Examples (RV/YV)
                   ↓
              Agent (Synthesizer)
                   ↓
            Sanskrit Construction
"""

from typing import TypedDict, List, Annotated, Literal, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.documents import Document
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
import operator
from src.helper import logger
from src.settings import Settings
from src.utils.citation_enhancer import (
    enhance_corpus_results_with_citations,
    create_enhanced_citations_list,
    CitationFormatter
)
from src.utils.devanagari_lexical import query_terms
import re

# Knowledge Graph — lazy import so KG failures never break RAG
try:
    from src.utils.vedic_kg import get_entity_context, extract_and_store_facts
    KG_ENABLED = True
except Exception as _kg_err:
    KG_ENABLED = False
    logger.warning(f"🕸️  KG disabled: {_kg_err}")

llm = Settings.get_llm()

# How many retrieved docs reach the synthesis LLM. Was 5 — starved the
# synthesizer (Gemini Flash has ~1M-token context; 12 docs ≈ a few thousand
# tokens). Raise further once AV/YV/Brahmana layers are indexed.
SYNTHESIS_DOC_BUDGET = 12

# Global shared vector store to avoid Qdrant lock issues
_SHARED_VECTOR_STORE = None
_SHARED_DOCS = None


def extract_source_texts(corpus_docs: List[Document]) -> str:
    """
    Extract unique source texts from corpus documents.
    Returns a formatted string like 'Rigveda, Pancavimsa Brahmana, and Satapatha Brahmana'
    """
    sources = set()
    for doc in corpus_docs:
        source = doc.metadata.get("source", "")
        if source:
            # Normalize source names
            if "rigveda" in source.lower():
                sources.add("Rigveda")
            elif "yajurveda" in source.lower():
                sources.add("Yajurveda")
            elif "pancavimsa" in source.lower() or "pancavamsa" in source.lower():
                sources.add("Pañcaviṃśa Brāhmaṇa")
            elif "satapatha" in source.lower():
                sources.add("Śatapatha Brāhmaṇa")
            elif "macdonell" in source.lower():
                sources.add("Macdonell's Vedic Grammar")
            elif "ramayana" in source.lower():
                sources.add("Ramayana")
            else:
                # Clean up generic source names
                clean = source.replace("_", " ").title()
                sources.add(clean)
    
    if not sources:
        return "the Vedic corpus"
    
    sources_list = sorted(list(sources))
    if len(sources_list) == 1:
        return sources_list[0]
    elif len(sources_list) == 2:
        return f"{sources_list[0]} and {sources_list[1]}"
    else:
        return ", ".join(sources_list[:-1]) + f", and {sources_list[-1]}"

def set_shared_vector_store(vec_db, docs):
    """Set the shared vector store instance from the frontend."""
    global _SHARED_VECTOR_STORE, _SHARED_DOCS
    _SHARED_VECTOR_STORE = vec_db
    _SHARED_DOCS = docs
    logger.info("[AGENTIC] Shared vector store configured")

# Shared retriever with proper noun variants
_SHARED_RETRIEVER = None

def get_shared_retriever():
    """Get the shared retriever with proper noun variants, or create if not set."""
    global _SHARED_RETRIEVER, _SHARED_VECTOR_STORE, _SHARED_DOCS
    if _SHARED_RETRIEVER is None:
        logger.info("[AGENTIC] Creating shared retriever with proper noun variants")
        if _SHARED_VECTOR_STORE is None:
            from src.utils.index_files import create_qdrant_vector_store
            _SHARED_VECTOR_STORE, _SHARED_DOCS = create_qdrant_vector_store(force_recreate=False)

        # Use the full HybridRetriever with proper noun variants
        from src.utils.retriever import create_retriever
        _SHARED_RETRIEVER = create_retriever(_SHARED_VECTOR_STORE, _SHARED_DOCS, top_n=5)

    return _SHARED_RETRIEVER


class AgentState(TypedDict):
    """State for the agentic RAG system"""
    question: str
    input_language: str  # ✅ NEW: "English" or "Devanagari"
    pinned_verse: Optional[dict]  # exact verse text when the query cites one (e.g. RV 10.60.2)
    query_type: str  # "construction" | "grammar" | "factual"

    # Extracted information
    english_words: List[str]  # Words to translate ["I", "want", "milk"]
    sanskrit_words: dict  # Dictionary results: {"milk": ["payas", "dugdha"]}
    grammar_rules: List[Document]  # Grammar rules from Macdonell
    corpus_examples: List[Document]  # Usage examples from RV/YV

    # Agent decisions
    messages: Annotated[List, operator.add]  # Agent's reasoning chain
    next_action: str  # What tool to use next

    # Final output
    answer: dict
    construction_complete: bool


# ============================================================
# TOOL 1: DICTIONARY LOOKUP (Enhanced with Monier-Williams)
# ============================================================

# Load cleaned Monier-Williams dictionary (10,635 high-quality entries)
_MONIER_WILLIAMS_DICT = None

def load_monier_williams():
    """Lazy load cleaned Monier-Williams dictionary"""
    global _MONIER_WILLIAMS_DICT
    if _MONIER_WILLIAMS_DICT is None:
        import json
        import os
        # Try cleaned dictionary first, fall back to original if not found
        dict_path = os.path.join(os.path.dirname(__file__), '..', '..', 'sanskrit_dictionary_cleaned.json')
        if not os.path.exists(dict_path):
            dict_path = os.path.join(os.path.dirname(__file__), '..', '..', 'sanskrit_dictionary.json')
            logger.warning(f"[DICTIONARY] Using original dictionary (may contain OCR errors)")

        try:
            with open(dict_path, 'r', encoding='utf-8') as f:
                _MONIER_WILLIAMS_DICT = json.load(f)
            logger.info(f"[DICTIONARY] Loaded Monier-Williams: {len(_MONIER_WILLIAMS_DICT)} entries from {os.path.basename(dict_path)}")
        except FileNotFoundError:
            logger.warning(f"[DICTIONARY] Monier-Williams not found at {dict_path}, using BASIC_LEXICON only")
            _MONIER_WILLIAMS_DICT = {}
    return _MONIER_WILLIAMS_DICT

@tool
def dictionary_lookup(word: str) -> str:
    """
    Look up an English word in Sanskrit dictionaries (19K+ entries from Monier-Williams).
    Returns Sanskrit equivalents with grammatical info.

    Args:
        word: English word to translate (e.g., "milk", "want", "I")

    Returns:
        Sanskrit equivalents with grammar notes
    """
    word_lower = word.lower()

    # Load Monier-Williams dictionary
    monier_dict = load_monier_williams()

    # Check Monier-Williams dictionary first (most comprehensive)
    if word_lower in monier_dict:
        sanskrit_terms = monier_dict[word_lower]
        # Filter out noise (terms with numbers or strange chars)
        clean_terms = [t for t in sanskrit_terms if not any(c.isdigit() for c in t) and len(t) > 2]

        if clean_terms:
            logger.info(f"[DICTIONARY] '{word}' → {clean_terms[:3]} (Monier-Williams)")
            return f"Sanskrit for '{word}': {', '.join(clean_terms[:5])}"

    # Fallback: not found
    logger.warning(f"[DICTIONARY] '{word}' not found in dictionary")
    return f"'{word}' not found in dictionary. Try a synonym or simpler word."


@tool
def grammar_rules_search(sanskrit_word: str, context: str = "") -> str:
    """
    Search grammar texts (Macdonell) for declension/conjugation rules.

    Args:
        sanskrit_word: Sanskrit word or root to get grammar for
        context: Additional context (e.g., "accusative case", "present tense")

    Returns:
        Grammar rules and tables
    """
    # TODO: Create separate grammar-only index
    # For now, search in main corpus with grammar filter
    logger.info(f"[GRAMMAR] Searching rules for '{sanskrit_word}' (context: {context})")

    query = f"{sanskrit_word} {context} declension conjugation grammar"

    try:
        # Use shared retriever with proper noun variants
        retriever = get_shared_retriever()

        grammar_docs = retriever.invoke(query)

        # Filter for grammar content (contains tables, rules, endings)
        grammar_indicators = ["declension", "conjugation", "case", "ending", "vibhakti", "suffix"]
        filtered = [doc for doc in grammar_docs if any(ind in doc.page_content.lower() for ind in grammar_indicators)]

        if filtered:
            result = "\n\n".join([doc.page_content[:500] for doc in filtered[:2]])
            logger.info(f"[GRAMMAR] Found {len(filtered)} grammar references")
            return result
        else:
            return "No specific grammar rules found. Using general patterns."

    except Exception as e:
        logger.error(f"[GRAMMAR] Error: {e}")
        return f"Grammar lookup failed: {e}"


@tool
def corpus_examples_search(sanskrit_terms: str, pattern: str = "") -> str:
    """
    Search Vedic corpus (RV/YV) for usage examples or factual information.

    Args:
        sanskrit_terms: Sanskrit words OR factual question to search for
        pattern: Sentence pattern to match (e.g., "sentence", "") - empty for factual queries

    Returns:
        Example sentences or relevant corpus passages (raw, without formatting)
    """
    logger.info(f"[CORPUS] Searching for '{sanskrit_terms}' (pattern: {pattern})")

    # If pattern is empty, treat as factual query - use direct search
    # Otherwise, treat as example search - append context
    if pattern:
        query = f"{sanskrit_terms} {pattern} example sentence usage"
    else:
        # For factual queries, use the question directly without modification
        query = sanskrit_terms

    try:
        # Use shared retriever with proper noun variants
        retriever = get_shared_retriever()

        examples = retriever.invoke(query)

        if examples:
            # Return raw document content (NO citation formatting here)
            # Citation formatting happens later in synthesize_answer_node
            result = "\n\n".join([doc.page_content for doc in examples[:5]])
            logger.info(f"[CORPUS] Found {len(examples)} passages (raw content)")
            return result
        else:
            return "No relevant passages found in corpus."

    except Exception as e:
        logger.error(f"[CORPUS] Error: {e}")
        return f"Corpus search failed: {e}"


# ============================================================
# AGENT NODES
# ============================================================

def classify_and_plan_node(state: AgentState):
    """
    Agent analyzes the query and plans which tools to use.
    """
    logger.info("---AGENT: PLANNING---")
    question = state["question"]

    # Classify query type
    construction_keywords = [
        "how do i say", "translate", "in sanskrit", "sanskrit for",
        "how to say", "say in sanskrit", "sanskrit word for",
        "construct", "write in sanskrit"
    ]
    grammar_keywords = ["explain", "what is the rule", "how does", "declension", "conjugation"]

    is_construction = any(kw in question.lower() for kw in construction_keywords)
    is_grammar = any(kw in question.lower() for kw in grammar_keywords)

    # A pinned verse always means "interpret THIS verse" — never an English→Sanskrit
    # construction. Force factual so the instruction text (e.g. "translate RV 10.60.2")
    # is NOT itself translated, and the pinned-verse synthesis branch is reached.
    if state.get("pinned_verse"):
        query_type = "factual"
        logger.info("[AGENT] Query type: FACTUAL (pinned verse — interpretation mode)")
    elif is_construction:
        query_type = "construction"
        logger.info("[AGENT] Query type: CONSTRUCTION (need dictionary + grammar + examples)")
    elif is_grammar:
        query_type = "grammar"
        logger.info("[AGENT] Query type: GRAMMAR (need grammar rules + examples)")
    else:
        query_type = "factual"
        logger.info("[AGENT] Query type: FACTUAL (use standard retrieval)")

    # Extract words to translate (for construction queries)
    english_words = []
    if is_construction:
        # Extract text inside quotes first (e.g., 'I want milk', "give me water")
        quoted = re.findall(r"['\"]([^'\"]+)['\"]", question)
        if quoted:
            # Get words from quoted text
            text = quoted[0].lower()
        else:
            # Try to extract the phrase being translated
            # Patterns: "translate X", "say X in sanskrit", "X in sanskrit"
            patterns = [
                r"translate\s+([^?]+?)(?:\s+in|\s+to|$)",
                r"say\s+([^?]+?)(?:\s+in|$)",
                r"how do i say\s+([^?]+?)(?:\s+in|$)",
                r"sanskrit for\s+([^?]+?)(?:\?|$)",
            ]

            text = None
            for pattern in patterns:
                match = re.search(pattern, question.lower())
                if match:
                    text = match.group(1).strip()
                    break

            if not text:
                # Fallback: use whole question
                text = question.lower()

        # Remove punctuation and split
        words = re.sub(r'[^\w\s]', ' ', text).split()

        # Remove common instruction words (but keep content words like "how", "you", "are")
        stop_words = {
            "do", "i", "say", "in", "sanskrit", "to", "the", "a", "an",
            "me", "can", "please", "vedic", "translate"
        }
        english_words = [w.strip() for w in words if w not in stop_words and len(w) > 2]
        logger.info(f"[AGENT] Extracted words to translate: {english_words}")

    # Decide first action
    if query_type == "construction":
        next_action = "dictionary"
    elif query_type == "grammar":
        next_action = "grammar"
    else:
        next_action = "corpus"

    return {
        "query_type": query_type,
        "english_words": english_words,
        "next_action": next_action,
        "messages": [HumanMessage(content=f"Planning for: {question}")]
    }


def execute_tools_node(state: AgentState):
    """
    Execute the tools based on agent's decision.
    """
    logger.info(f"---AGENT: EXECUTING TOOL: {state['next_action']}---")

    next_action = state["next_action"]

    if next_action == "dictionary":
        # Look up all English words
        sanskrit_words = {}
        for word in state["english_words"]:
            result = dictionary_lookup.invoke({"word": word})
            # Extract Sanskrit terms from result
            # Format: "Sanskrit for 'word': term1, term2, term3"
            if ":" in result and "not found" not in result.lower():
                terms = result.split(":", 1)[1].strip()
                sanskrit_words[word] = [t.strip() for t in terms.split(", ")]
            else:
                sanskrit_words[word] = []

        logger.info(f"[AGENT] Dictionary results: {sanskrit_words}")
        return {
            "sanskrit_words": sanskrit_words,
            "messages": [AIMessage(content=f"Found translations: {sanskrit_words}")],
            "next_action": "grammar"  # Next: get grammar rules
        }

    elif next_action == "grammar":
        # Get grammar rules for Sanskrit words
        grammar_rules = []
        for eng_word, sans_words in state.get("sanskrit_words", {}).items():
            if sans_words:
                first_term = sans_words[0] if isinstance(sans_words, list) else sans_words
                # Determine context based on word type
                context = "declension" if eng_word in ["milk", "water", "fire"] else "conjugation"
                result = grammar_rules_search.invoke({"sanskrit_word": first_term, "context": context})
                grammar_rules.append(Document(page_content=result, metadata={"word": eng_word}))

        logger.info(f"[AGENT] Found {len(grammar_rules)} grammar references")
        return {
            "grammar_rules": grammar_rules,
            "messages": [AIMessage(content=f"Retrieved grammar rules for {len(grammar_rules)} words")],
            "next_action": "corpus"  # Next: find examples
        }

    elif next_action == "corpus":
        # Get corpus examples - retrieve raw documents directly
        query_type = state.get("query_type", "")

        if query_type == "construction":
            # For construction: search using Sanskrit terms from dictionary
            sanskrit_terms = ", ".join([
                term for terms in state.get("sanskrit_words", {}).values()
                for term in (terms if isinstance(terms, list) else [terms])
            ])
            query = f"{sanskrit_terms} example sentence usage"
        else:
            # For factual/grammar queries: search using the original question
            question = state.get("question", "")
            query = question

        # Retrieve raw documents directly from retriever (preserves metadata)
        retriever = get_shared_retriever()
        corpus_examples = retriever.invoke(query)
        
        logger.info(f"[AGENT] Retrieved {len(corpus_examples)} corpus documents with metadata")
        return {
            "corpus_examples": corpus_examples,
            "messages": [AIMessage(content=f"Retrieved {len(corpus_examples)} corpus examples")],
            "next_action": "synthesize"  # Next: construct answer
        }

    else:
        return {"next_action": "synthesize"}


def synthesize_answer_node(state: AgentState):
    """
    Agent synthesizes all information into final Sanskrit construction.
    """
    logger.info("---AGENT: SYNTHESIZING ANSWER---")

    question = state["question"]
    query_type = state["query_type"]

    if query_type == "construction":
        # Gather all information
        dictionary_info = state.get("sanskrit_words", {})
        grammar_info = state.get("grammar_rules", [])
        examples_info = state.get("corpus_examples", [])

        # Extract the English phrase to translate
        english_phrase = question.lower()
        for kw in ["translate", "say", "how do i say", "in sanskrit", "sanskrit for", "to sanskrit", "to vedic sanskrit"]:
            english_phrase = english_phrase.replace(kw, "")
        english_phrase = english_phrase.replace("can you", "").replace("?", "").strip()

        # Build dictionary lookups text
        dict_text = ""
        for eng_word, skt_words in dictionary_info.items():
            if skt_words:
                dict_text += f"- {eng_word} → {', '.join(skt_words[:3])}\n"

        # Create synthesis prompt - simpler and more direct
        synthesis_prompt = f"""You are a Sanskrit tutor. Translate this English phrase to Vedic Sanskrit.

ENGLISH PHRASE: "{english_phrase}"

DICTIONARY LOOKUPS:
{dict_text if dict_text else "No dictionary entries found."}

INSTRUCTIONS:
Construct a grammatically correct Vedic Sanskrit sentence and format your response with these sections:

1. Sanskrit (Devanagari): [Write the Sanskrit text in Devanagari script]
2. Transliteration (IAST): [Write the romanized version]
3. Word-by-word breakdown: [Explain each word with grammar]
4. Grammar notes: [Brief explanation of sentence structure]

IMPORTANT: Provide a complete response with all sections. Do not leave any section empty.

EXAMPLE FORMAT:
**Sanskrit (Devanagari):** अहं त्वां प्रेम करोमि

**Transliteration (IAST):** ahaṃ tvāṃ prema karomi

**Word-by-word:**
- aham (अहम्): "I" (pronoun, nominative case, 1st person singular)
- tvām (त्वाम्): "you" (pronoun, accusative case, 2nd person singular)
- prema (प्रेम): "love" (noun, accusative)
- karomi (करोमि): "I do" (verb, present tense, 1st person singular)

**Grammar notes:** This constructs "I do love to you" = "I love you". Uses kartṛ-karma-kriyā structure.

Now provide the translation for "{english_phrase}":"""

        messages = [SystemMessage(content=synthesis_prompt)]
        # Use provider-compatible invocation (Gemini expects a plain string)
        response = Settings.invoke_llm(llm, messages)

        # Debug: Check what we got back
        logger.info(f"[AGENT] LLM response type: {type(response)}")
        logger.info(f"[AGENT] LLM response attributes: {dir(response)[:10]}")  # First 10 attributes

        answer_content = response.content if hasattr(response, 'content') else str(response)
        logger.info(f"[AGENT] LLM response length: {len(answer_content)} chars")

        if answer_content:
            logger.info(f"[AGENT] LLM response preview: {answer_content[:200]}")  # First 200 chars

        if not answer_content or len(answer_content) < 10:
            logger.warning("[AGENT] LLM returned empty or very short response! Using enhanced fallback.")
            # Enhanced fallback with construction guidance
            answer_content = f"""**Translation of "{english_phrase}" to Vedic Sanskrit:**

**Dictionary Lookups:**
{dict_text if dict_text else "No dictionary entries found."}

**Construction Guidance:**
To construct this sentence, you would typically need to:
1. Identify the subject, verb, and object
2. Choose appropriate Sanskrit words from the dictionary
3. Apply correct grammatical endings (vibhakti/conjugation)
4. Arrange in proper Sanskrit word order

**Example approach for "I love you":**
- "I" → aham (अहम्) - 1st person pronoun, nominative
- "love" → prema (प्रेम) or sneha (स्नेह) - noun for love
- "you" → tvām (त्वाम्) - 2nd person pronoun, accusative

A possible construction: **"अहं त्वां प्रेम करोमि"** (ahaṃ tvāṃ prema karomi)
- Literally: "I you love do" = "I love you"

*Note: This is a simplified construction. Consult grammar rules for proper classical usage.*"""

        answer = {
            "answer": answer_content,
            "citations": [],  # No citations for construction
            "construction": {
                "dictionary": dictionary_info,
                "grammar": "See explanation",
                "examples": "See corpus references"
            }
        }

        logger.info("[AGENT] Construction synthesis complete")

    elif query_type == "grammar":
        # Grammar explanation query - use grammar rules
        grammar_info = state.get("grammar_rules", [])

        grammar_context = ""
        if grammar_info:
            grammar_context = "\n\n".join([doc.page_content for doc in grammar_info[:3]])

        synthesis_prompt = f"""You are a Sanskrit grammar expert. Answer this grammar question clearly and pedagogically.

QUESTION: {question}

GRAMMAR RULES FROM CORPUS:
{grammar_context if grammar_context else "No specific grammar rules found. Use your knowledge."}

INSTRUCTIONS:
1. Answer the grammar question clearly and with authority
2. Provide concrete examples from the Vedic corpus if available
3. Explain the rules step by step with Sanskrit examples
4. Use Devanagari and IAST transliteration where appropriate
5. Reference specific hymns or verses when applicable (e.g., "In RV 1.1.1...")

Provide a clear, educational answer with proper citations:"""

        messages = [SystemMessage(content=synthesis_prompt)]
        response = Settings.invoke_llm(llm, messages)

        answer_content = response.content if hasattr(response, 'content') else str(response)
        logger.info(f"[AGENT] Grammar response length: {len(answer_content)} chars")

        if not answer_content or len(answer_content) < 10:
            answer_content = "No grammar explanation could be generated. Please rephrase your question."

        answer = {
            "answer": answer_content,
            "citations": [doc.metadata.get("source", "Grammar corpus") for doc in grammar_info[:3]]
        }

        logger.info("[AGENT] Grammar synthesis complete")

    else:  # factual query
        # Factual query - use corpus search and RAG
        corpus_info = state.get("corpus_examples", [])

        corpus_context = ""
        source_texts = "the Vedic corpus"
        if corpus_info:
            # Use enhanced citations instead of raw page_content
            corpus_context = enhance_corpus_results_with_citations(corpus_info[:SYNTHESIS_DOC_BUDGET])
            # Extract actual source texts from corpus documents
            source_texts = extract_source_texts(corpus_info[:SYNTHESIS_DOC_BUDGET])

        # Check if we actually have meaningful corpus content
        has_corpus = corpus_context and len(corpus_context.strip()) > 50 and "No relevant passages" not in corpus_context

        # ── Knowledge Graph injection ─────────────────────────────────────
        # Extract named entities from query using the GAZETTEER's Latin-word
        # scanner, look up 2-hop neighborhood in the KG, and prepend as
        # explicit relationship context so the LLM can reason across texts.
        kg_context = ""
        if KG_ENABLED:
            try:
                # Re-use the same entity detection path as lexical rescue
                from src.utils.devanagari_lexical import _LAT_WORD, _normalize_latin, GAZETTEER
                entity_names = [
                    w for w in _LAT_WORD.findall(question)
                    if _normalize_latin(w) in GAZETTEER
                ]
                if entity_names:
                    kg_context = get_entity_context(entity_names, hops=2)
                    if kg_context:
                        logger.info(f"🕸️  KG injecting {len(entity_names)} entities: {entity_names}")
            except Exception as _kg_e:
                logger.warning(f"🕸️  KG lookup failed (non-fatal): {_kg_e}")

        # Detect comparison-over-time questions (must match retriever's
        # diachronic mode, which layer-balances and [SOURCE:]-tags passages)
        is_diachronic = bool(re.search(
            r"(earlier|early|later|late|older|newer)[^.?]*\b(vedic|veda|period|"
            r"layer|mandala|time)|evolv|over time|diachronic|through time|chronolog",
            question, re.I))

        diachronic_block = """
7. This is a COMPARATIVE / CHRONOLOGICAL question. Passages carry [SOURCE: ...
   chronology: early_rigveda / late_rigveda] tags. STRUCTURE YOUR ANSWER BY
   LAYER: first what EARLY-layer passages (family books, Mandalas 2-7, oldest)
   show, then what LATE-layer passages (Mandalas 1, 8-10) show, then an explicit
   comparison of concrete details (weapons, chariots, horses, forts/pur,
   metals, tactics, social organization).
8. Do NOT retreat to a generic disclaimer if layer-specific evidence exists in
   the passages — extract and contrast whatever they DO show, however partial,
   and clearly mark inference vs attestation.
9. The full diachronic span is now indexed — use it: Rigveda (layer 1 = family
   books 2-7, earliest; layer 2 = maṇḍalas 1, 8-10), the Atharvaveda Śaunaka
   (layer 3, post-RV saṃhitā), both Yajurveda saṃhitās (Vājasaneyi/Śukla and
   Taittirīya/Kṛṣṇa), and the Brāhmaṇa prose (Aitareya, Pañcaviṃśa, Śatapatha;
   layer 4, the latest Vedic period). Frame conclusions across the WHOLE Vedic
   range (early RV → Brāhmaṇa prose), not just 'early vs late Rigveda', and name
   which text/layer each piece of evidence comes from.""" if is_diachronic else ""

        # ── Pinned-verse grounding (home-module verse interpretation) ─────────
        # When the user's question cited a specific verse, the frontend resolves
        # its exact text and passes it through. We inject it as authoritative
        # synthesis context WITHOUT touching retrieval — purely additive, and
        # only active when a verse was actually pinned. Normal queries skip this.
        pinned_verse = state.get("pinned_verse")
        pinned_block = ""
        if pinned_verse:
            # AUTHORITATIVE grounding for this hymn: anukramaṇī metadata (ṛṣi,
            # patron, theme) + curated KG facts for its named entities. These are
            # seed-verified (✓traditional), so they anchor name-vs-epithet calls.
            try:
                from src.utils.anukramani import format_anukramani_block
                anukr = pinned_verse.get("anukramani")
                if anukr:
                    pinned_block += format_anukramani_block(anukr) + "\n"
                ents = pinned_verse.get("kg_entities") or []
                if ents and KG_ENABLED:
                    ek = get_entity_context(ents, hops=2)
                    if ek:
                        pinned_block += ek + "\n"
            except Exception as _anukr_e:
                logger.warning(f"📜 anukramaṇī/KG injection failed (non-fatal): {_anukr_e}")

            focus_cite = pinned_verse["citation"]
            focus_text = pinned_verse["text"]
            sukta_text = pinned_verse.get("sukta_text")
            sukta_cite = pinned_verse.get("sukta_citation", "")
            if sukta_text and sukta_text.strip() != focus_text.strip():
                pinned_block += (
                    f"FOCUS VERSE — the exact verse the user asks about ({focus_cite}):\n"
                    f"{focus_text}\n\n"
                    f"FULL SŪKTA for context — {sukta_cite}. Use these surrounding verses to "
                    f"identify the referent: trace relative pronouns (yáḥ / yásya / tám), "
                    f"continuity of subject, and any named figures across the hymn before deciding "
                    f"whether a word in the focus verse is a proper noun or an epithet:\n{sukta_text}\n"
                )
            else:
                pinned_block += (
                    f"PINNED VERSE — exact corpus text for {focus_cite}:\n{focus_text}\n"
                )

        if pinned_block:
            support = (f"\nADDITIONAL CORPUS PASSAGES (supporting context only):\n{corpus_context}\n"
                       if has_corpus else "")
            synthesis_prompt = f"""You are a Sanskrit scholar interpreting a specific Vedic verse directly from its original text.

QUESTION: {question}
{(chr(10) + kg_context) if kg_context else ""}
{pinned_block}{support}
INSTRUCTIONS:
1. Interpret the FOCUS VERSE. If a FULL SŪKTA is provided, read the whole hymn FIRST and use it to fix the subject and referents of the focus verse — do NOT treat the focus verse as isolated. Resolving who/what the verse is about almost always requires the surrounding verses.
2. Provide: the Devanagari (as given), IAST transliteration, a word-by-word breakdown with sandhi resolution, grammatical analysis, and an English interpretation grounded in that morphology.
3. Work from the Sanskrit itself and Vedic grammar (Macdonell, Monier-Williams). You MAY reach conclusions that differ from earlier translators (Wilson, Griffith, etc.), but every claim must be justified from the words and grammar — never borrowed from an external translation.
4. Before deciding whether a word is a PROPER NOUN or an EPITHET, check the rest of the sūkta: do relative pronouns (yáḥ "who", yásya "whose") or later verses describe the same entity as a person, king, or agent (e.g. one who acts, rules, is served by others)? A coherent referent across the hymn outweighs an isolated etymological reading. Test your reading for semantic coherence — a single accusative string can describe more than one entity (e.g. a patron AND his chariot); do not force a 'lord/protector' word to modify an inanimate object.
5. Clearly distinguish what the text ATTESTS from what is INFERENCE. Where genuine ambiguity remains after using the whole sūkta, give the grammatical evidence on each side rather than asserting one reading.
6. Use any KNOWLEDGE GRAPH facts above only as corroborating context, not as a substitute for reading the text.
7. Cite the focus verse as {pinned_verse['citation']}.

Provide a careful, text-grounded interpretation:"""
        elif has_corpus:
            synthesis_prompt = f"""You are a Sanskrit scholar with expertise in Vedic texts, history, and culture.

QUESTION: {question}
{(chr(10) + kg_context) if kg_context else ""}
RELEVANT CORPUS PASSAGES FROM {source_texts.upper()}:
{corpus_context}

INSTRUCTIONS:
1. Answer the question based on the corpus passages provided above
2. **IMPORTANT**: When citing passages, use the verse references shown in the headers (e.g., "RV 1.33 - Sudas" or "RV 7.18 - Sudas") instead of generic "Passage N" labels
3. Cite specific details and verse references from the passages (names, events, descriptions)
4. Be informative and educational in your response
5. Use Sanskrit terms with transliteration when appropriate
6. If the passages mention the topic, explain what they say about it and reference which verse(s)
7. If the KNOWLEDGE GRAPH section above contains relevant facts, USE them to make connections the corpus passages alone may not make explicit (e.g. inherited dynasty membership, kinship chains){diachronic_block}

Provide a detailed answer based on the corpus passages, using proper verse references:"""
        else:
            synthesis_prompt = f"""You are a Sanskrit scholar with expertise in Vedic texts.

QUESTION: {question}

CORPUS STATUS: No relevant passages found in the current corpus ({source_texts}).

INSTRUCTIONS:
Please inform the user that this specific topic is not found in the available corpus and suggest:
1. Rephrasing the question
2. Asking about topics in the indexed corpus — the Rigveda (all 10 maṇḍalas), the
   Atharvaveda (Śaunaka), both Yajurveda saṃhitās (Vājasaneyi & Taittirīya), and the
   Aitareya, Pañcaviṃśa & Śatapatha Brāhmaṇas
3. Or provide very brief general knowledge if you have it (but note it's not from the corpus)

Provide a helpful response:"""

        messages = [SystemMessage(content=synthesis_prompt)]
        response = Settings.invoke_llm(llm, messages)

        # Debug LLM response
        logger.info(f"[AGENT] LLM response type: {type(response)}")
        logger.info(f"[AGENT] LLM response attributes: {dir(response)[:20]}")
        
        answer_content = response.content if hasattr(response, 'content') else str(response)
        logger.info(f"[AGENT] Factual response length: {len(answer_content)} chars")
        logger.info(f"[AGENT] Had corpus content: {has_corpus}")
        
        # Debug: Show first 200 chars of response
        if answer_content:
            logger.info(f"[AGENT] Response preview: {answer_content[:200]}")
        else:
            logger.warning(f"[AGENT] Response is empty! Full response object: {response}")

        if not answer_content or len(answer_content) < 10:
            answer_content = f"I couldn't find relevant information in the corpus to answer this question. Please try rephrasing or ask about topics covered in {source_texts}."

        answer = {
            "answer": answer_content,
            "citations": create_enhanced_citations_list(corpus_info[:SYNTHESIS_DOC_BUDGET]) if has_corpus else []
        }

        # ── Knowledge Graph extraction ────────────────────────────────────
        # Extract relationship triples from the LLM's answer and store them.
        # This builds the KG organically — every query that reveals a fact
        # saves it for future queries to use as pre-synthesis context.
        # Skip KG extraction for pinned-verse interpretations: those answers are
        # interpretive (and may be deliberately tentative), so we don't want them
        # auto-seeding the graph as asserted facts.
        if KG_ENABLED and has_corpus and answer_content and not pinned_verse:
            try:
                n_new = extract_and_store_facts(answer_content, question, llm)
                if n_new:
                    logger.info(f"🕸️  KG grew by {n_new} facts this query")
            except Exception as _kg_e:
                logger.warning(f"🕸️  KG extraction failed (non-fatal): {_kg_e}")

        logger.info("[AGENT] Factual synthesis complete")

    return {
        "answer": answer,
        "construction_complete": True,
        "messages": [AIMessage(content="Synthesis complete")]
    }


def should_continue(state: AgentState) -> str:
    """
    Router: Decide if agent should continue with tools or synthesize answer.
    Returns: "execute_tools" | "synthesize" | "end"
    """
    next_action = state.get("next_action", "")

    if next_action == "synthesize":
        return "synthesize"
    elif state.get("construction_complete"):
        return END
    elif next_action in ["dictionary", "grammar", "corpus"]:
        return "execute_tools"
    else:
        return END


# ============================================================
# BUILD AGENTIC RAG GRAPH
# ============================================================
def create_agentic_rag_graph():
    """
    Create the agentic RAG graph with planning, tool execution, and synthesis.
    """
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("classify_and_plan", classify_and_plan_node)
    workflow.add_node("execute_tools", execute_tools_node)
    workflow.add_node("synthesize", synthesize_answer_node)

    # Define edges
    workflow.set_entry_point("classify_and_plan")

    workflow.add_conditional_edges(
        "classify_and_plan",
        should_continue,
        {
            "execute_tools": "execute_tools",
            "synthesize": "synthesize",
            END: END
        }
    )

    workflow.add_conditional_edges(
        "execute_tools",
        should_continue,
        {
            "execute_tools": "execute_tools",
            "synthesize": "synthesize",
            END: END
        }
    )

    workflow.add_edge("synthesize", END)

    return workflow.compile()


def run_agentic_rag(question: str, input_language: str = "English",
                    pinned_verse: Optional[dict] = None):
    """
    Run the agentic RAG system on a question.

    Args:
        question: User's question
        input_language: Language of input ("English" or "Devanagari")
        pinned_verse: Optional exact verse text (dict with 'citation' and 'text')
            when the query cites a specific verse. Injected as authoritative
            synthesis context ONLY — retrieval is unaffected. None for all
            normal queries, so semantic search behaves identically.

    Returns:
        Final answer with construction details
    """
    logger.info(f"=== AGENTIC RAG START: {question} (Language: {input_language}"
                f"{', pinned ' + pinned_verse['citation'] if pinned_verse else ''}) ===")

    graph = create_agentic_rag_graph()

    initial_state = {
        "question": question,
        "input_language": input_language,  # ✅ Pass language preference
        "pinned_verse": pinned_verse,
        "query_type": "",
        "english_words": [],
        "sanskrit_words": {},
        "grammar_rules": [],
        "corpus_examples": [],
        "messages": [],
        "next_action": "",
        "answer": {},
        "construction_complete": False
    }

    result = graph.invoke(initial_state)

    logger.info("=== AGENTIC RAG COMPLETE ===")

    return result
