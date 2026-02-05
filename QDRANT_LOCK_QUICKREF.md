# Qdrant Lock Error - Quick Fix

## TL;DR

**The warning means:** Another process is still holding the Qdrant database lock

**Quick fixes (try in order):**

```bash
# 1. Use --force flag (cleans up & re-indexes)
python3 src/cli_run.py --local-only --force

# 2. Kill any lingering Python processes
pkill -f "cli_run"

# 3. Manual cleanup + retry
rm -rf vector_store vector_store_tmp_*
python3 src/cli_run.py --local-only --force

# 4. Wait 30 seconds and try again
sleep 30 && python3 src/cli_run.py --local-only --force
```

## Why It Happens

Qdrant's local file storage uses **exclusive locking** - only one process at a time.

| Scenario | Solution |
|----------|----------|
| Previous run crashed | Use `--force` to clean |
| Multiple terminals open | Use one terminal only |
| Ctrl+C pressed mid-run | Wait 10 sec, try again |
| Stale lock files | `rm -rf vector_store/` |

## What NOT to Do

❌ Don't delete `local_store/` - that has your documents  
❌ Don't try to run indexing in 2 terminals simultaneously  
❌ Don't force-kill Python if you have unsaved work elsewhere  

## What DOES Get Cleaned

✅ Using `--force` cleans: `vector_store/` and `local_store/` temp files  
✅ Your source PDFs in `library/vedic_texts/` are **never** deleted  
✅ Everything re-indexes from source documents

## Read Full Explanation

See: `QDRANT_LOCK_FIX.md` for detailed information
