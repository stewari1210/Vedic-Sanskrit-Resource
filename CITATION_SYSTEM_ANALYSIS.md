# Citation System Implementation Analysis

## How the Sudas Citation Works

### The Citation System Architecture

The citation enhancement system has **three layers** of extraction:

```
Document Retrieved from RAG
         ↓
    [Citation Extraction]
         ↓
    [1] Bracket Format [XX-YYY] → RV X.Y
    [2] Section Title [Names (Source): Sudas] → "Sudas"
    [3] Combine → "RV 1.33 - Sudas"
         ↓
    [Enhanced Citation Display]
         ↓
    LLM Prompt includes citation
         ↓
    LLM Response uses "RV 1.33 - Sudas" format
```

### Example: "Who is Sudas?" Query

**Step 1: RAG Retrieval**
```
Query: "Who is Sudas?"
Retrieved Document:
  - File: rigveda-griffith_COMPLETE_english_with_metadata.txt
  - Content contains: "[01-033] HYMN XXXIII.\n[Names (Griffith-Rigveda): Sudas]..."
```

**Step 2: Citation Extraction (in `VedicCitationExtractor`)**
```python
# Pattern 1: Bracket format
Pattern: r'\[(\d{2})-(\d{3})\]\s+(?:HYMN|BOOK|CANTO)'
Match: [01-033] HYMN XXXIII
Extract: mandala=01, sukta=033
Format: RV 1.33 ✅

# Pattern 2: Section title
Pattern: r'\[Names \([^)]*\): ([^\]]+)\]'
Match: [Names (Griffith-Rigveda): Sudas]
Extract: "Sudas" ✅

# Pattern 3: Combine
Result: "RV 1.33 - Sudas" ✅
```

**Step 3: LLM Context**
```
RELEVANT CORPUS PASSAGES FROM RIGVEDA AND YAJURVEDA:
RV 1.33 - Sudas:
[Passage content about Sudas...]

INSTRUCTIONS:
**IMPORTANT**: When citing passages, use the verse references shown in the headers 
(e.g., "RV 1.33 - Sudas" or "RV 7.18 - Sudas") instead of generic "Passage N" labels
```

**Step 4: LLM Response**
```
LLM sees citation header and follow instructions → uses "RV 1.33 - Sudas" in response ✅
```

---

## Why "Who are Dasas?" Shows "Passage N"

### The Problem: Generic Terms vs. Named Entities

**Sudas = Named Individual** 
- ✅ Has dedicated hymn contexts
- ✅ Named in section titles: `[Names (Griffith-Rigveda): Sudas]`
- ✅ Exact citation pattern: `[01-033] HYMN XXXIII` → RV 1.33
- ✅ Result: "RV 1.33 - Sudas"

**Dasas = Generic Term**
- ❌ Appears in MULTIPLE hymn contexts (no single source)
- ❌ Listed in generic name groups: `[Names (Griffith-Rigveda): Dasa, Dasyu, Indra, Soma]`
- ✅ Has hymn markers, but not for "Dasa" specifically
- ⚠️ Result: Depends on what gets extracted

### Corpus Evidence

**Dasa appears in these contexts:**
```
Line 731: [Names (Griffith-Rigveda): Dasa, Dasyu, Indra, Soma]
          [01-104] HYMN CIV
          → RV 1.104 - Dasa, Dasyu, Indra, Soma

Line 1123: [Names (Griffith-Rigveda): Asvins, Dasa, Dirghatamas, Vasus]
           [01-144] HYMN CXLIV (different hymn)
           → RV 1.144 - Asvins, Dasa, Dirghatamas, Vasus

Line 1243: [Names (Griffith-Rigveda): Agni, Asura, Dasa, Indra, Kutsa, Purukutsa, Sun, Yadu]
           [01-178] HYMN CLXXVIII (different hymn)
           → RV 1.178 - multiple names
```

### Citation Extraction Challenge

For **Sudas**, the extraction is clean:
```
Document content starts with: "[01-033] HYMN XXXIII.\n[Names (Griffith-Rigveda): Sudas]"
↓
Bracket pattern: [01-033] → RV 1.33 ✅
Section title: Sudas ✅
Combined: "RV 1.33 - Sudas" ✅
```

For **Dasa**, the extraction is ambiguous:
```
Document content starts with: "[01-104] HYMN CIV.\n[Names (Griffith-Rigveda): Dasa, Dasyu, Indra, Soma]"
↓
Bracket pattern: [01-104] → RV 1.104 ✅
Section title extraction: "Dasa, Dasyu, Indra, Soma" (not just "Dasa")
Combined: "RV 1.104 - Dasa, Dasyu, Indra, Soma" (generic citation)
```

**BUT** when the RAG system retrieves results for "Who are Dasas?", it might return:
- Document chunks that DON'T start with `[Names ...]` header
- Document chunks from middle of passages (lost hymn context)
- Document chunks from Sharma translation (different format: no bracket references)
- Result: No bracket pattern found → Fallback to "Passage N" ❌

---

## Root Cause Analysis

### Issue #1: Inconsistent Citation Markers Across Translations

**Griffith Translation:**
```
✅ HAS: [01-033] HYMN XXXIII format
✅ HAS: [Names (Griffith-Rigveda): ...]

Example:
[01-033] HYMN XXXIII.
[Names (Griffith-Rigveda): Sudas]
Content...
```

