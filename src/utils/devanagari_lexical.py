"""
Devanagari lexical rescue for proper-noun retrieval.

Problem: the corpus is Devanagari samhita text. BM25 tokenizes on whitespace,
so a Latin query ("Sudas") can never match, and even a Devanagari query
(सुदास) fails against inflected/sandhi surface forms (सुदासे, सुदाससः, सुदाः).

Fix: map query words to Devanagari surface-form variants via a gazetteer,
then SUBSTRING-scan the chunk corpus. Substrings survive most inflection and
sandhi; explicit variants (e.g. visarga form सुदाः) cover the rest.

This is intentionally independent of sandhi-splitting — a future padapatha
index supersedes it for general vocabulary, but a gazetteer remains the most
reliable route for proper names.
"""
import re
from typing import List, Tuple

from src.helper import logger

# Latin (normalized, lowercase) -> Devanagari surface-form variants.
# Order variants longest-first where it matters for counting.
GAZETTEER = {
    # --- Dasarajna cast (Mandala 7) ---
    "sudas":        ["सुदास", "सुदाः"],
    "sudasa":       ["सुदास", "सुदाः"],
    "dasarajna":    ["दाशराज्ञ", "दशराज्ञ"],
    "dasharajna":   ["दाशराज्ञ", "दशराज्ञ"],
    "vasishtha":    ["वसिष्ठ", "वशिष्ठ"],
    "vasistha":     ["वसिष्ठ", "वशिष्ठ"],
    "paijavana":    ["पैजवन"],
    "trtsu":        ["तृत्सु"],
    "tritsu":       ["तृत्सु"],
    "bharata":      ["भरत"],
    "puru":         ["पूरु"],
    "turvasha":     ["तुर्वश"],
    "turvasa":      ["तुर्वश"],
    "yadu":         ["यदु"],
    "druhyu":       ["द्रुह्यु"],
    "anu":          ["अनु"],
    "bheda":        ["भेद"],
    "purukutsa":    ["पुरुकुत्स"],
    "trasadasyu":   ["त्रसदस्यु"],
    "trksi":        ["तृक्षि", "तृक्ष"],   # Tṛkṣi Trāsadasyava (RV 8.22.7, 6.x)
    "trkshi":       ["तृक्षि", "तृक्ष"],   # ASCII spelling of the same name
    "divodasa":     ["दिवोदास"],
    "dasa":         ["दास"],
    "dasyu":        ["दस्यु"],
    # --- Rivers / places ---
    "parusni":      ["परुष्णी", "परुष्णि"],
    "parushni":     ["परुष्णी", "परुष्णि"],
    "ravi":         ["परुष्णी"],
    "sarasvati":    ["सरस्वती", "सरस्वत"],
    "saraswati":    ["सरस्वती", "सरस्वत"],   # alternate English spelling
    "sindhu":       ["सिन्धु"],
    "yamuna":       ["यमुना"],
    "vipas":        ["विपाश्"],
    "sutudri":      ["शुतुद्री"],
    # --- Deities / sages ---
    "indra":        ["इन्द्र"],
    "agni":         ["अग्नि"],
    "varuna":       ["वरुण"],
    "mitra":        ["मित्र"],
    "soma":         ["सोम"],
    "rudra":        ["रुद्र"],
    "marut":        ["मरुत्", "मरुद्"],
    "maruts":       ["मरुत्", "मरुद्"],
    "ushas":        ["उषस्", "उषा"],
    "usas":         ["उषस्", "उषा"],
    "ashvins":      ["अश्विन"],
    "asvins":       ["अश्विन"],
    "vishnu":       ["विष्णु"],
    "visnu":        ["विष्णु"],
    "brihaspati":   ["बृहस्पति"],
    "brhaspati":    ["बृहस्पति"],
    "brahmanaspati": ["ब्रह्मणस्पति"],
    "gritsamada":   ["गृत्समद"],
    "grtsamada":    ["गृत्समद"],
    "vishvamitra":  ["विश्वामित्र"],
    "visvamitra":   ["विश्वामित्र"],
    "vritra":       ["वृत्र"],
    "vrtra":        ["वृत्र"],
    # --- Brahmana prose proper nouns (layer 4) ---
    "vinashana":    ["विनशन", "विनश"],
    "vinasana":     ["विनशन", "विनश"],
    "drishadvati":  ["दृषद्वती", "दृषद्वत्"],
    "drshadvati":   ["दृषद्वती", "दृषद्वत्"],
    "sattra":       ["सत्त्र", "सत्र"],
    "panchavimsa":  ["पञ्चविंश"],
    "pancavimsa":   ["पञ्चविंश"],
    "tandya":       ["ताण्ड्य"],
    "videha":       ["विदेह"],
    "mathava":      ["माथव"],
    "harishchandra":["हरिश्चन्द्र"],
    "haricandra":   ["हरिश्चन्द्र"],
    "shunahshepa":  ["शुनःशेप"],
    "sunahsepa":    ["शुनःशेप"],
    # --- SB (Shatapatha Brahmana) key proper nouns ---
    "videgha":      ["विदेघ"],              # Videgha Mathava — personal name in SB 1.4.1
    "sadanira":     ["सदानीर", "सदनीर"],    # river (Gandak) = eastern limit of Aryan culture in SB
    "sadaniri":     ["सदानीर", "सदनीर"],
    "janaka":       ["जनक"],                # king of Videha (SB)
    "yajnavalkya":  ["याज्ञवल्क्य"],
    "yajnavalky":   ["याज्ञवल्क्य"],
    "pravahana":    ["प्रवाहण"],            # Pravahana Jaivali — eastern king (SB 3.1.2)
    "jaivali":      ["जैवलि"],
    "shatapatha":   ["शतपथ"],
    "madhyandina":  ["माध्यन्दिन"],
    "kosala":       ["कोसल"],               # eastern region (SB)
    "kuru":         ["कुरु"],               # NW region (contrasts with Kosala/Videha)
    "pancala":      ["पञ्चाल"],
    "panchala":     ["पञ्चाल"],
    "gandhara":     ["गन्धार"],
    "magadha":      ["मगध"],
    # --- AB (Aitareya Brahmana) key proper nouns ---
    "janamejaya":   ["जनमेजय"],
    "ambarisha":    ["अम्बरीष"],
    # Harishchandra story (AB 7.13–34)
    "vaidhasa":     ["वैधस"],               # patronymic: son/descendant of Vidhasa (AB 7.13.1)
    "ikshvaku":     ["ऐक्ष्वाक", "इक्ष्वाकु"],  # solar dynasty lineage tag in AB
    "iksvaku":      ["ऐक्ष्वाक", "इक्ष्वाकु"],
    "rohita":       ["रोहित"],              # Harishchandra's son (AB 7.14–7.17)
    "ajigarta":     ["अजीगर्त"],            # Shunahshepa's father (AB 7.15)
    "suyavasa":     ["सौयवसि"],             # Ajigarta's patronymic in AB
    # AB 8.21 king register
    "pariksit":     ["पारिक्षित", "परीक्षित"],
    "parikshit":    ["पारिक्षित", "परीक्षित"],
    "dausanti":     ["दौःषन्ति"],           # Bharata Dauḥṣanti (AB 8.23)
    # --- AV (Atharvaveda Śaunaka) key proper nouns (layer 3) ---
    "takman":       ["तक्मन्", "तक्मान"],     # fever (AVŚ 5.22 etc.) — the disease personified
    "gandhari":     ["गन्धारि", "गान्धारि"],  # NW people (AVŚ 5.22 takman geography)
    "mujavant":     ["मूजवन्त", "मूजवत्"],    # NW mountain people (AVŚ 5.22) — cf. Mūjavat soma
    "mujavat":      ["मूजवत्", "मूजवन्त"],
    "anga":         ["अङ्ग"],                # eastern people (AVŚ 5.22)
    "magadhi":      ["मगध"],                 # eastern people (AVŚ 5.22); cf. "magadha" above
    "balhika":      ["बल्हिक", "बाल्हिक"],    # NW (Bactria) people (AVŚ 5.22)
    "bahlika":      ["बल्हिक", "बाल्हिक"],
    "mahavrisha":   ["महावृष"],              # NW people (AVŚ 5.22)
    "mahavrsa":     ["महावृष"],
    "kushtha":      ["कुष्ठ"],               # the kuṣṭha healing-plant (AVŚ 5.4, 6.95)
    "kustha":       ["कुष्ठ"],
    "atharvan":     ["अथर्वन्", "अथर्व"],     # the Atharvan priests/seers
    "jangida":      ["जङ्गिड"],              # protective amulet-plant (AVŚ 2.4, 19.34-35)
    "sadanva":      ["सदान्वा", "सदान्व"],    # class of female demons (AVŚ 2.14 etc.)
}

