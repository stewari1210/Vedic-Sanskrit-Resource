# Source Text Filtering Enhancement

## Overview
Enhanced the RAG retriever to intelligently distinguish between Vedic texts (Rigveda, Yajurveda, etc.) when explicitly mentioned in queries. This prevents mixing sources inappropriately and provides clearer, more accurate answers.

## Problem Identified
When users asked "What is the role of Maruts in Yajurveda?", the system retrieved and presented primarily Rigveda content without distinguishing the source. This led to:
- Misleading answers that didn't reflect the specific text requested
- Mixing extensive Rigveda mythological descriptions with sparse Yajurveda ritual references
- Lack of transparency about source coverage differences

## Solution Implemented

### 1. Source Text Detection (`retriever.py`)
Added `_detect_source_text_filter()` method that:
- Detects mentions of specific Vedic texts: Rigveda, Yajurveda, Griffith's translations
- Identifies query type:
  - **Strict filtering**: Single text mentioned ("What is X in Rigveda?")
  - **Balanced retrieval**: Multiple texts mentioned ("Compare X in Rigveda and Yajurveda")
- Returns list of source identifiers and filtering mode

**Example detection:**
```python
Query: "What is the role of Maruts in Yajurveda?"
→ sources=['yajurveda'], strict=True

Query: "Compare Maruts in Rigveda and Yajurveda"
→ sources=['rigveda', 'yajurveda'], strict=False
```

### 2. Document Filtering (`retriever.py`)
Added `_filter_docs_by_source()` method that:
- Uses document metadata `filename` field to identify source
- **Strict mode**: Only returns documents from requested source(s)
- **Balanced mode**: Prioritizes requested sources but includes others
- Applies to both primary retrieval and query expansion docs

**Filtering logic:**
- Checks `doc.metadata['filename']` against source filters
- Matches: `'rigveda' in 'griffith-rigveda_COMPLETE_english_with_metadata'`
- Logs: Number of matching vs. filtered docs for transparency

### 3. Enhanced RAG Prompt (`prompts.py`)
Added "SOURCE TEXT DISTINCTION RULES" section:

#### Single Text Queries
- Focus ONLY on requested text documents
- Acknowledge source explicitly: "Based on Rigveda sources..."
- Do NOT mix in other texts unless comparative

#### Comparative Queries
- Explicitly distinguish sources: "In Rigveda, X. In Yajurveda, Y."
- Highlight coverage differences: "Rigveda has extensive descriptions, while Yajurveda focuses on ritual contexts"

#### Coverage Transparency
- State when text has limited mentions
- Clarify ritual vs. mythological focus differences
- Acknowledge when most content comes from one text despite query about another

## Usage Examples

### Before Enhancement
```
Q: "What is the role of Maruts in Yajurveda?"
Retrieved: 16 docs (mostly Rigveda hymns)
Answer: "The Maruts are powerful beings who bring rain, are associated with
         lightning, and have a strong connection to Indra. They are also
         mentioned as being involved in battles and conflicts."
Issue: Answer is generic, mostly from Rigveda, doesn't distinguish sources
```

### After Enhancement
```
Q: "What is the role of Maruts in Yajurveda?"
Log: "HybridRetriever: Detected source filter: ['yajurveda'] (strict)"
Log: "HybridRetriever: Strict filter applied - 4 docs match ['yajurveda'], 12 filtered out"
Expected Answer: "In Yajurveda, Maruts are invoked as 'voracious eaters of foes'
                 (Book IX, verse 44) and mentioned in ritual offerings (Seven Rice
                 Cakes to Maruts). They are described as friends of Indra. Note:
                 Yajurveda focuses on ritual invocations rather than extensive
                 mythological descriptions found in Rigveda."
```

