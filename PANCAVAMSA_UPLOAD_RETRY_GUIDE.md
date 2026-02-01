# Pancavamsa Brahmana Upload Retry & Verification Guide

## Status Summary

**Upload Attempt 1 - Partially Failed:**
- ✅ Batches 1-8: Successfully uploaded 8,000 points
- ❌ Batch 9: Timeout error on write operation
- ⏳ Batches 10-14: Not processed (5,888 points remaining)
- **Total to upload:** 13,888 chunks from Pancavamsa Brahmana

**Source Verification:**
- ✅ Local file: 41,384 lines (complete)
- ✅ All 25 chapters present in source text
- ✅ Chapter markers found: I-XXV confirmed
- ✅ Text ends with: "THE BRAHMANA of TWENTY FIVE CHAPTERS"

---

## Why Batch 9 Failed

The timeout likely occurred due to:
1. **Large batch size** - Batch of 1,000 points may exceed Qdrant Cloud write timeout
2. **Network latency** - Cloud API response time exceeded limit
3. **Server load** - Temporary Qdrant Cloud unavailability
4. **Payload size** - Total vector data for 1,000 points may be too large

**Solution:** Reduce batch size to 500 points and add retry logic

---

## Retry Steps

### Step 1: Run Verification Script First

Before retrying upload, verify chapter coverage:

```bash
python3 verify_pancavamsa_chapters.py
```

**Expected Output:**
```
✅ VERIFICATION PASSED: All 25 chapters are represented
```

This confirms:
- Source text is complete (all 25 chapters)
- Chapter references are properly formatted
- Ready for upload

### Step 2: Retry Upload with Smaller Batch Size

Run the improved upload script with reduced batch size:

```bash
python3 upload_vector_to_Qdrant_with_retry.py \
  --collection ancient_history \
  --recreate false \
  --batch-size 500 \
  --retry-count 3
```

**Parameters Explanation:**
- `--collection ancient_history` - Target collection (append mode)
- `--recreate false` - Keep existing points, add to collection
- `--batch-size 500` - Reduced from 1,000 to avoid timeouts
- `--retry-count 3` - Retry failed batches up to 3 times

### Step 3: Monitor Upload Progress

The script will display:
```
   ✅ Batch 9: Uploaded 500 points (Total: 8,500/13,888)
   ✅ Batch 10: Uploaded 500 points (Total: 9,000/13,888)
   ✅ Batch 11: Uploaded 500 points (Total: 9,500/13,888)
   ...
```

**Expected completion time:**
- 14 batches × 500 points = 28 API calls
- ~5-10 minutes depending on network
- With retries: up to 15 minutes worst case

### Step 4: Verify Final Count

After upload completes, check cloud collection:

```bash
python3 -c "
from qdrant_client import QdrantClient
import os
from dotenv import load_dotenv

load_dotenv()
client = QdrantClient(url=os.getenv('QDRANT_URL'), api_key=os.getenv('QDRANT_API_KEY'))
info = client.get_collection('ancient_history')
print(f'✅ Final point count: {info.points_count}')
print(f'   Expected: ~25,000+ (22,000 existing + 13,888 PB)')
"
```

---

## Upload Script Features

### New Retry with Exponential Backoff

```python
RETRY_DELAY = 5  # seconds
RETRY_COUNT = 3  # max attempts per batch

# If batch fails:
# Attempt 1: Error → Wait 5s
# Attempt 2: Error → Wait 5s
# Attempt 3: Error → Log as failed, continue
```

### Partial Upload Handling

- Uploads resume from batch 9 (not restart from batch 1)
- Already-uploaded points in cloud are preserved
- Failed batches are logged for manual retry if needed
- No duplicate points (upsert mode overwrites by ID)

### Progress Tracking

Real-time feedback:
```
📤 Uploading from local to cloud...
============================================================
   ✅ Batch 1: Uploaded 500 points (Total: 500/13,888)
   ✅ Batch 2: Uploaded 500 points (Total: 1,000/13,888)
   ⚠️  Batch 3: Error (attempt 1/3): Timeout
   ⚠️  Batch 3: Error (attempt 2/3): Timeout
   ✅ Batch 3: Uploaded 500 points (Total: 1,500/13,888)  [Succeeded on retry]
```

