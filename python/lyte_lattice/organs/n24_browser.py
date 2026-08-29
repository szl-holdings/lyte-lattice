"""N24 Browser — cite Playwright / Stagehand / Browserbase. Take the job. Do not rehost.

Not Browserbase. Not Stagehand cloud. Playwright lives in the Node console.
This organ receipts the plan. It does not launch Chromium.
"""
from __future__ import annotations

import shutil
from typing import Any, Mapping
from urllib.parse import urlparse

from lyte_lattice.organ import seal, text

NOTE = "Playwright lives in the Node console. This organ receipts the plan. Not Browserbase."
DEFAULT_URL = "https://a11oy.net"
ACTIONS = frozenset({"goto", "snapshot", "click"})
CHROMIUM_BINS = ("chromium", "chromium-browser", "google-chrome", "chrome")


def _chromium() -> dict[str, Any]:
    for name in CHROMIUM_BINS:
        path = shutil.which(name)
        if path:
            return {"present": True, "which": path, "bin": name}
    return {"present": False, "which": None, "bin": None}


def _http_url(url: str) -> bool:
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        return False
    if not parsed.netloc:
        return False
    return True


def act(payload: Mapping[str, Any]) -> dict[str, Any]:
    url = text(payload, "url", default=DEFAULT_URL) or DEFAULT_URL
    action = text(payload, "action", default="snapshot").strip().lower()
    if action not in ACTIONS:
        action = "snapshot"
    selector = text(payload, "selector", default="") or None
    wait_selector = selector or "body"
    click_selector = selector or "text=Proof"
    chromium = _chromium()

    if not _http_url(url):
        return seal(
            cell="N24",
            status="blocked",
            payload=payload,
            output={
                "url": url,
                "action": action,
                "steps": [],
                "launched": False,
                "playwright_in_organ": False,
                "chromium": chromium,
                "error": "only http(s) URLs",
                "note": NOTE,
            },
        )

    steps: list[dict[str, Any]] = [
        {"action": "goto", "url": url, "wait_until": "domcontentloaded"},
        {"action": "wait_for", "selector": wait_selector},
        {"action": "snapshot", "kind": "accessibility"},
    ]
    if action == "click":
        steps.append({"action": "click", "selector": click_selector})

    return seal(
        cell="N24",
        status="ok",
        payload=payload,
        output={
            "url": url,
            "action": action,
            "steps": steps,
            "launched": False,
            "playwright_in_organ": False,
            "chromium": chromium,
            "note": NOTE,
        },
    )
