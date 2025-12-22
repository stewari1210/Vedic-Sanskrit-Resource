import os
import helper

from keyvault import keyvault  # type: ignore
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

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1024"))  # Increased from 512 for better context & speed
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "128"))  # Scaled proportionally
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "10"))  # Number of chunks to retrieve per query

CHAT_MEMORY_WINDOW = (
    int(os.getenv("CHAT_MEMORY_WINDOW", "5")) * 2
)  # to account for human and ai messages
TOPIC_CHANGE_WINDOW = (
    int(os.getenv("TOPIC_CHANGE_WINDOW", "3")) * 2
)  # to account for human and ai messages

GEMINI_API_KEY = getattr(keyvault, "GEMINI_API_KEY", None) or os.getenv(
    "GEMINI_API_KEY"
)

if GEMINI_API_KEY:
    logger.info("GEMINI API Key loaded successfully.")
else:
    logger.warning("GEMINI API Key not found. Please check your keyvault or .env setup.")

GROQ_API_KEY = getattr(keyvault, "GROQ_API_KEY", None) or os.getenv("GROQ_API_KEY")
if GROQ_API_KEY:
    logger.info("GROQ API Key loaded successfully.")
else:
    logger.warning("GROQ API Key not found. Please check your keyvault or .env setup.")
