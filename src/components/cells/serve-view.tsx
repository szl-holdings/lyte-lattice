import { useState } from "react";
import { toast } from "sonner";
import { CellFrame } from "./cell-frame";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { Field, Panel, PanelHeader } from "@/components/ui/panel";
import { ENGINE_PROFILES, useLyte } from "@/lib/store";
import { gate, runLocalGuard, runStream } from "@/lib/run-ai";
import type { EngineId } from "@/lib/types";
import { cn, uid } from "@/lib/utils";

const ENGINES: EngineId[] = ["vllm", "sglang", "ollama", "trtllm"];

const POSTURE: Record<EngineId, string> = {
  vllm: "vLLM batch",
  sglang: "SGLang constrained",
  ollama: "Ollama chat",
  trtllm: "TRT extract",
};

export function ServeView() {
  const engine = useLyte((s) => s.serve.engine);
  const setEngine = useLyte((s) => s.setEngine);
  const messages = useLyte((s) => s.serve.messages);
  const pushServe = useLyte((s) => s.pushServe);
  const patchServe = useLyte((s) => s.patchServe);
  const clearServe = useLyte((s) => s.clearServe);
  const tempOverride = useLyte((s) => s.serve.temperatureOverride);
  const setServeTemp = useLyte((s) => s.setServeTemp);
  const adapter = useLyte((s) => s.adapters.find((a) => a.bound));
  const throttled = useLyte((s) => s.throttled.includes("serve"));
  const profile = ENGINE_PROFILES[engine];
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [servingId, setServingId] = useState<string | null>(null);

  const lastMetrics = [...messages].reverse().find((m) => m.role === "assistant" && m.metrics)?.metrics;
  const effectiveTemp = tempOverride ?? profile.temperature;

  async function send() {
    const text = draft.trim();
    if (!text || busy) return;
    const g = gate("serve");
    if (!g.ok) {
      toast.error(g.reason);
      return;
    }
    const scanned = runLocalGuard(text, "prompt");
    if (scanned.action === "block") {
      toast.error(`Guard blocked: ${scanned.reason}`);
      return;
    }
    const content = scanned.action === "redact" ? scanned.redacted : text;
    const history = messages
      .filter((m) => (m.role === "user" || m.role === "assistant") && m.content)
      .slice(-8)
      .map((m) => ({ role: m.role as "user" | "assistant", content: m.content }));

    pushServe({ id: uid("m"), role: "user", content, engine, ts: Date.now() });
    const asstId = uid("m");
    pushServe({ id: asstId, role: "assistant", content: "", engine, ts: Date.now() });
    setDraft("");
    setBusy(true);
    setServingId(asstId);

    let acc = "";
    const res = await runStream({
      cell: "serve",
      name: `${profile.name} complete`,
      user: content,
      engine,
      history,
      onDelta: (chunk) => {
        acc += chunk;
        patchServe(asstId, { content: acc });
      },
    });

    setBusy(false);
    setServingId(null);

    if (!res.ok) {
      toast.error(res.error);
      if (!acc) patchServe(asstId, { content: `[failed] ${res.error}` });
      return;
    }

    const outScan = runLocalGuard(res.text, "response");
    const out =
      outScan.action === "block"
        ? `[blocked] ${outScan.reason}`
        : outScan.action === "redact"
          ? outScan.redacted
          : res.text;
    patchServe(asstId, {
      content: out,
      usage: res.usage,
      metrics: { ttftMs: res.ttftMs, tokPerSec: res.tokPerSec },
    });
  }

  return (
    <CellFrame id="serve">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {ENGINES.map((id) => {
          const p = ENGINE_PROFILES[id];
          const on = engine === id;
          return (
            <button
              key={id}
              type="button"
              onClick={() => setEngine(id)}
              className={cn(
                "min-h-11 rounded-md border px-3 py-3 text-left transition-colors",
                on ? "border-accent bg-elevated" : "border-border bg-surface hover:border-border-strong",
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium">{p.name}</span>
                {on ? <Badge tone="accent">active</Badge> : null}
              </div>
              <p className="mt-1 text-xs text-muted">{p.cited}</p>
              <p className="mt-2 font-mono text-[11px] text-subtle">
                T {p.temperature} · max {p.maxTokens} · top_p {p.topP}
              </p>
              <p className="mt-1 text-xs text-muted">{POSTURE[id]}</p>
            </button>
          );
        })}
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.3fr_0.7fr]">
        <Panel pad={false} className="flex min-h-[420px] flex-col">
          <div className="flex items-center justify-between border-b border-border px-5 py-3">
            <PanelHeader title="Completions" hint="User-initiated. Grok 4.5 under the selected profile." />
            <Button variant="ghost" size="sm" onClick={clearServe}>
              Clear
            </Button>
          </div>
          <div className="flex-1 space-y-3 overflow-y-auto px-5 py-4">
            {messages.length === 0 ? (
              <p className="text-sm text-muted">
                Ask the serving layer. Guard scans prompts first when Lattice SENTRA is bound.
              </p>
            ) : (
              messages.map((m) => {
                const live = m.id === servingId;
                return (
                  <article
                    key={m.id}
                    className={cn(
                      "rounded-md border px-3 py-2.5 text-sm leading-relaxed",
                      m.role === "user" ? "border-border bg-sunken" : "border-border bg-elevated",
                    )}
                  >
                    <div className="mb-1 flex flex-wrap items-center gap-2 font-mono text-[10px] uppercase tracking-wider text-subtle">
                      <span>{m.role}</span>
                      <span>{ENGINE_PROFILES[m.engine].name}</span>
                      {m.usage ? (
                        <span className="tabular">
                          {m.usage.prompt}+{m.usage.completion} tok
                        </span>
                      ) : null}
                      {m.metrics ? (
                        <span className="tabular">
                          {m.metrics.ttftMs} ms · {m.metrics.tokPerSec} tok/s
                        </span>
                      ) : null}
                    </div>
                    {m.content ? (
                      <p className="whitespace-pre-wrap text-fg">
                        {m.content}
                        {live ? (
                          <span
                            className="ml-0.5 inline-block h-3.5 w-1 translate-y-0.5 bg-accent align-middle"
                            aria-hidden
                          />
                        ) : null}
                      </p>
                    ) : live ? (
                      <p className="text-sm text-muted">Serving…</p>
                    ) : (
                      <p className="text-sm text-muted">Empty completion.</p>
                    )}
                  </article>
                );
              })
            )}
          </div>
          <form
            className="border-t border-border p-4"
            onSubmit={(e) => {
              e.preventDefault();
              void send();
            }}
          >
            <Textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Prompt the active engine"
              rows={3}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault();
                  void send();
                }
              }}
            />
            <div className="mt-3 flex items-center justify-between gap-3">
              <p className="text-xs text-subtle">Ctrl/Cmd-Enter to send · Guard + Lattice apply</p>
              <Button type="submit" disabled={busy || !draft.trim()}>
                {busy ? "Serving…" : "Complete"}
              </Button>
            </div>
          </form>
        </Panel>
        <Panel>
          <PanelHeader title="Runtime" hint="Decoding posture for this turn." />
          <ul className="space-y-3 text-sm">
            <li className="flex justify-between gap-3">
              <span className="text-muted">Model</span>
              <span className="font-mono text-xs">grok-4.5</span>
            </li>
            <li className="flex justify-between gap-3">
              <span className="text-muted">Adapter</span>
              <span className="text-right">
                {adapter ? (
                  <>
                    {adapter.name}{" "}
                    <span className="font-mono text-xs text-subtle">r{adapter.rank}</span>
                  </>
                ) : (
                  "none bound"
                )}
              </span>
            </li>
            <li className="flex items-center justify-between gap-3">
              <span className="text-muted">Throttle</span>
              {throttled ? <Badge tone="warn">throttled</Badge> : <Badge>open</Badge>}
            </li>
            <li className="flex justify-between gap-3">
              <span className="text-muted">Last TTFT</span>
              <span className="font-mono text-xs tabular">
                {lastMetrics ? `${lastMetrics.ttftMs} ms` : "—"}
              </span>
            </li>
            <li className="flex justify-between gap-3">
              <span className="text-muted">tok/s</span>
              <span className="font-mono text-xs tabular">
                {lastMetrics ? lastMetrics.tokPerSec.toFixed(1) : "—"}
              </span>
            </li>
            <li className="flex justify-between gap-3">
              <span className="text-muted">Turns</span>
              <span className="tabular">{messages.length}</span>
            </li>
          </ul>
          <div className="mt-5">
            <Field
              label={`Temperature ${effectiveTemp.toFixed(1)}${tempOverride == null ? " · profile" : " · override"}`}
            >
              <input
                type="range"
                min={0.1}
                max={1.2}
                step={0.1}
                value={effectiveTemp}
                onChange={(e) => setServeTemp(Number(e.target.value))}
                className="w-full accent-[var(--color-accent)]"
                aria-label="Temperature override"
              />
            </Field>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="mt-2"
              disabled={tempOverride == null}
              onClick={() => setServeTemp(null)}
            >
              Profile default
            </Button>
          </div>
          <p className="mt-5 text-xs leading-relaxed text-muted">
            Profiles are real decoding postures on Grok 4.5, not local GPUs.
          </p>
        </Panel>
      </div>
    </CellFrame>
  );
}
