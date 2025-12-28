#!/usr/bin/env python3
"""
Clean up proper_noun_variants.json to keep only Griffith translations
Removes Sharma-specific data while preserving all variant mappings
"""
import json

def cleanup_for_griffith(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Update metadata
    data['_comment'] = "Proper noun variant mappings for Griffith translations - LITERAL TRANSLATION FOCUS"
    data['_sources'] = "Griffith's Rigveda + Griffith's Yajurveda (literal translations)"
    data['_total_translations'] = 2
    data['_philosophy'] = "Griffith provides literal, scholarly translations preserving original Sanskrit terminology and historical context"

    # Remove total_occurrences if it exists
    if '_total_occurrences' in data:
        del data['_total_occurrences']

    # Process each section
    for section_key in data:
        if section_key.startswith('_'):
            continue  # Skip metadata

        section = data[section_key]
        if not isinstance(section, dict):
            continue

        for name, entry in section.items():
            if not isinstance(entry, dict):
                continue

            # Update sources to keep only Griffith
            if 'sources' in entry:
                old_sources = entry['sources']

                # Skip if sources is not a dict
                if not isinstance(old_sources, dict):
                    continue

                new_sources = {}

                # Keep only Griffith sources
                if 'Griffith-Rigveda' in old_sources:
                    new_sources['Griffith-Rigveda'] = old_sources['Griffith-Rigveda']
                if 'Griffith-Yajurveda' in old_sources:
                    new_sources['Griffith-Yajurveda'] = old_sources['Griffith-Yajurveda']

                # Update total occurrences
                total = sum(new_sources.values())
                entry['sources'] = new_sources
                entry['total_occurrences'] = total

                # Update priority based on new total
                if total >= 50:
                    entry['priority'] = 'CRITICAL'
                elif total >= 20:
                    entry['priority'] = 'HIGH'
                elif total >= 5:
                    entry['priority'] = 'MEDIUM'
                else:
                    entry['priority'] = 'LOW'            # Remove Sharma-specific pattern notes
            if 'pattern' in entry:
                pattern = entry['pattern']
                if 'Sharma' in pattern:
                    # Keep only Griffith-relevant info or remove entirely
                    if 'Griffith' in pattern and not pattern.startswith('Sharma'):
                        # Extract Griffith part if it's meaningful
                        parts = pattern.split(',')
                        griffith_parts = [p.strip() for p in parts if 'Griffith' in p]
                        if griffith_parts:
                            entry['pattern'] = griffith_parts[0]
                        else:
                            del entry['pattern']
                    else:
                        del entry['pattern']

            # Update note to reflect Griffith-only context
            if 'note' in entry:
                note = entry['note']
                if 'Sharma' in note:
                    # Keep CRITICAL notes, remove Sharma references
                    if note.startswith('CRITICAL'):
                        entry['note'] = note.replace('Sharma', 'translation').replace('Sharma-R', 'Rigveda')
                    elif 'appears only in' in note:
                        del entry['note']
                    else:
                        del entry['note']

    # Write cleaned data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Cleaned proper_noun_variants.json for Griffith-only")
    print(f"   Removed Sharma-specific data")
    print(f"   Preserved all variant mappings")
    print(f"   Updated priorities based on Griffith occurrence counts")

if __name__ == '__main__':
    cleanup_for_griffith('proper_noun_variants.json', 'proper_noun_variants_griffith.json')
    print("\n📝 Review the output file, then:")
    print("   mv proper_noun_variants_griffith.json proper_noun_variants.json")
