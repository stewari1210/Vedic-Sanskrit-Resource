import pickle, os, re

CHUNKS_FILE = 'vector_store/ancient_history/docs_chunks.pkl'
if not os.path.isfile(CHUNKS_FILE):
    print('chunks_file_missing')
    raise SystemExit(1)

with open(CHUNKS_FILE, 'rb') as f:
    chunks = pickle.load(f)

patterns = [r'Trksi', r'Trksis', r'Trkṣi', r'Trksi\b', r'Trksis\b']
regex = re.compile('|'.join(patterns), flags=re.IGNORECASE)

matches = []
for idx, c in enumerate(chunks):
    m = regex.search(c.page_content)
    if m:
        snippet = m.group(0)
        pc = c.page_content
        start = max(0, m.start()-80)
        end = min(len(pc), m.end()+80)
        excerpt = pc[start:end].replace('\n', ' ')
        meta = c.metadata
        matches.append((idx, len(pc), snippet, excerpt, meta))

print('total_matches', len(matches))
for idx, length, snippet, excerpt, meta in matches[:20]:
    print('---')
    print('index', idx, 'len', length, 'match', snippet)
    print('title', meta.get('title'))
    print('filename', meta.get('filename'))
    print('source', meta.get('source'))
    print('urls', meta.get('urls'))
    print('other_meta_keys', [k for k in meta.keys() if k not in ('title','filename','source','urls')][:10])
    print('excerpt', excerpt)

# If no matches, also check for variants in proper_noun_variants.json
if not matches:
    import json
    with open('proper_noun_variants.json','r',encoding='utf-8') as f:
        data = json.load(f)
    # search tribes_and_kingdoms
    t = data.get('tribes_and_kingdoms',{})
    if 'Trksi' in t:
        print('\nTrksi entry in variants DB found:')
        print(json.dumps(t['Trksi'], indent=2, ensure_ascii=False))
