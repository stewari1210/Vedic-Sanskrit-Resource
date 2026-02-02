# Re-indexing Time Estimate: Multilingual Embeddings

**Date**: February 1, 2026  
**Task**: Re-index corpus with `paraphrase-multilingual-MiniLM-L12-v2` + Upload to Qdrant Cloud

---

## Current State

### Corpus Statistics
- **Total corpus size**: 57.4 MB (text files)
- **Number of files**: 9 text files
- **Current Qdrant points**: 26,921 chunks
- **Current embedding**: `all-mpnet-base-v2` (768 dimensions, English-only)
- **Target embedding**: `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions, multilingual)

### File Breakdown
```
50.2 MB - monier_williams_dictionary/mw.txt (MW dictionary - already in concept store)
1.6 MB  - pancavamsa_brahmana/pancavamsa_brahmana.txt
1.2 MB  - macdonell_vedic_grammar/macdonell_vedic_grammar.txt
1.2 MB  - satapatha_brahmana/part_01_books_1_2.txt
1.2 MB  - satapatha_brahmana/part_02_books_3_4.txt
0.9 MB  - satapatha_brahmana/part_04_books_8_9_10.txt
0.9 MB  - satapatha_brahmana/part_03_books_5_6_7.txt
0.2 MB  - satapatha_brahmana/part_05_books_11_12_13_14.txt
0.03 MB - mw-meta2.txt
```

**Note**: MW dictionary (50 MB) is already processed into concept store, so we DON'T need to re-embed it!

### Effective Corpus Size
**~7.2 MB of actual corpus text** (excluding MW dictionary)

---

## Time Estimate Breakdown

### Phase 1: Local Re-indexing

**Task**: Generate new embeddings with multilingual model

#### Step 1: Model Download (~2 minutes)
```bash
# Download paraphrase-multilingual-MiniLM-L12-v2
# Model size: ~450 MB
# Download speed: ~10 MB/s typical
```
- **Time**: 2-3 minutes (one-time)

#### Step 2: Embedding Generation
```python
# Corpus stats:
# - 7.2 MB text (excluding MW dictionary)
# - ~26,921 chunks (existing count)
# - Average chunk: ~270 characters

# Performance estimates for M1 Mac (CPU mode):
# - all-mpnet-base-v2: ~200 chunks/second
# - multilingual-MiniLM: ~250 chunks/second (smaller model)
```

**Calculation**:
```
26,921 chunks ÷ 250 chunks/sec = 107 seconds = ~2 minutes
```

**With batching overhead, file I/O, chunking**:
- **Best case**: 3-4 minutes
- **Typical**: 5-7 minutes
- **Conservative**: 10 minutes

#### Step 3: Create Local Qdrant Collection
```python
# Store embeddings in local Qdrant
# - Create new collection with 384-dim vectors
# - Insert 26,921 points
# - Build HNSW index
```

**Time**: 1-2 minutes

---

### Phase 2: Upload to Qdrant Cloud

**Task**: Upload 26,921 vectors to Qdrant Cloud

#### Upload Speed Analysis
```python
# Current collection: 26,921 points
# Vector size: 384 dimensions (multilingual) vs 768 (current)
# Data size per vector: 384 × 4 bytes = 1.5 KB
# Total vector data: 26,921 × 1.5 KB = ~40 MB

# Qdrant Cloud upload speed:
# - Batch size: 100-200 vectors per request
# - Network speed: 5-10 MB/s typical
# - API rate limits: ~10 requests/second
```

**Batch upload calculation**:
```
Scenario 1: Batch size 100, 10 req/sec
  - 26,921 ÷ 100 = 270 batches
  - 270 batches ÷ 10 req/sec = 27 seconds
  - With overhead: 1-2 minutes

Scenario 2: Batch size 200, conservative
  - 26,921 ÷ 200 = 135 batches
  - Network transfer: 40 MB ÷ 5 MB/s = 8 seconds
  - With retries, indexing: 3-5 minutes
```

**Typical upload time**: 3-5 minutes

---

## Total Time Estimate

### Best Case (Everything Optimal)
```
Model download:       2 min
Embedding generation: 3 min
Local indexing:       1 min
Upload to cloud:      1 min
----------------------------
TOTAL:               7 minutes
```

### Typical Case (Expected)
```
Model download:       3 min
Embedding generation: 5 min
Local indexing:       2 min
Upload to cloud:      3 min
----------------------------
TOTAL:               13 minutes
```

### Conservative Case (Safe Estimate)
```
Model download:       3 min
Embedding generation: 10 min
Local indexing:       2 min
Upload to cloud:      5 min
----------------------------
TOTAL:               20 minutes
```

---

## **Recommended Estimate: 15-20 minutes total**

### Breakdown:
1. **Model download**: 2-3 min (one-time)
2. **Re-indexing local files**: 7-12 min
3. **Upload to Qdrant Cloud**: 3-5 min

---

## Why Multilingual Model is FASTER

| Metric | all-mpnet-base-v2 | multilingual-MiniLM |
|--------|-------------------|---------------------|
| Dimensions | 768 | 384 (50% smaller!) |
| Model size | 420 MB | 470 MB |
| Speed | ~200 chunks/sec | ~250 chunks/sec |
| Upload size | 80 MB | 40 MB (50% less!) |
| Qdrant storage | More | Less |

**Benefits**:
- ✅ Faster embedding generation
- ✅ Faster uploads (50% less data)
- ✅ Less Qdrant Cloud storage
- ✅ Same or better quality for multilingual queries

---

## Implementation Steps

### Step 1: Switch Embedding Model (2 minutes)
```python
# In src/settings.py
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
```

### Step 2: Re-index Locally (7-12 minutes)
```bash
# Clear old local index
rm -rf vector_store/ancient_history

