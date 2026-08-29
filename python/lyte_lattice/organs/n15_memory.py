"""N15 Memory — in-process notes + tiny entity graph.

Cited: Mem0 / Zep Graphiti. Take the job. Do not rehost hosted memory.
NOT hosted Mem0. NOT Zep Cloud. NOT a Graphiti service.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Mapping

from lyte_lattice.organ import seal, text

# Module-level store. Seeded on first call if empty. Not a hosted graph.
_STORE: dict[str, Any] = {
    "notes": [],  # list[{id, text, ts, entities}]
    "graph": {},  # entity -> set[str] undirected adjacency
    "seq": 0,
}

_DEFAULT_TEXT = "Harbor Logistics cargo"

_MULTI_KEYWORDS = (
    "Harbor Logistics",
    "Jane Ortiz",
    "Marcus Chen",
)
_SINGLE_KEYWORDS = ("Serve", "Cover", "Quant")
_STOP = {
    "The",
    "A",
    "An",
    "This",
    "That",
    "These",
    "Those",
    "When",
    "What",
    "Who",
    "Why",
    "How",
    "Is",
    "Are",
    "Was",
    "Were",
    "Be",
    "On",
    "In",
    "Of",
    "For",
    "And",
    "Or",
    "To",
    "From",
    "With",
    "By",
    "At",
    "As",
    "If",
    "It",
    "Its",
}

_SEED_NOTES = (
    {
        "text": "Harbor Logistics is the commercial account. Cargo claims route to inland marine.",
        "ts": "2026-08-28T14:00:00Z",
    },
    {
        "text": "Serve TensorRT-LLM profile is preferred for extraction. SGLang for JSON.",
        "ts": "2026-08-29T09:10:00Z",
    },
)


def _tokens(blob: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", blob.lower())


def _token_set(blob: str) -> set[str]:
    return set(_tokens(blob))


def _parse_entities(blob: str, extra: str | None = None) -> list[str]:
    entities: list[str] = []
    masked = blob
    for phrase in _MULTI_KEYWORDS:
        if re.search(rf"\b{re.escape(phrase)}\b", masked, re.I):
            entities.append(phrase)
            masked = re.sub(rf"\b{re.escape(phrase)}\b", " ", masked, flags=re.I)
    for word in _SINGLE_KEYWORDS:
        if re.search(rf"\b{re.escape(word)}\b", masked):
            entities.append(word)
            masked = re.sub(rf"\b{re.escape(word)}\b", " ", masked)
    for m in re.finditer(r"\b([A-Z][a-zA-Z0-9]+(?:-[A-Z][a-zA-Z0-9]+)*)\b", masked):
        token = m.group(1)
        if token in _STOP:
            continue
        if token not in entities:
            entities.append(token)
    if extra:
        extra_s = extra.strip()
        if extra_s and extra_s not in entities:
            entities.append(extra_s)
    out: list[str] = []
    for e in entities:
        if e and e not in out:
            out.append(e)
    return out


def _link(entities: list[str]) -> None:
    graph: dict[str, set[str]] = _STORE["graph"]
    for ent in entities:
        graph.setdefault(ent, set())
    for i, a in enumerate(entities):
        for b in entities[i + 1 :]:
            if a == b:
                continue
            graph[a].add(b)
            graph[b].add(a)


def _remember(blob: str, ts: str | None = None, extra_entity: str | None = None) -> dict[str, Any]:
    _STORE["seq"] = int(_STORE["seq"]) + 1
    note_id = f"n{_STORE['seq']}"
    entities = _parse_entities(blob, extra_entity)
    stamp = ts or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    note = {"id": note_id, "text": blob, "ts": stamp, "entities": entities}
    _STORE["notes"].append(note)
    _link(entities)
    return note


def _ensure_seed() -> None:
    if _STORE["notes"]:
        return
    for row in _SEED_NOTES:
        _remember(row["text"], ts=row["ts"])


def _overlap_score(query: str, note_text: str) -> float:
    q = _token_set(query)
    n = _token_set(note_text)
    if not q or not n:
        return 0.0
    return float(len(q & n))


def _recall(query: str, entity: str | None) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for note in _STORE["notes"]:
        score = _overlap_score(query, note["text"])
        if entity:
            ents = {str(e).lower() for e in note.get("entities") or []}
            if entity.lower() in ents or entity.lower() in note["text"].lower():
                score += 1.0
        scored.append(
            {
                "id": note["id"],
                "text": note["text"],
                "ts": note["ts"],
                "entities": list(note["entities"]),
                "score": score,
            }
        )
    scored.sort(key=lambda row: (float(row["score"]), str(row["ts"])), reverse=True)
    return scored[:5]


def _graph_view() -> dict[str, Any]:
    graph: dict[str, set[str]] = _STORE["graph"]
    nodes = [{"id": name, "label": name} for name in sorted(graph)]
    seen: set[tuple[str, str]] = set()
    edges: list[dict[str, str]] = []
    for src, neighbors in graph.items():
        for dst in neighbors:
            pair = (src, dst) if src < dst else (dst, src)
            if pair in seen:
                continue
            seen.add(pair)
            edges.append({"source": pair[0], "target": pair[1]})
    edges.sort(key=lambda e: (e["source"], e["target"]))
    return {"nodes": nodes, "edges": edges}


def act(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    p = dict(payload or {})
    _ensure_seed()
    op = (text(p, "op", default="recall") or "recall").strip().lower()
    blob = text(p, "text", default=_DEFAULT_TEXT)
    entity = text(p, "entity") or None
    store_size = len(_STORE["notes"])
    if op == "remember":
        body = text(p, "text")
        if not body:
            return seal(
                cell="N15",
                status="warn",
                payload=p,
                output={"op": "remember", "error": "text required", "store_size": store_size},
            )
        note = _remember(body, extra_entity=entity)
        return seal(
            cell="N15",
            status="ok",
            payload=p,
            output={"op": "remember", "note": note, "store_size": len(_STORE["notes"])},
        )
    if op == "graph":
        view = _graph_view()
        return seal(
            cell="N15",
            status="ok",
            payload=p,
            output={"op": "graph", "nodes": view["nodes"], "edges": view["edges"], "store_size": store_size},
        )
    if op != "recall":
        return seal(
            cell="N15",
            status="warn",
            payload=p,
            output={
                "op": op,
                "error": "unknown op",
                "supported": ["remember", "recall", "graph"],
                "store_size": store_size,
            },
        )
    query = blob or _DEFAULT_TEXT
    hits = _recall(query, entity)
    return seal(
        cell="N15",
        status="ok",
        payload=p,
        output={"op": "recall", "query": query, "hits": hits, "store_size": store_size},
    )
