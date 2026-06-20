"""
Seed the Vedic Knowledge Graph with curated, AUTHORITATIVE facts.

Reads knowledge_store/kg_seed.json and upserts every entry under "facts" into
the KG with provenance='authoritative'. These facts are protected: the
self-building (inferred) extraction can never overwrite or downgrade them, and
an authoritative fact CORRECTS a conflicting inferred singleton.

Idempotent — safe to re-run. Run on a machine with the KG's Qdrant configured
(it also writes the local JSON mirror); without Qdrant it seeds the JSON only.

Usage:
    python seed_kg.py            # seed, then print stats
    python seed_kg.py --dry-run  # show what would be seeded, no writes
"""

import argparse
import json
import sys

from src.utils.anukramani import SEED_PATH
from src.utils.vedic_kg import add_fact, kg_stats
from src.helper import logger


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not SEED_PATH.exists():
        logger.error(f"Seed file not found: {SEED_PATH}")
        sys.exit(1)

    with open(SEED_PATH, encoding="utf-8") as f:
        seed = json.load(f)

    facts = seed.get("facts", [])
    print(f"Seed: {len(facts)} authoritative facts, "
          f"{len(seed.get('hymns', {}))} hymn anukramaṇī entries\n")

    if args.dry_run:
        for fct in facts:
            print(f"  • {fct['subject']} —[{fct['relation']}]→ {fct['object']}  "
                  f"[{fct.get('citation','')}]")
        print("\n(dry run — nothing written)")
        return

    new = 0
    for fct in facts:
        is_new = add_fact(
            subject=fct["subject"],
            relation=fct["relation"],
            obj=fct["object"],
            citation=fct.get("citation", ""),
            confidence="high",
            # Structural facts default to 'authoritative'; legend-derived facts
            # carry "provenance": "itihasa" in the seed.
            provenance=fct.get("provenance", "authoritative"),
        )
        new += int(bool(is_new))

    stats = kg_stats()
    print(f"\n✅ Seeded. New facts added: {new} "
          f"(others already present / merged as authoritative).")
    print(f"KG now: {stats['total_facts']} facts, {stats['total_entities']} entities.")
    print("Authoritative facts are now protected from inferred overwrites.")


if __name__ == "__main__":
    main()
