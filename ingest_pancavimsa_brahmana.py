#!/usr/bin/env python3
"""
Ingest the Pancavimsa Brahmana from GRETIL into Qdrant.

Source: https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/1_veda/2_bra/pncvbr1u.htm
Format: IAST Unicode (UTF-8), paragraphs tagged (PB book.chapter.paragraph)
Layer:  4  — brahmana_prose (latest Vedic layer)

Key passages for diachronic research:
  PB 6.6     : Sarasvati vinashana sattra (25.10.1-16 also carries this)
  PB 25.10   : "sārsvate vinasane" — sattra on the invisible Sarasvati
  PB 4.1     : Prajapati cosmogony

Usage:
    python ingest_pancavimsa_brahmana.py
    python ingest_pancavimsa_brahmana.py --dry-run   # parse only, no upload
"""
import argparse
import json
import pickle
import re
import shutil
import sys
import time
import urllib.request
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
load_dotenv(PROJECT_ROOT / ".env", override=True)

from indic_transliteration import sanscript
from langchain_core.documents import Document
from src.utils.index_files import chunk_doc
from src.config import (QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME,
                        LOCAL_FOLDER, VECTORDB_FOLDER)
from src.settings import Settings
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

GRETIL_URL = ("https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/"
              "1_veda/2_bra/pncvbr1u.htm")
FILENAME  = "pb"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
      "Accept": "text/html,*/*"}

# (PB 25.10.16) or (PB 1.1.1)
_PB_RE = re.compile(r"^\(PB\s+(\d+)\.(\d+)\.(\d+)\)\s+(.*)", re.DOTALL)


# ── 1. Fetch ────────────────────────────────────────────────────────────────

def fetch_gretil() -> str:
    print(f"⬇️  {GRETIL_URL}")
    req = urllib.request.Request(GRETIL_URL, headers=UA)
    raw = urllib.request.urlopen(req, timeout=90).read()
    # The page is declared as UTF-8; decode accordingly
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    # Strip HTML tags (the content is in <pre> or plain text after the table)
    text = re.sub(r"<[^>]+>", " ", text)
    # Collapse multiple spaces/nbsp
    text = re.sub(r"[\xa0 ]{2,}", " ", text)
    print(f"✅ {len(text):,} chars after HTML strip")
    return text


# ── 2. Parse ────────────────────────────────────────────────────────────────

def parse_paragraphs(text: str) -> list[tuple[int, int, int, str]]:
    """
    Returns list of (book, chapter, para, iast_text).
    The GRETIL file has one paragraph per (logical) line.  After HTML stripping
    some continuations land on the same line; the regex handles that.
    """
    paras = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # A line can contain multiple (PB …) tags if the HTML collapsed paragraphs.
        # We split on "(PB " boundaries and process each fragment.
        parts = re.split(r"(?=\(PB\s+\d+\.\d+\.\d+\))", line)
        for part in parts:
            part = part.strip()
            m = _PB_RE.match(part)
            if not m:
                continue
            book, chap, para_n = int(m.group(1)), int(m.group(2)), int(m.group(3))
            body = m.group(4).strip()
            if body:
                paras.append((book, chap, para_n, body))
    return paras


# ── 3. Convert ──────────────────────────────────────────────────────────────

def to_devanagari(iast: str) -> str:
    """IAST Unicode → Devanagari via indic_transliteration."""
    return sanscript.transliterate(iast, sanscript.IAST, sanscript.DEVANAGARI)


# ── 4. Build markdown ────────────────────────────────────────────────────────

def build_markdown(paras: list) -> str:
    """
    Group paragraphs by (book, chapter) and emit:

        ## PB B.CC
        {dev_text} ॥ B.C.P ॥
        {dev_text} ॥ B.C.P ॥
        ...
    """
    lines = ["# Pancavimsa Brahmana (Devanagari, from GRETIL)\n",
             "Source: GRETIL (Kümmel / Griffiths / Kobayashi, 2005). "
             "IAST → Devanagari via indic_transliteration.\n"]

    cur_key = None
    for book, chap, para_n, iast in paras:
        key = (book, chap)
        if key != cur_key:
            cur_key = key
            lines.append(f"\n## PB {book}.{chap}\n")
        dev = to_devanagari(iast)
        # Include "PB" prefix so chunks separated from their ## PB B.C header
        # can still be identified as Pancavimsa Brahmana, not Rigveda.
        lines.append(f"{dev} ॥ PB {book}.{chap}.{para_n} ॥")

    return "\n".join(lines)


# ── 5. Batched upload ────────────────────────────────────────────────────────

def upload_chunks(client, embed_model, chunks, batch_size=32):
    from uuid import uuid4
    total = len(chunks)
    for i in range(0, total, batch_size):
        bc = chunks[i:i + batch_size]
        vecs = embed_model.embed_documents([c.page_content for c in bc])
        points = [
            qmodels.PointStruct(
                id=str(uuid4()), vector=v,
                payload={"page_content": c.page_content, "metadata": c.metadata})
            for c, v in zip(bc, vecs)
        ]
        for attempt in range(4):
            try:
                client.upsert(collection_name=str(COLLECTION_NAME),
                              points=points, wait=True)
                break
            except Exception as e:
                if attempt == 3:
                    raise
                wait = 5 * (attempt + 1)
                print(f"   ⚠️  retry {attempt+1} in {wait}s ({type(e).__name__}: {e})")
                time.sleep(wait)
        print(f"   📤 {min(i+batch_size, total)}/{total}", end="\r")
    print()


