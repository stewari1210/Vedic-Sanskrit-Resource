#!/usr/bin/env python3
"""
Ingest the Vajasaneyi Samhita (Madhyandina recension) from TITUS into Qdrant.

Source: https://titus.uni-frankfurt.de/texte/etcs/ind/aind/ved/yvw/vs/vs{:03d}.htm
        Files vs001.htm – vs040.htm  (one file per adhyāya, 40 total)
Edition: Albrecht Weber, Berlin 1849 / repr. Varanasi 1972
         Entered by Martin Kümmel, Freiburg 1997; TITUS version by Jost Gippert

Format: TITUS transliteration (same encoding as AB):
          U+02B0 ʰ used for aspirates  (bʰ → bh, dʰ → dh, etc.)
          r + U+0325 combining ring    (r̥  → ṛ)
        Words in <a href="javascript:ci(ID,'...')">WORD</a> links.
        Structure: Paragraph: N  (adhyāya 1–40)
                   Verse: N      (verse number within adhyāya)
                   Sentence: a/b/c/…  (hemistich / pāda labels)

Citation format: VS {adhyāya}.{verse}  e.g. VS 1.1, VS 16.1, VS 40.1

Key passages:
  VS 1     : Opening rites (iṣe tvā ūrje tvā …)
  VS 16    : Śatarudrīya — 66 Rudra litanies  (namas te rudra manyave …)
  VS 17–18 : Vājapeya / Rājasūya ritual formulas
  VS 22–25 : Aśvamedha mantras
  VS 31    : Puruṣa-sūkta (sahasraśīrṣā puruṣaḥ …)
  VS 40    : Īśāvāsya Upaniṣad (īśāvāsyam idaṃ sarvam …)

Usage:
    python ingest_vajasaneyi_samhita.py             # all 40 adhyāyas
    python ingest_vajasaneyi_samhita.py 1 5         # adhyāyas 1–5 only
    python ingest_vajasaneyi_samhita.py --dry-run   # parse + convert; no upload
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
              "ved/yvw/vs/vs{:03d}.htm")
FILENAME  = "yv"
N_PARTS   = 40       # vs001.htm through vs040.htm  (one per adhyāya)
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
      "Accept": "text/html,*/*"}


# ── 1. TITUS → IAST normalisation (identical to AB) ──────────────────────────

def titus_to_iast(text: str) -> str:
    """Normalise TITUS transliteration to standard IAST."""
    text = text.replace('ʰ', 'h')   # bʰ→bh, dʰ→dh, kʰ→kh, etc.
    text = text.replace('r̥', 'ṛ')  # vocalic r  (r + U+0325)
    text = text.replace('R̥', 'Ṛ')
    text = text.replace('l̥', 'ḷ')  # vocalic l (rare in VS)
    return text


def normalize_vedic_iast(text: str) -> str:
    """Strip Vedic accent marks and normalise Vedic anusvāra before conversion.

    TITUS Saṃhitā texts carry Vedic pitch accents:
      U+0301 combining acute  (udātta:   é, á, ā́ …)
      U+0300 combining grave  (anudātta: è, à …)
      U+0302 combining circ.  (svarita in some encodings)

    TITUS also uses m̐ (m + U+0310 combining candrabindu, code '431E') for the
    Vedic anunāsika.  indic_transliteration maps this to ꣳ (U+A8F3, Devanagari
    Extended) rather than standard anusvāra ं.  Replace it with plain ṃ first.
    """
    # Vedic anunāsika m̐ → standard IAST ṃ (m + dot below U+1E43)
    text = text.replace('m̐', 'ṃ')
    text = text.replace('M̐', 'Ṃ')
    # Remove pitch-accent combining marks (leave IAST macrons/dots intact)
    text = text.replace('́', '')   # combining acute
    text = text.replace('̀', '')   # combining grave
    text = text.replace('̂', '')   # combining circumflex
    return text


def strip_vedic_devanagari_marks(text: str) -> str:
    """Remove Vedic combining marks that survived into the Devanagari output.

    These live in two Unicode blocks:
      U+1CD0–U+1CFF  Vedic Extensions
      U+A8E0–U+A8FF  Devanagari Extended
    """
    return ''.join(
        ch for ch in text
        if not (0x1CD0 <= ord(ch) <= 0x1CFF or 0xA8E0 <= ord(ch) <= 0xA8FF)
    )


def clean_titus_text(text: str) -> str:
    """Remove TITUS-specific markers."""
    # Avagraha / elision: Armenian apostrophe U+055A, plain apostrophe
    text = re.sub(r"['՚]\d*", '', text)
    # Line-continuation backslash (pāda separator \ and verse-end \\)
    text = text.replace('\\', ' ')
    # Sandhi markers
    text = re.sub(r'[=+]', '', text)
    # Collapse multiple spaces
    text = re.sub(r'  +', ' ', text)
    return text.strip()


def to_devanagari(iast: str) -> str:
    iast = titus_to_iast(iast)
    iast = normalize_vedic_iast(iast)
    iast = clean_titus_text(iast)
    dev  = sanscript.transliterate(iast, sanscript.IAST, sanscript.DEVANAGARI)
    return strip_vedic_devanagari_marks(dev)


# ── 2. Fetch ──────────────────────────────────────────────────────────────────

def fetch_part(n: int) -> str | None:
    """Fetch one TITUS VS page. Returns raw HTML or None on 404."""
    url = TITUS_BASE.format(n)
    req = urllib.request.Request(url, headers=UA)
    try:
        raw = urllib.request.urlopen(req, timeout=30).read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"⚠️  Adhyāya {n:02d}: 404 — skipping")
            return None
        raise
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


# ── 3. Parse ─────────────────────────────────────────────────────────────────

# Words in TITUS pages: <a href="javascript:ci(ID,'enc')">IAST_word</a>
_WORD_TAG_RE  = re.compile(
    r'<a\s[^>]*href\s*=\s*"javascript:ci\([^)]+\)"[^>]*>([^<]+)</a>', re.I)
_TAG_RE       = re.compile(r'<[^>]+>')
_PARAGRAPH_RE = re.compile(r'Paragraph:\s*(\d+)')
_VERSE_RE     = re.compile(r'Verse:\s*(\d+)')
_SENTENCE_RE  = re.compile(r'Sentence:\s*([a-z])')   # VS uses letters a/b/c/…

# Boilerplate to discard
_SKIP_RE = re.compile(
    r'(TITUS|White\s+Yajur|Vajasaneyi|Madhyandina|Previous\s+part|Next\s+part|'
    r'This\s+text\s+is\s+part|Copyright|Frankfurt|No\s+parts\s+of|'
    r'meta-|title:|Jost\s+Gippert|Albrecht\s+Weber|Martin\s+K.mmel|'
    r'Freiburg|Varanasi|Berlin|Chowkhamba|entered|converted|repr\.)',
    re.IGNORECASE)


def parse_html(html: str) -> tuple[int | None, list[tuple[int, str]]]:
    """Parse one TITUS VS HTML page (one adhyāya).

    Returns:
        adhyaya   — adhyāya number from 'Paragraph: N'
        verses    — list of (verse_n, combined_iast_text)
                    All hemistich sentences (a/b/c/…) are joined into one string.
    """
    raw_html = html_lib.unescape(html)
    raw_html = raw_html.replace('\xa0', ' ')

    # Replace each word-link with the visible word + space
    text = _WORD_TAG_RE.sub(lambda m: m.group(1) + ' ', raw_html)
    text = _TAG_RE.sub(' ', text)
    text = re.sub(r'[ \t]+', ' ', text)

    # Adhyāya number
    pm = _PARAGRAPH_RE.search(text)
    adhyaya = int(pm.group(1)) if pm else None

    # Footer cutoff
    footer = text.find('This text is part of')
    if footer == -1:
        footer = len(text)
    text = text[:footer]

    # Locate all verse positions
    verse_positions = [(m.start(), int(m.group(1)))
                       for m in _VERSE_RE.finditer(text)]

    verses = []
    for i, (vpos, vnum) in enumerate(verse_positions):
        # Content ends at next verse (or footer)
        end = verse_positions[i + 1][0] if i + 1 < len(verse_positions) else len(text)
        verse_block = text[vpos:end]

        # Split on Sentence: [a-z] markers and collect content
        sent_positions = [(m.start(), m.group(1))
                          for m in _SENTENCE_RE.finditer(verse_block)]

        parts = []
        for j, (spos, slabel) in enumerate(sent_positions):
            content_start = spos + len(f'Sentence: {slabel}')
            content_end   = sent_positions[j + 1][0] if j + 1 < len(sent_positions) else len(verse_block)
            chunk = verse_block[content_start:content_end].strip()
            # Drop boilerplate lines
            lines = [l.strip() for l in chunk.splitlines()
                     if l.strip() and not _SKIP_RE.search(l)]
            parts.append(' '.join(lines))

        combined = ' '.join(p for p in parts if p)
        combined = re.sub(r'  +', ' ', combined).strip()

        if len(combined) > 5:
            verses.append((vnum, combined))

    return adhyaya, verses


# ── 4. Build markdown ─────────────────────────────────────────────────────────

def build_markdown(all_parts: list[tuple[int | None, list[tuple[int, str]]]]) -> str:
    """Assemble all parsed adhyāyas into one VS markdown file.

    Citation format: ॥ VS {adhyāya}.{verse} ॥
    """
    lines = [
        "# Vajasaneyi Samhita (Devanagari, from TITUS/Weber 1849)\n",
        "Source: TITUS Project, Frankfurt (Jost Gippert). "
        "Madhyandina recension, ed. Albrecht Weber, Berlin 1849. "
        "TITUS transliteration → IAST → Devanagari (indic_transliteration).\n",
    ]

    for adhyaya, verses in all_parts:
        if not verses:
            continue
        lines.append(f"\n## VS {adhyaya}\n")
        for vnum, iast_text in verses:
            dev = to_devanagari(iast_text)
            citation = f"VS {adhyaya}.{vnum}"
            lines.append(f"{dev} ॥ {citation} ॥")

    return "\n".join(lines)


# ── 5. Upload helpers (identical to AB) ───────────────────────────────────────

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
                    help=f"Adhyāya numbers 1–{N_PARTS} (default: all)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Parse and convert only; skip Qdrant upload")
    args = ap.parse_args()
    parts = args.parts if args.parts else list(range(1, N_PARTS + 1))

    out_dir = Path(LOCAL_FOLDER) / FILENAME
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"📥 Fetching {len(parts)} TITUS VS adhyāyas "
          f"({parts[0]:02d}–{parts[-1]:02d}) …")

    all_parts: list[tuple[int | None, list]] = []
    skipped = 0
    total_verses = 0

    for n in parts:
        html = fetch_part(n)
        if html is None:
            skipped += 1
            continue
        adhyaya, verses = parse_html(html)
        all_parts.append((adhyaya, verses))
        total_verses += len(verses)

        if n % 10 == 0 or n == parts[-1]:
            print(f"  … adhyāya {n:02d} done  "
                  f"(adhyāya={adhyaya}, verses={len(verses)}, total={total_verses})")

        time.sleep(0.4)  # be polite to TITUS server

    print(f"\n✅ Parsed {len(all_parts)} adhyāyas, {total_verses} verses "
          f"({skipped} skipped/404)")

    # ── Spot-checks ─────────────────────────────────────────────────────────
    rudra_hits   = sum(1 for _, vs in all_parts for _, t in vs if 'rudra' in t.lower())
    purusa_hits  = sum(1 for _, vs in all_parts for _, t in vs if 'sahasra' in t.lower())
    isavasy_hits = sum(1 for _, vs in all_parts for _, t in vs if 'īśā' in t.lower() or 'isa' in t.lower())
    print(f"📍 Rudra verses  (VS 16):  {rudra_hits}")
    print(f"📍 Sahasra verses (VS 31): {purusa_hits}")
    print(f"📍 Īśā verses     (VS 40): {isavasy_hits}")

    # ── Dry-run sample ──────────────────────────────────────────────────────
    if args.dry_run:
        print("\n── Sample output (first 5 verses of VS 1) ──")
        for adhyaya, verses in all_parts[:1]:
            for vnum, iast in verses[:5]:
                dev = to_devanagari(iast)
                print(f"  VS {adhyaya}.{vnum}: {dev[:80]}…")

        print("\n── VS 16 sample (Śatarudrīya, first 3 verses) ──")
        for adhyaya, verses in all_parts:
            if adhyaya == 16:
                for vnum, iast in verses[:3]:
                    dev = to_devanagari(iast)
                    print(f"  VS 16.{vnum}: {dev[:80]}…")
                break

        print(f"\n⚡ --dry-run: skipping Qdrant upload")
        return

    # ── Build & save markdown ────────────────────────────────────────────────
    markdown = build_markdown(all_parts)
    md_path  = out_dir / f"{FILENAME}.md"
    md_path.write_text(markdown, encoding="utf-8")
    print(f"💾 Markdown: {md_path} ({len(markdown):,} chars)")

    # ── Metadata ─────────────────────────────────────────────────────────────
    metadata = {
        "title":   "Vajasaneyi Samhita",
        "author":  ["Vedic Tradition",
                    "Ed. Albrecht Weber, Berlin 1849",
                    "TITUS encoding by Martin Kümmel / Jost Gippert"],
        "subject": ("Vajasaneyi Samhita, Madhyandina recension (White Yajurveda). "
                    "40 adhyāyas. Key passages: VS 1 opening rites; "
                    "VS 16 Śatarudrīya (66 Rudra litanies); "
                    "VS 17–18 Vājapeya / Rājasūya; "
                    "VS 22–25 Aśvamedha; "
                    "VS 31 Puruṣa-sūkta; VS 40 Īśāvāsya Upaniṣad."),
        "summary": ("Vajasaneyi Samhita in Devanagari, converted from TITUS "
                    "transliteration (Weber 1849 ed.). Saṃhitā layer. "
                    "Contains the Śatarudrīya, Puruṣa-sūkta, "
                    "and the Īśāvāsya Upaniṣad."),
        "creator":      "TITUS Project, Frankfurt / Albrecht Weber",
        "source_url":   TITUS_BASE.replace("{:03d}", "001"),
        "source_format":"titus_html",
        "filename":     FILENAME,
        "preprocessing":"sanskrit",
        "source_type":  "vedic_text",
        "veda":              "vajasaneyi_samhita",
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

    # Delete old VS points
    client.delete(
        collection_name=str(COLLECTION_NAME),
        points_selector=qmodels.FilterSelector(filter=qmodels.Filter(must=[
            qmodels.FieldCondition(key="metadata.filename",
                                   match=qmodels.MatchValue(value=FILENAME))])),
        wait=True)
    print("🗑️  Deleted old VS points (if any)")

    embed_model = Settings.get_embed_model()
    upload_chunks(client, embed_model, chunks)
    after = client.get_collection(str(COLLECTION_NAME)).points_count
    print(f"✅ VS uploaded. Collection: {start:,} → {after:,} (+{after-start:,})")

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
