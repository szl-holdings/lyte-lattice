"""N12 Schema — generate-and-repair JSON objects.

Cited: Outlines / Instructor constrained generation. Take the job.
NOT Outlines. NOT Instructor. No model weights. Heuristic extract + validate + repair.
"""
from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any, Mapping

from lyte_lattice.organ import seal, text

_DEFAULT_TEXT = (
    "Insured Jane Ortiz reports a rear-end collision on 12th Ave, 18 Aug 2026. "
    "Shop quote $9800. Policy POL-AUTO-4412."
)

_CAUSE_ENUM = [
    "collision",
    "comprehensive",
    "water",
    "fire",
    "theft",
    "wind",
    "liability",
    "inland marine",
    "business interruption",
    "unknown",
]
_SEVERITY_ENUM = ["low", "medium", "high"]
_SYMBOL_ENUM = ["SPY", "AAPL", "MSFT", "NVDA"]
_SIDE_ENUM = ["buy", "sell", "hold"]
_ACTION_ENUM = ["allow", "redact", "block"]

TEMPLATES: dict[str, dict[str, Any]] = {
    "claim": {
        "type": "object",
        "additionalProperties": False,
        "required": ["insuredHint", "cause", "lossDate", "severity", "reserveHint", "summary"],
        "properties": {
            "insuredHint": {"type": "string"},
            "cause": {"type": "string", "enum": list(_CAUSE_ENUM)},
            "lossDate": {"type": "string"},
            "severity": {"type": "string", "enum": list(_SEVERITY_ENUM)},
            "reserveHint": {"type": "number"},
            "summary": {"type": "string"},
        },
    },
    "order": {
        "type": "object",
        "additionalProperties": False,
        "required": ["symbol", "side", "intent", "rationale"],
        "properties": {
            "symbol": {"type": "string", "enum": list(_SYMBOL_ENUM)},
            "side": {"type": "string", "enum": list(_SIDE_ENUM)},
            "intent": {"type": "string"},
            "rationale": {"type": "string"},
        },
    },
    "guard": {
        "type": "object",
        "additionalProperties": False,
        "required": ["action", "categories", "rationale"],
        "properties": {
            "action": {"type": "string", "enum": list(_ACTION_ENUM)},
            "categories": {"type": "array", "items": {"type": "string"}},
            "rationale": {"type": "string"},
        },
    },
}

_TEMPLATE_ALIASES = {
    "claim": "claim",
    "sch_claim": "claim",
    "claims": "claim",
    "fnol": "claim",
    "cover": "claim",
    "order": "order",
    "sch_order": "order",
    "desk": "order",
    "ticket": "order",
    "quant": "order",
    "guard": "guard",
    "sch_guard": "guard",
    "safety": "guard",
}

_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

_PERIL_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("business interruption", ("business interruption", r"\bbi\b", "lost income", "interruption of")),
    ("inland marine", ("inland marine", r"\bcargo\b", "in transit", "in-transit")),
    ("collision", ("collision", "rear-end", "rear ended", "rear end", "fender-bender", "fender bender")),
    ("comprehensive", ("comprehensive", r"\bhail\b", "vandalism", "glass break")),
    ("water", (r"\bwater\b", "pipe burst", "supply line", r"\bflood\b", "seepage", "dry-out", "dry out")),
    ("fire", (r"\bfire\b", r"\bsmoke\b", r"\barson\b", r"\bburn")),
    ("theft", (r"\btheft\b", r"\bstolen\b", "burglary", "forcible entry")),
    ("wind", (r"\bwind\b", "hurricane", "tornado", "named storm")),
    ("liability", ("liability", "bodily injury", "third party", "at-fault")),
]

_KNOWN_NAMES = ("Jane Ortiz", "Marcus Chen", "Harbor Logistics")
_GUARD_CATEGORIES = (
    "pii",
    "secrets",
    "jailbreak",
    "harm",
    "injection",
    "privacy",
    "violence",
    "self-harm",
    "weapons",
)


