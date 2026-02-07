# Solution: Add Genealogical Metadata to Qdrant Cloud

## Problem Analysis

**Root Cause Identified:**
Qdrant Cloud is missing custom metadata fields that the local store has. Specifically:
- ❌ `preprocessing='sanskrit'` (used for Sanskrit prioritization)
- ❌ `source` and `source_type` fields (used for genealogical filtering)
- ❌ Proper `keywords` array with 'sanskrit' tag

**Impact:** 
- Sanskrit prioritization (2.5x boost) WORKS for local store
- Sanskrit prioritization FAILS for Qdrant Cloud (no metadata to check)
- Genealogical queries fail on Cloud but work locally

## Solution: Option 4 - Enrich Metadata at Source

**Approach:** Add custom metadata fields to `_metadata.json` files BEFORE uploading to Qdrant Cloud.

### Step 1: Enrich Metadata Files (DONE ✅)

**Script:** `enrich_metadata.py`

**What it did:**
```python
# For each Rigveda _metadata.json file, added:
metadata['preprocessing'] = 'sanskrit'
metadata['source'] = 'Rigveda Mandala X'
metadata['source_type'] = 'veda'
metadata['keywords'].append('sanskrit')
```

**Results:**
- ✅ All 10 Rigveda mandala metadata files updated
- ✅ `r01_metadata.json` now has:
  - `preprocessing: 'sanskrit'`
  - `source: 'Rigveda Mandala 1'`
  - `source_type: 'veda'`
  - `keywords: [..., 'sanskrit']`

### Step 2: Re-Index Qdrant Cloud

**Why:** We need to delete the old Cloud collection and re-create it from the newly enriched metadata files.

**How:**

#### Option A: Using Qdrant Dashboard
1. Go to Qdrant Cloud Dashboard
2. Delete collection `ancient_history`
3. Run: `python -c "from src.utils.index_files import create_qdrant_vector_store; create_qdrant_vector_store(force_recreate=True)"`

#### Option B: Using Python
```bash
python src/utils/cleanup_and_reupload_qdrant.py
```

#### Option C: Manual Re-Index
```python
import os
os.environ['FORCE_RECREATE_QDRANT'] = 'true'

from src.utils.index_files import create_qdrant_vector_store
vector_store, chunks = create_qdrant_vector_store(force_recreate=True)
print("✅ Qdrant Cloud re-indexed with enriched metadata")
```

### Step 3: Verify Metadata in Cloud

After re-indexing, verify the new metadata is in Qdrant Cloud:

```bash
python check_qdrant_cloud_metadata.py
```

**Expected output:**
```
Metadata keys: [..., 'preprocessing', 'source', 'source_type', ...]
  - preprocessing: sanskrit
  - source: Rigveda Mandala 1
  - source_type: veda
  - keywords: [..., 'sanskrit']
```

### Step 4: Test Genealogical Queries

```bash
# With local store (should work)
python test_sudas_query.py

# With Streamlit (now should work with Cloud too)
streamlit run src/sanskrit_tutor_frontend.py
```

**Expected answer:** "The father of Sudas is Divodasa."

## Why This Works

**Data Flow with Enriched Metadata:**

```
local_store/r01_metadata.json (now has 'preprocessing': 'sanskrit')
  ↓
chunk_doc() in index_files.py
  ↓
chunks with metadata (includes 'preprocessing': 'sanskrit')
  ↓
QdrantVectorStore.from_documents(chunks)
  ↓
Qdrant Cloud (metadata now includes 'preprocessing': 'sanskrit')
  ↓
HybridRetriever._get_semantic_matches()
  ↓
Sanskrit prioritization boost applied! (2.5x multiplier)
  ↓
Correct answer: "Divodasa"
```

## Benefits of This Approach

✅ **Permanent:** Metadata stays in the source files  
✅ **Scalable:** Works for future documents too  
✅ **Cloud-Ready:** Metadata now transfers to Qdrant Cloud  
✅ **Minimal Code Change:** Only added one metadata enrichment script  
✅ **Reversible:** Metadata files can be reverted if needed  
✅ **Future-Proof:** All downstream processes (local and cloud) benefit  

## Why Previous Attempts Didn't Work

1. **Force Local Store:** ❌ Defeats purpose of Cloud, not scalable
2. **Metadata Detection in Retriever:** ⚠️ Works locally but doesn't help Cloud
3. **Environment Variables:** ❌ Temporary workaround, not permanent
4. **Add Metadata at Upload Time:** ✅ **THIS SOLUTION** - Most elegant

## Files Modified

- ✅ `local_store/*/r*_metadata.json` - 10 Rigveda files enriched
- ✅ `enrich_metadata.py` - Created script to add metadata
- ⏳ Qdrant Cloud collection - To be re-indexed

## Deployment Checklist

- [ ] Run `enrich_metadata.py` to update metadata files
- [ ] Delete old Qdrant Cloud collection or force_recreate=True
- [ ] Re-index with `create_qdrant_vector_store(force_recreate=True)`
- [ ] Verify metadata in Cloud with `check_qdrant_cloud_metadata.py`
- [ ] Test: `python test_sudas_query.py` ✅ Should return "Divodasa"
- [ ] Deploy Streamlit and test genealogical queries
- [ ] Verify non-genealogical queries still work (regression test)

## Timeline

- **Completed:** ✅ Metadata enrichment
- **Next:** Re-index Qdrant Cloud (5-10 minutes)
- **Then:** Testing and deployment (10 minutes)
- **Total:** ~20 minutes to fix

## Technical Details

### What Happens During Indexing

1. `load_documents_with_metadata()` loads from local_store + _metadata.json
2. **NEW:** Metadata now includes `preprocessing='sanskrit'`
3. `chunk_doc()` creates chunks, metadata flows through
4. `QdrantVectorStore.from_documents()` uploads to Cloud
5. **NEW:** Cloud now has the enriched metadata in payload
6. `HybridRetriever` can now detect Sanskrit via metadata

### Metadata Flow

```
_metadata.json (source)
    ↓
Document.metadata (LangChain)
    ↓
chunk.metadata (after chunking)
    ↓
Qdrant payload['metadata'] (on Cloud)
    ↓
Retrieved as doc.metadata in HybridRetriever
    ↓
Sanskrit prioritization logic checks metadata['preprocessing']
    ↓
2.5x boost applied!
```

## Fallback Plan

If re-indexing fails:
```bash
# Keep using local store temporarily
export FORCE_LOCAL_STORE=true
streamlit run src/sanskrit_tutor_frontend.py

# Or rollback metadata changes
git checkout local_store/*/r*_metadata.json
```

## Long-Term Improvements

- [ ] Automate metadata enrichment during initial document loading
- [ ] Add metadata validation step before uploading to Cloud
- [ ] Create admin UI to manage metadata enrichment
- [ ] Extract genealogical info programmatically from content
- [ ] Build genealogical knowledge graph for better queries