_DEV_WORD = re.compile(r"[ऀ-ॿ]{2,}")
_LAT_WORD = re.compile(r"[A-Za-z][A-Za-z\-]{2,}")

# ── Auto-transliteration ─────────────────────────────────────────────────────
# English words that must NOT be passed to the Sanskrit transliterator.
# (These don't look Sanskrit but share letter patterns that produce garbage.)
_ENGLISH_STOP = {
    "what", "who", "when", "where", "why", "how", "which", "is", "are",
    "was", "were", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "will", "would", "could", "should", "can", "may",
    "might", "must", "shall", "the", "and", "or", "but", "not",
    "in", "on", "at", "of", "for", "to", "from", "with", "by", "about",
    "into", "through", "after", "before", "between", "also", "then",
    "name", "tell", "give", "find", "list", "show", "explain", "describe",
    "king", "queen", "father", "mother", "son", "daughter", "wife",
    "brother", "sister", "ancestor", "descendant", "lord", "sage",
    "this", "that", "these", "those", "they", "their", "his", "her",
    "vedic", "text", "corpus", "passage", "verse", "hymn", "book",
    "chapter", "section", "story", "account", "meaning", "context",
    "known", "called", "said", "mentioned", "described", "found",
}


def _popular_to_iast_variants(token: str) -> List[str]:
    """
    Popular Sanskrit romanization → candidate IAST forms.

    People commonly write:
      sh  → ś  (harishchandra → hariścandra)
      ksh → kṣ (Lakshmi → Lakṣmī)
      ch  → c  (chandra → candra, as a *palatal* unaspirated)
      ri  → ṛ  (Krishna → Kṛṣṇa)

    We return *multiple* candidates because the mapping is ambiguous
    (sh can be ś or ṣ) — the corpus will validate which ones appear.
    """
    t = token.lower().strip()
    if len(t) < 4:
        return [t]

    variants = {t}   # always include the verbatim form

    # Strategy A: sh → ś,  ksh → kṣ  (most common popular convention)
    va = t
    va = va.replace('ksh', 'kṣ')
    va = re.sub(r'sh', 'ś', va)
    variants.add(va)

    # Strategy B: also replace ch → c (palatal stop, not aspirate छ)
    # e.g. "harishchandra" → va="hariśchandra" → vb="hariścandra"  ← correct IAST
    vb = va.replace('ch', 'c')
    variants.add(vb)

    # Strategy C: ri → ṛ (vocalic r, very common in popular spellings)
    vc = vb.replace('ri', 'ṛ')
    variants.add(vc)

    # Strategy D: sh → ṣ (retroflex sibilant — alternate for ṣ in names like
    # Viṣṇu written "Vishnu")
    vd = t.replace('sh', 'ṣ')
    variants.add(vd)

    return list(variants)


