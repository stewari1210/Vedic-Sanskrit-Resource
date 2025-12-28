# Local-Griffith Branch

## Overview
This branch contains a RAG system using **Griffith's literal translations only** of:
- Rigveda (Griffith)
- Yajurveda (Griffith)

## Philosophy
**Griffith's Approach**: Literal, scholarly translations that preserve:
- Original Sanskrit terminology
- Historical and cultural context
- Archaeological and linguistic accuracy
- Academic rigor

This provides a **consistent literal interpretation** across both Vedic texts, unlike mixing with Sharma's spiritual interpretations.

## Files Used
- `griffith-rigveda_COMPLETE_english_with_metadata.txt`
- `yajurveda-griffith_COMPLETE_english_with_metadata.txt`

## Key Features
✅ Proper noun variant expansion (Bharatas ↔ Trtsus, Vasistha variants, etc.)
✅ --debug flag for detailed retrieval information
✅ 50+ geographic locations (rivers, mountains, regions)
✅ Historical accuracy (Sudas-Puru relationship, Battle of Ten Kings context)
✅ Query expansion for location and tribal queries

## Usage

### Index and Query
```bash
python src/cli_run.py --files griffith-rigveda_COMPLETE_english_with_metadata.txt \
                               yajurveda-griffith_COMPLETE_english_with_metadata.txt \
                               --force
```

### With Debug Mode
```bash
python src/cli_run.py --files griffith-rigveda_COMPLETE_english_with_metadata.txt \
                               yajurveda-griffith_COMPLETE_english_with_metadata.txt \
                               --no-cleanup-prompt --debug
```

### Using run_rag.sh
```bash
./run_rag.sh --files griffith-rigveda_COMPLETE_english_with_metadata.txt \
                      yajurveda-griffith_COMPLETE_english_with_metadata.txt \
                      --debug
```

## Differences from local-consolidated
| Aspect | local-consolidated | local-griffith |
|--------|-------------------|----------------|
| Translations | 4 (Sharma RV/YV + Griffith RV/YV) | 2 (Griffith RV/YV only) |
| Philosophy | Mixed spiritual + literal | Consistent literal |
| Proper Nouns | ~43,706 occurrences | ~18,000 occurrences (Griffith only) |
| Use Case | Comparative study | Pure literal interpretation |

## Branch History
- Created from `local-consolidated` (2025-12-27)
- Removed Sharma translations for consistency
- Cleaned `proper_noun_variants.json` to Griffith-only data
- Preserved all technical improvements (debug mode, expanded locations, etc.)

## Related Branches
- `local-consolidated`: All 4 translations (backup/comparative study)
- `local-processing`: Original Griffith RV only (archived)
- `main`: Production branch
