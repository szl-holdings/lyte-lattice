import type { MosaicChunk } from "../types";

export function estimateTokens(text: string): number {
  return Math.max(1, Math.round(text.trim().split(/\s+/).length * 1.3));
}

export function chunkText(text: string, size = 90, overlap = 18): string[] {
  const words = text.replace(/\s+/g, " ").trim().split(" ").filter(Boolean);
  if (words.length === 0) return [];
  const chunks: string[] = [];
  let i = 0;
  while (i < words.length) {
    const slice = words.slice(i, i + size);
    chunks.push(slice.join(" "));
    if (i + size >= words.length) break;
    i += Math.max(1, size - overlap);
  }
  return chunks;
}

export function buildChunks(docId: string, text: string): MosaicChunk[] {
  return chunkText(text).map((t, i) => ({
    id: `${docId}_c${i}`,
    docId,
    text: t,
    tokens: estimateTokens(t),
  }));
}
