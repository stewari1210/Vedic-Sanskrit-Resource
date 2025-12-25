from helper import logger
from config import RETRIEVAL_K
from typing import List
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun


class HybridRetriever(BaseRetriever):
    """Custom hybrid retriever that combines semantic and keyword search.

    Retrieves from BOTH:
    - Semantic search (Qdrant): Good for conceptual queries like 'appearance', 'skin color'
    - Keyword search (BM25): Good for exact matches like 'HYMN XXXIII', '[02-033]'

    Then merges and deduplicates results, prioritizing exact keyword matches."""

    semantic_retriever: BaseRetriever
    keyword_retriever: BaseRetriever
    k: int = 10

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun = None
    ) -> List[Document]:
        """Get relevant documents from both retrievers and merge."""

        logger.info(f"HybridRetriever: Query = '{query}'")

        # Extract keywords for BM25 (remove action words like "summarize", "explain", etc.)
        # This helps BM25 match on the actual content patterns like "[02-033]" or "HYMN XXXIII"
        import re
        import unicodedata
        # Keep hymn references, numbers in brackets, and important nouns
        keyword_query = re.sub(r'\b(summarize|explain|describe|tell|about|what|who|when|where|why|how|is|are|the|a|an|in|on|at|for)\b', '', query, flags=re.IGNORECASE)
        keyword_query = keyword_query.strip()

        # Strip diacritical marks for BM25 (e.g., Sūdaḥ → Sudas, ā → a)
        # This helps match Sanskrit terms that may be transliterated differently
        keyword_query_normalized = unicodedata.normalize('NFD', keyword_query)
        keyword_query_normalized = ''.join(char for char in keyword_query_normalized if unicodedata.category(char) != 'Mn')

        # Remove punctuation except hyphens and brackets (keep [02-033] intact)
        keyword_query_normalized = re.sub(r'[^\w\s\[\]\-]', '', keyword_query_normalized)
        keyword_query_normalized = keyword_query_normalized.strip()

        # If we stripped too much, fall back to original query
        if len(keyword_query_normalized) < 2:
            keyword_query_normalized = query

        logger.info(f"HybridRetriever: Keyword query for BM25 = '{keyword_query_normalized}'")

        # Get results from both retrievers
        # Keyword retriever with extracted keywords (normalized, no diacritics)
        keyword_docs = self.keyword_retriever.invoke(keyword_query_normalized)
        # Semantic retriever with full natural language query (original with diacritics)
        semantic_docs = self.semantic_retriever.invoke(query)

        logger.info(f"HybridRetriever: BM25 returned {len(keyword_docs)} docs, Qdrant returned {len(semantic_docs)} docs")
        if keyword_docs:
            preview = keyword_docs[0].page_content[:100].replace('\n', ' ')
            has_target = '[02-033]' in keyword_docs[0].page_content
            logger.info(f"HybridRetriever: BM25 top result [has [02-033]: {has_target}]: {preview}...")
        if keyword_docs and len(keyword_docs) > 1:
            preview2 = keyword_docs[1].page_content[:100].replace('\n', ' ')
            has_target2 = '[02-033]' in keyword_docs[1].page_content
            logger.info(f"HybridRetriever: BM25 #2 result [has [02-033]: {has_target2}]: {preview2}...")

        # Merge and deduplicate (keep order: keyword results first, then semantic)
        seen_content = set()
        merged_docs = []

        # Add keyword results first (prioritize exact matches)
        for doc in keyword_docs:
            content_hash = hash(doc.page_content)
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                merged_docs.append(doc)

        # Add semantic results (skip duplicates)
        for doc in semantic_docs:
            content_hash = hash(doc.page_content)
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                merged_docs.append(doc)

        logger.info(f"HybridRetriever: Merged to {len(merged_docs)} unique docs, returning top {self.k}")

        # Return top k results
        return merged_docs[:self.k]
def create_retriever(vec_db, documents, top_n=5):
    """Create a hybrid retriever combining semantic (Qdrant) and keyword (BM25) search.

    This combines the best of both:
    - BM25 for exact matches: 'HYMN XXXIII', '[02-033]'
    - Semantic for concepts: 'appearance', 'skin color', 'Rudra description'
    """

    # Configure Qdrant semantic retriever
    qdrant_retriever = vec_db.as_retriever(search_kwargs={"k": RETRIEVAL_K})

    try:
        from langchain_community.retrievers import BM25Retriever

        # Create BM25 keyword retriever
        logger.info(f"Creating BM25 retriever with {len(documents)} documents")
        # Check if [02-033] exists in documents
        matching = [i for i, doc in enumerate(documents) if '[02-033]' in doc.page_content]
        logger.info(f"BM25 input: Found [02-033] in {len(matching)} documents (indices: {matching[:5]})")

        bm25_retriever = BM25Retriever.from_documents(documents=documents)
        bm25_retriever.k = RETRIEVAL_K

        # Create custom hybrid retriever
        hybrid = HybridRetriever(
            semantic_retriever=qdrant_retriever,
            keyword_retriever=bm25_retriever,
            k=RETRIEVAL_K
        )

        logger.info(f"Hybrid retriever created: BM25 (keywords) + Qdrant (semantic), k={RETRIEVAL_K}")
        return hybrid

    except Exception as e:
        logger.warning(
            f"BM25 unavailable ({e}). Using semantic retriever only.",
        )
        return qdrant_retriever
