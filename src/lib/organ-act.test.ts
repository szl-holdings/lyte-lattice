import assert from "node:assert/strict";
import { test } from "node:test";
import { Route } from "../routes/api/act.ts";

const handlers = Route.options.server!.handlers as unknown as {
  POST: (context: { request: Request }) => Promise<Response>;
};
const handle = handlers.POST;

function request(value: unknown) {
  return new Request("http://localhost/api/act", {
    method: "POST",
    body: JSON.stringify(value),
  });
}

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
