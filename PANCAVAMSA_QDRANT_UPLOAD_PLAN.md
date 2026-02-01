# Pancavamsa Brahmana - Qdrant Upload Plan

## Current Status

### Existing Collections in Qdrant Cloud
- **Collection Name**: `ancient_history`
- **Current Documents**: 
  - Rigveda (Griffith translation)
  - Satapatha Brahmana (5 parts, split books)
  - Macdonell Vedic Grammar
  - Griffith Ramayana
- **Current Chunk Count**: ~22,000 chunks

### New Document to Add
- **Name**: Pancavamsa Brahmana (W. Caland translation, 1931)
- **Source**: `local_store/prose_vedas/pancavamsa_brahmana/`
- **Text File**: `pancavamsa_brahmana.txt` (1.5 MB, 41,384 lines)
- **Estimated Chunks**: ~2,000-3,000 (depending on chunk size)
- **Expected Total After Upload**: ~24,000-25,000 chunks

## Citation Format

The Pancavamsa Brahmana uses: **PBr. X.Y.Z** (Book.Section.Verse)

### Examples
- PBr. X. 3.2 → PB 10.3.2
- PBr. IV. 2. 10 → PB 4.2.10
- PBr. XXI. 1. 1 → PB 21.1.1

**Status**: ✅ Citation pattern added to `citation_enhancer.py`

## Upload Process Steps

### 1. Verify Local Vector Store Has PB
```bash
# Check if local_store has PB indexed
python3 -c "from src.utils.index_files import load_documents_with_metadata; docs = load_documents_with_metadata('local_store'); print(f'Total docs: {len(docs)}')"
```

### 2. Create Qdrant Collection (if not exists)
```bash
# Or use existing "ancient_history" collection
python3 scripts/create_qdrant_collection.py --collection ancient_history --recreate false
```

### 3. Index PB to Qdrant
```bash
# Add PB to existing collection
python3 upload_vector_to_Qdrant.py --collection ancient_history --recreate false
```

### 4. Verify Upload
```bash
# Check chunk count in Qdrant
python3 -c "
from qdrant_client import QdrantClient
client = QdrantClient(
    url='https://014ab865-1a9a-4387-8672-182fbfbb2dba.us-east4-0.gcp.cloud.qdrant.io:6333',
    api_key='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.L9k9OYrFXW0loBo8w1LXORHr5oG8cLbjN4Fg3w2dWOw'
)
collection = client.get_collection('ancient_history')
print(f'Total points: {collection.points_count}')
"
```

## Implementation Notes

### upload_vector_to_Qdrant.py Updates Needed

The existing script needs to:

1. **Load from .env instead of hardcoded credentials**
   ```python
   from dotenv import load_dotenv
   import os
   
   load_dotenv()
   QDRANT_URL = os.getenv('QDRANT_URL')
   QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
   ```

2. **Support --recreate flag**
   - `--recreate true` - Delete and recreate collection (full reindex)
   - `--recreate false` - Add to existing collection (append mode)

3. **Handle PB-specific metadata**
   - Preserve `source` field (should be "Pancavamsa Brahmana")
   - Preserve `translator` field
   - Ensure citations are in proper format

4. **Batch upload with progress**
   - Upload in batches of 1000 points
   - Show progress: "Uploaded X/Y points"
   - Handle timeout gracefully

### Citation Enhancement

The citation_enhancer.py now supports:
- ✅ Rigveda Griffith: `[01-033]` → `RV 1.33`
- ✅ Rigveda Sharma: `RV X.Y` → `RV X.Y`
- ✅ Yajurveda Griffith: `VSKSE X.Y` → `YV X.Y`
- ✅ Yajurveda Sharma: `YV X.Y` → `YV X.Y`
- ✅ Satapatha Brahmana: `SB X.Y.Z` → `SB X.Y.Z`
- ✅ **Pancavamsa Brahmana**: `PBr. X.Y.Z` → `PB X.Y.Z` (NEW)

## Expected Outcome

After uploading Pancavamsa Brahmana to Qdrant:

1. **Enhanced RAG Capabilities**
   - Queries about Samaveda will now retrieve PB content
   - Queries about Vedic rituals will have more detailed responses
   - Cross-references between SB and PB will be possible

2. **Improved Citation Accuracy**
   - "PB 10.3.2" instead of "Passage 1234"
   - Full traceability to source document

3. **Better Semantic Search**
   - More comprehensive Brahmana content for ritual queries
   - Expanded vocabulary for philosophical concepts
   - More proper nouns for entity recognition

## Verification Checklist

- [ ] PB text file exists: `local_store/prose_vedas/pancavamsa_brahmana/pancavamsa_brahmana.txt`
- [ ] PB metadata exists: `local_store/prose_vedas/pancavamsa_brahmana/pancavamsa_brahmana_metadata.json`
- [ ] Citation pattern added to `citation_enhancer.py` (PBr. X.Y.Z → PB X.Y.Z)
- [ ] Citation pattern tested with sample PBr citations
- [ ] Roman numeral converter implemented in citation_enhancer
- [ ] upload_vector_to_Qdrant.py uses .env credentials
- [ ] upload_vector_to_Qdrant.py supports --recreate flag
- [ ] Qdrant collection "ancient_history" exists
- [ ] PB indexed to Qdrant without errors
- [ ] Point count verification successful
- [ ] Test query returns PB citations correctly

## Next Steps

1. Review and update `upload_vector_to_Qdrant.py` for production use
2. Test upload with a small batch first
3. Monitor upload progress
4. Verify citations appear in RAG responses
5. Update RAG system to use new PB content
6. Test end-to-end: Query → Retrieve PB → Format citations → Return response