def _auto_transliterate_token(token: str) -> List[str]:
    """
    Convert a Latin token to candidate Devanagari forms without any
    manual lookup table.

    Algorithm:
      1. Skip obvious English words.
      2. Generate candidate IAST normalizations (popular romanization rules).
      3. Run indic_transliteration IAST → Devanagari on each candidate.
      4. Return unique, non-trivial Devanagari strings.

    Caller is responsible for corpus validation (checking which forms
    actually occur as substrings in the indexed text).
    """
    t_lower = token.lower().strip()
    if t_lower in _ENGLISH_STOP or len(t_lower) < 4:
        return []

    try:
        from indic_transliteration import sanscript
    except ImportError:
        return []

    candidates: set = set()
    for iast_form in _popular_to_iast_variants(t_lower):
        try:
            dev = sanscript.transliterate(iast_form, sanscript.IAST,
                                          sanscript.DEVANAGARI)
            # Must be non-trivial Devanagari (at least 2 chars, ≥1 Devanagari code point)
            if dev and len(dev) >= 2 and any('ऀ' <= c <= 'ॿ' for c in dev):
                candidates.add(dev)
        except Exception:
            pass

    return list(candidates)

# Topical concept map: English research themes -> Devanagari corpus terms.
# Counts verified against the indexed RV corpus (2026-06-12). These rescue
# THEMATIC queries the same way the gazetteer rescues proper nouns: dense
# embeddings of English abstractions match devotional verse poorly.
THEME_GAZETTEER = {
    "warfare":  ["वज्र", "पृतना", "सेना", "आयुध", "युध्", "वर्म", "इषु", "धन्व", "पुरंदर", "गविष्टि"],
    "war":      ["वज्र", "पृतना", "सेना", "आयुध", "युध्", "वर्म", "इषु", "धन्व", "पुरंदर", "गविष्टि"],
    "battle":   ["पृतना", "युध्", "वज्र", "सेना", "गविष्टि"],
    "battles":  ["पृतना", "युध्", "वज्र", "सेना", "गविष्टि"],
    "weapon":   ["वज्र", "आयुध", "इषु", "धन्व", "इषुधि", "हस्तघ्न"],
    "weapons":  ["वज्र", "आयुध", "इषु", "धन्व", "इषुधि", "हस्तघ्न"],
    "army":     ["सेना", "पृतना"],
    "armies":   ["सेना", "पृतना"],
    "bow":      ["धन्व", "धनुः", "इषुधि"],
    "arrow":    ["इषु", "इषुधि"],
    "arrows":   ["इषु", "इषुधि"],
    "armor":    ["वर्म", "शिप्र", "हस्तघ्न"],
    "armour":   ["वर्म", "शिप्र", "हस्तघ्न"],
    "chariot":  ["रथ"],
    "chariots": ["रथ"],
    "horse":    ["अश्व"],
    "horses":   ["अश्व"],
    "fort":     ["पुरं", "पुरः", "पुरंदर"],
    "forts":    ["पुरं", "पुरः", "पुरंदर"],
    "fortress": ["पुरं", "पुरः", "पुरंदर"],
    "metal":    ["आयस", "अयः", "हिरण्य"],
    "metals":   ["आयस", "अयः", "हिरण्य"],
    "cattle":   ["गव्य", "गविष्टि"],
    "raid":     ["गविष्टि", "गव्य"],
    "raids":    ["गविष्टि", "गव्य"],
    "river":    ["नदी", "सिन्धु", "सरस्वती", "नद्य", "दृषद्वती"],
    "rivers":   ["नदी", "सिन्धु", "सरस्वती", "नद्य", "दृषद्वती"],
    # Brahmana-era concepts (layer 4)
    "sattra":   ["सत्त्र", "सत्र"],
    "vinashana": ["विनशन", "विनश"],
    "sacrifice": ["यज्ञ", "सत्त्र", "होत्र"],
    "ritual":   ["यज्ञ", "सत्त्र", "क्रतु", "विधि"],
    "migration": ["पूर्व", "पूर्वदेश", "विदेह", "माथव"],
    "king":     ["राजन्", "राजा", "क्षत्र", "सम्राट्"],
    "lineage":  ["वंश", "गोत्र", "कुल"],
}

