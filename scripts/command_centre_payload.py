#!/usr/bin/env python3
"""Command Centre finish payload. Stdout is honest JSON. Fail closed.

Grok-in-terminal: run --check first. --publish-space only with HF_TOKEN.
This script never invents RUNNING, joules, DSSE, or GPU trains.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

WAVES = {
    "W1": ["N1", "N2", "N3", "N4", "N5", "N6", "N7", "N8", "N9"],
    "W2": ["N10", "N11", "N12", "N13", "N14", "N15", "N16", "N17", "N18"],
    "W3": ["N19", "N20", "N21", "N22", "N23", "N24", "N25", "N26", "N27"],
}

LANES = [
    "szl-holdings/a11oy",
    "szl-holdings/lyte-lattice",
    "szl-holdings/holographic-unify",
    "szl-holdings/szl-hf-frontier",
    "szl-holdings/immune",
    "szl-holdings/hatun-mcp",
    "szl-holdings/szl-forge",
    "szl-holdings/vertical-services",
    "szl-holdings/szl-khipu",
    "szl-holdings/.github",
]

HUB = [
    "https://huggingface.co/SZLHOLDINGS",
    "https://huggingface.co/spaces/SZLHOLDINGS/a11oy",
    "https://huggingface.co/spaces/SZLHOLDINGS/lyte-lattice",
    "https://huggingface.co/SZLHOLDINGS/SZL-Khipu-1.5B",
]


def probe(url: str, timeout: float = 6.0) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "AlloyStateFabric/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            code = getattr(res, "status", 200)
            return {"url": url, "status": code, "state": "LIVE" if 200 <= code < 300 else "INCOMPLETE"}
    except Exception as err:
        return {"url": url, "status": None, "state": "UNAVAILABLE", "detail": str(err)}


def check() -> dict:
    token = bool(os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN"))
    return {
        "bind": "BIND_AS_A11OY_PACKAGE",
        "lambda": "Conjecture 1",
        "doctrine": "v11 LOCKED",
        "signer": "UNSIGNED-honest",
        "proven_trust": False,
        "product_certified": False,
        "hub_write": False,
        "hf_token_present": token,
        "waves": WAVES,
        "lanes": LANES,
        "hub_probes": [probe(u) for u in HUB],
        "publish": "UNAVAILABLE" if not token else "TOKEN_PRESENT_NOT_PUBLISHED",
        "note": "This plane does not write the Hub. --publish-space requires HF_TOKEN and exact commit readback.",
    }


def publish() -> dict:
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not token:
        return {
            "ok": False,
            "state": "UNAVAILABLE",
            "reason": "HF_TOKEN missing. Hub write refused. Space not mocked as RUNNING.",
        }
    return {
        "ok": False,
        "state": "BLOCKED",
        "reason": "Protected publisher only. This script refuses a silent Hub write even with a token. Hand the tip to the central publisher and wait for exact commit readback.",
        "space": "SZLHOLDINGS/lyte-lattice",
        "source": "szl-holdings/lyte-lattice",
    }


def main(argv: list[str]) -> int:
    if "--publish-space" in argv:
        out = publish()
    else:
        out = check()
    print(json.dumps(out, indent=2))
    return 0 if out.get("ok", True) is not False or out.get("state") == "UNAVAILABLE" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
