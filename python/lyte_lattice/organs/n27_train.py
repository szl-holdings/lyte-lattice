"""N27 Train — receipted GPU train gate.

Cited: szl-forge Unsloth QLoRA; szl-gpu-bridge. Take the job. Do not rehost Unsloth.
Local silhouette SGD is MEASURED in Alloy State Fabric. GPU train is UNAVAILABLE.
CUDA absent. WILLAY/KHIPU-R3/Waman NOT_APPROVED. gpu-bridge NEVER_DISPATCH.
Never a fabricated train. Compiler stays BLOCKED.
"""
from __future__ import annotations

import shutil
from typing import Any, Mapping

from lyte_lattice.organ import seal, text

NOTE = (
    "Not Unsloth. Not a Hub-certified trainer. Never a fabricated train. "
    "gpu-bridge NEVER_DISPATCH. Compiler stays BLOCKED."
)


def act(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    p = dict(payload or {})
    op = text(p, "op", default="gate") or "gate"
    smi = shutil.which("nvidia-smi")
    return seal(
        cell="N27",
        status="blocked",
        payload=p,
        honesty="UNAVAILABLE",
        output={
            "op": op,
            "trained": False,
            "weights": None,
            "cuda": False,
            "nvidia_smi": smi is not None,
            "registry": "NOT_APPROVED",
            "gpu_bridge": "NEVER_DISPATCH",
            "refused": ["willay", "khipu-r3", "waman"],
            "note": (
                "GPU train BLOCKED. CUDA runtime absent on this hologram. "
                "Local SGD silhouettes are MEASURED in Alloy State Fabric, not here. "
                + NOTE
            ),
        },
    )
