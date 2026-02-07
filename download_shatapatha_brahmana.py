#!/usr/bin/env python3
"""
Download Shatapatha Brahmana from Archive.org
Source: https://archive.org/stream/ShatpathBrahmanISayanacharyaAndShriHariSwami/
"""

import os
import requests
from pathlib import Path

def download_shatapatha_brahmana():
    """Download Shatapatha Brahmana text from Archive.org"""
    
    # Create library directory if it doesn't exist
    library_dir = Path("library/vedic_prose")
    library_dir.mkdir(parents=True, exist_ok=True)
    
    # URL for the DJVU txt file
    url = "https://archive.org/stream/ShatpathBrahmanISayanacharyaAndShriHariSwami/Shatpath%20Brahman%20I%20-%20Sayanacharya%20and%20Shri%20Hari%20Swami_djvu.txt"
    
    output_file = library_dir / "Shatapatha_Brahmana_I.txt"
    
    print(f"🔄 Downloading Shatapatha Brahmana from Archive.org...")
    print(f"📥 URL: {url}")
    
    try:
        # Download with a timeout
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Save to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(response.text)
        
        # Check file size and content
        file_size = output_file.stat().st_size
        with open(output_file, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.count('\n')
        
        print(f"✅ Download successful!")
        print(f"📊 File size: {file_size:,} bytes")
        print(f"📋 Lines: {lines:,}")
        print(f"💾 Saved to: {output_file}")
        
        # Show first 500 characters to verify content
        print(f"\n📖 First 500 characters of content:")
        print("=" * 50)
        print(content[:500])
        print("=" * 50)
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Download failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    download_shatapatha_brahmana()
