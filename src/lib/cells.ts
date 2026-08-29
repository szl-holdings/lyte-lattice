export const CELL_IDS = [
  "lyte",
  "serve",
  "graph",
  "guard",
  "mosaic",
  "lattice",
  "cover",
  "quant",
  "title",
  "retrieve",
  "observe",
  "tune",
  "schema",
  "energy",
  "tool",
  "memory",
  "eval",
  "mesh",
  "route",
  "cache",
  "voice",
  "sandbox",
  "identity",
  "rails",
  "browser",
  "policy",
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
      "Streaming inference with four engine profiles. Completions run on Grok 4.5; the Python organ receipts the decode posture. Not a local GPU cluster.",
    engine: "Grok 4.5 streaming + Python organ",
    honesty: "LIVE",
  },
  {
    id: "graph",
    n: "N2",
    title: "Graph",
    cited: "LangGraph agent orchestration",
    blurb: "Stateful graphs with Serve, Retrieve, Guard, Schema, Cover, and Quant nodes. Live steps, not storyboards.",
    engine: "In-browser graph interpreter + Python organ",
    honesty: "LIVE",
  },
  {
    id: "guard",
    n: "N3",
    title: "Guard",
    cited: "Llama Guard prompt/response safeguard",
    blurb: "Local classifiers mapped to Llama Guard S-codes, plus an optional Grok deep scan. Verdicts feed Lattice.",
    engine: "Local classifiers + Python organ",
    honesty: "LIVE",
  },
  {
    id: "mosaic",
    n: "N4",
    title: "Mosaic",
    cited: "MosaicML / Databricks own-data mosaic",
    blurb: "Own-data corpus with weights, quality, mix recipes, and streaming draws. Mixes feed Retrieve, Tune, and Graph.",
    engine: "Weighted mix + Python organ",
    honesty: "LIVE",
  },
  {
    id: "lattice",
    n: "N5",
    title: "Lattice",
    cited: "Immune-lattice SENTRA / YAWAR overlay bind",
    blurb: "SENTRA detects. YAWAR responds. Fire rules, isolate, throttle, redact, or escalate cells from live events.",
    engine: "Policy overlay + Python organ",
    honesty: "LIVE",
  },
  {
    id: "cover",
    n: "N6",
    title: "Cover",
    cited: "Guidewire P&C core",
    blurb: "Policies, FNOL, peril matrix, coverage check, reserves, payments, and notes. AI extraction lands structured claim fields via Schema.",
    engine: "P&C core + Python organ",
    honesty: "LIVE",
  },
  {
    id: "quant",
    n: "N7",
    title: "Quant",
    cited: "QuantConnect LEAN",
    blurb: "LEAN-style backtests on deterministic daily bars. Editable SMA, mean reversion, momentum, buy-and-hold. Not a live broker.",
    engine: "Event-driven backtester + Python organ",
    honesty: "LIVE",
  },
  {
    id: "title",
    n: "N8",
    title: "Title",
    cited: "Zillow / public records",
    blurb:
      "Public-records underwriting silhouette. PLUTO-style Kings/Queens sample is MEASURED. Occupancy is UNAVAILABLE. Not an MLS feed.",
    engine: "Python public-records organ",
    honesty: "LIVE",
  },
  {
    id: "retrieve",
    n: "N9",
    title: "Retrieve",
    cited: "LlamaIndex / Haystack / Letta",
    blurb: "BM25 over the mosaic, optional Grok rerank, and Letta-style memory threads the rest of the lattice can read.",
    engine: "BM25 + memory + Python organ",
    honesty: "LIVE",
  },
  {
    id: "observe",
    n: "N10",
    title: "Observe",
    cited: "Phoenix / LangSmith / Langfuse / DeepEval",
    blurb: "Every cell emits spans. Inspect traces, latency by cell, and run a local eval harness on recent outputs.",
    engine: "In-console tracer + Python organ",
    honesty: "LIVE",
  },
  {
    id: "tune",
    n: "N11",
    title: "Tune",
    cited: "Unsloth LoRA / QLoRA",
    blurb:
      "LoRA / QLoRA job specs from mosaic docs, JSONL export, and bound adapters that actually change Serve system + few-shot. Not a Hub-certified trainer.",
    engine: "Adapter packs + Python organ",
    honesty: "LIVE",
  },
  {
    id: "schema",
    n: "N12",
    title: "Schema",
    cited: "Outlines / Instructor constrained generation",
    blurb: "JSON Schema templates with generate-and-repair until the object validates. Cover and Graph consume the result.",
    engine: "Grok json_schema + Python organ",
    honesty: "LIVE",
  },
  {
    id: "energy",
    n: "N13",
    title: "Energy",
    cited: "RAPL / NVML joule channel",
    blurb:
      "The probe is LIVE. Joule is UNAVAILABLE unless RAPL energy_uj is actually read. Watts from NVML are never converted into joules.",
    engine: "Python RAPL/NVML probe",
    honesty: "LIVE",
  },
  {
    id: "tool",
    n: "N14",
    title: "Tool",
    cited: "Anthropic MCP",
    blurb: "MCP-shaped tools/list and tools/call against a local registry. Not a live MCP server to Anthropic.",
    engine: "Python MCP organ",
    honesty: "LIVE",
  },
  {
    id: "memory",
    n: "N15",
    title: "Memory",
    cited: "Mem0 / Zep Graphiti",
    blurb: "Remember, recall, and a tiny entity graph of operator facts. Not hosted Mem0 or Zep Cloud.",
    engine: "Python memory graph organ",
    honesty: "LIVE",
  },
  {
    id: "eval",
    n: "N16",
    title: "Eval",
    cited: "RAGAS / HELM / LMSYS Arena",
    blurb: "Local faithfulness, toxicity, structure, and latency scores. Not LMSYS Arena and not a HELM leaderboard.",
    engine: "Python eval organ",
    honesty: "LIVE",
  },
  {
    id: "mesh",
    n: "N17",
    title: "Mesh",
    cited: "NVIDIA Dynamo / Ray Serve / llm-d",
    blurb: "Replica placement and queue-depth hologram for serve profiles. Not a GPU mesh.",
    engine: "Python mesh planner",
    honesty: "LIVE",
  },
  {
    id: "route",
    n: "N18",
    title: "Route",
    cited: "LiteLLM / OpenRouter / RouteLLM",
    blurb: "Route a prompt onto a Serve profile by length, JSON need, and latency posture. Not OpenRouter billing.",
    engine: "Python router organ",
    honesty: "LIVE",
  },
  {
    id: "cache",
    n: "N19",
    title: "Cache",
    cited: "LMCache / Mooncake / GPTCache",
    blurb: "In-process prefix cache with hashed keys, get/put/stats. Not a distributed KV.",
    engine: "Python prefix cache",
    honesty: "LIVE",
  },
  {
    id: "voice",
    n: "N20",
    title: "Voice",
    cited: "LiveKit / Cartesia / Deepgram",
    blurb: "STT/TTS duration and phoneme plan. Not a LiveKit room and no audio bytes.",
    engine: "Python voice plan organ",
    honesty: "LIVE",
  },
  {
    id: "sandbox",
    n: "N21",
    title: "Sandbox",
    cited: "Daytona / E2B",
    blurb: "Restricted arithmetic expression exec with an AST whitelist. Not a cloud VM. No shell, no network.",
    engine: "Python AST sandbox",
    honesty: "LIVE",
  },
  {
    id: "identity",
    n: "N22",
    title: "Identity",
    cited: "SPIFFE / SPIRE / Astrix NHI",
    blurb: "Unsigned SPIFFE-shaped IDs for lattice workloads. Never signed. proven_trust stays false.",
    engine: "Python SPIFFE organ",
    honesty: "LIVE",
  },
  {
    id: "rails",
    n: "N23",
    title: "Rails",
    cited: "NVIDIA NeMo Guardrails",
    blurb: "Colang-style input, dialog, and output rails. Distinct from N3 Llama Guard S-codes.",
    engine: "Python rails organ",
    honesty: "LIVE",
  },
  {
    id: "browser",
    n: "N24",
    title: "Browser",
    cited: "Playwright / Stagehand / Browserbase",
    blurb: "Receipted Playwright plan: goto, wait, snapshot. Chromium is not launched from the Python organ.",
    engine: "Python browser plan organ",
    honesty: "LIVE",
  },
  {
    id: "policy",
    n: "N25",
    title: "Policy",
    cited: "AWS Cedar / Open Policy Agent",
    blurb: "Cedar-shaped allow/deny with reasons over lattice principals and resources. Not production Cedar or cluster OPA.",
    engine: "Python Cedar/OPA organ",
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

export const INNER_RING: CellId[] = [
  "serve",
  "graph",
  "guard",
  "mosaic",
  "lattice",
  "cover",
  "quant",
  "title",
  "retrieve",
  "observe",
  "tune",
  "schema",
];

export const OUTER_RING: CellId[] = [
  "energy",
  "tool",
  "memory",
  "eval",
  "mesh",
  "route",
  "cache",
  "voice",
  "sandbox",
  "identity",
  "rails",
  "browser",
  "policy",
];

export const RICH_CELLS: CellId[] = [
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
];
