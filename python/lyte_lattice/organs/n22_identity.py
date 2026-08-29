"""N22 Identity — cite SPIFFE / SPIRE / Astrix NHI. Take the job. Do not rehost.

Not SPIRE. Not a trust bundle. Never sign. proven_trust stays false.
"""
from __future__ import annotations

from typing import Any, Mapping

from lyte_lattice.organ import seal, text

NOTE = "Unsigned. proven_trust false. Not SPIRE. a-11-oy.com is not certified."
TRUST_DOMAIN = "a11oy.net"
HINT_EXPIRES_S = 3600


def _sanitize_workload(raw: str) -> str:
    cleaned: list[str] = []
    for ch in raw.strip().lower().replace(" ", "-"):
        if ch.isalnum() or ch in "-_":
            cleaned.append(ch)
    return "".join(cleaned) or "serve"


def _mint(workload: str) -> str:
    return f"spiffe://{TRUST_DOMAIN}/ns/lyte/sa/{workload}"


def _trust_domain(spiffe_id: str) -> str:
    if not spiffe_id.startswith("spiffe://"):
        return TRUST_DOMAIN
    rest = spiffe_id[len("spiffe://") :]
    domain = rest.split("/", 1)[0].strip()
    return domain or TRUST_DOMAIN


def _shape(spiffe_id: str) -> tuple[bool, str]:
    if not spiffe_id.startswith("spiffe://"):
        return False, "must start with spiffe://"
    if spiffe_id.endswith("/"):
        return False, "no trailing slash"
    rest = spiffe_id[len("spiffe://") :]
    if "/" not in rest:
        return False, "missing path"
    domain, path = rest.split("/", 1)
    if not domain or not path:
        return False, "missing trust domain or path"
    if "://" in path or " " in spiffe_id:
        return False, "malformed spiffe id"
    if "/ns/" not in f"/{path}" and "/sa/" not in f"/{path}":
        return True, "shape ok; path missing /ns/ or /sa/"
    return True, "ok"


def act(payload: Mapping[str, Any]) -> dict[str, Any]:
    workload = _sanitize_workload(text(payload, "workload", default="serve"))
    minted = _mint(workload)
    requested = text(payload, "spiffe_id", "spiffe", "id", default="")

    if requested:
        candidate = requested.rstrip("/")
        ok, shape_note = _shape(candidate)
        spiffe_id = candidate if ok else minted
        if not ok:
            shape_note = f"rejected requested id ({shape_note}); minted {minted}"
    else:
        spiffe_id = minted
        ok, shape_note = _shape(spiffe_id)

    # Fail closed on signing. This organ never emits a signature or a bundle.
    svid = {
        "spiffe_id": spiffe_id,
        "hint_expires_in_s": HINT_EXPIRES_S,
        "bundle": None,
        "signed": False,
        "jwt": None,
        "x509": None,
        "proven_trust": False,
        "trust_domain": _trust_domain(spiffe_id),
    }
    svid["signed"] = False
    svid["proven_trust"] = False
    svid["jwt"] = None
    svid["x509"] = None
    svid["bundle"] = None

    nhi = {"kind": "workload", "astrix": False}

    return seal(
        cell="N22",
        status="ok",
        payload=payload,
        output={
            "svid": svid,
            "nhi": nhi,
            "workload": workload,
            "shape": shape_note,
            "valid": ok,
            "note": NOTE,
        },
    )
