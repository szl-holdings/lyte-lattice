import assert from "node:assert/strict";
import { test } from "node:test";
import {
  clampCompleteInput,
  readSseData,
  validateCompleteInput,
  grokRequestBody,
} from "./grok-contract.ts";
import { streamGrok } from "./stream.ts";
import { handleComplete } from "./grok-stream.server.ts";

const input = { messages: [{ role: "user" as const, content: "Explain the measured result" }] };
function bytes(text: string) {
  const data = new TextEncoder().encode(text);
  return new ReadableStream<Uint8Array>({
    start(c) {
      for (const b of data) c.enqueue(Uint8Array.of(b));
      c.close();
    },
  });
}
function sse(text: string) {
  return new Response(bytes(text), { headers: { "content-type": "text/event-stream" } });
}
function request(value: unknown = input) {
  return new Request("http://localhost/api/complete", {
    method: "POST",
    body: JSON.stringify(value),
  });
}

test("missing provider key reports unavailable without fetching", async (t) => {
  const stub = t.mock.method(globalThis, "fetch", async () => {
    throw new Error("unexpected request");
  });
  assert.equal(
    (await handleComplete(request(), { apiKey: undefined, model: undefined })).status,
    503,
  );
  assert.equal(stub.mock.callCount(), 0);
});

test("consumer cancellation aborts the provider request", async (t) => {
  let providerSignal: AbortSignal | undefined;
  t.mock.method(globalThis, "fetch", async (_url: Parameters<typeof fetch>[0], options?: RequestInit) => {
    providerSignal = options?.signal as AbortSignal;
    return new Response(
      new ReadableStream<Uint8Array>({
        start(controller) {
          controller.enqueue(
            new TextEncoder().encode('data: {"choices":[{"delta":{"content":"first"}}]}\n\n'),
          );
          providerSignal?.addEventListener(
            "abort",
            () => controller.error(new Error("cancelled")),
            { once: true },
          );
        },
      }),
      { headers: { "content-type": "text/event-stream" } },
    );
  });
  const response = await handleComplete(request(), {
    apiKey: "test-only-placeholder",
    model: undefined,
  });
  const reader = response.body!.getReader();
  assert.equal((await reader.read()).done, false);
  await reader.cancel();
  assert.equal(providerSignal?.aborted, true);
});

