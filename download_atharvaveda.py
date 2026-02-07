#!/usr/bin/env python3
"""
Download all chapters of Atharva-Veda (Saunaka) from TITUS Project.
Source: http://titus.uni-frankfurt.de/texte/etcs/ind/aind/ved/av/avs/

The file naming scheme is:
- avs001.htm through avsNNN.htm where each represents a book:chapter pair
- Book 1 = files 001-99, Book 2 = 100-199, etc.
"""

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import re

BASE_URL = "http://titus.uni-frankfurt.de/texte/etcs/ind/aind/ved/av/avs/"
OUTPUT_DIR = "library/vedic_texts/atharvaveda"

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_text_from_html(html_content):
    """Extract readable Sanskrit text from HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser', from_encoding='utf-8')
    
    # Remove script and style elements
    for script in soup(["script", "style", "meta", "link"]):
        script.decompose()
    
    # Get text
    text = soup.get_text()
    
    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    return text

def download_atharvaveda_complete():
    """
    Download all chapters of Atharva-Veda.
    Based on TITUS documentation, we'll try downloading files in the sequence.
    """
    print("=" * 70)
    print("Downloading Atharva-Veda (Saunaka) from TITUS Project")
    print(f"Output directory: {OUTPUT_DIR}")
    print("=" * 70)
    print()
    
    total_downloaded = 0
    total_failed = 0
    consecutive_failures = 0
    failed_files = []
    
    # Try to download files sequentially until we hit many consecutive failures
    # Based on TITUS, files start from 001 and go up
    
    print("Downloading available chapters (will stop after 20 consecutive failures)...\n")
    
    # Download files sequentially
    print("Downloading available chapters (will stop after 20 consecutive failures)...\n")
    
    file_num = 1
    while consecutive_failures < 20:
        filename = f"avs{file_num:03d}.htm"
        url = urljoin(BASE_URL, filename)
        filename = f"avs{file_num:03d}.htm"
        url = urljoin(BASE_URL, filename)
        
        try:
            print(f"  [{file_num:04d}] Downloading {filename}...", end=" ", flush=True)
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Extract text content
            text_content = extract_text_from_html(response.content)
            
            if text_content.strip() and len(text_content) > 100:  # Only save if meaningful content
                # Save to file
                output_filename = f"avs{file_num:03d}.txt"
                output_path = os.path.join(OUTPUT_DIR, output_filename)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(text_content)
                
                print(f"✓ ({len(text_content)} chars)")
                total_downloaded += 1
                consecutive_failures = 0  # Reset counter on success
            else:
                print(f"✗ (empty content)")
                total_failed += 1
                failed_files.append(filename)
                consecutive_failures += 1
            
            # Respectful delay
            time.sleep(0.3)
            
        except requests.exceptions.RequestException as e:
            print(f"✗ ({str(e)[:30]})")
            total_failed += 1
            failed_files.append(filename)
            consecutive_failures += 1
        except Exception as e:
            print(f"✗ (parse error)")
            total_failed += 1
            failed_files.append(filename)
            consecutive_failures += 1
        
        file_num += 1
    
    print()
    print("=" * 70)
    print(f"Download complete!")
    print(f"Successfully downloaded: {total_downloaded} chapters")
    print(f"Failed: {total_failed}")
    print(f"Output directory: {OUTPUT_DIR}")
    if failed_files and len(failed_files) <= 10:
        print(f"Failed files: {', '.join(failed_files)}")
    print("=" * 70)

if __name__ == "__main__":
    download_atharvaveda_complete()
