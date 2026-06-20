# Vedic Sanskrit RAG — Project Status

> Living document. Last updated: 2026-06-19 (session with Claude).

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
| RV Mandalas 1–10 | ✅ indexed (clean) | all from .itx, Devanagari, verse-per-line, layer-tagged; citations patched to `॥ RV N.NNN.NN ॥` (10 552 verses); "Who is Sudas?" verified end-to-end |
| Pancavimsa Brahmana | ✅ indexed | `ingest_pancavimsa_brahmana.py`; GRETIL IAST→Devanagari, ॥ PB B.C.P ॥ markers, layer 4; BM25 pickle patched; PB 25.10.16 verified as #1 for vinashana query |
| Shatapatha Brahmana | ✅ script ready | `ingest_shatapatha_brahmana.py`; 14 GRETIL books, parser validated (SB 1.4.1 Videgha Mathava); run `python ingest_shatapatha_brahmana.py` on Mac |
| Aitareya Brahmana | ✅ indexed | `ingest_aitareya_brahmana.py`; TITUS Frankfurt, 285 pages (ab001–ab285), TITUS→IAST→Devanagari; `local_store/ab/ab.md` present (2026-06-13); AB 8 (king-consecration register) in corpus |
| Vajasaneyi Saṃhitā (VS) | ✅ script ready | `ingest_vajasaneyi_samhita.py`; TITUS IAST→Devanagari, ॥ VS A.V ॥ markers; run script to upload |
| Taittirīya Saṃhitā (TS) | ✅ indexed (clean) | `ingest_taittiriya_samhita.py`; TITUS ts001–ts100, event-driven parser, 4-level hierarchy (Kāṇḍa.Prapāṭhaka.Anuvāka.Verse), ॥ TS B.C.P.V ॥ markers, cross-file Book state, content-hash dedup (catches ts045/ts046 TITUS duplicates); **2197 verses, 7 Kāṇḍas, 44 Prapāṭhakas** — uploaded 2026-06-19 |
| Atharvaveda Śaunaka (AVŚ) | ✅ indexed | `ingest_atharvaveda_shaunaka.py`; GRETIL `avs___u.htm`, ~6000 verses, 20 kāṇḍas, IAST→Devanagari, ॥ AVŚ B.H.V ॥ markers, **layer 3** (`av_samhita`); fills diachronic gap between RV samhitas (1-2) and Brahmana prose (4). Key passages: AVŚ 5.22 (Gandhāri/Mūjavant/Aṅga/Magadha/Balhika peoples), AVŚ 20.127 (Parikṣit, Kuru king) — uploaded 2026-06-19 |

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

## Session log — 2026-06-14 (VS + TS ingest, RV citation fix, frontend)

### VS + TS ingest scripts completed
- `ingest_vajasaneyi_samhita.py` — TITUS Frankfurt, VS chapters, IAST→Devanagari.
- `ingest_taittiriya_samhita.py` — TITUS ts001–ts100, 4-level event-driven parser
  (Book/Chapter/Paragraph/Verse/Sentence). Fixes applied this session:
  - Structural label leakage (Book:/Chapter:/… appearing inside verse text as
    Devanagari garbage) — fixed with `end_pos` parameter on `flush_verse()` and
    `_STRUCT_LABEL_RE` stripping in `clean_titus_text()`.
  - `None` Book values across file boundaries — fixed with `default_book` /
    `default_chapter` cross-file state in `main()`.
  - TITUS duplicate files ts045/ts046 (copies of ts043/ts044) — fixed with
    `seen_hashes: set[int]`.
  - Dry-run confirmed: 2197 verses, Kāṇḍas 1–7, 44 Prapāṭhakas, clean citations.

### RV citation prefix fix
- All r01–r10.md files patched: `॥ N.NNN.NN ॥` → `॥ RV N.NNN.NN ॥` (10 552 verses).
  `rebuild_mandala_clean.py all` run 2026-06-19 — Qdrant payloads now reflect `RV` prefix. ✅