---

## If Upload Still Times Out

### Option A: Even Smaller Batch Size

```bash
python3 upload_vector_to_Qdrant_with_retry.py \
  --collection ancient_history \
  --recreate false \
  --batch-size 250 \
  --retry-count 5
```

### Option B: Upload During Off-Peak Hours

Qdrant Cloud may have less load during:
- 2-6 AM UTC
- Weekday early mornings

### Option C: Split Upload Manually

Upload specific sections separately:

```bash
# Only upload first 5,000 points
# (requires modifying script to add --limit-points flag)
```

---

## Expected Final State

**Collection Statistics:**
- Name: `ancient_history`
- Total points: ~24,888-25,888
  - Rigveda (Griffith + Sharma): ~15,000 points
  - Satapatha Brahmana: ~4,000 points
  - Grammar/Language: ~2,000-3,000 points
  - Ramayana: ~1,000-2,000 points
  - **Pancavamsa Brahmana (NEW): ~1,888 points**

**Citation Format:**
- All PB citations in chunks: `PB X.Y.Z` format
- Example: "PB 5.3.2" (Book 5, Section 3, Verse 2)
- RAG queries will return PB citations in responses

---

## Troubleshooting

### Problem: Still getting timeout after retry

**Solution 1:** Check Qdrant Cloud status
```bash
curl -s https://your-qdrant-instance.com/health | jq .
```

**Solution 2:** Verify .env credentials are correct
```bash
grep QDRANT .env | head -3
```

**Solution 3:** Test with single batch upload manually
```python
from qdrant_client import QdrantClient
client = QdrantClient(url="...", api_key="...")
# Manually upsert 100 points to test
```

### Problem: "Collection does not exist" error

**Expected:** Script will create it automatically on first upload

**If it fails:**
```bash
python3 -c "
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

client = QdrantClient(url='...', api_key='...')
client.create_collection(
    collection_name='ancient_history',
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
)
"
```

### Problem: Point counts don't match

**Expected:** 13,888 local → should see 13,888 added to cloud

**Verify:**
1. Check local point count: `python3 -c "from qdrant_client import QdrantClient; c = QdrantClient(path='vector_store'); print(c.get_collection('ancient_history').points_count)"`
2. Compare with cloud point count (should differ by previously-existing count)
3. If mismatch > 100 points, re-run upload with `--batch-size 250`

---

## Success Criteria

✅ **Upload successful when:**
1. No timeout errors in final 5 batches
2. Cloud point count increased by ~13,888
3. Verification script shows all 25 chapters represented
4. RAG queries return PB citations in proper format

✅ **Verification commands:**
```bash
# 1. Check upload completion
python3 upload_vector_to_Qdrant_with_retry.py --collection ancient_history

# 2. Verify chapters in chunks
python3 verify_pancavamsa_chapters.py

# 3. Test RAG query (after deployment)
curl http://localhost:8000/api/query -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "Pancavamsa fire ritual", "context_type": "ancient_history"}'
```

---

## Next Steps After Upload

1. **Update documentation**
   - Add PB citation format to RAG config
   - Document "PB X.Y.Z" in help text

2. **Deploy to production**
   - Restart RAG service to load updated collection
   - Warm up cache with test queries

3. **Monitor performance**
   - Track response times for PB queries
   - Verify citation extraction works

4. **Update web UI**
   - Add Pancavamsa as available source text
   - Display "Pancavamsa Brahmana (25 chapters)" in source selector

---

## Reference Data

**Pancavamsa Brahmana Summary:**
- Text: Sanskrit prose, W. Caland translation (English, 1931)
- Chapters: 25 (hence "Pancha-vamsa" = five-five)
- Publisher: Asiatic Society of Bengal
- File size: 1.5 MB
- Line count: 41,384 lines
- Chunks created: 13,888 (varies by chunking strategy)
- Citation format: `PBr. X.Y.Z` (Book.Section.Verse)
- Proper nouns: 70 extracted (deities, sages, schools, rituals, locations)

**Citation Examples:**
- `PBr. I. 1. 1` → Stored as `PB 1.1.1`
- `PBr. XXV. 10. 17` → Stored as `PB 25.10.17`
- `PBr. V. 3. 2` → Stored as `PB 5.3.2`
