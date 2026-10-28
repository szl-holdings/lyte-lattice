# SPDX-License-Identifier: Apache-2.0
"""Offline contract tests for the lyte_lattice CLI that /api/act spawns.

src/routes/api/act.ts runs `python3 -m lyte_lattice act --cell C --payload P`
with cwd and PYTHONPATH set to python/ and parses the last stdout line as JSON.
These tests run that same command with the standard library only: no network,
no credentials and no provider calls.

Run: python -I tests/test_lyte_cli_contract.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

PYTHON_ROOT = Path(__file__).resolve().parent.parent / "python"
TIMEOUT_S = 12  # TIMEOUT_MS in src/routes/api/act.ts
RUNNABLE = {"ok", "warn"}
STATUSES = {"ok", "warn", "error", "blocked"}


def cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, PYTHONPATH=str(PYTHON_ROOT), PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run(
        [sys.executable, "-m", "lyte_lattice", *args],
        cwd=PYTHON_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_S,
        check=False,
    )


class LyteCliContract(unittest.TestCase):
    cells: list[str] = []

    @classmethod
    def setUpClass(cls) -> None:
        proc = cli("list")
        if proc.returncode != 0:
            raise AssertionError(f"list exited {proc.returncode}: {proc.stderr[-400:]}")
        cls.cells = [row["cell"] for row in json.loads(proc.stdout)]

    def one_json(self, proc: subprocess.CompletedProcess[str]):
        lines = proc.stdout.splitlines()
        self.assertEqual(len(lines), 1, f"stdout must be one JSON value; stderr={proc.stderr[-400:]!r}")
        return json.loads(lines[0])

    def assert_no_fabricated_joule(self, rec) -> None:
        joule = rec["energy_joule"]
        if rec["cell"] == "N13" and rec["energy_honesty"] == "MEASURED":
            # Only a real RAPL energy_uj read may produce a joule.
            self.assertEqual(rec["output"]["rapl"]["honesty"], "MEASURED")
            self.assertIsInstance(joule, float)
            self.assertGreaterEqual(joule, 0.0)
        else:
            self.assertIsNone(joule)
            self.assertEqual(rec["energy_honesty"], "UNAVAILABLE")

    def assert_unsigned_receipt(self, rec, cell: str) -> None:
        self.assertEqual(rec["cell"], cell)
        self.assertIn(rec["status"], STATUSES)
        self.assertEqual(rec["lambda"], "Conjecture 1")
        receipt = rec["receipt"]
        self.assertIs(receipt["signed"], False)
        self.assertIs(receipt["proven_trust"], False)
        self.assertEqual(receipt["kind"], "UNSIGNED-honest")
        self.assertEqual(receipt["lambda"], "Conjecture 1")
        self.assertTrue(receipt["hash"].startswith("UNSIGNED-honest:"), receipt["hash"])
        self.assert_no_fabricated_joule(rec)

    def test_list_is_one_json_value_with_every_organ_loaded(self):
        proc = cli("list")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        rows = self.one_json(proc)
        cells = [row["cell"] for row in rows]
        self.assertGreaterEqual(len(cells), 27)
        self.assertEqual(cells, [f"N{i}" for i in range(1, len(cells) + 1)])
        for row in rows:
            self.assertEqual(row["loaded"], "ok", row)

    def test_every_organ_returns_one_unsigned_receipt(self):
        self.assertGreaterEqual(len(self.cells), 27)
        for cell in self.cells:
            with self.subTest(cell=cell):
                proc = cli("act", "--cell", cell, "--payload", "{}")
                rec = self.one_json(proc)
                self.assert_unsigned_receipt(rec, cell)
                self.assertEqual(proc.returncode, 0 if rec["status"] in RUNNABLE else 1)

    def test_ids_and_lowercase_resolve_to_the_same_cell(self):
        for alias in ("N8", "n8", "title"):
            with self.subTest(alias=alias):
                proc = cli("act", "--cell", alias, "--payload", "{}")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assert_unsigned_receipt(self.one_json(proc), "N8")

    def test_non_json_payload_exits_2_before_any_organ_runs(self):
        cases = (
            ("{not json", "payload is not JSON"),
            ("[1, 2]", "payload must be a JSON object"),
        )
        for raw, error in cases:
            with self.subTest(payload=raw):
                proc = cli("act", "--cell", "N8", "--payload", raw)
                self.assertEqual(proc.returncode, 2)
                body = self.one_json(proc)
                self.assertIs(body["ok"], False)
                self.assertTrue(body["error"].startswith(error), body)
                self.assertNotIn("receipt", body)

    def test_unknown_cell_fails_closed(self):
        for cell in ("N99", "not-an-organ"):
            with self.subTest(cell=cell):
                proc = cli("act", "--cell", cell, "--payload", "{}")
                self.assertEqual(proc.returncode, 1)
                rec = self.one_json(proc)
                self.assert_unsigned_receipt(rec, cell)
                self.assertEqual(rec["status"], "blocked")
                self.assertEqual(rec["id"], "unknown")
                self.assertEqual(rec["output"], {"error": "unknown cell"})

    def test_energy_joule_comes_only_from_a_real_rapl_read(self):
        proc = cli("act", "--cell", "energy", "--payload", "{}")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        rec = self.one_json(proc)
        self.assert_unsigned_receipt(rec, "N13")
        out = rec["output"]
        if out["rapl"]["honesty"] != "MEASURED":
            # NVML watts are never converted into joules.
            self.assertIsNone(out["joule"])
            self.assertEqual(out["honesty"], "UNAVAILABLE")
            self.assertIsNone(rec["energy_joule"])

    def test_wrap_joule_is_reported_and_gpu_train_stays_blocked(self):
        wrap = self.one_json(cli("act", "--cell", "N26", "--payload", "{}"))
        self.assertEqual(wrap["honesty"], "REPORTED")
        self.assertIsNone(wrap["output"]["energy_j"])
        proc = cli("act", "--cell", "N27", "--payload", "{}")
        self.assertEqual(proc.returncode, 1)
        train = self.one_json(proc)
        self.assert_unsigned_receipt(train, "N27")
        self.assertEqual(train["status"], "blocked")
        self.assertEqual(train["honesty"], "UNAVAILABLE")
        self.assertIs(train["output"]["trained"], False)
        self.assertIsNone(train["output"]["weights"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
