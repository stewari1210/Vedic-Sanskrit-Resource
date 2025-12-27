# Multi-Document Support for RAG System (PDFs and TXT files)

**Date**: December 26, 2024
**Feature**: Enhanced CLI to process multiple documents (PDFs and TXT files) simultaneously

---

## Overview

The RAG system now supports processing **multiple documents in different formats** in a single session. Supported formats:
- **PDF files** (with text or requiring OCR)
- **TXT files** (plain text, already converted)

All documents are indexed into a unified vector store while maintaining distinct source metadata for each file.### Key Benefits

✅ **Unified Search**: Query across all documents simultaneously
✅ **Source Attribution**: Each answer includes which document it came from
✅ **Comparative Analysis**: Ask questions spanning multiple texts
✅ **Single Index**: One vector store for all documents (efficient)
✅ **Metadata Preservation**: Each chunk knows its source document

---

## Usage Examples

### 1. Process Multiple PDFs (Method 1: Multiple --pdf flags)

```bash
python src/cli_run.py --pdf rigveda-griffith.pdf --pdf yajurveda-griffith.pdf
```

### 2. Process Multiple PDFs (Method 2: --pdfs with space-separated list)

```bash
python src/cli_run.py --pdfs rigveda-griffith.pdf yajurveda-griffith.pdf
```

### 3. Process Multiple PDFs with Force Reindex

```bash
python src/cli_run.py --pdfs rigveda-griffith.pdf yajurveda-griffith.pdf --force
```

### 4. Skip Cleanup Prompt

```bash
python src/cli_run.py --pdfs rigveda-griffith.pdf yajurveda-griffith.pdf --no-cleanup-prompt
```

### 5. Quiet Mode (Suppress INFO logs)

```bash
python src/cli_run.py --pdfs rigveda-griffith.pdf yajurveda-griffith.pdf -q
```

### 6. Set Default PDFs (Edit Code)

Edit `src/cli_run.py` and modify the `HARDCODED_PDFS` list:

```python
HARDCODED_PDFS = [
    os.path.join(project_root, "rigveda-griffith.pdf"),
    os.path.join(project_root, "yajurveda-griffith.pdf"),
]
```

Then simply run:
```bash
python src/cli_run.py
```

---

## How It Works

### 1. Document Processing

Each PDF is processed independently:
- Converted to Markdown (with images extracted)
- Metadata extracted (title, author, pages, etc.)
- Saved to `local_store/ancient_history/<filename>/`

**Example Structure:**
```
local_store/ancient_history/
├── rigveda/
│   ├── rigveda.md
│   ├── rigveda_metadata.json
│   └── images/
└── yajurveda/
    ├── yajurveda.md
    ├── yajurveda_metadata.json
    └── images/
```

### 2. Unified Indexing

All documents are chunked and indexed into a **single Qdrant collection**:
- Collection name: `ancient_history` (from `config.py`)
- Each chunk preserves its source document metadata
- Hybrid retrieval (BM25 + semantic) searches all documents

### 3. Source Attribution

Retrieved chunks include metadata:
```json
{
  "filename": "rigveda",
  "title": "The Hymns of the Rigveda",
  "pages": 506,
  "document_number": 1
}
```

This metadata is available to the answer generation system for proper citations.

---

## Example Queries (Rigveda + Yajurveda)

Once both PDFs are indexed, you can ask:

### 1. Cross-Document Questions

```
Q: "How do dwelling descriptions differ between Rigveda and Yajurveda?"
```

The system will retrieve relevant passages from both texts and compare them.

### 2. Entity Tracking Across Texts

```
Q: "Which tribes are mentioned in both Rigveda and Yajurveda?"
```

The system searches both documents and identifies common entities.

### 3. Period Comparison

```
Q: "What changes in ritual practices between the Rigveda period and Yajurveda period?"
```

The system can draw on both texts to show evolution over time.

### 4. Comprehensive Coverage

