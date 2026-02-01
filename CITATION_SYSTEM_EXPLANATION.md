# Citation System: Implementation Explanation

## Simple Explanation

### Why "Who is Sudas?" Works with Citations

```
Query: "Who is Sudas?"
   ↓
RAG retrieves from Griffith corpus:
   "[01-033] HYMN XXXIII.
    [Names (Griffith-Rigveda): Sudas]
    Content about Sudas..."
   ↓
Citation Extractor sees:
   - Bracket format: [01-033] → Extract "RV 1.33"
   - Name in section: [Names (...): Sudas] → Extract "Sudas"
   - Combine: "RV 1.33 - Sudas" ✅
   ↓
LLM Prompt receives:
   "RELEVANT CORPUS PASSAGES:
    RV 1.33 - Sudas:
    [content]
    
    INSTRUCTION: Use verse refs like 'RV 1.33 - Sudas' not 'Passage N'"
   ↓
LLM Response:
   "Sudas is mentioned in RV 1.33 as..." ✅
```

### Why "Who are Dasas?" Shows "Passage N"

```
Query: "Who are Dasas?"
   ↓
RAG retrieves (potentially from 3 different sources):
   
   Option A - Griffith with name header:
   "[01-104] HYMN CIV.
    [Names (Griffith-Rigveda): Dasa, Dasyu, Indra, Soma]
    Content..."
   → Citation Extractor: "RV 1.104 - Dasa, Dasyu, Indra, Soma" ✅
   
   Option B - Griffith without header (chunk from middle):
   "...content about Dasas...
    [some more content]..."
   → NO [01-XXX] pattern found
   → Falls back to "Passage 4" ❌
   
   Option C - Sharma translation (no bracket format):
   "RV 1.104 - Dasa, Dasyu, Indra
    ...content..."
   → NO [01-XXX] pattern found (different format)
   → Falls back to "Passage 4" ❌
   ↓
LLM Prompt receives mixed citations:
   "RELEVANT CORPUS PASSAGES:
    RV 1.104 - Dasa, Dasyu...: [content]
    Passage 2: [content]
    Passage 4: [content]
    ..."
   ↓
LLM Response:
   "Passages show that Dasas appear in different contexts..." ❌
```

---

## Technical Root Causes

### 1. **Griffith Translation vs. Sharma Translation**

| Aspect | Griffith | Sharma |
|--------|----------|--------|
| Bracket Format | ✅ `[01-033]` | ❌ No brackets |
| Names Section | ✅ `[Names (Griffith-Rigveda): Sudas]` | ❌ Different format |
| Citation Extraction | ✅ Easy | ❌ Not found |

### 2. **Named Individuals vs. Generic Terms**

| Type | Example | Issue | Solution |
|------|---------|-------|----------|
| Named | Sudas | Appears in 1-2 specific hymns | Easy to extract |
| Generic | Dasa, Dasyu | Appears in 10+ hymns, scattered | Hard to pick "main" reference |

### 3. **Document Chunking Loss**

```
Original Hymn (RV 1.104):
┌─────────────────────────────────┐
│ [01-104] HYMN CIV.              │  ← Citation here
│ [Names (...): Dasa, Dasyu, ...] │  ← Name here
│                                  │
│ Content Part 1 (512 tokens)      │ ← Chunk 1: Has header ✅
└─────────────────────────────────┘

Content Part 2 (512 tokens) from middle:
┌─────────────────────────────────┐
│ "...continuing text about Dasa" │ ← Chunk 2: NO header ❌
│ ...                              │
│ "...more Dasa references"        │
└─────────────────────────────────┘

Chunk 2 loses citation because it's from the middle!
```

---

## Current Citation System Code

### Location: `src/utils/citation_enhancer.py`

