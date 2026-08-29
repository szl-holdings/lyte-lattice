"""N5 Lattice — cite SENTRA / YAWAR. Take the job. Do not rehost.

Not a second Immune flagship. SENTRA detects. YAWAR responds.
"""
from __future__ import annotations

from typing import Any, Mapping

from lyte_lattice.organ import num, seal, text

# Built-in overlay rules. Cite SENTRA (detect) / YAWAR (respond).
RULES: list[dict[str, Any]] = [
    {
        "overlay": "yawar",
        "name": "Isolate Serve on jailbreak",
        "trigger": "guard.block",
        "action": "isolate",
        "target": "serve",
    },
    {
        "overlay": "yawar",
        "name": "Redact PII",
        "trigger": "guard.redact",
        "action": "redact",
        "target": "serve",
    },
    {
        "overlay": "sentra",
        "name": "Watch large reserves",
        "trigger": "cover.reserve>",
        "action": "human",
        "target": "cover",
        "threshold": 10000.0,
    },
    {
        "overlay": "sentra",
        "name": "Observe deep drawdown",
        "trigger": "quant.drawdown",
        "action": "observe",
        "target": "quant",
    },
    {
        "overlay": "yawar",
        "name": "Throttle Serve on injection",
        "trigger": "guard.injection",
        "action": "throttle",
        "target": "serve",
    },
]

HOLD_KEYS = {
    "isolate": "isolated",
    "throttle": "throttled",
    "human": "human",
    "redact": "redact",
}


def _as_detail(payload: Mapping[str, Any]) -> Any:
    if "detail" not in payload:
        return None
    v = payload.get("detail")
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v
    s = str(v).strip()
    if not s:
        return None
    n = num(payload, "detail", float("nan"))
    if n == n:  # not NaN
        try:
            float(s)
            return n if "." in s or "e" in s.lower() else (int(n) if n == int(n) else n)
        except ValueError:
            return s
    return s


def _detail_float(detail: Any) -> float | None:
    if isinstance(detail, (int, float)) and not isinstance(detail, bool):
        return float(detail)
    if isinstance(detail, str):
        try:
            return float(detail.strip())
        except ValueError:
            return None
    return None


def _match(rule: Mapping[str, Any], trigger: str, detail: Any) -> bool:
    want = str(rule.get("trigger") or "").strip()
    if not want:
        return False
    event = trigger.strip()
    if want.endswith(">"):
        key = want[:-1].strip()
        if not (event == want or event == key or event.startswith(key)):
            return False
        threshold = float(rule.get("threshold") if rule.get("threshold") is not None else 0.0)
        n = _detail_float(detail)
        return n is not None and n > threshold
    if want == "*" or want == event:
        return True
    if want.endswith(".*"):
        return event.startswith(want[:-2])
    if event.startswith(want):
        return True
    return False


def act(payload: Mapping[str, Any]) -> dict[str, Any]:
    trigger = text(payload, "trigger", "event", default="guard.block")
    cell = text(payload, "cell", "target", default="serve").lower() or "serve"
    detail = _as_detail(payload)

    event = {"trigger": trigger, "cell": cell, "detail": detail}
    decisions: list[dict[str, Any]] = []
    holds: dict[str, list[str]] = {"isolated": [], "throttled": [], "human": [], "redact": []}

    for rule in RULES:
        if not _match(rule, trigger, detail):
            continue
        reason = f"{str(rule['overlay']).upper()} {rule['name']}: {trigger}"
        if detail is not None:
            reason += f" ({detail})"
        decisions.append(
            {
                "overlay": rule["overlay"],
                "name": rule["name"],
                "action": rule["action"],
                "target": rule["target"],
                "reason": reason,
            }
        )
        hold_key = HOLD_KEYS.get(str(rule["action"]))
        target = str(rule["target"])
        if hold_key and target not in holds[hold_key]:
            holds[hold_key].append(target)

    return seal(
        cell="N5",
        status="ok" if decisions else "warn",
        payload=payload,
        output={
            "event": event,
            "decisions": decisions,
            "holds": holds,
        },
    )
