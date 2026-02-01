# Pancavamsa Brahmana Citation Format Analysis

## Citation Format Found in PB Text

### Primary Format: PBr. X.Y.Z
The Pancavamsa Brahmana uses the format: **PBr. X.Y.Z**

Where:
- **X** = Book/Adhyaya (Chapter, ranges 1-25)
- **Y** = Section/Kanda 
- **Z** = Verse/Pada (subdivisions within section)

### Examples Found in Text
```
PBr. X. 3.2         (Book X, Section 3, Verse 2)
PBr. IV. 2. 10      (Book IV, Section 2, Verse 10)
PBr. IV. 2. 7       (Book IV, Section 2, Verse 7)
PBr. IX. 8. 1       (Book IX, Section 8, Verse 1)
PBr. IX. 8. 13      (Book IX, Section 8, Verse 13)
PBr. IV. 1. 2       (Book IV, Section 1, Verse 2)
PBr. XII. 11. 18    (Book XII, Section 11, Verse 18)
PBr. XX. 3. 2       (Book XX, Section 3, Verse 2)
PBr. XIX. 13        (Book XIX, Section 13 - note: sometimes no verse number)
PBr. XIV. 9. 12     (Book XIV, Section 9, Verse 12)
PBr. XXL 1. 1       (Book XXI, Section 1, Verse 1)
```

## Citation Pattern for Regex

The pattern should be:
```regex
PBr\.\s+(\d+|\b[IVX]+\b)\.\s+(\d+)(?:\.\s+(\d+))?
```

Or more robust:
```regex
PBr\.\s+([0-9]+|[IVX]+)\s*\.\s*(\d+)(?:\s*\.\s*(\d+))?
```

This captures:
- Group 1: Book number (1-25, sometimes in Roman numerals)
- Group 2: Section/Kanda number
- Group 3: Verse/Pada number (optional)

## Standardized Output Format

All PBr. citations should be converted to: **PB X.Y.Z** or **PB X.Y**

Examples:
- PBr. X. 3.2 → PB 10.3.2
- PBr. IV. 2. 10 → PB 4.2.10
- PBr. XXI. 1. 1 → PB 21.1.1

## Integration with citation_enhancer.py

### Addition to PATTERNS dictionary:
```python
'pancavamsa_reference': r'PBr\.\s+([0-9]+|[IVX]+)\s*\.\s*(\d+)(?:\s*\.\s*(\d+))?',  # PBr. X.Y.Z format
```

### Addition to _format_citation method:
```python
elif pattern_name == 'pancavamsa_reference':
    book = match.group(1)
    # Convert Roman numerals to Arabic if needed
    if book.isupper():
        book = str(VedicCitationExtractor._roman_to_int(book))
    section = match.group(2)
    verse = match.group(3)
    verse_part = f".{verse}" if verse else ""
    return f"PB {book}.{section}{verse_part}"
```

### Helper method needed:
```python
@staticmethod
def _roman_to_int(roman: str) -> int:
    """Convert Roman numerals to integers (IV -> 4, XXI -> 21)"""
    values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    total = 0
    i = 0
    while i < len(roman):
        if i + 1 < len(roman) and values[roman[i]] < values[roman[i + 1]]:
            total += values[roman[i + 1]] - values[roman[i]]
            i += 2
        else:
            total += values[roman[i]]
            i += 1
    return total
```

## Comparison with Other Brahmana Citations

### Current SB (Satapatha Brahmana) Pattern
- Format: **SB X.Y.Z[.W]** (Adhyaya.Kanda.Pada[.Prapatha])
- Pattern: `(?:Satapatha|SB|Brahmana)\s+(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?`
- Examples: SB 1.1.1, SB 2.5.3.7

### Proposed PB (Pancavamsa Brahmana) Pattern
- Format: **PB X.Y[.Z]** (Book.Section[.Verse])
- Pattern: `PBr\.\s+([0-9]+|[IVX]+)\s*\.\s*(\d+)(?:\s*\.\s*(\d+))?`
- Examples: PB 1.1, PB 4.2.10, PB 21.1.1

## Notes

1. **Roman Numerals in Books**: Some citations use Roman numerals (I, IV, IX, XII, XIV, XIX, XX, XXI) for book numbers - need conversion function
2. **Optional Verse Number**: Some references only have Book.Section without verse number (e.g., PBr. XIX. 13)
3. **Spacing Variations**: PBr. citations sometimes have extra spaces around periods
4. **Cross-references**: PBr text references other texts like JBr. (Jaiminiya Brahmana), SB (Satapatha Brahmana), but these should be handled by existing patterns

## Testing Required

After implementation, test with these actual PBr citations from the text:
```
PBr. X. 3.2
PBr. IV. 2. 10
PBr. IV. 2. 7
PBr. IX. 8. 1
PBr. XXL 1. 1 (typo for XXI in text)
```

Expected outputs:
```
PB 10.3.2
PB 4.2.10
PB 4.2.7
PB 9.8.1
PB 21.1.1
```
