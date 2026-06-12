#!/usr/bin/env python3
"""
Regenerate vector_store/ancient_history/docs_chunks.pkl from local_store.

Why: the frontend's hybrid retriever feeds this pickle to BM25 (keyword
search). It was last built Apr 12 and contains only the old corrupt r02 —
no r07, no clean text — so lexical matches on names like सुदास silently
failed while semantic search alone carried the RAG.

Run on Mac after any upload script, then restart Streamlit:
    python rebuild_bm25_pickle.py
"""
import json
import pickle
import shutil
import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
load_dotenv(PROJECT_ROOT / ".env", override=True)

from langchain_core.documents import Document
from src.utils.index_files import chunk_doc
from src.config import COLLECTION_NAME, LOCAL_FOLDER

LOCAL_STORE = Path(LOCAL_FOLDER)  # anchored to project root in config
PKL = PROJECT_ROOT / "vector_store" / str(COLLECTION_NAME) / "docs_chunks.pkl"

documents = []
for folder in sorted(d for d in LOCAL_STORE.iterdir() if d.is_dir()):
    md = folder / f"{folder.name}.md"
    meta = folder / f"{folder.name}_metadata.json"
    if not md.exists():
        continue
    metadata = json.loads(meta.read_text()) if meta.exists() else {"filename": folder.name}
    documents.append(Document(page_content=md.read_text(encoding="utf-8"),
                              metadata=metadata))
    print(f"✅ {folder.name}: {metadata.get('title', '?')}")

assert documents, f"No documents found in {LOCAL_STORE}"
chunks = chunk_doc(documents)
print(f"✂️  {len(chunks)} chunks from {len(documents)} documents")

# sanity: key proper nouns must be searchable
joined = " ".join(c.page_content for c in chunks)
for w in ("सुदास", "दाशराज्ञ"):
    print(f"🔎 '{w}' in chunks: {joined.count(w)}")

PKL.parent.mkdir(parents=True, exist_ok=True)
if PKL.exists():
    shutil.copy(PKL, PKL.with_suffix(".pkl.bak"))
with open(PKL, "wb") as f:
    pickle.dump(chunks, f)
print(f"💾 Wrote {PKL} ({PKL.stat().st_size:,} bytes)")
print("\n➡️  Restart Streamlit and re-run the Sudas query.")
