import { completeGrok, type CompleteInput, type GrokMsg } from "./grok";
import { streamGrok } from "./stream";
import { ENGINE_PROFILES, useLyte } from "./store";
import { parseJsonLoose, repairPrompt, schemaPrompt, validateSchema, type JsonSchema } from "./engines/schema";
import { scanGuard } from "./engines/guard";
import { searchMosaic } from "./engines/bm25";
import type { CellId } from "./cells";
import type { EngineId, RetrieveHit } from "./types";

export function gate(cell: CellId): { ok: true } | { ok: false; reason: string } {
  const s = useLyte.getState();
  if (s.isolated.includes(cell)) {
    return { ok: false, reason: `${cell} is isolated by YAWAR. Release it in Lattice.` };
  }
  return { ok: true };
}

function systemFor(engine: EngineId): string {
  const s = useLyte.getState();
  const base = ENGINE_PROFILES[engine].system;
  const ad = s.adapters.find((a) => a.bound);
  if (!ad) return base;
  const shots = ad.fewshot
    .map((f) => `Example user: ${f.user}\nExample assistant: ${f.assistant}`)
    .join("\n");
  const qlora = ad.qlora ? "QLoRA 4-bit pack. " : "";
  return `${base}\n\nBound adapter "${ad.name}" (${qlora}LoRA r=${ad.rank}, alpha=${ad.alpha}, modules ${ad.modules.join(",")}).\n${ad.systemAddendum}\n${shots}`;
}

function completeInput(opts: {
  user: string;
  extraSystem?: string;
  engine?: EngineId;
  history?: GrokMsg[];
  jsonSchema?: CompleteInput["jsonSchema"];
  jsonObject?: boolean;
}): CompleteInput {
  const engine = opts.engine ?? useLyte.getState().serve.engine;
  const profile = ENGINE_PROFILES[engine];
  const throttled =
    useLyte.getState().throttled.includes("serve") || useLyte.getState().throttled.includes("graph");
  const maxTokens = throttled ? Math.min(180, profile.maxTokens) : profile.maxTokens;
  const temp = useLyte.getState().serve.temperatureOverride ?? profile.temperature;
  const sys = [systemFor(engine), opts.extraSystem].filter(Boolean).join("\n\n");
  const messages: GrokMsg[] = [
    { role: "system", content: sys },
    ...(opts.history ?? []),
    { role: "user", content: opts.user.slice(0, 7000) },
  ];
  return {
    messages,
    temperature: temp,
    maxTokens,
    topP: profile.topP,
    stop: profile.stop,
    jsonSchema: opts.jsonSchema,
    jsonObject: opts.jsonObject ?? (profile.jsonBias && /json/i.test(opts.user)),
  };
}

export async function runComplete(opts: {
  cell: CellId;
  name: string;
  user: string;
  extraSystem?: string;
  engine?: EngineId;
  history?: GrokMsg[];
  jsonSchema?: CompleteInput["jsonSchema"];
  jsonObject?: boolean;
}): Promise<{ ok: true; text: string; usage: { prompt: number; completion: number } } | { ok: false; error: string }> {
  const g = gate(opts.cell);
  if (!g.ok) {
    useLyte.getState().addTrace({
      cell: opts.cell,
      kind: "blocked",
      name: opts.name,
      status: "blocked",
      durationMs: 0,
      output: g.reason,
    });
    return { ok: false, error: g.reason };
  }

  const engine = opts.engine ?? useLyte.getState().serve.engine;
  const input = completeInput(opts);
  const t0 = performance.now();
  const res = await completeGrok({ data: input });
  const durationMs = Math.round(performance.now() - t0);
  if (!res.ok) {
    useLyte.getState().addTrace({
      cell: opts.cell,
      kind: "llm",
      name: opts.name,
      status: "error",
      durationMs,
      input: opts.user.slice(0, 400),
      output: res.error,
      meta: { engine },
    });
    return res;
  }
  useLyte.getState().addTrace({
    cell: opts.cell,
    kind: "llm",
    name: opts.name,
    status: "ok",
    durationMs,
    input: opts.user.slice(0, 400),
    output: res.text.slice(0, 800),
    meta: { engine, usage: res.usage },
  });
  return res;
}

export async function runStream(opts: {
  cell: CellId;
  name: string;
  user: string;
  extraSystem?: string;
  engine?: EngineId;
  history?: GrokMsg[];
  onDelta: (chunk: string) => void;
}): Promise<
  | { ok: true; text: string; usage: { prompt: number; completion: number }; ttftMs: number; tokPerSec: number }
  | { ok: false; error: string }
