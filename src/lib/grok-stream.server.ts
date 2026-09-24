import {
  grokRequestBody,
  readSseData,
  validateCompleteInput,
  type CompleteInput,
} from "./grok-contract.ts";

export async function handleComplete(
  request: Request,
  config = {
    apiKey: process.env.XAI_API_KEY,
    model: process.env.XAI_MODEL,
  },
): Promise<Response> {
  const apiKey = config.apiKey;
  if (!apiKey)
    return Response.json(
      { ok: false, error: "AI is not available in this environment" },
      { status: 503 },
    );
  let data: CompleteInput;
  try {
    data = validateCompleteInput(await request.json());
  } catch {
    return Response.json({ ok: false, error: "Invalid completion request" }, { status: 400 });
  }
  const abort = new AbortController();
  const signal = AbortSignal.any([request.signal, abort.signal, AbortSignal.timeout(60000)]);
  let upstream: Response;
  try {
    upstream = await fetch("https://api.x.ai/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify(grokRequestBody(data, true, config.model?.trim() || undefined)),
      signal,
    });
  } catch {
    return Response.json(
      { ok: false, error: "AI provider is unavailable or timed out" },
      { status: 502 },
    );
  }
  if (
    !upstream.ok ||
    !upstream.body ||
    !upstream.headers.get("content-type")?.includes("text/event-stream")
  ) {
    await upstream.body?.cancel().catch(() => undefined);
    return Response.json(
      { ok: false, error: "AI provider did not return a completion stream" },
      { status: 502 },
    );
  }
  const encoder = new TextEncoder();
  const events = readSseData(upstream.body);
  const encode = (payload: unknown) => encoder.encode(`data: ${JSON.stringify(payload)}\n\n`);
  const stream = new ReadableStream<Uint8Array>({
    async pull(controller) {
      try {
        while (true) {
          const next = await events.next();
          if (next.done) {
            controller.enqueue(encode({ error: "AI stream ended before completion" }));
            controller.close();
            return;
          }
          if (next.value === "[DONE]") {
            controller.enqueue(encode({ done: true }));
            controller.close();
            await events.return(undefined);
            return;
          }
          const json = JSON.parse(next.value);
          if (json.error) throw new Error("Provider stream error");
          const delta = json.choices?.[0]?.delta?.content;
          const result: Record<string, unknown> = {};
          if (typeof delta === "string" && delta) result.delta = delta;
          if (json.usage)
            result.usage = {
              prompt: json.usage.prompt_tokens ?? 0,
              completion: json.usage.completion_tokens ?? 0,
            };
          if (Object.keys(result).length) {
            controller.enqueue(encode(result));
            return;
          }
        }
      } catch {
        if (!abort.signal.aborted) {
          controller.enqueue(encode({ error: "AI stream failed or timed out" }));
          controller.close();
        }
        abort.abort();
        await events.return(undefined);
      }
    },
    async cancel() {
      abort.abort();
      await events.return(undefined);
    },
  });
  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      "X-Accel-Buffering": "no",
    },
  });
}
