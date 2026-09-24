import { createServerFn } from "@tanstack/react-start";
import { grokRequestBody, validateCompleteInput, type GrokResult } from "./grok-contract";
export { clampCompleteInput, grokRequestBody } from "./grok-contract";
export type {
  GrokMsg,
  GrokOk,
  GrokErr,
  GrokResult,
  CompleteInput,
  JsonSchemaSpec,
} from "./grok-contract";

export const completeGrok = createServerFn({ method: "POST" })
  .validator(validateCompleteInput)
  .handler(async ({ data }): Promise<GrokResult> => {
    const apiKey = process.env.XAI_API_KEY;
    if (!apiKey) return { ok: false, error: "AI is not available in this environment" };
    try {
      const res = await fetch("https://api.x.ai/v1/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
        body: JSON.stringify(
          grokRequestBody(data, false, process.env.XAI_MODEL?.trim() || undefined),
        ),
        signal: AbortSignal.timeout(60000),
      });
      if (!res.ok) {
        await res.body?.cancel().catch(() => undefined);
        return { ok: false, error: `AI provider returned HTTP ${res.status}` };
      }
      const body = await res.json();
      const text = body.choices?.[0]?.message?.content;
      if (typeof text !== "string" || !text.trim())
        return { ok: false, error: "AI provider returned no completion" };
      return {
        ok: true,
        text,
        usage: {
          prompt: body.usage?.prompt_tokens ?? 0,
          completion: body.usage?.completion_tokens ?? 0,
        },
      };
    } catch {
      return { ok: false, error: "AI request failed or timed out. Please retry." };
    }
  });
