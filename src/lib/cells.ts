export const CELL_IDS = [
  "lyte",
  "serve",
  "graph",
  "guard",
  "mosaic",
  "lattice",
  "cover",
  "quant",
  "retrieve",
  "observe",
  "tune",
  "schema",
] as const;

export type CellId = (typeof CELL_IDS)[number];

export type CellHonesty = "LIVE" | "STRUCTURAL-ONLY";

export type CellMeta = {
  id: CellId;
  n: string;
  title: string;
  cited: string;
  blurb: string;
  engine: string;
  honesty: CellHonesty;
};

export const CELLS: CellMeta[] = [
  {
    id: "lyte",
    n: "lyte",
    title: "Lyte",
    cited: "Owner-admitted design-partner cell",
    blurb:
      "Admitted STRUCTURAL-ONLY hub. Binds every cell and shows lattice health. Not a second flagship.",
    engine: "In-console lattice map + bind bus",
    honesty: "STRUCTURAL-ONLY",
  },
  {
    id: "serve",
    n: "N1",
    title: "Serve",
    cited: "vLLM / SGLang / Ollama / TensorRT-LLM",
    blurb:
      "Streaming inference with four engine profiles. Completions run on Grok 4.5; profiles change decoding, system, JSON bias, and latency posture. Not a local GPU cluster.",
    engine: "Grok 4.5 streaming via engine profiles",
    honesty: "LIVE",
  },
  {
    id: "graph",
    n: "N2",
    title: "Graph",
    cited: "LangGraph agent orchestration",
    blurb: "Stateful graphs with Serve, Retrieve, Guard, Schema, Cover, and Quant nodes. Live steps, not storyboards.",
    engine: "In-browser graph interpreter",
    honesty: "LIVE",
  },
  {
    id: "guard",
    n: "N3",
    title: "Guard",
    cited: "Llama Guard prompt/response safeguard",
    blurb: "Local classifiers mapped to Llama Guard S-codes, plus an optional Grok deep scan. Verdicts feed Lattice.",
    engine: "Local classifiers + optional Grok judge",
    honesty: "LIVE",
  },
  {
    id: "mosaic",
    n: "N4",
    title: "Mosaic",
    cited: "MosaicML / Databricks own-data mosaic",
    blurb: "Own-data corpus with weights, quality, mix recipes, and streaming draws. Mixes feed Retrieve, Tune, and Graph.",
    engine: "Weighted mix + chunker",
    honesty: "LIVE",
  },
  {
    id: "lattice",
    n: "N5",
    title: "Lattice",
    cited: "Immune-lattice SENTRA / YAWAR overlay bind",
    blurb: "SENTRA detects. YAWAR responds. Fire rules, isolate, throttle, redact, or escalate cells from live events.",
    engine: "Policy overlay on the bind bus",
    honesty: "LIVE",
  },
  {
    id: "cover",
    n: "N6",
    title: "Cover",
    cited: "Guidewire P&C core",
    blurb: "Policies, FNOL, peril matrix, coverage check, reserves, payments, and notes. AI extraction lands structured claim fields via Schema.",
    engine: "P&C core + Grok extract",
    honesty: "LIVE",
  },
  {
    id: "quant",
    n: "N7",
    title: "Quant",
    cited: "QuantConnect LEAN",
    blurb: "LEAN-style backtests on deterministic daily bars. Editable SMA, mean reversion, momentum, buy-and-hold, with live stats. Not a live broker.",
    engine: "In-browser event-driven backtester",
    honesty: "LIVE",
  },
  {
    id: "retrieve",
    n: "N9",
    title: "Retrieve",
    cited: "LlamaIndex / Haystack / Letta",
    blurb: "BM25 over the mosaic, optional Grok rerank, and Letta-style memory threads the rest of the lattice can read.",
    engine: "BM25 + memory + optional Grok rerank",
    honesty: "LIVE",
  },
  {
    id: "observe",
    n: "N10",
    title: "Observe",
    cited: "Phoenix / LangSmith / Langfuse / DeepEval",
    blurb: "Every cell emits spans. Inspect traces, latency by cell, and run a local eval harness on recent outputs.",
    engine: "In-console tracer + eval harness",
    honesty: "LIVE",
  },
  {
    id: "tune",
    n: "N11",
    title: "Tune",
    cited: "Unsloth LoRA / QLoRA",
    blurb:
      "LoRA / QLoRA job specs from mosaic docs, JSONL export, and bound adapters that actually change Serve system + few-shot. Not a Hub-certified trainer.",
    engine: "Adapter packs bound into Serve",
    honesty: "LIVE",
  },
  {
    id: "schema",
    n: "N12",
    title: "Schema",
    cited: "Outlines / Instructor constrained generation",
    blurb: "JSON Schema templates with generate-and-repair until the object validates. Cover and Graph consume the result.",
    engine: "Grok json_schema + repair loop",
    honesty: "LIVE",
  },
];

export const CELL_MAP: Record<CellId, CellMeta> = Object.fromEntries(
  CELLS.map((c) => [c.id, c]),
) as Record<CellId, CellMeta>;

export function isCellId(v: string): v is CellId {
  return (CELL_IDS as readonly string[]).includes(v);
}

export const OPERATING_CELLS = CELLS.filter((c) => c.id !== "lyte");