```python
class VedicCitationExtractor:
    PATTERNS = {
        'bracket_reference': r'\[(\d{2})-(\d{3})\]\s+(?:HYMN|BOOK|CANTO)',
        'rigveda_hymn': r'(?:RV|Rigveda)\s+(\d+)\.(\d+)(?:\.(\d+))?',
        # ... other patterns
    }
    
    @staticmethod
    def extract_verse_reference(text: str) -> Optional[str]:
        """Try each pattern to extract citation."""
        for pattern_name, pattern in VedicCitationExtractor.PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return VedicCitationExtractor._format_citation(pattern_name, match)
        return None

def enhance_corpus_results_with_citations(examples: List[Document]) -> str:
    """
    For each document:
    1. Extract citation (tries bracket format [01-033], then RV X.Y, etc.)
    2. Extract section title ([Names (...): Title])
    3. Combine: "RV 1.33 - Sudas"
    4. Format with content
    """
```

### Current Behavior

```python
# Extract citation from first 500 characters only
citation = VedicCitationExtractor.extract_verse_reference(doc.page_content[:500])

# If found and has title, combine them
if citation and section_title:
    citation_label = f"{citation} - {section_title}"
else:
    citation_label = f"Passage {passage_number}"  # ← Fallback
```

**Problems:**
1. Only searches first 500 chars → Middle chunks lose citations
2. Ignores document metadata → No pre-computed citations
3. No Sharma translation support → Falls back to Passage N
4. No hybrid approach → Doesn't combine metadata + content extraction

---

## Why This Matters

### Current Results

**Good:** "Who is Sudas?" 
- Returns: "RV 1.33 - Sudas" ✅
- LLM trained to use this format → Response uses verse references

**Bad:** "Who are Dasas?"
- Returns: "Passage 1, Passage 2, Passage 4" ❌
- LLM sees generic format → Response uses generic format
- User sees: "passages show that" (not "RV X.Y shows that")

### Impact

This inconsistency breaks the citation system because:
- LLM only learned to use verse references from seeing them in prompts
- Generic "Passage N" inputs produce generic outputs
- Different queries get different citation styles (confusing UX)
- Reduces educational value (students learn verse references only for some queries)

---

## Next Steps (Recommendations)

### Priority 1: Add Metadata-Based Citations
**When to implement:** Before next production deployment

Modify document indexing to include pre-computed verse references:
```python
Document(
    page_content="...",
    metadata={
        "verse_reference": "RV 1.104",  # ← Add this
        "hymn_title": "Dasa, Dasyu, Indra",
        "translation": "Griffith"
    }
)
```

Then in citation extractor:
```python
# Try metadata first (faster, more reliable)
citation = doc.metadata.get("verse_reference")
if not citation:
    # Fallback to content extraction
    citation = extract_from_content(doc.page_content)
```

### Priority 2: Full Document Bracket Search
**When to implement:** Current iteration

Change extraction from 500 chars to full document:
```python
# Current: searches only first 500 chars
citation = extract_verse_reference(doc.page_content[:500])

# Improved: searches entire document, uses first match
bracket_matches = re.findall(r'\[(\d{2})-(\d{3})\]', doc.page_content)
if bracket_matches:
    citation = format_as_rv_reference(bracket_matches[0])
```

### Priority 3: Multi-Translation Support
**When to implement:** After metadata citations

Add patterns for Sharma translation format and handle gracefully.

### Priority 4: Context-Aware Names
**When to implement:** Long-term enhancement

For multi-name headers like `[Names (...): Dasa, Dasyu, Indra]`:
- Reorder names based on query relevance
- "Who are Dasas?" → "Dasa, Dasyu, Indra"
- "Tell me about Indra" → "Indra, Dasa, Dasyu"

---

## Summary

| Query | Current | Issue | Fix |
|-------|---------|-------|-----|
| "Who is Sudas?" | "RV 1.33 - Sudas" ✅ | None | None needed |
| "Who are Dasas?" | "Passage 1-4" ❌ | Missing citations | Metadata + full search |
| "Tell about Indra" | "Passage N" ❌ | Multiple contexts | Query-aware extraction |

The citation system **is working** for specific named entities (Sudas), but needs enhancement for generic terms (Dasas) due to:
1. Document chunking losing headers
2. Multiple translations with different formats
3. Terms appearing in multiple contexts

**Recommended fix:** Add metadata-based verse references + full document bracket search (can implement today, no breaking changes)

