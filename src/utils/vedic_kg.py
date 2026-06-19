"""
Vedic Knowledge Graph — self-building from RAG query responses.

Design:
  POST-synthesis: extract entity-relationship triples from LLM answers and
                  persist them to knowledge_store/vedic_relations.json.
  PRE-synthesis:  inject known relationships as context so the LLM can
                  make multi-hop inferences ("Trasadasyu is son of Purukutsa
                  who is Ikshvaku → Trasadasyu is also Ikshvaku").

The JSON grows organically with every query. Over time it becomes a full
knowledge graph loadable into NetworkX for multi-hop traversal.

Relation taxonomy
─────────────────
Kinship     : has_son | has_daughter | has_father | has_mother |
              has_brother | has_sister | has_spouse
Lineage     : member_of_dynasty | founded_dynasty | patronymic | epithet
Social role : is_king_of | is_purohita_of | is_disciple_of | is_guru_of
Events      : fought | allied_with | performed_ritual | received_boon
Identity    : same_as   (cross-text identity resolution)
Geography   : located_at | flows_through | associated_with_place |
              originates_from | disappears_at | dwells_on
Attribute   : has_attribute
"""

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.helper import logger

# ── Storage ───────────────────────────────────────────────────────────────────
#
# Backend strategy (2026-06-19 migration):
#   • Qdrant Cloud collection "vedic_kg" is the SOURCE OF TRUTH. It persists
#     across Streamlit Cloud redeploys (the local JSON does not). Each triple is
#     a single payload-only point (1-dim dummy vector — we never vector-search
#     the KG, we look up by exact subject key from the in-memory cache).
#   • Local JSON (knowledge_store/vedic_relations.json) is a BEST-EFFORT MIRROR
#     for offline/local dev and as a backup. On Streamlit Cloud its filesystem
#     is ephemeral, so the mirror write is wrapped in try/except and a failure
#     never breaks the app — Qdrant remains authoritative.
#   • The in-memory _KG_CACHE is unchanged in shape, so query-time reads
#     (get_entity_context) stay in memory with zero per-query Qdrant latency.

KG_PATH = Path(__file__).parent.parent.parent / "knowledge_store" / "vedic_relations.json"

KG_COLLECTION = "vedic_kg"

# Deterministic namespace so the same triple always maps to the same point id
# (re-upserts overwrite rather than duplicate).
_KG_UUID_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "vedic-sanskrit-tutor/vedic_kg")

_KG_CACHE: Optional[dict] = None
_QDRANT_CLIENT = None
_QDRANT_DISABLED = False   # set True after a hard failure so we stop retrying


def _get_qdrant_client():
    """
    Return a cached QdrantClient for the KG collection, or None if Qdrant is
    not configured / unreachable. Creates the collection on first use.
    """
    global _QDRANT_CLIENT, _QDRANT_DISABLED
    if _QDRANT_DISABLED:
        return None
    if _QDRANT_CLIENT is not None:
        return _QDRANT_CLIENT
    try:
        from src.config import QDRANT_URL, QDRANT_API_KEY
        if not QDRANT_URL or not QDRANT_API_KEY:
            logger.info("🕸️  KG: Qdrant not configured — using local JSON only.")
            _QDRANT_DISABLED = True
            return None
        from qdrant_client import QdrantClient
        from qdrant_client.http.models import VectorParams, Distance
        client = QdrantClient(url=str(QDRANT_URL), api_key=str(QDRANT_API_KEY))
        existing = {c.name for c in client.get_collections().collections}
        if KG_COLLECTION not in existing:
            # 1-dim dummy vector with DOT distance: we never search by vector,
            # we only store/retrieve payloads. DOT tolerates zero vectors.
            client.create_collection(
                collection_name=KG_COLLECTION,
                vectors_config=VectorParams(size=1, distance=Distance.DOT),
            )
            logger.info(f"🕸️  KG: created Qdrant collection '{KG_COLLECTION}'")
        _QDRANT_CLIENT = client
        return client
    except Exception as e:
        logger.warning(f"🕸️  KG: Qdrant unavailable ({e}) — falling back to local JSON.")
        _QDRANT_DISABLED = True
        return None


