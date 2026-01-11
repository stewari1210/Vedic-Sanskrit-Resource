#!/usr/bin/env python3
"""Quick test script for gTTS with Sanskrit text."""

import tempfile
from pathlib import Path

try:
    from gtts import gTTS
    print("✓ gTTS imported successfully")
except ImportError:
    print("✗ gTTS not found. Install with: pip install gtts")
    exit(1)

# Test texts
test_texts = [
    ("अग्नि", "Single word"),
    ("अग्निमीळे पुरोहितं यज्ञस्य देवमृत्विजम्", "Full verse (RV 1.1.1)"),
    ("नमस्ते", "Common greeting"),
]

print("\n" + "="*60)
print("Testing gTTS with Sanskrit texts")
print("="*60)

for text, description in test_texts:
    print(f"\n📝 Testing: {description}")
    print(f"   Text: {text}")

    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3', mode='wb') as fp:
            audio_path = fp.name

        print(f"   Creating audio file: {audio_path}")

        # Generate speech
        tts = gTTS(text=text, lang='hi', slow=True)
        tts.save(audio_path)

        # Check file
        if Path(audio_path).exists():
            size = Path(audio_path).stat().st_size
            print(f"   ✓ Success! File size: {size} bytes")

            if size == 0:
                print(f"   ✗ Warning: File is empty!")

            # Clean up
            Path(audio_path).unlink()
        else:
            print(f"   ✗ Error: File was not created")

    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")

print("\n" + "="*60)
print("Test complete!")
print("="*60)
