# Monier-Williams Concept Store Implementation Summary

**Date**: February 1, 2026  
**Objective**: Create JSON concept store from MW dictionary to enhance RAG with bilingual Sanskrit/Hindi support

---

## Overview

The MW Concept Store bridges the gap between:
- **Devanagari queries** (सरस्वती) ↔ **IAST corpus** (Sarasvatī)
- **User queries** ↔ **Sanskrit definitions/context**
- **Modern questions** ↔ **Vedic text references**

---

## Architecture

### How the Concept Store Works in RAG

```
User Query: "सरस्वती नदी के विलुप्त होने"
    ↓
┌─────────────────────────────────────────────────────┐
│ Step 1: Transliteration Layer                      │
│ normalize_query() → ['Sarasvatī', 'sarasvati', ... ]│
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│ Step 2: MW Concept Store Lookup                     │
│ • Input: "सरस्वती"                                   │
│ • Finds: sarasvati entry                             │
│ • Returns:                                           │
│   - Definitions: "goddess of speech", "sacred river" │
│   - Vedic refs: RV. vii, 95, 2 | MBh. ix, 2188      │
│   - Related: vāc, speech, learning                   │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│ Step 3: Enhanced Vector Search                      │
│ • Search with ALL variants (Devanagari + IAST)      │
│ • Expand query with MW definitions                   │
│ • Boost results matching Vedic references            │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│ Step 4: Results + MW Context                        │
│ • Corpus chunks from Qdrant                          │
│ • + MW dictionary definitions (sidebar)              │
│ • + Vedic references for grounding                   │
└─────────────────────────────────────────────────────┘
```

---

## Implementation

### 1. Parser Script

**File**: `parse_monier_williams_concept_store.py`

**Function**: Parse 48MB `mw.txt` → Structured JSON

**Input Format** (MW dictionary pseudo-XML):
```
<L>237579<pc>1182,2<k1>sarasvatI<k2>sa/rasvatI<e>2A
¦ N. of a river (celebrated in RV. and held to be a goddess...
¦ <s>sarasvatī</s> ¦ <lex>f.</lex> goddess of eloquence...
<ls>RV. vii, 95, 2</ls>, <ls>MBh. ix, 2188</ls>
```

**Output Format** (JSON):
```json
{
  "sarasvati": {
    "headwords": ["sarasvatI", "sa/ras—vatI", "sarasvati"],
    "iast_variants": ["sarasvatī", "sarasvat", "saras"],
    "devanagari": "सरस्वति",
    "definitions": [
      "goddess of eloquence and learning",
      "sacred river in Rig Veda",
      "identified with Speech (vāc)"
    ],
    "vedic_refs": ["RV. vii, 95, 2", "MBh. ix, 2188", "VS. xix, 12"],
    "record_ids": ["237579", "237580"]
  }
}
```

**Output Statistics**:
- **Total entries**: 176,146 concepts
- **Lookup keys**: 522,880 keys (includes all variants)
- **File size**: 108.5 MB JSON
- **Processing time**: ~7 seconds on M1 Mac

---

### 2. Integration Utility

**File**: `src/utils/mw_concept_store.py`

**Class**: `MWConceptStore`

**Key Methods**:

| Method | Purpose | Example |
|--------|---------|---------|
| `lookup(term)` | Find MW entry for Sanskrit term | `lookup("अग्नि")` → agni definitions |
| `expand_query(query)` | Add MW definitions to query | `"agni"` → `"agni fire sacrificial god"` |
| `get_vedic_context(query)` | Extract Vedic references | `"soma"` → `["RV.", "AV.", "YV."]` |
| `get_all_variants(term)` | Get all script variants | `"agni"` → `{"अग्नि", "agni", "agni/"}` |
| `batch_lookup(terms)` | Lookup multiple terms | Efficient for multi-word queries |

**Features**:
- ✅ Fast O(1) lookup via pre-built index
- ✅ Bidirectional transliteration (Devanagari ↔ IAST)
- ✅ Automatic normalization (removes accents, diacritics)
- ✅ Vedic reference extraction
- ✅ Query expansion for semantic search

---

### 3. Demo Script

**File**: `demo_mw_rag_integration.py`

**Demonstrates**:
1. Query enhancement with transliteration variants
2. MW dictionary lookup for Sanskrit terms
3. Semantic expansion with definitions
4. Vedic grounding with text references
5. Integration pseudocode for retriever.py

