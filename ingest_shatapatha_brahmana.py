#!/usr/bin/env python3
"""
Ingest the Shatapatha Brahmana (Madhyandina recension) from GRETIL into Qdrant.

Source: https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/1_veda/2_bra/satapath/sb_NN_u.htm
        (14 separate files, sb_01_u.htm through sb_14_u.htm)
Format: IAST Unicode (UTF-8), paragraphs tagged book.adhyaya.brahmana.[N]
        Text spans multiple lines; ID is on its own line before the text.
Layer:  4  — brahmana_prose (latest Vedic layer)

Key passages for diachronic research:
  SB 1.4.1   : Videgha Mathava eastward migration legend (fire moving east of Sadanira)
  SB 3.1.2   : Pravahana Jaivali and the Panchagni doctrine (eastern kings know Brahman)
  SB 12.9.3  : Vamsha (teacher lineage lists)
  SB 13.5    : Ashvamedha geography

Usage:
    python ingest_shatapatha_brahmana.py            # all 14 books
    python ingest_shatapatha_brahmana.py 1          # single book
    python ingest_shatapatha_brahmana.py 1 4 14     # subset
    python ingest_shatapatha_brahmana.py --dry-run  # parse only, no upload
"""
import argparse
import json
import pickle
import re
import shutil
import sys
import time
import urllib.error
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

GRETIL_BASE = ("https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/"
               "1_veda/2_bra/satapath/sb_{:02d}_u.htm")
FILENAME = "sb"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
      "Accept": "text/html,*/*"}

# SB paragraph ID: book.adhyaya.brahmana.[N]   e.g.  1.4.1.[5]
_SB_ID_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)\.\[(\d+)\]\s*$")

# Lines to skip: GRETIL boilerplate / encoding table rows
_SKIP_RE = re.compile(
    r"^(long [aAiIuU]|vocalic|retroflex|palatal|velar|anusvara|visarga|"
    r"SATAPATHA|Data input|Bracketted|NOTE:|Therefore|Unless|For a|"
    r"For further|THIS GRETIL|TEXT FILE|COPYRIGHT|Text converted|"
    r"multibyte|description:|---|\*{5}|\|)",
    re.IGNORECASE)


# ── 1. Fetch one book ────────────────────────────────────────────────────────

def fetch_book(book: int) -> str | None:
    """Fetch one SB book from GRETIL. Returns None if the URL is missing (404)."""
    url = GRETIL_BASE.format(book)
    req = urllib.request.Request(url, headers=UA)
    try:
        raw = urllib.request.urlopen(req, timeout=90).read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"⚠️  SB Book {book}: not found on GRETIL (404) — skipping")
            return None
        raise
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    # Strip HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[\xa0 ]{2,}", " ", text)
    return text


# ── 2. Parse all paragraphs from one book's HTML ────────────────────────────

def parse_book(text: str, expected_book: int) -> list[tuple[int,int,int,int,str]]:
    """
    Returns list of (book, adhyaya, brahmana, para_n, iast_text).

    The SB format has the ID on its own line, then a blank line, then the
    IAST prose (which may span several lines) ending at the next blank line
    before the next ID.
    """
    lines = text.splitlines()
    paras = []
    current_id = None
    buf = []

    def flush():
        if current_id and buf:
            body = " ".join(buf).strip()
            # Collapse runs of whitespace
            body = re.sub(r"\s+", " ", body)
            if len(body) > 10:
                paras.append((*current_id, body))

    for line in lines:
        line = line.strip()
        # Detect paragraph ID
        m = _SB_ID_RE.match(line)
        if m:
            flush()
            buf = []
            b, a, br, p = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
            current_id = (b, a, br, p)
            continue
        # Skip boilerplate and empty lines when we have no current_id
        if not current_id:
            continue
        if not line or _SKIP_RE.match(line):
            continue
        buf.append(line)

    flush()

    # Only keep paragraphs for the expected book (avoids header pollution)
    paras = [p for p in paras if p[0] == expected_book]
    return paras


