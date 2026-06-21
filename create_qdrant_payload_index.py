"""
Create keyword payload indexes on the Qdrant Cloud collection so the retriever
can filter by corpus server-side.

WHY: Qdrant rejects a filter on an un-indexed payload field with
  400 "Index required but not found for <field> of type [keyword]".
The collection was created without payload indexes, so `metadata.veda` filtering
fails. This one-time script adds the indexes. Safe to re-run (already-exists is
treated as success).

Run on your Mac (qdrant-client installed, QDRANT_URL/QDRANT_API_KEY set):

    python create_qdrant_payload_index.py
"""

from src.config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

# Fields the retriever filters/may filter on. KEYWORD = exact-match string index.
FIELDS = [
    "metadata.veda",
    "metadata.chronology_name",
    "metadata.filename",
]


def main():
    if not (QDRANT_URL and QDRANT_API_KEY):
        print("❌ QDRANT_URL / QDRANT_API_KEY not configured.")
        return

    c = QdrantClient(url=str(QDRANT_URL), api_key=str(QDRANT_API_KEY), timeout=120)

    for field in FIELDS:
        try:
            c.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name=field,
                field_schema=qm.PayloadSchemaType.KEYWORD,
                wait=True,
            )
            print(f"✅ indexed {field}")
        except Exception as e:
            msg = str(e).lower()
            if "already exists" in msg or "already indexed" in msg:
                print(f"✅ {field} already indexed")
            else:
                print(f"⚠️  {field}: {e}")

    # Confirm the veda filter now works.
    try:
        f = qm.Filter(must=[qm.FieldCondition(
            key="metadata.veda", match=qm.MatchValue(value="atharvaveda_shaunaka"))])
        n = c.count(collection_name=COLLECTION_NAME, count_filter=f, exact=True).count
        print(f"\nFilter test — metadata.veda=atharvaveda_shaunaka → {n} points.")
        if n:
            print("✅ Server-side corpus filtering is live. Restart Streamlit.")
        else:
            print("⚠️  Index works but 0 AV points — AV isn't in this collection. "
                  "Run check_atharvaveda_in_qdrant.py, then re-ingest if needed.")
    except Exception as e:
        print(f"⚠️  Filter test failed: {e}")


if __name__ == "__main__":
    main()