def _point_id(s_key: str, relation: str, o_key: str) -> str:
    """Deterministic UUID for a triple so re-upserts dedup instead of duplicate."""
    return str(uuid.uuid5(_KG_UUID_NAMESPACE, f"{s_key}|{relation}|{o_key}"))


def _upsert_triple_to_qdrant(s_key: str, subject: str, relation: str,
                              obj: str, o_key: str, fact: dict) -> None:
    """Best-effort upsert of one triple as a payload-only Qdrant point."""
    client = _get_qdrant_client()
    if client is None:
        return
    try:
        from qdrant_client.http.models import PointStruct
        client.upsert(
            collection_name=KG_COLLECTION,
            points=[PointStruct(
                id=_point_id(s_key, relation, o_key),
                vector=[0.0],
                payload={
                    "subject": subject,
                    "subject_key": s_key,
                    "relation": relation,
                    "object": obj,
                    "object_key": o_key,
                    "citations": fact.get("citations", []),
                    "confidence": fact.get("confidence", "medium"),
                    "added_at": fact.get("added_at", str(datetime.now())),
                },
            )],
        )
    except Exception as e:
        logger.warning(f"🕸️  KG: Qdrant upsert failed ({e}) — JSON mirror still holds it.")


def _build_kg_from_triples(triples: list) -> dict:
    """
    Reconstruct the entity-centric cache dict from a flat list of triple
    payloads (each: subject, subject_key, relation, object, object_key,
    citations, confidence, added_at). Dynasty membership is derived.
    """
    entities: dict = {}
    for t in triples:
        s_key = t["subject_key"]
        o_key = t.get("object_key") or _norm(t["object"])
        ent = entities.setdefault(s_key, {"display_name": t["subject"], "relations": []})
        ent["relations"].append({
            "relation": t["relation"],
            "object": t["object"],
            "citations": t.get("citations", []),
            "confidence": t.get("confidence", "medium"),
            "added_at": t.get("added_at", ""),
        })
        # Ensure object appears as a node too (object-only nodes keep relations=[])
        entities.setdefault(o_key, {"display_name": t["object"], "relations": []})

    # Rebuild dynasty member index from member_of_dynasty edges
    for s_key, ent in list(entities.items()):
        for fact in ent["relations"]:
            if fact["relation"] == "member_of_dynasty":
                d_key = _norm(fact["object"])
                dyn = entities.setdefault(d_key, {"display_name": fact["object"],
                                                  "relations": []})
                dyn["type"] = "dynasty"
                dyn.setdefault("members", [])
                if s_key not in dyn["members"]:
                    dyn["members"].append(s_key)

    total = sum(len(e.get("relations", [])) for e in entities.values())
    return {
        "_meta": {"created": "qdrant", "total_facts": total,
                  "last_updated": str(datetime.now())},
        "entities": entities,
    }


def _load_from_qdrant(client) -> Optional[dict]:
    """Scroll all KG points and rebuild the cache, or None if collection empty."""
    triples = []
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=KG_COLLECTION,
            with_payload=True, with_vectors=False,
            limit=1000, offset=offset,
        )
        for p in points:
            pl = p.payload or {}
            if "subject_key" in pl and "relation" in pl and "object" in pl:
                triples.append(pl)
        if offset is None:
            break
    if not triples:
        return None
    return _build_kg_from_triples(triples)

VALID_RELATIONS = {
    # Kinship
    "has_son", "has_daughter", "has_father", "has_mother",
    "has_brother", "has_sister", "has_spouse",
    # Lineage
    "member_of_dynasty", "founded_dynasty", "patronymic", "epithet",
    # Social role
    "is_king_of", "is_purohita_of", "is_disciple_of", "is_guru_of",
    # Events
    "fought", "allied_with", "performed_ritual", "received_boon",
    # Identity
    "same_as",
    # Geography — use canonical place names as objects
    "located_at",          # entity's primary location / site (Vinashana, Kurukshetra…)
    "flows_through",       # river passes through a region
    "associated_with_place",  # looser geographic association
    "originates_from",     # source / birth-place
    "disappears_at",       # for rivers that go underground (Sarasvati vinashana)
    "dwells_on",           # people/tribes settled on a river / place
    # Attribute (generic — use a geography relation first if possible)
    "has_attribute",
}

