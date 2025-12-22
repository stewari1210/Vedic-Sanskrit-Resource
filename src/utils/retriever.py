from helper import logger
from config import RETRIEVAL_K


def create_retriever(vec_db, documents, top_n=5):
    """Create a retriever. Use Qdrant by default; optionally use BM25 if available.

    This function intentionally treats the BM25 dependency as optional so the
    CLI can run without installing `rank_bm25`. If BM25 is installed, it will
    be created but we default to returning the Qdrant retriever (best for
    vector search)."""
    # Configure Qdrant retriever to return more documents (default is only 4)
    # For large documents, we need more context to provide comprehensive answers
    qdrant_retriever = vec_db.as_retriever(search_kwargs={"k": RETRIEVAL_K})

    try:
        # Import lazily because rank_bm25 is an optional extra that may not be
        # installed in the user's environment.
        from langchain_community.retrievers import BM25Retriever

        bm25_retriever = BM25Retriever.from_documents(documents=documents)
        logger.info("BM25 retriever created successfully; returning Qdrant retriever by default.")
    except Exception as e:  # pragma: no cover - environment-dependent
        logger.warning(
            "BM25 retriever unavailable (rank_bm25 not installed or error): %s. Using Qdrant retriever only.",
            e,
        )

    # Return the Qdrant retriever for vector search. If you prefer BM25,
    # change this line to `return bm25_retriever` when BM25 is available.
    return qdrant_retriever
