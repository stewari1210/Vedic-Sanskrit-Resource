# Vedic Sanskrit RAG — Project Status

> Living document. Last updated: 2026-06-10 (session with Claude).

## Mission

A RAG system over the Vedas in **original Sanskrit** (not colonial-era English
translations), queryable in natural language, for probing proper nouns,
rivers, and geography — and tracking how they evolve from earlier to later
Vedic layers. Long-term: LLM translation grounded in Vedic grammar texts
(Macdonell, Monier-Williams) instead of inherited translator bias.

## Architecture

- **Frontend:** Streamlit (`src/sanskrit_tutor_frontend.py`), agentic RAG via
  LangGraph (`src/utils/agentic_rag.py`), Gemini for synthesis
- **Vector store:** Qdrant Cloud, cluster "Vedic-RAG" (free tier, us-east4),
  collection `ancient_history`, 768-dim cosine
- **Embeddings:** `paraphrase-multilingual-mpnet-base-v2` (cross-lingual
  English ↔ Devanagari)
- **Retrieval:** HybridRetriever = semantic (Qdrant) + BM25 (local pickle)
  + Devanagari lexical rescue (substring gazetteer) + MW dictionary expansion
- **Keyword index:** `vector_store/ancient_history/docs_chunks.pkl`
  (must stay in sync with cloud — see Lessons)

## Corpus state

| Source | Status | Notes |
|---|---|---|
| RV Mandalas 1–10 | ✅ indexed (clean) | all from .itx, Devanagari, verse-per-line, layer-tagged; "Who is Sudas?" verified end-to-end |
| Atharvaveda (Shaunaka) | 📋 planned | local copy is IAST (`library/vedic_texts/AV_sanskrit/`); prefer Devanagari source — sanskritdocuments.org has AV .itx |
| Yajurveda (Vajasaneyi) | 📋 planned | no Sanskrit text locally (only Griffith/Sharma English); fetch from sanskritdocuments.org |
| Shatapatha Brahmana | 📋 planned | local file is unusable OCR; need clean source (GRETIL) |

## Evidence sources — kings, clans, lineages, material culture

Target corpus for the diachronic research goal (identify rulers/clans and
their world as it changed: Sarasvati drying, eastward movement). The
genealogical/geographic payload is concentrated in **Brahmana prose**, not
just the samhitas.

| Source | Evidence it carries | Sanskrit availability | Local copy? |
|---|---|---|---|
| **Pancavimsa Brahmana** | सरस्वत्या विनशने sattras (25.10) — locates where the Sarasvati disappears; sattra geography along Sarasvati/Drishadvati | ✅ GRETIL (Kümmel/Griffiths/Kobayashi, transliteration) | English only (Caland OCR) |
| **Shatapatha Brahmana** (Madhyandina) | Videgha Mathava eastward-migration legend (1.4.1); vamsha teacher-lineage lists; king consecrations; eastern (Videha/Kosala) orientation | ✅ GRETIL (Gardner) | English only (Eggeling OCR / archive.org HTML) |
| **Aitareya Brahmana** | Book 8: register of consecrated kings (Janamejaya, Bharata…); Shunahshepa legend (Ikshvaku king Harishchandra) | ✅ GRETIL | ❌ none — must fetch |
| **Vajasaneyi Samhita** (Shukla YV) | Eastern tradition (Yajnavalkya); purushamedha victim catalog (ch. 30–31) is here; pairs with SB | ✅ GRETIL / sanskritdocuments | English only (Griffith) |
| **Taittiriya Samhita** (Krishna YV) | Western/Kuru-region ritual prose; material culture (agriculture, metals, animals) | ✅ TITUS / GRETIL | English only (Sharma/Griffith refs) |
| **Maitrayani & Kathaka Samhitas** | Localized NW/western recensions — geographic contrast signal vs eastern VS/SB | ✅ TITUS | ❌ none |
| **AV Shaunaka** | Material culture: healing, houses, agriculture, king-making | ✅ sanskritdocuments .itx (IAST copy local) | IAST in `library/vedic_texts/AV_sanskrit/` |
| **AV Paippalada** | More historical-geographic material than Shaunaka | ✅ GRETIL (Lubotsky) | ❌ none |
| **Baudhayana Shrauta Sutra** | 18.44 Amavasu/Ayu passage — the most-debated migration text | ✅ GRETIL | ❌ none |

Notes:
- All Sanskrit sources are **romanized transliteration** (IAST/ISO), not
  Devanagari — fine: the pipeline already converts script mechanically.
- The local English translations (Caland PB, Eggeling SB, Griffith) are kept
  as a **reference layer** for cross-checking LLM translations — not corpus.
- Geographic framing: Shukla VS/SB lean **eastern** (Videha/Kosala); Krishna
  TS/MS/KS lean **western/NW** (Kuru region). Taittiriya's South-Indian
  association is its medieval recitation tradition, not its composition. The
  east-west contrast between the two YV branches is itself a migration signal.

### Chunk metadata schema (current)

`veda`, `mandala`, `chronology_layer`, `chronology_name`, `filename`,
`preprocessing: "sanskrit"`, `source_type: "vedic_text"`, plus title/summary.

