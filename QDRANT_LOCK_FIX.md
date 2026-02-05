# Qdrant Local Lock Warning - Explanation and Solution

## The Warning

```
WARNING: Could not open local Qdrant at vector_store: Storage folder vector_store 
is already accessed by another instance of Qdrant client. If you require concurrent 
access, use Qdrant server instead.. Creating temporary storage.
```

## What This Means

**Qdrant's local file-based storage uses exclusive file locking** - only ONE process can access it at a time.

When you see this warning, it means:
1. The `vector_store/` folder is **locked by another process** 
2. This is usually because:
   - A previous run didn't exit cleanly (e.g., you pressed Ctrl+C)
   - Another terminal still has a Python process holding the lock
   - Stale lock files from crashes

When this happens, the system **falls back to creating a temporary folder** (`vector_store_tmp_...`) which gets deleted, so your data isn't persisted.

## Why You See This Every Time

If you're seeing it repeatedly:
1. **Previous run didn't close properly** → Lock file still exists
2. **Multiple processes running** → Check your terminals for lingering Python processes
3. **Stale lock files** → From crashed indexing runs

## Solutions (in order of ease)

### Solution 1: Use the `--force` flag (EASIEST)
This is the recommended approach:

```bash
python3 src/cli_run.py --local-only --force
```

**What `--force` does:**
- Deletes old `vector_store/` and `local_store/` completely
- Clears lock files
- Starts fresh indexing

### Solution 2: Kill lingering processes

```bash
# Check for Python processes
ps aux | grep python

# Kill any indexing processes
killall python3

# Or more specific
pkill -f "src/cli_run.py"
```

### Solution 3: Manual cleanup

```bash
# Remove the entire vector store
rm -rf vector_store/
rm -rf vector_store_tmp_*

# Remove lock files specifically
rm -rf vector_store/.lock
```

### Solution 4: Wait for process to exit

If another process is using it, Qdrant will eventually timeout and release the lock. Wait 30 seconds and try again.

## The Fix (Now Implemented)

I've updated `src/utils/index_files.py` with automatic retry logic:

```python
while retry_count < max_retries and client is None:
    try:
        client = QdrantClient(path=str(VECTORDB_FOLDER))
        logger.info(f"✅ Successfully connected to local Qdrant")
    except RuntimeError as rte:
        if "already accessed" in error_msg:
            logger.warning(f"⚠️  Local Qdrant locked, retrying...")
            time.sleep(2)  # Wait 2 seconds and retry
```

**What this does:**
- Automatically retries 3 times before giving up
- Waits 2 seconds between retries
- Gives helpful error messages about what might be wrong
- Only falls back to temporary storage if all retries fail

## Prevention: Best Practices

### 1. Always exit cleanly
```bash
# Press Ctrl+C then wait for proper shutdown
Q> exit    # Or Ctrl+D in the REPL
```

### 2. One terminal at a time
- Don't run indexing in multiple terminals simultaneously
- Even reading/querying requires a lock

### 3. Use `--force` when starting fresh
```bash
# After making code changes or indexing new documents
python3 src/cli_run.py --local-only --force
```

### 4. Check for dangling processes
```bash
# If you suspect stuck processes
ps aux | grep "cli_run\|qdrant"
```

## Architecture Context

Your system uses:
- **Local Qdrant**: File-based storage in `vector_store/`
- **File locking**: Unix-style exclusive locks (incompatible with concurrent access)
- **Alternative**: Qdrant Server (runs as separate process, supports concurrency)

If you need concurrent access, you'd need to set up Qdrant Server instead of local storage.

## Related Issues

This is a known limitation of file-based databases:
- SQLite has similar issues
- LevelDB has similar issues
- PostgreSQL/Redis don't have this problem (they're server-based)

## Troubleshooting Flowchart

```
See warning?
├─ Try --force flag first
│  ├─ Works? → Done!
│  └─ Fails? → Check below
├─ Run: ps aux | grep python
│  ├─ See running process? → Kill it
│  └─ None running? → Clean up files
├─ rm -rf vector_store/ vector_store_tmp_*
├─ Retry indexing
│  ├─ Works? → Done!
│  └─ Still fails? → Restart terminal/machine
```

## Questions?

- **Is this a bug?** No, it's expected behavior for file-based storage
- **Will the `--force` approach lose data?** Only re-indexes documents (source PDFs are kept)
- **Why not use Qdrant Server?** More complex setup, but eliminates lock issues
- **Should I be worried?** No - it's just a storage implementation detail
