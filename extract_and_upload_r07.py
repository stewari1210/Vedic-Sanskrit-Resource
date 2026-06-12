#!/usr/bin/env python3
"""
Extract Rigveda Mandala 7 (r07.pdf) and upload to Qdrant Cloud `ancient_history`.

Mirrors the r02 pipeline exactly:
  PDF --pymupdf--> local_store/ancient_history/r07/r07.md (+ metadata json)
      --chunk_doc--> chunks (with Sanskrit preprocessing)
      --Qdrant.from_documents--> append to cloud collection (no recreate)

Run on Mac:  python extract_and_upload_r07.py
"""
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
# override=True: .env beats any stale shell vars / st.secrets fallback
load_dotenv(PROJECT_ROOT / ".env", override=True)

import fitz  # pymupdf
from langchain_community.vectorstores import Qdrant
from langchain_core.documents import Document
from src.utils.index_files import chunk_doc
from src.config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME
from src.settings import Settings
from qdrant_client import QdrantClient

PDF_PATH = PROJECT_ROOT / "library/vedic_texts/RV_sanskrit/r07.pdf"
OUT_DIR = PROJECT_ROOT / "local_store/ancient_history/r07"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---- 1. Extract (same as _extract_pdf_with_pymupdf) ----
print(f"\n📖 Extracting {PDF_PATH.name} ...")
parts = []
with fitz.open(str(PDF_PATH)) as doc:
    pdf_meta = doc.metadata or {}
    page_count = doc.page_count
    toc = doc.get_toc()
    for page_num in range(len(doc)):
        text = doc[page_num].get_text("text")
        if isinstance(text, str) and text.strip():
            parts.append(f"## Page {page_num + 1}\n\n{text}")
markdown = "\n\n".join(parts)
md_file = OUT_DIR / "r07.md"
md_file.write_text(markdown, encoding="utf-8")
print(f"✅ {len(markdown):,} chars, {page_count} pages -> {md_file}")

# ---- 2. Metadata (same schema as r02_metadata.json) ----
metadata = {
    "title": "Rigveda Mandala 7",
    "author": ["Vedic Tradition",
               "Transliterated by: Aufrecht/van Nooten/Holland (Samhita), Detlef Eichler"],
    "affiliations": [],
    "subject": "Hymns from the Rigveda, Mandala 7.",
    "doi": "",
    "year": "2013",
    "month": "July",
    "keywords": ["veda", "rigveda", "svara", "Sanskrit", "doc_veda",
                 "Sanskrit Documents, Unicode Devanagari Searchable pdf"],
    "summary": ("This document contains the seventh mandala of the Rigveda, "
                "attributed to the rishi Vasishtha. Devanagari text from "
                "sanskritdocuments.org for personal study and research."),
    "format": pdf_meta.get("format", "PDF 1.5"),
    "creator": pdf_meta.get("creator", "sanskritdocuments.org"),
    "producer": pdf_meta.get("producer", "XeLaTeX"),
    "creationDate": pdf_meta.get("creationDate", ""),
    "modDate": pdf_meta.get("modDate", ""),
    "trapped": pdf_meta.get("trapped", ""),
    "encryption": None,
    "pages": page_count,
    "toc": toc,
    "filename": "r07",
    "preprocessing": "sanskrit",
    "source_type": "vedic_text",
}
meta_file = OUT_DIR / "r07_metadata.json"
meta_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"✅ Metadata -> {meta_file}")

# ---- 3. Chunk ----
doc_obj = Document(page_content=markdown, metadata=metadata)
chunks = chunk_doc([doc_obj])
print(f"✂️  {len(chunks)} chunks")

# ---- 4. Upload ONLY r07 (append; r02 untouched) ----
client = QdrantClient(url=str(QDRANT_URL), api_key=str(QDRANT_API_KEY))
before = client.get_collection(str(COLLECTION_NAME)).points_count
print(f"🔌 Connected. Points before: {before:,}")

Qdrant.from_documents(
    documents=chunks,
    embedding=Settings.get_embed_model(),
    url=str(QDRANT_URL),
    api_key=str(QDRANT_API_KEY),
    collection_name=str(COLLECTION_NAME),
    force_recreate=False,
    prefer_grpc=False,
)
after = client.get_collection(str(COLLECTION_NAME)).points_count
print(f"✅ Done. Points: {before:,} -> {after:,} (+{after - before:,})")
