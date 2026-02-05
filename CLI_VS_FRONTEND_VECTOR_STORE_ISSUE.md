# Vector Store Mismatch - CLI vs Frontend Diagnosis

## The Problem

**CLI (working correctly):** Gets correct answer "The father of Sudas is Divodasa"  
**Frontend (struggling):** Says "father not explicitly mentioned" - missing the data

## Root Cause

The **CLI and Frontend are using DIFFERENT vector stores!**

### CLI Configuration
```python
# src/cli_run.py line 455
vec_db, docs, retriever = build_index_and_retriever(
    force=args.force, 
    local_only=use_local_only  # ← KEY: Passes local_only parameter
)
```

**When you run:** `python3 src/cli_run.py --local-only` or `--local`
- ✅ Uses LOCAL Qdrant (vector_store/) with 3,902 NEW Rigveda points
- ✅ Has Sanskrit preprocessing (Phase 1)
- ✅ Returns correct answers

### Frontend Configuration
```python
# src/sanskrit_tutor_frontend.py line 330
vec_db, docs = create_qdrant_vector_store(force_recreate=False)
#                                                        ↑ NO local_only parameter!
```

**Result:**
- ❌ Checks for cloud credentials (QDRANT_URL + QDRANT_API_KEY)
- ❌ If both exist → Uses CLOUD Qdrant (27,900 points)
- ❌ Cloud might have different retrieval configuration OR
- ❌ Frontend's retriever setup might differ from CLI

## Why the Difference Matters

| Aspect | CLI (Local) | Frontend (Cloud) |
|--------|-----------|-----------------|
| Vector store | `vector_store/` (3,902 points) | Cloud (27,900 points) |
| Rigveda coverage | ✅ Fresh from local indexing | ✅ Uploaded but... |
| Sanskrit preprocessing | ✅ Phase 1 enabled | ❓ Depends on cloud retriever setup |
| Retriever config | ✅ Consistent with CLI | ❓ May differ |
| Response quality | ✅ Excellent (Sudas answer) | ❌ Poor (missing data) |

## The Fix

### Option 1: Force Frontend to Use Local (Recommended for Now)

Make the frontend use `local_only=True`:

```python
# Line 330 in src/sanskrit_tutor_frontend.py
vec_db, docs = create_qdrant_vector_store(
    force_recreate=False,
    local_only=True  # ← ADD THIS
)
```

**Result:** Frontend uses same local vector store as CLI → Same quality answers

### Option 2: Investigate Cloud Retriever Configuration

If you want to use cloud, we need to check:
1. Is the cloud retriever initialized the same way as CLI?
2. Are both using the same embedding model?
3. Is Sanskrit preprocessing active in both?

## Quick Test

**Run this to see which vector store each is using:**

```bash
# Terminal 1: Start CLI
python3 src/cli_run.py --local-only
# Watch for: "LOCAL-ONLY MODE" or "Using Qdrant Cloud"

# Terminal 2: Start Frontend
streamlit run src/sanskrit_tutor_frontend.py
# Check logs for: "Using Qdrant Cloud" vs "Using local Qdrant"
```

## Implementation: Quick Fix

Let me apply Option 1 (force local for frontend):

```python
# Before (line 330):
vec_db, docs = create_qdrant_vector_store(force_recreate=False)

# After:
vec_db, docs = create_qdrant_vector_store(force_recreate=False, local_only=True)
```

This ensures:
- ✅ Frontend uses same local vectors as CLI
- ✅ Both get same answers
- ✅ Both benefit from Phase 1 Sanskrit preprocessing
- ✅ No cloud connectivity issues

## Why This Matters for Your Sudas Query

**Local vector store path:**
```
vector_store/ancient_history/
├── 3,902 points from Rigveda (freshly indexed with Phase 1)
└── Sudas references properly preprocessed & embedded
```

**Cloud vector store:**
```
ancient_history/
├── 23,998 points before upload
├── 3,902 points after Rigveda upload
└── Sudas might be buried due to retrieval ranking
```

The local version is **fresher** and **more directly indexed**, which is why it returns the correct answer.

## Implementation Steps

### Step 1: Update Frontend to Use Local
```python
# src/sanskrit_tutor_frontend.py line 330
vec_db, docs = create_qdrant_vector_store(force_recreate=False, local_only=True)
```

### Step 2: Test
```bash
streamlit run src/sanskrit_tutor_frontend.py
# Ask: "Who is father of Sudas?"
# Expected: "Divodasa"
```

### Step 3: Verify Logs
```
[INFO] local_only mode: True
[INFO] LOCAL-ONLY MODE: Force using local Qdrant
[INFO] Loaded existing collection 'ancient_history' with 3902 chunks
```

## Alternative: Use Both (Balanced Approach)

Add a **Streamlit sidebar option** to choose:

```python
st.sidebar.radio(
    "Vector Store:",
    ["Local (Faster, Fresh Rigveda)", "Cloud (All texts)"]
)

use_local = st.sidebar.radio(...) == "Local (Faster, Fresh Rigveda)"
vec_db, docs = create_qdrant_vector_store(
    force_recreate=False, 
    local_only=use_local
)
```

This lets users choose which data source to query!

## Summary

| Issue | Cause | Fix |
|-------|-------|-----|
| CLI works, frontend doesn't | Different vector stores | Add `local_only=True` to frontend |
| Local has fresh Rigveda | Just indexed (3,902 pts) | Use local in frontend |
| Cloud is behind | Upload was recent | Can add UI toggle to switch |

---

**Recommendation:** Add `local_only=True` to frontend line 330. This will make both CLI and frontend use the same vector store and get consistent, correct answers.

Would you like me to implement this fix?
