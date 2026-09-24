import { readSseData, type CompleteInput, type GrokResult } from "./grok-contract.ts";

export async function streamGrok(
  data: CompleteInput,
  onDelta: (chunk: string) => void,
): Promise<GrokResult> {
  let text = "";
  let usage = { prompt: 0, completion: 0 };
  try {
    const res = await fetch("/api/complete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
      signal: AbortSignal.timeout(65000),
    });
    if (!res.ok || !res.headers.get("content-type")?.includes("text/event-stream")) {
      const body = await res.json().catch(() => ({}));
      return { ok: false, error: body.error ?? `AI request returned HTTP ${res.status}` };
    }
    if (!res.body) return { ok: false, error: "Empty stream" };
    for await (const event of readSseData(res.body)) {
      const v = JSON.parse(event);
      if (typeof v.error === "string") return { ok: false, error: v.error };
      if (v.usage) usage = v.usage;
      if (typeof v.delta === "string") {
        text += v.delta;
        onDelta(v.delta);
      }
      if (v.done === true)
        return text.trim()
          ? { ok: true, text, usage }
          : { ok: false, error: "AI provider returned no completion" };
    }
    return { ok: false, error: "AI stream ended before completion. Please retry." };
  } catch {
    return { ok: false, error: "AI stream failed or timed out. Please retry." };
  }
}