**Sample Output**:
```
Query: "अग्नि पूजा कैसे करें"

Step 1: Transliteration
  • Agni pūjā kaise kareṃ
  • agni pūjā kaise kareṃ
  • अग्नि पूजा कैसे करें

Step 2: MW Lookup
  ✅ 'अग्नि' → 'agni'
     Devanagari: अग्नि
     Definitions: fire, sacrificial fire, god Agni
     Vedic refs: RV., AV., TS.

Step 3: Enhanced Query
  "अग्नि पूजा कैसे करें fire sacrificial agni"

Step 4: RAG Strategy
  • Search with ALL variants
  • Boost results from RV/AV/TS
  • Return corpus + MW definitions
```

---

## Integration Points

### A. Retriever Enhancement

**File**: `src/utils/retriever.py`

**Modifications needed**:

```python
from src.utils.mw_concept_store import MWConceptStore
from src.utils.transliteration import TransliterationHelper

class EnhancedRetriever:
    def __init__(self):
        self.mw = MWConceptStore()
        self.trans = TransliterationHelper()
        # ... existing code
    
    def retrieve(self, query: str, k: int = 5):
        # 1. Generate transliteration variants
        variants = self.trans.normalize_query(query)
        
        # 2. Lookup in MW concept store
        mw_results = []
        for word in query.split():
            result = self.mw.lookup(word)
            if result['found']:
                mw_results.append(result)
        
        # 3. Expand query with MW definitions
        enhanced_query = self.mw.expand_query(query)
        
        # 4. Multi-variant search in Qdrant
        all_results = []
        for variant in [enhanced_query] + variants[:3]:
            results = self.qdrant_client.search(
                query_vector=self.embed_model.encode(variant),
                limit=k
            )
            all_results.extend(results)
        
        # 5. Deduplicate and rank
        unique_results = self._deduplicate(all_results)
        
        # 6. Boost by Vedic references
        if mw_results:
            vedic_refs = self._extract_vedic_refs(mw_results)
            ranked_results = self._boost_by_refs(unique_results, vedic_refs)
        
        # 7. Attach MW context
        for result in ranked_results[:k]:
            result['mw_context'] = mw_results
        
        return ranked_results[:k]
```

---

### B. Streamlit UI Enhancement

**File**: `sanskrit_tutor_web.py`

**Display MW context alongside results**:

```python
def display_results(results):
    for i, result in enumerate(results, 1):
        st.markdown(f"### Result {i}")
        st.write(result['text'])
        st.caption(f"Source: {result['metadata']['title']}")
        
        # Add MW dictionary context
        if result.get('mw_context'):
            with st.expander("📖 Sanskrit Dictionary Context"):
                for mw in result['mw_context']:
                    st.markdown(f"**{mw['primary_key']}** ({mw['devanagari']})")
                    st.write(mw['definitions'][0])
                    st.caption(f"Vedic refs: {', '.join(mw['vedic_refs'][:5])}")
```

---

## Benefits

### 1. Script Bridging
- **Problem**: User queries "सरस्वती" (Devanagari) but corpus has "Sarasvatī" (IAST)
- **Solution**: MW lookup generates all variants → search matches both

### 2. Semantic Expansion
- **Problem**: Query "agni" is ambiguous (fire? god? digestive fire?)
- **Solution**: MW provides definitions → semantic search uses context

### 3. Vedic Grounding
- **Problem**: Generic results without source text attribution
- **Solution**: MW references (RV, YV, AV) → boost relevant corpus chunks

### 4. Bilingual Support
- **Problem**: Hindi/Devanagari queries fail on English-only embeddings
- **Solution**: MW + transliteration layer bridges languages

---

## Performance

| Metric | Value |
|--------|-------|
| Concept store size | 108.5 MB |
| Total entries | 176,146 |
| Lookup keys | 522,880 |
| Average lookup time | < 1ms (O(1) dict lookup) |
| Memory usage | ~150 MB loaded |
| Startup time | ~2 seconds to load JSON |

**Optimization**: Keep concept store loaded in memory (one-time load cost)

---

## Testing

### Test Cases

