import type { Bar } from "./types";

function mulberry32(seed: number) {
  let a = seed >>> 0;
  return () => {
    a += 0x6d2b79f5;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function sessionDays(n: number, end = new Date("2026-08-28")): string[] {
  const days: string[] = [];
  const d = new Date(Date.UTC(end.getUTCFullYear(), end.getUTCMonth(), end.getUTCDate()));
  while (days.length < n) {
    const wd = d.getUTCDay();
    if (wd !== 0 && wd !== 6) days.push(d.toISOString().slice(0, 10));
    d.setUTCDate(d.getUTCDate() - 1);
  }
  return days.reverse();
}

function round2(n: number) {
  return Math.round(n * 100) / 100;
}

function path(seed: number, start: number, vol: number, n: number, drift: number): Bar[] {
  const rng = mulberry32(seed);
  const days = sessionDays(n);
  let px = start;
  return days.map((d) => {
    const shock = (rng() * 2 - 1) * vol;
    const o = px;
    const c = Math.max(1, o * (1 + drift + shock));
    const span = vol * 0.55;
    const h = Math.max(o, c) * (1 + rng() * span);
    const l = Math.min(o, c) * (1 - rng() * span);
    const v = Math.round(18_000_000 + rng() * 90_000_000);
    px = c;
    return { d, o: round2(o), h: round2(h), l: round2(l), c: round2(c), v };
  });
}

export const MARKET: Record<string, Bar[]> = {
  SPY: path(11, 512.4, 0.0072, 252, 0.00028),
  AAPL: path(23, 187.2, 0.013, 252, 0.00034),
  MSFT: path(41, 415.8, 0.011, 252, 0.0003),
  NVDA: path(73, 108.6, 0.022, 252, 0.00058),
};

export const SYMBOLS = Object.keys(MARKET);
