import { createFileRoute } from "@tanstack/react-router";
import { clampCompleteInput, grokRequestBody, type CompleteInput } from "@/lib/grok";

export const Route = createFileRoute("/api/complete")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const apiKey = process.env.XAI_API_KEY;
        if (!apiKey) {
          return Response.json({ ok: false, error: "AI is not available in this environment" }, { status: 503 });
        }

        let data: CompleteInput;
        try {
          data = (await request.json()) as CompleteInput;
        } catch {
          return Response.json({ ok: false, error: "Invalid JSON" }, { status: 400 });
        }

        const { messages } = clampCompleteInput(data);
        if (!messages.length) {
          return Response.json({ ok: false, error: "Empty prompt" }, { status: 400 });
        }

        const upstream = await fetch("https://api.x.ai/v1/chat/completions", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${apiKey}`,
          },
          body: JSON.stringify(grokRequestBody(data, true)),
        });

        if (!upstream.ok || !upstream.body) {
          const body = await upstream.text().catch(() => "");
          return Response.json(
            { ok: false, error: `xAI error ${upstream.status}${body ? `: ${body.slice(0, 180)}` : ""}` },
            { status: 502 },
          );
        }

        const encoder = new TextEncoder();
        const decoder = new TextDecoder();
        const reader = upstream.body.getReader();

        const stream = new ReadableStream({
          async start(controller) {
            let buffer = "";
            try {
              while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop() ?? "";
                for (const line of lines) {
                  const trimmed = line.trim();
                  if (!trimmed.startsWith("data:")) continue;
                  const payload = trimmed.slice(5).trim();
                  if (payload === "[DONE]") {
                    controller.enqueue(encoder.encode("data: {\"done\":true}\n\n"));
                    continue;
                  }
                  try {
                    const json = JSON.parse(payload) as {
                      choices?: { delta?: { content?: string } }[];
                      usage?: { prompt_tokens?: number; completion_tokens?: number };
                    };
                    const delta = json.choices?.[0]?.delta?.content ?? "";
                    if (delta) {
                      controller.enqueue(
                        encoder.encode(`data: ${JSON.stringify({ delta })}\n\n`),
                      );
                    }
                    if (json.usage) {
                      controller.enqueue(
                        encoder.encode(
                          `data: ${JSON.stringify({
                            usage: {
                              prompt: json.usage.prompt_tokens ?? 0,
                              completion: json.usage.completion_tokens ?? 0,
                            },
                          })}\n\n`,
                        ),
                      );
                    }
                  } catch {
                    // skip malformed chunk
                  }
                }
              }
              controller.enqueue(encoder.encode("data: {\"done\":true}\n\n"));
            } catch (err) {
              const message = err instanceof Error ? err.message : "stream failed";
              controller.enqueue(encoder.encode(`data: ${JSON.stringify({ error: message })}\n\n`));
            } finally {
              controller.close();
            }
          },
        });

        return new Response(stream, {
          headers: {
            "Content-Type": "text/event-stream; charset=utf-8",
            "Cache-Control": "no-cache, no-transform",
            Connection: "keep-alive",
          },
        });
      },
    },
  },
});
