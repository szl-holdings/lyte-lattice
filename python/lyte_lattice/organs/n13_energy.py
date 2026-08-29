"""N13 Energy — RAPL / NVML joule channel.

Cited: RAPL / NVML. Take the job. Do not rehost a fake probe.
Probe is LIVE. Joule is UNAVAILABLE unless RAPL actually reads energy_uj.
NEVER invent a joule number. NEVER convert NVML watts into joules.
"""
from __future__ import annotations

import os
from typing import Any, Mapping

from lyte_lattice.organ import energy_channel, seal, text


def _uname() -> dict[str, str]:
    if not hasattr(os, "uname"):
        return {
            "sysname": "unknown",
            "nodename": "unknown",
            "release": "unknown",
            "version": "unknown",
            "machine": "unknown",
        }
    u = os.uname()
    return {
        "sysname": getattr(u, "sysname", "") or "unknown",
        "nodename": getattr(u, "nodename", "") or "unknown",
        "release": getattr(u, "release", "") or "unknown",
        "version": getattr(u, "version", "") or "unknown",
        "machine": getattr(u, "machine", "") or "unknown",
    }


def act(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    p = dict(payload or {})
    op = text(p, "op", default="probe") or "probe"
    channel = energy_channel()
    powercap_path = "/sys/class/powercap"
    output = dict(channel)
    output["op"] = op
    output["host"] = _uname()
    output["powercap_exists"] = os.path.isdir(powercap_path)
    output["powercap_path"] = powercap_path
    return seal(cell="N13", status="ok", payload=p, output=output)
