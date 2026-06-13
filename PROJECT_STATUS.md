# Vedic Sanskrit RAG — Project Status

> Living document. Last updated: 2026-06-13 (session with Claude).

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
| Pancavimsa Brahmana | ✅ indexed | `ingest_pancavimsa_brahmana.py`; GRETIL IAST→Devanagari, ॥ PB B.C.P ॥ markers, layer 4; BM25 pickle patched; PB 25.10.16 verified as #1 for vinashana query |
| Shatapatha Brahmana | ✅ script ready | `ingest_shatapatha_brahmana.py`; 14 GRETIL books, parser validated (SB 1.4.1 Videgha Mathava); run `python ingest_shatapatha_brahmana.py` on Mac |
| Aitareya Brahmana | ✅ script ready | `ingest_aitareya_brahmana.py`; TITUS Frankfurt, 285 pages (ab001–ab285), TITUS→IAST→Devanagari; run script to upload |
| Atharvaveda (Shaunaka) | 📋 planned | local copy is IAST (`library/vedic_texts/AV_sanskrit/`); prefer Devanagari source — sanskritdocuments.org has AV .itx |
| Yajurveda (Vajasaneyi) | 📋 planned | no Sanskrit text locally (only Griffith/Sharma English); fetch from sanskritdocuments.org |

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

## Session log — 2026-06-12 (PB ingest + retrieval fixes)

### Retrieval improvements (warfare query)
- **THEME_GAZETTEER** added to `devanagari_lexical.py`: English research themes
  (warfare, weapons, forts, metals, chariots, sacrifice, migration, lineage, etc.)
  map to corpus-verified Devanagari terms. Validation: "warfare" → RV 6.75
  (वज्र×291, वर्म×27, इषु+धन्व hits), RV 10.103 across early/late layers.
- **SYNTHESIS_DOC_BUDGET = 12** in `agentic_rag.py` (was hardcoded 5).
- **Diachronic synthesis prompt** added: layer-structured answer when comparison
  query detected; states corpus-coverage limits honestly.
- **_SKIP set** pruned: "king", "river", "battle", "lineage" etc. removed so
  they expand via THEME_GAZETTEER instead of being silently dropped.

### Pancavimsa Brahmana ingest script
- `ingest_pancavimsa_brahmana.py` written; fetches GRETIL single-file HTML
  (Kümmel/Griffiths/Kobayashi, all 25 books), parses `(PB B.C.P) text`
  paragraphs, converts IAST→Devanagari, chunks and uploads to Qdrant as
  layer-4 metadata, re-syncs BM25 pickle.
- Dry-run parser validated (PB 25.10 Sarasvati vinashana passage confirmed
  present and parseable).
- GAZETTEER extended: vinashana, sattra, drishadvati, videha, mathava,
  harishchandra, shunahshepa.
- THEME_GAZETTEER extended: sattra, sacrifice, ritual, migration, lineage, king.

**To complete PB ingest:** run `python ingest_pancavimsa_brahmana.py` on Mac,
then `python build_corpus_lexicon.py` to rebuild the token lexicon.

## Session log — 2026-06-13 (SB ingest + AB source gap + retrieval fixes)

### Shatapatha Brahmana ingest script
- `ingest_shatapatha_brahmana.py` written; fetches 14 GRETIL books
  (`sb_01_u.htm`–`sb_14_u.htm`), parses `B.A.Br.[N]` paragraph IDs
  (multi-line text, ID on its own line), converts IAST→Devanagari,
  saves per-book `.md` files to `local_store/sb/`, chunks and uploads
  to Qdrant as layer-4 metadata, re-syncs BM25 pickle (handles both
  RV-style single-md and SB-style multi-md folders).
- Verse IDs emit as `॥ SB B.A.Br.P ॥` (4-level citation) to match
  standard SB referencing (Eggeling/Weber).
- Parser validated: SB 1.4.1 (Videgha Mathava eastward migration —
  fire moves east of Sadanira) confirmed parseable from GRETIL HTML.
- Usage: `python ingest_shatapatha_brahmana.py --dry-run` to validate
  first; then `python ingest_shatapatha_brahmana.py` for all 14 books
  (~15–20 min on Mac).

### Aitareya Brahmana — source gap documented
- Searched GRETIL, TITUS, sanskritdocuments.org, vedicheritage.gov.in.
- GRETIL UTF-8 index has only the Aitareya *Upanishad*, not the Brahmana.
- TITUS has AB but access is restricted.
- No clean Sanskrit/IAST digital text found publicly. AB deferred;
  status marked ❌ in corpus table.

### PB retrieval fix (carried forward from 2026-06-12 session)
- Distinct-term-first scoring (`distinct × 1000 + total`) in
  `devanagari_lexical_hits()` ensures PB 25.10.16 (विनश + सरस्वत
  co-occurrence, score=4005) outranks high-frequency सत्त्र-only chunks.
- All 3562 PB paragraph markers patched to `॥ PB B.C.P ॥` format
  (both `local_store/pb/pb.md` and the BM25 pickle in-place).
- Duplicate keys removed from GAZETTEER (videha, harishchandra,
  shunahshepa were defined twice; Python silently kept the last).
- GAZETTEER extended with SB key names: videgha, sadanira, janaka,
  yajnavalkya, pravahana, jaivali, kosala, kuru, pancala, gandhara,
  magadha, janamejaya, ambarisha.

