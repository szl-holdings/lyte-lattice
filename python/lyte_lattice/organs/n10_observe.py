"""N10 Observe — cited Phoenix / LangSmith / Langfuse / DeepEval. Not those clouds."""
from __future__ import annotations

import json
import math
import re
from typing import Any, Mapping

from lyte_lattice.organ import seal, text

_NOTE = "Cited Phoenix / LangSmith / Langfuse / DeepEval. Not those clouds. Local span harness."
_TOX = re.compile(r"\b(bomb|kill|suicide)s?\b", re.IGNORECASE)
_TOKEN = re.compile(r"\w+")

DEMO_SPANS: list[dict[str, Any]] = [
    {
        "cell": "serve",
        "name": "complete",
        "status": "ok",
        "durationMs": 420,
        "input": "draft a coverage note for water FNOL",
        "output": '{"text": "coverage confirmed for sudden pipe burst"}',
    },
    {
        "cell": "serve",
        "name": "stream",
        "status": "ok",
        "durationMs": 3100,
        "input": "desk brief SMA SPY",
        "output": "draft claim note for the desk",
    },
    {
        "cell": "guard",
        "name": "scan",
        "status": "ok",
        "durationMs": 12,
        "input": "allow this FNOL narrative",
        "output": '{"action": "allow"}',
    },
    {
        "cell": "guard",
        "name": "scan",
        "status": "warn",
        "durationMs": 18,
        "input": "ssn in the note",
        "output": "redact ssn",
    },
    {
        "cell": "cover",
        "name": "fnol",
        "status": "ok",
        "durationMs": 8,
        "input": "pipe burst kitchen ceiling",
        "output": "CLM-9002 open water",
    },
    {
        "cell": "cover",
        "name": "reserve",
        "status": "warn",
        "durationMs": 6,
        "input": "set reserve on POL-HOME-1088",
        "output": "reserve 180000",
    },
    {
        "cell": "quant",
        "name": "backtest",
        "status": "ok",
        "durationMs": 44,
        "input": "sma SPY 10/30",
        "output": "sharpe 1.12",
    },
    {
        "cell": "quant",
        "name": "backtest",
        "status": "error",
        "durationMs": 9200,
        "input": "momentum NVDA",
        "output": "timeout",
    },
]


def _as_text(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    try:
        return json.dumps(v, sort_keys=True, default=str)
    except TypeError:
        return str(v)


def _normalize_spans(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or not raw:
        return [dict(s) for s in DEMO_SPANS]
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        dur = item.get("durationMs", item.get("duration_ms", 0))
        try:
            duration = float(dur)
        except (TypeError, ValueError):
            duration = 0.0
        out.append(
            {
                "cell": str(item.get("cell") or item.get("id") or "unknown"),
                "name": str(item.get("name") or item.get("op") or "span"),
                "status": str(item.get("status") or "ok"),
                "durationMs": duration,
                "input": _as_text(item.get("input")),
                "output": _as_text(item.get("output")),
            }
        )
    return out or [dict(s) for s in DEMO_SPANS]


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = min(len(ordered) - 1, max(0, math.ceil((p / 100.0) * len(ordered)) - 1))
    return ordered[rank]


def _json_parseable(raw: str) -> bool:
    s = raw.strip()
    if not s:
        return False
    try:
        json.loads(s)
        return True
    except (TypeError, ValueError, json.JSONDecodeError):
        return False


def _faithfulness(inp: str, out: str) -> float:
    in_toks = set(t.casefold() for t in _TOKEN.findall(inp) if t)
    if not in_toks:
        return 0.5
    out_toks = set(t.casefold() for t in _TOKEN.findall(out) if t)
    if not out_toks:
        return 0.0
    return min(1.0, len(in_toks & out_toks) / len(in_toks))


def _toxicity(out: str) -> float:
    return 1.0 if _TOX.search(out or "") else 0.0


def _structure(out: str) -> float:
    return 1.0 if _json_parseable(out) else 0.5


def _latency(ms: float) -> float:
    if ms < 2500:
        return 1.0
    if ms < 8000:
        return 0.7
    return 0.4


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _summary(spans: list[dict[str, Any]]) -> dict[str, Any]:
    by_cell: dict[str, int] = {}
    by_status: dict[str, int] = {}
    durations: list[float] = []
    errors = 0
    for sp in spans:
        cell = str(sp.get("cell") or "unknown")
        st = str(sp.get("status") or "ok")
        by_cell[cell] = by_cell.get(cell, 0) + 1
        by_status[st] = by_status.get(st, 0) + 1
        durations.append(float(sp.get("durationMs") or 0))
        if st in {"error", "blocked"}:
            errors += 1
    n = len(spans)
    return {
        "op": "summary",
        "n": n,
        "by_cell": by_cell,
        "p50": round(_percentile(durations, 50), 3),
        "p95": round(_percentile(durations, 95), 3),
        "error_rate": round((errors / n) if n else 0.0, 6),
        "by_status": by_status,
        "note": _NOTE,
    }


def _eval(spans: list[dict[str, Any]]) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for sp in spans:
        inp = _as_text(sp.get("input")) or str(sp.get("name") or "")
        out = _as_text(sp.get("output"))
        scores = {
            "faithfulness": round(_faithfulness(inp, out), 4),
            "toxicity": _toxicity(out),
            "structure": _structure(out),
            "latency": _latency(float(sp.get("durationMs") or 0)),
        }
        cases.append(
            {
                "cell": sp.get("cell"),
                "name": sp.get("name"),
                "status": sp.get("status"),
                "durationMs": sp.get("durationMs"),
                "scores": scores,
            }
        )
    mean = {
        "faithfulness": round(_mean([c["scores"]["faithfulness"] for c in cases]), 4),
        "toxicity": round(_mean([c["scores"]["toxicity"] for c in cases]), 4),
        "structure": round(_mean([c["scores"]["structure"] for c in cases]), 4),
        "latency": round(_mean([c["scores"]["latency"] for c in cases]), 4),
    }
    return {"op": "eval", "n": len(cases), "cases": cases, "mean": mean, "note": _NOTE}


def act(payload: Mapping[str, Any]) -> dict[str, Any]:
    op = text(payload, "op", "action", default="summary").strip().lower()
    if op not in {"summary", "eval"}:
        op = "summary"
    spans = _normalize_spans(payload.get("spans"))
    output = _eval(spans) if op == "eval" else _summary(spans)
    return seal(cell="N10", status="ok", payload=payload, output=output)
