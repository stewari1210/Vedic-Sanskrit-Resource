# Cohort Project — Robust Devanāgarī Input for the Vedic Sanskrit RAG

*A 12-week, part-time project brief (≈ 1 session/week). Prepared for the
Kaushalavardhanam cohort.*

## Mission

Make **Devanāgarī a first-class, morphology-aware input** to the Vedic Sanskrit
Resource, and give the knowledge graph a **Devanāgarī brain** — so a Sanskrit
speaker can type in their own script and get robust, verse-cited answers.

## Where the project is today

The system is a live, open-source Retrieval-Augmented QA app over seven Vedic
texts in original Devanāgarī (Ṛgveda, Atharvaveda Śaunaka, both Yajurveda
recensions, and three Brāhmaṇas). English retrieval is strong; it already
accepts Devanāgarī/IAST/mixed queries.

**The gap.** Devanāgarī input currently resolves through a *finite* gazetteer
(`src/utils/devanagari_lexical.py`) plus a corpus token lexicon — exact/substring
matching. There is **no general sandhi/lemmatiser** in the retrieval path, so
inflected or sandhi-joined Devanāgarī (e.g. `सुदासे` → `सुदास`) can slip through.
And the knowledge graph (`knowledge_store/`, `src/utils/vedic_kg.py`) is keyed on
**romanised** entity names only — it has **zero** Devanāgarī keys today.

## Definition of success

1. A **gold test set** of Devanāgarī queries with expected verses/entities, and a
   **baseline retrieval number** to improve against.
2. Inflected/sandhi Devanāgarī input measurably retrieves the right verses
   (a **lift over baseline**).
3. The knowledge graph answers a **Devanāgarī entity query** (god / river / king)
   and displays Devanāgarī labels.

---

## Two tracks

### Track A — Devanāgarī knowledge graph
- Add a Devanāgarī **label + alias layer** over entities: a script-agnostic
  canonical key plus Devanāgarī surface forms.
- Seed a starter Devanāgarī entity set (deities, rivers, kings) with variants.
- Make `get_entity_context()` resolve from Devanāgarī input; surface Devanāgarī
  labels in answers.
- Touches: `src/utils/vedic_kg.py`, `knowledge_store/kg_seed.json`.

### Track B — Robust Devanāgarī retrieval
- **Build the gold test set first** (30–50 `query → expected verse/entity`
  pairs). This is the linchpin: it turns a vague "it works" into a metric.
- Add **sandhi / inflection normalisation** so inflected forms reach their lemma
  and match the corpus. *Integrate* an existing segmenter (INRIA Sanskrit
  Heritage reader or `sanskrit_parser`) rather than build one; build on the
  existing `src/utils/sanskrit_preprocessor.py` / `sanskrit_lexicon.py`.
- Measure the lift on the gold set.
- Touches: `src/utils/retriever.py`, `src/utils/devanagari_lexical.py`,
  `src/utils/sanskrit_preprocessor.py`.

The tracks interlock: the lemma normalisation from Track B also feeds the KG
lookup in Track A, so the cohort shares a foundation, then splits.

---

## 12-week schedule

| Week | Focus | "Done" looks like |
|------|-------|-------------------|
| 1–2  | **Onboard.** Run the app locally; trace one query end-to-end; read `README.md` and the retriever/KG code. | Each student writes a one-paragraph "how a query flows." |
| 3–4  | **Gold set + baseline.** Author 30–50 Devanāgarī `query → expected` pairs; write a small eval script. | A committed `tests/devanagari_gold.jsonl` + a printed baseline accuracy number. |
| 5–7  | **Sandhi / lemma normalisation.** A `devanagari_query` step mapping inflected Devanāgarī → lemma candidates, wired into retrieval. | Measurable retrieval lift over the Week 4 baseline. |
| 8–10 | **Devanāgarī KG layer.** Devanāgarī aliases/keys + seed entities; resolve `get_entity_context` from Devanāgarī. | The KG answers a Devanāgarī entity query. |
| 11   | **Frontend Devanāgarī polish** + display of Devanāgarī labels. | A clean Devanāgarī-input experience in the app. |
| 12   | **Wrap-up.** Docs, demo, results-vs-baseline presentation. | Short write-up + before/after numbers. |

**Realistic expectation (part-time):** the gold set and normalisation fully
land, and the KG layer lands partially. Prioritise in that order.

## Working agreement (what makes a part-time cohort succeed)

- **Tiny PRs**, one task each; **a test required** per change.
- A **30-minute weekly sync**; a shared task board; a written "definition of
  done" per task.
- Ask early, commit often, keep the app runnable on `main`.

## Skills you'll take away

Python · embeddings & retrieval (RAG) · knowledge graphs · evaluation design ·
Sanskrit computational linguistics (sandhi, morphology, transliteration) ·
working in a real open-source codebase.

## Getting started

1. Clone the repo and run `streamlit run src/sanskrit_tutor_frontend.py`.
2. Read `README.md` (architecture), then skim `src/utils/retriever.py`,
   `src/utils/devanagari_lexical.py`, and `src/utils/vedic_kg.py`.
3. Investigate the existing `src/utils/sanskrit_preprocessor.py` and
   `sanskrit_lexicon.py` — build on them, don't start cold.
4. Pick a Week-1 task from the board and open your first PR.

---

*Reframe to keep in mind: **make Devanāgarī input measurably robust, and give the
knowledge graph a Devanāgarī brain.** The evaluation/gold-set work is the unsung
hero — a metric you can move is the most transferable skill here.*
