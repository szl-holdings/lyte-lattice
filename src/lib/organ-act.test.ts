import assert from "node:assert/strict";
import { test } from "node:test";
import { Route, buildOrganEnv } from "../routes/api/act.ts";

const handlers = Route.options.server!.handlers as unknown as {
  POST: (context: { request: Request }) => Promise<Response>;
};
const handle = handlers.POST;

function request(value: unknown, headers: Record<string, string> = {}) {
  return new Request("http://localhost/api/act", {
    method: "POST",
    headers: { "content-type": "application/json", ...headers },
    body: JSON.stringify(value),
  });
}

const CROSS_SITE = {
  "sec-fetch-site": "cross-site",
  "sec-fetch-mode": "no-cors",
  origin: "https://evil.example",
};

test("organ route rejects non-object request documents", async () => {
  for (const value of [null, [], true, 42, "N8"]) {
    const response = await handle({ request: request(value) });
    assert.equal(response.status, 400);
    assert.equal((await response.json()).ok, false);
  }
});

test("organ route rejects payloads the Python object contract cannot accept", async () => {
  for (const payload of [[], true, 42, "text"]) {
    const response = await handle({ request: request({ cell: "N8", payload }) });
    assert.equal(response.status, 400);
    assert.equal((await response.json()).error, "payload must be a JSON object");
  }
});

test("organ route bounds the UTF-8 bytes sent to the Python process", async () => {
  // This fits the former character limit but exceeds Linux's single-argument
  // limit, so the old path attempted spawn and returned an E2BIG server error.
  const payload = { text: "漢".repeat(50_000) };
  assert.ok(JSON.stringify(payload).length < 64_000);
  assert.ok(Buffer.byteLength(JSON.stringify(payload), "utf8") > 131_072);
  const response = await handle({ request: request({ cell: "N8", payload }) });
  assert.equal(response.status, 413);
  assert.equal((await response.json()).error, "payload too large");
});

test("valid Unicode and null/default payloads retain the organ receipt contract", async () => {
  for (const payload of [{ text: "measured 漢字 🌌" }, null, undefined]) {
    const response = await handle({ request: request({ cell: "N8", payload }) });
    assert.equal(response.status, 200);
    const receipt = await response.json();
    assert.equal(receipt.cell, "N8");
    assert.equal(receipt.receipt.signed, false);
    assert.equal(receipt.receipt.proven_trust, false);
  }
});

test("organ route denies a cross-site scripted POST before reading the body", async () => {
  const runs = await handle({
    request: request({ cell: "N21", payload: { code: "2**10" } }, CROSS_SITE),
  });
  assert.equal(runs.status, 403);
  assert.equal((await runs.json()).error, "cross-site request blocked");
  // An oversize payload returns 413 without the guard; 403 proves the guard runs first.
  const oversize = await handle({
    request: request({ cell: "N8", payload: { text: "x".repeat(64_001) } }, CROSS_SITE),
  });
  assert.equal(oversize.status, 403);
});

test("organ route denies a same-site sibling scripted POST", async () => {
  const response = await handle({
    request: request(
      { cell: "N21", payload: { code: "2**10" } },
      { "sec-fetch-site": "same-site", "sec-fetch-mode": "cors" },
    ),
  });
  assert.equal(response.status, 403);
  assert.equal((await response.json()).error, "cross-site request blocked");
});

test("organ route requires a JSON content type", async () => {
  const response = await handle({
    request: request(
      { cell: "N21", payload: { code: "2**10" } },
      { "content-type": "text/plain", "sec-fetch-site": "same-origin" },
    ),
  });
  assert.equal(response.status, 415);
  assert.equal((await response.json()).error, "content-type must be application/json");
});

test("organ route still serves same-origin JSON requests", async () => {
  const response = await handle({
    request: request(
      { cell: "N8", payload: { text: "same origin" } },
      { "sec-fetch-site": "same-origin", "sec-fetch-mode": "cors" },
    ),
  });
  assert.equal(response.status, 200);
  assert.equal((await response.json()).receipt.signed, false);
});

test("organ subprocess env is an allowlist that drops server secrets", () => {
  const env = buildOrganEnv(
    {
      XAI_API_KEY: "probe-secret",
      BETTER_AUTH_SECRET: "probe-secret",
      DATABASE_URL: "postgres://probe-secret",
      GROK_AUTH_CLIENT_SECRET: "probe-secret",
      PYTHONSTARTUP: "/tmp/evil.py",
      NODE_OPTIONS: "--require evil",
      PATH: "/usr/bin:/bin",
      LANG: "C.UTF-8",
    },
    "/srv/python",
  );
  for (const key of [
    "XAI_API_KEY",
    "BETTER_AUTH_SECRET",
    "DATABASE_URL",
    "GROK_AUTH_CLIENT_SECRET",
    "PYTHONSTARTUP",
    "NODE_OPTIONS",
  ]) {
    assert.equal(key in env, false, key);
  }
  assert.equal(env.PATH, "/usr/bin:/bin");
  assert.equal(env.LANG, "C.UTF-8");
  assert.equal(env.PYTHONPATH, "/srv/python");
  assert.equal(env.PYTHONNOUSERSITE, "1");
  assert.equal(env.PYTHONDONTWRITEBYTECODE, "1");
  assert.equal(env.PYTHONSAFEPATH, "1");
});

test("N21 act still returns an UNSIGNED receipt with a secret in the server env", async () => {
  const previous = process.env.XAI_API_KEY;
  process.env.XAI_API_KEY = "probe-secret";
  try {
    const response = await handle({
      request: request({ cell: "N21", payload: { code: "1 + 2 * 3" } }),
    });
    const text = await response.text();
    assert.equal(response.status, 200);
    assert.equal(text.includes("probe-secret"), false);
    const receipt = JSON.parse(text);
    assert.equal(receipt.receipt.signed, false);
    assert.equal(receipt.receipt.proven_trust, false);
  } finally {
    if (previous === undefined) delete process.env.XAI_API_KEY;
    else process.env.XAI_API_KEY = previous;
  }
});
