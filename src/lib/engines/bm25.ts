import type { MosaicDoc, RetrieveHit } from "../types";

function tokenize(s: string): string[] {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .split(/\s+/)
    .filter((w) => w.length > 1);
}

export function searchMosaic(docs: MosaicDoc[], query: string, k = 6): RetrieveHit[] {
  const qTokens = tokenize(query);
  if (qTokens.length === 0) return [];
  const chunks = docs.flatMap((d) => d.chunks.map((c) => ({ doc: d, chunk: c })));
  if (chunks.length === 0) return [];

  const df = new Map<string, number>();
  const docsTokens = chunks.map(({ chunk }) => tokenize(chunk.text));
  for (const toks of docsTokens) {
    const uniq = new Set(toks);
    for (const t of uniq) df.set(t, (df.get(t) ?? 0) + 1);
  }

  const N = chunks.length;
  const avgdl = docsTokens.reduce((s, t) => s + t.length, 0) / N;
  const k1 = 1.5;
  const b = 0.75;

  const scored: RetrieveHit[] = chunks.map(({ doc, chunk }, i) => {
    const toks = docsTokens[i];
    const tf = new Map<string, number>();
    for (const t of toks) tf.set(t, (tf.get(t) ?? 0) + 1);
    const dl = toks.length || 1;
    let score = 0;
    for (const qt of qTokens) {
      const f = tf.get(qt) ?? 0;
      if (!f) continue;
      const n = df.get(qt) ?? 0;
      const idf = Math.log(1 + (N - n + 0.5) / (n + 0.5));
      score += idf * ((f * (k1 + 1)) / (f + k1 * (1 - b + b * (dl / avgdl))));
    }
    score *= 0.65 + 0.35 * doc.quality;
    score *= 0.7 + 0.3 * Math.min(2, doc.weight);
    return {
      chunkId: chunk.id,
      docId: doc.id,
      title: doc.title,
      text: chunk.text,
      score,
    };
  });

  return scored
    .filter((h) => h.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, k);
}
