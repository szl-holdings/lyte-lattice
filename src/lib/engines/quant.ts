import type { Bar, QuantKind, QuantRun, QuantTrade } from "../types";
import { uid } from "../utils";

function sma(values: number[], n: number): Array<number | null> {
  const out: Array<number | null> = [];
  let sum = 0;
  for (let i = 0; i < values.length; i++) {
    sum += values[i];
    if (i >= n) sum -= values[i - n];
    out.push(i >= n - 1 ? sum / n : null);
  }
  return out;
}

function mean(xs: number[]) {
  if (!xs.length) return 0;
  return xs.reduce((a, b) => a + b, 0) / xs.length;
}

function stdev(xs: number[]) {
  if (xs.length < 2) return 0;
  const m = mean(xs);
  const v = xs.reduce((s, x) => s + (x - m) ** 2, 0) / (xs.length - 1);
  return Math.sqrt(v);
}

function maxDrawdown(equity: number[]) {
  let peak = equity[0] ?? 1;
  let dd = 0;
  for (const v of equity) {
    if (v > peak) peak = v;
    dd = Math.min(dd, peak === 0 ? 0 : v / peak - 1);
  }
  return dd;
}

export function backtest(
  bars: Bar[],
  kind: QuantKind,
  params: Record<string, number>,
  strategyId: string,
): QuantRun {
  const closes = bars.map((b) => b.c);
  const cash0 = 100_000;
  let cash = cash0;
  let qty = 0;
  const trades: QuantTrade[] = [];
  const equity: { d: string; v: number }[] = [];

  const fastN = Math.round(params.fast ?? 10);
  const slowN = Math.round(params.slow ?? 30);
  const look = Math.round(params.lookback ?? 20);
  const zEnter = params.z ?? 1.2;
  const momN = Math.round(params.mom ?? 60);

  const fast = sma(closes, fastN);
  const slow = sma(closes, slowN);

  for (let i = 0; i < bars.length; i++) {
    const px = closes[i];
    let target = qty;

    if (kind === "buyhold") {
      target = i === 0 ? Math.floor(cash0 / px) : qty;
    } else if (kind === "sma") {
      const f = fast[i];
      const s = slow[i];
      if (f != null && s != null) target = f > s ? Math.floor((cash + qty * px) * 0.99 / px) : 0;
    } else if (kind === "meanrev") {
      if (i >= look) {
        const window = closes.slice(i - look, i);
        const m = mean(window);
        const sd = stdev(window) || 1e-9;
        const z = (px - m) / sd;
        if (z < -zEnter) target = Math.floor((cash + qty * px) * 0.95 / px);
        else if (z > zEnter) target = 0;
      }
    } else if (kind === "momentum") {
      if (i >= momN) {
        const ret = px / closes[i - momN] - 1;
        target = ret > 0 ? Math.floor((cash + qty * px) * 0.99 / px) : 0;
      }
    }

    if (target !== qty) {
      const delta = target - qty;
      const side: "buy" | "sell" = delta > 0 ? "buy" : "sell";
      const abs = Math.abs(delta);
      cash -= delta * px;
      qty = target;
      trades.push({ d: bars[i].d, side, px, qty: abs });
    }
    equity.push({ d: bars[i].d, v: cash + qty * px });
  }

  const series = equity.map((e) => e.v);
  const rets: number[] = [];
  for (let i = 1; i < series.length; i++) {
    const prev = series[i - 1];
    if (prev) rets.push(series[i] / prev - 1);
  }
  const last = series[series.length - 1] ?? cash0;
  const first = series[0] ?? cash0;
  const ret = first ? last / first - 1 : 0;
  const years = Math.max(1 / 252, series.length / 252);
  const cagr = first > 0 ? Math.pow(last / first, 1 / years) - 1 : 0;
  const sharpe = (mean(rets) / (stdev(rets) || 1e-9)) * Math.sqrt(252);
  const wins = trades.filter((t, idx) => {
    if (t.side !== "sell") return false;
    const buy = [...trades.slice(0, idx)].reverse().find((x) => x.side === "buy");
    return buy ? t.px > buy.px : false;
  }).length;
  const sells = trades.filter((t) => t.side === "sell").length;

  return {
    id: uid("qrun"),
    strategyId,
    ts: Date.now(),
    equity,
    trades,
    stats: {
      ret,
      sharpe: Number.isFinite(sharpe) ? sharpe : 0,
      maxdd: maxDrawdown(series),
      win: sells ? wins / sells : 0,
      trades: trades.length,
      cagr,
    },
  };
}
