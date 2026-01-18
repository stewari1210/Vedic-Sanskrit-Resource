import asyncio
import time
from typing import List
import os

# Disable tokenizers parallelism warning when forking processes
# This prevents deadlock warnings when using HuggingFace tokenizers with multiprocessing
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# This needs to be done once at the top of your script
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings

from helper import logger
from config import (
    GROQ_API_KEY,
    GEMINI_API_KEY,
    EMBED_MODEL,
    LLM_PROVIDER,
    EVAL_LLM_PROVIDER,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_EVAL_MODEL,
    GEMINI_MODEL,
    EVAL_MODEL,
    MODEL_SPECS,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    EMBEDDING_PROVIDER,
)

# Import parallelization settings
try:
    from config_parallel import (
        OLLAMA_QA_NUM_THREAD,
        OLLAMA_QA_NUM_GPU,
        OLLAMA_QA_NUM_CTX,
        OLLAMA_EVAL_NUM_THREAD,
        OLLAMA_EVAL_NUM_GPU,
        OLLAMA_EVAL_NUM_CTX,
        OLLAMA_NUM_PARALLEL,
        EMBEDDING_BATCH_SIZE,
        EMBEDDING_NUM_WORKERS,
        EMBEDDING_DEVICE,
        print_resource_allocation,
    )
    PARALLEL_ENABLED = True
    # Print resource allocation on import
    print_resource_allocation()
except ImportError:
    # Fallback to defaults if config_parallel not available
    PARALLEL_ENABLED = False
    OLLAMA_QA_NUM_THREAD = 4
    OLLAMA_QA_NUM_GPU = 1
    OLLAMA_QA_NUM_CTX = 8192
    OLLAMA_EVAL_NUM_THREAD = 4
    OLLAMA_EVAL_NUM_GPU = 1
    OLLAMA_EVAL_NUM_CTX = 8192
    OLLAMA_NUM_PARALLEL = 1
    EMBEDDING_BATCH_SIZE = 16
    EMBEDDING_NUM_WORKERS = 1
    EMBEDDING_DEVICE = 'cpu'
    logger.info("Parallelization config not found - using default settings")


class RateLimitedEmbeddings:
    """
    Wrapper around GoogleGenerativeAIEmbeddings that adds rate limiting
    to avoid hitting the free tier quota (100 requests per minute).
    """

    def __init__(self, base_embeddings: GoogleGenerativeAIEmbeddings, delay: float = 0.65):
        """
        Args:
            base_embeddings: The underlying embedding model
            delay: Delay in seconds between requests (default 0.65s = ~92 req/min, safe buffer)
        """
        self.base_embeddings = base_embeddings
        self.delay = delay
        self.last_call_time = 0

    def _wait_if_needed(self):
        """Wait if necessary to respect rate limits."""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time

        if time_since_last_call < self.delay:
            sleep_time = self.delay - time_since_last_call
            time.sleep(sleep_time)

        self.last_call_time = time.time()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents with rate limiting."""
        self._wait_if_needed()
        return self.base_embeddings.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query with rate limiting."""
        self._wait_if_needed()
        return self.base_embeddings.embed_query(text)

    def __call__(self, text: str) -> List[float]:
        """Make the wrapper callable for compatibility with older LangChain versions."""
        return self.embed_query(text)

    def __getattr__(self, name):
        """Delegate all other attributes to the base embeddings."""
        return getattr(self.base_embeddings, name)


