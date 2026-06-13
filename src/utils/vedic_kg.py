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
Attribute   : has_attribute
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.helper import logger

# ── Storage ───────────────────────────────────────────────────────────────────

KG_PATH = Path(__file__).parent.parent.parent / "knowledge_store" / "vedic_relations.json"

_KG_CACHE: Optional[dict] = None

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
    # Attribute
    "has_attribute",
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
}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _norm(name: str) -> str:
    """Stable key: lowercase, underscores, no diacritics."""
    import unicodedata
    s = unicodedata.normalize("NFD", name.lower().strip())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def _load() -> dict:
    global _KG_CACHE
    if _KG_CACHE is not None:
        return _KG_CACHE
    KG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if KG_PATH.exists():
        with open(KG_PATH, encoding="utf-8") as f:
            _KG_CACHE = json.load(f)
        logger.info(f"🕸️  KG loaded: {_KG_CACHE['_meta']['total_facts']} facts, "
                    f"{len(_KG_CACHE['entities'])} entities")
    else:
        _KG_CACHE = {
            "_meta": {"created": str(datetime.now()), "total_facts": 0,
                      "last_updated": str(datetime.now())},
            "entities": {}
        }
    return _KG_CACHE


def _save(kg: dict):
    global _KG_CACHE
    total = sum(len(e.get("relations", [])) for e in kg["entities"].values())
    kg["_meta"]["total_facts"] = total
    kg["_meta"]["last_updated"] = str(datetime.now())
    with open(KG_PATH, "w", encoding="utf-8") as f:
        json.dump(kg, f, indent=2, ensure_ascii=False)
    _KG_CACHE = kg


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
            return False   # not a new fact

    # New fact
    existing.append({
        "relation": relation,
        "object": obj,
        "citations": [citation] if citation else [],
        "confidence": confidence,
        "from_query": source_query[:120] if source_query else "",
        "added_at": str(datetime.now()),
    })
    _save(kg)
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

_EXTRACTION_PROMPT = """You are extracting structured facts from a Vedic studies response.

RESPONSE TEXT:
{response}

INSTRUCTIONS:
- Extract ONLY facts that are EXPLICITLY STATED with corpus citations (RV, SB, AB, PB, YV).
- Do NOT infer or hallucinate. Only what is directly asserted with a citation.
- Use consistent English transliteration for entity names (e.g. "Purukutsa", "Trasadasyu").
- Allowed relation values: has_son | has_daughter | has_father | has_mother |
  has_brother | has_sister | has_spouse | member_of_dynasty | founded_dynasty |
  patronymic | epithet | is_king_of | is_purohita_of | is_disciple_of |
  is_guru_of | fought | allied_with | performed_ritual | received_boon |
  same_as | has_attribute

Output a JSON array (no markdown fences). Each element:
{{
  "subject": "entity name",
  "relation": "relation type from list above",
  "object": "related entity or value",
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