# Relations where (subject, relation) can have AT MOST ONE object.
# A second extraction with different phrasing won't create a duplicate entry.
_SINGLETON_RELATIONS = {
    "has_father", "has_mother",          # biological — exactly one
    "is_king_of",                        # one kingdom per king at any time
    "located_at",                        # canonical site
    "disappears_at",                     # rivers vanish at one canonical point
    "originates_from",                   # one source
}

# Automatic inverse pairs — adding A→B also adds B→A
_INVERSES = {
    "has_son":      "has_father",
    "has_daughter": "has_father",
    "has_father":   "has_son",
    "has_mother":   "has_son",
    "has_brother":  "has_brother",
    "has_sister":   "has_sister",
    "has_spouse":   "has_spouse",
    "same_as":      "same_as",
    "is_disciple_of": "is_guru_of",
    "is_guru_of":   "is_disciple_of",
    "is_purohita_of": None,   # no simple inverse
    "fought":       "fought",
    "allied_with":  "allied_with",
    # Geography — no automatic inverses; place→entity would be noisy
    "located_at":            None,
    "flows_through":         None,
    "associated_with_place": None,
    "originates_from":       None,
    "disappears_at":         None,
    "dwells_on":             None,
}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _norm(name: str) -> str:
    """Stable key: lowercase, underscores, no diacritics."""
    import unicodedata
    s = unicodedata.normalize("NFD", name.lower().strip())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def _load_from_json() -> dict:
    """Load the cache from the local JSON mirror, or an empty KG if absent."""
    try:
        KG_PATH.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    if KG_PATH.exists():
        with open(KG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {
        "_meta": {"created": str(datetime.now()), "total_facts": 0,
                  "last_updated": str(datetime.now())},
        "entities": {},
    }


def _load() -> dict:
    """
    Populate the in-memory cache. Qdrant Cloud is the source of truth; the local
    JSON is a fallback when Qdrant is unconfigured/unreachable or empty.
    """
    global _KG_CACHE
    if _KG_CACHE is not None:
        return _KG_CACHE

    client = _get_qdrant_client()
    if client is not None:
        try:
            kg = _load_from_qdrant(client)
            if kg is not None:
                _KG_CACHE = kg
                logger.info(f"🕸️  KG loaded from Qdrant: {kg['_meta']['total_facts']} "
                            f"facts, {len(kg['entities'])} entities")
                return _KG_CACHE
            # Collection exists but is empty — fall through to JSON (first-run seed).
            logger.info("🕸️  KG: Qdrant collection empty — loading local JSON seed.")
        except Exception as e:
            logger.warning(f"🕸️  KG: Qdrant load failed ({e}) — using local JSON.")

    _KG_CACHE = _load_from_json()
    logger.info(f"🕸️  KG loaded from JSON: {_KG_CACHE['_meta']['total_facts']} facts, "
                f"{len(_KG_CACHE['entities'])} entities")
    return _KG_CACHE


def _save(kg: dict):
    """
    Update meta and persist the JSON mirror (best-effort). Qdrant points are
    upserted incrementally in add_fact, so _save only refreshes the local
    backup — a read-only/ephemeral filesystem must never crash the app.
    """
    global _KG_CACHE
    total = sum(len(e.get("relations", [])) for e in kg["entities"].values())
    kg["_meta"]["total_facts"] = total
    kg["_meta"]["last_updated"] = str(datetime.now())
    _KG_CACHE = kg
    try:
        KG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(KG_PATH, "w", encoding="utf-8") as f:
            json.dump(kg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        # Expected on Streamlit Cloud (ephemeral FS). Qdrant remains authoritative.
        logger.debug(f"🕸️  KG: JSON mirror write skipped ({e}) — Qdrant is source of truth.")


# ── Public write API ──────────────────────────────────────────────────────────

def add_fact(subject: str, relation: str, obj: str, citation: str,
             confidence: str = "high", source_query: str = "",
             _add_inverse: bool = True) -> bool:
    """
    Add one (subject, relation, object) triple to the KG.

    Returns True if the fact was new, False if it already existed.
    Automatically adds inverse relation if defined in _INVERSES.
    """
    if relation not in VALID_RELATIONS:
        logger.warning(f"🕸️  Unknown relation '{relation}' — skipped")
        return False

    kg = _load()
    s_key = _norm(subject)
    o_key = _norm(obj)

    # Ensure entity node exists
    if s_key not in kg["entities"]:
        kg["entities"][s_key] = {"display_name": subject, "relations": []}

    existing = kg["entities"][s_key]["relations"]

    # Dedup by (relation, normalised object)
    for fact in existing:
        if fact["relation"] == relation and _norm(fact["object"]) == o_key:
            # Already stored — merge new citation if different
            cites = fact.setdefault("citations", [fact.get("citation", "")])
            if citation and citation not in cites:
                cites.append(citation)
                _save(kg)
                _upsert_triple_to_qdrant(s_key, subject, relation, obj, o_key, fact)
            return False   # not a new fact

    # Singleton check — for certain relations only one object is valid per subject.
    # A second extraction with different phrasing is treated as a duplicate.
    if relation in _SINGLETON_RELATIONS:
        for fact in existing:
            if fact["relation"] == relation:
                logger.debug(
                    f"🕸️  Singleton skip: {subject} —[{relation}]→ {obj} "
                    f"(already have → {fact['object']})"
                )
                return False

    # New fact
    new_fact = {
        "relation": relation,
        "object": obj,
        "citations": [citation] if citation else [],
        "confidence": confidence,
        "added_at": str(datetime.now()),
    }
    existing.append(new_fact)
    _save(kg)
    _upsert_triple_to_qdrant(s_key, subject, relation, obj, o_key, new_fact)
    logger.info(f"🕸️  +fact: {subject} —[{relation}]→ {obj}  [{citation}]")

    # Dynasty membership index
    if relation == "member_of_dynasty":
        if o_key not in kg["entities"]:
            kg["entities"][o_key] = {"display_name": obj, "type": "dynasty",
                                     "relations": [], "members": []}
        kg["entities"][o_key].setdefault("members", [])
        if s_key not in kg["entities"][o_key]["members"]:
            kg["entities"][o_key]["members"].append(s_key)
        _save(kg)

    # Automatic inverse
    if _add_inverse:
        inv = _INVERSES.get(relation)
        if inv:
            add_fact(obj, inv, subject, citation, confidence, source_query,
                     _add_inverse=False)

    return True


# ── Public read API ───────────────────────────────────────────────────────────

def get_entity_context(entity_names: list, hops: int = 2) -> str:
    """
    Return a formatted KNOWN RELATIONSHIPS block for the given entities.

    hops=1 → direct facts about each entity
    hops=2 → also follows each relation target one level deeper
             (enables: Trasadasyu → father=Purukutsa → dynasty=Ikshvaku)

    Returns "" if nothing is known (clean no-op when KG is empty).
    """
    kg = _load()
    if not kg["entities"]:
        return ""

    lines = []
    seen_facts: set = set()
    frontier = {_norm(e) for e in entity_names if e}

    for _ in range(hops):
        next_frontier: set = set()
        for key in frontier:
            if key not in kg["entities"]:
                continue
            entity = kg["entities"][key]
            display = entity.get("display_name", key)
            for fact in entity.get("relations", []):
                fkey = (key, fact["relation"], _norm(fact["object"]))
                if fkey in seen_facts:
                    continue
                seen_facts.add(fkey)
                cites = ", ".join(fact.get("citations", [fact.get("citation", "?")]))
                lines.append(
                    f"  • {display} —[{fact['relation']}]→ {fact['object']}"
                    + (f"  [{cites}]" if cites else "")
                )
                next_frontier.add(_norm(fact["object"]))
        frontier = next_frontier

    if not lines:
        return ""

    total = kg["_meta"]["total_facts"]
    return (
        f"KNOWLEDGE GRAPH ({total} corpus-grounded facts):\n"
        + "\n".join(lines)
        + "\n"
    )


def kg_stats() -> dict:
    """Return summary stats (entity count, fact count, top entities)."""
    kg = _load()
    entities = kg["entities"]
    top = sorted(entities.items(),
                 key=lambda kv: len(kv[1].get("relations", [])),
                 reverse=True)[:10]
    return {
        "total_facts": kg["_meta"]["total_facts"],
        "total_entities": len(entities),
        "last_updated": kg["_meta"].get("last_updated", "never"),
        "top_entities": [(k, len(v.get("relations", []))) for k, v in top],
    }


# ── LLM-powered fact extraction ───────────────────────────────────────────────

_EXTRACTION_PROMPT = """You are extracting structured facts from a Vedic studies response for a knowledge graph.

RESPONSE TEXT:
{response}

INSTRUCTIONS:
- Extract ONLY facts EXPLICITLY STATED with corpus citations (RV, SB, AB, PB, YV).
- Do NOT infer or hallucinate. Only directly asserted facts with a citation.
- Use consistent English transliteration for ALL entity and place names
  (e.g. "Purukutsa", "Trasadasyu", "Vinashana", "Sarasvati").
- For place names, use the shortest canonical form (e.g. "Vinashana" not
  "the place called Vinashana where the river disappears").

RELATION GUIDE — pick the most specific relation:
  Kinship     : has_son | has_daughter | has_father | has_mother |
                has_brother | has_sister | has_spouse
  Lineage     : member_of_dynasty | founded_dynasty | patronymic | epithet
  Social role : is_king_of | is_purohita_of | is_disciple_of | is_guru_of
  Events      : fought | allied_with | performed_ritual | received_boon
  Identity    : same_as
  Geography   : located_at | flows_through | associated_with_place |
                originates_from | disappears_at | dwells_on
  Attribute   : has_attribute  ← use ONLY if no geography/kinship/etc. relation fits

GEOGRAPHY EXAMPLES:
  "Sarasvati disappears at Vinashana" → subject=Sarasvati relation=disappears_at object=Vinashana
  "Purus dwelt on the banks of Sarasvati" → subject=Purus relation=dwells_on object=Sarasvati
  "Sarasvati flows through the Kurukshetra plain" → subject=Sarasvati relation=flows_through object=Kurukshetra

Output a JSON array (no markdown fences). Each element:
{{
  "subject": "canonical entity name",
  "relation": "relation from guide above",
  "object": "canonical entity or place name (short)",
  "citation": "e.g. RV 4.042.09 or AB 7.13.1",
  "confidence": "high or medium"
}}

If nothing extractable, output: []"""


def extract_and_store_facts(synthesis_response: str, question: str,
                             llm=None) -> int:
    """
    Call LLM to extract triples from a synthesis response and store them.
    Returns number of new facts added (0 if llm is None or extraction fails).
    """
    if llm is None or not synthesis_response:
        return 0

    prompt = _EXTRACTION_PROMPT.format(response=synthesis_response[:4000])

    try:
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])
        text = response.content if hasattr(response, "content") else str(response)

        # Strip markdown fences if present
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            text = m.group(1)
        text = text.strip()
        if not text or text == "[]":
            return 0

        facts = json.loads(text)
        if not isinstance(facts, list):
            return 0

        count = 0
        for f in facts:
            if not all(k in f for k in ("subject", "relation", "object", "citation")):
                continue
            if f["relation"] not in VALID_RELATIONS:
                continue
            is_new = add_fact(
                subject=f["subject"],
                relation=f["relation"],
                obj=f["object"],
                citation=f["citation"],
                confidence=f.get("confidence", "medium"),
                source_query=question,
            )
            if is_new:
                count += 1

        if count:
            logger.info(f"🕸️  Extracted {count} new KG facts from query: '{question[:60]}'")
        return count

    except Exception as e:
        logger.warning(f"🕸️  KG extraction failed: {e}")
        return 0


# ── NetworkX export (optional, for graph queries) ─────────────────────────────

def to_networkx():
    """
    Load the KG into a NetworkX DiGraph for multi-hop traversal.
    Requires: pip install networkx

    Usage:
        G = to_networkx()
        # All Ikshvaku kings:
        ikshvaku_members = [n for n, d in G.nodes(data=True)
                            if d.get('dynasty') == 'ikshvaku']
        # Shortest path from Ikshvaku to Harishchandra:
        nx.shortest_path(G, 'ikshvaku', 'harishchandra')
    """
    try:
        import networkx as nx
    except ImportError:
        raise ImportError("pip install networkx")

    kg = _load()
    G = nx.DiGraph()
    for key, entity in kg["entities"].items():
        G.add_node(key, display_name=entity.get("display_name", key))
        for fact in entity.get("relations", []):
            obj_key = _norm(fact["object"])
            G.add_edge(key, obj_key,
                       relation=fact["relation"],
                       citations=fact.get("citations", []),
                       confidence=fact.get("confidence", "?"))
    return G