### Frontend changes (src/sanskrit_tutor_frontend.py)
- Per-answer export: `.md` (and `.docx` via pandoc if installed) download button
  rendered after each assistant response, replacing the single "last answer" button.
- Corpus table updated: added VS and TS rows.
- "Why this project exists": added VS/TS to corpus list; added translator-bias
  neutralisation paragraph.
- "Get started" section simplified: Gemini auto-loads, sidebar only for LLM switching.
- Example question "Translate RV 1.1.1 word by word" removed; replaced with
  "What metals are mentioned in the Taittiriya Samhita?"

### KG migration note
The self-building KG (`vedic_kg.py`) currently persists to a local JSON file
(`knowledge_store/vedic_relations.json`). On Streamlit Cloud this resets on every
redeploy. Moving to Qdrant Cloud is **feasible** — see Architecture note below.

## Session log — 2026-06-18 (AV Shaunaka ingest script)

- Decision: **include AV Śaunaka.** Rationale — it is the richest Vedic source
  for material culture (medicine, herbs, agriculture, house-building, commerce)
  and it populates **layer 3**, previously reserved-but-empty, removing the
  diachronic gap between RV samhitas (1-2) and Brahmana prose (4). Concrete
  geography/king hooks: AVŚ 5.22 (takman banished to Gandhāri/Mūjavant/Aṅga/
  Magadha/Balhika — a NW↔east peoples spread) and AVŚ 20.127 (Parikṣit, king of
  the Kurus). Not a river/genealogy source — those are better covered by RV/SB.
- **Source correction:** PROJECT_STATUS previously said "sanskritdocuments.org
  has AV .itx". Verified false — /doc_veda hosts only AV *sūkta excerpts*
  (gosUkta, oShadhIsUkta…), no complete Śaunaka samhita .itx like r01–r10.
  Switched to GRETIL `avs___u.htm` (clean UTF-8 IAST whole-text, Orlandi 1991 /
  Roth-Whitney, Books 11-20 rev. Griffiths) — same provenance + pipeline as
  SB/VS/TS. Local `AV_sanskrit/` copy rejected: `atharvaveda_complete.txt` is
  encoding-corrupt, and the per-hymn `.txt` files merge all verses to one line
  with no verse IDs.
- `ingest_atharvaveda_shaunaka.py` written (RV-style single-folder `avs/avs.md`):
  fetch GRETIL → parse `(AVŚ_B,H.Va)` half-lines, group by verse key (joins
  a/b/c/e, strips `||n||`/`|n||`/`||4 ||`/pada bars) → IAST→Devanagari →
  ॥ AVŚ B.H.V ॥ → chunk → delete+upload layer 3 → re-sync BM25 pickle.
  Has `--dry-run` and `--self-test` (offline parser unit test — passes:
  half-line join, marker strip, AVŚ 5.22 + 20.127 anchors, takman/peoples
  names present in Devanagari output).
- GAZETTEER extended (`devanagari_lexical.py`): takman, gandhari, mujavant,
  anga, magadhi, balhika/bahlika, mahavrisha, kushtha, atharvan, jangida,
  sadanva.

**To complete AV ingest:** run `python ingest_atharvaveda_shaunaka.py` on Mac
(`--dry-run` first), then `python build_corpus_lexicon.py`, then restart Streamlit.

## Session log — 2026-06-19 (TS + AVŚ ingest complete, RV Qdrant sync)

