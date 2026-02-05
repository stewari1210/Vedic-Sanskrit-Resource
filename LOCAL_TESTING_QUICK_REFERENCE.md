# Quick Reference: Local Vector Store Testing

## TL;DR - Test Mandala 1 Locally in 30 Seconds

```bash
# One command to test everything locally
python3 src/cli_run.py \
  --file Rigveda_Mandala_1.txt \
  --local-only \
  --force

# Then ask questions:
# > Who is Agni?
# > What are Vedic fire rituals?
# > exit
```

## CLI Flags Reference

| Flag | Effect | Use Case |
|------|--------|----------|
| `--file PATH` | Process single file | Test one Vedic text |
| `--files PATH1 PATH2` | Process multiple files | Index multiple texts |
| `--local` | Prefer local over cloud | Local testing |
| `--local-only` | **FORCE local, ignore cloud creds** | Safe testing, offline work |
| `--force` | Delete & rebuild vector store | Fresh indexing |
| `--quiet` | Reduce logging verbosity | Cleaner output |
| `--debug` | Show retrieval details | Troubleshooting |

## What Gets Created

### Local Storage (After Running)
```
vector_store/ancient_history/     ← Vector embeddings
local_store/ancient_history/      ← Staging (deleted after processing)
```

### Check It Worked
```bash
# Verify vector store exists
ls -lh vector_store/ancient_history/

# Count indexed chunks
python3 -c "
import pickle
with open('vector_store/ancient_history/docs_chunks.pkl', 'rb') as f:
    print(f'Chunks indexed: {len(pickle.load(f))}')
"
```

## Common Commands

### Test 1: Mandala 1 with Local Storage
```bash
python3 src/cli_run.py --file Rigveda_Mandala_1.txt --local-only --force
```

### Test 2: Multiple Vedic Texts
```bash
python3 src/cli_run.py \
  --files Rigveda_Mandala_1.txt Yajurveda_Sample.txt Atharvaveda_Sample.txt \
  --local-only \
  --force
```

### Test 3: Quiet Mode (Less Logging)
```bash
python3 src/cli_run.py --file Rigveda_Mandala_1.txt --local-only --quiet
```

### Test 4: With Detailed Retrieval Info
```bash
python3 src/cli_run.py --file Rigveda_Mandala_1.txt --local-only --debug
```

### Test 5: Rebuild Existing Index
```bash
python3 src/cli_run.py --file Rigveda_Mandala_1.txt --local-only --force
```

## Troubleshooting Quick Fixes

| Problem | Solution |
|---------|----------|
| "Vector store already exists" | Add `--force` flag |
| "Connection to cloud failed" | Use `--local-only` flag |
| "Too much logging" | Add `--quiet` flag |
| "Can't find chunks" | Add `--force` to rebuild |
| "Embeddings taking forever" | Normal on first run (downloads model) |

## Performance Expectations

| Metric | Time |
|--------|------|
| First indexing (Mandala 1) | 50-70 seconds |
| Subsequent indexing | 10-15 seconds |
| Per-query latency | 100-200ms |
| Model download | One-time, ~400MB |

## Decision Tree: Which Flag to Use?

```
Want to test LOCALLY without cloud?
├─ YES → Use --local-only
└─ NO → Don't use either --local or --local-only

Have Qdrant Cloud credentials set?
├─ YES + no --local-only → Uses cloud
└─ NO → Always uses local
```

## Environment Verification

### Check Python Setup
```bash
python3 --version
# Expected: Python 3.9+ (ideally 3.11+)

python3 -c "import torch; print(f'PyTorch: {torch.__version__}')"
# Expected: 2.0+

python3 -c "import sentence_transformers; print('✓ sentence-transformers OK')"
python3 -c "import langchain; print('✓ langchain OK')"
python3 -c "import qdrant_client; print('✓ qdrant-client OK')"
```

### Verify No Cloud Credentials
```bash
echo "QDRANT_URL: $QDRANT_URL"
echo "QDRANT_API_KEY: $QDRANT_API_KEY"
# Expected: Both empty for pure local testing
```

## After Testing: Next Steps

### If Local Works ✓
→ Ready to move to Phase 2: Sanskrit word segmentation

### What to Test Next
```bash
# Test with different Vedic texts
python3 src/cli_run.py --file library/vedic_texts/*.txt --local-only --force

# Test query varieties
> Questions about concepts (e.g., "What is rita?")
> Questions about deities (e.g., "Who is Mitra?")
> Questions about rituals (e.g., "What is yajna?")
```

## Code Location Reference

| Component | File |
|-----------|------|
| CLI flags | `src/cli_run.py` line 345-354 |
| Function signature | `src/cli_run.py` line 160 |
| Vector store logic | `src/utils/index_files.py` line 203 |
| Main call | `src/cli_run.py` line 453-455 |

## Integration Documentation

- **Full Integration Guide:** `INDIC_NLP_INTEGRATION.md`
- **Testing Guide:** `LOCAL_TESTING_GUIDE.md`
- **Implementation Summary:** `LOCAL_VECTOR_STORE_IMPLEMENTATION_SUMMARY.md`

## Questions?

**Q: Will local mode affect cloud later?**
A: No. Cloud data stays in cloud. Local mode only creates separate local storage.

**Q: Can I switch between local and cloud?**
A: Yes. Different vector stores. Use `--force` when switching to rebuild.

**Q: Is local mode slower than cloud?**
A: For small texts (Mandala 1) → similar speed. For large texts → local might be faster (no network).

**Q: Should I use --local or --local-only?**
A: Use `--local-only` for guaranteed offline operation.

**Q: What if I forget --local-only?**
A: If cloud credentials exist, will attempt cloud. Just run again with `--local-only`.

---

**Last Updated:** 2024  
**Status:** Ready to Use ✓
