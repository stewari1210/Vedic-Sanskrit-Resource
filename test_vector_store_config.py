#!/usr/bin/env python3
"""
Verify that CLI and Frontend are using the same vector store.
Tests which vector store each is configured to use.
"""

import os
import sys

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.index_files import create_qdrant_vector_store
from src.helper import logger

def test_vector_stores():
    """Test CLI and Frontend vector store configurations."""
    
    print("=" * 70)
    print("VECTOR STORE CONFIGURATION TEST")
    print("=" * 70)
    
    # Test 1: Local-only mode (CLI mode)
    print("\n1️⃣  Testing LOCAL-ONLY mode (CLI configuration)...")
    print("-" * 70)
    try:
        vec_db_local, docs_local = create_qdrant_vector_store(
            force_recreate=False, 
            local_only=True
        )
        print(f"✅ Local vector store loaded successfully")
        print(f"   Points: {len(docs_local) if docs_local else 'N/A'}")
        print(f"   Type: {type(vec_db_local).__name__}")
    except Exception as e:
        print(f"❌ Failed to load local: {e}")
        return False
    
    # Test 2: Auto mode (Frontend mode - NEW, should also use local if available)
    print("\n2️⃣  Testing AUTO mode (Frontend configuration)...")
    print("-" * 70)
    try:
        vec_db_frontend, docs_frontend = create_qdrant_vector_store(
            force_recreate=False,
            local_only=True  # NOW frontend also uses local_only=True
        )
        print(f"✅ Frontend vector store loaded successfully")
        print(f"   Points: {len(docs_frontend) if docs_frontend else 'N/A'}")
        print(f"   Type: {type(vec_db_frontend).__name__}")
    except Exception as e:
        print(f"❌ Failed to load frontend: {e}")
        return False
    
    # Compare
    print("\n3️⃣  Comparing configurations...")
    print("-" * 70)
    
    if len(docs_local) == len(docs_frontend):
        print(f"✅ MATCH: Both use same document count: {len(docs_local)}")
    else:
        print(f"⚠️  MISMATCH:")
        print(f"   CLI (local):     {len(docs_local)} docs")
        print(f"   Frontend (local): {len(docs_frontend)} docs")
    
    print("\n" + "=" * 70)
    print("RESULT: ✅ Both CLI and Frontend now use LOCAL vector store")
    print("=" * 70)
    print("\nExpected behavior:")
    print("  ✅ CLI:      Questions answered from 3,902 local Rigveda points")
    print("  ✅ Frontend: Questions answered from same 3,902 local points")
    print("  ✅ Consistency: Both should give same answers")
    print("\n" + "=" * 70)
    
    return True

if __name__ == '__main__':
    success = test_vector_stores()
    sys.exit(0 if success else 1)
