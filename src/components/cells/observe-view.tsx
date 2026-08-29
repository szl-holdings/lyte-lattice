import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { toast } from "sonner";
import { CellFrame } from "./cell-frame";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { OPERATING_CELLS, type CellId } from "@/lib/cells";
import { scanGuard } from "@/lib/engines/guard";
import { useLyte } from "@/lib/store";
import { fmtTime, pct, uid } from "@/lib/utils";
import type { EvalRun, TraceSpan, TraceStatus } from "@/lib/types";

function tone(status: TraceSpan["status"]) {
  if (status === "ok") return "ok" as const;
  if (status === "blocked" || status === "error") return "danger" as const;
  return "warn" as const;
}

function percentile(values: number[], p: number): number {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const rank = Math.min(sorted.length - 1, Math.max(0, Math.ceil((p / 100) * sorted.length) - 1));
  return sorted[rank] ?? 0;
}

function evalTraces(traces: TraceSpan[]): EvalRun {
  const llm = traces.filter((t) => t.kind === "llm" || t.kind === "run").slice(0, 8);
  const cases = (llm.length ? llm : traces.slice(0, 6)).map((t) => {
    const out = t.output ?? "";
    const input = t.input ?? "";
    const guard = scanGuard(out || input, useLyte.getState().guardPolicy, "response");
    const toks = new Set(input.toLowerCase().split(/\W+/).filter((w) => w.length > 3));
    const hits = out
      .toLowerCase()
      .split(/\W+/)
      .filter((w) => toks.has(w)).length;
    const faithfulness = toks.size ? Math.min(1, hits / Math.min(12, toks.size)) : 0.5;
    const toxicity = guard.action === "block" ? 1 : guard.action === "redact" ? 0.4 : 0;
    const jsonOk = (() => {
      try {
        if (!out.trim().startsWith("{") && !out.trim().startsWith("[")) return 0.5;
        JSON.parse(out);
        return 1;
      } catch {
        return 0;
      }
    })();
    return {
      input: t.name,
      output: out.slice(0, 220),
      scores: {
        faithfulness: Number(faithfulness.toFixed(2)),
        toxicity: Number(toxicity.toFixed(2)),
        structure: jsonOk,
        latency: t.durationMs > 8000 ? 0.4 : t.durationMs > 2500 ? 0.7 : 1,
      },
    };
  });
  return {
    id: uid("eval"),
    ts: Date.now(),
    name: "DeepEval local harness",
    cases,
  };
}

const STATUSES: TraceStatus[] = ["ok", "warn", "error", "blocked"];