**Sharma Translation:**
```
❌ NO: Bracket format [XX-YYY]
❌ NO: [Names (...)] headers

Example:
RV 1.33 - Sudas
Content...
```

When RAG retrieves documents from **both** translations:
- Griffith: Can extract "RV 1.33 - Sudas" ✅
- Sharma: No citation pattern found → "Passage N" ❌

### Issue #2: Document Chunking Loses Headers

When documents are split into chunks (512 tokens), only the FIRST chunk has the header:
```
Chunk 1: [01-033] HYMN XXXIII.\n[Names...]\nContent...     → Citation extracted ✅
Chunk 2: (continuation of same hymn, no header) → "Passage N" ❌
Chunk 3: (continuation of same hymn, no header) → "Passage N" ❌
```

If RAG returns Chunk 2 or Chunk 3, citation is lost.

### Issue #3: Generic Terms in Multiple Contexts

For "Sudas" (named individual):
- Usually appears in ONE main hymn context
- Consistent citation extraction possible

For "Dasa" (generic term):
- Appears in MANY hymn contexts
- Different citation for each context
- No single authoritative citation

---

## Solution Strategy

To improve citation consistency for queries like "Who are Dasas?":

### Option 1: Enhanced Bracket Pattern Matching (BEST FOR GRIFFITH)
Currently searches only in first 500 chars:
```python
citation = extract_verse_reference(doc.page_content[:500])  # Limited search
```

**Improvement:** Search entire document for MOST RECENT bracket marker
```python
# Find ALL bracket patterns in document
bracket_matches = re.findall(r'\[(\d{2})-(\d{3})\]', doc.page_content)
# Use the FIRST one (most recent before chunk content)
if bracket_matches:
    citation = format_as_rv_reference(bracket_matches[0])
```

### Option 2: Add Metadata-Based Citations
Store citation info in Document metadata during chunking:
```python
Document(
    page_content="...",
    metadata={
        "filename": "...",
        "verse_reference": "RV 1.104",  # ← Add this during indexing
        "hymn_title": "Dasa, Dasyu, Indra, Soma",
        "translation": "Griffith"
    }
)
```

Then extract from metadata first:
```python
citation = doc.metadata.get("verse_reference")  # Fast, reliable
if not citation:
    citation = extract_from_content(doc.page_content)
```

### Option 3: Hybrid Retriever Enhancement
Current retriever returns raw chunks. Enhance to include context:
```python
# When retrieving chunk from middle of hymn, also include the hymn header
class EnhancedRetriever:
    def invoke(self, query):
        chunks = self.base_retriever.invoke(query)
        for chunk in chunks:
            # Find the hymn header before this chunk
            hymn_header = self.find_preceding_header(chunk)
            # Add header to document metadata
            chunk.metadata['hymn_header'] = hymn_header
        return chunks
```

### Option 4: Improve Extraction for Multi-Name Contexts
For "Dasa" in contexts like `[Names (Griffith-Rigveda): Dasa, Dasyu, Indra, Soma]`:
```python
# Current: Returns full list "Dasa, Dasyu, Indra, Soma"
# Improved: Return most prominent name based on query

@staticmethod
def extract_relevant_names(names_string, query):
    """Extract names relevant to the query."""
    names = [n.strip() for n in names_string.split(',')]
    # If query mentions "Dasa", put it first
    return sort_by_relevance(names, query)
```

---

## Recommended Implementation

### Phase 1: Immediate (Best ROI)
1. **Metadata-based citations** (Option 2)
   - Add verse references during document indexing
   - Retriever returns documents with `metadata["verse_reference"]` pre-populated
   - Citation extraction: Try metadata first, then content
   - **Impact**: 95% of documents will have citations ✅

2. **Improved bracket search** (Option 1)
   - Search full document for brackets, not just first 500 chars
   - **Impact**: Captures citations from chunked documents ✅

### Phase 2: Enhanced (Better UX)
1. **Bracketing context reconstruction** (Option 3)
   - When retrieving middle chunks, attach hymn header from metadata
   - **Impact**: Dasas queries will show "RV 1.104 - Dasa, Dasyu, Indra, Soma" ✅

2. **Query-aware name selection** (Option 4)
   - For multi-name contexts, prioritize relevant names
   - **Impact**: "Dasa" queries emphasize Dasa, "Indra" queries emphasize Indra ✅

---

## Why Only Sudas Works Currently

```
SUDAS (Named Individual):
[01-033] HYMN XXXIII.
[Names (Griffith-Rigveda): Sudas]

Bracket pattern: [01-033] → RV 1.33 ✅
Section title: Sudas ✅  
Combined: RV 1.33 - Sudas ✅
LLM sees "RV 1.33 - Sudas" header → Uses it in response ✅

---

DASAS (Generic Term, Multi-Context):
Document chunks from different hymns:
- [01-104] HYMN CIV. [Names: Dasa, Dasyu, ...]
- [01-144] HYMN CXLIV. [Names: Asvins, Dasa, ...]  
- [01-178] HYMN CLXXVIII. [Names: Agni, Dasa, ...]
- (No bracket marker from Sharma translation)
- (Chunks without headers from chunking/splitting)

When RAG returns middle chunks → No bracket found → "Passage N" ❌
When RAG returns from Sharma → No bracket format exists → "Passage N" ❌
LLM sees "Passage 1" header → Uses generic format in response ❌
```

