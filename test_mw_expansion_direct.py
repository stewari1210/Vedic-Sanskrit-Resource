"""Direct test of _enhance_query_with_mw() method"""
import os
os.chdir('/Users/shivendratewari/github/Vedic-Sanskrit-Tutor')

# Clear Python cache
import sys
if os.path.exists('src/utils/__pycache__'):
    import shutil
    shutil.rmtree('src/utils/__pycache__')

# Import retriever module
from src.utils.agentic_rag import get_shared_retriever

print("=" * 80)
print("TESTING _enhance_query_with_mw() WITH ENGLISH QUERIES")
print("=" * 80)

# Get the shared retriever
retriever = get_shared_retriever()

# Test English queries
test_queries = [
    "Who is Sudas?",
    "Which verses talk about birth of Rama in Ramayana?",
    "सुदास कौन है?",  # Hindi (should expand)
]

for query in test_queries:
    print(f"\n{'='*80}")
    print(f"Testing: '{query}'")
    print(f"{'='*80}")
    
    enhanced, variants, mw_context = retriever._enhance_query_with_mw(query)
    
    print(f"Enhanced query: '{enhanced[:150]}'...")
    print(f"Variants: {len(variants)}")
    print(f"MW Context entries: {len(mw_context)}")
    
    if query == enhanced:
        print("✅ Query NOT expanded (correct for English)")
    else:
        print("❌ Query WAS expanded (incorrect for English or correct for Hindi)")
