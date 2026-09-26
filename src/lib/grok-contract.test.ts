import assert from "node:assert/strict";
import { test } from "node:test";
import {
  clampCompleteInput,
  readSseData,
  validateCompleteInput,
  grokRequestBody,
  stopFilter,
  truncateAtStop,
} from "./grok-contract.ts";
import { streamGrok } from "./stream.ts";
import { completeOnce, handleComplete } from "./grok-stream.server.ts";

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

// xAI reasoning models reject stop, presence_penalty and frequency_penalty.
const REJECTED_BY_REASONING_MODELS = ["stop", "presence_penalty", "frequency_penalty"];
const withStop = { ...input, stop: ["\n\n\n"] };
const placeholder = { apiKey: "test-only-placeholder", model: undefined };
type FetchStub = { mock: { calls: { arguments: unknown[] }[] } };
function sentBody(stub: FetchStub, call = 0) {
  const options = stub.mock.calls[call].arguments[1] as RequestInit;
  return JSON.parse(String(options.body)) as Record<string, unknown>;
}
function chatJson(content: string) {
  return Response.json({
    choices: [{ message: { content } }],
    usage: { prompt_tokens: 5, completion_tokens: 3 },
  });
}
function providerDelta(content: string) {
  return `data: ${JSON.stringify({ choices: [{ delta: { content } }] })}\n\n`;
}
async function streamEvents(response: Response) {
  const events: Record<string, unknown>[] = [];
  for await (const event of readSseData(response.body!)) events.push(JSON.parse(event));
  return events;
}
test("request bodies never carry stop or penalty parameters", () => {
  for (const stream of [false, true])
    for (const extra of [{}, { jsonObject: true }, { jsonSchema: { name: "r", schema: {} } }]) {
      const body = grokRequestBody({ ...withStop, ...extra }, stream);
      for (const key of REJECTED_BY_REASONING_MODELS) assert.equal(key in body, false, key);
    }
});
test("both provider paths omit stop from the bytes sent to xAI", async (t) => {
  const stub = t.mock.method(globalThis, "fetch", async () => chatJson("ok"));
  await completeOnce(withStop, placeholder);
  stub.mock.mockImplementation(async () => sse("data: [DONE]\n\n"));
  await (await handleComplete(request(withStop), placeholder)).text();
  assert.equal(stub.mock.callCount(), 2);
  for (const call of [0, 1])
    for (const key of REJECTED_BY_REASONING_MODELS)
      assert.equal(key in sentBody(stub, call), false, key);
});
test("stop sequences are applied locally at the earliest match", () => {
  assert.equal(truncateAtStop("keep\n\n\ndrop", ["\n\n\n"]), "keep");
  assert.equal(truncateAtStop("a END b STOP c", ["STOP", "END"]), "a ");
  assert.equal(truncateAtStop("no match", ["\n\n\n"]), "no match");
  assert.equal(truncateAtStop("untouched\n\n\n", undefined), "untouched\n\n\n");
  assert.equal(truncateAtStop("untouched", []), "untouched");
});
test("streaming stop filter matches whole-text truncation for any chunking", () => {
  let seed = 7;
  const rand = (n: number) => (seed = (seed * 48271) % 2147483647) % n;
  const alphabet = ["a", "\n", "\n", "b", "🌌", " "];
  for (let round = 0; round < 500; round++) {
    let text = "";
    for (let i = rand(40); i > 0; i--) text += alphabet[rand(alphabet.length)];
    const stop = round % 3 ? ["\n\n\n"] : ["\n\n\n", "b🌌"];
    const filter = stopFilter(stop);
    let out = "";
    let i = 0;
    while (i < text.length) {
      const size = 1 + rand(5);
      const part = filter.push(text.slice(i, i + size));
      // An emitted delta never ends inside a surrogate pair.
      if (part) assert.equal(/[\uD800-\uDBFF]$/.test(part), false);
      out += part;
      i += size;
    }
    out += filter.flush();
    assert.equal(out, truncateAtStop(text, stop), JSON.stringify({ text, stop }));
  }
  const passthrough = stopFilter(undefined);
  assert.equal(passthrough.push("a\n\n\nb"), "a\n\n\nb");
  assert.equal(passthrough.flush(), "");
});
test("non-streaming completion truncates at the profile stop sequence", async (t) => {
  const stub = t.mock.method(globalThis, "fetch", async () => chatJson("keep this\n\n\nnot this"));
  assert.deepEqual(await completeOnce(withStop, placeholder), {
    ok: true,
    text: "keep this",
    usage: { prompt: 5, completion: 3 },
  });
  // Without a stop sequence the provider text is returned unchanged.
  assert.deepEqual(await completeOnce(input, placeholder), {
    ok: true,
    text: "keep this\n\n\nnot this",
    usage: { prompt: 5, completion: 3 },
  });
  // Text that is empty once truncated is still no completion.
  stub.mock.mockImplementation(async () => chatJson("\n\n\nonly after the stop"));
  assert.deepEqual(await completeOnce(withStop, placeholder), {
    ok: false,
    error: "AI provider returned no completion",
  });
});
test("non-streaming completion without a key is unavailable and never fetches", async (t) => {
  const stub = t.mock.method(globalThis, "fetch", async () => {
    throw new Error("unexpected request");
  });
  assert.deepEqual(await completeOnce(withStop, { apiKey: undefined, model: undefined }), {
    ok: false,
    error: "AI is not available in this environment",
  });
  assert.equal(stub.mock.callCount(), 0);
});
test("streaming completion withholds text after a stop split across deltas", async (t) => {
  t.mock.method(globalThis, "fetch", async () =>
    sse(
      providerDelta("keep\n") +
        providerDelta("\n") +
        providerDelta("\nnot this") +
        providerDelta(" or this") +
        'data: {"usage":{"prompt_tokens":2,"completion_tokens":9}}\n\ndata: [DONE]\n\n',
    ),
  );
  const events = await streamEvents(await handleComplete(request(withStop), placeholder));
  assert.equal(events.map((e) => e.delta ?? "").join(""), "keep");
  assert.equal(events.filter((e) => e.done).length, 1);
  assert.deepEqual(events.at(-1), { done: true });
  assert.deepEqual(events.find((e) => e.usage)?.usage, { prompt: 2, completion: 9 });
});
test("streaming completion releases held-back text when no stop appears", async (t) => {
  t.mock.method(globalThis, "fetch", async () =>
    sse(providerDelta("ends in\n\n") + "data: [DONE]\n\n"),
  );
  const events = await streamEvents(await handleComplete(request(withStop), placeholder));
  assert.equal(events.map((e) => e.delta ?? "").join(""), "ends in\n\n");
  assert.deepEqual(events.at(-1), { done: true });
});
test("streaming truncation after a stop still requires the provider DONE event", async (t) => {
  t.mock.method(globalThis, "fetch", async () => sse(providerDelta("a\n\n\nb")));
  const events = await streamEvents(await handleComplete(request(withStop), placeholder));
  assert.equal(events.filter((e) => e.done).length, 0);
  assert.match(String(events.at(-1)?.error), /ended before completion/);
});
