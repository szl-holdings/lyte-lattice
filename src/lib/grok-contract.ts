/** Shared completion contract, independent of framework and credentials. */
export type GrokMsg = { role: "system" | "user" | "assistant"; content: string };
export type GrokOk = { ok: true; text: string; usage: { prompt: number; completion: number } };
export type GrokErr = { ok: false; error: string };
export type GrokResult = GrokOk | GrokErr;
export type JsonSchemaSpec = { name: string; schema: Record<string, unknown>; strict?: boolean };
export type CompleteInput = {
  messages: GrokMsg[];
  temperature?: number;
  maxTokens?: number;
  topP?: number;
  stop?: string[];
  jsonSchema?: JsonSchemaSpec;
  jsonObject?: boolean;
};
const object = (v: unknown): v is Record<string, unknown> =>
  v !== null && typeof v === "object" && !Array.isArray(v);

export function validateCompleteInput(value: unknown): CompleteInput {
  if (
    !object(value) ||
    !Array.isArray(value.messages) ||
    value.messages.length < 1 ||
    value.messages.length > 32
  )
    throw new Error("Provide between 1 and 32 messages");
  let total = 0;
  for (const m of value.messages) {
    if (
      !object(m) ||
      typeof m.role !== "string" ||
      !["system", "user", "assistant"].includes(String(m.role)) ||
      typeof m.content !== "string" ||
      !m.content.trim()
    )
      throw new Error("Each message needs a valid role and nonempty text");
    total += m.content.length;
  }
  if (total > 32000) throw new Error("Prompt exceeds 32000 characters");
  for (const key of ["temperature", "maxTokens", "topP"])
    if (
      value[key] !== undefined &&
      (typeof value[key] !== "number" || !Number.isFinite(value[key]))
    )
      throw new Error(key + " must be a finite number");
  if (
    value.stop !== undefined &&
    (!Array.isArray(value.stop) ||
      value.stop.length > 4 ||
      value.stop.some((s) => typeof s !== "string" || !s.length || s.length > 200))
  )
    throw new Error("stop must contain at most four short strings");
  if (value.jsonObject !== undefined && typeof value.jsonObject !== "boolean")
    throw new Error("jsonObject must be a boolean");
  if (value.jsonSchema !== undefined) {
    const s = value.jsonSchema;
    if (
      !object(s) ||
      typeof s.name !== "string" ||
      !/^[a-zA-Z0-9_-]{1,64}$/.test(s.name) ||
      !object(s.schema) ||
      (s.strict !== undefined && typeof s.strict !== "boolean") ||
      JSON.stringify(s.schema).length > 16000
    )
      throw new Error("Invalid JSON schema specification");
  }
  return value as CompleteInput;
}
export function clampCompleteInput(value: CompleteInput) {
  const data = validateCompleteInput(value);
  return {
    messages: data.messages.map((m) => ({ role: m.role, content: m.content.slice(0, 8000) })),
    max_tokens: Math.min(900, Math.max(64, Math.round(data.maxTokens ?? 420))),
    temperature: Math.min(1.2, Math.max(0, data.temperature ?? 0.6)),
    top_p: Math.min(1, Math.max(0.05, data.topP ?? 0.95)),
  };
}
/**
 * xAI documents that its reasoning models reject `stop`, `presence_penalty` and
 * `frequency_penalty` with an error, so none of them is sent for any model. A profile's
 * stop sequences are applied to the returned text instead (`truncateAtStop`,
 * `stopFilter`).
 */
export function grokRequestBody(data: CompleteInput, stream = false, model = "grok-4.5") {
  const body: Record<string, unknown> = { model, ...clampCompleteInput(data), stream };
  if (data.jsonSchema)
    body.response_format = {
      type: "json_schema",
      json_schema: { ...data.jsonSchema, strict: data.jsonSchema.strict ?? true },
    };
  else if (data.jsonObject) body.response_format = { type: "json_object" };
  if (stream) body.stream_options = { include_usage: true };
  return body;
}
/** Cut text before the earliest stop sequence, as a provider-side `stop` would. */
export function truncateAtStop(text: string, stop?: string[]): string {
  let cut = text.length;
  for (const s of stop ?? []) {
    const i = s ? text.indexOf(s) : -1;
    if (i >= 0 && i < cut) cut = i;
  }
  return text.slice(0, cut);
}
/**
 * Streaming form of `truncateAtStop`. `push` returns the text that is safe to
 * emit: it holds back just enough characters to recognise a stop sequence split
 * across deltas, and returns nothing once a stop sequence has been seen. `flush`
 * releases the held-back tail when the provider reports completion.
 */
export function stopFilter(stop?: string[]) {
  const sequences = (stop ?? []).filter((s) => s.length);
  const hold = Math.max(0, ...sequences.map((s) => s.length - 1));
  let pending = "";
  let stopped = false;
  return {
    push(chunk: string): string {
      if (stopped) return "";
      if (!sequences.length) return chunk;
      pending += chunk;
      const cut = truncateAtStop(pending, sequences);
      if (cut.length < pending.length) {
        stopped = true;
        pending = "";
        return cut;
      }
      let emit = Math.max(0, pending.length - hold);
      // Never split a UTF-16 surrogate pair between two deltas.
      const last = pending.charCodeAt(emit - 1);
      if (emit > 0 && last >= 0xd800 && last <= 0xdbff) emit--;
      const out = pending.slice(0, emit);
      pending = pending.slice(emit);
      return out;
    },
    flush(): string {
      const out = stopped ? "" : pending;
      pending = "";
      return out;
    },
  };
}
/** Parse complete SSE events across arbitrary byte and CRLF boundaries. */
export async function* readSseData(body: ReadableStream<Uint8Array>): AsyncGenerator<string> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let data: string[] = [];
  let eventBytes = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true });
      if (buffer.length > 1000000) throw new Error("Provider event exceeded stream limit");
      let i: number;
      while ((i = buffer.indexOf("\n")) >= 0) {
        const line = buffer.slice(0, i).replace(/\r$/, "");
        buffer = buffer.slice(i + 1);
        if (!line) {
          if (data.length) yield data.join("\n");
          data = [];
          eventBytes = 0;
        } else if (line.startsWith("data:")) {
          const part = line.slice(5).replace(/^ /, "");
          eventBytes += part.length;
          if (eventBytes > 1000000) throw new Error("Provider event exceeded stream limit");
          data.push(part);
        }
      }
      if (done) break;
    }
    // An unterminated event is incomplete; callers require an explicit DONE event.
  } finally {
    await reader.cancel().catch(() => undefined);
    reader.releaseLock();
  }
}
