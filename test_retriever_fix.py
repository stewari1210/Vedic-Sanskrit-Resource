#!/usr/bin/env python3
"""Test the retriever fix for proper noun source handling."""

import os
import sys
import shutil

# Add project root to path
from pathlib import Path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.index_files import create_qdrant_vector_store
from src.utils.retriever import create_retriever

def test_retriever():
    """Test the retriever with a query."""
    print("=" * 60)
    print("Testing Retriever Fix for Proper Noun Sources")
    print("=" * 60)
    
    # Clean up old vector stores
    print("\n1️⃣  Cleaning up old vector stores...")
    for path in ['vector_store', 'local_store']:
        if os.path.exists(path):
            shutil.rmtree(path)
            print(f"   ✓ Removed {path}")
    
    # Find and list available test files
    test_files_dir = project_root / 'library' / 'vedic_texts'
    if test_files_dir.exists():
        test_files = list(test_files_dir.glob('*.pdf')) + list(test_files_dir.glob('*.txt'))
        if test_files:
            print(f"\n2️⃣  Found {len(test_files)} test files")
            test_file = str(test_files[0])
            print(f"   Using: {test_file}")
        else:
            print("\n❌ No PDF or TXT files found in library/vedic_texts/")
            return False
    else:
        print(f"\n❌ Directory not found: {test_files_dir}")
        return False
    
    # Process the file
    print("\n3️⃣  Processing file and creating vector store...")
    try:
        from src.utils.process_files import process_uploaded_pdfs
        from src.config import LOCAL_FOLDER, COLLECTION_NAME
        
        # Copy file to local store
        local_dir = Path(LOCAL_FOLDER) / COLLECTION_NAME
        local_dir.mkdir(parents=True, exist_ok=True)
        dest_file = local_dir / Path(test_file).name
        shutil.copy(test_file, dest_file)
        print(f"   ✓ Copied file to {dest_file}")
        
        # Process the file
        print("   Processing PDF/TXT...")
        docs = process_uploaded_pdfs()
        print(f"   ✓ Processed {len(docs)} documents")
        
        # Create vector store
        print("\n4️⃣  Creating vector store...")
        vec_db, docs_from_store = create_qdrant_vector_store(force_recreate=True, local_only=True)
        print(f"   ✓ Created vector store with {len(docs_from_store)} documents")
        
        # Create retriever
        print("\n5️⃣  Creating retriever...")
        retriever = create_retriever(vec_db, docs_from_store)
        print("   ✓ Retriever created successfully")
        
        # Test a query
        print("\n6️⃣  Testing query retrieval...")
        query = "Who is Agni?"
        print(f"   Query: '{query}'")
        try:
            results = retriever.invoke(query)
            print(f"   ✓ Retrieved {len(results)} documents successfully!")
            
            if results:
                print(f"\n   Top result:")
                print(f"   - Title: {results[0].metadata.get('title', 'N/A')[:60]}")
                print(f"   - Content: {results[0].page_content[:100]}...")
            
            print("\n✅ TEST PASSED: Retriever is working correctly!")
            return True
            
        except AttributeError as e:
            if "'list' object has no attribute 'values'" in str(e):
                print(f"   ❌ TEST FAILED: The sources list bug is still present!")
                print(f"   Error: {e}")
                return False
            else:
                raise
        except Exception as e:
            print(f"   ❌ TEST FAILED with error: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_retriever()
    sys.exit(0 if success else 1)
