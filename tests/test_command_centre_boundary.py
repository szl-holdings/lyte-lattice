#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""The presentation package must not name itself as the SZLHOLDINGS/lyte source."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest import mock
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "command_centre_payload.py"
SPEC = importlib.util.spec_from_file_location("command_centre_payload", SCRIPT)
PAYLOAD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PAYLOAD)


class CommandCentreBoundary(unittest.TestCase):
    def test_missing_token_refuses_before_any_hub_write(self):
        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch.object(urllib.request, "urlopen") as urlopen:
            result = PAYLOAD.publish()
        urlopen.assert_not_called()
        self.assertFalse(result["ok"])
        self.assertEqual(result["state"], "UNAVAILABLE")
        self.assertNotIn("source", result)

    def test_token_still_blocks_and_names_lyte_services(self):
        token = "synthetic-not-a-hub-credential"
        with mock.patch.dict(os.environ, {"HF_TOKEN": token}, clear=True), \
             mock.patch.object(urllib.request, "urlopen") as urlopen:
            result = PAYLOAD.publish()
        urlopen.assert_not_called()
        self.assertFalse(result["ok"])
        self.assertEqual(result["state"], "BLOCKED")
        self.assertEqual(result["space"], "SZLHOLDINGS/lyte")
        self.assertEqual(result["source"], "szl-holdings/lyte-services")
        self.assertEqual(result["presentation_source"], "szl-holdings/lyte-lattice")
        self.assertNotEqual(result["source"], result["presentation_source"])
        self.assertNotIn(token, json.dumps(result))
        self.assertNotIn("huggingface.co/api", json.dumps(result))

    def test_operator_finish_notes_do_not_recreate_the_retired_space(self):
        text = (ROOT / "payloads" / "GROK-TERMINAL-FINISH.md").read_text(encoding="utf-8")
        self.assertNotIn(
            "Push `szl-holdings/lyte-lattice` Dockerfile-derived Space to `SZLHOLDINGS/lyte-lattice`",
            text,
        )
        self.assertIn("szl-holdings/lyte-services", text)
        self.assertIn("must not be recreated", text)


if __name__ == "__main__":
    unittest.main()
