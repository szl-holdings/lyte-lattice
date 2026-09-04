#!/usr/bin/env python3
"""Unify SZLHOLDINGS Spaces. Stdlib. Fail closed.

  python3 unify_spaces.py
  python3 unify_spaces.py --apply
"""
from __future__ import annotations

import json, os, sys, urllib.request

KEEP = ["a11oy", "killinchu", "immune", "lyte", "vertical-services"]
FOLD = {
    "immune-lattice": "immune",
    "counsel": "ayllu",
    "ayllu": "https://a11oy.net/ayllu/",
    "sentra": "vertical-services",
    "finance": "vertical-services",
    "terra": "vertical-services",
    "david-leads": "https://a-11-oy.com",
}
UNIFY = {
    "szl-command-lab": "a11oy",
    "szl-model-inference-lab": "a11oy",
    "szl-frontier": "a11oy",
    "szl-constellation": "a11oy",
}

def list_public():
    url = "https://huggingface.co/api/spaces?author=SZLHOLDINGS&limit=100"
    req = urllib.request.Request(url, headers={"User-Agent": "SZL-Unify/1.0"})
    with urllib.request.urlopen(req, timeout=20) as res:
        data = json.loads(res.read().decode())
    if isinstance(data, dict):
        data = data.get("items") or []
    return sorted((s.get("id") or "").split("/")[-1] for s in data if s.get("id"))

def plan():
    slugs = list_public()
    return {
        "bind": "BIND_AS_A11OY_PACKAGE",
        "lambda": "Conjecture 1",
        "hub_write": False,
        "policy": "pause+private, never delete",
        "measured_public": slugs,
        "count": len(slugs),
        "exact_name_duplicates": [],
        "keep": KEEP,
        "fold": FOLD,
        "unify_stragglers_into": "SZLHOLDINGS/a11oy",
        "unify": UNIFY,
        "unknown": [s for s in slugs if s not in KEEP and s not in FOLD and s not in UNIFY],
    }

def apply():
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not token:
        return {"ok": False, "state": "UNAVAILABLE", "reason": "HF_TOKEN missing. No pause. No delete."}
    return {
        "ok": False,
        "state": "BLOCKED",
        "reason": "Protected publisher only. pause+private FOLDs. Never delete.",
        "would_pause_private": sorted(list(FOLD) + list(UNIFY)),
        "would_keep_running": KEEP,
    }

if __name__ == "__main__":
    print(json.dumps(apply() if "--apply" in sys.argv else plan(), indent=2))
