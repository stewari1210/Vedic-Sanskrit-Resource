#!/usr/bin/env python3
"""
Ingest the Aitareya Brahmana from TITUS (Frankfurt) into Qdrant.

Source: https://titus.uni-frankfurt.de/texte/etcs/ind/aind/ved/rv/ab/ab{:03d}.htm
        Files ab001.htm – ab285.htm (285 sub-sections, one per adhyāya)
Format: TITUS transliteration (near-IAST):
          U+02B0 ʰ used for aspirates  (bʰ → bh, dʰ → dh, etc.)
          r + U+0325 combining ring    (r̥  → ṛ)
        Words wrapped in <a href="javascript:ci(ID,'...')">WORD</a> links.
Layer:  4 — brahmana_prose (latest Vedic)

Key passages:
  AB 7.27-34 : Shunahshepa legend (Harishchandra, Ikshvaku lineage, royal
               consecration origin myth)
  AB 8.21    : King register — Janamejaya Pārikṣita, Bharata Dauḥṣanti, etc.

Copyright:
  The TITUS digital edition is © TITUS Project, Frankfurt a/M.
  The underlying text (Th. Aufrecht ed., Bonn 1879) is public domain.
  This script extracts plain transliterated text only.

Usage:
    python ingest_aitareya_brahmana.py             # all 285 parts
    python ingest_aitareya_brahmana.py 1 50        # parts 1–50 only
    python ingest_aitareya_brahmana.py --dry-run   # parse + convert; no upload
"""
import argparse
import html as html_lib
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

TITUS_BASE = ("https://titus.uni-frankfurt.de/texte/etcs/ind/aind/"
              "ved/rv/ab/ab{:03d}.htm")
FILENAME  = "ab"
N_PARTS   = 285      # ab001.htm through ab285.htm
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
      "Accept": "text/html,*/*"}


# ── 1. TITUS → IAST normalisation ────────────────────────────────────────────

def titus_to_iast(text: str) -> str:
    """Normalise TITUS transliteration to standard IAST.

    TITUS uses:
      U+02B0 (ʰ, modifier letter small h) for aspirates → replace with plain h.
      r + U+0325 (combining ring below) for vocalic ṛ → U+1E5B.
      l + U+0325 for vocalic ḷ (rare) → U+1E37.
    """
    text = text.replace('ʰ', 'h')      # bʰ→bh, dʰ→dh, kʰ→kh, etc.
    text = text.replace('r̥', 'ṛ')    # vocalic r
    text = text.replace('R̥', 'Ṛ')
    text = text.replace('l̥', 'ḷ')    # vocalic l (AV/later texts)
    return text


def clean_titus_text(text: str) -> str:
    """Remove TITUS-specific markers that have no IAST equivalent."""
    # Avagraha / elision markers: Armenian apostrophe U+055A, plain apostrophe
    # e.g. 'po = apo (elided), ՚1 = footnote marker
    text = re.sub(r"['՚]\d*", '', text)
    # Line-continuation backslash (appears in verse citations)
    text = text.replace('\\', ' ')
    # Sandhi markers: = (virama ligature) and + (e.g. adʰvaryo+u)
    text = re.sub(r'[=+]', '', text)
    # Collapse multiple spaces
    text = re.sub(r'  +', ' ', text)
    return text.strip()


def to_devanagari(iast: str) -> str:
    iast = titus_to_iast(iast)
    iast = clean_titus_text(iast)
    return sanscript.transliterate(iast, sanscript.IAST, sanscript.DEVANAGARI)


# ── 2. Fetch ─────────────────────────────────────────────────────────────────

def fetch_part(n: int) -> str | None:
    """Fetch one TITUS AB page. Returns raw HTML or None on 404."""
    url = TITUS_BASE.format(n)
    req = urllib.request.Request(url, headers=UA)
    try:
        raw = urllib.request.urlopen(req, timeout=30).read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"⚠️  Part {n:03d}: 404 — skipping")
            return None
        raise
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


# ── 3. Parse ──────────────────────────────────────────────────────────────────