# English stopwords that pass the proper-noun-ish filter; skip lexicon lookup
_SKIP = {"which", "verses", "verse", "describe", "describes", "talk", "talks",
         "about", "what", "where", "when", "tell", "hymn",
         "hymns", "mention", "mentions", "there",
         "this", "that", "with", "from", "does", "have", "veda", "rigveda",
         "mandala", "sanskrit", "their", "story", "meaning"}
# Note: "king", "kings", "river", "rivers", "battle", "history", "lineage",
# "sattra", "sacrifice", "ritual", "migration" removed from _SKIP — they are
# now handled by THEME_GAZETTEER and should expand to Devanagari terms.


def normalize_iast_ascii(s: str) -> str:
    """IAST (or sloppy English) -> plain ASCII. MUST match build_corpus_lexicon."""
    s = s.lower().strip()
    table = {
        "ā": "a", "ī": "i", "ū": "u", "ṝ": "ri", "ṛ": "ri", "ḹ": "li",
        "ḷ": "li", "ṃ": "m", "ṁ": "m", "ḥ": "", "ñ": "n", "ṅ": "n",
        "ṇ": "n", "ṭ": "t", "ḍ": "d", "ś": "sh", "ṣ": "sh",
    }
    for k, v in table.items():
        s = s.replace(k, v)
    # c -> ch (candra -> chandra), preserving existing ch as chh
    s = s.replace("ch", "\x00").replace("c", "ch").replace("\x00", "chh")
    # strip any remaining combining marks / non-alpha
    import unicodedata
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if ch.isascii() and ch.isalpha())


