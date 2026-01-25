import os
import src.helper as helper

from dotenv import load_dotenv

load_dotenv()

logger = helper.logger
# Determine model name for the main LLM. Prefer explicit MODEL env var, then
# GROQ_MODEL. If neither is set, keep the value as None so higher-level
# code can omit the `model` kwarg and avoid passing an invalid default to the
# provider client (which previously caused a 404 / model_not_found).
model_name = os.getenv("MODEL") or os.getenv("GROQ_MODEL") or None
if not model_name:
    logger.warning(
        "No MODEL/GROQ_MODEL env var set; no model will be passed to the LLM client."
    )

MODEL_SPECS = {
    "model": model_name,
    # environment variables may be missing; parse safely with defaults
    "temperature": float(os.getenv("TEMPERATURE", "0.0")),
    "top_p": float(os.getenv("TOP_P", "1.0")),
    "max_tokens": int(os.getenv("MAX_TOKENS", 2048)),
    "timeout": int(os.getenv("TIMEOUT", 600)),
    "max_retries": int(os.getenv("MAX_RETRIES", 2)),
    "response_format": os.getenv("RESPONSE_FORMAT", None),
    # "seed": int(os.getenv("SEED", 42)),
}

EVAL_MODEL = os.getenv("EVAL_MODEL") or model_name or None
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "ancient_history")
LOCAL_FOLDER = os.getenv("LOCAL_FOLDER", "local_store")
VECTORDB_FOLDER = os.getenv("VECTORDB_FOLDER", "vector_store")

# Embedding configuration
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "local-fast")  # local-fast, local-best, or gemini
EMBED_MODEL = os.getenv("EMBED_MODEL")

# LLM Provider configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")  # groq, ollama, or gemini
EVAL_LLM_PROVIDER = os.getenv("EVAL_LLM_PROVIDER", None) or LLM_PROVIDER  # Use different provider for evaluation (optional)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")  # Ollama server URL
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")  # Ollama model name
OLLAMA_EVAL_MODEL = os.getenv("OLLAMA_EVAL_MODEL", "llama3.1:8b")  # Ollama evaluation model
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")  # Gemini model name (free tier: gemini-2.0-flash-exp, gemini-1.5-flash, gemini-1.5-pro)

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "768"))  # Reduced from 1024 for Groq token limits (6K max)
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "96"))  # Scaled proportionally (was 128)
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "3"))  # Number of chunks to retrieve per query (reduced from 5 for Groq token limit)

# Hybrid retriever weights (must sum to 1.0)
SEMANTIC_WEIGHT = float(os.getenv("SEMANTIC_WEIGHT", "0.7"))  # Weight for Qdrant semantic search (conceptual)
KEYWORD_WEIGHT = float(os.getenv("KEYWORD_WEIGHT", "0.3"))     # Weight for BM25 keyword search (exact matches)

# Query expansion via proper noun association
# Reduced from 2 to 1 to stay within Groq token limits (6K max)
EXPANSION_DOCS = int(os.getenv("EXPANSION_DOCS", "1"))  # Number of additional docs to retrieve per proper noun for context expansion

# Low-confidence answer handling
USE_REGENERATION = os.getenv("USE_REGENERATION", "true").lower() == "true"  # Enable/disable regeneration with superior model
REGENERATION_PROVIDER = os.getenv("REGENERATION_PROVIDER", "groq").lower()  # Provider for regeneration: groq, gemini, or ollama
REGENERATION_MODEL = os.getenv("REGENERATION_MODEL", "llama-3.3-70b-versatile")  # Model for regeneration (provider-specific)
MAX_REGENERATION_ATTEMPTS = int(os.getenv("MAX_REGENERATION_ATTEMPTS", "1"))  # Maximum regeneration attempts to prevent infinite loops (REDUCED from 2 to 1 to save API calls)

# Document citations in responses
# Set to False for Ollama (simpler structured output), True for Groq/Gemini (full citations)
ENABLE_CITATIONS = os.getenv("ENABLE_CITATIONS", "false").lower() == "true"

CHAT_MEMORY_WINDOW = (
    int(os.getenv("CHAT_MEMORY_WINDOW", "5")) * 2
)  # to account for human and ai messages
TOPIC_CHANGE_WINDOW = (
    int(os.getenv("TOPIC_CHANGE_WINDOW", "3")) * 2
)  # to account for human and ai messages

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    logger.info("GEMINI API Key loaded successfully.")
else:
    logger.warning("GEMINI API Key not found. Please check your keyvault or .env setup.")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if GROQ_API_KEY:
    logger.info("GROQ API Key loaded successfully.")
else:
    logger.warning("GROQ API Key not found. Please check your keyvault or .env setup.")