# Words in TITUS pages: <a href="javascript:ci(ID,'enc')">IAST_word</a>
_WORD_TAG_RE = re.compile(
    r'<a\s[^>]*href\s*=\s*"javascript:ci\([^)]+\)"[^>]*>([^<]+)</a>', re.I)
_TAG_RE = re.compile(r'<[^>]+>')
_CHAPTER_RE   = re.compile(r'Chapter:\s*(\d+)')
_PARAGRAPH_RE = re.compile(r'Paragraph:\s*(\d+)')
_SENTENCE_RE  = re.compile(r'Sentence:\s*(\d+)')

# Lines to discard after tag stripping
_SKIP_RE = re.compile(
    r'(TITUS|Rg-Veda|Aitareya-Brahmana|Part No\.|Previous part|Next part|'
    r'This text is part|Copyright|Frankfurt|No parts of|'
    r'meta-|title:|Jost Gippert|Aufrecht|Erlangen|converted|entered)',
    re.IGNORECASE)


def parse_html(html: str) -> tuple[int | None, int | None, list[tuple[int, str]]]:
    """Parse one TITUS AB HTML page.

    Returns:
        new_chapter   — pañcikā number if page opens a new chapter, else None
        new_paragraph — adhyāya number for this page (always present)
        sentences     — list of (sentence_n, raw_iast_text)
    """
    # Decode HTML entities FIRST (e.g. &nbsp; → space, &amp; → &)
    # Without this, &nbsp; would pass through tag-stripping unchanged and
    # then be transliterated as Sanskrit letters (→ &न्ब्स्प्; garbage).
    raw_html = html_lib.unescape(html)
    # Replace non-breaking spaces with regular spaces
    raw_html = raw_html.replace('\xa0', ' ')
    # Replace each word-link with the visible text + space
    text = _WORD_TAG_RE.sub(lambda m: m.group(1) + ' ', raw_html)
    # Strip remaining tags
    text = _TAG_RE.sub(' ', text)
    # Collapse whitespace
    text = re.sub(r'[ \t]+', ' ', text)

    # Chapter (pañcikā) and paragraph (adhyāya)
    new_chapter = None
    cm = _CHAPTER_RE.search(text)
    if cm:
        new_chapter = int(cm.group(1))

    new_paragraph = None
    pm = _PARAGRAPH_RE.search(text)
    if pm:
        new_paragraph = int(pm.group(1))

    # Sentences: split on "Sentence: N" boundaries
    positions = [(m.start(), int(m.group(1)))
                 for m in _SENTENCE_RE.finditer(text)]

    sentences = []
    # Footer cutoff
    footer = text.find('This text is part of')
    if footer == -1:
        footer = len(text)

    for i, (pos, snum) in enumerate(positions):
        # Content starts just after "Sentence: N"
        content_start = pos + len(f'Sentence: {snum}')
        content_end   = positions[i + 1][0] if i + 1 < len(positions) else footer

        raw = text[content_start:content_end].strip()

        # Discard lines that are navigation / boilerplate
        lines = [l.strip() for l in raw.splitlines()
                 if l.strip() and not _SKIP_RE.search(l)]
        raw = ' '.join(lines)
        raw = re.sub(r'  +', ' ', raw).strip()

        if len(raw) > 5:
            sentences.append((snum, raw))

    return new_chapter, new_paragraph, sentences


# ── 4. Build markdown ─────────────────────────────────────────────────────────