def _sandhi_variants(norm: str) -> List[str]:
    """Initial-vowel sandhi can change/absorb a word's first sound when fused
    with the previous word (a+i->e, a+u->o, a+a->a absorbed)."""
    out = [norm]
    if norm.startswith("i") and len(norm) > 4:
        out.append("e" + norm[1:])          # ikshvaku -> ekshvaku (yasya+i = ye)
    if norm.startswith("u") and len(norm) > 4:
        out.append("o" + norm[1:])
    if norm.startswith("a") and len(norm) > 5:
        out.append(norm[1:])                # initial a absorbed entirely
    return out


_LEXICON = None
_LEXICON_TRIED = False


def _load_lexicon():
    global _LEXICON, _LEXICON_TRIED
    if _LEXICON_TRIED:
        return _LEXICON
    _LEXICON_TRIED = True
    try:
        import pickle
        from pathlib import Path
        from src.config import VECTORDB_FOLDER, COLLECTION_NAME
        p = Path(str(VECTORDB_FOLDER)) / str(COLLECTION_NAME) / "corpus_lexicon.pkl"
        if p.exists():
            with open(p, "rb") as f:
                _LEXICON = pickle.load(f)
            logger.info(f"🪷 Corpus lexicon loaded: {len(_LEXICON['primary']):,} keys")
        else:
            logger.info(f"🪷 No corpus lexicon at {p} (run build_corpus_lexicon.py)")
    except Exception as e:
        logger.warning(f"🪷 Corpus lexicon load failed: {e}")
    return _LEXICON


def lexicon_lookup(word: str, lexicon=None, max_tokens: int = 12,
                   max_keys: int = 6, per_key: int = 4) -> List[str]:
    """Latin word -> Devanagari surface forms found in the corpus.
    Tries exact, prefix, then infix (sandhi-fused compounds), on both the
    primary map and the sh-collapsed skeleton map."""
    lex = lexicon if lexicon is not None else _load_lexicon()
    if not lex:
        return []
    results: List[str] = []
    seen = set()

    def _collect(keys_map, cand, mode):
        matches = []
        if mode == "exact" and cand in keys_map:
            matches = [cand]
        elif mode == "prefix":
            matches = [k for k in keys_map if k.startswith(cand)]
        elif mode == "infix":
            matches = [k for k in keys_map if cand in k]
        matches.sort(key=len)  # shortest keys = closest to the bare word
        for k in matches[:max_keys]:
            for tok in keys_map[k][:per_key]:
                if tok not in seen:
                    seen.add(tok)
                    results.append(tok)

    norm = normalize_iast_ascii(word)
    if len(norm) < 4:
        return []
    cands = _sandhi_variants(norm)
    skel_cands = [c.replace("sh", "s") for c in cands]

    for mode in ("exact", "prefix", "infix"):
        for c in cands:
            _collect(lex["primary"], c, mode)
        for c in skel_cands:
            _collect(lex["skeleton"], c, mode)
        if len(results) >= max_tokens:
            break
    return results[:max_tokens]


