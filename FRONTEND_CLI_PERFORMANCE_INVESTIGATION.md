# CLI vs Frontend Performance Discrepancy - Investigation Guide

## The Real Issue

Both **should be using Qdrant Cloud** (27,900 points with Rigveda), but they're giving **different quality answers**:

- **CLI:** "The father of Sudas is Divodasa" ✅ Correct
- **Frontend:** "father not explicitly mentioned" ❌ Missing data

## Key Constraint

✅ **Frontend MUST use Qdrant Cloud** for Streamlit Cloud deployment  
✅ **Cannot use local vector_store** (not accessible in cloud environment)

## Possible Root Causes

### 1. Different Retriever Configurations

**CLI Retriever setup:**
- `src/utils/retriever.py` - HybridRetriever class
- BM25 + Semantic search
- Proper noun boosting
- MW Concept Store integration
- Sanskrit preprocessing

**Frontend Retriever setup:**
- Need to verify if using same HybridRetriever
- Check if all components initialized identically

### 2. Different LLM Instructions

**CLI:**
- Uses `final_block_rag.py` with specific prompts
- Has evaluation and refinement loops
- Sanskrit-aware question processing

**Frontend:**
- Uses `agentic_rag.py`
- May have different prompt structure
- May have different evaluation criteria

### 3. Different Question Processing

**CLI question:** "Who is father of Sudas?"
- Processes through: grammar check → enrichment → retrieval → ranking

**Frontend question:** "Who is father of Sudas?"
- May skip some steps or process differently

### 4. Embedding Model Mismatch

**Check if using same embedding:**
```python
# Both should use:
EMBEDDING_PROVIDER=local-multilingual
# paraphrase-multilingual-mpnet-base-v2 (768-dim)
```

### 5. Vector Store State

**After Rigveda upload:**
- Local: Fresh 3,902 points (well-ranked)
- Cloud: 27,900 total points (Rigveda may be mixed in)

The **local version may rank Sudas references higher** because it's a smaller, more focused collection.

## Diagnostic Steps

### Step 1: Check Logs
```bash
# CLI logs will show:
# - Which retriever being used
# - How many docs retrieved
# - Reranking scores
# - LLM prompts

# Frontend logs will show:
# - Different pipeline
# - May have less detail
```

### Step 2: Verify Retriever Configuration
```python
# In CLI and Frontend, check:
print(type(retriever))  # Should be HybridRetriever
print(retriever.k)      # Number of docs retrieved
print(retriever.mw_store)  # MW enabled?
```

### Step 3: Compare Retrieved Documents

**CLI retrieval for "Who is father of Sudas?":**
- How many documents returned?
- What are the top 3 scores?
- Which documents mention Divodasa?

**Frontend retrieval for same query:**
- Same number of documents?
- Different ranking?
- Missing Divodasa reference?

### Step 4: Check Embedding Models

```python
# Verify both use same embedding
from src.settings import Settings
embed_model = Settings.get_embed_model()
print(embed_model)  # Should be paraphrase-multilingual-mpnet-base-v2
```

## Most Likely Cause

Given that:
1. CLI is working correctly with cloud Qdrant
2. Frontend is using same cloud Qdrant
3. But getting worse results

**Most likely:** Different retriever or ranking configuration between CLI and frontend RAG pipelines.

### Hypothesis: Frontend's Agentic RAG May Be Less Aggressive

**CLI (final_block_rag.py):**
- Has evaluation loop
- Refines poor answers
- Multiple retrieval attempts
- Aggressive reranking

**Frontend (agentic_rag.py):**
- May accept first answer
- May not refine
- May have different document retrieval count

## Next Investigation

### To Identify the Exact Issue

1. **Run same query in both:**
   ```bash
   # CLI
   Q> Who is father of Sudas?
   # Note the retrieved documents and scores
   
   # Frontend (in debug)
   # Insert logging to show retrieved documents
   ```

2. **Compare retrieved documents** - Are they different or just ranked differently?

3. **Compare LLM inputs** - Is the prompt different? Are different docs being shown?

4. **Check embedding consistency** - Are both using exact same embedding model?

## Potential Solutions (When You Identify the Cause)

### If retriever is different:
```python
# Ensure frontend uses same retriever as CLI
# Make sure HybridRetriever is initialized identically
```

### If ranking is different:
```python
# Verify k parameter (number of docs retrieved)
# Check reranking score thresholds
# Ensure proper noun boosting is active
```

### If preprocessing is different:
```python
# Verify Sanskrit preprocessing is enabled
# Check Phase 1 settings in both
```

### If LLM is different:
```python
# Ensure both use same model and temperature
# Check prompt templates are identical
```

## Strategy Going Forward

✅ **Keep cloud Qdrant for both** (necessary for Streamlit Cloud)
✅ **Investigate which component differs** between CLI and Frontend
✅ **Sync the better-performing configuration** to frontend
✅ **Test locally first** before Streamlit Cloud deployment

This way:
- Streamlit Cloud frontend will work correctly
- CLI will continue working
- Both will give consistent high-quality answers from cloud Qdrant

---

## Files to Compare

- `src/final_block_rag.py` - CLI's RAG pipeline
- `src/agentic_rag.py` - Frontend's RAG pipeline
- `src/utils/retriever.py` - Retriever configuration
- `src/settings.py` - Embedding and model settings

## Summary

The issue is NOT about which vector store is used (both should use cloud).  
The issue is likely about **HOW** the retriever or LLM processes queries differently.

Once you identify which component differs, we can sync the configurations and get the frontend working as well as the CLI.
