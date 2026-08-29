import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { toast } from "sonner";
import { CellFrame } from "./cell-frame";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field, Panel, PanelHeader } from "@/components/ui/panel";
import { backtest } from "@/lib/engines/quant";
import { MARKET, SYMBOLS } from "@/lib/market";
import { runComplete } from "@/lib/run-ai";
import { useLyte } from "@/lib/store";
import type { QuantKind } from "@/lib/types";
import { cn, money, pct } from "@/lib/utils";

function ParamSlider({
  label,
  value,
  min,
  max,
  step = 1,
  digits,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  digits?: number;
  onChange: (n: number) => void;
}) {
  const shown = digits != null ? value.toFixed(digits) : String(value);
  return (
    <Field label={`${label} ${shown}`}>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        aria-label={label}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-[var(--color-accent)]"
      />
    </Field>
  );
}

function kindHint(kind: QuantKind) {
  if (kind === "sma") return "Buy when fast SMA crosses above slow. Flatten on the cross back.";
  if (kind === "meanrev") return "Fade z beyond the threshold on the lookback window.";
  if (kind === "momentum") return "Hold when trailing-window return is positive.";
  return "Buy once at the first close. No free parameters.";
}

export function QuantView() {
  const strategies = useLyte((s) => s.strategies);
  const runs = useLyte((s) => s.quantRuns);
  const addRun = useLyte((s) => s.addQuantRun);
  const updateStrategy = useLyte((s) => s.updateStrategy);
  const [sid, setSid] = useState(strategies[0]?.id ?? "");
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const st = strategies.find((s) => s.id === sid) ?? strategies[0];
  const last = runs.find((r) => r.strategyId === st?.id) ?? runs[0];

  const bars = st ? MARKET[st.symbol] : undefined;

  function setParam(patch: Record<string, number>) {
    if (!st) return;
    const next = { ...st.params, ...patch };
    if (st.kind === "sma") {
      const fastN = Math.round(next.fast ?? 10);
      let slowN = Math.round(next.slow ?? 30);
      if (fastN >= slowN) slowN = fastN + 1;
      next.fast = fastN;
      next.slow = slowN;
    }
    updateStrategy(st.id, { params: next });
  }

  function run() {
    if (!st || !bars) return;
    const result = backtest(bars, st.kind, st.params, st.id);
    addRun(result);
    useLyte.getState().addTrace({
      cell: "quant",
      kind: "backtest",
      name: st.name,
      status: result.stats.maxdd < -0.2 ? "warn" : "ok",
      durationMs: 4,
      output: `ret ${pct(result.stats.ret)} sharpe ${result.stats.sharpe.toFixed(2)} dd ${pct(result.stats.maxdd)} win ${pct(result.stats.win)}`,
    });
    if (result.stats.maxdd < -0.2) {
      useLyte.getState().emitLattice({
        trigger: "quant.drawdown",
        cell: "quant",
        detail: result.stats.maxdd.toFixed(3),
      });
    }
    toast.success(`Backtest ${st.symbol} complete.`);
  }

  async function brief() {
    if (!last || !st || busy) return;
    setBusy(true);
    const res = await runComplete({
      cell: "quant",
      name: "desk brief",
      engine: "trtllm",
      user: `Write a 4-sentence desk brief for ${st.name} on ${st.symbol}. Stats: return ${pct(last.stats.ret)}, Sharpe ${last.stats.sharpe.toFixed(2)}, max DD ${pct(last.stats.maxdd)}, win ${pct(last.stats.win)}, trades ${last.stats.trades}, CAGR ${pct(last.stats.cagr)}. Deterministic synthetic bars, not live broker fills.`,
    });
    setBusy(false);
    if (!res.ok) toast.error(res.error);
    else setNote(res.text);
  }

  const chart = useMemo(
    () =>
      last?.equity.filter((_, i) => i % 3 === 0).map((p) => ({ d: p.d.slice(5), v: Math.round(p.v) })) ?? [],
    [last],
  );

  const fast = st?.params.fast ?? 10;
  const slow = st?.params.slow ?? 30;
  const lookback = st?.params.lookback ?? 20;
  const z = st?.params.z ?? 1.2;
  const mom = st?.params.mom ?? 60;

  return (
    <CellFrame id="quant">
      <p className="max-w-3xl text-sm text-muted">
        Deterministic synthetic daily bars, close fills, no live broker.
      </p>

      <div className="flex flex-wrap gap-2">
        {strategies.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => setSid(s.id)}
            className={cn(
              "rounded-sm border px-3 py-2 text-left text-sm",
              s.id === st?.id ? "border-accent bg-elevated" : "border-border bg-surface",
            )}
          >
            <span className="block font-medium">{s.name}</span>
            <span className="font-mono text-[11px] text-subtle">{s.symbol}</span>
          </button>
        ))}
      </div>
      <p className="font-mono text-[11px] text-subtle">Market {SYMBOLS.join(" · ")}</p>

      {st ? (
        <Panel>
          <PanelHeader
            title="Parameters"
            hint={`${kindHint(st.kind)} Re-run to mark equity.`}
            action={<Badge tone="muted">{st.kind}</Badge>}
          />
          {st.kind === "sma" ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <ParamSlider
                label="Fast"
                value={fast}
                min={2}
                max={80}
                onChange={(n) => setParam({ fast: n })}
              />
              <ParamSlider
                label="Slow"
                value={slow}
                min={5}
                max={200}
                onChange={(n) => setParam({ slow: n })}
              />
            </div>
          ) : null}
          {st.kind === "meanrev" ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <ParamSlider
                label="Lookback"
                value={lookback}
                min={5}
                max={90}
                onChange={(n) => setParam({ lookback: n })}
              />
              <ParamSlider
                label="Z"
                value={z}
                min={0.4}
                max={3}
                step={0.1}
                digits={1}
                onChange={(n) => setParam({ z: n })}
              />
            </div>
          ) : null}
          {st.kind === "momentum" ? (
            <ParamSlider
              label="Mom window"
              value={mom}
              min={5}
              max={180}
              onChange={(n) => setParam({ mom: n })}
            />
          ) : null}
          {st.kind === "buyhold" ? (
            <p className="text-sm text-muted">Buy and hold has no free parameters.</p>
          ) : null}
        </Panel>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <Button type="button" onClick={run}>
          Run backtest
        </Button>
        <Button type="button" variant="secondary" disabled={!last || busy} onClick={() => void brief()}>
          {busy ? "Briefing…" : "Desk brief"}
        </Button>
      </div>

      {last ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {[
            ["Return", pct(last.stats.ret)],
            ["CAGR", pct(last.stats.cagr)],
            ["Sharpe", last.stats.sharpe.toFixed(2)],
            ["Max DD", pct(last.stats.maxdd)],
            ["Win", pct(last.stats.win)],
            ["Trades", String(last.stats.trades)],
          ].map(([k, v]) => (
            <Panel key={k}>
              <p className="font-mono text-[10px] uppercase tracking-wider text-subtle">{k}</p>
              <p className="mt-1 font-mono text-xl tabular">{v}</p>
            </Panel>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted">Run a strategy to mark equity to the synthetic close.</p>
      )}

      {chart.length ? (
        <Panel pad={false} className="p-4">
          <PanelHeader title="Equity" hint="Start cash 100,000 · daily close fills · no shorting." />
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chart}>
                <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" />
                <XAxis dataKey="d" tick={{ fill: "var(--color-subtle)", fontSize: 11 }} />
                <YAxis
                  tick={{ fill: "var(--color-subtle)", fontSize: 11 }}
                  tickFormatter={(v) => `${Math.round(Number(v) / 1000)}k`}
                />
                <Tooltip
                  contentStyle={{
                    background: "var(--color-elevated)",
                    border: "1px solid var(--color-border)",
                    borderRadius: 8,
                  }}
                  formatter={(v) => money(Number(v))}
                />
                <Line type="monotone" dataKey="v" stroke="var(--color-accent)" dot={false} strokeWidth={1.6} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      ) : null}

      {last ? (
        <Panel>
          <PanelHeader title="Fills" />
          <div className="max-h-48 overflow-y-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-subtle">
                <tr>
                  <th className="py-2">Date</th>
                  <th>Side</th>
                  <th>Px</th>
                  <th>Qty</th>
                </tr>
              </thead>
              <tbody>
                {last.trades.map((t, i) => (
                  <tr key={i} className="border-t border-border">
                    <td className="py-1.5 tabular">{t.d}</td>
                    <td>
                      <Badge tone={t.side === "buy" ? "ok" : "warn"}>{t.side}</Badge>
                    </td>
                    <td className="tabular">{t.px.toFixed(2)}</td>
                    <td className="tabular">{t.qty}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      ) : null}

      {note ? (
        <Panel>
          <PanelHeader title="Desk brief" />
          <p className="text-sm leading-relaxed text-muted">{note}</p>
        </Panel>
      ) : null}
    </CellFrame>
  );
}
