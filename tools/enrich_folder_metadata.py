#!/usr/bin/env python3
"""
Add or enrich metadata files for documents in a folder. Designed to support
Sanskrit/Devanagari detection and add fields used by our retriever.

Usage:
    python tools/enrich_folder_metadata.py /path/to/folder --apply

If --apply is omitted this will run in dry-run mode and print proposed changes.
"""
import argparse
import json
from pathlib import Path
import re

DEVANAGARI_RANGE = ('\u0900', '\u097F')

# IAST transliteration markers (diacritics and special characters)
IAST_MARKERS = {
    'ā', 'ī', 'ū',      # long vowels
    'ṛ', 'ṝ', 'ḷ',      # vocalic consonants
    'ṅ', 'ñ', 'ṇ',      # nasals
    'ś', 'ṣ',           # sibilants
    'ṃ', 'ḥ',           # anusvara, visarga
    'ṭ', 'ḍ',           # retroflex
    'Ā', 'Ī', 'Ū',      # capital long vowels
    'Ṛ', 'Ṝ', 'Ḷ',      # capital vocalic
    'Ṅ', 'Ñ', 'Ṇ',      # capital nasals
    'Ś', 'Ṣ',           # capital sibilants
}


def contains_devanagari(text: str, sample_len: int = 5000, threshold: float = 0.05) -> bool:
    """
    Detect Devanagari script in text.
    Robust detection: if many Devanagari chars exist anywhere in the text,
    treat as Sanskrit. This avoids HTML headers masking Devanagari content.
    """
    if not text:
        return False
    # Quick sample check first for speed
    s = text[:sample_len]
    sample_count = sum(1 for c in s if DEVANAGARI_RANGE[0] <= c <= DEVANAGARI_RANGE[1])
    if sample_count / max(1, len(s)) > threshold:
        return True
    # Fallback: scan more of the text and accept if there are >=50 Devanagari chars
    total_count = sum(1 for c in text if DEVANAGARI_RANGE[0] <= c <= DEVANAGARI_RANGE[1])
    return total_count >= 50


def contains_iast_transliteration(text: str, threshold: int = 10) -> bool:
    """
    Detect IAST transliteration markers (diacritics).
    Sanskrit texts typically use diacritics like ā, ī, ū, ṛ, ś, ṣ, ṃ, ḥ, etc.
    
    Args:
        text: Text to check
        threshold: Minimum number of IAST markers to consider text as Sanskrit
    
    Returns:
        True if text contains >=threshold IAST diacritics
    """
    if not text:
        return False
    # Count IAST markers in text
    marker_count = sum(1 for c in text if c in IAST_MARKERS)
    return marker_count >= threshold


def guess_source_type(filename: str, content: str) -> str:
    name = filename.lower()
    if 'brahman' in name or 'brahmana' in name or 'brahmana' in content.lower():
        return 'brahmana'
    if 'rigveda' in name or 'rigveda' in content.lower() or 'rig veda' in content.lower():
        return 'veda'
    if 'yajur' in name or 'yajurveda' in content.lower():
        return 'veda'
    if 'ramayan' in name or 'ramayana' in content.lower():
        return 'epic'
    return 'prose'


def enrich_file(file_path: Path, apply: bool = False) -> dict:
    text = file_path.read_text(encoding='utf-8', errors='ignore')
    base = file_path.stem
    metadata_file = file_path.with_name(f"{base}_metadata.json")

    if metadata_file.exists():
        try:
            metadata = json.loads(metadata_file.read_text(encoding='utf-8'))
        except Exception:
            metadata = {}
    else:
        metadata = {}

    # Fill defaults
    title = metadata.get('title') or base.replace('_', ' ').strip()
    filename = metadata.get('filename') or base
    creator = metadata.get('creator') or 'archive.org'
    keywords = metadata.get('keywords') or []

    # Detection: check for both Devanagari and IAST transliteration
    is_deva = contains_devanagari(text)
    is_iast = contains_iast_transliteration(text)
    is_sanskrit = is_deva or is_iast
    guessed_type = guess_source_type(base, text)

    changed = False
    updates = {}

    # Set preprocessing to 'sanskrit' if either Devanagari or IAST detected
    if metadata.get('preprocessing') != 'sanskrit' and is_sanskrit:
        metadata['preprocessing'] = 'sanskrit'
        updates['preprocessing'] = 'sanskrit'
        changed = True

    if 'source' not in metadata:
        metadata['source'] = title
        updates['source'] = title
        changed = True

    if metadata.get('source_type') != guessed_type:
        metadata['source_type'] = guessed_type
        updates['source_type'] = guessed_type
        changed = True

    if 'sanskrit' not in [k.lower() for k in keywords]:
        keywords = list(keywords) + ['sanskrit']
        metadata['keywords'] = keywords
        updates['keywords'] = keywords
        changed = True

    # Always ensure filename/title fields
    if metadata.get('filename') != filename:
        metadata['filename'] = filename
        updates['filename'] = filename
        changed = True
    if metadata.get('title') != title:
        metadata['title'] = title
        updates['title'] = title
        changed = True

    # Add a simple summary if not present
    if 'summary' not in metadata:
        metadata['summary'] = text[:400].strip()
        updates['summary'] = '<first 400 chars>'
        changed = True

    if apply and changed:
        metadata_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'path': str(file_path), 'metadata_file': str(metadata_file), 'changed': changed, 'updates': updates}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder', type=str, help='Folder to scan (recursive)')
    ap.add_argument('--apply', action='store_true', help='Write metadata files to disk')
    args = ap.parse_args()

    p = Path(args.folder)
    if not p.exists():
        print('Folder does not exist:', p)
        return

    candidates = list(p.rglob('*.txt')) + list(p.rglob('*.md'))
    print(f'Found {len(candidates)} files in {p} (recursive)')

    results = []
    for f in candidates:
        res = enrich_file(f, apply=args.apply)
        results.append(res)
        status = 'UPDATED' if res['changed'] else 'skipped'
        print(f"{status}: {f} -> {Path(res['metadata_file']).name} | updates: {list(res['updates'].keys())}")

    total = sum(1 for r in results if r['changed'])
    print('\nTotal files updated:', total)

if __name__ == '__main__':
    main()
