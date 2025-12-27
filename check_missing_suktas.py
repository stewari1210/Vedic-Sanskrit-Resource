#!/usr/bin/env python3
"""
Check which Suktas were filtered out during parsing.

Rigveda has 1028 hymns total across 10 Mandalas:
- Mandala 1: 191 hymns
- Mandala 2: 43 hymns
- Mandala 3: 62 hymns
- Mandala 4: 58 hymns
- Mandala 5: 87 hymns
- Mandala 6: 75 hymns
- Mandala 7: 104 hymns
- Mandala 8: 103 hymns
- Mandala 9: 114 hymns
- Mandala 10: 191 hymns
Total: 1028 hymns
"""

import re
from pathlib import Path
from collections import defaultdict


# Expected Sukta counts per Mandala (Rigveda standard)
EXPECTED_SUKTAS = {
    1: 191,
    2: 43,
    3: 62,
    4: 58,
    5: 87,
    6: 75,
    7: 104,
    8: 103,
    9: 114,
    10: 191
}


def extract_suktas_from_file(file_path):
    """Extract all Mandala/Sukta references from file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all "Mandala X/Sukta Y" patterns
    matches = re.findall(r'Mandala (\d+)/Sukta (\d+)', content)

    # Store as set of (mandala, sukta) tuples
    suktas = set()
    for mandala, sukta in matches:
        suktas.add((int(mandala), int(sukta)))

    return suktas


def compare_versions(original_suktas, parsed_suktas):
    """Compare original vs parsed to find missing Suktas."""
    missing = defaultdict(list)

    for mandala in range(1, 11):
        expected_count = EXPECTED_SUKTAS[mandala]

        # Find all expected Suktas for this Mandala
        expected = set(range(1, expected_count + 1))

        # Find which ones we have in original
        original_for_mandala = {s for m, s in original_suktas if m == mandala}

        # Find which ones we have in parsed
        parsed_for_mandala = {s for m, s in parsed_suktas if m == mandala}

        # Which ones are missing from parsed?
        missing_from_parsed = original_for_mandala - parsed_for_mandala

        if missing_from_parsed:
            missing[mandala] = sorted(missing_from_parsed)

    return missing


def check_sudas_in_suktas(original_file, parsed_file, missing_suktas):
    """Check if Sudas appears in the missing Suktas."""
    print("\n" + "="*70)
    print("🔍 CHECKING FOR SUDAS IN MISSING SUKTAS")
    print("="*70)

    with open(original_file, 'r', encoding='utf-8') as f:
        original_content = f.read()

    sudas_suktas = []

    for mandala, sukta_list in missing_suktas.items():
        for sukta in sukta_list:
            # Find the content for this Sukta in original
            pattern = rf'Mandala {mandala}/Sukta {sukta}\b(.*?)(?=Mandala \d+/Sukta \d+|\Z)'
            match = re.search(pattern, original_content, re.DOTALL)

            if match:
                sukta_content = match.group(1)
                if 'Sudas' in sukta_content or 'Sudasa' in sukta_content:
                    sudas_suktas.append((mandala, sukta))
                    print(f"\n⚠️  Mandala {mandala}/Sukta {sukta} contains Sudas/Sudasa!")

                    # Show snippet
                    lines = sukta_content.split('\n')
                    for i, line in enumerate(lines[:30]):  # First 30 lines
                        if 'Sudas' in line or 'Sudasa' in line:
                            print(f"  Line {i+1}: {line.strip()[:100]}")

    if not sudas_suktas:
        print("\n✅ None of the missing Suktas contain Sudas/Sudasa")

    return sudas_suktas


def main():
    print("="*70)
    print("SUKTA COMPLETENESS CHECK")
    print("="*70)
    print()

    original_file = Path('rigveda-sharma.txt')
    parsed_file = Path('rigveda-sharma_english.txt')

    if not original_file.exists():
        print(f"❌ Original file not found: {original_file}")
        return 1

    if not parsed_file.exists():
        print(f"❌ Parsed file not found: {parsed_file}")
        return 1

    # Extract Suktas from both files
    print("📖 Extracting Suktas from original file...")
    original_suktas = extract_suktas_from_file(original_file)
    print(f"  Found: {len(original_suktas)} unique Suktas")

    print("\n📖 Extracting Suktas from parsed English file...")
    parsed_suktas = extract_suktas_from_file(parsed_file)
    print(f"  Found: {len(parsed_suktas)} unique Suktas")

    # Compare
    print("\n" + "="*70)
    print("📊 COMPARISON BY MANDALA")
    print("="*70)

    total_original = 0
    total_parsed = 0
    total_missing = 0

    missing_suktas = {}

    for mandala in range(1, 11):
        original_for_mandala = {s for m, s in original_suktas if m == mandala}
        parsed_for_mandala = {s for m, s in parsed_suktas if m == mandala}
        missing = sorted(original_for_mandala - parsed_for_mandala)

        total_original += len(original_for_mandala)
        total_parsed += len(parsed_for_mandala)
        total_missing += len(missing)

        status = "✅" if not missing else "⚠️"

        print(f"\n{status} Mandala {mandala}:")
        print(f"  Expected: {EXPECTED_SUKTAS[mandala]} Suktas")
        print(f"  In original: {len(original_for_mandala)} Suktas")
        print(f"  In parsed: {len(parsed_for_mandala)} Suktas")
        print(f"  Missing: {len(missing)} Suktas")

        if missing:
            missing_suktas[mandala] = missing
            # Show missing Suktas
            if len(missing) <= 20:
                print(f"  Missing Sukta numbers: {', '.join(map(str, missing))}")
            else:
                print(f"  Missing Sukta numbers: {', '.join(map(str, missing[:10]))} ... and {len(missing)-10} more")

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total Suktas in original: {total_original}")
    print(f"Total Suktas in parsed: {total_parsed}")
    print(f"Total Suktas missing: {total_missing}")
    print(f"Retention rate: {(total_parsed/total_original*100):.1f}%")

    if total_missing == 0:
        print("\n✅ PERFECT! All Suktas preserved.")
    elif total_missing < 50:
        print(f"\n✓ GOOD: Only {total_missing} Suktas filtered out ({(total_missing/total_original*100):.1f}%)")
    else:
        print(f"\n⚠️  SIGNIFICANT: {total_missing} Suktas filtered out ({(total_missing/total_original*100):.1f}%)")

    # Check if Sudas is in missing Suktas
    if missing_suktas:
        sudas_suktas = check_sudas_in_suktas(original_file, parsed_file, missing_suktas)

        if sudas_suktas:
            print("\n" + "="*70)
            print("🚨 CRITICAL FINDING")
            print("="*70)
            print(f"{len(sudas_suktas)} Sukta(s) containing Sudas/Sudasa were filtered out:")
            for mandala, sukta in sudas_suktas:
                griffith_code = f"[{mandala:02d}-{sukta:03d}]"
                print(f"  • Mandala {mandala}/Sukta {sukta} (Griffith: {griffith_code})")
            print("\nThese need to be recovered!")

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
