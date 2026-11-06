# SPDX-License-Identifier: Apache-2.0
"""N21 Sandbox: bounded evaluation that still matches Python's own results.

The organ evaluates its AST whitelist with an interpreter instead of eval().
These tests pin two properties, offline and with the standard library only:

* every admitted expression gives exactly what CPython's own evaluation of the
  same whitelisted tree gives (value, type, or exception type);
* an expression whose integers would outgrow MAX_INT_BITS is refused quickly,
  through the same CLI that src/routes/api/act.ts spawns, instead of running
  until the route's 12 s SIGKILL.

Run: python -I tests/test_n21_sandbox.py
"""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest

PYTHON_ROOT = Path(__file__).resolve().parent.parent / "python"
sys.path.insert(0, str(PYTHON_ROOT))

from lyte_lattice.organs import n21_sandbox  # noqa: E402

# Well under TIMEOUT_MS (12 s) in src/routes/api/act.ts; interpreter start-up
# dominates. The unbounded expressions below ran past this budget before.
CLI_BUDGET_S = 6.0

ADMITTED = (
    "1 + 2 * 3",
    "(1 + 2) * 3",
    "2 ** 10",
    "2 ** -2",
    "-2 ** 2",
    "(-2) ** 3",
    "2 ** 3 ** 2",
    "7 // 2",
    "-7 // 2",
    "7 % -3",
    "-7.5 % 2",
    "7 / 2",
    "1e308 * 10",
    "0.1 + 0.2",
    "3j * 2j",
    "(1 + 2j) ** 2",
    "(-1) ** 0.5",
    "True + True",
    "-True",
    "+False",
    "not 0",
    "not 2.5",
    "0 and 1 / 0",
    "2 and 3",
    "0 or 0.0",
    "0 or 5 or 1 / 0",
    "1 < 2 < 3",
    "1 < 2 > 3",
    "3 > 2 == 2.0",
    "1 == 1 != 2",
    "None",
    "2 ** 4000",
    "3 ** 2584",
    "(-3) ** 2584",
    "1 ** (2 ** 4000)",
    "(-1) ** (2 ** 4000 + 1)",
    "0 ** 0",
    "2.0 ** (2 ** 4000)",
    "2 ** -(2 ** 4000)",
    "1 / 0",
    "1 % 0",
    "0 ** -1",
    "1j < 2",
    "2j // 1",
    "(2 ** 4000) / 3",
)


def reference(code: str):
    """CPython's own evaluation of the whitelisted tree, as eval() did before."""
    tree = ast.parse(code, mode="eval")
    try:
        value = eval(compile(tree, "<reference>", "eval"), {"__builtins__": {}}, {})  # noqa: S307
    except Exception as exc:  # the organ must raise the same exception type
        return ("raises", type(exc).__name__)
    return ("value", type(value).__name__, repr(value))


def organ(code: str):
    out = n21_sandbox.act({"code": code})["output"]
    if out["error"] is None:
        value = out["result"]
        return ("value", type(value).__name__, repr(value))
    if out["error"].startswith("illegal node type"):
        return ("refused", out["error"])
    return ("raises", out["error"].split(":", 1)[0])


def cli(code: str) -> tuple[dict, float]:
    env = dict(os.environ, PYTHONPATH=str(PYTHON_ROOT), PYTHONDONTWRITEBYTECODE="1")
    payload = json.dumps({"code": code})
    started = time.monotonic()
    proc = subprocess.run(
        [sys.executable, "-m", "lyte_lattice", "act", "--cell", "N21", "--payload", payload],
        cwd=PYTHON_ROOT, env=env, capture_output=True, text=True,
        timeout=CLI_BUDGET_S, check=False,
    )
    elapsed = time.monotonic() - started
    lines = proc.stdout.splitlines()
    if len(lines) != 1:
        raise AssertionError(f"stdout must be one JSON value; stderr={proc.stderr[-400:]!r}")
    return json.loads(lines[0]), elapsed


class N21MatchesPython(unittest.TestCase):
    def test_admitted_expressions_match_cpython(self):
        for code in ADMITTED:
            with self.subTest(code=code):
                self.assertEqual(organ(code), reference(code))

    def test_whitelist_is_unchanged(self):
        for code, node in (("__import__('os')", "Call"), ("x", "Name"), ("(1).real", "Attribute"),
                           ("'a' * 3", "Constant"), ("[1][0]", "Subscript"), ("1 << 3", "LShift"),
                           ("lambda: 1", "Lambda"), ("(x := 1)", "NamedExpr"),
                           ("1 if 0 else 2", "IfExp")):
            with self.subTest(code=code):
                out = n21_sandbox.act({"code": code})["output"]
                self.assertIs(out["allowed"], False)
                self.assertEqual(out["error"], f"illegal node type: {node}")

    def test_bound_admits_up_to_max_int_bits(self):
        bits = n21_sandbox.MAX_INT_BITS
        ok = n21_sandbox.act({"code": f"2 ** {bits - 1}"})
        self.assertEqual(ok["status"], "ok")
        self.assertEqual(ok["output"]["result"].bit_length(), bits)
        for code in (f"2 ** {bits}", f"2 ** {bits - 1} * 2", "3 ** 2585", f"-(2 ** {bits - 1}) * 2"):
            with self.subTest(code=code):
                rec = n21_sandbox.act({"code": code})
                self.assertEqual(rec["status"], "blocked")
                self.assertIs(rec["output"]["allowed"], False)
                self.assertIsNone(rec["output"]["result"])
                self.assertEqual(rec["output"]["error"], f"bound exceeded: integer above {bits} bits")


class N21RefusesUnboundedWorkQuickly(unittest.TestCase):
    def test_unbounded_integers_are_refused_before_the_route_deadline(self):
        for code in ("9**9**9", "9**9**9**9", "10**10**8", "2**20000", "(9**9)**(9**9)",
                     "((2**4000)*(2**4000))**2"):
            with self.subTest(code=code):
                rec, elapsed = cli(code)
                self.assertLess(elapsed, CLI_BUDGET_S)
                self.assertEqual(rec["cell"], "N21")
                self.assertEqual(rec["status"], "blocked")
                self.assertIs(rec["receipt"]["signed"], False)
                self.assertEqual(rec["output"]["error"],
                                 f"bound exceeded: integer above {n21_sandbox.MAX_INT_BITS} bits")

    def test_default_expression_still_runs(self):
        rec, _ = cli("1 + 2 * 3")
        self.assertEqual(rec["status"], "ok")
        self.assertEqual(rec["output"]["result"], 7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