def build_markdown(
        all_parts: list[tuple[int | None, int | None, list[tuple[int, str]]]]
) -> str:
    """Assemble all parsed parts into one AB markdown file.

    Citation format: ॥ AB P.A.S ॥
      P = pañcikā (1–8)
      A = adhyāya number within pañcikā (resets at each new Chapter)
      S = sentence number within adhyāya
    """
    lines = [
        "# Aitareya Brahmana (Devanagari, from TITUS/Aufrecht 1879)\n",
        "Source: TITUS Project, Frankfurt (Jost Gippert). "
        "Based on Th. Aufrecht ed., Bonn 1879. "
        "TITUS transliteration → IAST → Devanagari (indic_transliteration).\n",
    ]

    cur_pancika   = 0
    prev_titus_para = 0     # last "Paragraph: N" seen
    adhyaya_in_p  = 0       # adhyāya counter within current pañcikā

    for new_chapter, new_paragraph, sentences in all_parts:
        if not sentences:
            continue

        # Update pañcikā (Chapter)
        if new_chapter is not None and new_chapter != cur_pancika:
            cur_pancika     = new_chapter
            adhyaya_in_p    = 0
            prev_titus_para = 0

        # Update adhyāya within pañcikā
        if new_paragraph is not None and new_paragraph != prev_titus_para:
            prev_titus_para = new_paragraph
            adhyaya_in_p   += 1
            lines.append(f"\n## AB {cur_pancika}.{adhyaya_in_p}\n")

        for snum, iast_text in sentences:
            dev = to_devanagari(iast_text)
            lines.append(f"{dev} ॥ AB {cur_pancika}.{adhyaya_in_p}.{snum} ॥")

    return "\n".join(lines)


# ── 5. Upload helpers ─────────────────────────────────────────────────────────

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