```
Q: "Tell me about the Bharatas in all available texts"
```

The system searches all indexed documents for mentions of Bharatas.

---

## Technical Details

### Modified Files

**File 1: `src/cli_run.py`**
- Changed `--pdf` to accept multiple values (using `action='append'`)
- Added `--pdfs` flag for space-separated list
- Modified `prepare_and_process()` to accept list of paths
- Updated docstrings and help text

**Key Changes:**
```python
# Before
HARDCODED_PDF = os.path.join(project_root, "sample.pdf")

# After
HARDCODED_PDFS = [os.path.join(project_root, "sample.pdf")]

# Before
def prepare_and_process(pdf_path: str):
    # Process single PDF

# After
def prepare_and_process(pdf_paths: list):
    # Process multiple PDFs
```

### Metadata Structure

Each document's metadata (`<filename>_metadata.json`):

```json
{
  "format": "PDF 1.3",
  "title": "The Hymns of the Rigveda",
  "author": "Ralph Griffith",
  "pages": 506,
  "filename": "rigveda",
  "toc": [],
  ...
}
```

This metadata propagates to all chunks during text splitting.

### Retrieval System

The `create_retriever()` function in `src/utils/retriever.py`:
1. Performs BM25 keyword search across all documents
2. Performs semantic similarity search across all documents
3. Reranks results (across all sources)
4. Returns top-k chunks with metadata intact

---

## Verification

### Test Multi-PDF Metadata Preservation

Run the test script:

```bash
python test_multi_pdf.py
```

**Expected Output:**
```
======================================================================
Testing Multi-PDF Metadata Preservation
======================================================================

✅ Loaded 2 document(s)

Document: rigveda
  - Title: The Hymns of the Rigveda. Translated by Ralph Griffith...
  - Pages: 506
  - Content length: 1234567 chars

Document: yajurveda
  - Title: The Yajurveda. Translated by Ralph Griffith...
  - Pages: 320
  - Content length: 987654 chars

======================================================================
Summary: 2 unique document(s) found
Document names: rigveda, yajurveda
======================================================================

✅ SUCCESS: Multiple PDFs are properly distinguished!
Each document maintains its own metadata (filename, title, etc.)
Chunks from each document will be tagged with their source.
```

---

## Workflow for Adding Yajurveda

### Step 1: Prepare PDFs

```bash
# Place both PDFs in project root
cp /path/to/rigveda-griffith.pdf ~/github/RAG-CHATBOT-CLI-Version/
cp /path/to/yajurveda-griffith.pdf ~/github/RAG-CHATBOT-CLI-Version/
```

### Step 2: Clean Previous Index (Optional)

```bash
# If you want fresh indexing of both PDFs
rm -rf local_store/ancient_history/
rm -rf vector_store/ancient_history/
```

Or let the CLI prompt you for cleanup.

### Step 3: Process Both PDFs

```bash
cd ~/github/RAG-CHATBOT-CLI-Version
python src/cli_run.py --pdfs rigveda-griffith.pdf yajurveda-griffith.pdf
```

**Output:**
```
Will process 2 PDF(s): ['rigveda-griffith.pdf', 'yajurveda-griffith.pdf']
Copied PDF to local_store/ancient_history/rigveda-griffith.pdf
Copied PDF to local_store/ancient_history/yajurveda-griffith.pdf
Processing 2 PDF(s)...
Successfully processed 2 PDF(s)
[Indexing progress...]
Successfully created vector store at vector_store/ancient_history
Loaded existing collection 'ancient_history' with 5432 chunks
```

### Step 4: Verify Multi-Document Setup

```bash
python test_multi_pdf.py
```

Should show both documents loaded with distinct metadata.

### Step 5: Query Both Documents

```bash
# CLI already running in REPL mode
You: Where did the Bharatas dwell according to the Rigveda?
[Answer with Rigveda citations]

You: What does Yajurveda say about the Bharatas?
[Answer with Yajurveda citations]

You: Compare references to Bharatas in both texts
[Comparative answer citing both sources]
```

