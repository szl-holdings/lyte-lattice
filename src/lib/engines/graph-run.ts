import { coverageCheck, inferCause, nextClaimNumber, suggestedReserve } from "./cover";
import { backtest } from "./quant";
import { MARKET } from "../market";
import { retrieveHits, runComplete, runJson, runLocalGuard } from "../run-ai";
import { useLyte } from "../store";
import type { CoverClaim, GraphDef, GraphRun, GraphStep, TraceStatus } from "../types";
import { uid } from "../utils";

export async function executeGraph(
  graph: GraphDef,
  input: string,
  onStep?: (step: GraphStep) => void,
): Promise<GraphRun> {
  const s = useLyte.getState();
  const t0 = Date.now();
  const steps: GraphStep[] = [];
  const ctx: Record<string, string> = { input };
  let blocked = false;

  const start = graph.nodes.find((n) => n.type === "input") ?? graph.nodes[0];

  const queue: string[] = start ? [start.id] : [];
  const seen = new Set<string>();

  while (queue.length) {
    const id = queue.shift()!;
    if (seen.has(id)) continue;
    seen.add(id);
    const node = graph.nodes.find((n) => n.id === id);
    if (!node) continue;
    const ns = Date.now();
    let output = "";
    let status: TraceStatus = "ok";

    try {
      if (node.type === "input") {
        output = input;
        ctx.input = input;
      } else if (node.type === "retrieve") {
        const hits = retrieveHits(ctx.input || input, Number(node.config.k ?? 4));
        output = hits.map((h, i) => `[${i + 1}] ${h.title}: ${h.text}`).join("\n\n") || "No mosaic hits.";
        ctx.retrieve = output;
      } else if (node.type === "guard") {
        const text = ctx.serve || ctx.input || input;
        const v = runLocalGuard(text, ctx.serve ? "response" : "prompt");
        output = `${v.action}: ${v.reason}`;
        ctx.guard = v.action;
        ctx.guardText = v.action === "redact" ? v.redacted : text;
        if (v.action === "block") {
          blocked = true;
          status = "blocked";
        }
      } else if (node.type === "condition") {
        const truth = ctx.guard === "block" || blocked;
        output = truth ? "true" : "false";
        ctx.cond = output;
      } else if (node.type === "serve") {
        const prompt = [
          ctx.retrieve ? `Context from Retrieve:\n${ctx.retrieve.slice(0, 2500)}` : "",
          ctx.quant ? `Quant snapshot:\n${ctx.quant}` : "",
          `Operator:\n${ctx.guardText || ctx.input || input}`,
        ]
          .filter(Boolean)
          .join("\n\n");
        const engine = (node.config.engine as "vllm" | "sglang" | "ollama" | "trtllm") || "vllm";
        const res = await runComplete({
          cell: "graph",
          name: `graph ${graph.name} / ${node.label}`,
          user: prompt,
          engine,
        });
        if (!res.ok) {
          status = "error";
          output = res.error;
        } else {
          output = res.text;
          ctx.serve = res.text;
        }
      } else if (node.type === "schema") {
        const tpl = s.schemas.find((t) => t.id === (node.config.template || "sch_claim")) ?? s.schemas[0];
        const res = await runJson({
          cell: "graph",
          name: `graph schema ${tpl?.name ?? ""}`,
          instruction: `Extract from this narrative:\n${ctx.guardText || ctx.input || input}`,
          schema: tpl.schema,
        });
        if (!res.ok) {
          status = "error";
          output = res.error;
        } else {
          output = JSON.stringify(res.value, null, 2);
          ctx.schema = output;
          useLyte.getState().setSchemaOutput(tpl.id, res.value, res.raw, res.attempts);
        }
      } else if (node.type === "cover") {
        const narrative = ctx.guardText || ctx.input || input;
        let extracted: Record<string, string> = {};
        try {
          extracted = ctx.schema ? (JSON.parse(ctx.schema) as Record<string, string>) : {};
        } catch {
          extracted = {};
        }
        const policy = s.policies[0];
        const cause = String(extracted.cause || inferCause(narrative));
        const check = coverageCheck(policy, cause);
        const claim: CoverClaim = {
          id: uid("clm"),
          number: nextClaimNumber(useLyte.getState().claims),
          policyId: policy.id,
          status: check.covered ? "open" : "denied",
          cause,
          narrative,
          lossDate: String(extracted.lossDate || new Date().toISOString().slice(0, 10)),
          reserve: check.covered ? Number(extracted.reserveHint || suggestedReserve(narrative, policy)) : 0,
          paid: 0,
          extracted: Object.fromEntries(Object.entries(extracted).map(([k, v]) => [k, String(v)])),
          notes: [{ ts: Date.now(), text: `Opened from Graph "${graph.name}". ${check.reason}` }],
        };
        useLyte.getState().addClaim(claim);
        output = `${claim.number} ${claim.status} · ${cause} · reserve ${claim.reserve}`;
        ctx.cover = output;
        if (claim.reserve > 50000) {
          useLyte.getState().emitLattice({ trigger: "cover.reserve>", cell: "cover", detail: String(claim.reserve) });
        }
      } else if (node.type === "quant") {
        const last = s.quantRuns[0];
        const st = s.strategies[0];
        if (last) {
          output = `${st?.name ?? last.strategyId}: ret ${(last.stats.ret * 100).toFixed(1)}%, Sharpe ${last.stats.sharpe.toFixed(2)}, maxDD ${(last.stats.maxdd * 100).toFixed(1)}%, trades ${last.stats.trades}`;
        } else {
          const run = backtest(MARKET[st.symbol] ?? MARKET.SPY, st.kind, st.params, st.id);
          useLyte.getState().addQuantRun(run);
          output = `Ran ${st.name}: ret ${(run.stats.ret * 100).toFixed(1)}%, Sharpe ${run.stats.sharpe.toFixed(2)}`;
        }
        ctx.quant = output;
      } else if (node.type === "end") {
        output = ctx.serve || ctx.cover || ctx.schema || ctx.quant || ctx.guardText || input;
      }
    } catch (e) {
      status = "error";
      output = e instanceof Error ? e.message : "node failed";
    }

    const step: GraphStep = {
      nodeId: node.id,
      label: node.label,
      output,
      status,
      durationMs: Date.now() - ns,
    };
    steps.push(step);
    onStep?.(step);

    const cond = ctx.cond;
    for (const e of graph.edges.filter((x) => x.from === node.id)) {
      if (e.when === "always") queue.push(e.to);
      else if (e.when === "true" && cond === "true") queue.push(e.to);
      else if (e.when === "false" && cond !== "true") queue.push(e.to);
    }
  }

  const fail = steps.find((st) => st.status === "error" || st.status === "blocked");
  const result = [...steps].reverse().find((st) => st.output)?.output ?? "";
  const run: GraphRun = {
    id: uid("grun"),
    graphId: graph.id,
    ts: t0,
    status: fail ? fail.status : "ok",
    input,
    steps,
    result,
  };
  useLyte.getState().addGraphRun(run);
  useLyte.getState().addTrace({
    cell: "graph",
    kind: "run",
    name: graph.name,
    status: run.status,
    durationMs: Date.now() - t0,
    input,
    output: result.slice(0, 600),
  });
  return run;
}
