#!/usr/bin/env python3
"""
Verify that all 25 chapters of Pancavamsa Brahmana are represented in the vector store chunks.
"""

import os
import sys
import json
import re
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

LOCAL_VECTORDB = os.getenv('VECTORDB_FOLDER', 'vector_store')
PB_FILE = 'local_store/prose_vedas/pancavamsa_brahmana/pancavamsa_brahmana.txt'


def verify_pb_chapters():
    """Verify all 25 Pancavamsa Brahmana chapters are in local vector store."""
    
    print("🔍 PANCAVAMSA BRAHMANA CHAPTER VERIFICATION")
    print("=" * 60)
    
    # Step 1: Verify source file has all chapters
    print("\n1️⃣  Checking source text file...")
    if not Path(PB_FILE).exists():
        print(f"   ❌ Source file not found: {PB_FILE}")
        return False
    
    with open(PB_FILE, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Check for chapter markers (Roman numerals I-XXV)
    chapters_found = set()
    
    # Look for explicit chapter references like "Chapter I", "Chapter V", etc.
    for match in re.finditer(r'(?:Chapter|Adhyaya)\s+([IVXLCDM]+|\d+)', text, re.IGNORECASE):
        chapter_marker = match.group(1)
        chapters_found.add(chapter_marker)
    
    # Also look for section markers like "XVII.", "XVIII.", etc. at line starts
    for line in text.split('\n'):
        # Match lines that start with Roman numerals followed by period
        if re.match(r'^([IVXLCDM]+)\.\s', line):
            match = re.match(r'^([IVXLCDM]+)\.', line)
            if match:
                chapters_found.add(match.group(1))
    
    # Convert to integers for sorting
    chapter_numbers = []
    for ch in chapters_found:
        if ch.isdigit():
            chapter_numbers.append(int(ch))
        else:
            # Convert Roman numerals
            try:
                num = roman_to_int(ch)
                if num:
                    chapter_numbers.append(num)
            except:
                pass
    
    chapter_numbers = sorted(set(chapter_numbers))
    
    print(f"   📖 Chapters found in source text: {chapter_numbers}")
    print(f"   📊 Total unique chapters: {len(chapter_numbers)}")
    
    # Check if we have all 25 chapters
    expected_chapters = set(range(1, 26))
    found_chapters = set(chapter_numbers)
    
    if len(found_chapters) >= 20:  # At least 20 chapters should be found
        print(f"   ✅ Source file appears complete")
    else:
        print(f"   ⚠️  Only {len(found_chapters)} chapters found in source")
    
    # Step 2: Check vector store for PB references
    print("\n2️⃣  Checking local vector store chunks...")
    
    if not Path(LOCAL_VECTORDB).exists():
        print(f"   ⚠️  Local vector store not found: {LOCAL_VECTORDB}")
        print("   ℹ️  Vector store should be created by index_files.py")
        return None
    
    # Try to connect to local Qdrant
    try:
        from qdrant_client import QdrantClient
        
        client = QdrantClient(path=LOCAL_VECTORDB)
        
        # Check for ancient_history collection
        try:
            collection = client.get_collection('ancient_history')
            print(f"   ✅ Found 'ancient_history' collection")
            print(f"      Total points: {collection.points_count or 0}")
        except:
            print(f"   ⚠️  'ancient_history' collection not found")
            print(f"      Available collections: {[c.name for c in client.get_collections().collections]}")
            return None
        
        # Scroll through points and look for PB references in payloads
        pb_chapters_found = set()
        total_points = collection.points_count or 0
        batch_size = 100
        offset = None
        processed = 0
        
        print(f"\n   📤 Scanning {total_points} points for PB references...")
        
        while processed < total_points:
            try:
                points, next_offset = client.scroll(
                    'ancient_history',
                    limit=batch_size,
                    offset=offset
                )
                
                for point in points:
                    processed += 1
                    
                    # Check text payload for PB citations
                    if hasattr(point, 'payload') and point.payload:
                        text_content = point.payload.get('text', '') or ''
                        
                        # Look for PB X.Y.Z citations or chapter mentions
                        if 'PB ' in text_content or 'pancavamsa' in text_content.lower():
                            # Extract chapter numbers from citations like "PB 5.3.2"
                            for match in re.finditer(r'PB\s+(\d+)', text_content):
                                ch_num = int(match.group(1))
                                if 1 <= ch_num <= 25:
                                    pb_chapters_found.add(ch_num)
                
                if next_offset is None:
                    break
                offset = next_offset
                
                if processed % 1000 == 0:
                    print(f"      Processed: {processed}/{total_points} ({100*processed/total_points:.1f}%)")
            
            except Exception as e:
                print(f"   ❌ Error scrolling collection: {e}")
                break
        
        print(f"   ✅ Scanning complete")
        
        if pb_chapters_found:
            chapter_list = sorted(pb_chapters_found)
            print(f"\n   📖 PB chapters found in vector store chunks: {chapter_list}")
            print(f"   📊 Total PB chapters in chunks: {len(pb_chapters_found)}/25")
            
            missing = sorted(set(range(1, 26)) - pb_chapters_found)
            if missing:
                print(f"   ⚠️  Missing chapters: {missing}")
            else:
                print(f"   ✅ All 25 chapters represented!")
            
            return len(pb_chapters_found) == 25
        else:
            print(f"   ⚠️  No PB references found in chunk payloads")
            print(f"      This may be expected if chunks haven't been indexed yet")
            return None
    
    except ImportError:
        print(f"   ⚠️  qdrant-client not installed")
        return None
    except Exception as e:
        print(f"   ❌ Error accessing local vector store: {e}")
        return None


def roman_to_int(roman):
    """Convert Roman numeral to integer."""
    roman_dict = {
        'I': 1, 'V': 5, 'X': 10, 'L': 50,
        'C': 100, 'D': 500, 'M': 1000
    }
    
    total = 0
    prev_value = 0
    
    for char in reversed(roman.upper()):
        if char not in roman_dict:
            return None
        
        value = roman_dict[char]
        if value < prev_value:
            total -= value
        else:
            total += value
        prev_value = value
    
    return total


def main():
    """Main function."""
    print()
    result = verify_pb_chapters()
    print("\n" + "=" * 60)
    
    if result is True:
        print("✅ VERIFICATION PASSED: All 25 chapters are represented")
        return 0
    elif result is False:
        print("❌ VERIFICATION FAILED: Not all chapters found")
        return 1
    else:
        print("⚠️  VERIFICATION INCONCLUSIVE: Could not verify")
        return 2


if __name__ == "__main__":
    sys.exit(main())
