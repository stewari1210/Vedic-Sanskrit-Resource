# Guide: Enhancing Document Metadata for Better Citations

This guide explains how to prepare your Vedic texts to work optimally with the citation enhancement system.

## Quick Start: Essential Metadata Fields

For each text file in `local_store/`, create a corresponding `*_metadata.json` with these fields:

### Rigveda Format

```json
{
  "filename": "rigveda-griffith_COMPLETE_english_with_metadata",
  "title": "Rigveda - Griffith Translation",
  "collection": "Rigveda",
  "translation": "Griffith",
  "year": 1870,
  
  "verse_reference": "RV 1.1.1",
  "mandala": 1,
  "sukta": 1,
  "hymn_number": 1
}
```

### Yajurveda Format

```json
{
  "filename": "yajurveda-griffith_COMPLETE_english_with_metadata",
  "title": "Yajurveda - Griffith Translation",
  "collection": "Yajurveda",
  "translation": "Griffith",
  
  "verse_reference": "YV 3.45",
  "adhyaya": 3,
  "verse_number": 45
}
```

### Brahmana Format

```json
{
  "filename": "satapatha_brahmana_part_01",
  "title": "Satapatha Brahmana - Part 1",
  "collection": "Satapatha Brahmana",
  
  "verse_reference": "SB 1.1.1.1",
  "adhyaya": 1,
  "kanda": 1,
  "pada": 1,
  "prapatha": 1
}
```

### Ramayana Format

```json
{
  "filename": "griffith-ramayana",
  "title": "The Ramayana - Griffith Translation",
  "collection": "Ramayana",
  "book": 1,
  "canto": 1
}
```

## Metadata Field Reference

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `filename` | string | YES | Identifier for the text | "rigveda-griffith..." |
| `title` | string | YES | Full title | "Rigveda - Griffith Translation" |
| `collection` | string | YES | Vedic text category | "Rigveda", "Yajurveda", "Brahmana" |
| `verse_reference` | string | OPTIONAL | Pre-computed citation | "RV 1.1.1" |
| `mandala` | integer | For RV | Mandala number | 1-10 |
| `sukta` | integer | For RV | Hymn/Sukta number | 1-191 |
| `adhyaya` | integer | For YV/BR | Chapter/Adhyaya | 1-N |
| `kanda` | integer | For BR | Section number | 1-14 |
| `pada` | integer | For BR | Subsection | 1-5 |
| `prapatha` | integer | For BR | Verse within section | 1-N |
| `author` | string | OPTIONAL | Original composer (if known) | "Valmiki" |
| `translator` | string | OPTIONAL | Modern translator | "Ralph T. H. Griffith" |
| `year` | integer | OPTIONAL | Publication year | 1870-1876 |
| `source_url` | string | OPTIONAL | Original source | "http://vedabase.io/..." |

## Content Header Conventions

Structure your markdown files with clear headers that include verse numbers:

### Example: Rigveda Chapter

```markdown
# Book I - Mandala 1

## Hymn 1 - Invocation to Agni (RV 1.1)

### Verse 1 (RV 1.1.1)
Agni, the sacred fire, is worshipped at dawn...

### Verse 2 (RV 1.1.2)
O Agni, accept these prayers...

## Hymn 2 - To Indra (RV 1.2)

### Verse 1 (RV 1.2.1)
Indra, mighty among the gods, receives our praise...
```

### Example: Yajurveda Chapter

```markdown
# Yajurveda - Adhyaya 1

## Verse 1 (YV 1.1)
The sacred fire must be arranged with proper care...

## Verse 2 (YV 1.2)
Seven priests perform the ritual according to the Vedas...
```

### Example: Satapatha Brahmana Chapter

```markdown
# Book I - Adhyaya 1

## Kanda 1 - Pada 1

### Prapatha 1 (SB 1.1.1.1)
The sacrifice originates from Prajapati...

### Prapatha 2 (SB 1.1.1.2)
The gods and asuras were of divine origin...
```

## Citation Extraction Logic

The system extracts citations in this order:

### 1. Metadata First (Highest Priority)
```python
if metadata.get('verse_reference'):
    citation = metadata['verse_reference']  # Use stored value
    # Returns: "RV 1.1.1"
```

### 2. Calculated from Components
```python
if metadata.get('mandala') and metadata.get('sukta'):
    mandala = metadata['mandala']
    sukta = metadata['sukta']
    citation = f"RV {mandala}.{sukta}"
    # Returns: "RV 1.1"
```

### 3. Extract from Headers
```python
# Searches text for patterns like:
# "# Hymn 1: ..."
# "RV 1.1.1"
# "### Verse 1 (RV 1.1.1)"
citation = extract_from_headers(text)
```

### 4. Fallback
```python
citation = f"Passage {passage_number}"
```

## Best Practices

### ✅ DO:

