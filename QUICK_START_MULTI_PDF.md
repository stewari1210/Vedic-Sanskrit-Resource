# Quick Start: Adding Yajurveda to RAG System

## Prerequisites

✅ You have `rigveda-griffith.pdf` (already processed as `griffith.pdf`)
✅ You have `yajurveda-griffith.pdf` (North Yajurveda translation by Ralph Griffith)

---

## Option A: Process Both PDFs from Scratch (Clean Start)

```bash
# 1. Clean existing data
rm -rf local_store/ancient_history/
rm -rf vector_store/ancient_history/

# 2. Process both PDFs together
python src/cli_run.py \
  --pdfs rigveda-griffith.pdf yajurveda-griffith.pdf \
  --no-cleanup-prompt
```

**Time estimate:** 10-15 minutes (both PDFs)
**Result:** Unified index with both texts

---

## Option B: Add Yajurveda to Existing Rigveda Index

```bash
# 1. Keep existing Rigveda data, skip cleanup prompt
python src/cli_run.py \
  --pdf yajurveda-griffith.pdf \
  --no-cleanup-prompt \
  --force
```

**Time estimate:** 5-8 minutes (Yajurveda only)
**Result:** Existing Rigveda + New Yajurveda in same index

---

## Verify Multi-Document Setup

```bash
python test_multi_pdf.py
```

**Expected output:**
```
✅ Loaded 2 document(s)

Document: rigveda-griffith
  - Title: The Hymns of the Rigveda...
  - Pages: 506

Document: yajurveda-griffith
  - Title: The Yajurveda...
  - Pages: XXX

✅ SUCCESS: Multiple PDFs are properly distinguished!
```

---

## Example Queries (After Setup)

### Query 1: Specific to One Text
```
You: Where did the Bharatas dwell according to Rigveda?
AI: [Answer citing Rigveda hymns...]
```

### Query 2: Compare Across Texts
```
You: How do descriptions of horse sacrifice differ between Rigveda and Yajurveda?
AI: [Comparative answer citing both texts...]
```

### Query 3: Find All Mentions
```
You: What do both texts say about the Sarasvati river?
AI: [Answer combining information from both sources...]
```

### Query 4: Period Comparison
```
You: What changes in dwelling patterns between Early Vedic (Rigveda) and Later Vedic (Yajurveda)?
AI: [Analysis of differences with citations...]
```

---

## Benefits of Multi-Document Setup

✅ **Comprehensive Coverage**: Search both texts simultaneously
✅ **Source Attribution**: Know which text each answer comes from
✅ **Period Comparison**: Track evolution from Rigveda → Yajurveda
✅ **Shared Entities**: Find tribes/places mentioned in both
✅ **Unified Interface**: One query searches all indexed texts

---

## Troubleshooting

### Problem: Only one document showing after processing both

**Solution 1:** Check if both PDFs were actually processed
```bash
ls -la local_store/ancient_history/
# Should show 2 folders: rigveda-griffith/ and yajurveda-griffith/
```

**Solution 2:** Force clean reindex
```bash
rm -rf vector_store/ancient_history/
python src/cli_run.py --pdfs rigveda-griffith.pdf yajurveda-griffith.pdf --force
```

### Problem: Out of memory during processing

**Solution:** Process one at a time
```bash
# First, process Rigveda
python src/cli_run.py --pdf rigveda-griffith.pdf --no-cleanup-prompt

# Then, add Yajurveda (without deleting Rigveda)
python src/cli_run.py --pdf yajurveda-griffith.pdf --no-cleanup-prompt --force
```

---

## Files to Check

After successful multi-PDF processing:

```
local_store/ancient_history/
├── rigveda-griffith/
│   ├── rigveda-griffith.md
│   ├── rigveda-griffith_metadata.json
│   └── images/
└── yajurveda-griffith/
    ├── yajurveda-griffith.md
    ├── yajurveda-griffith_metadata.json
    └── images/

vector_store/ancient_history/
├── meta.json
├── collection/
└── docs_chunks.pkl  (contains chunks from BOTH documents)
```

---

## Next Steps

1. **Process both PDFs** using Option A or B above
2. **Verify** with `python test_multi_pdf.py`
3. **Start querying** to test cross-document retrieval
4. **Commit changes** when satisfied:
   ```bash
   git add -A
   git commit -m "feat: add multi-PDF support for Rigveda + Yajurveda indexing"
   git push origin local-processing
   ```

---

**Ready to go!** 🚀 Process both PDFs and start querying across Early and Later Vedic periods.
