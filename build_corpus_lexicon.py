#!/usr/bin/env python3
"""
Build a corpus-derived lexicon: every Devanagari token in local_store mapped
to normalized ASCII, so sloppy Latin queries (Ikshvaku / Iksvaku / ikṣvāku)
can be expanded to the exact surface forms that occur in the corpus —
including sandhi-fused ones (यस्येक्ष्वाकु...).

Output: vector_store/<collection>/corpus_lexicon.pkl
    {"primary":  {ascii_norm: [devanagari tokens...]},
     "skeleton": {ascii_norm_sh_collapsed: [devanagari tokens...]}}

Run on Mac after any corpus change:  python build_corpus_lexicon.py
"""
import pickle
import re
import sys
from collections import defaultdict
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
load_dotenv(PROJECT_ROOT / ".env", override=True)

from indic_transliteration import sanscript
from src.config import LOCAL_FOLDER, VECTORDB_FOLDER, COLLECTION_NAME
from src.utils.devanagari_lexical import normalize_iast_ascii

DEV_TOKEN = re.compile(r"[ऀ-ॿ]+")

# 1. Collect unique Devanagari tokens from all markdown in local_store
tokens = set()
md_files = sorted(Path(LOCAL_FOLDER).rglob("*.md"))
for md in md_files:
    for tok in DEV_TOKEN.findall(md.read_text(encoding="utf-8")):
        if len(tok) >= 3:
            tokens.add(tok)
print(f"📚 {len(md_files)} files -> {len(tokens):,} unique Devanagari tokens")

# 2. Transliterate each token to IAST, normalize to ASCII
primary = defaultdict(set)
skeleton = defaultdict(set)
for tok in tokens:
    iast = sanscript.transliterate(tok, sanscript.DEVANAGARI, sanscript.IAST)
    norm = normalize_iast_ascii(iast)
    if len(norm) < 3:
        continue
    primary[norm].add(tok)
    skeleton[norm.replace("sh", "s")].add(tok)

lexicon = {"primary": {k: sorted(v) for k, v in primary.items()},
           "skeleton": {k: sorted(v) for k, v in skeleton.items()}}

out = Path(VECTORDB_FOLDER) / str(COLLECTION_NAME) / "corpus_lexicon.pkl"
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "wb") as f:
    pickle.dump(lexicon, f)
print(f"💾 {len(lexicon['primary']):,} primary / {len(lexicon['skeleton']):,} skeleton keys -> {out}")

# 3. Sanity checks
from src.utils.devanagari_lexical import lexicon_lookup
for probe in ("ikshvaku", "iksvaku", "sudas", "sarasvati", "vasishtha"):
    hits = lexicon_lookup(probe, lexicon)
    print(f"🔎 '{probe}' -> {len(hits)} surface forms: {hits[:4]}")
