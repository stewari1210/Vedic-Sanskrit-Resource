# 🕉️ Vedic Sanskrit Tutor

**Ask questions about the Vedas in plain English and get answers grounded in the
original Sanskrit — not colonial-era translations.**

> 🔗 **Live app:** `https://https://vedic-sanskrit-resource.streamlit.app`

A retrieval-augmented question-answering system over the Vedic corpus in its
**original Devanāgarī**. You ask in English; the system retrieves the relevant
Sanskrit verses, grounds an answer in them, and replies in English with the
Sanskrit citations it relied on. It is built for probing proper nouns, rivers,
clans, kings, and material culture — and for tracking how they change from the
earliest to the latest Vedic layers.

Why "original Sanskrit, not translations"? Every English Veda you can read
online carries a 19th-century translator's interpretive choices. This project
keeps the Sanskrit as the source of truth and uses the LLM only to read and
explain it — so the answer reflects the verse, not Griffith's gloss of it.

---

## What you can do

- **Ask factual questions** — *"Who is Sudās?"*, *"What metals appear in the
  Taittirīya Saṃhitā?"*, *"Where is the disappearance of the Sarasvatī
  described?"* Answers cite the exact verses (e.g. `॥ RV 7.18.5 ॥`).
- **Compare across Vedic layers** — *"How does the Sarasvatī appear in earlier
  vs. later texts?"* The corpus is tagged by chronological layer, so the answer
  can contrast early Ṛgvedic hymns with later Brāhmaṇa prose.
- **Interpret a specific verse** — pin a citation (e.g. `RV 10.60.2`) and the
  system pulls the exact verse plus its surrounding sūkta and any traditional
  metadata (ṛṣi / devatā / meter / patron) before explaining it.
- **Verse Translation module** — a dedicated tab for word-by-word reading of a
  single verse, with Markdown / Word export of the result.

All queries can be in **English, Devanāgarī, IAST, or mixed script**.

---

## The corpus

Everything is the **digital-native Sanskrit text** (Devanāgarī, converted
mechanically from scholarly IAST/ITRANS editions), chunked verse-by-verse and
tagged with a chronological layer.

| Text | Layer | Source |
|---|---|---|
| Ṛgveda Saṃhitā (Maṇḍalas 1–10) | 1–2 (earliest) | sanskritdocuments.org (.itx) |
| Atharvaveda Śaunaka | 3 | GRETIL |
| Vājasaneyi Saṃhitā (Śukla YV) | 3 | TITUS |
| Taittirīya Saṃhitā (Kṛṣṇa YV) | 3 | TITUS |
| Aitareya Brāhmaṇa | 4 | TITUS |
| Pañcaviṃśa Brāhmaṇa | 4 | GRETIL |
| Śatapatha Brāhmaṇa | 4 (latest) | GRETIL |

Public-domain English translations (Griffith, Eggeling, Caland) are kept only as
an internal cross-checking reference layer — **never** as the answering corpus.

**Not yet included** (secondary/specialized texts): Maitrāyaṇī Saṃhitā, Kāṭhaka
Saṃhitā, Atharvaveda Paippalāda, and the Baudhāyana Śrauta Sūtra.

---

## How it works

```
English question
      │
      ▼
classify_and_plan ─▶ execute_tools ─▶ synthesize ─▶ English answer + Sanskrit citations
   (LangGraph agentic RAG; query is routed to the right tools)
```

- **Hybrid retriever** combines four channels so rare proper nouns are never
  missed: semantic search (Qdrant, cross-lingual 768-dim embeddings) + BM25
  keyword search + a **Devanāgarī lexical-rescue** layer (a gazetteer that maps
  English research themes and names to corpus-verified Sanskrit terms, defeating
  the script and sandhi barriers) + Monier-Williams dictionary expansion.
- **Cross-lingual embeddings** (`paraphrase-multilingual-mpnet-base-v2`) let an
  English query match Devanāgarī text directly.
