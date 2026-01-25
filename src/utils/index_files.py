import os
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

from src.helper import logger
from src.config import LOCAL_FOLDER, COLLECTION_NAME, VECTORDB_FOLDER
from src.settings import Settings


# load all processed markdown files
def load_documents_with_metadata(main_folder: str):
    """
    Loads markdown files and their metadata from the specified folder structure.
    """
    logger.info(f"Loading documents from {main_folder}")
    all_documents = []
    # Loop through each subdirectory, which corresponds to a document
    for filename in os.listdir(main_folder):
        file_path = os.path.join(main_folder, filename)
        logger.info(f"File path {file_path}")
        if os.path.isdir(file_path):
            md_file = os.path.join(file_path, f"{filename}.md")
            json_file = os.path.join(file_path, f"{filename}_metadata.json")

            if os.path.exists(md_file) and os.path.exists(json_file):
                # Load the markdown content
                with open(md_file, "r", encoding="utf-8") as f:
                    md_content = f.read()

                # Load the metadata
                with open(json_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)

                # Create a LangChain Document object
                doc = Document(page_content=md_content, metadata=metadata)
                all_documents.append(doc)
            else:
                logger.error(f"File does not exists {md_file} and {json_file}")

    logger.info(f"Loaded {len(all_documents)} documents stored in {LOCAL_FOLDER}")
    return all_documents


def chunk_doc(doc: List[Document], chunk_size: int = 512, chunk_overlap: int = 64):
    """
    Chunk the markdown documents
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "# ", "## "],  # Common markdown separators
    )

    # Use the text splitter to create nodes from the single original document.
    # LlamaIndex ensures metadata propagates to the generated nodes.
    chunks = text_splitter.split_documents(doc)

    return chunks


def create_qdrant_vector_store(force_recreate: bool = True) -> tuple[QdrantVectorStore, list]:
    """
    Creates and populates a Qdrant vector store (cloud or local).

    Args:
        force_recreate (bool): If True, forces recreation of the collection.

    Returns:
        Qdrant: An initialized LangChain Qdrant vector store object.
    """
    from src.config import QDRANT_URL, QDRANT_API_KEY, VECTORDB_FOLDER, COLLECTION_NAME, LOCAL_FOLDER
    
    logger.info(f"QDRANT_URL: {QDRANT_URL}")
    logger.info(f"QDRANT_API_KEY: {'***' if QDRANT_API_KEY else None}")
    logger.info(f"VECTORDB_FOLDER: {VECTORDB_FOLDER}")
    logger.info(f"COLLECTION_NAME: {COLLECTION_NAME}")
    
    if QDRANT_URL and QDRANT_API_KEY:
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
        logger.info(f"Document Chunks file: {CHUNKS_FILE} does not exist. Re-Indexing")
        # chunk documents
        documents = load_documents_with_metadata(
            os.path.join(str(LOCAL_FOLDER), str(COLLECTION_NAME))
        )
        chunks = chunk_doc(documents)

        # save chunks for retrieval
        with open(CHUNKS_FILE, "wb") as f:
            pickle.dump(chunks, f)
        # Create the Qdrant vector store from the documents
        if use_cloud:
            # For cloud, assume collection exists, just connect
            vector_store = QdrantVectorStore(
                client=client,
                collection_name=str(COLLECTION_NAME),
                embedding=Settings.embed_model,
                vector_name="embedding",  # Specify the vector name for cloud collection
            )
        else:
            try:
                vector_store = QdrantVectorStore.from_documents(
                    documents=chunks,
                    embedding=Settings.embed_model,
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

                # Ensure the directory exists for local Qdrant
                try:
                    client = QdrantClient(path=str(VECTORDB_FOLDER))
                except RuntimeError as rte:
                    # Local Qdrant storage may be locked by another process. Fall
                    # back to creating a temporary local storage to avoid the lock.
                    logger.warning(
                        "Could not open local Qdrant at %s: %s. Creating temporary storage.",
                        VECTORDB_FOLDER,
                        rte,
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
                sample_vec = Settings.embed_model.embed_documents([chunks[0].page_content])[0]
                dim = len(sample_vec)

                vectors_config = VectorParams(size=dim, distance=Distance.COSINE)

                # Create collection if it doesn't exist
                try:
                    client.create_collection(collection_name=str(COLLECTION_NAME), vectors_config=vectors_config)
                except Exception:
                    # If creation fails because collection exists, ignore
                    logger.debug("create_collection raised; continuing and attempting to upsert")

                # Construct the LangChain Qdrant wrapper and add documents
                qdrant_store = QdrantVectorStore(client=client, collection_name=str(COLLECTION_NAME), embedding=Settings.embed_model)
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
            vector_store = QdrantVectorStore(
                client=client,
                collection_name=str(COLLECTION_NAME),
                embedding=Settings.embed_model,
                vector_name="embedding" if use_cloud else "",  # Specify vector name for cloud
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
                    embedding=Settings.embed_model,
                    path=str(VECTORDB_FOLDER),
                    collection_name=str(COLLECTION_NAME),
                    force_recreate=False,
                )

        logger.info(f"Returning existing vector store at {VECTORDB_FOLDER}")
    return vector_store, chunks
