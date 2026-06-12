#!/usr/bin/env python3
"""
Rebuild Rigveda mandala(s) in Qdrant from CLEAN source text (.itx from
sanskritdocuments.org) with chronological-layer metadata, then re-sync the
BM25 chunks pickle so keyword and semantic search stay consistent.

Usage (on Mac):
    python rebuild_mandala_clean.py all        # all 10 mandalas
    python rebuild_mandala_clean.py 7          # one mandala
    python rebuild_mandala_clean.py 1 8 9 10   # a subset

Chronology scheme (standard):
    layer 1 "early_rigveda"  : family books, Mandalas 2-7 (oldest)
    layer 2 "late_rigveda"   : Mandalas 1, 8, 9, 10
    (layer 3 reserved for AV/YV samhitas, layer 4 for Brahmana prose)
"""
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
from src.config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME, LOCAL_FOLDER, VECTORDB_FOLDER
from src.settings import Settings
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

EARLY_BOOKS = {2, 3, 4, 5, 6, 7}
ID_RE = re.compile(r"\|\|\s*(\d+)\\?\.(\d+)\\?\.(\d+)")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
      "Accept": "text/plain,*/*"}


def build_mandala(mandala: int) -> list:
    """Download, parse, convert, save markdown+metadata. Returns chunks."""
    filename = f"r{mandala:02d}"
    url = f"https://sanskritdocuments.org/doc_veda/{filename}.itx"
    out_dir = Path(LOCAL_FOLDER) / filename
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 60}\n📚 MANDALA {mandala}\n{'=' * 60}")
    print(f"⬇️  {url}")
    raw = urllib.request.urlopen(
        urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf-8")
    print(f"✅ {len(raw):,} chars")

    # parse verses
    verses, buf = [], []
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith(("%", "\\", "#")):
            continue
        buf.append(s)
        m = ID_RE.search(s)
        if m:
            mand, hymn, verse = m.groups()
            text = " ".join(buf)
            text = text[: text.rfind("||")]
            text = text.replace("\\", "").replace("`", "").replace("'", "")
            text = re.sub(r"\s+", " ", text).strip()
            verses.append((int(hymn), f"{mand}.{hymn}.{verse}", text))
            buf = []
    assert verses, f"No verses parsed for mandala {mandala}"
    print(f"✅ {len(verses)} verses, {len(set(h for h, _, _ in verses))} hymns")

    # markdown with hymn headers
    lines, cur = [f"# Rigveda Mandala {mandala} (Devanagari, from {filename}.itx)\n"], None
    for hymn, vid, itx in verses:
        if hymn != cur:
            cur = hymn
            lines.append(f"\n## RV {mandala}.{hymn:03d}\n")
        dev = sanscript.transliterate(itx, sanscript.ITRANS, sanscript.DEVANAGARI)
        lines.append(f"{dev} ॥ {vid} ॥")
    markdown = "\n".join(lines)
    (out_dir / f"{filename}.md").write_text(markdown, encoding="utf-8")

    layer = 1 if mandala in EARLY_BOOKS else 2
    metadata = {
        "title": f"Rigveda Mandala {mandala}",
        "author": ["Vedic Tradition",
                   "Aufrecht/van Nooten/Holland (Samhita), transliterated by Detlef Eichler"],
        "subject": f"Hymns from the Rigveda, Mandala {mandala}. Clean Devanagari from ITX source.",
        "summary": (f"Mandala {mandala} of the Rigveda in clean Devanagari, converted from "
                    f"the ITRANS master ({filename}.itx, sanskritdocuments.org), "
                    "verse-per-line with hymn headers and verse IDs."),
        "creator": "sanskritdocuments.org",
        "source_format": "itx",
        "filename": filename,
        "preprocessing": "sanskrit",
        "source_type": "vedic_text",
        # chronological metadata for diachronic queries
        "veda": "rigveda",
        "mandala": mandala,
        "chronology_layer": layer,
        "chronology_name": "early_rigveda" if layer == 1 else "late_rigveda",
    }
    (out_dir / f"{filename}_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    chunks = chunk_doc([Document(page_content=markdown, metadata=metadata)])
    print(f"✂️  {len(chunks)} chunks (layer {layer})")
    return filename, chunks


def upload_chunks(client, embed_model, chunks, batch_size=32):
    """Embed and upsert in small batches with generous timeout + retries.

    (langchain's Qdrant.from_documents uses big batches and the client's
    default 5s timeout — times out on residential upload bandwidth.)
    """
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
                print(f"   ⚠️  upsert retry {attempt + 1} in {wait}s ({type(e).__name__})")
                time.sleep(wait)
        print(f"   📤 {min(i + batch_size, total)}/{total} chunks", end="\r")
    print()


def main():
    args = sys.argv[1:] or ["7"]
    mandalas = list(range(1, 11)) if args[0].lower() == "all" else [int(a) for a in args]

    client = QdrantClient(url=str(QDRANT_URL), api_key=str(QDRANT_API_KEY), timeout=60)
    try:
        client.create_payload_index(
            collection_name=str(COLLECTION_NAME),
            field_name="metadata.filename",
            field_schema=qmodels.PayloadSchemaType.KEYWORD, wait=True)
    except Exception:
        pass

    embed_model = Settings.get_embed_model()
    start_points = client.get_collection(str(COLLECTION_NAME)).points_count
    print(f"🔌 Connected. Points at start: {start_points:,}")

    for mandala in mandalas:
        filename, chunks = build_mandala(mandala)

        client.delete(
            collection_name=str(COLLECTION_NAME),
            points_selector=qmodels.FilterSelector(filter=qmodels.Filter(must=[
                qmodels.FieldCondition(key="metadata.filename",
                                       match=qmodels.MatchValue(value=filename))])),
            wait=True)

        upload_chunks(client, embed_model, chunks)
        n = client.get_collection(str(COLLECTION_NAME)).points_count
        print(f"✅ Mandala {mandala} uploaded. Collection now {n:,} points")
        time.sleep(2)  # be polite to sanskritdocuments.org

    # --- ALWAYS re-sync the BM25 pickle from local_store (prevents drift) ---
    print(f"\n{'=' * 60}\n🔁 Re-syncing BM25 chunks pickle\n{'=' * 60}")
    documents = []
    for folder in sorted(d for d in Path(LOCAL_FOLDER).iterdir() if d.is_dir()):
        md = folder / f"{folder.name}.md"
        meta = folder / f"{folder.name}_metadata.json"
        if md.exists():
            metadata = json.loads(meta.read_text()) if meta.exists() else {"filename": folder.name}
            documents.append(Document(page_content=md.read_text(encoding="utf-8"),
                                      metadata=metadata))
    all_chunks = chunk_doc(documents)
    pkl = Path(VECTORDB_FOLDER) / str(COLLECTION_NAME) / "docs_chunks.pkl"
    pkl.parent.mkdir(parents=True, exist_ok=True)
    if pkl.exists():
        shutil.copy(pkl, pkl.with_suffix(".pkl.bak"))
    with open(pkl, "wb") as f:
        pickle.dump(all_chunks, f)
    print(f"💾 {len(all_chunks)} chunks from {len(documents)} docs -> {pkl}")

    final = client.get_collection(str(COLLECTION_NAME)).points_count
    print(f"\n🏁 DONE. Cloud points: {start_points:,} -> {final:,}")
    print("➡️  Restart Streamlit and re-initialize.")


if __name__ == "__main__":
    main()