- **Verse-grounded interpretation:** a pinned citation is resolved from the raw
  text (not semantic search, which can't reliably surface a bare reference) and
  injected with its full sūkta and traditional anukramaṇī metadata.
- **Self-building knowledge graph** (persisted in Qdrant) accumulates
  entity facts across queries, with provenance tiers — `authoritative`
  (curated anukramaṇī ground truth), `itihāsa` (traditional legend, "the
  tradition holds…"), and `inferred` (LLM-extracted) — so verified facts are
  never overwritten by a guess.
- **Synthesis** runs on Google Gemini, grounded in the retrieved verses with
  explicit honesty instructions (state the corpus's limits rather than
  confabulate).

**Stack:** Streamlit · LangGraph / LangChain · Qdrant Cloud · Google Gemini ·
sentence-transformers · indic-transliteration.

---

## Run it yourself

### Prerequisites
- Python 3.11+
- A **Google Gemini** API key
- A **Qdrant Cloud** cluster (free tier is enough) populated with the corpus

### 1. Install
```bash
git clone https://github.com/stewari1210/Vedic-Sanskrit-Tutor.git
cd Vedic-Sanskrit-Tutor
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure secrets
Create `.streamlit/secrets.toml` (or a `.env` for local CLI use). The minimum to
talk to the deployed corpus:

```toml
# LLM
LLM_PROVIDER      = "gemini"
GEMINI_API_KEY    = "your-gemini-key"
GEMINI_MODEL      = "gemini-2.5-flash"

# Vector store
QDRANT_URL        = "https://your-cluster.qdrant.io"
QDRANT_API_KEY    = "your-qdrant-key"
COLLECTION_NAME   = "ancient_history"

# Embeddings — MUST match the model the collection was indexed with,
# or retrieval returns nothing. The shipped corpus uses the multilingual model.
EMBEDDING_PROVIDER = "local-multilingual"
```

> ⚠️ **Never commit secrets.** `.env`, `secrets.toml*`, and `*.toml.bak` are
> gitignored — keep it that way.

### 3. Launch
```bash
streamlit run src/sanskrit_tutor_frontend.py
```

### Building the corpus from scratch (optional)
If you're standing up your own Qdrant collection rather than pointing at an
existing one, the ingest pipeline lives at the repo root and is run on your own
machine (each script fetches from the real source, converts to Devanāgarī,
uploads to Qdrant, and re-syncs the BM25 index):

```bash
python rebuild_mandala_clean.py all       # Ṛgveda
python ingest_atharvaveda_shaunaka.py     # AVŚ
python ingest_taittiriya_samhita.py       # TS   (and the other ingest_*.py)
python build_corpus_lexicon.py            # rebuild the token lexicon
python seed_kg.py && python migrate_kg_to_qdrant.py   # seed + persist the KG
```

---

## Deploy to Streamlit Community Cloud

1. Push to GitHub.
2. On [share.streamlit.io](https://share.streamlit.io), point a new app at
   `src/sanskrit_tutor_frontend.py`.
3. Paste the keys from step 2 above into the app's **Secrets** panel.

Streamlit Community Cloud is free and redeploys on every push. It does **not**
support a fully custom domain (you get `*.streamlit.app`); for a branded domain,
put Cloudflare in front or host on Hugging Face Spaces / Render / Railway.

---

## Honest limitations

- **It only knows the indexed corpus.** Outside the seven texts above it will say
  so rather than invent an answer.
- **Synthesis is an LLM.** Interpretation answers are grounded in the retrieved
  verses, but a model can still err on a fine philological point; citations are
  shown so you can verify.
- **Running cost is the owner's.** A public deployment bills *your* Gemini and
  Qdrant quotas for every visitor. Set a spend cap on your Gemini key before
  sharing widely.

---

## License & attribution

The **software** is released under the [MIT License](LICENSE).

The **corpus texts, dictionaries, and anukramaṇī datasets are not** covered by
that grant — each retains its own license (GRETIL/TITUS scholarly terms, the
Apache-2.0 Digital Rigveda Anukramaṇī, public-domain Monier-Williams /
Bṛhaddevatā / Griffith). See [NOTICE](NOTICE) for full provenance and the terms
that apply to each dataset.

---

<p align="center">
<b>स्वाध्यायान्मा प्रमदः</b> — <i>Never neglect your study.</i><br>
— Taittirīya Upaniṣad
</p>