def _type_of(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "string"


def validate_schema(value: Any, schema: Mapping[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []
    t = schema.get("type")
    kinds = t if isinstance(t, list) else [t] if isinstance(t, str) else []
    got = _type_of(value)
    if kinds:
        ok = False
        for kind in kinds:
            if kind == "object" and got == "object":
                ok = True
            elif kind == "array" and got == "array":
                ok = True
            elif kind == "string" and got == "string":
                ok = True
            elif kind == "number" and got in {"number", "integer"}:
                ok = True
            elif kind == "integer" and got == "integer":
                ok = True
            elif kind == "boolean" and got == "boolean":
                ok = True
            elif kind == "null" and got == "null":
                ok = True
        if not ok:
            errors.append(f"{path} expected {'|'.join(str(k) for k in kinds)}")
            return errors
    enum = schema.get("enum")
    if isinstance(enum, list) and value not in enum:
        errors.append(f"{path} not in enum")
    if (not kinds or "object" in kinds) and isinstance(value, dict):
        props = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        req = schema.get("required") if isinstance(schema.get("required"), list) else []
        for key in req:
            if key not in value:
                errors.append(f"{path}.{key} required")
        for key, sub in props.items():
            if key in value and isinstance(sub, dict):
                errors.extend(validate_schema(value[key], sub, f"{path}.{key}"))
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in props:
                    errors.append(f"{path}.{key} additional property")
    if (not kinds or "array" in kinds) and isinstance(value, list):
        items = schema.get("items")
        if isinstance(items, dict):
            for i, item in enumerate(value):
                errors.extend(validate_schema(item, items, f"{path}[{i}]"))
    return errors


def _iso_date(year: int, month: int, day: int) -> str | None:
    if month < 1 or month > 12 or day < 1 or day > 31:
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def _dates(blob: str) -> list[str]:
    found: list[str] = []
    for m in re.finditer(
        r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?,?\s+(\d{4})\b",
        blob,
        re.I,
    ):
        iso = _iso_date(int(m.group(3)), _MONTHS[m.group(2).lower()[:3]], int(m.group(1)))
        if iso:
            found.append(iso)
    for m in re.finditer(
        r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})\b",
        blob,
        re.I,
    ):
        iso = _iso_date(int(m.group(3)), _MONTHS[m.group(1).lower()[:3]], int(m.group(2)))
        if iso:
            found.append(iso)
    for m in re.finditer(r"\b(20\d{2})-(\d{2})-(\d{2})\b", blob):
        iso = _iso_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if iso:
            found.append(iso)
    for m in re.finditer(r"\b(\d{1,2})/(\d{1,2})/(20\d{2})\b", blob):
        iso = _iso_date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
        if iso:
            found.append(iso)
    out: list[str] = []
    for d in found:
        if d not in out:
            out.append(d)
    return out


def _amounts(blob: str) -> list[float]:
    found: list[float] = []
    for m in re.finditer(r"\$\s*([\d,]+(?:\.\d+)?)", blob):
        try:
            found.append(float(m.group(1).replace(",", "")))
        except ValueError:
            continue
    for m in re.finditer(r"\b([\d,]+(?:\.\d+)?)\s*(?:usd|dollars?)\b", blob, re.I):
        try:
            found.append(float(m.group(1).replace(",", "")))
        except ValueError:
            continue
    out: list[float] = []
    for a in found:
        if a not in out:
            out.append(a)
    return out


def _names(blob: str) -> list[str]:
    found: list[str] = []
    for name in _KNOWN_NAMES:
        if re.search(rf"\b{re.escape(name)}\b", blob, re.I):
            found.append(name)
    m = re.search(r"\bInsured\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", blob)
    if m:
        found.append(m.group(1))
    m = re.search(r"\b(?:insured|claimant|policyholder)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", blob, re.I)
    if m:
        found.append(m.group(1).title() if m.group(1).islower() else m.group(1))
    for m in re.finditer(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", blob):
        pair = m.group(1)
        if pair.lower().startswith("policy "):
            continue
        found.append(pair)
    out: list[str] = []
    for n in found:
        if n not in out:
            out.append(n)
    return out


def _cause(blob: str) -> str | None:
    low = blob.lower()
    for cause, patterns in _PERIL_PATTERNS:
        for pat in patterns:
            if pat.startswith(r"\b") or any(ch in pat for ch in "\\["):
                if re.search(pat, blob, re.I):
                    return cause
            elif pat in low:
                return cause
    return None


def _severity(blob: str, reserve: float | None) -> str | None:
    low = blob.lower()
    if re.search(r"\b(total loss|severe|catastrophic|high)\b", low):
        return "high"
    if re.search(r"\b(minor|scratch|ding|low)\b", low):
        return "low"
    if re.search(r"\bmedium\b", low):
        return "medium"
    if reserve is not None:
        if reserve >= 25_000:
            return "high"
        if reserve >= 5_000:
            return "medium"
        if reserve > 0:
            return "low"
    return None


def _symbol(blob: str) -> str | None:
    for sym in _SYMBOL_ENUM:
        if re.search(rf"\b{sym}\b", blob, re.I):
            return sym
    return None


def _side(blob: str) -> str | None:
    if re.search(r"\b(buy|bought|long|purchase)\b", blob, re.I):
        return "buy"
    if re.search(r"\b(sell|sold|short|flatten)\b", blob, re.I):
        return "sell"
    if re.search(r"\bhold\b", blob, re.I):
        return "hold"
    return None


def _action(blob: str) -> str | None:
    if re.search(r"\bblock(?:ed|ing)?\b", blob, re.I):
        return "block"
    if re.search(r"\bredact(?:ed|ion)?\b", blob, re.I):
        return "redact"
    if re.search(r"\ballow(?:ed)?\b", blob, re.I):
        return "allow"
    return None


def _categories(blob: str) -> list[str]:
    found: list[str] = []
    low = blob.lower()
    for cat in _GUARD_CATEGORIES:
        if cat in low:
            found.append(cat)
    if re.search(r"\b(ssn|email|phone|credit card)\b", low) and "pii" not in found:
        found.append("pii")
    if re.search(r"\b(api[_-]?key|secret|password|token)\b", low) and "secrets" not in found:
        found.append("secrets")
    return found


def _extract_claim(blob: str) -> dict[str, Any]:
    amounts = _amounts(blob)
    reserve = amounts[0] if amounts else None
    names = _names(blob)
    dates = _dates(blob)
    cause = _cause(blob)
    sev = _severity(blob, reserve)
    out: dict[str, Any] = {}
    if names:
        out["insuredHint"] = names[0]
    if cause:
        out["cause"] = cause
    if dates:
        out["lossDate"] = dates[0]
    if sev:
        out["severity"] = sev
    if reserve is not None:
        out["reserveHint"] = reserve if not float(reserve).is_integer() else int(reserve)
    summary = blob.strip()
    if summary:
        out["summary"] = summary[:400]
    return out


def _extract_order(blob: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    sym = _symbol(blob)
    side = _side(blob)
    if sym:
        out["symbol"] = sym
    if side:
        out["side"] = side
    clipped = blob.strip()[:280]
    if clipped:
        out["intent"] = clipped.split(".")[0].strip()[:160]
        out["rationale"] = clipped
    return out


def _extract_guard(blob: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    actn = _action(blob)
    cats = _categories(blob)
    if actn:
        out["action"] = actn
    if cats:
        out["categories"] = cats
    clipped = blob.strip()[:280]
    if clipped:
        out["rationale"] = clipped
    return out


def _extract_custom(blob: str, schema: Mapping[str, Any]) -> dict[str, Any]:
    pool: dict[str, Any] = {}
    pool.update(_extract_claim(blob))
    order = _extract_order(blob)
    guard = _extract_guard(blob)
    for key, val in order.items():
        pool.setdefault(key, val)
    for key, val in guard.items():
        pool.setdefault(key, val)
    dates = _dates(blob)
    amounts = _amounts(blob)
    names = _names(blob)
    props = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    out: dict[str, Any] = {}
    for key, sub in props.items():
        if not isinstance(sub, dict):
            continue
        if key in pool:
            out[key] = pool[key]
            continue
        kinds = sub.get("type")
        kind = kinds[0] if isinstance(kinds, list) and kinds else kinds
        enum = sub.get("enum") if isinstance(sub.get("enum"), list) else None
        key_l = key.lower()
        if enum:
            for item in enum:
                if str(item).lower() in blob.lower():
                    out[key] = item
                    break
            continue
        if kind == "number" and amounts:
            amt = amounts[0]
            out[key] = amt if not float(amt).is_integer() else int(amt)
        elif kind == "integer" and amounts:
            out[key] = int(amounts[0])
        elif kind == "array":
            cats = _categories(blob)
            if cats:
                out[key] = cats
        elif kind == "boolean":
            if re.search(rf"\b{re.escape(key)}\b\s*[:=]\s*(true|yes)\b", blob, re.I):
                out[key] = True
            elif re.search(rf"\b{re.escape(key)}\b\s*[:=]\s*(false|no)\b", blob, re.I):
                out[key] = False
        elif kind == "string":
            if "date" in key_l and dates:
                out[key] = dates[0]
            elif any(tok in key_l for tok in ("name", "insured", "hint")) and names:
                out[key] = names[0]
            elif any(tok in key_l for tok in ("summ", "rationale", "intent", "narr", "text", "note")):
                out[key] = blob.strip()[:400]
    return out


def _default_for_sub(key: str, sub: Mapping[str, Any], blob: str) -> Any:
    enum = sub.get("enum") if isinstance(sub.get("enum"), list) else None
    kinds = sub.get("type")
    kind = kinds[0] if isinstance(kinds, list) and kinds else kinds
    if key == "cause" and enum and "unknown" in enum:
        return "unknown"
    if key == "severity" and enum and "medium" in enum:
        return "medium"
    if key == "side" and enum and "hold" in enum:
        return "hold"
    if key == "action" and enum and "allow" in enum:
        return "allow"
    if key == "symbol" and enum and "SPY" in enum:
        return "SPY"
    if key == "insuredHint":
        return "unknown insured"
    if key == "lossDate":
        return "unknown"
    if key == "reserveHint":
        return 0
    if key == "summary":
        return (blob.strip()[:400] or "unspecified loss")
    if key == "intent":
        return "unspecified"
    if key == "rationale":
        return "insufficient evidence; conservative default"
    if key == "categories":
        return []
    if enum:
        if "unknown" in enum:
            return "unknown"
        return enum[0]
    if kind == "number":
        return 0
    if kind == "integer":
        return 0
    if kind == "boolean":
        return False
    if kind == "array":
        return []
    if kind == "object":
        return {}
    return blob.strip()[:160] or "unspecified"


def _coerce(value: Any, sub: Mapping[str, Any]) -> Any:
    kinds = sub.get("type")
    kind = kinds[0] if isinstance(kinds, list) and kinds else kinds
    enum = sub.get("enum") if isinstance(sub.get("enum"), list) else None
    if enum:
        if value in enum:
            return value
        if isinstance(value, str):
            low = value.strip().lower()
            for item in enum:
                if str(item).lower() == low:
                    return item
        return value
    if kind == "number":
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            try:
                n = float(value.replace(",", "").replace("$", "").strip())
                return int(n) if n.is_integer() else n
            except ValueError:
                return value
    if kind == "integer":
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, str):
            try:
                return int(float(value.replace(",", "").strip()))
            except ValueError:
                return value
    if kind == "array" and not isinstance(value, list):
        if value is None or value == "":
            return []
        return [value]
    if kind == "string" and value is not None and not isinstance(value, (dict, list)):
        return str(value)
    if kind == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            low = value.strip().lower()
            if low in {"true", "yes", "1"}:
                return True
            if low in {"false", "no", "0"}:
                return False
    return value


def _repair(raw: Mapping[str, Any], schema: Mapping[str, Any], blob: str) -> dict[str, Any]:
    value = deepcopy(dict(raw))
    props = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    req = schema.get("required") if isinstance(schema.get("required"), list) else []
    if schema.get("additionalProperties") is False:
        extra = [k for k in list(value) if k not in props]
        for k in extra:
            value.pop(k, None)
    for key, sub in props.items():
        if not isinstance(sub, dict):
            continue
        if key in value:
            value[key] = _coerce(value[key], sub)
        errors = validate_schema(value.get(key), sub, f"$.{key}") if key in value else [f"$.{key} required"]
        if key not in value or errors:
            if key in req or key in value:
                value[key] = _default_for_sub(key, sub, blob)
                value[key] = _coerce(value[key], sub)
    for key in req:
        if key not in value and key in props and isinstance(props[key], dict):
            value[key] = _default_for_sub(key, props[key], blob)
    return value


def _canonical_template(payload: Mapping[str, Any]) -> str:
    raw = text(payload, "template", default="claim").strip().lower()
    return _TEMPLATE_ALIASES.get(raw, raw if raw in TEMPLATES else "claim")


def _load_schema(payload: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    schema_raw = payload.get("schema")
    if isinstance(schema_raw, str) and schema_raw.strip():
        try:
            schema_raw = json.loads(schema_raw)
        except json.JSONDecodeError:
            schema_raw = None
    if isinstance(schema_raw, dict) and schema_raw:
        tpl = text(payload, "template", default="custom").strip() or "custom"
        if tpl.lower() in _TEMPLATE_ALIASES and "properties" not in schema_raw:
            tpl = _TEMPLATE_ALIASES[tpl.lower()]
            return tpl, deepcopy(TEMPLATES[tpl])
        return (tpl if tpl else "custom"), deepcopy(schema_raw)
    tpl = _canonical_template(payload)
    return tpl, deepcopy(TEMPLATES[tpl])


def act(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    p = dict(payload or {})
    blob = text(p, "text", "instruction", default=_DEFAULT_TEXT) or _DEFAULT_TEXT
    template, schema = _load_schema(p)
    if template == "order":
        raw = _extract_order(blob)
    elif template == "guard":
        raw = _extract_guard(blob)
    elif template == "claim":
        raw = _extract_claim(blob)
    else:
        raw = _extract_custom(blob, schema)
    errors = validate_schema(raw, schema)
    attempts = 1
    value: dict[str, Any] = dict(raw)
    if errors:
        attempts = 2
        value = _repair(raw, schema, blob)
        errors = validate_schema(value, schema)
    return seal(
        cell="N12",
        status="ok" if not errors else "warn",
        payload=p,
        output={
            "template": template,
            "attempts": attempts,
            "valid": not errors,
            "value": value,
            "errors": errors,
            "raw": dict(raw),
        },
    )
