"""N1 Serve — cite vLLM / SGLang / Ollama / TensorRT-LLM. Take the job. Do not rehost.

Not a local GPU cluster. Completions terminate on Grok 4.5 via the TS Serve cell.
This organ receipts the decode posture. It does not run GPU inference.
"""
from __future__ import annotations

from typing import Any, Mapping

from lyte_lattice.organ import num, seal, text

PROFILES: dict[str, dict[str, Any]] = {
    "vllm": {
        "name": "vLLM",
        "cited": "Paged attention · continuous batching",
        "temperature": 0.7,
        "max_tokens": 520,
        "top_p": 0.95,
        "json_bias": False,
        "stop": [],
    },
    "sglang": {
        "name": "SGLang",
        "cited": "Radix attention · constrained decoding",
        "temperature": 0.4,
        "max_tokens": 480,
        "top_p": 0.9,
        "json_bias": True,
        "stop": [],
    },
    "ollama": {
        "name": "Ollama",
        "cited": "Local-first conversational",
        "temperature": 0.8,
        "max_tokens": 420,
        "top_p": 1.0,
        "json_bias": False,
        "stop": [],
    },
    "trtllm": {
        "name": "TensorRT-LLM",
        "cited": "Low-latency extraction",
        "temperature": 0.2,
        "max_tokens": 280,
        "top_p": 0.8,
        "json_bias": False,
        "stop": ["\n\n\n"],
    },
}

ALIASES = {
    "vllm": "vllm",
    "sglang": "sglang",
    "ollama": "ollama",
    "trtllm": "trtllm",
    "trt-llm": "trtllm",
    "trt_llm": "trtllm",
    "tensorrt-llm": "trtllm",
    "tensorrt_llm": "trtllm",
    "tensorrtllm": "trtllm",
    "tensorrt": "trtllm",
}

NOTE = (
    "Completions in this hologram terminate on Grok 4.5 via the TS Serve cell. "
    "This organ receipts the posture, it does not run GPU inference."
)
DEFAULT_PROMPT = "Ping the lattice."


def _flag(payload: Mapping[str, Any], key: str) -> bool | None:
    if key not in payload:
        return None
    v = payload[key]
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return bool(v)
    s = str(v).strip().lower()
    if s in {"1", "true", "yes", "on"}:
        return True
    if s in {"0", "false", "no", "off", ""}:
        return False
    return None


def _decode_plan(engine: str, profile: Mapping[str, Any], prompt: str, json_bias: bool) -> list[str]:
    chars = len(prompt)
    tokens = max(1, chars // 4)
    steps = [
        f"Select {profile['name']} posture — {profile['cited']}",
        "Bind hologram system prompt (no local GPU runtime)",
        f"Ingest prompt ({chars} chars, ~{tokens} tokens)",
    ]
    if engine == "vllm":
        steps.append("Page the KV cache; admit the request into a continuous batch")
    elif engine == "sglang":
        steps.append("Reuse radix-attention prefix cache; prefer constrained decoding")
    elif engine == "ollama":
        steps.append("Local-first conversational decode; short paragraphs")
    else:
        steps.append("Low-latency extractive decode; no preamble")
    if json_bias:
        steps.append("Enable JSON bias / constrained decoding")
    else:
        steps.append("JSON bias off — free-form completion")
    steps.append(
        f"Sample temperature={profile['temperature']} top_p={profile['top_p']} "
        f"max_tokens={profile['max_tokens']}"
    )
    stop = profile.get("stop") or []
    if stop:
        steps.append("Honor stop sequences: " + ", ".join(str(s) for s in stop))
    steps.append("Hand the completion to Grok 4.5 via the TS Serve cell")
    steps.append("Seal this receipt; do not run GPU inference in the organ")
    return steps


def act(payload: Mapping[str, Any]) -> dict[str, Any]:
    raw_engine = text(payload, "engine", default="vllm")
    engine = ALIASES.get(raw_engine.lower().strip())
    if engine is None:
        return seal(
            cell="N1",
            status="blocked",
            payload=payload,
            output={
                "engine": raw_engine,
                "error": f"unknown engine {raw_engine!r}; expected vllm|sglang|ollama|trtllm",
                "engines": list(PROFILES),
                "note": NOTE,
            },
        )

    base = PROFILES[engine]
    override = _flag(payload, "json_bias")
    json_bias = base["json_bias"] if override is None else override
    prompt = text(payload, "prompt", "text", "user", default=DEFAULT_PROMPT)

    temp = num(payload, "temperature", float(base["temperature"]))
    max_tokens = int(num(payload, "max_tokens", float(base["max_tokens"])))
    top_p = num(payload, "top_p", float(base["top_p"]))

    profile = {
        "name": base["name"],
        "cited": base["cited"],
        "temperature": temp,
        "max_tokens": max_tokens,
        "top_p": top_p,
        "json_bias": json_bias,
        "stop": list(base["stop"]),
    }
    chars = len(prompt)
    token_estimate = max(1, chars // 4) if chars else 0

    return seal(
        cell="N1",
        status="ok",
        payload=payload,
        output={
            "engine": engine,
            "profile": profile,
            "prompt_chars": chars,
            "token_estimate": token_estimate,
            "decode_plan": _decode_plan(engine, profile, prompt, json_bias),
            "note": NOTE,
        },
    )
