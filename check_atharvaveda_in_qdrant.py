"""
Diagnose which corpora are present in the Qdrant Cloud collection, by SCROLLING
and inspecting payloads client-side — no server-side filter, so it works even
though the collection has no payload index on `veda` (which is the real reason
the earlier filtered check returned 400 "Index required but not found").

Run on your Mac (qdrant-client installed, QDRANT_URL/QDRANT_API_KEY set):

    python check_atharvaveda_in_qdrant.py
"""

from collections import Counter

from src.config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME
from qdrant_client import QdrantClient


def _veda_of(payload: dict) -> str:
    """Return the veda value regardless of flat vs nested ('metadata') payload."""
    if not payload:
        return "<none>"
    md = payload.get("metadata", payload)
    return md.get("veda") or md.get("chronology_name") or "<none>"


def main():
    if not (QDRANT_URL and QDRANT_API_KEY):
        print("❌ QDRANT_URL / QDRANT_API_KEY not configured.")
        return

    c = QdrantClient(url=str(QDRANT_URL), api_key=str(QDRANT_API_KEY), timeout=120)
    total = c.count(collection_name=COLLECTION_NAME, exact=True).count
    print(f"Collection '{COLLECTION_NAME}': {total} points total\n")

    veda_counts = Counter()
    nested = flat = 0
    av_sample = None
    offset = None
    scanned = 0
    while True:
        points, offset = c.scroll(
            collection_name=COLLECTION_NAME,
            limit=1000, offset=offset,
            with_payload=True, with_vectors=False,
        )
        for p in points:
            pl = p.payload or {}
            if "metadata" in pl and isinstance(pl["metadata"], dict):
                nested += 1
            else:
                flat += 1
            v = _veda_of(pl)
            veda_counts[v] += 1
            if av_sample is None and isinstance(v, str) and "atharva" in v.lower():
                av_sample = pl
        scanned += len(points)
        if offset is None:
            break

    print(f"Scanned {scanned} points. Payload shape: nested(metadata.*)={nested}, flat={flat}\n")
    print("veda / chronology_name breakdown:")
    for v, n in veda_counts.most_common():
        flag = "  ←AV" if isinstance(v, str) and "atharva" in v.lower() else ""
        print(f"  {n:>6}  {v}{flag}")

    av_total = sum(n for v, n in veda_counts.items()
                   if isinstance(v, str) and "atharva" in v.lower())
    print()
    if av_total:
        md = (av_sample or {}).get("metadata", av_sample or {})
        content = (av_sample or {}).get("page_content", "")[:160].replace("\n", " ")
        print(f"✅ Atharvaveda IS in the collection: {av_total} points.")
        print(f"   exact veda value = {md.get('veda')!r}, payload key = "
              f"{'metadata.veda' if 'metadata' in (av_sample or {}) else 'veda'}")
        print(f"   sample: file={md.get('filename')} | {content}…")
        print("\n→ Next: the collection has NO payload index on that field, so the")
        print("  retriever's server-side filter fails. Run:")
        print("      python create_qdrant_payload_index.py")
        print("  then restart Streamlit.")
    else:
        print("❌ No Atharvaveda points found by scanning every payload.")
        print("   The ingest did not land in this collection. Re-run on this Mac:")
        print("      python ingest_atharvaveda_shaunaka.py --dry-run   # validate")
        print("      python ingest_atharvaveda_shaunaka.py             # upload")
        print("      python build_corpus_lexicon.py                    # rebuild lexicon")
        print("   then restart Streamlit.")


if __name__ == "__main__":
    main()
