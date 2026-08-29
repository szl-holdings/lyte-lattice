import type { MosaicChunk, MosaicDoc } from "../types";

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

/** MosaicML-style weighted mix: draw `n` chunks proportional to doc weight × quality. */
export function mixSample(docs: MosaicDoc[], n: number, seed = 1): MosaicChunk[] {
  const pool = docs.flatMap((d) => d.chunks.map((c) => ({ c, w: Math.max(0.05, d.weight) * (0.5 + d.quality) })));
  if (!pool.length || n <= 0) return [];
  const total = pool.reduce((s, p) => s + p.w, 0);
  const rng = mulberry32(seed);
  const out: MosaicChunk[] = [];
  for (let i = 0; i < n; i++) {
    let r = rng() * total;
    let chosen = pool[0]!.c;
    for (const p of pool) {
      r -= p.w;
      if (r <= 0) {
        chosen = p.c;
        break;
      }
    }
    out.push(chosen);
  }
  return out;
}

export function mixRecipe(docs: MosaicDoc[]): { title: string; share: number; tokens: number }[] {
  const tokens = docs.map((d) => ({
    title: d.title,
    tokens: d.chunks.reduce((s, c) => s + c.tokens, 0) * d.weight,
  }));
  const total = tokens.reduce((s, t) => s + t.tokens, 0) || 1;
  return tokens.map((t) => ({ title: t.title, share: t.tokens / total, tokens: Math.round(t.tokens) }));
}
