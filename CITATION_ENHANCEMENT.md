# Citation Enhancement System for Vedic Texts

## Overview

The RAG system now provides **verifiable, authentic citations** for retrieved passages instead of generic "Passage 1", "Passage 2" references. Citations are automatically extracted and formatted as proper Vedic text identifiers like "RV 1.1.1" (Rigveda 1.1.1), "YV 3.45" (Yajurveda 3.45), or "SB 1.1.1.1" (Satapatha Brahmana 1.1.1.1).

## How It Works

### Citation Sources (Priority Order)

1. **Metadata Fields** - Highest priority
   - `verse_reference`: "RV 1.1.1"
   - `hymn_number` + `mandala`: Rigveda format
   - `verse_number` + `adhyaya`: Yajurveda format
   - `reference`: Any stored reference

2. **Content Extraction** - Secondary
   - Regex patterns extract citations from text headers and structure
   - Examples: "# Hymn 1: Invocation to Agni" → "RV 1.1.1"
   - Supports multiple formats and translations

3. **Section Titles** - Enhanced context
   - Appends meaningful titles: "RV 1.1.1 - Invocation to Agni"
   - Provides immediate context for users

4. **Fallback** - Last resort
   - Generic "Passage N" if no reference found

### Supported Citation Formats

```
Rigveda:        RV 1.1.1 (Mandala.Sukta.Verse)
Yajurveda:      YV 3.45 (Adhyaya.Verse)
Brahmanas:      SB 1.1.1.1 (Adhyaya.Kanda.Pada.Prapatha)
Ramayana:       RM Book 1, Canto 1
Hymn:           Hymn 1 (Agni Invocation)
Generic:        Passage N (fallback only)
```

## Integration Points

### 1. In Agentic RAG (`src/utils/agentic_rag.py`)

**Before:**
```python
result = "\n\n".join([f"Passage {i+1}: {doc.page_content[:500]}" 
                      for i, doc in enumerate(examples)])
```

**After:**
```python
from src.utils.citation_enhancer import enhance_corpus_results_with_citations
result = enhance_corpus_results_with_citations(examples)
# Output: "RV 1.1.1 - Invocation to Agni:\n..."
```

### 2. Citation References in Answers

**Before:**
```json
{
  "citations": ["Corpus passage 1", "Corpus passage 2"]
}
```

**After:**
```json
{
  "citations": [
    {
      "citation": "RV 1.1.1 - Invocation to Agni",
      "source": "rigveda-griffith_COMPLETE_english_with_metadata",
      "chunk_index": 0,
      "url_fragment": "rv-1-1-1-invocation-to-agni"
    },
    {
      "citation": "RV 1.1.2",
      "source": "rigveda-griffith_COMPLETE_english_with_metadata",
      "chunk_index": 1,
      "url_fragment": "rv-1-1-2"
    }
  ]
}
```

## User Experience Example

### Query: "Which Rigvedic verses contain gender-specific language?"

**Response:**

> Based on the provided corpus passages, here's an analysis of Rigvedic verses containing gender-specific language:

**RV 1.1.1 - Invocation to Agni:**
The passage highlights gendered language through divine pairs and deities...

**RV 7.33.14 - Vasishtha's Cosmic Order:**
Vasishtha speaks of universal laws distinguishing masculine and feminine principles...

**RV 10.85.1-47 - The Wedding Hymn:**
This hymn explicitly discusses gender roles in marriage and domestic relationships...

---

## Technical Details

### Citation Extraction Patterns

```python
# Rigveda: RV 1.1.1 or Rigveda 1.1
'rigveda_hymn': r'(?:Hymn|RV|Rigveda)\s+(\d+)\.(\d+)(?:\.(\d+))?'

# Yajurveda: YV 1.1 or Verse 1.1  
'yajurveda_verse': r'(?:YV|Yajurveda|Verse)\s+(\d+)\.(\d+)'

# Brahmanas: SB 1.1.1.1
'brahmana_reference': r'(?:Satapatha|SB|Brahmana)\s+(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?'

# Markdown headers: # Hymn 1: Title or ## Book 1: Description
'heading_pattern': r'^#+\s*(?:Hymn|Verse|Sutra|Section|Book)\s+(\d+)(?::\s*(.+))?'
```

### Processing Flow

```
Retrieved Document
    ↓
[1] Check metadata for stored verse_reference
    ↓ (not found)
[2] Extract from content using regex patterns
    ↓ (not found)
[3] Extract section title from headers
    ↓
CitationFormatter.format_citation_with_source()
    ↓
"RV 1.1.1 - Invocation to Agni"
```

## Adding Citations to New Texts

### Option 1: Store in Metadata (Recommended)

Create a `filename_metadata.json` with verse references:

```json
{
  "filename": "rigveda-griffith_COMPLETE_english_with_metadata",
  "title": "Rigveda - Griffith Translation",
  "verse_reference": "RV 1.1.1",
  "mandala": 1,
  "sukta": 1,
  "hymn_number": 1
}
```

### Option 2: Include in Text Headers

Ensure text includes proper headers:

```markdown
# Hymn 1: Invocation to Agni
## Mandala 1, Sukta 1
### RV 1.1.1 - From Griffith Translation

[Content...]
```

### Option 3: Use Smart Extraction

The system automatically extracts from unstructured text:

```
"In RV 1.1.1, Agni is invoked as the messenger between mortals and gods..."
→ Citation extracted as "RV 1.1.1"
```

## Citation Validation

To verify citations work correctly:

```python
from src.utils.citation_enhancer import VedicCitationExtractor

text = "This is from RV 1.1.1 and discusses..."
citation = VedicCitationExtractor.extract_verse_reference(text)
print(citation)  # Output: "RV 1.1.1"
```

## Future Enhancements

1. **Direct URL Linking**
   - Generate links to external Vedic databases
   - Example: Direct link to RV 1.1.1 on vedabase.io

2. **Multi-Translation Comparison**
   - Show same verse from different translations
   - Compare Griffith vs Sharma interpretations

3. **Hyperlinked Citations**
   - Click citations to jump to original text
   - Internal linking within Streamlit UI

4. **Verse Text Display**
   - Show original Sanskrit alongside translation
   - Include transliteration

5. **Citation Analytics**
   - Track most-cited verses
   - Identify gaps in corpus coverage

## Files Modified

- `src/utils/citation_enhancer.py` - New citation extraction and formatting module
- `src/utils/agentic_rag.py` - Updated to use enhanced citations

## Related Documentation

- See `RETRIEVER_INTEGRATION_SUMMARY.md` for retrieval pipeline
- See `proper_noun_variants.json` for cross-translation reference mapping
- See `local_store/` structure for document organization
