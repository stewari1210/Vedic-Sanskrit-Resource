# Source Boosting Fix for Proper Noun Queries

## Problem Identified

When asking "Who is Sudas?", the RAG was returning information about **Sudas Paijavana of Iksvakus** (from a Pancavamsa Brahmana footnote) instead of the famous **Sudas of Bharatas/Trtsus** (from RV 7.18 - Battle of Ten Kings).

### Why This Happened

1. **Two different Sudas figures exist:**
   - Sudas of Bharatas/Trtsus (RV 7.18) - **THE famous one** - 35 mentions in Rigveda
   - Sudas Paijavana of Iksvakus (Pancavamsa Brahmana footnote) - less famous, secondary reference

2. **BM25 keyword search ranked the footnote HIGHER:**
   - Pancavamsa footnote: Dense prose with explicit statement "Sudas Paijavana... king of Iksvakus"
   - RV 7.18: Poetic verses, Bharata/Trtsu association is more implicit
   - Result: Footnote appeared at top of results despite being secondary source

3. **Log evidence:**
   ```
   [2026-02-01 14:39:46,290: INFO: retriever]: HybridRetriever: BM25 top result: 
   1 This tale is apparently shortened and by consequence incomprehensible...
   ```
   This is from Pancavamsa Brahmana, NOT Rigveda!

## Solution Implemented

Added **automatic source boosting** based on proper noun database (lines 612-664 in `src/utils/retriever.py`):

### How It Works

1. **Detect proper nouns** in query (e.g., "Sudas")

2. **Check proper_noun_variants.json** for source priority:
   ```json
   "Sudas": {
     "sources": {
       "Griffith-Rigveda": 35,  ← Primary source (most mentions)
       "Griffith-Yajurveda": 0
     }
   }
   ```

3. **Boost primary sources:**
   - **Primary source documents (Rigveda): 2x score boost** ✅
   - **Commentary/footnote documents (Brahmana): 0.5x score downrank** ⬇️

4. **Re-sort results** by new scores

### Code Added

```python
# BOOST PRIMARY SOURCES based on proper noun database
proper_nouns = self._extract_proper_nouns(query)

if proper_nouns:
    from src.utils.proper_noun_variants import get_proper_noun_context
    
    # Check each proper noun for source priority
    primary_sources = set()
    for noun in proper_nouns:
        metadata = get_proper_noun_context(noun)
        if metadata and 'sources' in metadata:
            sources_dict = metadata['sources']
            # Find source with highest occurrence count
            max_count = max(sources_dict.values())
            for source_name, count in sources_dict.items():
                if count == max_count and count > 0:
                    # Map to filename patterns
                    if 'Rigveda' in source_name:
                        primary_sources.add('rigveda')
                    elif 'Yajurveda' in source_name:
                        primary_sources.add('yajurveda')
    
    if primary_sources:
        logger.info(f"🎯 Detected proper nouns {proper_nouns} - boosting primary sources: {primary_sources}")
        
        for content_hash in doc_scores:
            doc = seen_content[content_hash]
            filename = doc.metadata.get('filename', '').lower()
            
            is_primary = any(ps in filename for ps in primary_sources)
            is_commentary = any(term in filename for term in ['brahmana', 'commentary'])
            
            if is_primary and not is_commentary:
                doc_scores[content_hash] *= 2.0  # BOOST
            elif is_commentary and not is_primary:
                doc_scores[content_hash] *= 0.5  # DOWNRANK
```

## Expected Behavior After Fix

### Before Fix ❌
```
Query: "Who is Sudas?"
Top result: Pancavamsa Brahmana footnote → "Sudas Paijavana, king of Iksvakus"
Result: Wrong/incomplete answer focusing on less famous figure
```

### After Fix ✅
```
Query: "Who is Sudas?"
Top results: 
  1. RV 7.18 (Boosted 2x) → Sudas of Trtsus/Bharatas, Battle of Ten Kings
  2. RV 7.19 (Primary source) → More about Sudas and Indra
  3. Pancavamsa footnote (Downranked 0.5x) → Secondary reference to Iksvaku Sudas

Result: Correct answer prioritizing famous Bharata Sudas, may mention Iksvaku variant as secondary
```

## Files Modified

- ✅ `src/utils/retriever.py` (Lines 612-664)
  - Added proper noun detection
  - Added automatic source priority detection from proper_noun_variants.json
  - Added 2x boost for primary sources
  - Added 0.5x downrank for commentaries/footnotes
  - Added detailed logging

## Testing Required

1. **Clear cache:**
   ```bash
   find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
   pkill -f streamlit
   ```

2. **Restart Streamlit:**
   ```bash
   streamlit run sanskrit_tutor_frontend.py
   ```

3. **Test query:**
   - Query: `"Who is Sudas?"`
   - Expected logs:
     ```
     🎯 Detected proper nouns ['Sudas'] - boosting primary sources: {'rigveda'}
     🎯 Boosted primary source: rigveda-griffith... (score X → 2X)
     ⬇️  Downranked commentary: pancavamsa_brahmana... (score Y → 0.5Y)
     ```

4. **Verify answer:**
   - Should mention **Sudas of Bharatas/Trtsus** as primary
   - Should mention **Battle of Ten Kings** (RV 7.18)
   - May mention **Vasistha** as his priest
   - May mention Iksvaku Sudas as **secondary/less famous** figure

## Known Limitations

1. **Citation format still shows "Passage N"** instead of "RV 7.18.15" - separate issue to fix
2. **Only works for proper nouns in database** - if a name isn't in proper_noun_variants.json, no boosting occurs
3. **Assumes highest mention count = primary source** - may not always be true for comparative queries

## Rollback (if needed)

The fix is isolated to lines 612-664 in `src/utils/retriever.py`. Can be reverted with:
```bash
git diff src/utils/retriever.py
git checkout src/utils/retriever.py  # if needed
```

## Next Steps

- [ ] Test with Sudas query
- [ ] Test with Divodasa query (should boost Rigveda)
- [ ] Test with Sarasvati vinasana query (should still boost Pancavimsa as before)
- [ ] Fix citation formatting to show "RV 7.18.15" instead of "Passage 4"