# ── 6. Main ───────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("parts", nargs="*", type=int,
                    help=f"Part numbers 1–{N_PARTS} (default: all)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Parse and convert only; skip Qdrant upload")
    args = ap.parse_args()
    parts = args.parts if args.parts else list(range(1, N_PARTS + 1))

    out_dir = Path(LOCAL_FOLDER) / FILENAME
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"📥 Fetching {len(parts)} TITUS AB parts "
          f"({parts[0]:03d}–{parts[-1]:03d}) …")

    all_parts: list[tuple[int | None, int | None, list]] = []
    skipped = 0
    total_sentences = 0

    for n in parts:
        html = fetch_part(n)
        if html is None:
            skipped += 1
            continue
        new_chap, new_para, sents = parse_html(html)
        all_parts.append((new_chap, new_para, sents))
        total_sentences += len(sents)

        if n % 50 == 0 or n == parts[-1]:
            print(f"  … part {n:03d} done  "
                  f"(ch={new_chap}, para={new_para}, "
                  f"sents={len(sents)}, total={total_sentences})")

        time.sleep(0.4)   # be polite to TITUS server

    print(f"\n✅ Parsed {len(all_parts)} parts, {total_sentences} sentences "
          f"({skipped} skipped/404)")

    # ── Spot-checks ────────────────────────────────────────────────────────
    # Shunahshepa (AB 7.27–34) and Janamejaya (AB 8.21) are key passages
    harishchandra_hits = 0
    janamejaya_hits    = 0
    for _, _, sents in all_parts:
        for _, iast in sents:
            low = iast.lower()
            if 'hariś' in low or 'harisc' in low:
                harishchandra_hits += 1
            if 'janamejaya' in low:
                janamejaya_hits += 1
    print(f"📍 Harishchandra sentences: {harishchandra_hits}")
    print(f"📍 Janamejaya sentences:    {janamejaya_hits}")

    # ── Build & save markdown ───────────────────────────────────────────────
    markdown = build_markdown(all_parts)
    md_path  = out_dir / f"{FILENAME}.md"
    md_path.write_text(markdown, encoding="utf-8")
    print(f"💾 Markdown: {md_path} ({len(markdown):,} chars)")

    # ── Metadata ────────────────────────────────────────────────────────────
    metadata = {
        "title":   "Aitareya Brahmana",
        "author":  ["Vedic Tradition",
                    "Ed. Th. Aufrecht, Bonn 1879",
                    "TITUS encoding by Fco. Javier Martínez García / Jost Gippert"],
        "subject": ("Aitareya Brahmana of the Rigveda. 8 pañcikās. "
                    "Key passages: Shunahshepa legend (AB 7.27-34, "
                    "Harishchandra / Ikshvaku lineage / royal consecration origin); "
                    "AB 8.21 king register (Janamejaya, Bharata Dauḥṣanti)."),
        "summary": ("Aitareya Brahmana in Devanagari, converted from TITUS "
                    "transliteration (Aufrecht 1879 ed.). Brahmana prose, layer 4. "
                    "Contains the earliest extant king register and the "
                    "Shunahshepa narrative central to Indian kingship ideology."),
        "creator":      "TITUS Project, Frankfurt / Th. Aufrecht",
        "source_url":   TITUS_BASE.replace("{:03d}", "001"),
        "source_format":"titus_html",
        "filename":     FILENAME,
        "preprocessing":"sanskrit",
        "source_type":  "vedic_text",
        "veda":              "aitareya_brahmana",
        "chronology_layer":  4,
        "chronology_name":   "brahmana_prose",
    }
    meta_path = out_dir / f"{FILENAME}_metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False),
                         encoding="utf-8")

    # ── Chunk ───────────────────────────────────────────────────────────────
    doc    = Document(page_content=markdown, metadata=metadata)
    chunks = chunk_doc([doc])
    print(f"✂️  {len(chunks)} chunks (layer 4)")

    if args.dry_run:
        print("\n⚡ --dry-run: skipping Qdrant upload and BM25 resync")
        # Show sample passage (Harishchandra, typically in part ~220s)
        for _, _, sents in all_parts[-80:]:
            for _, iast in sents:
                if 'hariś' in iast.lower() or 'harisc' in iast.lower():
                    dev = to_devanagari(iast)
                    print(f"\nSample Harishchandra sentence:\n  {dev[:200]}")
                    return
        return

    # ── Upload to Qdrant ────────────────────────────────────────────────────
    client = QdrantClient(url=str(QDRANT_URL), api_key=str(QDRANT_API_KEY),
                          timeout=60)
    try:
        client.create_payload_index(
            collection_name=str(COLLECTION_NAME),
            field_name="metadata.filename",
            field_schema=qmodels.PayloadSchemaType.KEYWORD, wait=True)
    except Exception:
        pass

    start = client.get_collection(str(COLLECTION_NAME)).points_count
    print(f"\n🔌 Connected. Points before: {start:,}")

    # Delete old AB points
    client.delete(
        collection_name=str(COLLECTION_NAME),
        points_selector=qmodels.FilterSelector(filter=qmodels.Filter(must=[
            qmodels.FieldCondition(key="metadata.filename",
                                   match=qmodels.MatchValue(value=FILENAME))])),
        wait=True)
    print("🗑️  Deleted old AB points (if any)")

    embed_model = Settings.get_embed_model()
    upload_chunks(client, embed_model, chunks)
    after = client.get_collection(str(COLLECTION_NAME)).points_count
    print(f"✅ AB uploaded. Collection: {start:,} → {after:,} (+{after-start:,})")

    # ── Resync BM25 pickle ──────────────────────────────────────────────────
    print(f"\n{'='*60}\n🔁 Re-syncing BM25 chunks pickle\n{'='*60}")
    documents = []
    for folder in sorted(d for d in Path(LOCAL_FOLDER).iterdir() if d.is_dir()):
        # RV/PB/AB style: single .md per folder
        md   = folder / f"{folder.name}.md"
        meta = folder / f"{folder.name}_metadata.json"
        if md.exists():
            m = (json.loads(meta.read_text()) if meta.exists()
                 else {"filename": folder.name})
            documents.append(Document(
                page_content=md.read_text(encoding="utf-8"), metadata=m))
        else:
            # SB style: multiple per-book .md files in one folder
            meta_f = folder / f"sb_metadata.json"
            m_base = (json.loads(meta_f.read_text())
                      if meta_f.exists() else {"filename": folder.name})
            for sub_md in sorted(folder.glob("*.md")):
                bm = re.search(r"_(\d+)\.md$", sub_md.name)
                m  = ({**m_base, "book": int(bm.group(1)),
                       "title": f"Shatapatha Brahmana Book {bm.group(1)}"}
                      if bm else m_base)
                documents.append(Document(
                    page_content=sub_md.read_text(encoding="utf-8"),
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
