"""N11 Tune — LoRA / QLoRA adapter pack receipts.

Cited: Unsloth LoRA / QLoRA. Take the job. Do not rehost Unsloth.
NOT Unsloth. NOT a Hub-certified trainer. NO GPU fine-tune.
"""
from __future__ import annotations

import json
from typing import Any, Mapping

from lyte_lattice.organ import num, seal, text

# Baked claims + lattice desk snippets. Hologram corpus, not a training run.
_BAKED: list[dict[str, str]] = [
    {
        "instruction": "Use the P&C Claims Desk Manual.",
        "input": "When is FNOL opened?",
        "output": (
            "First notice of loss (FNOL) is opened the hour the insured reports. "
            "Capture loss date, location, narrative, and third parties before coverage is confirmed."
        ),
    },
    {
        "instruction": "Use the P&C Claims Desk Manual.",
        "input": "What does auto collision cover?",
        "output": (
            "Auto collision covers at-fault and not-at-fault impacts with another vehicle or object. "
            "A typical bumper-and-radiator repair reserve is about $12,000, never above policy limit."
        ),
    },
    {
        "instruction": "Use the SENTRA / YAWAR Bind Spec.",
        "input": "What does SENTRA detect?",
        "output": (
            "SENTRA is the detection overlay. It watches Guard verdicts, Cover reserve spikes, "
            "Serve prompt injections, and Quant leverage-like drawdowns."
        ),
    },
    {
        "instruction": "Use the SENTRA / YAWAR Bind Spec.",
        "input": "What does YAWAR do?",
        "output": (
            "YAWAR is the response overlay. Actions: isolate, throttle, redact, human, observe. "
            "Binds are directed: Guard to Lattice is SENTRA, Lattice to Serve is YAWAR."
        ),
    },
    {
        "instruction": "Use the P&C Claims Desk Manual.",
        "input": "Pipe burst, kitchen ceiling down. What peril?",
        "output": (
            "Home water — sudden pipe burst is covered; long-term seepage is not. "
            "Open FNOL, set a dry-out reserve, confirm the policy is in force."
        ),
    },
]

_DEFAULT_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj"]
_SYSTEM_ADDENDUM = (
    "You are the LYTE claims and lattice desk. Prefer FNOL language, named perils, "
    "and bind overlay terms. Be terse."
)
_FEWSHOT = [
    {
        "user": "Pipe burst, kitchen ceiling down. What peril?",
        "assistant": (
            "Home water — sudden pipe burst is covered; long-term seepage is not. "
            "Open FNOL, set a dry-out reserve, confirm the policy is in force."
        ),
    }
]
_NOTE = (
    "Not a Hub-certified trainer. Bind changes Serve system+few-shot in the TS cell; "
    "this organ receipts the pack."
)
# Hologram LoRA shapes. in=out=4096 is an ESTIMATE, not measured.
_IN_FEATURES = 4096
_OUT_FEATURES = 4096


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value) and value != 0
    s = str(value).strip().lower()
    if s in {"1", "true", "yes", "y", "on"}:
        return True
    if s in {"0", "false", "no", "n", "off", ""}:
        return False
    return default


def _as_modules(payload: Mapping[str, Any]) -> list[str]:
    raw = payload.get("modules")
    if raw is None or raw == "":
        return list(_DEFAULT_MODULES)
    if isinstance(raw, (list, tuple)):
        mods = [str(x).strip() for x in raw if str(x).strip()]
        return mods or list(_DEFAULT_MODULES)
    s = str(raw).strip()
    if not s:
        return list(_DEFAULT_MODULES)
    parts = [p.strip() for p in s.split(",") if p.strip()]
    return parts or list(_DEFAULT_MODULES)


def _as_docs(payload: Mapping[str, Any]) -> list[str]:
    raw = payload.get("docs")
    if raw is None or raw == "":
        return []
    if isinstance(raw, (list, tuple)):
        return [str(d).strip() for d in raw if str(d).strip()]
    s = str(raw).strip()
    return [s] if s else []


def _jsonl_preview(docs: list[str]) -> str:
    rows: list[str] = [json.dumps(row, ensure_ascii=False) for row in _BAKED]
    for i, doc in enumerate(docs):
        snippet = doc[:280]
        rows.append(
            json.dumps(
                {
                    "instruction": "Use the operator-supplied desk note.",
                    "input": snippet,
                    "output": snippet,
                },
                ensure_ascii=False,
            )
        )
        if i >= 7:
            break
    return "\n".join(rows)


def _param_count_est(rank: int, n_modules: int) -> dict[str, Any]:
    value = int(rank) * (_IN_FEATURES + _OUT_FEATURES) * int(n_modules)
    return {
        "value": value,
        "unit": "params",
        "label": "ESTIMATE not measured",
        "honesty": "ESTIMATE",
        "formula": "rank * (in + out) * n_modules",
        "in": _IN_FEATURES,
        "out": _OUT_FEATURES,
        "rank": int(rank),
        "n_modules": int(n_modules),
        "note": "Hologram number. in=out=4096 assumed. Not measured. Not a trained adapter.",
    }


def act(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    p = dict(payload or {})
    name = text(p, "name", default="Claims desk LoRA pack") or "Claims desk LoRA pack"
    rank_n = num(p, "rank", 16.0)
    alpha_n = num(p, "alpha", 32.0)
    rank = int(rank_n) if rank_n == rank_n else 16
    alpha = int(alpha_n) if alpha_n == alpha_n else 32
    if "rank" not in p or p.get("rank") in (None, ""):
        rank = 16
    if "alpha" not in p or p.get("alpha") in (None, ""):
        alpha = 32
    qlora = _as_bool(p.get("qlora"), False)
    modules = _as_modules(p)
    docs = _as_docs(p)
    preview = _jsonl_preview(docs)
    adapter = {
        "name": name,
        "rank": rank,
        "alpha": alpha,
        "qlora": qlora,
        "modules": modules,
        "bound": True,
        "jsonl_preview": preview,
        "system_addendum": _SYSTEM_ADDENDUM,
        "fewshot": [dict(shot) for shot in _FEWSHOT],
        "param_count_est": _param_count_est(rank, len(modules)),
    }
    return seal(
        cell="N11",
        status="ok",
        payload=p,
        output={"adapter": adapter, "note": _NOTE},
    )