# Re-index with new model
python3 src/utils/index_files.py
# This will:
# - Load multilingual model
# - Chunk all corpus files
# - Generate 384-dim embeddings
# - Create local Qdrant collection
```

### Step 3: Upload to Cloud (3-5 minutes)
```bash
# Upload with improved script
python3 upload_vector_to_Qdrant_improved.py \
    --collection ancient_history \
    --recreate true

# This will:
# - Delete old cloud collection (768-dim)
# - Create new collection (384-dim)
# - Upload 26,921 points in batches
# - Verify upload completion
```

---

## What Will Improve with Multilingual Embeddings

### Before (English-only embeddings)
```
Query: "सरस्वती नदी के विलुप्त संबंधित श्लोक"
Embedding: [0.1, -0.3, ...] (random, no meaning)
Results: Irrelevant chunks (no understanding of Devanagari)
```

### After (Multilingual embeddings)
```
Query: "सरस्वती नदी के विलुप्त संबंधित श्लोक"
Embedding: [0.8, 0.6, ...] (meaningful, understands Hindi/Sanskrit)
+ MW Enhancement: "sarasvati river disappear verse"
Results: Relevant chunks about Sarasvati's disappearance
```

---

## Verification After Re-indexing

### Test Queries
```python
test_queries = [
    "सरस्वती नदी के विलुप्त होने",        # Devanagari
    "Sarasvatī river disappearance",     # IAST
    "अग्नि पूजा की विधि",                # Hindi
    "soma rasa का महत्व",                 # Mixed
]
```

### Expected Improvements
| Query Type | Before | After |
|------------|--------|-------|
| Devanagari | ❌ No results | ✅ Relevant results |
| IAST | ✅ Works | ✅ Better results |
| Hindi | ❌ No results | ✅ Relevant results |
| Mixed | ❌ Fails | ✅ Works |

---

## Optimization Tips

### Speed Up Embedding Generation
```python
# In src/settings.py
EMBEDDING_BATCH_SIZE = 32  # Increase from 16
EMBEDDING_DEVICE = "mps"   # Use Metal (M1 GPU) if available
```

### Speed Up Upload
```python
# In upload script
BATCH_SIZE = 200           # Larger batches
MAX_WORKERS = 4            # Parallel uploads
```

---

## Risk Mitigation

### Backup Strategy
```bash
# Before re-indexing, backup current collection
python3 -c "
from qdrant_client import QdrantClient
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
# Create snapshot
snapshot = client.create_snapshot('ancient_history')
print(f'Backup created: {snapshot.name}')
"
```

### Rollback Plan
If multilingual embeddings don't work well:
1. Keep old local vector store as backup
2. Can recreate old collection from backup snapshot
3. Switch back to `all-mpnet-base-v2` in settings

---

## Cost Analysis

### Qdrant Cloud Storage
```
Current: 26,921 vectors × 768 dim × 4 bytes = 82 MB
New:     26,921 vectors × 384 dim × 4 bytes = 41 MB

Savings: 41 MB (50% reduction!)
```

### Free Tier Limits
- Qdrant Cloud Free: 1 GB storage
- Current usage: 82 MB (8% of limit)
- After reindex: 41 MB (4% of limit)

**Conclusion**: Well within free tier, no cost concerns

---

## Final Recommendation

### Timeline
```
Today (Feb 1):
  [x] Steps 1 & 2 (MW integration) - DONE
  [ ] Test current system               - 10 min
  [ ] Backup current collection         - 2 min
  [ ] Switch to multilingual model      - 2 min
  
Tomorrow (Feb 2):
  [ ] Re-index locally                  - 10 min
  [ ] Upload to Qdrant Cloud            - 5 min
  [ ] Test bilingual queries            - 15 min
  [ ] Verify improvements               - 10 min
  --------------------------------
  TOTAL:                                ~45 minutes
```

### Success Criteria
- ✅ Devanagari queries return relevant results
- ✅ Hindi queries work correctly
- ✅ Mixed script queries (Hindi + English) work
- ✅ MW dictionary context enhances results
- ✅ IAST queries still work (or better)

---

## Summary

**Expected Total Time: 15-20 minutes**

- ✅ Model download: 2-3 min (one-time)
- ✅ Re-indexing: 7-12 min
- ✅ Upload: 3-5 min

**Impact**: 
- Enables true bilingual support (Devanagari/Hindi/IAST)
- 50% smaller vectors (faster, less storage)
- Combined with MW integration → powerful bilingual RAG

**Risk**: Low (can rollback if needed)

**Recommendation**: Do it tomorrow when you have 30-45 minutes for full process + testing