### All three pending corpus ingests confirmed complete
- **TS re-ingested (clean):** `ingest_taittiriya_samhita.py` re-run with content-hash dedup fix (not HTML-hash). Result: 2197 verses, 7 Kāṇḍas, 44 Prapāṭhakas — ts045/ts046 duplicates correctly suppressed. TS upgraded to ✅ indexed (clean).
- **RV Qdrant payloads synced:** `rebuild_mandala_clean.py all` run — all 10 552 RV chunks now have `॥ RV N.NNN.NN ॥` citation format in Qdrant cloud payloads. Backlog item 4 closed.
- **AVŚ uploaded:** `ingest_atharvaveda_shaunaka.py` run (GRETIL `avs___u.htm`, ~6000 verses, layer 3 `av_samhita`). Fills the diachronic gap between RV samhitas (layers 1-2) and Brahmana prose (layer 4). Key passages in corpus: AVŚ 5.22 (takman banished to Gandhāri/Mūjavant/Aṅga/Magadha/Balhika), AVŚ 20.127 (Parikṣit, Kuru king). AVŚ upgraded to ✅ indexed.

### Retrieval fix (corpus-aware filtering)
- `_detect_source_text_filter()` in `retriever.py` extended to cover all 6 corpus texts (RV, TS, VS, SB, AB, PB). Strict single-corpus mode enabled for unambiguous queries. Root-cause of "RV cited for TS metals question": retriever had no TS/VS/SB/AB/PB entries so all queries were unfiltered.

### AB status corrected
- `local_store/ab/ab.md` exists (2026-06-13) — AB was already indexed. Corpus table corrected from "script ready" to ✅ indexed.

### Still pending
- VS ingest: `ingest_vajasaneyi_samhita.py` script ready, not yet run.
- SB ingest: `ingest_shatapatha_brahmana.py` script ready, not yet run (~15–20 min on Mac).
- Corpus lexicon rebuild: `python build_corpus_lexicon.py` needed after TS + AVŚ addition.

## Session log — 2026-06-19 (KG → Qdrant Cloud migration)

### `vedic_kg.py` storage moved to Qdrant Cloud (backlog #12 implemented)
- **Source of truth is now the Qdrant Cloud collection `vedic_kg`**; the local
  `knowledge_store/vedic_relations.json` is demoted to a best-effort mirror.
  Rationale: the JSON resets on every Streamlit Cloud redeploy (ephemeral FS),
  wiping the self-built graph. A cloud collection persists across redeploys —
  including when the app is `<iframe>`-embedded in WordPress (the Streamlit app
  still runs on Streamlit Cloud; WordPress only displays it).
- **Schema:** one payload-only point per triple — `{subject, subject_key,
  relation, object, object_key, citations[], confidence, added_at}`. 1-dim dummy
  vector (`[0.0]`, Distance.DOT): we never vector-search the KG, we look up by
  exact subject key. Point id = `uuid5(namespace, "s_key|relation|o_key")` so
  re-upserts dedup and migration is idempotent.
- **Self-building loop unchanged:** `extract_and_store_facts()` → `add_fact()`
  still fires post-synthesis after every query (`agentic_rag.py:720`). `add_fact`
  now *also* upserts the new triple to Qdrant. So the graph keeps growing per
  query exactly as before — it just persists now.
- **In-memory cache preserved:** `_load()` pulls all points into the same
  `_KG_CACHE` dict on startup; query-time `get_entity_context()` reads stay in
  memory (zero per-query Qdrant latency). Public API (`add_fact`,
  `get_entity_context`, `kg_stats`, `to_networkx`) byte-for-byte unchanged —
  no caller touched.
- **Resilience:** Qdrant load failure / not-configured falls back to JSON;
  collection-empty falls back to JSON seed; JSON mirror write wrapped in
  try/except so a read-only/ephemeral FS never crashes the app. Qdrant stays
  authoritative throughout.
- **Backfill:** `migrate_kg_to_qdrant.py` (idempotent, `--dry-run`) flattens the
  329 facts / 131 entities into points and upserts them. Verified offline: the
  Qdrant→cache rebuild reproduces the JSON graph exactly (329 facts, 0 relation
  mismatches, 7 dynasty member-lists preserved). Note: `kg_stats()` entity count
  rises (object-only nodes — e.g. dynasties — now materialise as nodes;
  cosmetic, no behavioural change).

**To complete migration:** on Mac (Qdrant reachable), run
`python migrate_kg_to_qdrant.py --dry-run` then `python migrate_kg_to_qdrant.py`;
confirm the printed point count. App then loads the KG from Qdrant on next start.

