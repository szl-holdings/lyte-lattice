import { createServerFn } from "@tanstack/react-start";

export type GrokMsg = { role: "system" | "user" | "assistant"; content: string };

export type GrokOk = {
  ok: true;
  text: string;
  usage: { prompt: number; completion: number };
};

export type GrokErr = { ok: false; error: string };

export type GrokResult = GrokOk | GrokErr;

export type JsonSchemaSpec = {
  name: string;
  schema: Record<string, unknown>;
  strict?: boolean;
};

export type CompleteInput = {
  messages: GrokMsg[];
  temperature?: number;
  maxTokens?: number;
  topP?: number;
  stop?: string[];
  jsonSchema?: JsonSchemaSpec;
  jsonObject?: boolean;
};

const MAX_PROMPT = 8000;
const MAX_TOKENS_CAP = 900;

export function clampCompleteInput(data: CompleteInput) {
  const messages = data.messages.map((m) => ({
    role: m.role,
    content: m.content.slice(0, MAX_PROMPT),
  }));
  const max_tokens = Math.min(MAX_TOKENS_CAP, Math.max(64, Math.round(data.maxTokens ?? 420)));
  const temperature = Math.min(1.2, Math.max(0, data.temperature ?? 0.6));
  const top_p = Math.min(1, Math.max(0.05, data.topP ?? 0.95));
  return { messages, max_tokens, temperature, top_p };
}

export function grokRequestBody(data: CompleteInput, stream = false) {
  const { messages, max_tokens, temperature, top_p } = clampCompleteInput(data);
  const body: Record<string, unknown> = {
    model: "grok-4.5",
    messages,
    temperature,
    max_tokens,
    top_p,
    stream,
  };
  if (data.stop?.length) body.stop = data.stop.slice(0, 4);
  if (data.jsonSchema) {
    body.response_format = {
      type: "json_schema",
      json_schema: {
        name: data.jsonSchema.name.slice(0, 64) || "object",
        schema: data.jsonSchema.schema,
        strict: data.jsonSchema.strict ?? true,
      },
    };
  } else if (data.jsonObject) {
    body.response_format = { type: "json_object" };
  }
  if (stream) body.stream_options = { include_usage: true };
  return body;
}

export const completeGrok = createServerFn({ method: "POST" })
  .validator((input: CompleteInput) => input)
  .handler(async ({ data }): Promise<GrokResult> => {
    const apiKey = process.env.XAI_API_KEY;
    if (!apiKey) return { ok: false, error: "AI is not available in this environment" };

    const { messages } = clampCompleteInput(data);
    if (!messages.length) return { ok: false, error: "Empty prompt" };

    const res = await fetch("https://api.x.ai/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify(grokRequestBody(data, false)),
    });

    if (!res.ok) {
      const body = await res.text().catch(() => "");
      return { ok: false, error: `xAI error ${res.status}${body ? `: ${body.slice(0, 180)}` : ""}` };
    }

    const body = (await res.json()) as {
      choices?: { message?: { content?: string } }[];
      usage?: { prompt_tokens?: number; completion_tokens?: number };
    };
    const text = body.choices?.[0]?.message?.content ?? "";
    return {
      ok: true,
      text,
      usage: {
        prompt: body.usage?.prompt_tokens ?? 0,
        completion: body.usage?.completion_tokens ?? 0,
      },
    };
  });
