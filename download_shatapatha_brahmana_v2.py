#!/usr/bin/env python3
"""
Download Shatapatha Brahmana from Archive.org using OCR text extraction
"""

import os
import requests
from pathlib import Path
import re
from urllib.parse import quote

def download_shatapatha_brahmana_ocr():
    """
    Download Shatapatha Brahmana from Archive.org using the OCR text file directly
    """
    
    # Create library directory if it doesn't exist
    library_dir = Path("library/vedic_prose")
    library_dir.mkdir(parents=True, exist_ok=True)
    
    # Archive.org identifier for this book
    identifier = "ShatpathBrahmanISayanacharyaAndShriHariSwami"
    
    # Try different file paths
    urls = [
        # Direct OCR text file
        f"https://archive.org/download/{identifier}/{identifier}_djvu.txt",
        # Alternative path
        f"https://archive.org/download/{identifier}/{identifier}_page_numbers.json",
    ]
    
    output_file = library_dir / "Shatapatha_Brahmana_I.txt"
    
    print(f"🔄 Downloading Shatapatha Brahmana from Archive.org...")
    print(f"📦 Identifier: {identifier}")
    
    for url in urls:
        print(f"\n📥 Trying URL: {url}")
        try:
            # Download with a timeout
            response = requests.get(url, timeout=30, allow_redirects=True)
            
            if response.status_code == 200:
                # Check if it's the djvu.txt file
                if "_djvu.txt" in url:
                    # Extract text from the HTML/DJVU response
                    text = response.text
                    
                    # Try to find the actual content between common markers
                    if "<pre" in text:
                        # Extract content from <pre> tags
                        match = re.search(r'<pre[^>]*>(.*?)</pre>', text, re.DOTALL)
                        if match:
                            text = match.group(1)
                    
                    # Remove remaining HTML tags
                    text = re.sub(r'<[^>]+>', '', text)
                    text = re.sub(r'&[a-zA-Z]+;', '', text)
                    
                    # Save to file
                    with open(output_file, "w", encoding="utf-8") as f:
                        f.write(text)
                    
                    # Check file size and content
                    file_size = output_file.stat().st_size
                    lines = text.count('\n')
                    
                    print(f"✅ Download successful!")
                    print(f"📊 File size: {file_size:,} bytes")
                    print(f"📋 Lines: {lines:,}")
                    print(f"💾 Saved to: {output_file}")
                    
                    # Show first 1000 characters to verify content
                    print(f"\n📖 First 1000 characters of content:")
                    print("=" * 70)
                    print(text[:1000])
                    print("=" * 70)
                    
                    return True
        
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Failed: {e}")
            continue
    
    print(f"\n❌ Could not download from provided URLs. Trying alternative method...")
    
    # Try to get the list of files from the item API
    print(f"📋 Fetching file list from Archive.org API...")
    api_url = f"https://archive.org/metadata/{identifier}"
    
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Look for text files
        print(f"\n📁 Available files in this item:")
        text_files = []
        for file_info in data.get('files', []):
            name = file_info.get('name', '')
            size = file_info.get('size', '')
            if '.txt' in name or '.pdf' in name:
                print(f"  - {name} ({size} bytes)")
                if '.txt' in name:
                    text_files.append(name)
        
        if text_files:
            # Use the first text file
            text_file = text_files[0]
            download_url = f"https://archive.org/download/{identifier}/{quote(text_file)}"
            print(f"\n📥 Downloading: {text_file}")
            
            response = requests.get(download_url, timeout=30)
            response.raise_for_status()
            
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(response.text)
            
            file_size = output_file.stat().st_size
            lines = response.text.count('\n')
            
            print(f"✅ Download successful!")
            print(f"📊 File size: {file_size:,} bytes")
            print(f"📋 Lines: {lines:,}")
            print(f"💾 Saved to: {output_file}")
            
            return True
    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return False

if __name__ == "__main__":
    download_shatapatha_brahmana_ocr()