## Session log — 2026-06-20 (verse-grounded interpretation + anukramaṇī-seeded KG)

### Verse interpretation grounding (retriever untouched)
- **Exact-verse lookup** (`_lookup_verse_text` in `sanskrit_tutor_frontend.py`): a
  cited verse (`RV 10.60.2`, `Mandala 10 Sukta 60`, `10.60.1`…) is resolved
  directly from `local_store/rNN.md` — not via semantic retrieval, which could
  not reliably surface a bare citation. Markers are `॥ M.SSS.VV ॥` (no `RV`
  prefix on the danda; `RV` is only in the `## RV M.SSS` header).
- **Whole-sūkta anchoring:** the lookup returns the focus verse PLUS the full
  sūkta, because name-vs-epithet calls need the surrounding verses (relative
  pronouns `yáḥ/yásya`, named figures). E.g. RV 10.60.2 only resolves once v3
  (`yó janān…`), v4 (Ikṣvāku), v5 (`rathaproṣṭheṣu` patronymic) and v6 (`rājan`)
  are in view.
- **Verse Translation tab** (mode=`translation`) feeds the focus verse + sūkta
  context inline; **Home chat** uses a separate `pinned_verse` side-channel
  (`run_agentic_rag(pinned_verse=…)` → `AgentState.pinned_verse` →
  `synthesize_answer_node`). The pin is gated on a citation being present, kept
  across follow-ups via `st.session_state.pinned_verse`, and dropped on topic
  change. **Retrieval/BM25 are never touched** — normal semantic queries are
  byte-for-byte unchanged.
- Chatbox leak fixed: `ask_tutor` now writes `chat_history` only for
  `mode="conversation"`, so module tabs don't post into the Home chat.

### KG provenance tiers (self-learning preserved)
- `add_fact` gains a `provenance` field: `authoritative` (curated/anukramaṇī
  ground truth) vs `inferred` (LLM-extracted, the self-building path).
  Authoritative facts are **protected** — an inferred add can never overwrite or
  downgrade one, and an authoritative add *corrects* a conflicting inferred
  singleton. Stored on the fact + Qdrant payload + JSON; surfaced as
  `✓traditional` in `get_entity_context`. The graph keeps self-building; it just
  can't clobber verified facts. Pinned-verse (interpretive) answers are excluded
  from KG extraction so tentative readings don't pollute the graph.

### Curated anukramaṇī seed (starter)
- `knowledge_store/kg_seed.json` — **3 hymns (10.060, 7.018, 3.062) + 16 entity
  facts**, indigenous sources only (anukramaṇī + Bṛhaddevatā/itihāsa), no
  translations. `seed_kg.py` (idempotent, `--dry-run`) upserts the facts as
  `authoritative`. `src/utils/anukramani.py` loads the seed and, when a hymn is
  pinned, injects an ANUKRAMAṆĪ block (ṛṣi/devatā/patron/theme) + the entities'
  KG facts into synthesis.
- **Outcome:** flash's RV 10.60.2 reading went confabulation → correct — it now
  names Asamāti as the king (anukramaṇī patron = Asamāti Rāthaproṣṭha), cites
  v5 `rathaproṣṭheṣu` (the patronymic it had silently dropped), and only diverges
  on *Bhajeratha* (a now-defensible, genuinely contested call, not a hallucination).

### Decision — anukramaṇī coverage roadmap
The anukramaṇī ṛṣi/devatā/meter schema applies to **metrical saṃhitās**, not
prose Brāhmaṇas. Agreed scope:
- **RV** — full anukramaṇī ingest (Śaunaka's Ārṣa/Daivata/Chandas + Kātyāyana
  Sarvānukramaṇī; GRETIL/VedaWeb), all 1028 sūktas.
- **AVŚ** — full (its Bṛhatsarvānukramaṇī).
- **YV (VS, TS)** — **partial**: section-level ṛṣi/devatā only (prose-heavy, unit
  is a ritual section, not a sūkta).
