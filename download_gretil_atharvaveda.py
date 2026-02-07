#!/usr/bin/env python3
"""
Download Atharva-Veda (IAST transliteration) from GRETIL project.
Source: http://gretil.sub.uni-goettingen.de/gretil/1_sanskr/1_veda/1_sam/avs___u.htm

The GRETIL version provides IAST transliteration with diacritics:
- ā, ī, ū (long vowels)
- ṛ, ṝ (vocalic r)
- ṅ, ñ, ṇ (nasals)
- ś, ṣ (sibilants)
- ṃ (anusvara), ḥ (visarga)

This is excellent for NLP processing and semantic embeddings.
"""

import os
import requests
from bs4 import BeautifulSoup
import re
import time

BASE_URL = "http://gretil.sub.uni-goettingen.de/gretil/1_sanskr/1_veda/1_sam/avs___u.htm"
OUTPUT_DIR = "library/vedic_texts/atharvaveda_gretil"

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_hymns_from_html(html_content):
    """
    Extract hymns from GRETIL HTML.
    Format is: (AVŚ_BOOK,HYMN.VERSE[HALF]a) text ... text ... ||VERSE||
    """
    # Remove HTML tags but preserve content
    soup = BeautifulSoup(html_content, 'html.parser')
    text = soup.get_text()
    
    # Find all hymn references and extract content
    # Pattern: (AVŚ_X,Y.Za) ... || or ||N||
    hymns = {}
    
    # Split by hymn markers
    pattern = r'\(AVŚ_(\d+),(\d+)\.(\d+)[a-z]?\)'
    
    # Find all matches to identify hymn boundaries
    for match in re.finditer(pattern, text):
        book = int(match.group(1))
        hymn = int(match.group(2))
        verse = int(match.group(3))
        
        key = (book, hymn)
        if key not in hymns:
            hymns[key] = {
                'book': book,
                'hymn': hymn,
                'verses': [],
                'raw_text': ''
            }
    
    # Extract full hymn text
    hymn_blocks = re.split(r'\|\|(\d+)\|\|', text)
    
    current_hymn = None
    for i, block in enumerate(hymn_blocks):
        # Look for hymn identifiers at start of block
        matches = re.findall(r'\(AVŚ_(\d+),(\d+)\.', block)
        if matches:
            book, hymn = int(matches[0][0]), int(matches[0][1])
            current_hymn = (book, hymn)
            if current_hymn in hymns:
                # Extract clean text by removing markup
                clean_text = re.sub(r'\(AVŚ_[^)]+\)', '', block)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                hymns[current_hymn]['raw_text'] = clean_text
    
    return hymns

def download_and_process():
    """Download and process the Atharvaveda GRETIL file."""
    print("=" * 70)
    print("Downloading Atharva-Veda (IAST Transliteration) from GRETIL")
    print(f"Source: {BASE_URL}")
    print(f"Output directory: {OUTPUT_DIR}")
    print("=" * 70)
    print()
    
    try:
        print("Fetching GRETIL Atharvaveda...", end=" ", flush=True)
        response = requests.get(BASE_URL, timeout=30)
        response.raise_for_status()
        print("✓")
        print(f"Downloaded {len(response.content)} bytes\n")
        
        # Extract hymns
        print("Parsing hymn structure...", end=" ", flush=True)
        hymns = extract_hymns_from_html(response.content)
        print(f"✓ Found {len(hymns)} hymns\n")
        
        # Save complete file
        print("Saving complete Atharvaveda...", end=" ", flush=True)
        output_file = os.path.join(OUTPUT_DIR, "atharvaveda_complete.txt")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
        file_size = os.path.getsize(output_file)
        print(f"✓ ({file_size} bytes)")
        
        # Save individual hymns
        print("\nSaving individual hymns:")
        saved_count = 0
        for (book, hymn), hymn_data in sorted(hymns.items()):
            if hymn_data['raw_text']:
                book_dir = os.path.join(OUTPUT_DIR, f"Book_{book:02d}")
                os.makedirs(book_dir, exist_ok=True)
                
                filename = f"Book_{book:02d}_Hymn_{hymn:03d}.txt"
                filepath = os.path.join(book_dir, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"[AVŚ_{book},{hymn}]\n\n")
                    f.write(hymn_data['raw_text'])
                
                if saved_count % 20 == 0:
                    print(f"  Saved {saved_count} hymns...", end=" ", flush=True)
                saved_count += 1
        
        print(f"\n  ✓ Total: {saved_count} hymn files saved\n")
        
        print("=" * 70)
        print("Download and processing complete!")
        print(f"Total files created: {saved_count + 1} (1 complete + {saved_count} individual)")
        print(f"Output: {OUTPUT_DIR}")
        print()
        print("IAST Markers present in this text:")
        print("  - Vowels: ā, ī, ū, ṛ, ṝ, ḷ (long/vocalic forms)")
        print("  - Nasals: ṅ, ñ, ṇ")
        print("  - Sibilants: ś, ṣ")
        print("  - Specials: ṃ (anusvara), ḥ (visarga)")
        print("=" * 70)
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    download_and_process()