def query_terms(query: str, deep: bool = False) -> List[str]:
    """Devanagari search terms implied by the query (both scripts).
    deep=True widens the lexicon expansion (for exhaustive concordance).

    Pipeline per Latin token (short-circuits when a stage returns results):
      1. THEME_GAZETTEER  — English concept → Devanagari terms (war, river…)
      2. Manual GAZETTEER — curated proper-noun lookup
      3. Corpus lexicon   — data-derived from indexed Devanagari text
      4. Auto-transliteration — normalize popular romanization → IAST →
         Devanagari; works for any Sanskrit name not in any manual list
    """
    kw = dict(max_tokens=48, max_keys=20, per_key=8) if deep else {}
    terms: List[str] = []
    seen: set = set()

    def _add(new_terms):
        for t in new_terms:
            if t not in seen:
                seen.add(t)
                terms.append(t)

    # Pass Devanagari words in the query through directly
    _add(_DEV_WORD.findall(query))

    for w in _LAT_WORD.findall(query):
        norm = _normalize_latin(w)

        # Stage 1: theme concepts
        theme = THEME_GAZETTEER.get(norm, [])
        if theme:
            _add(theme)
            continue

        # Stage 2: skip list
        if norm in _SKIP:
            continue

        # Stage 3a: manual GAZETTEER (curated proper nouns)
        gaz = GAZETTEER.get(norm, [])
        _add(gaz)

        # Stage 3b: corpus lexicon (built from indexed text — catches
        # inflected/sandhi forms the GAZETTEER doesn't enumerate)
        lex_hits: List[str] = []
        if len(norm) >= 4:
            lex_hits = lexicon_lookup(w, **kw)
            _add(lex_hits)

        # Stage 4: auto-transliteration fallback
        # Runs when GAZETTEER and lexicon both returned nothing, AND the
        # token doesn't look like a common English word.
        # e.g. "harishchandra" → hariścandra → हरिश्चन्द्र (verified in corpus)
        #      "ajigarta"      → ajīgarta   → अजीगर्त
        #      "parikshit"     → pārikṣita → पारिक्षित
        if not gaz and not lex_hits and norm not in _ENGLISH_STOP and len(norm) >= 4:
            auto = _auto_transliterate_token(w)
            if auto:
                logger.info(f"🔤 Auto-transliterate '{w}' → {auto}")
            _add(auto)

    return terms


def _normalize_latin(word: str) -> str:
    import unicodedata
    w = unicodedata.normalize("NFD", word.lower())
    return "".join(c for c in w if unicodedata.category(c) != "Mn").replace("-", "")


_VERSE_LINE_ID = re.compile(r"^(.+?॥ (\d+\.\d+\.\d+) ॥)\s*$", re.M)


def concordance(query: str, docs: list, max_verses: int = 60):
    """Exhaustive scan: EVERY verse in the corpus containing any Devanagari
    term implied by the query. Top-k retrieval cannot answer 'which verses
    mention X' completely; this can. Returns (text_block_or_None, terms)."""
    terms = query_terms(query, deep=True)
    if not terms or not docs:
        return None, terms
    found = {}
    for d in docs:
        content = getattr(d, "page_content", "")
        if not any(t in content for t in terms):
            continue
        for m in _VERSE_LINE_ID.finditer(content):
            line, vid = m.group(1).strip(), m.group(2)
            if vid not in found and any(t in line for t in terms):
                found[vid] = line
    if not found:
        return None, terms

    def _key(v):
        a, b, c = v.split(".")
        return (int(a), int(b), int(c))

    vids = sorted(found, key=_key)
    trunc = " (list truncated)" if len(vids) > max_verses else ""
    body = "\n".join(found[v] for v in vids[:max_verses])
    text = (f"## CONCORDANCE — exhaustive corpus scan\n"
            f"Search terms (surface forms): {', '.join(terms)}\n"
            f"These terms occur in exactly {len(vids)} verse(s) in the indexed "
            f"corpus{trunc}. Complete list:\n{body}")
    logger.info(f"📇 Concordance: terms={terms} -> {len(vids)} verses")
    return text, terms


def devanagari_lexical_hits(query: str, docs: list, top_k: int = 5) -> Tuple[list, List[str]]:
    """Substring-scan `docs` for Devanagari terms implied by `query`.

    Scoring: distinct query terms matched (primary key) + total hit count
    (tiebreaker).  This prevents a high-frequency generic term (e.g. सत्त्र)
    from outranking a rare co-occurrence (e.g. सरस्वत + विनश in PB 25.10).

    Returns (matched_docs_sorted_by_score, terms_used).
    """
    terms = query_terms(query)
    if not terms or not docs:
        return [], terms

    scored = []
    for doc in docs:
        content = getattr(doc, "page_content", "")
        distinct = sum(1 for t in terms if t in content)
        if distinct == 0:
            continue
        total = sum(content.count(t) for t in terms)
        # distinct * 1000 ensures a 2-term match always beats a 1-term match
        # regardless of how many times the single term repeats
        score = distinct * 1000 + total
        scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    hits = [doc for _, doc in scored[:top_k]]
    if hits:
        top_distinct = scored[0][0] // 1000
        logger.info(
            f"🪷 Devanagari lexical: terms={terms} -> {len(scored)} docs matched, "
            f"top distinct_terms={top_distinct} score={scored[0][0]}")
    else:
        logger.info(f"🪷 Devanagari lexical: terms={terms} -> no substring matches")
    return hits, terms