- **Brāhmaṇas (AB, PB, SB)** — anukramaṇī **N/A** (prose, no ṛṣi/devatā/meter);
  instead curate **legend/king/ritual-topic** metadata + śākhā/author per section.
- **Bṛhaddevatā legend layer** — curated/extracted (Macdonell ed., GRETIL/
  archive.org), tagged **`traditional/itihāsa`** provenance and phrased as "the
  tradition holds X" (distinct from "the mantra says X"). Supplies the
  patron/king/legend anchors (the layer that fixed the Asamāti case) and the
  Brāhmaṇa legend metadata. Only a few dozen hymns carry major ākhyānas, so
  tractable.
- All layers slot into the same `kg_seed.json["hymns"]` structure → the
  injection path needs no change. Ingest scripts fetch from real sources (run on
  Mac), never hand-typed.
- **Cost-aware note:** synthesis stays on gemini-2.5-flash; the open lever for
  residual reasoning errors is a *gated* evaluator/critic pass (one extra call,
  only on interpretation queries, ideally a cheap OpenRouter reasoning model with
  a Vedic rubric) — not upgrading the always-on synthesis model.

## Backlog (rough priority)

1. **Run SB ingest** — `python ingest_shatapatha_brahmana.py` (on Mac, ~15–20 min).
   Key passages: SB 1.4.1 (Videgha Mathava eastward migration), SB 3.1.2
   (Pravahana Jaivali eastern doctrine), SB 13.5 (Ashvamedha geography).
   Run `--dry-run` first. Note: SB Book 12 returns 404 from GRETIL — Vāṃśa
   lineage lists (SB 12.9.3) not in corpus until alternate source found.
2. **Run VS ingest** — `python ingest_vajasaneyi_samhita.py`. Eastern YV
   tradition; Yajnavalkya; pairs with SB for east/west Yajurvedic contrast.
3. ~~**Run TS ingest**~~ — ✅ done 2026-06-19 (2197 verses, clean).
4. ~~**Re-ingest RV chunks**~~ — ✅ done 2026-06-19 (`rebuild_mandala_clean.py all`).
5. **Corpus lexicon rebuild** — `python build_corpus_lexicon.py` after TS + AVŚ
   addition. Maps every Devanagari token to normalized ASCII for sandhi-fused
   form rescue.
6. **Diachronic Sarasvati verification** — after SB indexed, test
   "How does the Sarasvati appear in earlier vs later Vedic texts?" — should
   cite RV river hymns (layer 1/2) + PB 25.10 vinashana (layer 4) + SB 1.4.1
   Videgha Mathava (layer 4).
7. **Re-run PB ingest** (optional) — `python ingest_pancavimsa_brahmana.py`
   to update Qdrant with the ॥ PB B.C.P ॥ format (BM25 pickle already
   patched; Qdrant still has old ॥ B.C.P ॥ markers in payloads).
8. ~~**Run AV Shaunaka ingest**~~ — ✅ done 2026-06-19 (~6000 verses, layer 3).
9. **Aitareya Brahmana** — ✅ indexed (`local_store/ab/ab.md`, 2026-06-13).
   AB 8 king-consecration register in corpus. Source: TITUS Frankfurt.
10. **Diachronic query tool** — ✅ first version shipped (2026-06-12).
    Remaining: true per-layer filtered Qdrant searches (layers 3-4 now populated
    with AVŚ).
11. **Gazetteer expansion** — extend GAZETTEER with VS/TS proper nouns
    (Yajnavalkya, Taittiriya-specific ritual terms, Kuru-region geography).
    AVŚ names already added (takman, gandhari, mujavant, anga, magadhi, etc.).
12. ~~**KG → Qdrant Cloud**~~ — ✅ implemented 2026-06-19 (`vedic_kg.py` reads/writes
    Qdrant collection `vedic_kg`, JSON demoted to mirror; `migrate_kg_to_qdrant.py`
    backfill ready). Remaining: run the backfill on Mac to populate the cloud
    collection from the existing 329 facts.
