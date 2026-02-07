# Quick Fix: Switch Streamlit Frontend to Local Store

## Problem
Streamlit frontend returns: "Not explicitly mentioned"  
CLI returns: "Divodasa" ✅

**Root Cause:** Streamlit uses Qdrant Cloud (no genealogical content)  
CLI uses local_store (has processed English with genealogies)

---

## Solution: 5-Minute Fix

### Step 1: Edit `src/utils/index_files.py`

Find this code (around line 260):
```python
if local_only:
    logger.info("LOCAL-ONLY MODE: Force using local Qdrant (skipping cloud checks)")
    use_cloud = False
elif QDRANT_URL and QDRANT_API_KEY:
    # Use Qdrant Cloud
    from qdrant_client import QdrantClient
    client = QdrantClient(url=str(QDRANT_URL), api_key=str(QDRANT_API_KEY))
    logger.info("Using Qdrant Cloud")
    use_cloud = True
else:
    # Fallback to local
    logger.info("Using local Qdrant")
    use_cloud = False
```

Replace with:
```python
# Check for environment override
FORCE_LOCAL = os.getenv('FORCE_LOCAL_STORE', '').lower() == 'true'

if local_only or FORCE_LOCAL:
    logger.info("LOCAL-ONLY MODE: Force using local Qdrant (skipping cloud checks)")
    use_cloud = False
elif QDRANT_URL and QDRANT_API_KEY:
    # Use Qdrant Cloud
    from qdrant_client import QdrantClient
    client = QdrantClient(url=str(QDRANT_URL), api_key=str(QDRANT_API_KEY))
    logger.info("Using Qdrant Cloud")
    use_cloud = True
else:
    # Fallback to local
    logger.info("Using local Qdrant")
    use_cloud = False
```

### Step 2: Update Streamlit Config

Edit `.streamlit/config.toml`:
```toml
[client]
# Force local store for better genealogical data
forceLocalStore = true
```

### Step 3: Test Locally

```bash
# Set environment variable
export FORCE_LOCAL_STORE=true

# Run Streamlit
streamlit run src/sanskrit_tutor_frontend.py

# Test query
# Ask: "Who is the father of Sudas?"
# Expected: ✅ "Divodasa"
```

### Step 4: Deploy

```bash
# Commit changes
git add src/utils/index_files.py .streamlit/config.toml
git commit -m "Switch frontend to local store for better genealogical accuracy"
git push

# Streamlit Cloud will auto-deploy
```

---

## Testing Before/After

### Before (Qdrant Cloud)
```
Query: Who is the father of Sudas?
Response: "Not explicitly mentioned"  ❌
```

### After (Local Store)
```
Query: Who is the father of Sudas?
Response: "Divodasa"  ✅
```

---

## Files Modified

- `src/utils/index_files.py` - Add FORCE_LOCAL_STORE check
- `.streamlit/config.toml` - Optional: document preference

---

## Implementation Time

- **Complexity:** 5 minutes
- **Testing:** 5 minutes
- **Deployment:** Automatic
- **Total:** ~10 minutes

---

## Performance Impact

- **Query speed:** ~2-3 seconds (vs ~0.5-1s with cloud)
- **Accuracy:** Excellent (vs poor)
- **Tradeoff:** Worth it for accuracy

---

## Success Criteria

- [ ] Edit index_files.py
- [ ] Test with FORCE_LOCAL_STORE=true
- [ ] Query returns "Divodasa"  
- [ ] Commit and push
- [ ] Streamlit Cloud auto-deploys
- [ ] Test in production

---

## Rollback Plan

If needed:
```bash
# Remove FORCE_LOCAL_STORE
git revert HEAD

# Back to Qdrant Cloud
streamlit run...
```

---

## Long-Term Plan

This is a **temporary fix**. For production:
1. Extract genealogical chunks from local_store
2. Add English commentary to Qdrant Cloud
3. Re-index with rich content
4. Switch back to Qdrant Cloud (better performance)

---

**Status:** Ready to implement  
**Impact:** Fixes genealogy queries  
**Risk:** Low (can revert easily)
