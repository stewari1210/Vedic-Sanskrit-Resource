# ⚡ RAG Retrieval Fix - Quick Summary

## Problem
Asking "Who is Sudas?" returned RV 7.33 (wrong hymn) instead of RV 1.33 or RV 7.18 (correct hymns mentioning Sudas).

## Root Cause  
**Double citation formatting broke the retrieval accuracy:**
1. `corpus_examples_search()` formatted citations
2. `synthesize_answer_node()` tried to format again
3. Lost metadata → wrong documents retrieved

## Solution
Call retriever directly in `execute_tools_node()` instead of through tool abstraction:

```python
# OLD (loses metadata):
result = corpus_examples_search.invoke({...})  # Returns formatted string
corpus_examples = [Document(page_content=result)]  # Wraps string

# NEW (preserves metadata):
retriever = get_shared_retriever()
corpus_examples = retriever.invoke(query)  # Returns Document objects
```

## Result
✅ Retrieval accuracy restored
✅ Citations still work perfectly
✅ Proper noun variants fully utilized

## Changes
- **File**: `src/utils/agentic_rag.py`
- **Lines changed**: ~20 (corpus_examples_search + execute_tools_node)
- **Commits**: `90ba9da`, `bf33f7f`

## Test
Ask: "Who is Sudas?"
Should get: RV 1.33 - Sudas, RV 7.18 - Sudas (not RV 7.33)

---

## Technical Insight

The lesson: **Tool abstraction loses metadata at system boundaries**.

When you return a string from a tool, then wrap it in a Document, you've lost:
- Original document boundaries
- Ranking/scoring information
- Source metadata
- Semantic relationships

**Solution pattern**: When metadata matters, call the retriever directly instead of wrapping tool results.
