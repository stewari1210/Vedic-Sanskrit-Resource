# Multilingual Re-indexing Guide (768 Dimensions)

## Overview

This guide explains how to re-index the corpus with **multilingual embeddings** while maintaining **768 dimensions** (no Qdrant schema changes needed).

## Model Change

**FROM**: `sentence-transformers/all-mpnet-base-v2` (English-only, 768-dim)  
**TO**: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` (Multilingual, 768-dim)

### Benefits
✅ **Same dimensions** (768) - no Qdrant collection recreation needed  
✅ **Multilingual support** - Hindi, Sanskrit, Devanagari, 50+ languages  
✅ **High quality** - MPNet architecture (similar to current model)  
✅ **Simple update** - just overwrite existing vectors  
✅ **MW integration ready** - works with transliteration layer  

## Time Estimate

| Step | Duration | Details |
|------|----------|---------|
| Model download | Already done! | 1.1 GB model downloaded during testing |
| Local re-indexing | 7-12 minutes | 26,921 chunks, 7.2 MB corpus |
| Upload to Qdrant Cloud | 3-5 minutes | Update existing points (no schema change) |
| **TOTAL** | **10-17 minutes** | ~15 minutes average |

## Re-indexing Steps

### Step 1: Update Configuration ✅ DONE

The embedding model has been updated in `src/settings.py`:

```python
# Line ~166 in src/settings.py (local-best provider)
model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
```

### Step 2: Clear Old Local Index

```bash
cd /Users/shivendratewari/github/Vedic-Sanskrit-Tutor

# Remove old local vector store (forces re-indexing)
rm -rf vector_store/ancient_history
```

### Step 3: Re-index Corpus Locally

```bash
# Re-index all files in local_store/ with new multilingual embeddings
python3 src/utils/index_files.py

# Expected output:
# - Processing 9 text files (7.2 MB effective corpus)
# - Generating embeddings with paraphrase-multilingual-mpnet-base-v2
# - Creating 26,921 chunks with 768-dim vectors
# - Duration: ~7-12 minutes
```

### Step 4: Upload to Qdrant Cloud (Update Mode)

Check your upload script - you want to **UPDATE** existing points, not recreate:

```bash
# Option A: If upload script supports --update flag
python3 upload_vector_to_Qdrant_improved.py --collection ancient_history --update

# Option B: Or use standard upload (will overwrite points with same IDs)
python3 upload_vector_to_Qdrant_improved.py --collection ancient_history
```

**Important**: Since dimensions are the same (768), you can **update vectors in-place**. The upload script should:
- Keep existing collection schema
- Update vector values for existing point IDs
- Preserve all metadata (titles, sources, etc.)
- Duration: ~3-5 minutes

### Step 5: Test Bilingual Queries

After re-indexing, test with Streamlit:

```bash
# Start Streamlit app
bash run_sanskrit_tutor_web.sh
```

**Test queries**:
1. **Devanagari**: `सरस्वती नदी के विलुप्त होने का उल्लेख`
2. **Hindi**: `अग्नि पूजा की विधि क्या है?`
3. **IAST**: `Sarasvatī river disappearance in Vedas`
4. **Mixed**: `soma रस का महत्व क्या है?`

**Expected results**:
- ✅ All queries return relevant corpus documents
- ✅ MW context expander shows dictionary definitions
- ✅ Vedic references appear in MW context
- ✅ LLM answers are grounded in retrieved context

## Verification Checklist

After re-indexing:

- [ ] Check Qdrant collection dimensions are still 768:
  ```bash
  python3 -c "from qdrant_client import QdrantClient; client = QdrantClient(url='<your-url>', api_key='<your-key>'); print(client.get_collection('ancient_history'))"
  ```

- [ ] Verify point count unchanged (26,921 points):
  ```bash
  python3 -c "from qdrant_client import QdrantClient; client = QdrantClient(url='<your-url>', api_key='<your-key>'); print(client.count('ancient_history'))"
  ```

- [ ] Test Devanagari query in Streamlit UI
- [ ] Verify MW context appears in results
- [ ] Check response quality for bilingual queries

## Troubleshooting

### Issue: Upload script recreates collection instead of updating

**Solution**: Modify upload script to update existing points:

```python
# In upload script, use upsert instead of recreate
client.upsert(
    collection_name="ancient_history",
    points=points,
    wait=True
)
```

### Issue: Dimension mismatch error

**Check**: Verify model is actually 768-dim:

```bash
python3 -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2'); print('Dimensions:', model.get_sentence_embedding_dimension())"
```

Should output: `Dimensions: 768`

### Issue: Slow re-indexing

**Optimization**: Use GPU if available:

```bash
# Check if MPS (Mac GPU) is available
python3 -c "import torch; print('MPS available:', torch.backends.mps.is_available())"

# If yes, update EMBEDDING_DEVICE in .env or config
# EMBEDDING_DEVICE=mps  # Mac GPU
# EMBEDDING_DEVICE=cuda  # NVIDIA GPU
```

## Why 768 Dimensions Work

The `paraphrase-multilingual-mpnet-base-v2` model:
- Uses the same **MPNet architecture** as the current model
- Outputs **768-dimensional vectors** (verified above)
- Trained on **parallel corpora** (50+ languages including Hindi)
- Maintains **semantic similarity** across languages
- Compatible with existing Qdrant collection schema

This means:
1. **No schema migration** - same vector size, same distance metric (Cosine)
2. **Drop-in replacement** - just update model name in settings
3. **Backward compatible** - can mix old and new embeddings temporarily
4. **Zero downtime** - update points incrementally if needed

## Post-Reindexing Benefits

After completion, your RAG system will:

1. **Understand Devanagari queries** directly (no transliteration needed for search)
2. **Handle mixed-script queries** (e.g., "soma रस का महत्व")
3. **Cross-lingual retrieval** (Hindi query → Sanskrit text matches)
4. **MW integration enhanced** - transliteration + multilingual search
5. **Better semantic matching** for Indic language concepts

## Timeline Summary

| Task | Duration |
|------|----------|
| Configuration update | ✅ Done (1 minute) |
| Clear old index | 10 seconds |
| Re-index locally | 7-12 minutes |
| Upload to cloud | 3-5 minutes |
| Testing | 10-15 minutes |
| **TOTAL** | **~30 minutes** |

**Status**: Ready to proceed! Model already downloaded (1.1 GB).

---

**Next Step**: Run Step 2 (clear old index) when you're ready to start re-indexing.
