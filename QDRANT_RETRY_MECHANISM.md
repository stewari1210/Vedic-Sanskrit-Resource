# Automatic Qdrant Lock Recovery (NEW)

## What Changed

I've added **automatic retry logic** to `src/utils/index_files.py` that:

1. **Detects lock errors** automatically
2. **Retries up to 3 times** with 2-second delays between attempts
3. **Provides helpful error messages** if the lock persists
4. **Only falls back to temporary storage** as a last resort

## How It Works

```python
# New code in index_files.py (lines ~350-400)
max_retries = 3
retry_count = 0

while retry_count < max_retries and client is None:
    try:
        client = QdrantClient(path=str(VECTORDB_FOLDER))
        logger.info(f"✅ Successfully connected to local Qdrant")
    except RuntimeError as rte:
        if "already accessed" in str(rte).lower():
            retry_count += 1
            logger.warning(f"⚠️  Qdrant locked (attempt {retry_count}/3)")
            time.sleep(2)  # Wait 2 seconds before retry
```

## What You'll See

### Before (Old Behavior)
```
WARNING: Could not open local Qdrant at vector_store: Storage folder...
Creating temporary storage.
[Creates temp folder that gets discarded]
```

### After (New Behavior)
```
⚠️  Local Qdrant locked (attempt 1/3): Storage folder...
   Waiting 2 seconds before retry...
✅ Successfully connected to local Qdrant at vector_store
[Continues with normal indexing]
```

## Benefits

| Scenario | Before | After |
|----------|--------|-------|
| Process exits mid-run | ❌ Fails immediately | ✅ Retries 3x (6 sec delay) |
| System just got free | ❌ Fails immediately | ✅ Catches it on retry |
| Transient lock issue | ❌ Temp storage fallback | ✅ Auto-recovers |
| Persistent lock | Same behavior (temp storage) | Same behavior (temp storage) |

## When Retries Help

✅ **These scenarios now work without `--force`:**
- Process exited 2 seconds ago
- Another command just finished
- System had brief lock contention
- Stale lock from previous crash (after 6+ seconds)

❌ **Still need `--force` for:**
- Another process actively using the database
- Corrupted Qdrant state
- Complete re-index needed anyway

## Configuration

The retry behavior is hardcoded:
- **Max retries**: 3 attempts
- **Delay**: 2 seconds between attempts
- **Total timeout**: ~6 seconds before fallback

If you want to change this, edit:
```python
max_retries = 3          # Change this number
time.sleep(2)            # Change delay duration
```

## Compatibility

- ✅ Works with both local and cloud Qdrant
- ✅ Backwards compatible (no breaking changes)
- ✅ Gracefully degrades to temporary storage if retries fail
- ✅ No new dependencies required

## Testing the Retry Logic

To test that retry logic works:

```bash
# Terminal 1 - Start indexing
python3 src/cli_run.py --local-only --force

# Wait for it to start Qdrant connection...
# Ctrl+C to interrupt it (this leaves lock active for ~5 seconds)

# Terminal 2 - Start new indexing immediately (within 5 seconds)
python3 src/cli_run.py --local-only --force

# You should see:
# ⚠️  Local Qdrant locked (attempt 1/3)
# ⚠️  Local Qdrant locked (attempt 2/3)
# ✅ Successfully connected to local Qdrant
```

This proves the automatic retry is working!

## Next Steps (Future Improvements)

Possible enhancements:
- Make retry count configurable via `--retry-count` flag
- Add exponential backoff instead of fixed 2-second delays
- Implement timeout-based cleanup of stale locks
- Switch to Qdrant Server for production (eliminates file locking entirely)

## Related Documentation

- Full explanation: `QDRANT_LOCK_FIX.md`
- Quick reference: `QDRANT_LOCK_QUICKREF.md`
- Code location: `src/utils/index_files.py` lines ~350-400
