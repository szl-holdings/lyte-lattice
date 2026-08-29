"""Resolve N1–N25 organs. Unknown or missing modules fail closed."""
from __future__ import annotations

import importlib
import traceback
from typing import Any, Mapping

from lyte_lattice.organ import CELLS, blocked, normalize_cell, seal


def resolve(cell: str):
    n = normalize_cell(cell)
    if n is None:
        return None, None
    modname = CELLS[n]["module"]
    try:
        return n, importlib.import_module(modname)
    except Exception as exc:
        return n, exc


def act(cell: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    p = dict(payload or {})
    n, mod = resolve(cell)
    if n is None:
        return blocked(cell or "unknown", "unknown cell", p)
    if isinstance(mod, Exception):
        return seal(
            cell=n,
            status="blocked",
            payload=p,
            output={
                "error": f"organ missing or failed to import: {mod}",
                "trace": traceback.format_exception_only(type(mod), mod)[-1].strip(),
            },
        )
    fn = getattr(mod, "act", None)
    if not callable(fn):
        return blocked(n, "organ has no act()", p)
    try:
        raw = fn(p)
    except Exception as exc:
        return seal(
            cell=n,
            status="error",
            payload=p,
            output={"error": str(exc), "trace": traceback.format_exc().splitlines()[-8:]},
        )
    if not isinstance(raw, dict):
        return seal(cell=n, status="error", payload=p, output={"error": "organ returned non-dict"})
    # Re-seal so hash/signature/joule cannot be forged by the organ.
    status = str(raw.get("status") or "ok")
    if status not in {"ok", "warn", "error", "blocked"}:
        status = "error"
    output = raw.get("output", raw)
    honesty = raw.get("honesty") if raw.get("honesty") in {"LIVE", "STRUCTURAL-ONLY", "UNAVAILABLE"} else None
    return seal(cell=n, status=status, payload=p, output=output, honesty=honesty)


def list_cells() -> list[dict[str, str]]:
    rows = []
    for n, meta in CELLS.items():
        _, mod = resolve(n)
        rows.append(
            {
                "cell": n,
                "id": meta["id"],
                "title": meta["title"],
                "cited": meta["cited"],
                "honesty": meta["honesty"],
                "loaded": "ok" if not isinstance(mod, Exception) and mod is not None else "missing",
            }
        )
    return rows