13. **Padapatha / sandhi phase** — VedaWeb (github.com/VedaWebProject) has
    full RV padapatha + Zurich morphological annotation; foundation for the
    grammar-grounded translation goal.
14. **AV Paippalāda** (future) — more historical-geographic material than Śaunaka;
    GRETIL (Lubotsky). Defer until VS + SB are indexed and diachronic queries
    are verified.
15. **RV anukramaṇī bulk ingest** — fetch/parse Śaunaka's & Kātyāyana's
    anukramaṇīs (GRETIL/VedaWeb) → ṛṣi/devatā/meter for all 1028 sūktas into
    `kg_seed.json["hymns"]`. The cleanest, highest-coverage grounding floor.
    (Starter seed for 10.060/7.018/3.062 already in place, 2026-06-20.)
16. **Bṛhaddevatā legend layer** — curated/extracted (Macdonell HOS ed.,
    GRETIL/archive.org), `traditional/itihāsa` provenance; the patron/king/legend
    anchors (Subandhu/Asamāti, Śunaḥśepa, Purūravas–Urvaśī, …) + Brāhmaṇa
    legends. Only a few dozen hymns carry major ākhyānas → tractable.
17. **AVŚ anukramaṇī** — Bṛhatsarvānukramaṇī → ṛṣi/devatā/meter per Śaunaka hymn.
18. **YV (VS/TS) partial anukramaṇī** — section-level ṛṣi/devatā only (prose unit).
19. **Brāhmaṇa legend/topic curation** (AB/PB/SB) — no ṛṣi/devatā/meter; curate
    legend/king/ritual-topic + śākhā/author per section instead.
20. **Gated evaluator/critic** (cost-aware) — one extra LLM call on interpretation
    (pinned-verse) queries only, with a Vedic-philology rubric; ideally a cheap
    OpenRouter reasoning model. Catches residual flash errors (e.g. dropping a
    word adjacent to the one being analysed) without upgrading always-on synthesis.

## KG → Qdrant Cloud migration (architecture note)

**Current:** `knowledge_store/vedic_relations.json` — local file, resets on Streamlit
Cloud redeploy, single-process only (JSON file locking not safe under concurrency).

**Recommended approach** (feasible, moderate effort):

1. Add a `vedic_kg` Qdrant collection (free tier; triples are tiny — each ~200 bytes).
2. No embedding vector needed for triples: store as payload-only points with UUID IDs.
   Schema per point: `{subject, relation, object, citations[], confidence, added_at}`.
3. On app startup: fetch all points into the existing `_KG_CACHE` dict — same in-memory
   cache as today, so query-time latency is unchanged.
4. On write (`add_fact`): upsert one Qdrant point + update memory cache.
5. For entity lookup (`get_entity_context`): use the memory cache (as now); no Qdrant
   filter call needed per query.
6. For multi-hop traversal: the `to_networkx()` export continues to work from cache.

**Why not full vector KG:** Qdrant's vector search is unnecessary for structured
triple lookup (we query by exact subject key, not semantic similarity). Adding embeddings
per triple would inflate the collection and add latency for no benefit yet.

**Effort estimate:** ~150 lines in `vedic_kg.py`. The public API (`add_fact`,
`get_entity_context`, `kg_stats`, `to_networkx`) stays identical — callers unchanged.

## Lessons learned

- **Two indexes, one truth:** any script that writes to Qdrant must re-sync
  the BM25 pickle. The rebuild script now does this automatically.
- **Never trust PDF text layers for Devanagari** — always prefer the
  digital-native source (.itx/GRETIL).
- **Silent fallbacks hide failures:** BM25 dying quietly cost hours; loud
  logging (🪷 RESCUE ENTRY) is now in place.
- **Embeddings don't know rare names:** dense retrieval needs a lexical
  channel for proper nouns, regardless of script or chunk quality.
