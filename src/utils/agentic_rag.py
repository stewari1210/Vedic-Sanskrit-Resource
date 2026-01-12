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

from typing import TypedDict, List, Annotated, Literal
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.documents import Document
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
import operator
from helper import logger
from settings import Settings
import re

llm = Settings.llm

# Global shared vector store to avoid Qdrant lock issues
_SHARED_VECTOR_STORE = None
_SHARED_DOCS = None

def set_shared_vector_store(vec_db, docs):
    """Set the shared vector store instance from the frontend."""
    global _SHARED_VECTOR_STORE, _SHARED_DOCS
    _SHARED_VECTOR_STORE = vec_db
    _SHARED_DOCS = docs
    logger.info("[AGENTIC] Shared vector store configured")

def get_shared_vector_store():
    """Get the shared vector store, or create if not set."""
    global _SHARED_VECTOR_STORE, _SHARED_DOCS
    if _SHARED_VECTOR_STORE is None:
        logger.warning("[AGENTIC] No shared vector store set, creating new instance")
        from utils.index_files import create_qdrant_vector_store
        _SHARED_VECTOR_STORE, _SHARED_DOCS = create_qdrant_vector_store(force_recreate=False)
    return _SHARED_VECTOR_STORE, _SHARED_DOCS


class AgentState(TypedDict):
    """State for the agentic RAG system"""
    question: str
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
        # Use shared vector store instead of creating new one
        vec_db, docs = get_shared_vector_store()
        retriever = vec_db.as_retriever(search_kwargs={"k": 3})

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
    Search Vedic corpus (RV/YV) for usage examples.

    Args:
        sanskrit_terms: Sanskrit words to find examples for (comma-separated)
        pattern: Sentence pattern to match (e.g., "subject verb object")

    Returns:
        Example sentences from corpus
    """
    logger.info(f"[CORPUS] Searching examples for '{sanskrit_terms}' (pattern: {pattern})")

    query = f"{sanskrit_terms} {pattern} example sentence usage"

    try:
        # Use shared vector store instead of creating new one
        vec_db, docs = get_shared_vector_store()
        retriever = vec_db.as_retriever(search_kwargs={"k": 3})

        examples = retriever.invoke(query)

        if examples:
            result = "\n\n".join([f"Example {i+1}: {doc.page_content[:300]}" for i, doc in enumerate(examples[:2])])
            logger.info(f"[CORPUS] Found {len(examples)} examples")
            return result
        else:
            return "No corpus examples found."

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

    if is_construction:
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

        # Remove common words
        stop_words = {
            "how", "do", "i", "say", "in", "sanskrit", "to", "the", "a", "an",
            "what", "is", "me", "you", "can", "please", "vedic", "translate"
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
        # Get corpus examples
        query_type = state.get("query_type", "")

        if query_type == "construction":
            # For construction: search using Sanskrit terms from dictionary
            sanskrit_terms = ", ".join([
                term for terms in state.get("sanskrit_words", {}).values()
                for term in (terms if isinstance(terms, list) else [terms])
            ])
            result = corpus_examples_search.invoke({"sanskrit_terms": sanskrit_terms, "pattern": "sentence"})
        else:
            # For factual/grammar queries: search using the original question
            question = state.get("question", "")
            result = corpus_examples_search.invoke({"sanskrit_terms": question, "pattern": ""})

        corpus_examples = [Document(page_content=result)]

        logger.info(f"[AGENT] Found corpus examples")
        return {
            "corpus_examples": corpus_examples,
            "messages": [AIMessage(content="Retrieved corpus examples")],
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
        response = llm.invoke(messages)

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
1. Answer the grammar question clearly
2. Provide examples if relevant
3. Explain the rules step by step
4. Use Devanagari and IAST transliteration where appropriate

Provide a clear, educational answer:"""

        messages = [SystemMessage(content=synthesis_prompt)]
        response = llm.invoke(messages)

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
        if corpus_info:
            corpus_context = "\n\n".join([doc.page_content for doc in corpus_info[:5]])

        synthesis_prompt = f"""You are a Sanskrit scholar answering questions about Vedic texts, history, and culture.

QUESTION: {question}

RELEVANT CORPUS PASSAGES:
{corpus_context if corpus_context else "No specific passages found in the corpus."}

INSTRUCTIONS:
1. Answer the question based on the corpus passages provided
2. Be accurate and cite specific text references when possible
3. If the corpus doesn't contain relevant information, say so clearly
4. Use Sanskrit terms with transliteration when appropriate

Provide an informative answer:"""

        messages = [SystemMessage(content=synthesis_prompt)]
        response = llm.invoke(messages)

        answer_content = response.content if hasattr(response, 'content') else str(response)
        logger.info(f"[AGENT] Factual response length: {len(answer_content)} chars")

        if not answer_content or len(answer_content) < 10:
            answer_content = "I couldn't find relevant information in the corpus to answer this question. Please try rephrasing or ask about topics covered in the Rigveda and Yajurveda."

        answer = {
            "answer": answer_content,
            "citations": [f"Corpus passage {i+1}" for i in range(len(corpus_info[:5]))]
        }

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


def run_agentic_rag(question: str):
    """
    Run the agentic RAG system on a question.

    Args:
        question: User's question

    Returns:
        Final answer with construction details
    """
    logger.info(f"=== AGENTIC RAG START: {question} ===")

    graph = create_agentic_rag_graph()

    initial_state = {
        "question": question,
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
