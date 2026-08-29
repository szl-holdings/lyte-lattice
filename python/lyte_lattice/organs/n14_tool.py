"""N14 Tool — MCP-shaped JSON-RPC silhouette.

Cited: Anthropic MCP. Take the job. Do not rehost a live MCP server.
NOT a live MCP server to Anthropic. NOT hosted tools.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from lyte_lattice.organ import BIND, LAMBDA, seal, text

_NOTE = "Not a live MCP server to Anthropic."
_PROTOCOL = "2025-03-26"
_SERVER = {"name": "lyte-lattice-tool", "version": "0.2.0"}

ToolFn = Callable[[dict[str, Any]], Any]


def _echo(arguments: dict[str, Any]) -> dict[str, Any]:
    return {"text": text(arguments, "text", default="")}


def _time(_arguments: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {"utc": now.isoformat().replace("+00:00", "Z"), "unix": int(now.timestamp())}


def _hash(arguments: dict[str, Any]) -> dict[str, Any]:
    blob = text(arguments, "text", default="")
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return {"sha256": digest, "text_len": len(blob)}


def _lattice_health(_arguments: dict[str, Any]) -> dict[str, Any]:
    return {"cells": 25, "bind": BIND, "lambda": LAMBDA}


def _title_lookup(arguments: dict[str, Any]) -> dict[str, Any]:
    address = text(arguments, "address", default="")
    return {"note": "delegate to N8", "address": address}


TOOLS: dict[str, dict[str, Any]] = {
    "echo": {
        "name": "echo",
        "description": "Echo text back. Silhouette only.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
        "fn": _echo,
    },
    "time": {
        "name": "time",
        "description": "UTC clock reading from the organ host.",
        "inputSchema": {"type": "object", "properties": {}},
        "fn": _time,
    },
    "hash": {
        "name": "hash",
        "description": "SHA-256 hex digest of text.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
        "fn": _hash,
    },
    "lattice_health": {
        "name": "lattice_health",
        "description": "Lattice hologram health silhouette. 25 cells. BIND package.",
        "inputSchema": {"type": "object", "properties": {}},
        "fn": _lattice_health,
    },
    "title_lookup": {
        "name": "title_lookup",
        "description": "Public-records title lookup delegates to N8. Not a title plant.",
        "inputSchema": {
            "type": "object",
            "properties": {"address": {"type": "string"}},
            "required": ["address"],
        },
        "fn": _title_lookup,
    },
}


def _list_tools() -> dict[str, Any]:
    tools = []
    for spec in TOOLS.values():
        tools.append(
            {
                "name": spec["name"],
                "description": spec["description"],
                "inputSchema": spec["inputSchema"],
            }
        )
    return {"tools": tools}


def _mcp_result(data: Any, is_error: bool = False) -> dict[str, Any]:
    if isinstance(data, (dict, list)):
        rendered = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    else:
        rendered = str(data)
    return {
        "content": [{"type": "text", "text": rendered}],
        "structured": data,
        "isError": is_error,
    }


def _arguments(payload: Mapping[str, Any]) -> dict[str, Any]:
    raw = payload.get("arguments")
    if isinstance(raw, dict):
        return dict(raw)
    params = payload.get("params")
    if isinstance(params, dict) and isinstance(params.get("arguments"), dict):
        return dict(params["arguments"])
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {"text": raw}
    return {}


def _method(payload: Mapping[str, Any]) -> str:
    raw = text(payload, "method", default="tools/list").strip() or "tools/list"
    aliases = {
        "list": "tools/list",
        "tools.list": "tools/list",
        "call": "tools/call",
        "tools.call": "tools/call",
        "init": "initialize",
        "initialize": "initialize",
        "tools/list": "tools/list",
        "tools/call": "tools/call",
    }
    return aliases.get(raw, raw)


def _tool_name(payload: Mapping[str, Any]) -> str:
    name = text(payload, "name")
    if name:
        return name
    params = payload.get("params")
    if isinstance(params, dict):
        return str(params.get("name") or "").strip()
    return ""


def _envelope(method: str, result: Any) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "method": method,
        "result": result,
        "note": _NOTE,
    }


def act(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    p = dict(payload or {})
    method = _method(p)
    if method == "initialize":
        result = {
            "protocolVersion": _PROTOCOL,
            "serverInfo": dict(_SERVER),
            "capabilities": {"tools": {}},
        }
        return seal(cell="N14", status="ok", payload=p, output=_envelope(method, result))
    if method == "tools/list":
        return seal(cell="N14", status="ok", payload=p, output=_envelope(method, _list_tools()))
    if method == "tools/call":
        name = _tool_name(p)
        spec = TOOLS.get(name)
        if spec is None:
            result = _mcp_result(
                {"error": "unknown tool", "name": name or None, "code": -32601},
                is_error=True,
            )
            return seal(cell="N14", status="warn", payload=p, output=_envelope(method, result))
        fn: ToolFn = spec["fn"]
        data = fn(_arguments(p))
        result = _mcp_result(data, is_error=False)
        result["name"] = name
        return seal(cell="N14", status="ok", payload=p, output=_envelope(method, result))
    result = {
        "error": "unknown method",
        "method": method,
        "code": -32601,
        "supported": ["initialize", "tools/list", "tools/call"],
    }
    return seal(cell="N14", status="warn", payload=p, output=_envelope(method, result))
