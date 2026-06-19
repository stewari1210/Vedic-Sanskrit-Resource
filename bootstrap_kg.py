#!/usr/bin/env python3
"""
Bootstrap vedic_relations.json from pre-existing structured JSON files.

Run ONCE (safe to re-run — add_fact deduplicates):
    python bootstrap_kg.py

Sources used:
  - proper_noun_variants.json  (rich structured data: priests, clans, dynasties, sages)

Facts skipped intentionally:
  - Spelling/transliteration variants  → handled by GAZETTEER, not the KG
  - "Grandson of X" lineage strings    → not a direct has_son; no intermediate node
  - Free-text context blurbs           → too noisy; use LLM extraction from corpus instead
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from src.utils.vedic_kg import add_fact, kg_stats

BASE = Path(__file__).parent


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean_name(val: str) -> str:
    """Strip parenthetical glosses: 'Kuru (Kaurayan = ...)' → 'Kuru'."""
    return val.split("(")[0].strip().rstrip(",").strip()


def _best_cite(data: dict, fallback: str = "proper_noun_variants.json") -> str:
    """Return the most specific citation available in a data dict."""
    for field in ("key_verse", "hymn_reference"):
        val = data.get(field)
        if val and isinstance(val, str):
            # Just grab the RV/SB/AB citation portion, not the parenthetical note
            m = re.search(r"(RV|SB|AB|PB|YV)\s*[\d\.]+", val)
            if m:
                return m.group(0)
            return val[:60]
    return fallback


def _king_of(role: str) -> str | None:
    """
    Extract kingdom from a role string.
    'King of Bharatas (Trtsu-Bharata clan)' → 'Bharatas'
    'Demon King/Antagonist'                  → None
    """
    m = re.match(r"(?:King|Chieftain|Chief)\s+of\s+([A-Za-z\-]+)", role, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


# ── Source 1: proper_noun_variants.json ──────────────────────────────────────

def bootstrap_pnv() -> int:
    path = BASE / "proper_noun_variants.json"
    if not path.exists():
        print(f"  [skip] {path.name} not found")
        return 0

    with open(path, encoding="utf-8") as f:
        d = json.load(f)

    count = 0

    # ── Nested categories: each key maps to a dict of {name: {data}} ──────
    nested_cats = {
        "sages":              "sage",
        "kings_and_heroes":   "king_or_hero",
        "tribes_and_kingdoms": "tribe",
        "rivers_and_geography": "geography",
    }

    for cat, _label in nested_cats.items():
        items = d.get(cat, {})
        if not isinstance(items, dict):
            continue

        for name, data in items.items():
            if not isinstance(data, dict):
                continue

            # Use canonical name if provided (better transliteration)
            canonical = data.get("canonical", name)
            cite = _best_cite(data)

            # priest → is_purohita_of
            priest = data.get("priest")
            if priest and isinstance(priest, str):
                if add_fact(_clean_name(priest), "is_purohita_of", canonical, cite):
                    count += 1

            # clan / dynasty / clan_affiliation → member_of_dynasty
            for field in ("clan", "dynasty", "clan_affiliation"):
                val = data.get(field)
                if val and isinstance(val, str):
                    clean = _clean_name(val)
                    # Normalise "Kuru dynasty" → "Kuru"
                    clean = re.sub(r"\s+dynasty$", "", clean, flags=re.IGNORECASE).strip()
                    if clean and len(clean) > 1:
                        if add_fact(canonical, "member_of_dynasty", clean, cite):
                            count += 1

            # group (e.g. "Saptarishi (Seven Sages)") → member_of_dynasty
            group = data.get("group")
            if group and isinstance(group, str):
                clean_group = _clean_name(group)
                if add_fact(canonical, "member_of_dynasty", clean_group, cite):
                    count += 1

            # role → is_king_of  (only when "King of X" pattern present)
            role = data.get("role", "")
            if isinstance(role, str):
                kingdom = _king_of(role)
                if kingdom:
                    if add_fact(canonical, "is_king_of", kingdom, cite):
                        count += 1

            # lineage → has_father  (only direct "Son of X"; skip grandsons)
            lineage = data.get("lineage", "")
            if isinstance(lineage, str):
                m = re.match(r"[Ss]on of (.+)", lineage)
                if m:
                    parent = _clean_name(m.group(1))
                    if add_fact(canonical, "has_father", parent, cite):
                        count += 1

    # ── Flat tribe/dynasty entries (top-level keys that are dicts not dicts-of-dicts) ──
    flat_tribe_cats = [
        "Purus", "Kurus", "Panchalas", "Trtsus", "Trksi",
        "Magadha", "Krivis", "Turvashas", "Srinjayas", "Somakas", "Keshins",
    ]
    for cat in flat_tribe_cats:
        data = d.get(cat)
        if not isinstance(data, dict) or "canonical" not in data:
            continue
        canonical = data["canonical"]
        cite = _best_cite(data)

        # priest
        priest = data.get("priest")
        if priest and isinstance(priest, str):
            if add_fact(_clean_name(priest), "is_purohita_of", canonical, cite):
                count += 1

        # dynasty / clan
        for field in ("clan", "dynasty"):
            val = data.get(field)
            if val and isinstance(val, str):
                clean = _clean_name(val)
                if clean:
                    if add_fact(canonical, "member_of_dynasty", clean, cite):
                        count += 1

    # ── Hard-coded high-confidence facts from context fields ────────────────
    # These are clearly stated in the JSON context text but can't be parsed generically.
    hardcoded = [
        # Geography — Sarasvati vinashana
        ("Sarasvati", "disappears_at",    "Vinashana",  "PB 25.10.2"),
        ("Sarasvati", "flows_through",    "Kurukshetra","RV 3.023.04"),
        # Tribe mergers / formations
        ("Bharatas",  "allied_with",      "Purus",      "proper_noun_variants.json"),
        ("Trtsus",    "member_of_dynasty","Bharatas",   "proper_noun_variants.json"),
        ("Srinjayas", "allied_with",      "Bharatas",   "proper_noun_variants.json"),
        # Kuru lineage from Trasadasyu context
        ("Trasadasyu","member_of_dynasty","Kuru",       "RV 10.033.04"),
        # Sudas vs Purus — Battle of Ten Kings
        ("Sudas",     "fought",           "Purus",      "RV 7.018.13"),
    ]
    for subj, rel, obj, cite in hardcoded:
        if add_fact(subj, rel, obj, cite):
            count += 1

    return count


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Bootstrapping Vedic Knowledge Graph...")
    print()

    stats_before = kg_stats()
    print(f"Before: {stats_before['total_facts']} facts, {stats_before['total_entities']} entities")
    print()

    n1 = bootstrap_pnv()
    print(f"\n  proper_noun_variants.json → {n1} new facts")

    print()
    stats_after = kg_stats()
    print(f"After:  {stats_after['total_facts']} facts, {stats_after['total_entities']} entities")
    print(f"Net new: {stats_after['total_facts'] - stats_before['total_facts']} facts")
    print()
    print("Top entities by fact count:")
    for entity, cnt in stats_after["top_entities"]:
        print(f"  {entity}: {cnt} facts")