# ── 6. Main ──────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Parse and convert only; skip Qdrant upload")
    args = ap.parse_args()

    # --- Fetch & parse ---
    html = fetch_gretil()
    paras = parse_paragraphs(html)
    if not paras:
        sys.exit("❌ No paragraphs parsed — check regex / URL")

    books = sorted({b for b, _, _, _ in paras})
    print(f"✅ {len(paras)} paragraphs, books {books[0]}–{books[-1]}")

    # Spot-check important passage: PB 25.10 (Sarasvati vinashana)
    saras = [(b, c, p, t) for b, c, p, t in paras if b == 25 and c == 10]
    print(f"📍 PB 25.10 paragraphs found: {len(saras)}")

    # --- Build markdown ---
    markdown = build_markdown(paras)
    out_dir = Path(LOCAL_FOLDER) / FILENAME
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{FILENAME}.md"
    md_path.write_text(markdown, encoding="utf-8")
    print(f"💾 Markdown: {md_path} ({len(markdown):,} chars)")

    # --- Metadata ---
    metadata = {
        "title": "Pancavimsa Brahmana",
        "author": ["Vedic Tradition",
                   "Input by Martin Kümmel, Arlo Griffiths, Masato Kobayashi (GRETIL 2005)"],
        "subject": ("Pancavimsa (= Tandya Maha) Brahmana of the Samaveda. "
                    "25 books. Key passages: sattra rituals, Sarasvati vinashana "
                    "(PB 25.10), soma-related liturgy."),
        "summary": ("Pancavimsa Brahmana in Devanagari, converted from GRETIL IAST. "
                    "Brahmana prose, layer 4. Contains the Sarasvati vinashana "
                    "sattra passage (PB 25.10) — evidence for the drying of the "
                    "Sarasvati river."),
        "creator": "GRETIL (Göttingen Register of Electronic Texts in Indian Languages)",
        "source_url": GRETIL_URL,
        "source_format": "iast_html",
        "filename": FILENAME,
        "preprocessing": "sanskrit",
        "source_type": "vedic_text",
        # chronological metadata
        "veda": "pancavimsa_brahmana",
        "chronology_layer": 4,
        "chronology_name": "brahmana_prose",
    }
    meta_path = out_dir / f"{FILENAME}_metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False),
                         encoding="utf-8")
    print(f"💾 Metadata: {meta_path}")

    # --- Chunk ---
    doc = Document(page_content=markdown, metadata=metadata)
    chunks = chunk_doc([doc])
    print(f"✂️  {len(chunks)} chunks (layer 4)")

    if args.dry_run:
        print("⚡ --dry-run: skipping Qdrant upload and BM25 resync")
        print("Sample chunk 0:\n", chunks[0].page_content[:300])
        return

    # --- Upload to Qdrant ---
    client = QdrantClient(url=str(QDRANT_URL), api_key=str(QDRANT_API_KEY), timeout=60)
    try:
        client.create_payload_index(
            collection_name=str(COLLECTION_NAME),
            field_name="metadata.filename",
            field_schema=qmodels.PayloadSchemaType.KEYWORD, wait=True)
    except Exception:
        pass

    start = client.get_collection(str(COLLECTION_NAME)).points_count
    print(f"🔌 Connected. Points before: {start:,}")

    # Delete any previous PB points
    client.delete(
        collection_name=str(COLLECTION_NAME),
        points_selector=qmodels.FilterSelector(filter=qmodels.Filter(must=[
            qmodels.FieldCondition(key="metadata.filename",
                                   match=qmodels.MatchValue(value=FILENAME))])),
        wait=True)
    print("🗑️  Deleted old PB points (if any)")

    embed_model = Settings.get_embed_model()
    upload_chunks(client, embed_model, chunks)
    after = client.get_collection(str(COLLECTION_NAME)).points_count
    print(f"✅ PB uploaded. Collection: {start:,} → {after:,} points (+{after-start:,})")

    # --- Resync BM25 pickle ---
    print(f"\n{'='*60}\n🔁 Re-syncing BM25 chunks pickle\n{'='*60}")
    documents = []
    for folder in sorted(d for d in Path(LOCAL_FOLDER).iterdir() if d.is_dir()):
        md = folder / f"{folder.name}.md"
        meta = folder / f"{folder.name}_metadata.json"
        if md.exists():
            m = json.loads(meta.read_text()) if meta.exists() else {"filename": folder.name}
            documents.append(Document(page_content=md.read_text(encoding="utf-8"),
                                      metadata=m))
    all_chunks = chunk_doc(documents)
    pkl = Path(VECTORDB_FOLDER) / str(COLLECTION_NAME) / "docs_chunks.pkl"
    pkl.parent.mkdir(parents=True, exist_ok=True)
    if pkl.exists():
        shutil.copy(pkl, pkl.with_suffix(".pkl.bak"))
    with open(pkl, "wb") as f:
        pickle.dump(all_chunks, f)
    print(f"💾 {len(all_chunks)} chunks from {len(documents)} docs → {pkl}")
    print("\n🏁 Done. Restart Streamlit and re-initialize.")


if __name__ == "__main__":
    main()