| Query | Expected Behavior |
|-------|-------------------|
| `"अग्नि पूजा"` | MW finds "agni" → expands to "fire, sacrificial, god" → searches corpus |
| `"Sarasvatī river"` | MW finds "sarasvati" → adds Devanagari variant → matches both scripts |
| `"soma juice"` | MW finds "soma" → adds "moon god", "ritual plant" → semantic boost |
| `"वेद में ऋषि"` | MW finds "veda" → adds refs (RV, YV, AV) → boosts results from those texts |

### Validation Queries
```python
# Test in demo_mw_rag_integration.py
test_queries = [
    "अग्नि पूजा कैसे करें",           # Devanagari
    "Sarasvatī river disappearance",  # IAST + English
    "सोम रस का महत्व",                # Hindi
    "Indra and Agni relationship",   # English
    "वेद में ऋषि",                    # Devanagari
]
```

---

## Next Steps

### Phase 1: Integration (Current)
- ✅ **DONE**: Create MW concept store (176,146 entries)
- ✅ **DONE**: Build integration utility (`mw_concept_store.py`)
- ✅ **DONE**: Create demo showing RAG enhancement
- ⏳ **TODO**: Integrate into `src/utils/retriever.py`
- ⏳ **TODO**: Add MW context display in `sanskrit_tutor_web.py`

### Phase 2: Multilingual Embeddings
- ⏳ **TODO**: Switch to `paraphrase-multilingual-MiniLM-L12-v2`
- ⏳ **TODO**: Re-index corpus with multilingual embeddings
- ⏳ **TODO**: Upload to Qdrant Cloud

### Phase 3: Testing & Validation
- ⏳ **TODO**: Test bilingual queries (Sanskrit/Hindi/English)
- ⏳ **TODO**: Measure retrieval accuracy improvement
- ⏳ **TODO**: User testing with Hindi speakers

---

## Files Created

1. **`parse_monier_williams_concept_store.py`** (370 lines)
   - Parser: mw.txt → JSON concept store
   - Creates lookup index with 522,880 keys

2. **`monier_williams_concept_store.json`** (108.5 MB)
   - Structured concept store with 176,146 entries
   - Includes metadata, concepts, and lookup index

3. **`src/utils/mw_concept_store.py`** (328 lines)
   - Integration utility for RAG
   - MWConceptStore class with lookup/expansion methods

4. **`demo_mw_rag_integration.py`** (200 lines)
   - Demo showing MW + transliteration enhancement
   - Pseudocode for retriever integration

---

## Technical Notes

### MW Dictionary Format
- **Source**: Cologne Digital Sanskrit Lexicon
- **Format**: Pseudo-XML with structured entries
- **Size**: 48 MB (877,322 lines)
- **Entries**: 280,816 dictionary entries
- **Markup**: `<L>` records, `<k1>` headwords, `<s>` Sanskrit, `<ls>` references

### Normalization Strategy
- Remove Vedic accents (`/`, `-`, `\`)
- Lowercase for case-insensitive lookup
- Strip punctuation (`.`, `,`, `।`, `॥`)
- Generate Devanagari ↔ IAST variants

### Lookup Index Design
```python
lookup_index = {
    "sarasvati": "sarasvati",      # Primary key
    "सरस्वति": "sarasvati",         # Devanagari → primary
    "sarasvatī": "sarasvati",      # IAST variant → primary
    "sa/ras—vatI": "sarasvati",    # MW headword → primary
}
```
- **Advantage**: O(1) lookup regardless of input script
- **Size**: 522,880 keys covering all variants

---

## Related Documentation

- **Transliteration**: See `src/utils/transliteration.py`
- **Bilingual Support**: See `CONVERSATIONAL_WORDS_FIX.md`
- **RAG Architecture**: See `SANSKRIT_TUTOR_README.md`
- **Pancavamsa Metadata**: See `PANCAVAMSA_METADATA_FIX.md` (if exists)

---

## References

- **MW Dictionary**: https://www.sanskrit-lexicon.uni-koeln.de/scans/MWScan/2020/web/webtc/
- **indic-transliteration**: https://github.com/sanskrit/indic_transliteration_py
- **Qdrant Vector DB**: https://qdrant.tech/documentation/
- **Sentence Transformers**: https://www.sbert.net/docs/pretrained_models.html

---

**Status**: ✅ MW Concept Store successfully created and ready for RAG integration

**Impact**: Enables bilingual Sanskrit/Hindi queries with proper transliteration and semantic grounding in Vedic texts
