"""
Anukramaṇī seed access — the curated, AUTHORITATIVE layer of the Vedic KG.

The anukramaṇī are the traditional indigenous indices of the Veda: for each
sūkta they record the ṛṣi (seer/composer), the devatā (deity), the meter, and
(via the Bṛhaddevatā / itihāsa tradition) the human patron and legend. Because
they are native Vedic apparatus rather than colonial translations, using them to
ground interpretation is consistent with the project's anti-translator-bias goal.

This module loads knowledge_store/kg_seed.json and exposes:
  • load_seed()                  → the raw seed dict (cached)
  • get_hymn_anukramani(hymn_id) → {rishi, devata, patron, theme, entities} | None
  • format_anukramani_block(meta) → a prompt-ready text block

Hymn ids are "M.SSS" with a 3-digit zero-padded sūkta, e.g. "10.060", "7.018".
"""

import json
from pathlib import Path
from typing import Optional

from src.helper import logger

SEED_PATH = Path(__file__).parent.parent.parent / "knowledge_store" / "kg_seed.json"

_SEED_CACHE: Optional[dict] = None


def load_seed() -> dict:
    """Load (and cache) the curated seed. Returns {} if missing/unreadable."""
    global _SEED_CACHE
    if _SEED_CACHE is not None:
        return _SEED_CACHE
    try:
        with open(SEED_PATH, encoding="utf-8") as f:
            _SEED_CACHE = json.load(f)
    except Exception as e:
        logger.warning(f"📜 anukramaṇī seed not loaded ({e}); KG grounding disabled.")
        _SEED_CACHE = {}
    return _SEED_CACHE


def get_hymn_anukramani(hymn_id: str) -> Optional[dict]:
    """Return the anukramaṇī metadata for a hymn id like '10.060', or None."""
    return load_seed().get("hymns", {}).get(hymn_id)


def format_anukramani_block(meta: dict) -> str:
    """Render hymn metadata as an authoritative prompt block."""
    if not meta:
        return ""
    parts = ["ANUKRAMAṆĪ — traditional (authoritative) metadata for this hymn:"]
    if meta.get("rishi"):
        parts.append(f"  • Ṛṣi (composer): {meta['rishi']}")
    if meta.get("devata"):
        parts.append(f"  • Devatā: {meta['devata']}")
    if meta.get("patron"):
        parts.append(f"  • Patron: {meta['patron']}")
    if meta.get("theme"):
        parts.append(f"  • Theme: {meta['theme']}")
    parts.append("Treat the named patron/figures above as established proper nouns "
                 "of the tradition; do not re-analyse them into common-noun epithets "
                 "unless the text positively contradicts this.")
    return "\n".join(parts) + "\n"