# ── 3. Convert IAST → Devanagari ────────────────────────────────────────────

def to_devanagari(iast: str) -> str:
    return sanscript.transliterate(iast, sanscript.IAST, sanscript.DEVANAGARI)


# ── 4. Build markdown for one book ──────────────────────────────────────────

def build_book_markdown(paras: list, book: int) -> str:
    """
    Group by (adhyaya) and emit:
        ## SB B.A
        {dev_text} ॥ SB B.A.Br.P ॥
    Standard SB citation is book.adhyaya.brahmana.paragraph.
    """
    lines = [f"# Shatapatha Brahmana Book {book} (Devanagari, from GRETIL)\n",
             "Source: GRETIL (H.S. Ananthanarayana and W.P. Lehman). "
             "Madhyandina recension. IAST → Devanagari via indic_transliteration.\n"]

    cur_adhyaya = None
    for b, a, br, p, iast in paras:
        if a != cur_adhyaya:
            cur_adhyaya = a
            lines.append(f"\n## SB {b}.{a}\n")
        dev = to_devanagari(iast)
        lines.append(f"{dev} ॥ SB {b}.{a}.{br}.{p} ॥")

    return "\n".join(lines)


# ── 5. Batched upload (shared with PB script pattern) ───────────────────────

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
    ap.add_argument("books", nargs="*", type=int,
                    help="Book numbers 1-14 (default: all 14)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Parse and convert only; skip Qdrant upload")
    args = ap.parse_args()
    books = args.books if args.books else list(range(1, 15))

    out_dir = Path(LOCAL_FOLDER) / FILENAME
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build/update the per-book markdown files
    all_paras_count = 0
    for book in books:
        print(f"\n{'='*60}\n📚 SB Book {book}\n{'='*60}")
        html = fetch_book(book)
        if html is None:
            continue  # 404 — already printed warning in fetch_book
        paras = parse_book(html, book)
        if not paras:
            print(f"⚠️  No paragraphs for book {book} — check parser")
            continue

        # Spot-check SB 1.4.1 (Videgha Mathava) if this is book 1
        if book == 1:
            vmk = [(b,a,br,p,t) for b,a,br,p,t in paras if a==4 and br==1]
            print(f"📍 SB 1.4.1 paragraphs found: {len(vmk)}")
            if vmk:
                print(f"   First: {vmk[0][4][:120]}")

        print(f"✅ {len(paras)} paragraphs")
        all_paras_count += len(paras)

        md = build_book_markdown(paras, book)
        book_md_path = out_dir / f"sb_{book:02d}.md"
        book_md_path.write_text(md, encoding="utf-8")
        print(f"💾 {book_md_path} ({len(md):,} chars)")
        time.sleep(1)  # be polite to GRETIL

    print(f"\n✅ Total paragraphs across {len(books)} books: {all_paras_count:,}")

    # Write combined metadata (one entry for the whole SB)
    metadata = {
        "title": "Shatapatha Brahmana (Madhyandina)",
        "author": ["Vedic Tradition",
                   "Input by H.S. Ananthanarayana and W.P. Lehman (GRETIL)"],
        "subject": ("Shatapatha Brahmana, Madhyandina recension. 14 books. "
                    "Key passages: Videgha Mathava eastward migration (SB 1.4.1), "
                    "Pravahana Jaivali eastern doctrine (SB 3.1.2), "
                    "Ashvamedha geography, vamsha lists."),
        "summary": ("Shatapatha Brahmana in Devanagari, converted from GRETIL IAST "
                    "(Madhyandina recension). Brahmana prose, layer 4. Eastern orientation "
                    "(Videha/Kosala). Contains the Videgha Mathava legend tracing "
                    "fire's movement from Sarasvati/Sindhu east of the Sadanira."),
        "creator": "GRETIL (Göttingen Register of Electronic Texts in Indian Languages)",
        "source_url": GRETIL_BASE.format(1).replace("01", "NN"),
        "source_format": "iast_html",
        "filename": FILENAME,
        "preprocessing": "sanskrit",
        "source_type": "vedic_text",
        "veda": "shatapatha_brahmana",
        "chronology_layer": 4,
        "chronology_name": "brahmana_prose",
    }
    meta_path = out_dir / f"{FILENAME}_metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False),
                         encoding="utf-8")

    if args.dry_run:
        print("⚡ --dry-run: skipping Qdrant upload and BM25 resync")
        # Show sample chunk from book 1 SB 1.4.1
        book1_md = (out_dir / "sb_01.md").read_text(encoding="utf-8")
        for i, line in enumerate(book1_md.splitlines()):
            if "विदेघ" in line or "सदानीर" in line or "माथव" in line:
                print(f"\nSample Videgha Mathava line:\n  {line[:180]}")
                break
        return

    # ── Upload to Qdrant ────────────────────────────────────────────────────
    client = QdrantClient(url=str(QDRANT_URL), api_key=str(QDRANT_API_KEY), timeout=60)
    try:
        client.create_payload_index(
            collection_name=str(COLLECTION_NAME),
            field_name="metadata.filename",
            field_schema=qmodels.PayloadSchemaType.KEYWORD, wait=True)
    except Exception:
        pass

    start = client.get_collection(str(COLLECTION_NAME)).points_count
    print(f"\n🔌 Connected. Points before: {start:,}")

    # Delete any previous SB points
    client.delete(
        collection_name=str(COLLECTION_NAME),
        points_selector=qmodels.FilterSelector(filter=qmodels.Filter(must=[
            qmodels.FieldCondition(key="metadata.filename",
                                   match=qmodels.MatchValue(value=FILENAME))])),
        wait=True)
    print("🗑️  Deleted old SB points (if any)")

    embed_model = Settings.get_embed_model()

    # Chunk and upload each book's markdown with shared metadata
    total_chunks = 0
    for book_md_path in sorted(out_dir.glob("sb_*.md")):
        book_content = book_md_path.read_text(encoding="utf-8")
        book_num = int(book_md_path.stem.split("_")[1])
        book_meta = {**metadata, "book": book_num,
                     "filename": FILENAME,
                     "title": f"Shatapatha Brahmana Book {book_num} (Madhyandina)"}
        chunks = chunk_doc([Document(page_content=book_content, metadata=book_meta)])
        print(f"\n📖 Book {book_num}: {len(chunks)} chunks — uploading...")
        upload_chunks(client, embed_model, chunks)
        total_chunks += len(chunks)

    after = client.get_collection(str(COLLECTION_NAME)).points_count
    print(f"\n✅ SB uploaded ({total_chunks} chunks). Collection: {start:,} → {after:,} (+{after-start:,})")

    # ── Resync BM25 pickle ─────────────────────────────────────────────────
    print(f"\n{'='*60}\n🔁 Re-syncing BM25 chunks pickle\n{'='*60}")
    documents = []
    for folder in sorted(d for d in Path(LOCAL_FOLDER).iterdir() if d.is_dir()):
        # RV-style: single markdown per folder named folder.md
        md = folder / f"{folder.name}.md"
        meta_f = folder / f"{folder.name}_metadata.json"
        if md.exists():
            m = json.loads(meta_f.read_text()) if meta_f.exists() else {"filename": folder.name}
            documents.append(Document(page_content=md.read_text(encoding="utf-8"), metadata=m))
        else:
            # SB-style: multiple per-book markdowns in one folder
            for sub_md in sorted(folder.glob("*.md")):
                sub_meta_name = f"{FILENAME}_metadata.json"
                sub_meta_f = folder / sub_meta_name
                m = (json.loads(sub_meta_f.read_text())
                     if sub_meta_f.exists() else {"filename": folder.name})
                # Override title per book
                book_num_match = re.search(r"_(\d+)\.md$", sub_md.name)
                if book_num_match:
                    m = {**m, "book": int(book_num_match.group(1)),
                         "title": f"Shatapatha Brahmana Book {book_num_match.group(1)}"}
                documents.append(Document(page_content=sub_md.read_text(encoding="utf-8"),
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
