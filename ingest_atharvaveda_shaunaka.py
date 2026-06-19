#!/usr/bin/env python3
"""
Ingest the Atharvaveda (Śaunaka recension) into Qdrant as a layer-3 samhita.

Source: GRETIL single-file Unicode IAST
        https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/1_veda/1_sam/avs___u.htm
        (Orlandi 1991 ed., collated with Roth/Whitney; Books 11-20 revised by
        Arlo Griffiths.) The whole saṃhitā is one HTML file, ~6000 verses,
        20 kāṇḍas.

Why GRETIL and not sanskritdocuments .itx (as the RV ingest uses):
        sanskritdocuments hosts only individual AV *sūkta excerpts* under
        /doc_veda (gosUkta, oShadhIsUkta, …), not a single complete Śaunaka
        saṃhitā .itx the way it carries r01–r10 for the Rigveda. GRETIL is the
        clean digital-native IAST whole-text — same provenance and pipeline
        (IAST → Devanagari, mechanical) already used for SB / VS / TS. The
        local copy in library/vedic_texts/AV_sanskrit/ is unusable for this:
        atharvaveda_complete.txt is encoding-corrupted, and the per-hymn .txt
        files merge all verses onto one line with no per-verse IDs.

Format (one verse spans 2+ half-lines a / c [/ b / e], ID-tagged):
        (AVŚ_1,1.1a) ye triṣaptāḥ pariyanti viśvā rūpāṇi bibhrataḥ |
        (AVŚ_1,1.1c) vācas patir balā teṣāṃ tanvo adya dadhātu me ||1||

Layer:  3  — av_samhita (post-RV samhita; the empty middle layer between the
        RV samhitas (layers 1-2) and the Brahmana prose (layer 4)).

Citation emitted per verse: ॥ AVŚ B.H.V ॥   (kāṇḍa.sūkta.ṛc)

Key passages for the diachronic research goal:
  AVŚ 5.22    : takman (fever) hymn — banishes fever to the Gandhāris,
                Mūjavants, Mahāvṛṣas, Balhikas (NW) and Aṅgas, Magadhas (east):
                a peoples/geography spread signal.
  AVŚ 20.127  : Kuntāpa "Parikṣit" hymn — praise of Parikṣit, king of the Kurus
                (a dynastic / Kuru-realm data point in a samhita layer).
  Material culture throughout: medicine/herbs, agriculture (3.17 ploughing),
  house-building (9.3), commerce (3.15), cattle.

Usage:
    python ingest_atharvaveda_shaunaka.py            # fetch, convert, upload
    python ingest_atharvaveda_shaunaka.py --dry-run  # parse + convert only
    python ingest_atharvaveda_shaunaka.py --self-test # offline parser unit test

After a real run, rebuild the corpus lexicon:
    python build_corpus_lexicon.py
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

GRETIL_URL = ("https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/"
              "1_veda/1_sam/avs___u.htm")
FILENAME = "avs"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
      "Accept": "text/html,*/*"}

# Verse half-line ID:  (AVŚ_<book>,<hymn>.<verse><half>)  e.g. (AVŚ_5,22.1a)
# The script (S with acute) may arrive as Ś or as decomposed S + combining
# acute; match either by allowing the character class plus an optional combiner.
_AV_ID_RE = re.compile(
    r"\(AV[ŚśSS]́?_(\d+),(\d+)\.(\d+)([a-z])\)\s*(.*)"
)
# Trailing verse-end / pada markers to strip from accumulated text:
#   ||5||  ||5 ||  || 5 ||  |1||  single trailing |
_END_MARK_RE = re.compile(r"\|\|?\s*\d*\s*\|\|?\s*$")


# ── 1. Fetch the single GRETIL file ──────────────────────────────────────────

def fetch_text() -> str:
    req = urllib.request.Request(GRETIL_URL, headers=UA)
    raw = urllib.request.urlopen(req, timeout=120).read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    # Strip HTML tags; normalise non-breaking spaces.
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\xa0", " ")
    return text


# ── 2. Parse all verses ──────────────────────────────────────────────────────

def parse_verses(text: str) -> list[tuple[int, int, int, str]]:
    """
    Return [(book, hymn, verse, iast_text), …] in document order.

    Half-lines that share (book,hymn,verse) are concatenated (a + c [+ b + e]).
    We group purely by the verse key in the ID tag — robust against the
    occasional malformed end marker (e.g. 'svāhā |1||', '||4 ||').
    """
    verses: list[tuple[int, int, int, str]] = []
    cur_key: tuple[int, int, int] | None = None
    buf: list[str] = []

    def flush():
        if cur_key and buf:
            body = " ".join(buf)
            body = _END_MARK_RE.sub("", body)          # drop trailing ||n||
            body = body.replace("|", " ")              # internal pada bars
            body = re.sub(r"\s+", " ", body).strip()
            if len(body) > 2:
                verses.append((*cur_key, body))

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        m = _AV_ID_RE.search(line)
        if not m:
            continue
        book, hymn, verse = int(m.group(1)), int(m.group(2)), int(m.group(3))
        payload = m.group(5).strip()
        key = (book, hymn, verse)
        if key != cur_key:
            flush()
            cur_key = key
            buf = []
        buf.append(payload)

    flush()
    return verses


# ── 3. IAST → Devanagari ─────────────────────────────────────────────────────

def to_devanagari(iast: str) -> str:
    return sanscript.transliterate(iast, sanscript.IAST, sanscript.DEVANAGARI)


# ── 4. Build markdown ────────────────────────────────────────────────────────

def build_markdown(verses: list) -> str:
    lines = [
        "# Atharvaveda Saṃhitā — Śaunaka recension (Devanagari, from GRETIL)\n",
        "Source: GRETIL (Orlandi 1991, coll. Roth/Whitney; Books 11-20 rev. "
        "Arlo Griffiths). IAST → Devanagari via indic_transliteration. "
        "Layer 3 (post-RV samhita).\n",
    ]
    cur_hymn = None
    for b, h, v, iast in verses:
        if (b, h) != cur_hymn:
            cur_hymn = (b, h)
            lines.append(f"\n## AVŚ {b}.{h}\n")
        dev = to_devanagari(iast)
        lines.append(f"{dev} ॥ AVŚ {b}.{h}.{v} ॥")
    return "\n".join(lines)


def build_metadata() -> dict:
    return {
        "title": "Atharvaveda Saṃhitā (Śaunaka)",
        "author": ["Vedic Tradition",
                   "GRETIL: ed. Orlandi 1991, coll. Roth/Whitney, "
                   "Books 11-20 rev. Arlo Griffiths"],
        "subject": ("Atharvaveda, Śaunaka recension. 20 kāṇḍas. Material "
                    "culture (medicine, herbs, agriculture, house-building, "
                    "commerce), royal charms. Key passages: takman/peoples "
                    "hymn (AVŚ 5.22 — Gandhāri/Mūjavant/Aṅga/Magadha), Parikṣit "
                    "of the Kurus (AVŚ 20.127)."),
        "summary": ("Atharvaveda Śaunaka saṃhitā in Devanagari, converted from "
                    "GRETIL IAST. Layer 3 (post-RV samhita) — the chronological "
                    "bridge between the RV samhitas (layers 1-2) and the "
                    "Brahmana prose (layer 4). Richest Vedic source for everyday "
                    "material culture; AVŚ 5.22 carries a NW↔east peoples spread "
                    "and AVŚ 20.127 names King Parikṣit of the Kurus."),
        "creator": "GRETIL (Göttingen Register of Electronic Texts in Indian Languages)",
        "source_url": GRETIL_URL,
        "source_format": "iast_html",
        "filename": FILENAME,
        "preprocessing": "sanskrit",
        "source_type": "vedic_text",
        "veda": "atharvaveda_shaunaka",
        "chronology_layer": 3,
        "chronology_name": "av_samhita",
    }


# ── 5. Batched upload (shared pattern with RV / SB scripts) ───────────────────

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


# ── 6. Self-test (offline parser unit test) ──────────────────────────────────

_SAMPLE = """
(AVŚ_1,25.1a) yad agnir āpo adahat praviśya yatrākṛṇvan dharmadhṛto namāṃsi |
(AVŚ_1,25.1c) tatra ta āhuḥ paramaṃ janitraṃ sa naḥ saṃvidvān pari vṛṅgdhi takman ||1||

