import { useState } from "react";
import { toast } from "sonner";
import { CellFrame } from "./cell-frame";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { executeGraph } from "@/lib/engines/graph-run";
import { gate } from "@/lib/run-ai";
import { useLyte } from "@/lib/store";
import type { GraphStep } from "@/lib/types";
import { cn } from "@/lib/utils";

export function GraphView() {
  const graphs = useLyte((s) => s.graphs);
  const runs = useLyte((s) => s.graphRuns);
  const [gid, setGid] = useState(graphs[0]?.id ?? "");
  const graph = graphs.find((g) => g.id === gid) ?? graphs[0];
  const [input, setInput] = useState(
    "Water loss at Marcus Chen home. Pipe burst, kitchen ceiling collapsed. Need FNOL handling.",
  );
  const [busy, setBusy] = useState(false);
  const [liveSteps, setLiveSteps] = useState<GraphStep[]>([]);

  async function run() {
    if (!graph || busy) return;
    const g = gate("graph");
    if (!g.ok) {
      toast.error(g.reason);
      return;
    }
    setBusy(true);
    setLiveSteps([]);
    try {
      const result = await executeGraph(graph, input.trim(), (step) => {
        setLiveSteps((prev) => [...prev, step]);
      });
      if (result.status === "blocked") toast.message("Graph halted on Guard.");
      else if (result.status === "error") toast.error("Graph finished with an error.");
      else toast.success("Graph completed.");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Graph failed.");
    } finally {
      setBusy(false);
    }
  }

  const last = runs.find((r) => r.graphId === graph?.id) ?? runs[0];
  const steps = busy ? liveSteps : last?.steps ?? [];
  const liveNodeId = busy ? liveSteps[liveSteps.length - 1]?.nodeId : undefined;
  const blockedIds = new Set(steps.filter((st) => st.status === "blocked").map((st) => st.nodeId));

  return (
    <CellFrame id="graph">
      <div className="flex flex-wrap gap-2">
        {graphs.map((g) => (
          <button
            key={g.id}
            type="button"
            onClick={() => setGid(g.id)}
            className={cn(
              "rounded-sm border px-3 py-2 text-left text-sm",
              g.id === graph?.id ? "border-accent bg-elevated" : "border-border bg-surface",
            )}
          >
            <span className="block font-medium">{g.name}</span>
            <span className="block text-xs text-muted">{g.blurb}</span>
          </button>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <Panel pad={false}>
          <div className="px-5 pt-5">
            <PanelHeader title="Graph" hint="LangGraph-style interpreter. Nodes call live cells." />
          </div>
          {graph ? (
            <svg viewBox="0 0 100 80" className="h-auto w-full px-2 pb-3" aria-label={graph.name}>
              {graph.edges.map((e, i) => {
                const a = graph.nodes.find((n) => n.id === e.from);
                const b = graph.nodes.find((n) => n.id === e.to);
                if (!a || !b) return null;
                return (
                  <g key={i}>
                    <line
                      x1={a.x}
                      y1={a.y}
                      x2={b.x}
                      y2={b.y}
                      stroke="var(--color-border-strong)"
                      strokeWidth={0.4}
                    />
                    {e.when !== "always" ? (
                      <text
                        x={(a.x + b.x) / 2}
                        y={(a.y + b.y) / 2 - 1.5}
                        textAnchor="middle"
                        fill="var(--color-subtle)"
                        style={{ fontSize: 2.2 }}
                      >
                        {e.when}
                      </text>
                    ) : null}
                  </g>
                );
              })}
              {graph.nodes.map((n) => {
                const blocked = blockedIds.has(n.id);
                const live = liveNodeId === n.id && !blocked;
                const fill = blocked
                  ? "var(--color-danger)"
                  : live
                    ? "var(--color-accent)"
                    : "var(--color-elevated)";
                const stroke = blocked
                  ? "var(--color-danger)"
                  : live
                    ? "var(--color-accent)"
                    : "var(--color-border-strong)";
                const label = live ? "var(--color-accent-fg)" : "var(--color-fg)";
                return (
                  <g key={n.id} transform={`translate(${n.x} ${n.y})`}>
                    <rect
                      x={-11}
                      y={-4.2}
                      width={22}
                      height={8.4}
                      rx={1.2}
                      fill={fill}
                      stroke={stroke}
                      strokeWidth={live || blocked ? 0.55 : 0.35}
                      className={blocked ? "animate-pulse" : undefined}
                    />
                    <text
                      y={0.7}
                      textAnchor="middle"
                      fill={label}
                      style={{ fontSize: 2.05, fontFamily: "IBM Plex Sans, sans-serif" }}
                    >
                      {n.label}
                    </text>
                  </g>
                );
              })}
            </svg>
          ) : null}
          <form
            className="border-t border-border p-4"
            onSubmit={(e) => {
              e.preventDefault();
              void run();
            }}
          >
            <Textarea value={input} onChange={(e) => setInput(e.target.value)} rows={4} />
            <div className="mt-3 flex justify-end">
              <Button type="submit" disabled={busy || !input.trim()}>
                {busy ? "Running…" : "Run graph"}
              </Button>
            </div>
          </form>
        </Panel>
        <Panel>
          <PanelHeader
            title="Last run"
            hint={busy ? "Steps land as each node finishes." : "Each step is a real engine call."}
          />
          {busy && liveSteps.length === 0 ? (
            <p className="text-sm text-muted">Running…</p>
          ) : steps.length === 0 ? (
            <p className="text-sm text-muted">No runs yet.</p>
          ) : (
            <ol className="space-y-3">
              {steps.map((st, i) => (
                <li key={`${st.nodeId}-${i}`} className="rounded-md border border-border bg-sunken p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium">{st.label}</span>
                    <Badge
                      tone={st.status === "ok" ? "ok" : st.status === "blocked" ? "danger" : "warn"}
                    >
                      {st.status}
                    </Badge>
                  </div>
                  <p className="mt-2 max-h-28 overflow-y-auto whitespace-pre-wrap text-xs text-muted">
                    {st.output || "—"}
                  </p>
                </li>
              ))}
            </ol>
          )}
        </Panel>
      </div>
    </CellFrame>
  );
}