class Settings:
    # ============================================================
    # EMBEDDINGS: Dynamic Configuration based on EMBEDDING_PROVIDER
    # ============================================================
    # Configure embedding model based on environment variable
    # Options: "local-fast", "local-best", "gemini"

    _provider = EMBEDDING_PROVIDER.lower()

    if _provider == "gemini":
        # Google Gemini Embeddings (requires API key, has quotas)
        logger.info(f"Using Gemini embeddings: {EMBED_MODEL}")
        embed_kwargs = {}
        if EMBED_MODEL:
            embed_kwargs["model"] = EMBED_MODEL
        if GEMINI_API_KEY:
            embed_kwargs["google_api_key"] = GEMINI_API_KEY
        _base_embed_model = GoogleGenerativeAIEmbeddings(**embed_kwargs)
        embed_model = RateLimitedEmbeddings(_base_embed_model, delay=0.65)

    elif _provider == "local-best":
        # Sentence Transformers: High Quality (MTEB ~64)
        logger.info("Using local embeddings: sentence-transformers/all-mpnet-base-v2 (best quality)")
        logger.info(f"  • Parallelization: batch_size={EMBEDDING_BATCH_SIZE}, device={EMBEDDING_DEVICE}")
        embed_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-mpnet-base-v2",
            model_kwargs={
                'device': EMBEDDING_DEVICE,  # Use GPU if available (mps for Mac, cuda for NVIDIA)
            },
            encode_kwargs={
                'normalize_embeddings': True,
                'batch_size': EMBEDDING_BATCH_SIZE,  # Batch processing for speed
            }
        )

    else:  # default to "local-fast"
        # Sentence Transformers: Fast & High Quality (MTEB ~62)
        logger.info("Using local embeddings: BAAI/bge-small-en-v1.5 (fast & efficient)")
        logger.info(f"  • Parallelization: batch_size={EMBEDDING_BATCH_SIZE}, device={EMBEDDING_DEVICE}")
        embed_model = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-en-v1.5",
            model_kwargs={
                'device': EMBEDDING_DEVICE,  # Use GPU if available
            },
            encode_kwargs={
                'normalize_embeddings': True,
                'batch_size': EMBEDDING_BATCH_SIZE,  # Batch processing
            }
        )

    # LLM Provider Selection: Groq or Ollama for main QA
    llm_provider = LLM_PROVIDER.lower()
    eval_llm_provider = EVAL_LLM_PROVIDER.lower()

    if llm_provider == "ollama":
        logger.info(f"Using Ollama LLM for QA: {OLLAMA_MODEL} at {OLLAMA_BASE_URL}")
        logger.info(f"  • Parallelization: {OLLAMA_QA_NUM_THREAD} threads, GPU enabled (Metal), context={OLLAMA_QA_NUM_CTX}")
        llm = ChatOllama(
            base_url=OLLAMA_BASE_URL,
            model=OLLAMA_MODEL,
            temperature=MODEL_SPECS["temperature"],
            num_ctx=OLLAMA_QA_NUM_CTX,  # Context window size
            num_thread=OLLAMA_QA_NUM_THREAD,  # CPU threads for parallel processing
            num_gpu=OLLAMA_QA_NUM_GPU,  # Enable GPU (Mac: 1=enabled)
            timeout=120,  # 2 minute timeout to prevent hanging
        )
    elif llm_provider == "gemini":
        # Use Google Gemini as the primary QA model when requested
        if not GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not found - falling back to Groq or Ollama based on configuration.")
            # If GEMINI_API_KEY missing, fall through to Groq branch below
            groq_model = MODEL_SPECS.get("model")
            logger.info(f"Using Groq LLM for QA: {groq_model}")
            llm = ChatGroq(
                api_key=GROQ_API_KEY,
                model=groq_model,
                max_tokens=MODEL_SPECS["max_tokens"],
                timeout=MODEL_SPECS["timeout"],
                max_retries=MODEL_SPECS["max_retries"],
            )
        else:
            logger.info(f"Using Google Gemini LLM for QA: {GEMINI_MODEL}")
            llm = ChatGoogleGenerativeAI(
                model=GEMINI_MODEL,
                google_api_key=GEMINI_API_KEY,
                temperature=MODEL_SPECS["temperature"],
                max_tokens=MODEL_SPECS["max_tokens"],
                timeout=MODEL_SPECS["timeout"],
                max_retries=MODEL_SPECS["max_retries"],
            )
    else:  # Default to Groq
        # Validate Groq model configuration
        groq_model = MODEL_SPECS.get("model")
        if GROQ_API_KEY and not groq_model:
            raise RuntimeError(
                "GROQ_API_KEY is set but no model is configured. Please set the MODEL or GROQ_MODEL environment variable to a valid Groq model name."
            )

        logger.info(f"Using Groq LLM for QA: {groq_model}")
        llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model=groq_model,
            max_tokens=MODEL_SPECS["max_tokens"],
            timeout=MODEL_SPECS["timeout"],
            max_retries=MODEL_SPECS["max_retries"],
        )

    # Evaluator LLM - can use different provider (e.g., Gemini for evaluating Ollama 8B responses)
    if eval_llm_provider == "ollama":
        logger.info(f"Using Ollama LLM for Evaluation: {OLLAMA_EVAL_MODEL} at {OLLAMA_BASE_URL}")
        logger.info(f"  • Parallelization: {OLLAMA_EVAL_NUM_THREAD} threads, GPU enabled (Metal), context={OLLAMA_EVAL_NUM_CTX}")
        evaluator_llm = ChatOllama(
            base_url=OLLAMA_BASE_URL,
            model=OLLAMA_EVAL_MODEL,
            temperature=MODEL_SPECS["temperature"],
            num_ctx=OLLAMA_EVAL_NUM_CTX,
            num_thread=OLLAMA_EVAL_NUM_THREAD,  # CPU threads
            num_gpu=OLLAMA_EVAL_NUM_GPU,  # Enable GPU (Mac: 1=enabled)
            timeout=180,  # 3 minute timeout (32B model is larger, takes longer)
        )
    elif eval_llm_provider == "gemini":
        if not GEMINI_API_KEY:
            logger.warning("No GEMINI_API_KEY found for evaluation. Falling back to same LLM as QA.")
            evaluator_llm = llm
        else:
            logger.info(f"Using Google Gemini LLM for Evaluation: {GEMINI_MODEL}")
            evaluator_llm = ChatGoogleGenerativeAI(
                model=GEMINI_MODEL,
                google_api_key=GEMINI_API_KEY,
                temperature=MODEL_SPECS["temperature"],
                max_tokens=MODEL_SPECS["max_tokens"],
                timeout=MODEL_SPECS["timeout"],
                max_retries=MODEL_SPECS["max_retries"],
            )
    else:  # Use Groq for evaluation
        if not GROQ_API_KEY:
            logger.warning("No GROQ_API_KEY found for evaluation. Falling back to same LLM as QA.")
            evaluator_llm = llm
        else:
            logger.info(f"Using Groq LLM for Evaluation: {EVAL_MODEL}")
            evaluator_llm = ChatGroq(
                api_key=GROQ_API_KEY,
                model=EVAL_MODEL,
                max_tokens=MODEL_SPECS["max_tokens"],
                timeout=MODEL_SPECS["timeout"],
                max_retries=MODEL_SPECS["max_retries"],
            )

    chunk_size = CHUNK_SIZE
    chunk_overlap = CHUNK_OVERLAP
