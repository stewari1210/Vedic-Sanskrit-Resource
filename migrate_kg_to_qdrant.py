"""
One-time backfill: migrate the local Vedic KG JSON into the Qdrant Cloud
collection 'vedic_kg'.

Reads knowledge_store/vedic_relations.json (entity-centric) and upserts every
(subject, relation, object) triple as a payload-only Qdrant point, using the
same deterministic point ids as src/utils/vedic_kg.py — so running this twice
is idempotent (no duplicates) and is safe to re-run.

After migration the running app loads the KG from Qdrant (source of truth) and
the JSON becomes a best-effort local mirror only.

Usage:
    python migrate_kg_to_qdrant.py            # migrate, then verify
    python migrate_kg_to_qdrant.py --dry-run  # show what would be uploaded, no writes
"""

import argparse
import json
import sys

from src.utils import vedic_kg as kg
from src.helper import logger

BATCH = 256


def collect_triples(data: dict) -> list:
    """Flatten the entity-centric JSON into payload dicts (one per triple)."""
    triples = []
    for s_key, ent in data.get("entities", {}).items():
        subject = ent.get("display_name", s_key)
        for f in ent.get("relations", []):
            o_key = kg._norm(f["object"])
            triples.append({
                "id": kg._point_id(s_key, f["relation"], o_key),
                "payload": {
                    "subject": subject,
                    "subject_key": s_key,
                    "relation": f["relation"],
                    "object": f["object"],
                    "object_key": o_key,
                    "citations": f.get("citations", []),
                    "confidence": f.get("confidence", "medium"),
                    "added_at": f.get("added_at", ""),
                },
            })
    return triples


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Parse and report only; do not write to Qdrant.")
    args = ap.parse_args()

    if not kg.KG_PATH.exists():
        logger.error(f"No JSON to migrate at {kg.KG_PATH}")
        sys.exit(1)

    with open(kg.KG_PATH, encoding="utf-8") as f:
        data = json.load(f)

    triples = collect_triples(data)
    n_entities = len(data.get("entities", {}))
    print(f"Source JSON: {n_entities} entities, {len(triples)} triples "
          f"(meta total_facts={data.get('_meta', {}).get('total_facts')})")

    if args.dry_run:
        for t in triples[:10]:
            p = t["payload"]
            print(f"  • {p['subject']} —[{p['relation']}]→ {p['object']}  {p['citations']}")
        print(f"  … ({len(triples)} total) — dry run, nothing uploaded.")
        return

    client = kg._get_qdrant_client()
    if client is None:
        logger.error("Qdrant not configured/reachable. Set QDRANT_URL and "
                     "QDRANT_API_KEY (secrets.toml / .env) and retry.")
        sys.exit(1)

    from qdrant_client.http.models import PointStruct
    points = [PointStruct(id=t["id"], vector=[0.0], payload=t["payload"])
              for t in triples]

    uploaded = 0
    for i in range(0, len(points), BATCH):
        chunk = points[i:i + BATCH]
        client.upsert(collection_name=kg.KG_COLLECTION, points=chunk, wait=True)
        uploaded += len(chunk)
        print(f"  upserted {uploaded}/{len(points)}")

    # Verify
    count = client.count(collection_name=kg.KG_COLLECTION, exact=True).count
    print(f"\n✅ Migration complete. Qdrant '{kg.KG_COLLECTION}' now holds {count} points "
          f"(expected ≥ {len(triples)}).")
    print("The app will now load the KG from Qdrant on startup; JSON is a mirror.")


if __name__ == "__main__":
    main()