test("reject malformed request shapes before provider I/O", () => {
  for (const value of [
    null,
    [],
    {},
    { messages: [] },
    { messages: [null] },
    { messages: [{ role: "tool", content: "x" }] },
    { messages: [{ role: ["user"], content: "x" }] },
    { messages: [{ role: "user", content: 3 }] },
    { messages: [{ role: "user", content: " " }] },
    { ...input, maxTokens: NaN },
    { ...input, temperature: Infinity },
    { ...input, stop: [2] },
    { ...input, jsonSchema: { name: "bad name", schema: {} } },
    { ...input, messages: Array(33).fill(input.messages[0]) },
    { messages: [{ role: "user", content: "x".repeat(32001) }] },
  ])
    assert.throws(() => validateCompleteInput(value));
});
test("valid requests preserve schema/model and clamp finite sampling values", () => {
  const body = grokRequestBody(
    {
      ...input,
      maxTokens: 5000,
      temperature: -1,
      topP: 2,
      jsonSchema: { name: "result", schema: { type: "object" } },
    },
    true,
    "configured-model",
  );
  assert.equal(body.model, "configured-model");
  assert.equal(body.max_tokens, 900);
  assert.equal(body.temperature, 0);
  assert.equal(body.top_p, 1);
  assert.deepEqual(body.stream_options, { include_usage: true });
  assert.equal(clampCompleteInput(input).messages[0].content, input.messages[0].content);
});
test("SSE preserves Unicode across individual bytes and CRLF event boundaries", async () => {
  const events = [];
  for await (const event of readSseData(
    bytes(': pulse\r\ndata: {"delta":"🌌"}\r\n\r\ndata: [DONE]\n\n'),
  ))
    events.push(event);
  assert.deepEqual(events, ['{"delta":"🌌"}', "[DONE]"]);
});
test("SSE discards unterminated events and cancels on early consumer return", async () => {
  const events = [];
  for await (const event of readSseData(bytes('data: {"done":true}'))) events.push(event);
  assert.deepEqual(events, []);
  let cancelled = false;
  const source = new ReadableStream<Uint8Array>({
    start(c) {
      c.enqueue(new TextEncoder().encode("data: [DONE]\n\n"));
    },
    cancel() {
      cancelled = true;
    },
  });
  for await (const _ of readSseData(source)) break;
  assert.equal(cancelled, true);
});
test("client accepts only an explicit complete nonempty stream", async (t) => {
  t.mock.method(globalThis, "fetch", async () =>
    sse(
      'data: {"delta":"measured"}\r\n\r\ndata: {"usage":{"prompt":4,"completion":1}}\n\ndata: {"done":true}\n\n',
    ),
  );
  const seen: string[] = [];
  assert.deepEqual(await streamGrok(input, (s) => seen.push(s)), {
    ok: true,
    text: "measured",
    usage: { prompt: 4, completion: 1 },
  });
  assert.deepEqual(seen, ["measured"]);
});
test("client reports truncated, empty, malformed, provider-error and failed streams", async (t) => {
  const cases = [
    'data: {"delta":"partial"}\n\n',
    'data: {"done":true}\n\n',
    "data: not-json\n\n",
    'data: {"error":"unavailable"}\n\n',
  ];
  const stub = t.mock.method(globalThis, "fetch", async () => sse(cases[0]));
  for (const payload of cases) {
    stub.mock.mockImplementation(async () => sse(payload));
    assert.equal((await streamGrok(input, () => {})).ok, false);
  }
  stub.mock.mockImplementation(async () => {
    throw new Error("network");
  });
  assert.equal((await streamGrok(input, () => {})).ok, false);
});
test("server rejects invalid JSON shape without a provider call", async (t) => {
  const stub = t.mock.method(globalThis, "fetch", async () => {
    throw new Error("must not fetch");
  });
  assert.equal(
    (
      await handleComplete(request({ messages: null }), {
        apiKey: "test-only-placeholder",
        model: undefined,
      })
    ).status,
    400,
  );
  assert.equal(stub.mock.callCount(), 0);
});
test("server emits one done event and preserves usage, including split Unicode", async (t) => {
  t.mock.method(globalThis, "fetch", async () =>
    sse(
      'data: {"choices":[{"delta":{"content":"🌌"}}]}\r\n\r\ndata: {"usage":{"prompt_tokens":2,"completion_tokens":1}}\n\ndata: [DONE]\n\n',
    ),
  );
  const response = await handleComplete(request(), {
    apiKey: "test-only-placeholder",
    model: undefined,
  });
  assert.equal(response.status, 200);
  const body = await response.text();
  assert.equal(body.split('"done":true').length - 1, 1);
  assert.match(body, /🌌/);
  assert.match(body, /"prompt":2/);
});
test("server does not convert provider truncation into success", async (t) => {
  t.mock.method(globalThis, "fetch", async () =>
    sse('data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'),
  );
  const body = await (
    await handleComplete(request(), { apiKey: "test-only-placeholder", model: undefined })
  ).text();
  assert.match(body, /ended before completion/);
  assert.doesNotMatch(body, /"done":true/);
});
test("server translates network failures and non-SSE responses without leaking upstream bodies", async (t) => {
  const stub = t.mock.method(globalThis, "fetch", async () => {
    throw new Error("private diagnostic");
  });
  assert.equal(
    (await handleComplete(request(), { apiKey: "test-only-placeholder", model: undefined })).status,
    502,
  );
  stub.mock.mockImplementation(async () => Response.json({ private: "diagnostic" }));
  const response = await handleComplete(request(), {
    apiKey: "test-only-placeholder",
    model: undefined,
  });
  assert.equal(response.status, 502);
  assert.doesNotMatch(await response.text(), /diagnostic/);
});