> {
  const g = gate(opts.cell);
  if (!g.ok) {
    useLyte.getState().addTrace({
      cell: opts.cell,
      kind: "blocked",
      name: opts.name,
      status: "blocked",
      durationMs: 0,
      output: g.reason,
    });
    return { ok: false, error: g.reason };
  }
  const engine = opts.engine ?? useLyte.getState().serve.engine;
  const input = completeInput(opts);
  const t0 = performance.now();
  let first = 0;
  const res = await streamGrok(input, (chunk) => {
    if (!first) first = performance.now();
    opts.onDelta(chunk);
  });
  const durationMs = Math.round(performance.now() - t0);
  const ttftMs = first ? Math.round(first - t0) : durationMs;
  if (!res.ok) {
    useLyte.getState().addTrace({
      cell: opts.cell,
      kind: "llm",
      name: opts.name,
      status: "error",
      durationMs,
      input: opts.user.slice(0, 400),
      output: res.error,
      meta: { engine, stream: true },
    });
    return res;
  }
  const tokPerSec = durationMs > 0 ? (res.usage.completion || res.text.split(/\s+/).length) / (durationMs / 1000) : 0;
  useLyte.getState().addTrace({
    cell: opts.cell,
    kind: "llm",
    name: opts.name,
    status: "ok",
    durationMs,
    input: opts.user.slice(0, 400),
    output: res.text.slice(0, 800),
    meta: { engine, usage: res.usage, stream: true, ttftMs, tokPerSec },
  });
  return { ...res, ttftMs, tokPerSec: Number(tokPerSec.toFixed(1)) };
}

export async function runJson<T = unknown>(opts: {
  cell: CellId;
  name: string;
  instruction: string;
  schema: JsonSchema;
  engine?: EngineId;
}): Promise<{ ok: true; value: T; raw: string; attempts: number } | { ok: false; error: string; raw?: string; attempts: number }> {
  const schemaName = opts.name.replace(/[^A-Za-z0-9_]/g, "_").slice(0, 40) || "object";
  const first = await runComplete({
    cell: opts.cell,
    name: opts.name,
    engine: opts.engine ?? "sglang",
    user: schemaPrompt(opts.schema, opts.instruction),
    jsonSchema: { name: schemaName, schema: opts.schema, strict: true },
  });
  if (!first.ok) return { ...first, attempts: 1 };
  try {
    const value = parseJsonLoose(first.text);
    const errors = validateSchema(value, opts.schema);
    if (!errors.length) return { ok: true, value: value as T, raw: first.text, attempts: 1 };
    const repair = await runComplete({
      cell: opts.cell,
      name: `${opts.name} repair`,
      engine: "sglang",
      user: repairPrompt(opts.schema, first.text, errors),
      jsonSchema: { name: schemaName, schema: opts.schema, strict: true },
    });
    if (!repair.ok) return { ok: false, error: repair.error, raw: first.text, attempts: 2 };
    const value2 = parseJsonLoose(repair.text);
    const errors2 = validateSchema(value2, opts.schema);
    if (errors2.length) return { ok: false, error: errors2.join("; "), raw: repair.text, attempts: 2 };
    return { ok: true, value: value2 as T, raw: repair.text, attempts: 2 };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "JSON parse failed", raw: first.text, attempts: 1 };
  }
}

export function runLocalGuard(text: string, direction: "prompt" | "response" = "prompt") {
  const s = useLyte.getState();
  const verdict = scanGuard(text, s.guardPolicy, direction);
  s.addGuard(verdict);
  s.addTrace({
    cell: "guard",
    kind: "scan",
    name: `${direction} ${verdict.action}`,
    status: verdict.action === "block" ? "blocked" : verdict.action === "redact" ? "warn" : "ok",
    durationMs: 1,
    input: text.slice(0, 280),
    output: verdict.reason,
    meta: { action: verdict.action },
  });
  if (verdict.action === "block") s.emitLattice({ trigger: "guard.block", cell: "guard", detail: verdict.reason });
  if (verdict.action === "redact") s.emitLattice({ trigger: "guard.redact", cell: "guard", detail: verdict.reason });
  if (verdict.categories.find((c) => c.id === "injection" && c.hit)) {
    s.emitLattice({ trigger: "guard.injection", cell: "guard" });
  }
  return verdict;
}

export function retrieveHits(q: string, k = 5): RetrieveHit[] {
  const s = useLyte.getState();
  const hits = searchMosaic(s.mosaic, q, k);
  s.addTrace({
    cell: "retrieve",
    kind: "search",
    name: "BM25",
    status: hits.length ? "ok" : "warn",
    durationMs: 1,
    input: q,
    output: hits.map((h) => h.title).join(", ") || "no hits",
    meta: { k: hits.length },
  });
  return hits;
}

export async function rerankHits(q: string, hits: RetrieveHit[]): Promise<RetrieveHit[]> {
  if (hits.length <= 1) return hits;
  const res = await runComplete({
    cell: "retrieve",
    name: "Grok rerank",
    engine: "trtllm",
    jsonObject: true,
    user: `Rank these passages for the query. Return JSON {"order":[chunkId,...]} best-first.\nQuery: ${q}\nPassages:\n${hits
      .map((h) => `${h.chunkId} | ${h.title}: ${h.text.slice(0, 280)}`)
      .join("\n")}`,
  });
  if (!res.ok) return hits;
  try {
    const parsed = parseJsonLoose(res.text) as { order?: string[] };
    const order = parsed.order ?? [];
    const map = new Map(hits.map((h) => [h.chunkId, h]));
    const ranked: RetrieveHit[] = [];
    order.forEach((id, i) => {
      const h = map.get(id);
      if (h) {
        ranked.push({ ...h, rerank: hits.length - i });
        map.delete(id);
      }
    });
    for (const rest of map.values()) ranked.push(rest);
    return ranked;
  } catch {
    return hits;
  }
}