1. **Include verse references in metadata**
   ```json
   {"verse_reference": "RV 1.1.1"}
   ```

2. **Use consistent header formatting**
   ```markdown
   # Hymn 1: Invocation to Agni (RV 1.1)
   ```

3. **Break text into meaningful chunks**
   - One hymn/verse per section
   - Clear section breaks with headers

4. **Store translation info**
   ```json
   {"translator": "Ralph T. H. Griffith", "year": 1870}
   ```

### ❌ DON'T:

1. **Use ambiguous headers**
   ```markdown
   # Section 1  ← Too vague
   ```

2. **Mix verse numbers**
   - Keep RV, YV, SB formats separate and consistent

3. **Store only filename**
   - Include verse reference for accuracy

4. **Skip metadata files**
   - They're critical for citations to work

## Validation Checklist

Before deploying a new text, verify:

- [ ] Metadata file exists: `name_metadata.json`
- [ ] `filename` field is unique
- [ ] `collection` matches Vedic text type
- [ ] `verse_reference` format is correct (e.g., "RV 1.1.1")
- [ ] Headers include verse numbers
- [ ] Text is properly chunked (meaningful breaks)
- [ ] No personal notes or OCR artifacts remain
- [ ] Citations can be tested and verified

## Testing Citation Extraction

```python
from src.utils.citation_enhancer import VedicCitationExtractor, CitationFormatter
from langchain_core.documents import Document

# Create test document
doc = Document(
    page_content="# Hymn 1: Invocation to Agni\nThe text of the hymn...",
    metadata={
        "filename": "rigveda-griffith",
        "verse_reference": "RV 1.1.1"
    }
)

# Test citation extraction
citation, source = CitationFormatter.format_citation_with_source(doc, 1)
print(f"Citation: {citation}")
print(f"Source: {source}")

# Expected output:
# Citation: RV 1.1.1 - Invocation to Agni
# Source: rigveda-griffith
```

## Common Citation Patterns

### Pattern 1: Rigveda Mandala.Sukta.Verse
```
RV 1.1.1   → Rigveda, Mandala 1, Sukta 1, Verse 1
RV 10.19.4 → Rigveda, Mandala 10, Sukta 19, Verse 4
```

### Pattern 2: Yajurveda Adhyaya.Verse
```
YV 1.1     → Yajurveda, Chapter 1, Verse 1
YV 40.1    → Yajurveda, Chapter 40, Verse 1
```

### Pattern 3: Satapatha Brahmana
```
SB 1.1.1.1   → Book 1, Chapter 1, Section 1, Prapatha 1
SB 14.4.2.38 → Book 14, Chapter 4, Section 2, Prapatha 38
```

### Pattern 4: Ramayana
```
RM Book 1, Canto 1    → Ramayana, Book 1, Canto 1
RM Book 6, Canto 115  → Ramayana, Book 6, Canto 115
```

## Example: Complete Metadata File

```json
{
  "_comment": "Metadata for Rigveda Griffith translation chunks",
  "filename": "rigveda-griffith_COMPLETE_english_with_metadata",
  "title": "The Rigveda of Valmiki - English Translation",
  "author": "Valmiki (attributed)",
  "translator": "Ralph T. H. Griffith, M.A.",
  "collection": "Rigveda",
  "format": "Complete Translation",
  "language": "English",
  "original_language": "Sanskrit",
  "publication_info": "Trübner & Co., London; E. J. Lazarus, Benares",
  "year": 1870,
  "pages": 1022,
  "mandala": 1,
  "sukta": 1,
  "hymn_number": 1,
  "verse_reference": "RV 1.1.1",
  "subject": "Vedic Hymns",
  "keywords": ["Rigveda", "Vedic", "Sanskrit", "Griffith"],
  "description": "Complete English translation of the Rigveda by Ralph T. H. Griffith",
  "access_url": "https://vedabase.io/en/rigveda/",
  "last_updated": "2025-01-25"
}
```

## Troubleshooting

### Citation shows "Passage N" instead of verse reference

**Check:**
1. Is `verse_reference` in metadata?
2. Does text header match extraction patterns?
3. Is the document loaded correctly?

**Fix:**
```json
{
  "verse_reference": "RV 1.1.1"
}
```

### Wrong citation appears

**Check:**
1. Is metadata `verse_reference` correct?
2. Are multiple patterns matching?
3. Is header text ambiguous?

**Fix:** Ensure unique headers with explicit verse numbers
```markdown
# Hymn 1: Invocation to Agni (RV 1.1.1)
```

### Citation missing section title

**Check:**
1. Does header follow convention?
2. Is text after verse number?

**Fix:**
```markdown
# Hymn 1: Invocation to Agni
```
(Good - system extracts "Invocation to Agni")

---

For questions or issues, refer to `CITATION_ENHANCEMENT.md` or test with the provided testing script.
