"""N17 Mesh — NVIDIA Dynamo / Ray Serve / llm-d cited job. Not those products.

Cite the leader. Take the job. Do not rehost.
Replica placement hologram. No GPUs. Engine image is a tag, not a pull.
"""
from __future__ import annotations

from typing import Any, Mapping

from lyte_lattice.organ import num, seal, text

ENGINES = ("vllm", "sglang", "ollama", "trtllm")
ENGINE_ALIASES = {
    "vllm": "vllm",
    "sglang": "sglang",
    "ollama": "ollama",
    "trtllm": "trtllm",
    "trt-llm": "trtllm",
    "tensorrt-llm": "trtllm",
    "tensorrt": "trtllm",
    "tensorrtllm": "trtllm",
}
MAX_REPLICAS = 64
NOTE = "Not NVIDIA Dynamo. Not Ray. No GPUs in this hologram."


def _engine(payload: Mapping[str, Any]) -> str:
    raw = text(payload, "engine", default="vllm").lower().replace("_", "-")
    if not raw:
        return "vllm"
    return ENGINE_ALIASES.get(raw, raw)


def _int_field(payload: Mapping[str, Any], key: str, default: int) -> int:
    try:
        return int(num(payload, key, float(default)))
    except (TypeError, ValueError):
        return default


def act(payload: Mapping[str, Any]) -> dict[str, Any]:
    engine = _engine(payload)
    replicas_req = _int_field(payload, "replicas", 4)
    queue_depth = _int_field(payload, "queue_depth", 12)
    if queue_depth < 0:
        queue_depth = 0

    if replicas_req < 1:
        return seal(
            cell="N17",
            status="blocked",
            payload=payload,
            output={
                "error": "replicas must be >= 1",
                "engine": engine,
                "replicas": replicas_req,
                "queue": {"depth": queue_depth, "wait_s_model": None, "honesty": "REPORTED"},
                "nodes": [],
                "note": NOTE,
            },
        )

    capped = replicas_req > MAX_REPLICAS
    replicas = MAX_REPLICAS if capped else replicas_req
    known = engine in ENGINES
    image = f"lyte-hologram/serve-{engine}:UNSIGNED-not-a-pull"
    nodes = [
        {
            "id": f"r{i}",
            "engine": engine,
            "image": image,
            "gpu": None,
            "gpu_honesty": "UNAVAILABLE",
            "status": "planned",
        }
        for i in range(replicas)
    ]
    wait_s = round(queue_depth / (replicas * 8.0), 6)
    status = "warn" if capped or not known else "ok"
    return seal(
        cell="N17",
        status=status,
        payload=payload,
        output={
            "engine": engine,
            "image": image,
            "replicas": replicas,
            "replicas_requested": replicas_req,
            "replicas_capped": capped,
            "nodes": nodes,
            "queue": {
                "depth": queue_depth,
                "wait_s_model": wait_s,
                "honesty": "REPORTED",
                "model": "M/D/1",
                "service_rate_model": replicas * 8,
                "note": "wait_s_model = queue_depth / (replicas * 8); MODEL not measured",
            },
            "engine_note": "engine image is a hologram tag, not a registry pull",
            "note": NOTE,
        },
    )
