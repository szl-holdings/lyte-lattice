"""N6 Cover — cited Guidewire P&C. Not InsuranceSuite. Not a live carrier core."""
from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping

from lyte_lattice.organ import num, seal, text

POLICIES: dict[str, dict[str, Any]] = {
    "POL-AUTO-4412": {
        "id": "pol_auto",
        "number": "POL-AUTO-4412",
        "insured": "Jane Ortiz",
        "line": "auto",
        "premium": 1840,
        "limit": 250_000,
        "deductible": 500,
        "status": "in-force",
        "effective": "2026-01-12",
        "expiry": "2027-01-12",
        "perils": ["collision", "comprehensive", "liability"],
    },
    "POL-HOME-1088": {
        "id": "pol_home",
        "number": "POL-HOME-1088",
        "insured": "Marcus Chen",
        "line": "home",
        "premium": 2260,
        "limit": 800_000,
        "deductible": 2500,
        "status": "in-force",
        "effective": "2025-09-01",
        "expiry": "2026-09-01",
        "perils": ["water", "fire", "theft", "wind"],
    },
    "POL-CML-2201": {
        "id": "pol_cml",
        "number": "POL-CML-2201",
        "insured": "Harbor Logistics LLC",
        "line": "commercial",
        "premium": 18400,
        "limit": 2_000_000,
        "deductible": 10000,
        "status": "in-force",
        "effective": "2026-03-01",
        "expiry": "2027-03-01",
        "perils": ["liability", "property", "inland marine", "business interruption"],
    },
}

_BY_ID = {p["id"]: p for p in POLICIES.values()}

PERIL_MATRIX: dict[str, str] = {
    "collision": "Auto collision covers at-fault and not-at-fault impacts with another vehicle or object.",
    "comprehensive": "Comprehensive covers theft, hail, flood to the vehicle, and vandalism.",
    "liability": "Liability covers third-party bodily injury and property damage on the form.",
    "uninsured": "Uninsured motorist is an auto-form endorsement, not a home or commercial named peril.",
    "water": "Home water covers sudden pipe burst, not long-term seepage.",
    "fire": "Fire is covered unless the fire is arson by the insured.",
    "theft": "Theft requires signs of forcible entry on homeowners.",
    "wind": "Wind is covered subject to hurricane deductible in coastal counties.",
    "property": "Commercial property covers buildings and contents named on the form.",
    "inland marine": "Commercial inland marine covers cargo in transit.",
    "business interruption": "Business interruption requires a covered property peril first.",
}

_CAUSE_PAIRS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"colli|rear-end|fender|hit my|hit another|crash"), "collision"),
    (re.compile(r"hail|stolen vehicle|break-in.*car|vandal"), "comprehensive"),
    (re.compile(r"water|pipe|flood|leak|sprinkler|supply line"), "water"),
    (re.compile(r"fire|smoke|burn"), "fire"),
    (re.compile(r"theft|stolen|burgl"), "theft"),
    (re.compile(r"wind|storm|tornado|hurricane"), "wind"),
    (re.compile(r"cargo|inland|shipment"), "inland marine"),
    (re.compile(r"interrupt|cannot operate|shutdown"), "business interruption"),
    (re.compile(r"slip|injury|bodily|third[- ]party|liability"), "liability"),
]

_CAUSE_ALIAS = {
    "pipe": "water",
    "pipe burst": "water",
    "burst": "water",
    "flood": "water",
    "leak": "water",
    "crash": "collision",
    "rear end": "collision",
    "rear-end": "collision",
    "bi": "business interruption",
    "business-interruption": "business interruption",
    "cargo": "inland marine",
    "inland_marine": "inland marine",
    "inland-marine": "inland marine",
}

_BASE_RESERVE = {"auto": 8_500, "home": 18_000, "commercial": 45_000}
_NOTE = "Cited Guidewire P&C core. Not InsuranceSuite. Not a live carrier core."


def _norm_cause(raw: str) -> str:
    s = re.sub(r"[_]+", " ", raw.strip().lower())
    s = re.sub(r"\s+", " ", s)
    return _CAUSE_ALIAS.get(s, s)


def infer_cause(narrative: str) -> str:
    n = narrative.lower()
    for pat, cause in _CAUSE_PAIRS:
        if pat.search(n):
            return cause
    return "unknown"


def _lookup_policy(payload: Mapping[str, Any]) -> tuple[str, dict[str, Any] | None]:
    raw = payload.get("policy")
    if isinstance(raw, dict):
        key = text(raw, "number", "id", "policy", default="")
    else:
        key = text(payload, "policy", "policyId", "policy_id", "number", default="POL-HOME-1088")
    key = key.strip()
    if not key:
        key = "POL-HOME-1088"
    upper = key.upper()
    hit = POLICIES.get(upper) or POLICIES.get(key) or _BY_ID.get(key) or _BY_ID.get(key.lower())
    if hit is None:
        for p in POLICIES.values():
            if p["number"].upper() == upper or p["id"].lower() == key.lower():
                hit = p
                break
    return key, hit


