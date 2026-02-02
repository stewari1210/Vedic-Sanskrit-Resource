#!/usr/bin/env python3
"""
Monier-Williams Dictionary Parser - Creates JSON Concept Store for RAG

This script parses the MW dictionary (mw.txt) to create a structured concept store
that enables:
1. Exact Sanskrit word lookup (Devanagari → IAST → definitions)
2. Semantic expansion (find related terms, meanings)
3. Vedic text grounding (RV/YV/AV references)

Output: monier_williams_concept_store.json
Format: {
    "sarasvatī": {
        "headwords": ["sarasvatI", "sarasvat"],
        "iast": "sarasvatī",
        "devanagari": "सरस्वती",
        "definitions": ["goddess of eloquence", "sacred river"],
        "vedic_refs": ["RV.vii.95.2", "MBh.ix.2188"],
        "record_id": "237579"
    }
}

Usage:
    python3 parse_monier_williams_concept_store.py
"""

import re
import json
from pathlib import Path
from collections import defaultdict
from indic_transliteration import sanscript
from tqdm import tqdm

# Input/output paths
MW_DICT_PATH = Path("local_store/grammar_texts/monier_williams_dictionary/mw.txt")
OUTPUT_JSON = Path("monier_williams_concept_store.json")

# Regex patterns for MW format
ENTRY_START_PATTERN = re.compile(r'<L>(\d+(?:\.\d+)?)<pc>([^<]*)<k1>([^<]+)<k2>([^<]+)<e>(.+)')
SANSKRIT_TAG_PATTERN = re.compile(r'<s>([^<]+)</s>')
REFERENCE_TAG_PATTERN = re.compile(r'<ls>([^<]+)</ls>')
LEX_TAG_PATTERN = re.compile(r'<lex>([^<]+)</lex>')
DEFINITION_CLEANUP = re.compile(r'<[^>]+>')  # Remove all XML tags


