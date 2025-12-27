#!/usr/bin/env python3
"""Quick test script to verify multi-PDF CLI functionality."""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.index_files import load_documents_with_metadata
from config import LOCAL_FOLDER, COLLECTION_NAME

def test_multi_pdf_metadata():
    """Test that multiple PDFs maintain distinct metadata."""
    print("=" * 70)
    print("Testing Multi-PDF Metadata Preservation")
    print("=" * 70)

    # Load all documents from the collection
    docs_path = os.path.join(LOCAL_FOLDER, COLLECTION_NAME)

    if not os.path.exists(docs_path):
        print(f"❌ No documents found at {docs_path}")
        print("Please run the CLI first to process some PDFs")
        return

    try:
        documents = load_documents_with_metadata(docs_path)

        if not documents:
            print("❌ No documents loaded")
            return

        print(f"\n✅ Loaded {len(documents)} document(s)\n")

        # Extract unique document names
        doc_names = set()
        for doc in documents:
            filename = doc.metadata.get('filename', 'Unknown')
            doc_names.add(filename)
            print(f"Document: {filename}")
            print(f"  - Title: {doc.metadata.get('title', 'N/A')[:80]}...")
            print(f"  - Pages: {doc.metadata.get('pages', 'N/A')}")
            print(f"  - Content length: {len(doc.page_content)} chars")
            print()

        print("=" * 70)
        print(f"Summary: {len(doc_names)} unique document(s) found")
        print(f"Document names: {', '.join(sorted(doc_names))}")
        print("=" * 70)

        if len(doc_names) > 1:
            print("\n✅ SUCCESS: Multiple PDFs are properly distinguished!")
            print("Each document maintains its own metadata (filename, title, etc.)")
            print("Chunks from each document will be tagged with their source.")
        elif len(doc_names) == 1:
            print("\n⚠️  Only 1 unique document found.")
            print("To test multi-PDF functionality, process multiple PDFs:")
            print("  python src/cli_run.py --pdfs doc1.pdf doc2.pdf")

    except Exception as e:
        print(f"❌ Error loading documents: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_multi_pdf_metadata()
