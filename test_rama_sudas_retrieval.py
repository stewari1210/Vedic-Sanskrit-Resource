#!/usr/bin/env python3
"""
Quick test to verify Rama, Sudas, and Divodasa retrieval works.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from utils.agentic_rag import run_agentic_rag

print("🧪 TESTING RAG RETRIEVAL FOR RAMA, SUDAS, DIVODASA")
print("=" * 80)

queries = [
    "Which verses talk about birth of Rama in Ramayana?",
    "Who is Sudas?",
    "Who is Divodasa?"
]

for query in queries:
    print(f"\n📝 Query: {query}")
    print("-" * 80)
    
    try:
        result = run_agentic_rag(query)
        
        answer = result.get('answer', 'No answer')
        citations = result.get('citations', [])
        
        print(f"✅ Answer: {answer[:300]}...")
        if citations:
            print(f"📚 Citations: {citations[:3]}")
        else:
            print("⚠️  No citations")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print()

print("=" * 80)
print("✅ Test complete!")
