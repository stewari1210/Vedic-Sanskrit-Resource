import pickle, os
from collections import Counter

CHUNKS_FILE = 'vector_store/ancient_history/docs_chunks.pkl'
print('exists', os.path.isfile(CHUNKS_FILE))
chunks = pickle.load(open(CHUNKS_FILE, 'rb'))
print('total_chunks', len(chunks))
if len(chunks) == 0:
    raise SystemExit(0)

c0 = chunks[0]
print('type0', type(c0))
print('metadata_keys0', list(c0.metadata.keys()))
print('len_content0', len(c0.page_content))
print('sample_metadata0', {k: c0.metadata.get(k) for k in list(c0.metadata)[:10]})

# sample distribution of content lengths (first N)
N = min(2000, len(chunks))
lengths = [len(c.page_content) for c in chunks[:N]]
rounded = [l//50*50 for l in lengths]
print('sample_lengths_counter', Counter(rounded).most_common()[:10])

# check for explicit chunk_size key across first M chunks
M = min(500, len(chunks))
found_keys = set()
chunk_size_key_count = 0
for i, c in enumerate(chunks[:M]):
    if isinstance(c.metadata, dict) and 'chunk_size' in c.metadata:
        chunk_size_key_count += 1
    if isinstance(c.metadata, dict):
        found_keys.update(c.metadata.keys())

print('chunk_size_key_count_first{}_chunks'.format(M), chunk_size_key_count)
print('metadata_keys_union_sample', sorted(list(found_keys)))

# show a sample chunk metadata for a chunk containing 'Divodasa' or 'Trksi' if present
targets = ['Divodasa', 'Trksi', 'Trksis', 'Trkṣi']
found = []
for idx, c in enumerate(chunks):
    pc = c.page_content
    if any(t in pc for t in targets):
        found.append((idx, len(pc), list(c.metadata.keys()), (pc[:200].replace('\n',' ') + '...')))
    if len(found) >= 5:
        break

print('sample_hits', found)