**To complete SB ingest:** run `python ingest_shatapatha_brahmana.py`
on Mac, then `python build_corpus_lexicon.py` to rebuild token lexicon.
After that, re-initialize the Streamlit app to reload BM25.

## Session log — 2026-06-12 (Streamlit Cloud deploy)

- **Crash fixed:** floating `langgraph` resolved to 1.0.10, incompatible with
  pinned `langchain-core==1.2.3` (`Reviver(allowed_objects=)` TypeError) →
  pinned langgraph 1.0.5 / checkpoint 3.0.1 / prebuilt 1.0.5.
- **Cloud parity:** `.gitignore` excluded `local_store/` + `vector_store/` —
  the deploy had no BM25 pickle/lexicon/corpus → un-ignored corpus markdown
  and the two pickles; committed.
- **SECURITY INCIDENT:** `.streamlit/secrets.toml.bak` (created during the
  secrets sync — committable because the ignore pattern didn't cover `.bak`)
  was pushed to the public repo; Google scanner revoked the Gemini key
  (`403: API key reported as leaked`). Qdrant key exposed in the same file.
  Remediation: both keys rotated, file untracked & deleted, gitignore
  hardened (`secrets.toml*`, `*.toml.bak`). Older history also contains a
  committed secrets.toml ("Add secrets.toml", later deleted) — history purge
  via `git filter-repo` recommended; rotation neutralizes old keys regardless.

## Key scripts

| Script | Purpose |
|---|---|
| `rebuild_mandala_clean.py [all\|N…]` | download .itx → clean Devanagari → chunk → delete+upload to cloud → re-sync BM25 pickle |
| `ingest_pancavimsa_brahmana.py` | fetch GRETIL PB HTML → IAST→Devanagari → chunk → delete+upload (layer 4) → re-sync BM25 pickle |
| `ingest_shatapatha_brahmana.py [N…] [--dry-run]` | fetch GRETIL SB 14 books → IAST→Devanagari → per-book .md → delete+upload (layer 4) → re-sync BM25 pickle |
| `ingest_aitareya_brahmana.py [N…] [--dry-run]` | fetch TITUS 285 pages (ab001–ab285) → TITUS→IAST→Devanagari → single .md → delete+upload (layer 4) → re-sync BM25 pickle |
| `rebuild_bm25_pickle.py` | regenerate keyword-index pickle from `local_store` |
| `build_corpus_lexicon.py` | scan all local_store markdown → build corpus_lexicon.pkl (Devanagari→ASCII map) |
| `test_sudas_retrieval.py` | isolation test: retriever finds Sudas/RV 7.18? |
| `extract_and_upload_r07.py` | (superseded by rebuild_mandala_clean.py) |

## Backlog (rough priority)

1. **Run SB ingest** — `python ingest_shatapatha_brahmana.py` (on Mac, ~15–20 min).
   Key passages: SB 1.4.1 (Videgha Mathava eastward migration), SB 3.1.2
   (Pravahana Jaivali eastern doctrine), SB 13.5 (Ashvamedha geography).
   Run `--dry-run` first to verify SB 1.4.1 Devanagari conversion.
2. **Corpus lexicon rebuild** — `python build_corpus_lexicon.py` after every
   corpus change. Maps every Devanagari token to normalized ASCII for
   sandhi-fused form rescue.
3. **Diachronic Sarasvati verification** — after SB indexed, test
   "How does the Sarasvati appear in earlier vs later Vedic texts?" — should
   cite RV river hymns (layer 1/2) + PB 25.10 vinashana (layer 4) + SB 1.4.1
   Videgha Mathava (layer 4).
4. **Re-run PB ingest** (optional) — `python ingest_pancavimsa_brahmana.py`
   to update Qdrant with the ॥ PB B.C.P ॥ format (BM25 pickle already
   patched; Qdrant still has old ॥ B.C.P ॥ markers in payloads).
5. **AV Shaunaka** — local IAST copy in `library/vedic_texts/AV_sanskrit/`;
   also on sanskritdocuments.org as .itx. Layer 3 metadata, AVŚ
   book.hymn.verse IDs. Next corpus addition after SB.
6. **YV Vajasaneyi Samhita** — GRETIL or sanskritdocuments.org (layer 3).
   Pairs naturally with SB (same eastern/Videha tradition).
7. **Aitareya Brahmana** — ❌ no clean digital source found; deferred.
   Revisit if TITUS access opens or a new GRETIL upload appears.
8. **Diachronic query tool** — ✅ first version shipped (2026-06-12).
   Remaining: true per-layer filtered Qdrant searches once AV/YV (layers 3-4)
   are indexed.
9. **Gazetteer expansion** — auto-generate Devanagari surface forms from
   `proper_noun_variants.json`; current hand-built list ~55 names.
10. **Padapatha / sandhi phase** — VedaWeb (github.com/VedaWebProject) has
    full RV padapatha + Zurich morphological annotation; foundation for the
    grammar-grounded translation goal.

## Lessons learned

- **Two indexes, one truth:** any script that writes to Qdrant must re-sync
  the BM25 pickle. The rebuild script now does this automatically.
- **Never trust PDF text layers for Devanagari** — always prefer the
  digital-native source (.itx/GRETIL).
- **Silent fallbacks hide failures:** BM25 dying quietly cost hours; loud
  logging (🪷 RESCUE ENTRY) is now in place.
- **Embeddings don't know rare names:** dense retrieval needs a lexical
  channel for proper nouns, regardless of script or chunk quality.
