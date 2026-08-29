"""N2 Graph — cite LangGraph. Take the job. Do not rehost.

Not LangGraph. Not a hosted agent runtime. Walk a local DAG with tiny stubs.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from lyte_lattice.organ import seal, text

DEFAULT_INPUT = "What peril covers a sudden pipe burst?"

PRESETS: dict[str, dict[str, Any]] = {
    "research": {
        "nodes": [
            {"id": "n0", "type": "input", "label": "Question"},
            {"id": "n1", "type": "retrieve", "label": "Retrieve"},
            {"id": "n2", "type": "serve", "label": "Draft"},
            {"id": "n3", "type": "guard", "label": "Guard"},
            {"id": "n4", "type": "end", "label": "Brief"},
        ],
        "edges": [
            {"from": "n0", "to": "n1", "when": "always"},
            {"from": "n1", "to": "n2", "when": "always"},
            {"from": "n2", "to": "n3", "when": "always"},
            {"from": "n3", "to": "n4", "when": "always"},
        ],
    },
    "fnol": {
        "nodes": [
            {"id": "n0", "type": "input", "label": "Narrative"},
            {"id": "n1", "type": "guard", "label": "Guard"},
            {"id": "n2", "type": "condition", "label": "Blocked?"},
            {"id": "n3", "type": "schema", "label": "Extract"},
            {"id": "n4", "type": "cover", "label": "Open claim"},
            {"id": "n5", "type": "end", "label": "Stop"},
        ],
        "edges": [
            {"from": "n0", "to": "n1", "when": "always"},
            {"from": "n1", "to": "n2", "when": "always"},
            {"from": "n2", "to": "n5", "when": "true"},
            {"from": "n2", "to": "n3", "when": "false"},
            {"from": "n3", "to": "n4", "when": "always"},
        ],
    },
    "trade": {
        "nodes": [
            {"id": "n0", "type": "input", "label": "Ask"},
            {"id": "n1", "type": "quant", "label": "Quant snapshot"},
            {"id": "n2", "type": "serve", "label": "Desk note"},
            {"id": "n3", "type": "end", "label": "Note"},
        ],
        "edges": [
            {"from": "n0", "to": "n1", "when": "always"},
            {"from": "n1", "to": "n2", "when": "always"},
            {"from": "n2", "to": "n3", "when": "always"},
        ],
    },
}

SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
IGNORE_RE = re.compile(r"ignore\s+previous", re.IGNORECASE)


def _node_dict(raw: Any, idx: int) -> dict[str, str]:
    if isinstance(raw, str):
        kind = raw.strip() or "input"
        return {"id": f"n{idx}", "type": kind, "label": kind.title()}
    if isinstance(raw, Mapping):
        kind = str(raw.get("type") or raw.get("kind") or "input").strip() or "input"
        nid = str(raw.get("id") or f"n{idx}")
        label = str(raw.get("label") or kind.title())
        return {"id": nid, "type": kind, "label": label}
    return {"id": f"n{idx}", "type": "input", "label": "Input"}


def _edge_dict(raw: Any) -> dict[str, str] | None:
    if not isinstance(raw, Mapping):
        return None
    src = raw.get("from", raw.get("src"))
    dst = raw.get("to", raw.get("dst"))
    if src is None or dst is None:
        return None
    when = str(raw.get("when") or "always").strip().lower() or "always"
    return {"from": str(src), "to": str(dst), "when": when}


def _build_custom(nodes_raw: Any, edges_raw: Any) -> dict[str, Any]:
    nodes = [_node_dict(n, i) for i, n in enumerate(list(nodes_raw or []))]
    edges: list[dict[str, str]] = []
    if isinstance(edges_raw, list) and edges_raw:
        for e in edges_raw:
            parsed = _edge_dict(e)
            if parsed:
                edges.append(parsed)
    else:
        for a, b in zip(nodes, nodes[1:]):
            edges.append({"from": a["id"], "to": b["id"], "when": "always"})
    return {"nodes": nodes, "edges": edges}


def _guard_stub(text_in: str) -> tuple[str, str]:
    if IGNORE_RE.search(text_in) or SSN_RE.search(text_in):
        return "blocked", "block: ignore-previous or SSN-shaped token"
    return "ok", "allow"


def _schema_stub(text_in: str) -> str:
    low = text_in.lower()
    if "rear" in low:
        cause = "collision"
    elif "pipe" in low:
        cause = "water"
    else:
        cause = "unknown"
    return f"cause={cause}"


def _run_node(node: Mapping[str, str], inp: str, ctx: dict[str, Any]) -> tuple[str, str]:
    kind = node["type"]
    if kind == "input":
        ctx["input"] = inp
        return "ok", inp
    if kind == "retrieve":
        out = "retrieved 3 mosaic chunks"
        ctx["retrieve"] = out
        return "ok", out
    if kind == "serve":
        bits = [ctx.get("retrieve") or "", ctx.get("quant") or "", ctx.get("guardText") or inp]
        body = " ".join(b for b in bits if b).strip()
        draft = f"Desk draft: {body[:280]}"
        ctx["serve"] = draft
        out = f"drafted {len(draft)} chars"
        ctx["serve_note"] = out
        return "ok", out
    if kind == "guard":
        src = str(ctx.get("serve") or ctx.get("guardText") or ctx.get("input") or inp)
        status, out = _guard_stub(src)
        ctx["guard"] = "block" if status == "blocked" else "allow"
        ctx["guardText"] = src
        if status == "blocked":
            ctx["blocked"] = True
        return status, out
    if kind == "condition":
        truth = bool(ctx.get("blocked")) or ctx.get("guard") == "block"
        out = "true" if truth else "false"
        ctx["cond"] = out
        return "ok", out
    if kind == "schema":
        src = str(ctx.get("guardText") or ctx.get("input") or inp)
        out = _schema_stub(src)
        ctx["schema"] = out
        return "ok", out
    if kind == "cover":
        if ctx.get("blocked") or ctx.get("guard") == "block":
            out = "cover withheld — prior guard blocked"
            ctx["cover"] = out
            return "blocked", out
        out = "FNOL opened"
        ctx["cover"] = out
        return "ok", out
    if kind == "quant":
        out = "SMA 10/30 posture: long"
        ctx["quant"] = out
        return "ok", out
    if kind == "end":
        if ctx.get("blocked") and not ctx.get("cover"):
            out = "stop"
        else:
            out = str(
                ctx.get("cover")
                or ctx.get("serve_note")
                or ctx.get("serve")
                or ctx.get("schema")
                or ctx.get("quant")
                or ctx.get("guardText")
                or inp
            )
        ctx["end"] = out
        return "ok", out
    return "error", f"unknown node type {kind!r}"


def _walk(graph: Mapping[str, Any], inp: str) -> tuple[list[dict[str, Any]], bool]:
    nodes = list(graph.get("nodes") or [])
    edges = list(graph.get("edges") or [])
    by_id = {n["id"]: n for n in nodes}
    start = next((n for n in nodes if n.get("type") == "input"), nodes[0] if nodes else None)
    steps: list[dict[str, Any]] = []
    if start is None:
        return steps, False

    ctx: dict[str, Any] = {"input": inp, "blocked": False, "cond": "false"}
    queue = [start["id"]]
    seen: set[str] = set()

    while queue:
        nid = queue.pop(0)
        if nid in seen:
            continue
        seen.add(nid)
        node = by_id.get(nid)
        if node is None:
            continue
        status, output = _run_node(node, inp, ctx)
        steps.append(
            {
                "id": node["id"],
                "type": node["type"],
                "label": node["label"],
                "status": status,
                "output": output,
            }
        )
        cond = str(ctx.get("cond") or "false")
        for edge in edges:
            if edge.get("from") != nid:
                continue
            when = str(edge.get("when") or "always").lower()
            dest = str(edge.get("to") or "")
            if not dest:
                continue
            if when == "always":
                queue.append(dest)
            elif when == "true" and cond == "true":
                queue.append(dest)
            elif when == "false" and cond != "true":
                queue.append(dest)

    return steps, bool(ctx.get("blocked"))


def act(payload: Mapping[str, Any]) -> dict[str, Any]:
    inp = text(payload, "input", "prompt", "text", "narrative", default=DEFAULT_INPUT)
    raw_preset = text(payload, "preset", default="")
    nodes_raw = payload.get("nodes")
    edges_raw = payload.get("edges")

    custom = isinstance(nodes_raw, list) and bool(nodes_raw)
    if custom:
        graph = _build_custom(nodes_raw, edges_raw)
        preset = raw_preset.lower() if raw_preset else "custom"
    else:
        key = raw_preset.lower() if raw_preset else "research"
        if key not in PRESETS:
            return seal(
                cell="N2",
                status="blocked",
                payload=payload,
                output={
                    "preset": raw_preset,
                    "input": inp,
                    "error": f"unknown preset {raw_preset!r}; expected research|fnol|trade or nodes/edges",
                    "presets": list(PRESETS),
                    "steps": [],
                    "result": "",
                    "blocked": False,
                },
            )
        graph = PRESETS[key]
        preset = key

    steps, blocked = _walk(graph, inp)
    if not steps:
        return seal(
            cell="N2",
            status="error",
            payload=payload,
            output={
                "preset": preset,
                "input": inp,
                "steps": [],
                "result": "",
                "blocked": False,
                "error": "graph has no walkable nodes",
            },
        )

    fail = next((s for s in steps if s["status"] in {"error", "blocked"}), None)
    result = ""
    for s in reversed(steps):
        if s.get("output"):
            result = str(s["output"])
            break
    status = "ok"
    if fail and fail["status"] == "error":
        status = "error"
    elif blocked or (fail and fail["status"] == "blocked"):
        status = "blocked"

    return seal(
        cell="N2",
        status=status,
        payload=payload,
        output={
            "preset": preset,
            "input": inp,
            "steps": steps,
            "result": result,
            "blocked": blocked,
        },
    )
