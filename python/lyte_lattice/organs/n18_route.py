"""N18 Route — LiteLLM / OpenRouter / RouteLLM cited job. Not billing.

Cite the leader. Take the job. Do not rehost.
Deterministic prompt → Serve hologram posture. Not a proxy.
"""
from __future__ import annotations

from typing import Any, Mapping

from lyte_lattice.organ import seal, text

DEFAULT_PROMPT = "Return JSON {cause, reserveHint} for this FNOL."
DEFAULT_CANDIDATES = ["vllm", "sglang", "ollama", "trtllm"]
ALIASES = {
    "vllm": "vllm",
    "sglang": "sglang",
    "ollama": "ollama",
    "trtllm": "trtllm",
    "trt-llm": "trtllm",
    "tensorrt-llm": "trtllm",
    "tensorrt": "trtllm",
    "tensorrtllm": "trtllm",
}
NOTE = "Not OpenRouter. Not LiteLLM proxy. Chosen profile is a Serve hologram posture."


def _clamp(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _candidates(payload: Mapping[str, Any]) -> list[str]:
    raw = payload.get("candidates")
    items: list[Any]
    if isinstance(raw, str):
        items = [p.strip() for p in raw.split(",") if p.strip()]
    elif isinstance(raw, list):
        items = raw
    else:
        items = []
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        name = ALIASES.get(str(item).strip().lower().replace("_", "-"), str(item).strip().lower())
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out or list(DEFAULT_CANDIDATES)


def _signals(prompt: str) -> dict[str, bool]:
    pl = prompt.lower()
    return {
        "json": ("json" in pl) or ("schema" in pl),
        "long": len(prompt) > 800,
        "extractive": any(k in pl for k in ("extract", "fields", "fnol")),
    }


def _score(name: str, prompt: str, sig: Mapping[str, bool]) -> float:
    n = len(prompt)
    if name == "sglang":
        s = 0.95 if sig["json"] else 0.40
        if sig["long"]:
            s -= 0.10
        return round(_clamp(s), 3)
    if name == "vllm":
        s = 0.30 + min(0.65, n / 1230.0)
        if sig["json"]:
            s = min(s, 0.55)
        if sig["long"]:
            s = max(s, 0.90)
        return round(_clamp(s), 3)
    if name == "trtllm":
        s = 0.92 if sig["extractive"] else 0.34
        if sig["json"] and sig["extractive"]:
            s = 0.70
        return round(_clamp(s), 3)
    if name == "ollama":
        s = 0.28 if (sig["json"] or sig["long"] or sig["extractive"]) else 0.70
        return round(_clamp(s), 3)
    return 0.15


def _route(prompt: str, candidates: list[str]) -> tuple[str, str]:
    sig = _signals(prompt)
    have = set(candidates)
    if sig["json"] and "sglang" in have:
        return "sglang", "prompt asks for JSON or contains json/schema"
    if sig["long"] and "vllm" in have:
        return "vllm", "prompt length > 800"
    if sig["extractive"] and "trtllm" in have:
        return "trtllm", "prompt looks extractive (extract/fields/FNOL)"
    if "ollama" in have:
        return "ollama", "default conversational posture"
    chosen = candidates[0] if candidates else "ollama"
    return chosen, "first available candidate"


def act(payload: Mapping[str, Any]) -> dict[str, Any]:
    prompt = text(payload, "prompt", default=DEFAULT_PROMPT)
    if not prompt:
        prompt = DEFAULT_PROMPT
    candidates = _candidates(payload)
    sig = _signals(prompt)
    chosen, reason = _route(prompt, candidates)
    scores = {c: _score(c, prompt, sig) for c in candidates}
    return seal(
        cell="N18",
        status="ok",
        payload=payload,
        output={
            "prompt_chars": len(prompt),
            "prompt": prompt,
            "candidates": candidates,
            "signals": sig,
            "chosen": chosen,
            "reason": reason,
            "scores": scores,
            "note": NOTE,
        },
    )
