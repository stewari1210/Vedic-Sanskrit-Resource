import os
import src.helper as helper

from dotenv import load_dotenv

load_dotenv()

logger = helper.logger

def get_config_value(key, default=None, cast_type=None):
    """Get configuration value from environment or Streamlit secrets."""
    value = os.getenv(key)
    if value is None:
        try:
            import streamlit as st
            # Try to access st.secrets, but don't fail if it's not available
            value = st.secrets.get(key)
        except Exception:
            # st.secrets not available or any other error
            pass
    
    # If we found a value, cast it if needed
    if value is not None:
        if cast_type:
            if cast_type == int:
                return int(value)
            elif cast_type == float:
                return float(value)
            elif cast_type == bool:
                return str(value).lower() in ('true', '1', 'yes', 'on')
        return value
    
    # No value found, return default (cast if needed)
    if default is not None and cast_type:
        if cast_type == int:
            return int(default)
        elif cast_type == float:
            return float(default)
        elif cast_type == bool:
            return bool(default)
    
    return default

# Determine model name for the main LLM. Prefer explicit MODEL env var, then
# GROQ_MODEL. If neither is set, keep the value as None so higher-level
# code can omit the `model` kwarg and avoid passing an invalid default to the
# provider client (which previously caused a 404 / model_not_found).
model_name = get_config_value("MODEL") or get_config_value("GROQ_MODEL") or None
if not model_name:
    logger.warning(
        "No MODEL/GROQ_MODEL env var set; no model will be passed to the LLM client."
    )

MODEL_SPECS = {
    "model": model_name,
    # environment variables may be missing; parse safely with defaults
    "temperature": get_config_value("TEMPERATURE", "0.0", float),
    "top_p": get_config_value("TOP_P", "1.0", float),
    "max_tokens": get_config_value("MAX_TOKENS", 2048, int),
    "timeout": get_config_value("TIMEOUT", 600, int),
    "max_retries": get_config_value("MAX_RETRIES", 2, int),
    "response_format": get_config_value("RESPONSE_FORMAT", None),
    # "seed": int(os.getenv("SEED", 42)),
}

EVAL_MODEL = get_config_value("EVAL_MODEL") or model_name or None
COLLECTION_NAME = get_config_value("COLLECTION_NAME", "ancient_history")
LOCAL_FOLDER = get_config_value("LOCAL_FOLDER", "local_store")
VECTORDB_FOLDER = get_config_value("VECTORDB_FOLDER", "vector_store")

# Embedding configuration
EMBEDDING_PROVIDER = get_config_value("EMBEDDING_PROVIDER", "local-best")  # local-fast, local-best, or gemini
EMBED_MODEL = get_config_value("EMBED_MODEL")

# LLM Provider configuration
LLM_PROVIDER = get_config_value("LLM_PROVIDER", "groq")  # groq, ollama, or gemini
EVAL_LLM_PROVIDER = get_config_value("EVAL_LLM_PROVIDER", None) or LLM_PROVIDER  # Use different provider for evaluation (optional)
OLLAMA_BASE_URL = get_config_value("OLLAMA_BASE_URL", "http://localhost:11434")  # Ollama server URL
OLLAMA_MODEL = get_config_value("OLLAMA_MODEL", "llama3.1:8b")  # Ollama model name
OLLAMA_EVAL_MODEL = get_config_value("OLLAMA_EVAL_MODEL", "llama3.1:8b")  # Ollama evaluation model
GEMINI_MODEL = get_config_value("GEMINI_MODEL", "gemini-2.0-flash-exp")  # Gemini model name (free tier: gemini-2.0-flash-exp, gemini-1.5-flash, gemini-1.5-pro)

CHUNK_SIZE = get_config_value("CHUNK_SIZE", 768, int)  # Reduced from 1024 for Groq token limits (6K max)
CHUNK_OVERLAP = get_config_value("CHUNK_OVERLAP", 96, int)  # Scaled proportionally (was 128)
RETRIEVAL_K = get_config_value("RETRIEVAL_K", 3, int)  # Number of chunks to retrieve per query (reduced from 5 for Groq token limit)

# Hybrid retriever weights (must sum to 1.0)
SEMANTIC_WEIGHT = get_config_value("SEMANTIC_WEIGHT", 0.7, float)  # Weight for Qdrant semantic search (conceptual)
KEYWORD_WEIGHT = get_config_value("KEYWORD_WEIGHT", 0.3, float)     # Weight for BM25 keyword search (exact matches)

# Query expansion via proper noun association
# Reduced from 2 to 1 to stay within Groq token limits (6K max)
EXPANSION_DOCS = get_config_value("EXPANSION_DOCS", 1, int)  # Number of additional docs to retrieve per proper noun for context expansion

# Low-confidence answer handling
USE_REGENERATION = get_config_value("USE_REGENERATION", True, bool)  # Enable/disable regeneration with superior model
REGENERATION_PROVIDER = get_config_value("REGENERATION_PROVIDER", "groq")  # Provider for regeneration: groq, gemini, or ollama
REGENERATION_MODEL = get_config_value("REGENERATION_MODEL", "llama-3.3-70b-versatile")  # Model for regeneration (provider-specific)
MAX_REGENERATION_ATTEMPTS = get_config_value("MAX_REGENERATION_ATTEMPTS", 1, int)  # Maximum regeneration attempts to prevent infinite loops (REDUCED from 2 to 1 to save API calls)

# Document citations in responses
# Set to False for Ollama (simpler structured output), True for Groq/Gemini (full citations)
ENABLE_CITATIONS = get_config_value("ENABLE_CITATIONS", False, bool)

CHAT_MEMORY_WINDOW = (
    get_config_value("CHAT_MEMORY_WINDOW", 5, int) * 2
)  # to account for human and ai messages
TOPIC_CHANGE_WINDOW = (
    get_config_value("TOPIC_CHANGE_WINDOW", 3, int) * 2
)  # to account for human and ai messages

# API Keys
GEMINI_API_KEY = get_config_value("GEMINI_API_KEY")
GROQ_API_KEY = get_config_value("GROQ_API_KEY")

if GEMINI_API_KEY:
    logger.info("GEMINI API Key loaded successfully.")
else:
    logger.warning("GEMINI API Key not found. Please check your keyvault or .env setup.")

if GROQ_API_KEY:
    logger.info("GROQ API Key loaded successfully.")
else:
    logger.warning("GROQ API Key not found. Please check your keyvault or .env setup.")

# Qdrant configuration
QDRANT_URL = get_config_value("QDRANT_URL")
QDRANT_API_KEY = get_config_value("QDRANT_API_KEY")
