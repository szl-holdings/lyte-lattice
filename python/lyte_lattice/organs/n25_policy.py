"""N25 Policy — cite AWS Cedar / OPA. Take the job. Do not rehost.

Not AWS Cedar production. Not OPA/Gatekeeper. Deny-overrides over baked hologram policies.
"""
from __future__ import annotations

from typing import Any, Mapping

from lyte_lattice.organ import mapping, seal, text

NOTE = "Not AWS Cedar production. Not OPA/Gatekeeper."

CLAIM_WRITE = frozenset({"claim.open", "claim.note", "claim.reserve"})
CELL_CONTROL = frozenset({"cell.isolate", "cell.release"})

# Numbered as specified. Forbid evaluated before permit (deny-overrides).
POLICIES: tuple[dict[str, str], ...] = (
    {
        "name": "permit-cover-adjuster-claim-write-when-in-force",
        "effect": "permit",
        "cedar": "permit cover-adjuster claim.open|note|reserve when in_force",
    },
    {
        "name": "forbid-claim-close-when-human-lock",
        "effect": "forbid",
        "cedar": "forbid claim.close when context.human_lock (YAWAR human)",
    },
    {
        "name": "permit-lattice-operator-cell-control",
        "effect": "permit",
        "cedar": "permit lattice-operator cell.isolate|cell.release",
    },
    {
        "name": "forbid-serve-complete-when-isolated",
        "effect": "forbid",
        "cedar": "forbid serve.complete when context.isolated",
    },
    {
        "name": "permit-retrieve-read-always",
        "effect": "permit",
        "cedar": "permit retrieve.read always",
    },
)


def _truth(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    s = str(value).strip().lower()
    if s in {"1", "true", "yes", "on"}:
        return True
    if s in {"0", "false", "no", "off", ""}:
        return False
    return default


def _norm_principal(raw: str) -> str:
    p = raw.strip().lower().replace("_", "-").replace(" ", "-")
    aliases = {
        "adjuster": "cover-adjuster",
        "cover": "cover-adjuster",
        "operator": "lattice-operator",
        "lattice": "lattice-operator",
        "serve": "serve-engine",
        "engine": "serve-engine",
        "anon": "anonymous",
    }
    return aliases.get(p, p)


def _norm_action(raw: str) -> str:
    a = raw.strip().lower().replace("_", ".").replace(" ", ".")
    return a.strip(".")


def _matches(
    name: str,
    principal: str,
    action: str,
    ctx: Mapping[str, bool],
) -> bool:
    if name == "permit-cover-adjuster-claim-write-when-in-force":
        return principal == "cover-adjuster" and action in CLAIM_WRITE and ctx["in_force"]
    if name == "forbid-claim-close-when-human-lock":
        return action == "claim.close" and ctx["human_lock"]
    if name == "permit-lattice-operator-cell-control":
        return principal == "lattice-operator" and action in CELL_CONTROL
    if name == "forbid-serve-complete-when-isolated":
        return action == "serve.complete" and ctx["isolated"]
    if name == "permit-retrieve-read-always":
        return action == "retrieve.read"
    return False


def act(payload: Mapping[str, Any]) -> dict[str, Any]:
    principal = _norm_principal(text(payload, "principal", default="cover-adjuster"))
    action = _norm_action(text(payload, "action", default="claim.close"))
    resource = text(payload, "resource", default="claim:CLM-9001") or "claim:CLM-9001"
    raw_ctx = mapping(payload, "context")
    ctx = {
        "human_lock": _truth(raw_ctx.get("human_lock", True), True),
        "isolated": _truth(raw_ctx.get("isolated", False), False),
        "in_force": _truth(raw_ctx.get("in_force", True), True),
    }

    forbid_hits: list[str] = []
    permit_hits: list[str] = []
    for policy in POLICIES:
        if not _matches(policy["name"], principal, action, ctx):
            continue
        if policy["effect"] == "forbid":
            forbid_hits.append(policy["name"])
        else:
            permit_hits.append(policy["name"])

    # Deny-overrides: any forbid wins, else a permit allows, else default-deny.
    if forbid_hits:
        decision = "deny"
        reasons = forbid_hits
    elif permit_hits:
        decision = "allow"
        reasons = permit_hits
    else:
        decision = "deny"
        reasons = ["default-deny"]

    return seal(
        cell="N25",
        status="ok",
        payload=payload,
        output={
            "decision": decision,
            "reasons": reasons,
            "principal": principal,
            "action": action,
            "resource": resource,
            "context": ctx,
            "policies_evaluated": [p["name"] for p in POLICIES],
            "note": NOTE,
        },
    )
