import type { CompleteInput, GrokResult } from "./grok";

export async function streamGrok(
  data: CompleteInput,
  onDelta: (chunk: string) => void,
): Promise<GrokResult> {
  const res = await fetch("/api/complete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  const ctype = res.headers.get("content-type") ?? "";
  if (!res.ok || !ctype.includes("text/event-stream")) {
    try {
      const body = (await res.json()) as { error?: string };
      return { ok: false, error: body.error ?? `stream ${res.status}` };
    } catch {
      return { ok: false, error: `stream ${res.status}` };
    }
  }

  if (!res.body) return { ok: false, error: "Empty stream" };

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let text = "";
  let usage = { prompt: 0, completion: 0 };
  let error: string | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const line = part.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;
      try {
        const json = JSON.parse(line.slice(5).trim()) as {
          delta?: string;
          done?: boolean;
          error?: string;
          usage?: { prompt: number; completion: number };
        };
        if (json.error) error = json.error;
        if (json.usage) usage = json.usage;
        if (json.delta) {
          text += json.delta;
          onDelta(json.delta);
        }
      } catch {
        // ignore
      }
    }
  }

  if (error) return { ok: false, error };
  return { ok: true, text, usage };
}
