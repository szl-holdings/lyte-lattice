"""CLI: python3 -m lyte_lattice act --cell N8 --payload '{}'

Stdout is one JSON value. Stderr is for humans. Fail closed.
"""
from __future__ import annotations

import argparse
import json
import sys

from lyte_lattice.organ import CELLS, canonical
from lyte_lattice.registry import act, list_cells


def _payload(raw: str) -> dict:
    raw = (raw or "").strip() or "{}"
    try:
        val = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(canonical({"ok": False, "error": f"payload is not JSON: {exc}"}), file=sys.stdout)
        sys.exit(2)
    if val is None:
        return {}
    if not isinstance(val, dict):
        print(canonical({"ok": False, "error": "payload must be a JSON object"}), file=sys.stdout)
        sys.exit(2)
    return val


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lyte_lattice", description="LYTE lattice organs")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_act = sub.add_parser("act", help="run one organ")
    p_act.add_argument("--cell", required=True, help="N1–N25 or id (serve, title, energy, …)")
    p_act.add_argument("--payload", default="{}", help="JSON object")

    sub.add_parser("list", help="list organs and load status")
    sub.add_parser("selftest", help="act every N1–N25 with empty payload")

    args = parser.parse_args(argv)

    if args.cmd == "list":
        print(canonical(list_cells()))
        return 0

    if args.cmd == "selftest":
        results = []
        for n in CELLS:
            rec = act(n, {})
            results.append(
                {
                    "cell": n,
                    "id": rec.get("id"),
                    "status": rec.get("status"),
                    "honesty": rec.get("honesty"),
                    "energy_honesty": rec.get("energy_honesty"),
                    "signed": rec.get("receipt", {}).get("signed"),
                    "proven_trust": rec.get("receipt", {}).get("proven_trust"),
                    "hash": rec.get("receipt", {}).get("hash"),
                    "error": (rec.get("output") or {}).get("error") if isinstance(rec.get("output"), dict) else None,
                }
            )
        print(canonical({"ok": all(r["status"] in {"ok", "warn"} for r in results), "results": results}))
        bad = [r for r in results if r["status"] not in {"ok", "warn"}]
        if bad:
            print(f"{len(bad)} organs not ok", file=sys.stderr)
            return 1
        return 0

    rec = act(args.cell, _payload(args.payload))
    print(canonical(rec))
    return 0 if rec.get("status") in {"ok", "warn"} else 1


if __name__ == "__main__":
    sys.exit(main())
