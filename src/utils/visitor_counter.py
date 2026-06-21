"""
Persistent visitor counter, backed by Qdrant Cloud.

Streamlit Community Cloud has an ephemeral filesystem and per-session
`st.session_state`, so any local counter resets on redeploy/reboot. This stores
a single counter point in a tiny Qdrant `site_stats` collection (the same
credentials the app already uses), so the tally survives restarts.

Notes:
- read-then-write is NOT atomic; under heavy concurrency a couple of increments
  could be lost. That's fine for a visitor tally.
- Everything degrades gracefully: if Qdrant isn't configured/reachable, the
  functions return None and the UI simply hides the counter.
"""

import uuid
from datetime import datetime
from typing import Optional

from src.helper import logger

STATS_COLLECTION = "site_stats"
_VISIT_POINT_ID = str(uuid.uuid5(uuid.NAMESPACE_URL, "vedic-sanskrit-tutor/visit-counter"))

_CLIENT = None
_DISABLED = False


def _client():
    global _CLIENT, _DISABLED
    if _DISABLED:
        return None
    if _CLIENT is not None:
        return _CLIENT
    try:
        from src.config import QDRANT_URL, QDRANT_API_KEY
        if not QDRANT_URL or not QDRANT_API_KEY:
            _DISABLED = True
            return None
        from qdrant_client import QdrantClient
        from qdrant_client.http.models import VectorParams, Distance
        c = QdrantClient(url=str(QDRANT_URL), api_key=str(QDRANT_API_KEY), timeout=10)
        existing = {x.name for x in c.get_collections().collections}
        if STATS_COLLECTION not in existing:
            # 1-dim dummy vector; we never search, only store the payload count.
            c.create_collection(
                collection_name=STATS_COLLECTION,
                vectors_config=VectorParams(size=1, distance=Distance.DOT),
            )
        _CLIENT = c
        return c
    except Exception as e:
        logger.warning(f"👣 visitor counter: Qdrant unavailable ({e}) — counter hidden.")
        _DISABLED = True
        return None


def _read(c) -> int:
    pts = c.retrieve(collection_name=STATS_COLLECTION, ids=[_VISIT_POINT_ID],
                     with_payload=True)
    if pts:
        return int((pts[0].payload or {}).get("count", 0))
    return 0


def get_visit_count() -> Optional[int]:
    """Current total, or None if the store is unavailable."""
    c = _client()
    if c is None:
        return None
    try:
        return _read(c)
    except Exception:
        return None


def increment_visit_count() -> Optional[int]:
    """Increment by one and return the new total, or None on failure."""
    c = _client()
    if c is None:
        return None
    try:
        from qdrant_client.http.models import PointStruct
        n = _read(c) + 1
        c.upsert(collection_name=STATS_COLLECTION, points=[PointStruct(
            id=_VISIT_POINT_ID, vector=[0.0],
            payload={"count": n, "updated_at": str(datetime.now())})])
        return n
    except Exception as e:
        logger.warning(f"👣 visitor counter increment failed: {e}")
        return None
