"""N26 Inference — wrapped inference joule.

Cited: szl-command-lab NVML/RAPL wrap. Take the job. Do not rehost.
Joule is REPORTED from the wrap, never MEASURED on this CPU hologram.
Never a fabricated joule. Compiler stays BLOCKED. Not a second meter.
"""
from __future__ import annotations

from typing import Any, Mapping

from lyte_lattice.organ import energy_channel, seal, text

NOTE = (
    "Not a second meter. Not an elevation. Not command-lab. "
    "Never a fabricated joule. Compiler stays BLOCKED."
)


def act(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    p = dict(payload or {})
    op = text(p, "op", default="wrap") or "wrap"
    channel = energy_channel()
    nvml = channel.get("nvml") if isinstance(channel.get("nvml"), dict) else {}
    # Wrap meter is the NVML/RAPL delta around a kernel on command-lab.
    # This hologram has no wrap. RAPL may exist; we still refuse to mint a wrap joule.
    return seal(
        cell="N26",
        status="ok",
        payload=p,
        honesty="REPORTED",
        output={
            "op": op,
            "energy_j": None,
            "wrap": "UNAVAILABLE",
            "channel": "LIVE",
            "rapl_honesty": channel.get("honesty"),
            "nvml_present": bool(nvml.get("present")),
            "note": (
                "Inference joule is REPORTED from command-lab /api/energy/inference. "
                "Not MEASURED on this CPU hologram. Never a fabricated joule."
            ),
            "refuse": NOTE,
        },
    )