def clean_text(text):
    """Remove XML tags and extra whitespace from text."""
    text = DEFINITION_CLEANUP.sub(' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_vedic_references(text):
    """
    Extract Vedic text references from definition text.
    Examples: RV., AV., TS., YV., MBh., etc.
    """
    refs = REFERENCE_TAG_PATTERN.findall(text)
    
    # Also capture bare references like "RV. vii, 95, 2"
    bare_ref_pattern = re.compile(r'\b(RV|AV|YV|TS|VS|ŚBr|PañcavBr|TBr|MBh|R\.|Hariv\.|Pur\.)\s*[ivxlcdm\d\.,\s]*', re.IGNORECASE)
    bare_refs = bare_ref_pattern.findall(text)
    
    all_refs = list(set(refs + bare_refs))
    return [ref.strip() for ref in all_refs if ref.strip()]


def normalize_iast(text):
    """
    Normalize IAST text by removing accents/diacritics and standardizing.
    sa/ras-vat → sarasvat
    """
    # Remove Vedic accent marks (/, -, \\)
    text = re.sub(r'[/\\-]', '', text)
    # Remove any remaining special markers
    text = re.sub(r'[°—]', '', text)
    return text.strip()


def to_devanagari(iast_text):
    """Convert IAST to Devanagari using sanscript."""
    try:
        normalized = normalize_iast(iast_text)
        devanagari = sanscript.transliterate(normalized, sanscript.IAST, sanscript.DEVANAGARI)
        return devanagari
    except Exception as e:
        print(f"Warning: Could not convert '{iast_text}' to Devanagari: {e}")
        return ""


def extract_definitions(entry_text):
    """
    Extract clean definitions from entry text.
    Returns list of definition strings.
    """
    definitions = []
    
    # Split by '¦' (definition separator in MW)
    parts = entry_text.split('¦')
    
    for part in parts:
        # Remove reference tags first
        part_no_refs = REFERENCE_TAG_PATTERN.sub('', part)
        
        # Clean up XML tags
        cleaned = clean_text(part_no_refs)
        
        # Skip empty or very short definitions
        if len(cleaned) > 5 and not cleaned.startswith('<'):
            # Truncate very long definitions
            if len(cleaned) > 300:
                cleaned = cleaned[:297] + "..."
            definitions.append(cleaned)
    
    return definitions[:5]  # Limit to first 5 definitions per entry


def parse_mw_dictionary():
    """
    Main parser: reads mw.txt line by line and extracts concept store entries.
    """
    concept_store = {}
    current_entry = None
    entry_buffer = []
    entries_processed = 0
    
    print(f"📖 Parsing Monier-Williams dictionary: {MW_DICT_PATH}")
    print(f"   File size: {MW_DICT_PATH.stat().st_size / 1024 / 1024:.1f} MB")
    
    with open(MW_DICT_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"   Total lines: {len(lines):,}")
    print("   Extracting entries...")
    
    for line in tqdm(lines, desc="Parsing MW", unit="lines"):
        line = line.strip()
        
        # Check if this is a new entry
        entry_match = ENTRY_START_PATTERN.match(line)
        
        if entry_match:
            # Process previous entry if exists
            if current_entry and entry_buffer:
                process_entry(current_entry, entry_buffer, concept_store)
                entries_processed += 1
            
            # Start new entry
            record_id, page_col, k1, k2, entry_type = entry_match.groups()
            current_entry = {
                'record_id': record_id,
                'page_col': page_col,
                'k1': k1,
                'k2': k2,
                'entry_type': entry_type
            }
            entry_buffer = [line]
        
        elif current_entry:
            # Continue building current entry
            entry_buffer.append(line)
            
            # Check for end marker
            if '<LEND>' in line:
                process_entry(current_entry, entry_buffer, concept_store)
                entries_processed += 1
                current_entry = None
                entry_buffer = []
    
    # Process final entry
    if current_entry and entry_buffer:
        process_entry(current_entry, entry_buffer, concept_store)
        entries_processed += 1
    
    print(f"\n✅ Processed {entries_processed:,} entries")
    print(f"✅ Created {len(concept_store):,} unique concept store entries")
    
    return concept_store


def process_entry(entry_meta, entry_lines, concept_store):
    """
    Process a single MW dictionary entry and add to concept store.
    Handles multiple variants and merges them under normalized headword.
    """
    entry_text = ' '.join(entry_lines)
    
    # Extract headwords
    k1 = entry_meta['k1']
    k2 = entry_meta['k2']
    
    # Normalize headwords
    k1_normalized = normalize_iast(k1)
    k2_normalized = normalize_iast(k2)
    
    # Use k1_normalized as primary key
    primary_key = k1_normalized.lower()
    
    # Skip if too short (likely abbreviations)
    if len(primary_key) < 2:
        return
    
    # Extract Sanskrit terms from <s> tags
    sanskrit_terms = SANSKRIT_TAG_PATTERN.findall(entry_text)
    
    # Extract definitions
    definitions = extract_definitions(entry_text)
    
    # Extract Vedic references
    vedic_refs = extract_vedic_references(entry_text)
    
    # Skip entries with no meaningful content
    if not definitions and not sanskrit_terms:
        return
    
    # Convert to Devanagari
    devanagari = to_devanagari(k1_normalized)
    
    # Create or update concept store entry
    if primary_key not in concept_store:
        concept_store[primary_key] = {
            'headwords': [],
            'iast_variants': [],
            'devanagari': devanagari,
            'definitions': [],
            'vedic_refs': [],
            'record_ids': []
        }
    
    # Merge data
    entry_data = concept_store[primary_key]
    
    # Add unique headwords
    for hw in [k1, k2, k1_normalized, k2_normalized]:
        if hw and hw not in entry_data['headwords']:
            entry_data['headwords'].append(hw)
    
    # Add Sanskrit IAST variants
    for term in sanskrit_terms:
        normalized_term = normalize_iast(term)
        if normalized_term and normalized_term not in entry_data['iast_variants']:
            entry_data['iast_variants'].append(normalized_term)
    
    # Add definitions (avoid duplicates)
    for defn in definitions:
        if defn not in entry_data['definitions']:
            entry_data['definitions'].append(defn)
    
    # Add Vedic references (avoid duplicates)
    for ref in vedic_refs:
        if ref not in entry_data['vedic_refs']:
            entry_data['vedic_refs'].append(ref)
    
    # Add record ID
    if entry_meta['record_id'] not in entry_data['record_ids']:
        entry_data['record_ids'].append(entry_meta['record_id'])


def create_lookup_index(concept_store):
    """
    Create reverse index for fast lookup:
    - Devanagari → primary_key
    - IAST variants → primary_key
    """
    lookup_index = {}
    
    for primary_key, entry_data in concept_store.items():
        # Add primary key
        lookup_index[primary_key] = primary_key
        
        # Add Devanagari variant
        if entry_data['devanagari']:
            lookup_index[entry_data['devanagari']] = primary_key
        
        # Add all headword variants
        for hw in entry_data['headwords']:
            hw_lower = hw.lower()
            if hw_lower not in lookup_index:
                lookup_index[hw_lower] = primary_key
        
        # Add IAST variants
        for variant in entry_data['iast_variants']:
            variant_lower = variant.lower()
            if variant_lower not in lookup_index:
                lookup_index[variant_lower] = primary_key
    
    return lookup_index


def save_concept_store(concept_store, output_path):
    """Save concept store and lookup index to JSON."""
    # Create lookup index
    lookup_index = create_lookup_index(concept_store)
    
    # Prepare output
    output_data = {
        'metadata': {
            'source': 'Monier-Williams Sanskrit-English Dictionary',
            'version': 'mw.txt (Cologne Digital Sanskrit Lexicon)',
            'total_entries': len(concept_store),
            'total_lookup_keys': len(lookup_index),
            'created': '2026-02-01'
        },
        'concept_store': concept_store,
        'lookup_index': lookup_index
    }
    
    print(f"\n💾 Saving concept store to: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    file_size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"✅ Saved {len(concept_store):,} entries ({file_size_mb:.1f} MB)")
    print(f"✅ Lookup index: {len(lookup_index):,} keys")


def test_concept_store(concept_store_path):
    """Test the concept store with sample queries."""
    print("\n🧪 Testing concept store...")
    
    with open(concept_store_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    concept_store = data['concept_store']
    lookup_index = data['lookup_index']
    
    # Test cases
    test_queries = [
        'sarasvatī',
        'सरस्वती',
        'agni',
        'अग्नि',
        'veda',
        'ṛgveda'
    ]
    
    print("\nTest Queries:")
    for query in test_queries:
        if query in lookup_index:
            primary_key = lookup_index[query]
            entry = concept_store[primary_key]
            print(f"\n✅ '{query}' → '{primary_key}'")
            print(f"   Devanagari: {entry['devanagari']}")
            print(f"   Definitions: {entry['definitions'][:2]}")
            print(f"   Vedic refs: {entry['vedic_refs'][:3]}")
        else:
            print(f"\n❌ '{query}' not found")


def main():
    """Main execution."""
    print("=" * 70)
    print("Monier-Williams Dictionary → JSON Concept Store Parser")
    print("=" * 70)
    
    # Check input file exists
    if not MW_DICT_PATH.exists():
        print(f"❌ Error: MW dictionary not found at {MW_DICT_PATH}")
        print("   Please ensure the file exists.")
        return
    
    # Parse dictionary
    concept_store = parse_mw_dictionary()
    
    # Save to JSON
    save_concept_store(concept_store, OUTPUT_JSON)
    
    # Test
    test_concept_store(OUTPUT_JSON)
    
    print("\n" + "=" * 70)
    print("✅ Concept store creation complete!")
    print(f"📄 Output: {OUTPUT_JSON}")
    print("\nNext steps:")
    print("1. Integrate with src/utils/retriever.py")
    print("2. Add MW lookup before vector search")
    print("3. Test with bilingual queries")
    print("=" * 70)


if __name__ == '__main__':
    main()
