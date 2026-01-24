import pickle, os, re
from collections import defaultdict

CHUNKS_FILE = 'vector_store/ancient_history/docs_chunks.pkl'
if not os.path.isfile(CHUNKS_FILE):
    print('chunks_file_missing')
    raise SystemExit(1)

with open(CHUNKS_FILE, 'rb') as f:
    chunks = pickle.load(f)

patterns = [r'Ikshvaku', r'Ikshvakus', r'Ikshvauks', r'Ikshvāku', r'Ikshvaku\b', r'Ikshvakus\b']
regex = re.compile('|'.join(patterns), flags=re.IGNORECASE)

matches = []
for idx, c in enumerate(chunks):
    pc = c.page_content
    m = regex.search(pc)
    if m:
        snippet = m.group(0)
        start = max(0, m.start() - 60)
        end = min(len(pc), m.end() + 60)
        excerpt = pc[start:end].replace('\n', ' ')
        matches.append((idx, len(pc), snippet, excerpt, list(c.metadata.keys())))

print('total_matches', len(matches))
for m in matches[:20]:
    idx, length, snippet, excerpt, meta = m
    print('---')
    print('index', idx, 'len', length, 'match', snippet)
    print('meta_keys_sample', meta[:10])
    print('excerpt', excerpt)

# Also do a case-insensitive exact search for 'Ikshvaku' in metadata values
meta_matches = []
for idx, c in enumerate(chunks):
    for k, v in c.metadata.items():
        try:
            if isinstance(v, str) and re.search(r'Ikshvaku', v, flags=re.IGNORECASE):
                meta_matches.append((idx, k, v))
                break
        except Exception:
            continue

print('meta_field_matches', len(meta_matches))
for mm in meta_matches[:10]:
    print(mm)