Chronology layers: **1** = RV family books 2–7 (earliest) · **2** = RV
1/8/9/10 · **3** (reserved) = AV/YV samhitas · **4** (reserved) = Brahmana prose.

## Session log — 2026-06-10

Fixed, in order discovered:

1. **Dead cluster:** old Qdrant cluster (`014ab865…`) deleted; February bulk
   uploads died with it. `.streamlit/secrets.toml` still pointed at it → fixed
   (synced to live cluster `d4611ef7…`; backup `.bak`).
2. **Corrupt text layer:** pymupdf extraction of the XeLaTeX PDFs duplicated
   glyphs and destroyed proper nouns (सुदास appeared 0 times in indexed M7).
   → Rebuilt from clean `.itx` ITRANS masters (sanskritdocuments.org),
   ITRANS→Devanagari via `indic_transliteration`, verse-per-line with hymn
   headers (`rebuild_mandala_clean.py`).
3. **Stale BM25 pickle:** keyword index frozen at April snapshot (old corrupt
   r02 only) → `rebuild_bm25_pickle.py`; now auto-synced after every upload.
4. **Cross-script lexical gap:** Latin queries ("Sudas") can never token-match
   Devanagari; inflection/sandhi (सुदासे, सुदाः) defeats whole-token BM25 even
   in-script → `src/utils/devanagari_lexical.py` (gazetteer ~40 names +
   substring scan) wired into HybridRetriever as "lexical rescue".
5. **CWD-relative paths (root cause of "restart didn't help"):**
   `vector_store`/`local_store` resolved against the process working
   directory; Streamlit read a stale EMPTY pickle elsewhere → BM25 silently
   dead. Paths now anchored to project root in `src/config.py`; empty pickle
   self-heals in `src/utils/index_files.py`.
6. **Upload timeouts:** qdrant-client default 5s write timeout × large
   langchain batches failed on home bandwidth → direct batched upserts
   (batch 32, timeout 60s, 4 retries with backoff).

**Verification:** "Who is Sudas?" now retrieves RV 7.18 / 7.83 chunks
(confirmed end-to-end in Streamlit after fix #5).

7. **Hymn-context expansion (small-to-big retrieval):** 512-char chunks cut
   narrative context — RV 10.60.4 names Ikshvaku but king Asamati is named in
   10.60.2/5, so "which Ikshvaku king?" failed. Top retrieval hits are now
   expanded to the full hymn(s) the chunk touches before synthesis
   (`_expand_hymn_context` in retriever.py; validated on the Asamati case).
   Remaining structural fixes: Anukramani metadata (rishi/patron per hymn,
   comes with VedaWeb ingest) and the entity index.

## Key scripts

| Script | Purpose |
|---|---|
| `rebuild_mandala_clean.py [all\|N…]` | download .itx → clean Devanagari → chunk → delete+upload to cloud → re-sync BM25 pickle |
| `rebuild_bm25_pickle.py` | regenerate keyword-index pickle from `local_store` |
| `test_sudas_retrieval.py` | isolation test: retriever finds Sudas/RV 7.18? |
| `extract_and_upload_r07.py` | (superseded by rebuild_mandala_clean.py) |

## Backlog (rough priority)

1. **Corpus lexicon** (built 2026-06-10, verify in app) — `build_corpus_lexicon.py`
   maps every Devanagari corpus token to normalized ASCII so arbitrary Latin
   spellings (Ikshvaku/Iksvaku) expand to actual surface forms, including
   sandhi-fused ones (यस्येक्ष्वाकु…). Re-run after every corpus change.
   Note: `local_store/` layout is now flat (`local_store/rXX/`); old
   PDF-extract copies moved to `legacy_local_store_pdf_extracts/`.
2. **AV in Devanagari** — check `https://sanskritdocuments.org/doc_veda/` for
   AV .itx; extend rebuild script (layer 3 metadata, AVŚ book.hymn.verse IDs).
3. **YV Vajasaneyi Samhita** — same source/pipeline (layer 3).
4. **Clean Shatapatha Brahmana** — GRETIL transliteration → Devanagari
   (layer 4); replaces garbage OCR file.
5. **Diachronic query tool** — agent tool that detects evolution-over-time
   questions and runs per-layer filtered retrievals for comparison
   (metadata.chronology_layer index already in place).
6. **Gazetteer expansion** — auto-generate Devanagari surface forms for the
   ~44k proper-noun references in the existing variant JSONs
   (`proper_noun_variants.json` etc.); current hand-built list is ~40 names.
7. **Padapatha / sandhi phase** — VedaWeb (github.com/VedaWebProject) has the
   full RV with padapatha + Zurich morphological annotation; foundation for
   the grammar-grounded translation goal.

## Lessons learned

- **Two indexes, one truth:** any script that writes to Qdrant must re-sync
  the BM25 pickle. The rebuild script now does this automatically.
- **Never trust PDF text layers for Devanagari** — always prefer the
  digital-native source (.itx/GRETIL).
- **Silent fallbacks hide failures:** BM25 dying quietly cost hours; loud
  logging (🪷 RESCUE ENTRY) is now in place.
- **Embeddings don't know rare names:** dense retrieval needs a lexical
  channel for proper nouns, regardless of script or chunk quality.