(AVŚ_5,22.1a) agnis takmānam apa bādhatām itaḥ somo grāvā varuṇaḥ pūtadakṣāḥ |
(AVŚ_5,22.1c) vedir barhiḥ samidhaḥ śośucānā apa dveṣāṃsy amuyā bhavantu ||1||

(AVŚ_5,22.5a) oko asya mūjavanta oko asya mahāvṛṣāḥ |
(AVŚ_5,22.5c) yāvaj jātas takmaṃs tāvān asi balhikeṣu nyocaraḥ ||5||

(AVŚ_2,17.1a) ojo 'sy ojo me dāḥ svāhā |1||

(AVŚ_20,127.1a) upa no na ramasi sūktena vacasā vayaṃ bhadreṇa vacasā vayam ||1||
"""


def self_test():
    verses = parse_verses(_SAMPLE)
    assert verses, "parser returned no verses"
    keys = [(b, h, v) for b, h, v, _ in verses]
    assert (5, 22, 1) in keys, "missing AVŚ 5.22.1"
    assert (20, 127, 1) in keys, "missing AVŚ 20.127.1"
    # 5.22.1 should join both half-lines (a + c)
    text_5_22_1 = next(t for b, h, v, t in verses if (b, h, v) == (5, 22, 1))
    assert "bhavantu" in text_5_22_1 and "agnis" in text_5_22_1, \
        "half-lines not concatenated"
    assert "||" not in text_5_22_1 and "|" not in text_5_22_1, \
        "end/pada markers not stripped"
    # malformed '|1||' marker handled
    text_2_17_1 = next(t for b, h, v, t in verses if (b, h, v) == (2, 17, 1))
    assert text_2_17_1.endswith("svāhā"), f"bad strip: {text_2_17_1!r}"
    print(f"✅ parser self-test passed: {len(verses)} verses")
    print("\nSample Devanagari conversions + citations:")
    for b, h, v, iast in verses:
        if (b, h, v) in {(1, 25, 1), (5, 22, 5), (20, 127, 1)}:
            print(f"  ॥ AVŚ {b}.{h}.{v} ॥  {to_devanagari(iast)[:70]}")
    # takman/peoples names must survive conversion
    md = build_markdown(verses)
    for name in ("तक्मन्", "मूजवन्त", "महावृष", "बल्हिक"):
        assert name in md, f"expected Devanagari name {name} not in output"
    print("✅ takman + peoples names (तक्मन्/मूजवन्त/महावृष/बल्हिक) present")


# ── 7. Main ──────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Fetch, parse, convert, write local .md only; no upload")
    ap.add_argument("--self-test", action="store_true",
                    help="Run offline parser unit test and exit")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return

    out_dir = Path(LOCAL_FOLDER) / FILENAME
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}\n📚 Atharvaveda Śaunaka (GRETIL)\n{'='*60}")
    print(f"⬇️  {GRETIL_URL}")
    text = fetch_text()
    print(f"✅ {len(text):,} chars")

    verses = parse_verses(text)
    assert verses, "No verses parsed — check _AV_ID_RE against the source"
    books = sorted({b for b, _, _, _ in verses})
    hymns = len({(b, h) for b, h, _, _ in verses})
    print(f"✅ {len(verses):,} verses · {hymns} hymns · kāṇḍas {books[0]}–{books[-1]}")

    # Spot-check the two diachronic anchor hymns.
    for (bk, hy), label in [((5, 22), "takman/peoples"),
                            ((20, 127), "Parikṣit/Kuru")]:
        sel = [(b, h, v, t) for b, h, v, t in verses if b == bk and h == hy]
        print(f"📍 AVŚ {bk}.{hy} ({label}): {len(sel)} verses"
              + (f" — v1: {to_devanagari(sel[0][3])[:60]}" if sel else " — MISSING"))

    markdown = build_markdown(verses)
    metadata = build_metadata()
    (out_dir / f"{FILENAME}.md").write_text(markdown, encoding="utf-8")
    (out_dir / f"{FILENAME}_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"💾 {out_dir/f'{FILENAME}.md'} ({len(markdown):,} chars)")

    chunks = chunk_doc([Document(page_content=markdown, metadata=metadata)])
    print(f"✂️  {len(chunks)} chunks (layer 3, av_samhita)")

    if args.dry_run:
        print("⚡ --dry-run: skipping Qdrant upload and BM25 resync")
        for line in markdown.splitlines():
            if "तक्मन्" in line and "मूजवन्त" not in line:
                continue
            if "मूजवन्त" in line or "बल्हिक" in line:
                print(f"\nSample peoples line:\n  {line[:200]}")
                break
        return

    # ── Upload to Qdrant ─────────────────────────────────────────────────────
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

    client.delete(
        collection_name=str(COLLECTION_NAME),
        points_selector=qmodels.FilterSelector(filter=qmodels.Filter(must=[
            qmodels.FieldCondition(key="metadata.filename",
                                   match=qmodels.MatchValue(value=FILENAME))])),
        wait=True)
    print("🗑️  Deleted old AVŚ points (if any)")

    embed_model = Settings.get_embed_model()
    upload_chunks(client, embed_model, chunks)
    after = client.get_collection(str(COLLECTION_NAME)).points_count
    print(f"✅ AVŚ uploaded ({len(chunks)} chunks). Collection: {start:,} → {after:,} (+{after-start:,})")

    # ── Resync BM25 pickle from local_store (RV-style single-md folders) ──────
    print(f"\n{'='*60}\n🔁 Re-syncing BM25 chunks pickle\n{'='*60}")
    documents = []
    for folder in sorted(d for d in Path(LOCAL_FOLDER).iterdir() if d.is_dir()):
        md = folder / f"{folder.name}.md"
        meta_f = folder / f"{folder.name}_metadata.json"
        if md.exists():
            m = json.loads(meta_f.read_text()) if meta_f.exists() else {"filename": folder.name}
            documents.append(Document(page_content=md.read_text(encoding="utf-8"), metadata=m))
        else:
            # SB-style multi-md folders (sb/): keep them in the index too.
            for sub_md in sorted(folder.glob("*.md")):
                meta_name = f"{folder.name}_metadata.json"
                sub_meta_f = folder / meta_name
                m = (json.loads(sub_meta_f.read_text())
                     if sub_meta_f.exists() else {"filename": folder.name})
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
    print("\n🏁 Done. Run `python build_corpus_lexicon.py`, then restart Streamlit.")


if __name__ == "__main__":
    main()