---

## Limitations & Considerations

### 1. Collection Name Scope

All PDFs in one session share the same `COLLECTION_NAME` (default: `ancient_history`).

**To use different collections:**
- Edit `.env`: `COLLECTION_NAME=rigveda_collection`
- Process Rigveda only
- Change to `COLLECTION_NAME=yajurveda_collection`
- Process Yajurveda only

**For unified collection (recommended):**
- Keep same `COLLECTION_NAME` for all related texts
- Rely on metadata to distinguish sources

### 2. Reindexing

The system uses a chunks cache file (`docs_chunks.pkl`). To reindex:
- Use `--force` flag to force clean reindex
- Or manually delete `vector_store/ancient_history/` folder

### 3. Memory Considerations

Processing multiple large PDFs requires:
- Sufficient disk space for markdown conversion
- RAM for embedding generation
- Time for indexing (proportional to total content)

**Example:** 2 PDFs × 500 pages × 2000 chars/page = ~2M chars to embed

### 4. Citation Clarity

When multiple documents discuss the same topic, the AI may cite both:
- Citations include `document_name` and `document_number`
- Users can see which answer comes from which text

---

## Future Enhancements

### Phase 1 (Current - DONE ✅)
- ✅ Multi-PDF processing in single CLI run
- ✅ Unified vector store with metadata preservation
- ✅ Source attribution in retrieved chunks

### Phase 2 (TODO)
- [ ] Document filtering: `--filter-source rigveda` to search only one text
- [ ] Source preference weighting: prioritize Rigveda results
- [ ] Cross-reference detection: automatically link related passages
- [ ] Document comparison mode: side-by-side answers

### Phase 3 (Advanced - TODO)
- [ ] Knowledge graph connecting entities across texts
- [ ] Timeline reconstruction (Early Vedic → Later Vedic)
- [ ] Entity tracking: "Where is X mentioned across all texts?"
- [ ] Contradiction detection: "What differs between texts?"

---

## Troubleshooting

### Issue 1: "PDF not found"

**Error:**
```
FileNotFoundError: PDF not found: rigveda-griffith.pdf
```

**Solution:**
- Ensure PDFs are in project root OR use absolute paths
- Check filename spelling (case-sensitive on Linux/macOS)

### Issue 2: Only One Document Indexed

**Symptom:**
```bash
python test_multi_pdf.py
# Shows only 1 document
```

**Solution:**
- Check `local_store/ancient_history/` - should have multiple subfolders
- Ensure both PDFs were processed (check logs)
- Run with `--force` to force reindex

### Issue 3: Old Data Not Cleared

**Symptom:** Query results don't include new PDF content

**Solution:**
```bash
# Clean everything
rm -rf local_store/ancient_history/
rm -rf vector_store/ancient_history/
rm -rf vector_store_tmp_*/

# Reprocess with --force
python src/cli_run.py --pdfs doc1.pdf doc2.pdf --force
```

### Issue 4: Out of Memory During Indexing

**Solution:**
- Process PDFs one at a time
- Use smaller chunk sizes (edit `config.py`)
- Close other applications to free RAM

---

## Summary

✅ **Enhanced CLI**: Now accepts multiple PDFs via `--pdf` or `--pdfs`
✅ **Unified Index**: All documents in single collection for efficient search
✅ **Source Attribution**: Metadata preserved for each document
✅ **Backward Compatible**: Single PDF processing still works
✅ **Ready for Yajurveda**: Can add North Yajurveda alongside Rigveda

**Next Steps:**
1. Place both PDFs in project root
2. Run: `python src/cli_run.py --pdfs rigveda-griffith.pdf yajurveda-griffith.pdf`
3. Verify with: `python test_multi_pdf.py`
4. Start querying both texts simultaneously!

---

**Status**: ✅ Implemented and Ready for Testing
**Last Updated**: December 26, 2024