def _coverage(policy: dict[str, Any] | None, cause: str) -> tuple[bool, str]:
    if policy is None:
        return False, "unknown policy"
    if policy["status"] != "in-force":
        return False, f"lapsed: policy {policy['number']} is {policy['status']}"
    if cause in ("", "unknown"):
        return False, "peril not on form: cause of loss is not classified"
    allowed = {p.lower() for p in policy["perils"]}
    if cause.lower() not in allowed:
        return False, (
            f"peril not on form: {cause} is not a covered peril on {policy['line']} policy {policy['number']}"
        )
    return True, f"{cause} matches {policy['line']} perils on {policy['number']}"


def _suggested_reserve(narrative: str, policy: dict[str, Any]) -> float:
    nums = [
        float(m.group(1).replace(",", ""))
        for m in re.finditer(r"\$?\s?([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.\d{2})?", narrative)
    ]
    in_band = [n for n in nums if 250 <= n <= policy["limit"]]
    if in_band:
        return min(policy["limit"], max(in_band))
    return min(float(policy["limit"]), float(_BASE_RESERVE.get(policy["line"], 10_000)))


def _clamp_reserve(value: float, limit: float) -> float:
    if value != value:  # NaN
        return 0.0
    return max(0.0, min(float(limit), float(value)))


def _claim_number(policy_no: str, narrative: str, cause: str) -> str:
    h = hashlib.sha256(f"{policy_no}|{cause}|{narrative}".encode("utf-8")).hexdigest()
    n = 9001 + (int(h[:8], 16) % 999)
    return f"CLM-{n}"


def _claim(
    *,
    policy: dict[str, Any] | None,
    cause: str,
    narrative: str,
    status: str,
    reserve: float,
) -> dict[str, Any]:
    number = policy["number"] if policy else "UNKNOWN"
    return {
        "number": _claim_number(number, narrative, cause),
        "policy": number,
        "policyId": policy["id"] if policy else None,
        "status": status,
        "cause": cause,
        "narrative": narrative,
        "reserve": reserve,
        "paid": 0,
    }


def act(payload: Mapping[str, Any]) -> dict[str, Any]:
    action = text(payload, "action", default="coverage").strip().lower()
    if action not in {"coverage", "fnol", "reserve"}:
        action = "coverage"
    narrative = text(
        payload,
        "narrative",
        "note",
        "loss",
        default="Upstairs supply line failed overnight. Ceiling in kitchen down.",
    )
    requested, policy = _lookup_policy(payload)
    cause_raw = text(payload, "cause", "peril", default="")
    has_narrative = any(k in payload for k in ("narrative", "note", "loss"))
    if cause_raw:
        cause = _norm_cause(cause_raw)
    elif not has_narrative:
        inferred = infer_cause(narrative)
        cause = inferred if inferred != "unknown" else "water"
    else:
        cause = infer_cause(narrative)
    if not cause:
        cause = "water"

    covered, reason = _coverage(policy, cause)
    status = "ok" if covered else "warn"

    reserve_in = payload.get("reserve", None)
    has_reserve = reserve_in is not None and str(reserve_in).strip() != ""
    limit = float(policy["limit"]) if policy else 0.0

    claim: dict[str, Any] | None = None
    if action == "fnol":
        if has_reserve and policy:
            reserve = _clamp_reserve(num(payload, "reserve", 0.0), limit)
        elif policy and covered:
            reserve = _suggested_reserve(narrative, policy)
        else:
            reserve = 0.0
        claim_status = "open" if covered else "fnol"
        claim = _claim(policy=policy, cause=cause, narrative=narrative, status=claim_status, reserve=reserve)
        if policy and reserve > 0.2 * limit:
            status = "warn"
            reason = f"{reason} Reserve {reserve:.0f} exceeds 20% of limit {limit:.0f}."
    elif action == "reserve":
        raw = num(payload, "reserve", 0.0)
        reserve = _clamp_reserve(raw, limit) if policy else 0.0
        if policy and raw > limit:
            reason = f"{reason} Reserve clamped from {raw:.0f} to limit {limit:.0f}."
        if policy and reserve > 0.2 * limit:
            status = "warn"
            reason = f"{reason} Reserve {reserve:.0f} exceeds 20% of limit {limit:.0f}."
        elif not covered:
            status = "warn"
        claim_status = "open" if covered else "fnol"
        claim = _claim(policy=policy, cause=cause, narrative=narrative, status=claim_status, reserve=reserve)

    output: dict[str, Any] = {
        "action": action,
        "policy": {
            "id": policy["id"],
            "number": policy["number"],
            "insured": policy["insured"],
            "line": policy["line"],
            "limit": policy["limit"],
            "deductible": policy["deductible"],
            "status": policy["status"],
            "perils": list(policy["perils"]),
        }
        if policy
        else {"number": requested},
        "covered": covered,
        "reason": reason,
        "peril_matrix": dict(PERIL_MATRIX),
        "cause": cause,
        "narrative": narrative,
        "note": _NOTE,
    }
    if claim is not None:
        output["claim"] = claim
    return seal(cell="N6", status=status, payload=payload, output=output)