### Comparative Query
```
Q: "How are Maruts described in Rigveda and Yajurveda?"
Log: "HybridRetriever: Detected source filter: ['rigveda', 'yajurveda'] (balanced)"
Log: "HybridRetriever: Balanced filter - 10 docs prioritized, 6 others included"
Expected Answer: "In Rigveda, Maruts are extensively described as storm deities,
                 sons of Rudra, associated with rain, lightning, and battles. They
                 are praised in numerous hymns (1.38, 1.85, 1.87, etc.). In
                 Yajurveda, Maruts appear primarily in ritual contexts - they are
                 invoked in offerings and described as friends of Indra, but lack
                 the extensive mythological narratives found in Rigveda."
```

## Technical Details

### Source Detection Patterns
```python
source_mapping = {
    'rigveda': ['rigveda', 'rig veda', 'rig-veda', 'rgveda'],
    'yajurveda': ['yajurveda', 'yajur veda', 'yajur-veda'],
    'griffith-rigveda': ['griffith rigveda', 'griffith\'s rigveda'],
    'griffith-yajurveda': ['griffith yajurveda', 'griffith\'s yajurveda'],
}
```

### Comparative Query Indicators
```python
comparative_keywords = ['both', 'compare', 'comparison', 'versus', 'vs', 'and', 'between']
```

### Document Metadata Matching
```python
filename = doc.metadata.get('filename', '').lower()
matches = any(source in filename for source in source_filters)
# Example: 'yajurveda' in 'yajurveda-griffith_complete_english_with_metadata' → True
```

## Logging Output
The enhancement adds detailed logging for transparency:

```
[INFO: retriever]: HybridRetriever: Detected source filter: ['yajurveda'] (strict (single source))
[INFO: retriever]: HybridRetriever: Strict filter applied - 4 docs match ['yajurveda'], 12 filtered out
[INFO: retriever]: HybridRetriever: Added 2 expansion docs via proper noun association
[INFO: retriever]: HybridRetriever: Total docs (primary + expansion) = 6
```

## Files Modified

1. **`src/utils/retriever.py`**
   - Added `_detect_source_text_filter()` method (lines ~141-178)
   - Added `_filter_docs_by_source()` method (lines ~180-210)
   - Integrated filtering into `_get_relevant_documents()` (lines ~235, ~445)

2. **`src/utils/prompts.py`**
   - Added "SOURCE TEXT DISTINCTION RULES" to `RAG_PROMPT` (lines ~148-195)
   - Provided examples for single-text and comparative queries

## Testing Recommendations

### Test Case 1: Single Text Query (Strict)
```bash
python3 src/cli_run.py --debug
Q> What is the role of Maruts in Yajurveda?
```
Expected:
- Log shows strict filtering detected
- Answer focuses on Yajurveda content (ritual offerings, invocations)
- Acknowledges limited mythological coverage compared to Rigveda

### Test Case 2: Comparative Query (Balanced)
```bash
Q> Compare how Indra is described in Rigveda and Yajurveda
```
Expected:
- Log shows balanced filtering detected
- Answer explicitly distinguishes: "In Rigveda... In Yajurveda..."
- Highlights coverage differences

### Test Case 3: No Source Mentioned (No Filtering)
```bash
Q> Who are the Maruts?
```
Expected:
- No source filtering detected
- Retrieves from all available texts
- Answer doesn't need to distinguish sources unless naturally relevant

## Benefits

1. **Accuracy**: Users get information from the specific text they requested
2. **Transparency**: Clear logging shows which sources were used
3. **Clarity**: Answers explicitly state source text origins
4. **Coverage Awareness**: System acknowledges when one text has more/less information
5. **Comparative Analysis**: Properly structures answers comparing multiple texts

## Future Enhancements

1. Add support for additional Vedic texts (Samaveda, Atharvaveda)
2. Implement translator-specific filtering (Griffith vs. Sharma)
3. Add source statistics to debug output (X% from Rigveda, Y% from Yajurveda)
4. Support sub-text filtering (e.g., "Rigveda Book 7" for Battle of Ten Kings)

## Related Issues
- Fixes: Maruts query returning predominantly Rigveda content for Yajurveda-specific question
- Improves: Source attribution and transparency
- Enables: Better comparative analysis between texts
