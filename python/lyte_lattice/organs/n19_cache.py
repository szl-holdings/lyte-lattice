"""N19 Cache — LMCache / Mooncake / GPTCache cited job. Not distributed KV.

Cite the leader. Take the job. Do not rehost.
In-process prefix-cache hologram: put / get / stats.
"""
from __future__ import annotations

import hashlib
import time
from typing import Any, Mapping

from lyte_lattice.organ import seal, text

NOTE = "Not LMCache distributed. Not Mooncake."
SEED_KEY = "fnol:pipe"
SEED_VAL = "home water sudden burst"
STATS_KEY_CAP = 12

_CACHE: dict[str, dict[str, Any]] = {}


def _sha256_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _storeable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool, dict, list)):
        return value
    return str(value)


def _seed_if_empty() -> None:
    if _CACHE:
        return
    _CACHE[SEED_KEY] = {
        "value": SEED_VAL,
        "hash": _sha256_key(SEED_KEY),
        "ts": time.time(),
        "hits": 0,
    }


def _prefix_note(key: str) -> str | None:
    if not key:
        return None
    for stored in _CACHE:
        if stored and stored != key and key.startswith(stored):
            return "prefix hit silhouette"
    return None


def _hits_total() -> int:
    total = 0
    for row in _CACHE.values():
        try:
            total += int(row.get("hits") or 0)
        except (TypeError, ValueError):
            pass
    return total


def _stats_body(extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    keys = list(_CACHE.keys())[:STATS_KEY_CAP]
    body: dict[str, Any] = {
        "op": "stats",
        "size": len(_CACHE),
        "keys": keys,
        "hits_total": _hits_total(),
        "note": NOTE,
    }
    if extra:
        body.update(dict(extra))
    return body


def act(payload: Mapping[str, Any]) -> dict[str, Any]:
    _seed_if_empty()
    op = text(payload, "op", default="stats").lower() or "stats"
    key = text(payload, "key")
    prefix = _prefix_note(key) if key else None

    if op == "put":
        if not key:
            return seal(
                cell="N19",
                status="warn",
                payload=payload,
                output={
                    "op": "put",
                    "error": "key required",
                    "size": len(_CACHE),
                    "note": NOTE,
                },
            )
        digest = _sha256_key(key)
        prev = _CACHE.get(key)
        hits = int(prev.get("hits") or 0) if isinstance(prev, dict) else 0
        _CACHE[key] = {
            "value": _storeable(payload.get("value")),
            "hash": digest,
            "ts": time.time(),
            "hits": hits,
        }
        out: dict[str, Any] = {
            "op": "put",
            "key": key,
            "hash": digest,
            "size": len(_CACHE),
            "note": NOTE,
        }
        if prefix:
            out["prefix"] = prefix
        return seal(cell="N19", status="ok", payload=payload, output=out)

    if op == "get":
        if not key:
            return seal(
                cell="N19",
                status="warn",
                payload=payload,
                output={"op": "get", "error": "key required", "hit": False, "note": NOTE},
            )
        row = _CACHE.get(key)
        if row is None:
            miss: dict[str, Any] = {
                "op": "get",
                "key": key,
                "hit": False,
                "size": len(_CACHE),
                "note": NOTE,
            }
            if prefix:
                miss["prefix"] = prefix
            return seal(cell="N19", status="warn", payload=payload, output=miss)
        row["hits"] = int(row.get("hits") or 0) + 1
        hit: dict[str, Any] = {
            "op": "get",
            "key": key,
            "hit": True,
            "value": row.get("value"),
            "hash": row.get("hash"),
            "hits": row["hits"],
            "ts": row.get("ts"),
            "note": NOTE,
        }
        if prefix:
            hit["prefix"] = prefix
        return seal(cell="N19", status="ok", payload=payload, output=hit)

    extra: dict[str, Any] = {}
    if prefix:
        extra["key"] = key
        extra["prefix"] = prefix
    status = "ok" if op == "stats" else "warn"
    if op not in {"stats", "get", "put"}:
        extra["op_requested"] = op
        extra["op"] = "stats"
    return seal(cell="N19", status=status, payload=payload, output=_stats_body(extra))
