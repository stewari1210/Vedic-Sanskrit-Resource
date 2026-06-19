#!/usr/bin/env python3
"""
Ingest the Taittiriya Samhita (Kṛṣṇa / Black Yajurveda) from TITUS into Qdrant.

Source: https://titus.uni-frankfurt.de/texte/etcs/ind/aind/ved/yvs/ts/ts{:03d}.htm
        Files ts001.htm – ts0??.htm  (one file per Prapāṭhaka / Chapter)
Edition: Albrecht Weber, Leipzig 1871–72; Makoto Fushimi (Ōsaka)
         TITUS encoding by Jost Gippert

Format: Same TITUS transliteration as VS/AB:
          U+02B0 ʰ used for aspirates  (bʰ → bh, kʰ → kh …)
          r + U+0325 combining ring    (r̥  → ṛ)
        Words in <a href="javascript:ci(ID,'...')">WORD</a> links.
        Structure: Book: N       (Kāṇḍa 1–7)
                   Chapter: N    (Prapāṭhaka within kāṇḍa)
                   Paragraph: N  (Anuvāka within prapāṭhaka)
                   Verse: N
                   Sentence: N=letter  (hemistich/pāda labels)
                     (sentence 1 sometimes has no =letter)

Variant manuscript markers (stripped before conversion):
        {F …}   Freiburg ms.
        {W …}   another witness
        {ASS …} Āpastamba Śrauta Sūtra citation
        {BI …}  another witness
        {GOLS …} Gottingen / other ms.

Citation format: TS {kāṇḍa}.{prapāṭhaka}.{anuvāka}.{verse}
                 e.g. TS 1.1.1.1

Key passages:
  TS 1.1   : Opening rites (agnaye tvā …)
  TS 1.8   : Aśvamedha formulas
  TS 2.5   : Śatarudrīya section
  TS 4.5   : Puruṣa-sūkta in YV recension
  TS 5     : Soma ritual
  TS 6–7   : Pravargya and other solemn rites

Usage:
    python ingest_taittiriya_samhita.py             # all prapāṭhakas
    python ingest_taittiriya_samhita.py 1 5         # files ts001–ts005 only
    python ingest_taittiriya_samhita.py --dry-run   # parse + convert; no upload
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
              "ved/yvs/ts/ts{:03d}.htm")
FILENAME  = "ts"
N_PARTS   = 100      # upper bound; graceful 404 handling terminates early
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
      "Accept": "text/html,*/*"}


# ── 1. TITUS → IAST normalisation ────────────────────────────────────────────

def titus_to_iast(text: str) -> str:
    """Normalise TITUS transliteration to standard IAST."""
    text = text.replace('ʰ', 'h')   # bʰ→bh, dʰ→dh, kʰ→kh, etc.
    text = text.replace('r̥', 'ṛ')  # vocalic r  (r + U+0325)
    text = text.replace('R̥', 'Ṛ')
    text = text.replace('l̥', 'ḷ')  # vocalic l (rare)
    return text


def normalize_vedic_iast(text: str) -> str:
    """Strip Vedic accent marks and normalise Vedic anusvāra before conversion.

    TITUS Saṃhitā texts carry Vedic pitch accents:
      U+0301 combining acute  (udātta:   é, á, ā́ …)
      U+0300 combining grave  (anudātta: è, à …)
      U+0302 combining circ.  (svarita in some encodings)

    TITUS also uses m̐ (m + U+0310 combining candrabindu, code '431E') for the
    Vedic anunāsika.  indic_transliteration maps this to ꣳ (U+A8F3) rather than
    standard anusvāra ं.  Replace it with plain ṃ first.
    """
    text = text.replace('m̐', 'ṃ')
    text = text.replace('M̐', 'Ṃ')
    text = text.replace('́', '')   # combining acute  U+0301
    text = text.replace('̀', '')   # combining grave  U+0300
    text = text.replace('̂', '')   # combining circ.  U+0302
    return text


def strip_vedic_devanagari_marks(text: str) -> str:
    """Remove Vedic combining marks that survived into the Devanagari output.

    Two Unicode blocks:
      U+1CD0–U+1CFF  Vedic Extensions
      U+A8E0–U+A8FF  Devanagari Extended
    """
    return ''.join(
        ch for ch in text
        if not (0x1CD0 <= ord(ch) <= 0x1CFF or 0xA8E0 <= ord(ch) <= 0xA8FF)
    )


def strip_variant_markers(text: str) -> str:
    """Remove TS variant manuscript markers: {F …}, {W …}, {ASS …} etc."""
    # Remove entire {KEY text} blocks
    text = re.sub(r'\{[A-Z][^}]*\}', '', text)
    # Remove any stray opening/closing braces
    text = re.sub(r'[{}]', '', text)
    return text


def clean_titus_text(text: str) -> str:
    """Remove TITUS-specific markers."""
    # Avagraha / elision: Armenian apostrophe U+055A, plain apostrophe
    text = re.sub(r"['՚]\d*", '', text)
    # Line-continuation backslash (pāda separator \ and verse-end //)
    text = text.replace('//', ' ').replace('\\', ' ')
    # Strip any TITUS structural labels that bled into sentence content
    # e.g. "Paragraph: 3 Verse: 1 Sentence: 2=b" → ""
    text = _STRUCT_LABEL_RE.sub(' ', text)
    # Sandhi markers
    text = re.sub(r'[=+]', '', text)
    # Collapse multiple spaces
    text = re.sub(r'  +', ' ', text)
    return text.strip()


def to_devanagari(iast: str) -> str:
    iast = titus_to_iast(iast)
    iast = normalize_vedic_iast(iast)
    iast = strip_variant_markers(iast)
    iast = clean_titus_text(iast)
    dev  = sanscript.transliterate(iast, sanscript.IAST, sanscript.DEVANAGARI)
    return strip_vedic_devanagari_marks(dev)


# ── 2. Fetch ──────────────────────────────────────────────────────────────────

def fetch_part(n: int) -> str | None:
    """Fetch one TITUS TS page. Returns raw HTML or None on 404."""
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

_WORD_TAG_RE  = re.compile(
    r'<a\s[^>]*href\s*=\s*"javascript:ci\([^)]+\)"[^>]*>([^<]+)</a>', re.I)
_TAG_RE       = re.compile(r'<[^>]+>')

_BOOK_RE      = re.compile(r'Book:\s*(\d+)')
_CHAPTER_RE   = re.compile(r'Chapter:\s*(\d+)')
_PARAGRAPH_RE = re.compile(r'Paragraph:\s*(\d+)')
_VERSE_RE     = re.compile(r'Verse:\s*(\d+)')
# Sentence: 1  or  Sentence: 1=a
_SENTENCE_RE  = re.compile(r'Sentence:\s*(\d+)(?:=([a-z]))?')

_SKIP_RE = re.compile(
    r'(TITUS|Taittiriya|Taittir|Black\s+Yajur|Previous\s+part|Next\s+part|'
    r'This\s+text\s+is\s+part|Copyright|Frankfurt|No\s+parts\s+of|'
    r'meta-|title:|Jost\s+Gippert|Albrecht\s+Weber|Makoto\s+Fushimi|'
    r'Leipzig|Freiburg|entered|converted|repr\.)',
    re.IGNORECASE)

# Strip TITUS structural labels that may bleed into sentence content
_STRUCT_LABEL_RE = re.compile(
    r'\b(?:Book|Chapter|Paragraph|Verse|Sentence):\s*[\d=a-zA-Z]+\b', re.I)

# A "verse record" carries its full hierarchical address
VerseTuple = tuple  # (book, chapter, paragraph, verse_n, combined_iast)


def parse_html(html: str,
               default_book: int | None = None,
               default_chapter: int | None = None) -> list[VerseTuple]:
    """Parse one TITUS TS HTML page.

    Returns a flat list of (book, chapter, paragraph, verse_n, combined_iast).

    default_book / default_chapter: carry state across file boundaries.
    TITUS only emits "Book: N" / "Chapter: N" at the first occurrence in a
    sequence; subsequent files within the same Kāṇḍa/Prapāṭhaka don't repeat
    those labels, so we inherit the last known values.
    """
    raw_html = html_lib.unescape(html)
    raw_html = raw_html.replace('\xa0', ' ')

    # Replace each word-link with the visible word + space
    text = _WORD_TAG_RE.sub(lambda m: m.group(1) + ' ', raw_html)
    text = _TAG_RE.sub(' ', text)
    text = re.sub(r'[ \t]+', ' ', text)

    # Footer cutoff
    footer = text.find('This text is part of')
    if footer == -1:
        footer = len(text)
    text = text[:footer]

    # Collect all structural markers with their positions
    events = []  # (pos, kind, value)
    for m in _BOOK_RE.finditer(text):
        events.append((m.start(), 'book', int(m.group(1))))
    for m in _CHAPTER_RE.finditer(text):
        events.append((m.start(), 'chapter', int(m.group(1))))
    for m in _PARAGRAPH_RE.finditer(text):
        events.append((m.start(), 'paragraph', int(m.group(1))))
    for m in _VERSE_RE.finditer(text):
        events.append((m.start(), 'verse', int(m.group(1))))
    for m in _SENTENCE_RE.finditer(text):
        # value = (sentence_number, letter_or_None, start_of_content)
        content_start = m.end()
        events.append((m.start(), 'sentence', (int(m.group(1)), m.group(2), content_start)))
    events.sort(key=lambda e: e[0])

    # Walk events, accumulating sentences per verse
    results: list[VerseTuple] = []
    # Initialise from caller-supplied defaults so book/chapter persist across files
    cur_book    = default_book
    cur_chapter = default_chapter
    cur_para = cur_verse = None
    cur_sentences: list[tuple[int, tuple]] = []   # (pos, value) pairs

    def flush_verse(end_pos: int | None = None):
        """Combine accumulated sentences into one verse record.

        end_pos: position of the structural event that triggered this flush.
                 Bounds the last sentence so it doesn't swallow subsequent
                 paragraphs/verses (the core bug: without this, last sentence
                 ran to len(text), picking up all remaining structural labels
                 which then got transliterated into Devanagari garbage).
        """
        nonlocal cur_sentences
        if cur_verse is None or not cur_sentences:
            cur_sentences = []
            return
        if end_pos is None:
            end_pos = len(text)
        parts = []
        for idx, (spos, sval) in enumerate(cur_sentences):
            _, _, c_start = sval
            next_spos = (cur_sentences[idx + 1][0]
                         if idx + 1 < len(cur_sentences) else end_pos)
            chunk = text[c_start:next_spos].strip()
            lines = [l.strip() for l in chunk.splitlines()
                     if l.strip() and not _SKIP_RE.search(l)]
            parts.append(' '.join(lines))
        combined = re.sub(r'  +', ' ', ' '.join(p for p in parts if p)).strip()
        if len(combined) > 5:
            results.append((cur_book, cur_chapter, cur_para, cur_verse, combined))
        cur_sentences = []

    for pos, kind, value in events:
        if kind == 'book':
            flush_verse(pos)
            cur_book    = value
            cur_chapter = cur_para = cur_verse = None
        elif kind == 'chapter':
            flush_verse(pos)
            cur_chapter = value
            cur_para = cur_verse = None
        elif kind == 'paragraph':
            flush_verse(pos)
            cur_para  = value
            cur_verse = None
        elif kind == 'verse':
            flush_verse(pos)
            cur_verse     = value
            cur_sentences = []
        elif kind == 'sentence':
            cur_sentences.append((pos, value))

    flush_verse()   # final flush: end_pos = len(text) is correct for last verse
    return results


# ── 4. Build markdown ─────────────────────────────────────────────────────────

def build_markdown(all_verses: list[VerseTuple]) -> str:
    """Assemble all parsed verses into one TS markdown file.

    Citation format: ॥ TS {book}.{chapter}.{paragraph}.{verse} ॥
    Sections are grouped by Book > Chapter > Paragraph.
    """
    lines = [
        "# Taittiriya Samhita (Devanagari, from TITUS/Weber 1871–72)\n",
        "Source: TITUS Project, Frankfurt (Jost Gippert). "
        "Black Yajurveda (Kṛṣṇa YV), ed. Albrecht Weber, Leipzig 1871–72. "
        "TITUS transliteration → IAST → Devanagari (indic_transliteration).\n",
    ]

    prev_book = prev_chapter = prev_para = None
    for book, chapter, para, vnum, iast_text in all_verses:
        if book != prev_book:
            lines.append(f"\n## TS {book}\n")
            prev_book = book
            prev_chapter = prev_para = None
        if chapter != prev_chapter:
            lines.append(f"\n### TS {book}.{chapter}\n")
            prev_chapter = chapter
            prev_para = None
        if para != prev_para:
            lines.append(f"\n#### TS {book}.{chapter}.{para}\n")
            prev_para = para

        dev      = to_devanagari(iast_text)
        citation = f"TS {book}.{chapter}.{para}.{vnum}"
        lines.append(f"{dev} ॥ {citation} ॥")

    return "\n".join(lines)


# ── 5. Upload helpers (identical to VS) ───────────────────────────────────────

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
                    help=f"File numbers 1–{N_PARTS} to fetch (default: all)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Parse and convert only; skip Qdrant upload")
    args = ap.parse_args()
    parts = args.parts if args.parts else list(range(1, N_PARTS + 1))

    out_dir = Path(LOCAL_FOLDER) / FILENAME
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"📥 Fetching TS from TITUS (files {parts[0]:03d}–{parts[-1]:03d}, "
          f"404 terminates gracefully) …")

    all_verses: list[VerseTuple] = []
    skipped = 0
    consecutive_404 = 0
    last_book: int | None = None     # carried across files
    last_chapter: int | None = None
    seen_hashes: set[int] = set()    # dedup: skip files identical to a prior file

    for n in parts:
        html = fetch_part(n)
        if html is None:
            skipped += 1
            consecutive_404 += 1
            if consecutive_404 >= 3:
                print(f"   3 consecutive 404s — assuming end of corpus at part {n-2}")
                break
            continue
        consecutive_404 = 0

        verses = parse_html(html,
                            default_book=last_book,
                            default_chapter=last_chapter)

        # Deduplicate: TITUS serves ts043/ts045 and ts044/ts046 with identical
        # verse content but slightly different HTML wrappers (navigation links,
        # timestamps), so hash(html) differs. Hash the extracted verse tuples instead.
        content_hash = hash(tuple(verses))
        if content_hash in seen_hashes:
            print(f"  ts{n:03d}: content identical to a prior file — skipping")
            skipped += 1
            continue
        seen_hashes.add(content_hash)
        all_verses.extend(verses)

        # Update carried state from whatever this file set
        for v in verses:
            if v[0] is not None:
                last_book = v[0]
            if v[1] is not None:
                last_chapter = v[1]

        if verses:
            b, c, p = verses[0][0], verses[0][1], verses[0][2]
            print(f"  ts{n:03d}: TS {b}.{c}.{p}… → {len(verses)} verses "
                  f"(total {len(all_verses)})")
        else:
            print(f"  ts{n:03d}: 0 verses parsed")

        time.sleep(0.4)  # be polite to TITUS server

    print(f"\n✅ Parsed {len(all_verses)} verses across all prapāṭhakas "
          f"({skipped} skipped/404)")

    # ── Spot-checks ─────────────────────────────────────────────────────────
    books = sorted({v[0] for v in all_verses if v[0]})
    print(f"📍 Books (Kāṇḍas) found: {books}")
    for bk in books:
        count = sum(1 for v in all_verses if v[0] == bk)
        print(f"   Kāṇḍa {bk}: {count} verses")

    # ── Dry-run sample ──────────────────────────────────────────────────────
    if args.dry_run:
        print("\n── Sample output (first 8 verses of TS 1.1.1) ──")
        sample = [v for v in all_verses if v[0] == 1 and v[1] == 1 and v[2] == 1]
        for b, c, p, vnum, iast in sample[:8]:
            dev = to_devanagari(iast)
            print(f"  TS {b}.{c}.{p}.{vnum}: {dev[:80]}…")

        if len(books) > 1:
            print(f"\n── Sample: first 3 verses of Kāṇḍa {books[1]} ──")
            for b, c, p, vnum, iast in [v for v in all_verses if v[0] == books[1]][:3]:
                dev = to_devanagari(iast)
                print(f"  TS {b}.{c}.{p}.{vnum}: {dev[:80]}…")

        print(f"\n⚡ --dry-run: skipping Qdrant upload")
        return

    # ── Build & save markdown ────────────────────────────────────────────────
    markdown = build_markdown(all_verses)
    md_path  = out_dir / f"{FILENAME}.md"
    md_path.write_text(markdown, encoding="utf-8")
    print(f"💾 Markdown: {md_path} ({len(markdown):,} chars)")

    # ── Metadata ─────────────────────────────────────────────────────────────
    metadata = {
        "title":   "Taittiriya Samhita",
        "author":  ["Vedic Tradition (Taittiriya / Kṛṣṇa Yajurveda school)",
                    "Ed. Albrecht Weber, Leipzig 1871–72",
                    "TITUS encoding by Jost Gippert / Makoto Fushimi"],
        "subject": ("Taittiriya Samhita, Black Yajurveda (Kṛṣṇa YV). "
                    "7 Kāṇḍas. Key passages: TS 1.1 opening rites; "
                    "TS 1.8 Aśvamedha; TS 2.5 Śatarudrīya; "
                    "TS 4.5 Puruṣa-sūkta; TS 5 Soma ritual; "
                    "TS 6–7 Pravargya and solemn rites."),
        "summary": ("Taittiriya Samhita in Devanagari, converted from TITUS "
                    "transliteration (Weber 1871–72 ed.). Saṃhitā layer. "
                    "Contains mantras for all major Vedic rites together with "
                    "embedded Brāhmaṇa passages (unique to Kṛṣṇa YV)."),
        "creator":      "TITUS Project, Frankfurt / Albrecht Weber",
        "source_url":   TITUS_BASE.replace("{:03d}", "001"),
        "source_format":"titus_html",
        "filename":     FILENAME,
        "preprocessing":"sanskrit",
        "source_type":  "vedic_text",
        "veda":              "taittiriya_samhita",
        "chronology_layer":  2,
        "chronology_name":   "samhita",
    }
    meta_path = out_dir / f"{FILENAME}_metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False),
                         encoding="utf-8")

    # ── Chunk ─────────────────────────────────────────────────────────────────
    doc    = Document(page_content=markdown, metadata=metadata)
    chunks = chunk_doc([doc])
    print(f"✂️  {len(chunks)} chunks (layer 2 — saṃhitā)")

    # ── Upload to Qdrant ─────────────────────────────────────────────────────
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

    # Delete old TS points
    client.delete(
        collection_name=str(COLLECTION_NAME),
        points_selector=qmodels.FilterSelector(filter=qmodels.Filter(must=[
            qmodels.FieldCondition(key="metadata.filename",
                                   match=qmodels.MatchValue(value=FILENAME))])),
        wait=True)
    print("🗑️  Deleted old TS points (if any)")

    embed_model = Settings.get_embed_model()
    upload_chunks(client, embed_model, chunks)
    after = client.get_collection(str(COLLECTION_NAME)).points_count
    print(f"✅ TS uploaded. Collection: {start:,} → {after:,} (+{after-start:,})")

    # ── Resync BM25 pickle ───────────────────────────────────────────────────
    print(f"\n{'='*60}\n🔁 Re-syncing BM25 chunks pickle\n{'='*60}")
    documents = []
    for folder in sorted(d for d in Path(LOCAL_FOLDER).iterdir() if d.is_dir()):
        md   = folder / f"{folder.name}.md"
        meta = folder / f"{folder.name}_metadata.json"
        if md.exists():
            m = (json.loads(meta.read_text()) if meta.exists()
                 else {"filename": folder.name})
            documents.append(Document(
                page_content=md.read_text(encoding="utf-8"), metadata=m))
        else:
            # SB style: multiple per-book .md files in one folder
            meta_f = folder / "sb_metadata.json"
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
