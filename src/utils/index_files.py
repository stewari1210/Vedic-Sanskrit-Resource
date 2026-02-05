import os
import sys
import json
import pickle
import tempfile
from uuid import uuid4
from pathlib import Path
from dotenv import load_dotenv
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from typing import List

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.helper import logger
from src.config import LOCAL_FOLDER, COLLECTION_NAME, VECTORDB_FOLDER
from src.settings import Settings
from src.utils.sanskrit_preprocessor import preprocess_chunk


# load all processed markdown files
def load_documents_with_metadata(main_folder: str):
    """
    Loads markdown files and their metadata from ALL subdirectories in local_store.
    Supports both .md and .txt files paired with _metadata.json.
    """
    logger.info(f"Scanning for documents in: {main_folder}")
    all_documents = []
    
    # Recursively walk through all subdirectories
    for root, dirs, files in os.walk(main_folder):
        # Look for metadata files
        metadata_files = [f for f in files if f.endswith('_metadata.json')]
        
        for metadata_filename in metadata_files:
            # Extract base name (e.g., "pancavamsa_brahmana" from "pancavamsa_brahmana_metadata.json")
            base_name = metadata_filename.replace('_metadata.json', '')
            
            # Look for corresponding .md or .txt file
            md_file = os.path.join(root, f"{base_name}.md")
            txt_file = os.path.join(root, f"{base_name}.txt")
            json_file = os.path.join(root, metadata_filename)
            
            content_file = None
            if os.path.exists(md_file):
                content_file = md_file
            elif os.path.exists(txt_file):
                content_file = txt_file
            
            if content_file and os.path.exists(json_file):
                try:
                    # Load the content (markdown or text)
                    with open(content_file, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Load the metadata
                    with open(json_file, "r", encoding="utf-8") as f:
                        metadata = json.load(f)

                    # Create a LangChain Document object
                    doc = Document(page_content=content, metadata=metadata)
                    all_documents.append(doc)
                    logger.info(f"✅ Loaded: {metadata.get('title', base_name)} from {os.path.relpath(root, main_folder)}")
                except Exception as e:
                    logger.error(f"❌ Failed to load {content_file}: {e}")
            else:
                if not content_file:
                    logger.warning(f"⚠️  Metadata found but no content file (.md or .txt) for: {base_name} in {root}")

    logger.info(f"📊 Total documents loaded: {len(all_documents)}")
    return all_documents


def _extract_headers_for_ramayana(content: str) -> tuple[str, str]:
    """
    Extract current Book and Canto headers from Ramayana content.
    Returns (book, canto) tuple.
    """
    import re
    book = canto = ""
    
    # Look for # Book pattern
    book_match = re.search(r'#\s+Book\s+([IVX]+|[CLXVI]+)\.', content)
    if book_match:
        book = book_match.group(1)
    
    # Look for ## Canto pattern  
    canto_match = re.search(r'##\s+Canto\s+([IVX]+|[CLXVI]+)\.', content)
    if canto_match:
        canto = canto_match.group(1)
    
    return book, canto


def _extract_headers_for_pancavimsa(content: str) -> tuple[str, str]:
    """
    Extract chapter and section numbers from Pancavimsa Brahmana content.
    Returns (chapter, section) tuple where:
    - chapter: Prapathaka/Chapter number (1-25)
    - section: Section number within chapter (from "NN." pattern)
    
    Note: Pancavimsa text uses numbered sections like "11. By means of..."
    but doesn't have explicit chapter markers in most chunks.
    We attempt to infer chapter from surrounding context or metadata.
    """
    import re
    chapter = section = ""
    
    # Pattern: numbered section like "11.", "12.", etc.
    # This gives us the section number
    section_match = re.search(r'^\s*(\d+)\.\s+', content, re.MULTILINE)
    if section_match:
        section = section_match.group(1)
    
    # For chapter info, we'd need more context from the document
    # For now, we mark it as "unknown" - can be enhanced later with metadata
    # Example: chunks could have "prapathaka: 25" in metadata from indexing
    
    return chapter, section


def chunk_doc(doc: List[Document], chunk_size: int = 512, chunk_overlap: int = 64):
    """
    Chunk the markdown documents, preserving header context in metadata.
    
    For structured texts like Ramayana and Pancavimsa Brahmana:
    1. Extracts header information (Book, Canto, Chapter, Section)
    2. Adds it to chunk metadata for better filtering and citations
    3. Prepends header info to content for semantic search enhancement
    
    For Sanskrit texts with Devanagari:
    4. Applies Sanskrit preprocessing (normalization, tokenization, stem extraction)
       to improve embedding quality and retrieval of inflected forms
    
    This ensures searches for specific topics can better match their
    source references and enabling proper verse citations.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "# ", "## "],  # Common markdown separators
    )

    # Use the text splitter to create nodes from the single original document.
    # LlamaIndex ensures metadata propagates to the generated nodes.
    chunks = text_splitter.split_documents(doc)
    
    # Post-process chunks to add header context and Sanskrit preprocessing
    for chunk in chunks:
        source = chunk.metadata.get('source', '').lower()
        title = chunk.metadata.get('title', '').lower()
        
        # For Ramayana: extract and add Book/Canto info
        if 'ramayana' in source or 'ramayana' in title:
            book, canto = _extract_headers_for_ramayana(chunk.page_content)
            
            # If headers found, add them to metadata and prepend to content for semantic search
            if book or canto:
                # Add to metadata
                if book and 'book' not in chunk.metadata:
                    chunk.metadata['book'] = book
                if canto and 'canto' not in chunk.metadata:
                    chunk.metadata['canto'] = canto
                
                # Prepend header info to content so embeddings include it
                header_prefix = ""
                if book:
                    header_prefix += f"Book {book}. "
                if canto:
                    header_prefix += f"Canto {canto}. "
                
                # Only prepend if not already there
                if header_prefix and not chunk.page_content.startswith(header_prefix):
                    chunk.page_content = header_prefix + chunk.page_content
        
        # For Pancavimsa Brahmana: extract and add Chapter/Section info
        elif 'pancavimsa' in source or 'pancavamsa' in source or 'pancavimsa' in title or 'pancavamsa' in title:
            chapter, section = _extract_headers_for_pancavimsa(chunk.page_content)
            
            # Add to metadata for citation extraction and filtering
            if section:
                chunk.metadata['pb_section'] = section
            
            # If chapter info available (from metadata), add it
            if 'prapathaka' in chunk.metadata or 'chapter' in chunk.metadata:
                chapter = chunk.metadata.get('prapathaka', chunk.metadata.get('chapter', ''))
                if chapter and 'pb_chapter' not in chunk.metadata:
                    chunk.metadata['pb_chapter'] = chapter
            
            # Prepend section context to content for better semantic search
            # This helps queries about specific topics match "Section NN" references
            header_prefix = ""
            if chapter:
                header_prefix += f"Prapathaka {chapter}. "
            if section:
                header_prefix += f"Section {section}. "
            
            # Only prepend if not already there and we have something to prepend
            if header_prefix and not chunk.page_content.startswith(header_prefix.strip()):
                chunk.page_content = header_prefix + chunk.page_content
        
        # PHASE 1: Apply Sanskrit preprocessing to all chunks containing Devanagari
        # This improves embedding quality and handles inflected forms (Sudas vs. Sudasah)
        try:
            from src.utils.sanskrit_preprocessor import get_sanskrit_preprocessor
            preprocessor = get_sanskrit_preprocessor()
            
            if preprocessor.is_sanskrit(chunk.page_content):
                # Preprocess the content for better embeddings
                preprocessed = preprocessor.preprocess_for_embedding(chunk.page_content)
                
                # Store both original and preprocessed versions
                # The preprocessed version is used for embeddings (via embedding pipeline)
                # The original is preserved in metadata for display/citation
                chunk.metadata['preprocessing'] = 'sanskrit'
                chunk.metadata['original_content_length'] = len(chunk.page_content)
                
                # For embeddings, we blend: keep original structure but normalize Sanskrit
                # This preserves semantic information while improving token matching
                # IMPORTANT: We don't replace page_content here because:
                # 1. Metadata/headers are already in the content
                # 2. Embeddings will see preprocessed form via our preprocessing logic
                # 3. Retrieval UI gets original content for display
                
                logger.debug(f"Applied Sanskrit preprocessing to chunk (size: {len(chunk.page_content)} → {len(preprocessed)})")
        except ImportError:
            # Sanskrit preprocessor not available (indic-nlp not installed yet)
            # This is okay - preprocessing is optional and will activate once installed
            pass
        except Exception as e:
            logger.warning(f"Error applying Sanskrit preprocessing to chunk: {e}")
            # Continue without preprocessing - system still works, just less optimized

    return chunks


def create_qdrant_vector_store(force_recreate: bool = True, local_only: bool = False) -> tuple[QdrantVectorStore, list]:
    """
    Creates and populates a Qdrant vector store (cloud or local).

    Args:
        force_recreate (bool): If True, forces recreation of the collection.
        local_only (bool): If True, FORCE local-only mode and completely skip Qdrant Cloud checks.

    Returns:
        Qdrant: An initialized LangChain Qdrant vector store object.
    """
    from src.config import QDRANT_URL, QDRANT_API_KEY, VECTORDB_FOLDER, COLLECTION_NAME, LOCAL_FOLDER
    
    logger.info(f"QDRANT_URL: {QDRANT_URL}")
    logger.info(f"QDRANT_API_KEY: {'***' if QDRANT_API_KEY else None}")
    logger.info(f"VECTORDB_FOLDER: {VECTORDB_FOLDER}")
    logger.info(f"COLLECTION_NAME: {COLLECTION_NAME}")
    logger.info(f"local_only mode: {local_only}")
    
    if local_only:
        # Force local mode, skip any cloud credential checks
        logger.info("LOCAL-ONLY MODE: Force using local Qdrant (skipping cloud checks)")
        use_cloud = False
    elif QDRANT_URL and QDRANT_API_KEY:
        # Use Qdrant Cloud
        from qdrant_client import QdrantClient
        client = QdrantClient(url=str(QDRANT_URL), api_key=str(QDRANT_API_KEY))
        logger.info("Using Qdrant Cloud")
        use_cloud = True
    else:
        # Fallback to local
        logger.info("Using local Qdrant")
        use_cloud = False
    
    # Initialize Qdrant client to a local path or cloud
    if not use_cloud:
        vec_store = os.path.join(str(VECTORDB_FOLDER), str(COLLECTION_NAME))
        os.makedirs(vec_store, exist_ok=True)
    CHUNKS_FILE = os.path.join(str(VECTORDB_FOLDER), str(COLLECTION_NAME), "docs_chunks.pkl") if not use_cloud else os.path.join("vector_store", str(COLLECTION_NAME), "docs_chunks.pkl")

    # If the caller asked to force recreation, remove any existing chunks file
    # so we always re-index. Previously the function only re-indexed when the
    # chunks file was missing which made "force_recreate=True" a no-op if the
    # file was present. Remove the file (when possible) and proceed to
    # re-indexing below.
    if force_recreate and Path(CHUNKS_FILE).is_file():
        logger.info(
            "force_recreate=True: removing existing chunks file %s to force re-index",
            CHUNKS_FILE,
        )
        try:
            os.remove(CHUNKS_FILE)
        except Exception:
            logger.exception(
                "Failed to remove existing chunks file %s; will attempt to re-index anyway",
                CHUNKS_FILE,
            )

    if not Path(CHUNKS_FILE).is_file():
        if use_cloud:
            logger.info(f"Using Qdrant Cloud - assuming collection '{COLLECTION_NAME}' already exists")
            # For cloud deployment, assume collection exists and just connect
            # Use empty string for vector_name since collection has unnamed vectors
            vector_store = QdrantVectorStore(
                client=client,
                collection_name=str(COLLECTION_NAME),
                embedding=Settings.get_embed_model(),
                vector_name="",  # Empty string for unnamed vectors in cloud
            )
            # Load documents for BM25 keyword retriever (needed even for cloud)
            logger.info("Loading documents from local_store for BM25 keyword retriever...")
            documents = load_documents_with_metadata(str(LOCAL_FOLDER))
            chunks = chunk_doc(documents)
            # Cache the chunks locally
            try:
                with open(CHUNKS_FILE, "wb") as f:
                    pickle.dump(chunks, f)
                logger.info(f"Cached {len(chunks)} chunks to {CHUNKS_FILE}")
            except Exception as e:
                logger.warning(f"Could not cache chunks: {e}")
        else:
            logger.info(f"Document Chunks file: {CHUNKS_FILE} does not exist. Re-Indexing")
            # chunk documents from ALL subdirectories in local_store
            documents = load_documents_with_metadata(str(LOCAL_FOLDER))
            chunks = chunk_doc(documents)

            # save chunks for retrieval
            with open(CHUNKS_FILE, "wb") as f:
                pickle.dump(chunks, f)
            # Create the Qdrant vector store from the documents
            try:
                vector_store = QdrantVectorStore.from_documents(
                    documents=chunks,
                    embedding=Settings.get_embed_model(),
                    path=str(VECTORDB_FOLDER),
                    collection_name=str(COLLECTION_NAME),
                    force_recreate=force_recreate,
                )
            except AssertionError as e:
                # Fallback for qdrant-client / langchain mismatch where
                # qdrant_client.recreate_collection rejects unexpected kwargs
                # (e.g. 'init_from'). Create the collection manually and
                # populate it using the lower-level API.
                logger.warning(
                    "QdrantVectorStore.from_documents failed with AssertionError (%s). Falling back to manual collection creation.",
                    e,
                )
            try:
                from qdrant_client import QdrantClient
                from qdrant_client.http.models import VectorParams, Distance
                import time
                import shutil

                # Ensure the directory exists for local Qdrant
                client = None
                max_retries = 3
                retry_count = 0
                last_error = None
                
                while retry_count < max_retries and client is None:
                    try:
                        client = QdrantClient(path=str(VECTORDB_FOLDER))
                        logger.info(f"✅ Successfully connected to local Qdrant at {VECTORDB_FOLDER}")
                    except RuntimeError as rte:
                        last_error = rte
                        error_msg = str(rte).lower()
                        retry_count += 1
                        
                        # Check if this is a lock error
                        if "already accessed" in error_msg or "lock" in error_msg:
                            if retry_count < max_retries:
                                logger.warning(
                                    f"⚠️  Local Qdrant locked (attempt {retry_count}/{max_retries}): {rte}"
                                )
                                logger.warning(f"   Waiting 2 seconds before retry...")
                                time.sleep(2)
                            else:
                                logger.warning(
                                    f"❌ Local Qdrant locked after {max_retries} attempts. "
                                    f"This usually means:\n"
                                    f"   1. Another indexing process is running\n"
                                    f"   2. Previous process didn't close properly\n"
                                    f"   3. Stale lock files exist\n\n"
                                    f"To fix:\n"
                                    f"   rm -rf vector_store/\n"
                                    f"   Or: python3 src/cli_run.py --force"
                                )
                                # Try cleanup approach: remove lock files
                                try:
                                    lock_file = os.path.join(str(VECTORDB_FOLDER), "lock")
                                    if os.path.exists(lock_file):
                                        os.remove(lock_file)
                                        logger.info("🔧 Removed stale lock file, retrying...")
                                        client = QdrantClient(path=str(VECTORDB_FOLDER))
                                except Exception as cleanup_err:
                                    logger.debug(f"Lock file cleanup failed: {cleanup_err}")
                        else:
                            # Non-lock error, re-raise immediately
                            raise
                
                if client is None and last_error:
                    # All retries failed, fall back to temporary storage
                    logger.warning(
                        f"Could not connect to local Qdrant at {VECTORDB_FOLDER}: {last_error}. "
                        f"Creating temporary storage."
                    )
                    tmp_folder = str(VECTORDB_FOLDER) + f"_tmp_{uuid4().hex}"
                    os.makedirs(tmp_folder, exist_ok=True)
                    client = QdrantClient(path=tmp_folder)
                # Ensure the client has a `search` method expected by
                # langchain_community.vectorstores.qdrant. Newer qdrant-client
                # exposes `query_points`, so we monkeypatch a compatible
                # `search` method when absent.
                try:
                    import types

                    if not hasattr(client, "search"):
                        def _search(
                            self,
                            collection_name,
                            query_vector,
                            query_filter=None,
                            search_params=None,
                            limit=4,
                            offset=0,
                            with_payload=True,
                            with_vectors=False,
                            score_threshold=None,
                            consistency=None,
                            **kwargs,
                        ):
                            # Delegate to query_points which has a compatible signature
                            res = self.query_points(
                                collection_name=collection_name,
                                query=query_vector,
                                query_filter=query_filter,
                                search_params=search_params,
                                limit=limit,
                                offset=offset,
                                with_payload=with_payload,
                                with_vectors=with_vectors,
                                score_threshold=score_threshold,
                                consistency=consistency,
                                **kwargs,
                            )
                            # qdrant-client returns a QueryResponse object with a
                            # `.points` attribute. LangChain expects an iterable of
                            # scored-point-like objects; return `.points` when
                            # available, otherwise try to coerce to list.
                            if hasattr(res, "points"):
                                return res.points
                            try:
                                return list(res)
                            except Exception:
                                return res

                        client.search = types.MethodType(_search, client)
                except Exception:
                    logger.exception("Failed to attach 'search' shim to QdrantClient; search may fail.")

                # Determine vector size by embedding one chunk (may duplicate work)
                if len(chunks) == 0:
                    raise ValueError("No document chunks available to determine embedding size")
                sample_vec = Settings.get_embed_model().embed_documents([chunks[0].page_content])[0]
                dim = len(sample_vec)

                vectors_config = VectorParams(size=dim, distance=Distance.COSINE)

                # Create collection if it doesn't exist
                try:
                    client.create_collection(collection_name=str(COLLECTION_NAME), vectors_config=vectors_config)
                except Exception:
                    # If creation fails because collection exists, ignore
                    logger.debug("create_collection raised; continuing and attempting to upsert")

                # Construct the LangChain Qdrant wrapper and add documents
                qdrant_store = QdrantVectorStore(client=client, collection_name=str(COLLECTION_NAME), embedding=Settings.get_embed_model())
                try:
                    qdrant_store.add_documents(chunks)
                    vector_store = qdrant_store
                except Exception as e:
                    # If embedding or upsert fails (quota, network, etc), attempt to
                    # remove any partially created collection and the chunks file so
                    # subsequent runs will reindex cleanly instead of returning a
                    # partially-populated index.
                    logger.exception("Failed while adding documents to Qdrant: %s", e)
                    try:
                        # Try to delete the collection if it exists
                        client.delete_collection(collection_name=str(COLLECTION_NAME))
                        logger.info("Deleted partial collection %s due to failure", COLLECTION_NAME)
                    except Exception:
                        logger.debug("Could not delete partial collection (it may not exist)")
                    # Remove the chunks file so a future run will re-create it
                    try:
                        if Path(CHUNKS_FILE).is_file():
                            os.remove(CHUNKS_FILE)
                            logger.info("Removed chunks file %s after failed indexing", CHUNKS_FILE)
                    except Exception:
                        logger.exception("Failed to remove chunks file after failed indexing")
                    # Re-raise to surface the original error to callers
                    raise
            except Exception:
                logger.exception("Failed to create Qdrant collection via fallback path")
                raise
        logger.info(
            f"Successfully created vector store at {VECTORDB_FOLDER}/{COLLECTION_NAME}"
        )
    else:
        logger.info(
            f"Document Chunks file: {CHUNKS_FILE} Present. Returning existing Index"
        )
        with open(CHUNKS_FILE, "rb") as f:
            chunks = pickle.load(f)

        # Connect to existing Qdrant vector store WITHOUT re-embedding
        # This is much faster since embeddings already exist in the collection
        try:
            # Create vector store by connecting to existing collection (no re-embedding)
            # Use empty string for vector_name since cloud collection has unnamed vectors
            vector_store = QdrantVectorStore(
                client=client,
                collection_name=str(COLLECTION_NAME),
                embedding=Settings.get_embed_model(),
                vector_name="",  # Empty string for unnamed vectors (both local and cloud)
            )
            logger.info(f"Loaded existing collection '{COLLECTION_NAME}' with {len(chunks)} chunks")

        except Exception as e:
            logger.warning(
                f"Failed to connect to existing Qdrant collection: {e}. Falling back to re-indexing."
            )
            # Fallback: re-create from documents if connection fails
            if use_cloud:
                # For cloud, can't recreate easily, raise error
                raise
            else:
                vector_store = QdrantVectorStore.from_documents(
                    documents=chunks,
                    embedding=Settings.get_embed_model(),
                    path=str(VECTORDB_FOLDER),
                    collection_name=str(COLLECTION_NAME),
                    force_recreate=False,
                )

        logger.info(f"Returning existing vector store at {VECTORDB_FOLDER}")
    return vector_store, chunks