export function ObserveView() {
  const traces = useLyte((s) => s.traces);
  const evals = useLyte((s) => s.evals);
  const addEval = useLyte((s) => s.addEval);
  const [filter, setFilter] = useState<CellId | "all">("all");
  const [open, setOpen] = useState<string | null>(null);
  const shown = useMemo(
    () => (filter === "all" ? traces : traces.filter((t) => t.cell === filter)),
    [traces, filter],
  );
  const active = shown.find((t) => t.id === open) ?? shown[0];

  const statusCounts = useMemo(() => {
    const acc: Record<TraceStatus, number> = { ok: 0, warn: 0, error: 0, blocked: 0 };
    for (const t of shown) acc[t.status] += 1;
    return acc;
  }, [shown]);

  const durations = useMemo(() => shown.map((t) => t.durationMs), [shown]);
  const p50 = percentile(durations, 50);
  const p95 = percentile(durations, 95);

  const avgByCell = useMemo(() => {
    const map = new Map<string, { sum: number; n: number }>();
    for (const t of shown) {
      const cur = map.get(t.cell) ?? { sum: 0, n: 0 };
      cur.sum += t.durationMs;
      cur.n += 1;
      map.set(t.cell, cur);
    }
    return [...map.entries()].map(([cell, { sum, n }]) => ({
      cell,
      avg: Math.round(sum / n),
    }));
  }, [shown]);

  function runEval() {
    if (!traces.length) {
      toast.message("No spans to score.");
      return;
    }
    const run = evalTraces(traces);
    addEval(run);
    useLyte.getState().addTrace({
      cell: "observe",
      kind: "eval",
      name: run.name,
      status: "ok",
      durationMs: 2,
      output: `${run.cases.length} cases`,
    });
    toast.success("Eval scored recent spans.");
  }

  const last = evals[0];

  return (
    <CellFrame id="observe">
      <div className="flex flex-wrap items-center gap-2">
        <Button size="sm" variant={filter === "all" ? "primary" : "secondary"} onClick={() => setFilter("all")}>
          All
        </Button>
        {OPERATING_CELLS.map((c) => (
          <Button
            key={c.id}
            size="sm"
            variant={filter === c.id ? "primary" : "ghost"}
            onClick={() => setFilter(c.id)}
          >
            {c.n}
          </Button>
        ))}
        <Button className="sm:ml-auto" size="sm" onClick={runEval}>
          Run eval
        </Button>
      </div>

      <div className="flex flex-wrap gap-2">
        {STATUSES.map((s) => (
          <Badge key={s} tone={tone(s)}>
            {s} {statusCounts[s]}
          </Badge>
        ))}
        <Badge tone="muted">p50 {p50}ms</Badge>
        <Badge tone="muted">p95 {p95}ms</Badge>
      </div>

      {avgByCell.length ? (
        <Panel pad={false} className="p-4">
          <PanelHeader title="Avg duration by cell" hint="Computed on the filtered span set." />
          <div className="h-[180px] max-h-[180px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={avgByCell} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" />
                <XAxis dataKey="cell" tick={{ fill: "var(--color-subtle)", fontSize: 11 }} />
                <YAxis
                  tick={{ fill: "var(--color-subtle)", fontSize: 11 }}
                  tickFormatter={(v) => `${v}`}
                  width={36}
                />
                <Tooltip
                  contentStyle={{
                    background: "var(--color-elevated)",
                    border: "1px solid var(--color-border)",
                    borderRadius: 8,
                  }}
                  formatter={(v) => [`${Number(v)}ms`, "avg"]}
                />
                <Bar dataKey="avg" fill="var(--color-accent)" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
        <Panel pad={false}>
          <div className="px-5 pt-5">
            <PanelHeader title="Traces" hint="Phoenix / Langfuse-style spans from every cell." />
          </div>
          <div className="max-h-[480px] overflow-y-auto">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-surface text-subtle">
                <tr>
                  <th className="px-5 py-2 font-medium">Time</th>
                  <th className="py-2 font-medium">Cell</th>
                  <th className="py-2 font-medium">Name</th>
                  <th className="py-2 font-medium">Status</th>
                  <th className="px-5 py-2 font-medium">ms</th>
                </tr>
              </thead>
              <tbody>
                {shown.length === 0 ? (
                  <tr>
                    <td className="px-5 py-6 text-muted" colSpan={5}>
                      Empty. Completions, scans, backtests, and graphs land here.
                    </td>
                  </tr>
                ) : (
                  shown.map((t) => (
                    <tr
                      key={t.id}
                      className="cursor-pointer border-t border-border hover:bg-elevated"
                      onClick={() => setOpen(t.id)}
                    >
                      <td className="px-5 py-2 font-mono tabular text-subtle">{fmtTime(t.ts)}</td>
                      <td className="py-2 capitalize">{t.cell}</td>
                      <td className="py-2 text-muted">{t.name}</td>
                      <td className="py-2">
                        <Badge tone={tone(t.status)}>{t.status}</Badge>
                      </td>
                      <td className="px-5 py-2 font-mono tabular">{t.durationMs}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Panel>
        <Panel>
          <PanelHeader title="Span" />
          {!active ? (
            <p className="text-sm text-muted">Select a row.</p>
          ) : (
            <div className="space-y-3 text-sm">
              <p>
                <span className="text-muted">{active.cell}</span> · {active.kind} · {active.name}
              </p>
              {active.input ? (
                <pre className="max-h-32 overflow-auto rounded-md border border-border bg-sunken p-3 text-xs text-muted">
                  {active.input}
                </pre>
              ) : null}
              {active.output ? (
                <pre className="max-h-40 overflow-auto rounded-md border border-border bg-sunken p-3 text-xs text-muted">
                  {active.output}
                </pre>
              ) : null}
            </div>
          )}
        </Panel>
      </div>

      {last ? (
        <Panel>
          <PanelHeader title={last.name} hint={`${last.cases.length} cases · local DeepEval-style scores`} />
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-subtle">
                <tr>
                  <th className="py-2">Case</th>
                  <th>Faith</th>
                  <th>Tox</th>
                  <th>Struct</th>
                  <th>Lat</th>
                </tr>
              </thead>
              <tbody>
                {last.cases.map((c, i) => (
                  <tr key={i} className="border-t border-border">
                    <td className="py-2">{c.input}</td>
                    <td className="tabular">{pct(c.scores.faithfulness, 0)}</td>
                    <td className="tabular">{pct(c.scores.toxicity, 0)}</td>
                    <td className="tabular">{pct(c.scores.structure, 0)}</td>
                    <td className="tabular">{pct(c.scores.latency, 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      ) : null}
    </CellFrame>
  );
}
