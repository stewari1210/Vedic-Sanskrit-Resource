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

from src.helper import logger
from src.config import (
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
    # LAZY INITIALIZATION: Defer embedding/LLM setup until first access
    # ============================================================
    
    _embed_model = None
    _llm = None  
    _eval_llm = None
    
    @classmethod
    def get_embed_model(cls):
        """Get embedding model with lazy initialization."""
        if cls._embed_model is None:
            cls._init_embed_model()
        return cls._embed_model
        
    @classmethod
    def get_llm(cls):
        """Get main LLM with lazy initialization."""
        if cls._llm is None:
            cls._init_llm()
        return cls._llm
        
    @classmethod
    def get_eval_llm(cls):
        """Get evaluation LLM with lazy initialization."""
        if cls._eval_llm is None:
            cls._init_eval_llm()
        return cls._eval_llm
    
    @classmethod
    def _init_embed_model(cls):
        """Initialize embedding model based on current config."""
        from src.config import get_config_value
        _provider = str(get_config_value("EMBEDDING_PROVIDER", "local-fast")).lower() if get_config_value("EMBEDDING_PROVIDER") else "local-fast"
        logger.info(f"EMBEDDING_PROVIDER from config: '{get_config_value('EMBEDDING_PROVIDER')}' -> '{_provider}'")

        if _provider == "gemini":
            # Google Gemini Embeddings (requires API key, has quotas)
            logger.info(f"Using Gemini embeddings: {get_config_value('EMBED_MODEL')}")
            embed_kwargs = {}
            if get_config_value("EMBED_MODEL"):
                embed_kwargs["model"] = get_config_value("EMBED_MODEL")
            if get_config_value("GEMINI_API_KEY"):
                embed_kwargs["google_api_key"] = get_config_value("GEMINI_API_KEY")
            _base_embed_model = GoogleGenerativeAIEmbeddings(**embed_kwargs)
            cls._embed_model = RateLimitedEmbeddings(_base_embed_model, delay=0.65)

        elif _provider == "local-best":
            # Sentence Transformers: High Quality (MTEB ~64)
            logger.info("Using local embeddings: sentence-transformers/all-mpnet-base-v2 (best quality)")
            logger.info(f"  • Parallelization: batch_size={get_config_value('EMBEDDING_BATCH_SIZE', 16, int)}, device={get_config_value('EMBEDDING_DEVICE', 'cpu')}")
            cls._embed_model = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-mpnet-base-v2",
                model_kwargs={
                    'device': get_config_value("EMBEDDING_DEVICE", "cpu"),  # Use GPU if available (mps for Mac, cuda for NVIDIA)
                },
                encode_kwargs={
                    'normalize_embeddings': True,
                    'batch_size': get_config_value("EMBEDDING_BATCH_SIZE", 16, int),  # Batch processing for speed
                }
            )

        else:  # default to "local-fast"
            # Sentence Transformers: Fast & High Quality (MTEB ~62)
            logger.info("Using local embeddings: BAAI/bge-small-en-v1.5 (fast & efficient)")
            logger.info(f"  • Parallelization: batch_size={get_config_value('EMBEDDING_BATCH_SIZE', 16, int)}, device={get_config_value('EMBEDDING_DEVICE', 'cpu')}")
            cls._embed_model = HuggingFaceEmbeddings(
                model_name="BAAI/bge-small-en-v1.5",
                model_kwargs={
                    'device': get_config_value("EMBEDDING_DEVICE", "cpu"),  # Use GPU if available
                },
                encode_kwargs={
                    'normalize_embeddings': True,
                    'batch_size': get_config_value("EMBEDDING_BATCH_SIZE", 16, int),  # Batch processing
                }
            )
    
    @classmethod
    def _init_llm(cls):
        """Initialize main LLM based on current config."""
        from src.config import get_config_value
        llm_provider = str(get_config_value("LLM_PROVIDER", "groq")).lower() if get_config_value("LLM_PROVIDER") else "groq"
        
        if llm_provider == "ollama":
            logger.info(f"Using Ollama LLM for QA: {get_config_value('OLLAMA_MODEL', 'llama3.1:8b')} at {get_config_value('OLLAMA_BASE_URL', 'http://localhost:11434')}")
            logger.info(f"  • Parallelization: {get_config_value('OLLAMA_QA_NUM_THREAD', 4, int)} threads, GPU enabled (Metal), context={get_config_value('OLLAMA_QA_NUM_CTX', 8192, int)}")
            cls._llm = ChatOllama(
                base_url=get_config_value("OLLAMA_BASE_URL", "http://localhost:11434"),
                model=get_config_value("OLLAMA_MODEL", "llama3.1:8b"),
                temperature=get_config_value("TEMPERATURE", 0.0, float),
                num_ctx=get_config_value("OLLAMA_QA_NUM_CTX", 8192, int),  # Context window size
                num_thread=get_config_value("OLLAMA_QA_NUM_THREAD", 4, int),  # CPU threads for parallel processing
                num_gpu=get_config_value("OLLAMA_QA_NUM_GPU", 1, int),  # Enable GPU (Mac: 1=enabled)
            )
        elif llm_provider == "gemini":
            # Use Google Gemini as the primary QA model when requested
            if not get_config_value("GEMINI_API_KEY"):
                logger.warning("GEMINI_API_KEY not found - falling back to Groq or Ollama based on configuration.")
                # If GEMINI_API_KEY missing, fall through to Groq branch below
                groq_model = get_config_value("MODEL") or get_config_value("GROQ_MODEL")
                logger.info(f"Using Groq LLM for QA: {groq_model}")
                cls._llm = ChatGroq(
                    api_key=get_config_value("GROQ_API_KEY"),
                    model=groq_model,
                    max_tokens=get_config_value("MAX_TOKENS", 2048, int),
                    timeout=get_config_value("TIMEOUT", 600, int),
                    max_retries=get_config_value("MAX_RETRIES", 2, int),
                )
            else:
                logger.info(f"Using Google Gemini LLM for QA: {get_config_value('GEMINI_MODEL', 'gemini-2.0-flash-exp')}")
                cls._llm = ChatGoogleGenerativeAI(
                    model=get_config_value("GEMINI_MODEL", "gemini-2.0-flash-exp"),
                    google_api_key=get_config_value("GEMINI_API_KEY"),
                    temperature=get_config_value("TEMPERATURE", 0.0, float),
                    max_tokens=get_config_value("MAX_TOKENS", 2048, int),
                    timeout=get_config_value("TIMEOUT", 600, int),
                    max_retries=get_config_value("MAX_RETRIES", 2, int),
                )
        else:  # Default to Groq
            # Validate Groq model configuration
            groq_model = get_config_value("MODEL") or get_config_value("GROQ_MODEL")
            if get_config_value("GROQ_API_KEY") and not groq_model:
                raise RuntimeError(
                    "GROQ_API_KEY is set but no model is configured. Please set the MODEL or GROQ_MODEL environment variable to a valid Groq model name."
                )

            logger.info(f"Using Groq LLM for QA: {groq_model}")
            cls._llm = ChatGroq(
                api_key=get_config_value("GROQ_API_KEY"),
                model=groq_model,
                max_tokens=get_config_value("MAX_TOKENS", 2048, int),
                timeout=get_config_value("TIMEOUT", 600, int),
                max_retries=get_config_value("MAX_RETRIES", 2, int),
            )
    
    @classmethod
    def _init_eval_llm(cls):
        """Initialize evaluation LLM based on current config."""
        from src.config import get_config_value
        eval_llm_provider = str(get_config_value("EVAL_LLM_PROVIDER") or get_config_value("LLM_PROVIDER", "groq")).lower()
        
        if eval_llm_provider == "ollama":
            logger.info(f"Using Ollama LLM for Evaluation: {get_config_value('OLLAMA_EVAL_MODEL', 'llama3.1:8b')} at {get_config_value('OLLAMA_BASE_URL', 'http://localhost:11434')}")
            logger.info(f"  • Parallelization: {get_config_value('OLLAMA_EVAL_NUM_THREAD', 4, int)} threads, GPU enabled (Metal), context={get_config_value('OLLAMA_EVAL_NUM_CTX', 8192, int)}")
            cls._eval_llm = ChatOllama(
                base_url=get_config_value("OLLAMA_BASE_URL", "http://localhost:11434"),
                model=get_config_value("OLLAMA_EVAL_MODEL", "llama3.1:8b"),
                temperature=0.3,  # Lower temperature for evaluation
                num_ctx=get_config_value("OLLAMA_EVAL_NUM_CTX", 8192, int),
                num_thread=get_config_value("OLLAMA_EVAL_NUM_THREAD", 4, int),
                num_gpu=get_config_value("OLLAMA_EVAL_NUM_GPU", 1, int),
            )
        elif eval_llm_provider == "gemini":
            logger.info(f"Using Google Gemini LLM for Evaluation: {get_config_value('GEMINI_MODEL', 'gemini-2.0-flash-exp')}")
            cls._eval_llm = ChatGoogleGenerativeAI(
                model=get_config_value("GEMINI_MODEL", "gemini-2.0-flash-exp"),
                google_api_key=get_config_value("GEMINI_API_KEY"),
                temperature=0.3,
                max_tokens=1024,
                timeout=120,
                max_retries=2,
            )
        else:  # Default to Groq
            logger.info(f"Using Groq LLM for Evaluation: {get_config_value('EVAL_MODEL') or get_config_value('MODEL') or get_config_value('GROQ_MODEL')}")
            cls._eval_llm = ChatGroq(
                api_key=get_config_value("GROQ_API_KEY"),
                model=get_config_value("EVAL_MODEL") or get_config_value("MODEL") or get_config_value("GROQ_MODEL"),
                temperature=0.3,
                max_tokens=1024,
                timeout=120,
                max_retries=2,
            )

    @staticmethod
    def invoke_llm(llm_obj, messages_or_str):
        """
        Unified helper to invoke the configured LLM across providers.

        - For Gemini (ChatGoogleGenerativeAI) the client expects a plain string
          for 'invoke', so we flatten message lists into a single prompt.
        - For other providers (Ollama, Groq) we forward the messages list
          (SystemMessage/HumanMessage) as-is.

        Args:
            llm_obj: The instantiated LLM client (Settings.llm)
            messages_or_str: Either a single string prompt or a list of message
                             objects (SystemMessage/HumanMessage/etc.)

        Returns:
            The LLM response object from the provider.
        """
        from src.config import get_config_value

        provider = str(get_config_value("LLM_PROVIDER", "groq")).lower()

        # If user passed a plain string, just forward it
        if isinstance(messages_or_str, str):
            return llm_obj.invoke(messages_or_str)

        # If Gemini, flatten messages into a single prompt string
        if provider == "gemini":
            parts = []
            for m in messages_or_str:
                # Try to extract `.content` or fall back to str(m)
                content = getattr(m, "content", None) or str(m)
                parts.append(content)
            prompt = "\n\n".join(parts)
            return llm_obj.invoke(prompt)

        # Default: pass the messages list through (Ollama, Groq)
        return llm_obj.invoke(messages_or_str)
