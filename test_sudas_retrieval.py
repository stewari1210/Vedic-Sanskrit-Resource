#!/usr/bin/env python3
"""Isolation test: does the retriever (not the app) find Sudas / RV 7.18?

Run on Mac:  python test_sudas_retrieval.py
"""
import re
import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
load_dotenv(PROJECT_ROOT / ".env", override=True)

# 1. Can the rescue module even be imported the way retriever.py imports it?
try:
    from src.utils.devanagari_lexical import devanagari_lexical_hits, query_terms
    print("✅ devanagari_lexical imports OK")
    print(f"   query_terms('Who is Sudas?') = {query_terms('Who is Sudas?')}")
except Exception as e:
    print(f"❌ devanagari_lexical import FAILED: {e}")

# 2. Build retriever exactly like the app does
from src.utils.index_files import create_qdrant_vector_store
from src.utils.retriever import create_retriever

vec_db, docs = create_qdrant_vector_store(force_recreate=False)
print(f"\n📦 docs for BM25: {len(docs) if docs else 0} chunks")
if docs:
    joined = " ".join(d.page_content for d in docs)
    print(f"   सुदास in BM25 docs: {joined.count('सुदास')}")

retriever = create_retriever(vec_db, docs)
print(f"🔧 retriever type: {type(retriever).__name__}")  # HybridRetriever or fallback?

# 3. Run the query and inspect what comes back
print("\n" + "=" * 70)
results = retriever.invoke("Who is Sudas?")
print(f"\n📄 {len(results)} docs returned. Verse IDs + सुदास counts per doc:")
for i, d in enumerate(results[:10]):
    ids = re.findall(r"॥ (\d+\.\d+\.\d+) ॥", d.page_content)[:3]
    n = d.page_content.count("सुदास") + d.page_content.count("सुदाः")
    print(f"  {i+1}. verses={ids or '?'}  sudas_hits={n}  "
          f"file={d.metadata.get('filename', '?')}")

hit = any(d.page_content.count("सुदास") > 0 for d in results)
print("\n" + ("✅ SUCCESS: Sudas chunks retrieved" if hit
              else "❌ FAIL: no Sudas chunks in results"))
