import { buildChunks } from "./engines/chunk";
import { CELL_IDS, type CellId } from "./cells";
import type {
  CoverClaim,
  CoverPolicy,
  GraphDef,
  LatticeBind,
  LatticeRule,
  MemoryThread,
  MosaicDoc,
  QuantStrategy,
  SchemaTemplate,
  TuneAdapter,
} from "./types";

function doc(partial: Omit<MosaicDoc, "chunks">): MosaicDoc {
  return { ...partial, chunks: buildChunks(partial.id, partial.text) };
}

export const SEED_DOCS: MosaicDoc[] = [
  doc({
    id: "doc_claims",
    title: "P&C Claims Desk Manual",
    source: "cover-core",
    weight: 1.2,
    quality: 0.92,
    tags: ["p&c", "fnol", "reserves"],
    text: `First notice of loss (FNOL) is opened the hour the insured reports. Capture loss date, location, narrative, and third parties before coverage is confirmed. Auto collision covers at-fault and not-at-fault impacts with another vehicle or object. Comprehensive covers theft, hail, flood to the vehicle, and vandalism. Home water covers sudden pipe burst, not long-term seepage. Fire is covered unless the fire is arson by the insured. Theft requires signs of forcible entry on homeowners. Wind is covered subject to hurricane deductible in coastal counties. Commercial inland marine covers cargo in transit. Business interruption requires a covered property peril first. Reserves should equal expected unpaid loss plus adjustment expense, never above policy limit. A $12,000 bumper and radiator repair on auto is a typical collision reserve. Deny when the peril is not on the form or the policy is lapsed. Notes belong on the claim file, not in email.`,
  }),
  doc({
    id: "doc_serve",
    title: "Serving Profile Notes",
    source: "serve-core",
    weight: 1,
    quality: 0.88,
    tags: ["inference", "vllm", "sglang"],
    text: `vLLM profile: continuous batching, paged attention, default temperature 0.7, top_p 0.95, suited to mixed chat throughput. SGLang profile: radix-attention prefix cache and constrained decoding, temperature 0.6, prefers JSON and tool-shaped answers. Ollama profile: local-first, higher temperature 0.8, shorter system, conversational. TensorRT-LLM profile: low latency, conservative temperature 0.4, tight max tokens, good for extraction. All four profiles in this console terminate on Grok 4.5; they are serving postures, not separate GPU runtimes. Keep max_tokens modest. Never loop the model. User initiates every completion.`,
  }),
  doc({
    id: "doc_lattice",
    title: "SENTRA / YAWAR Bind Spec",
    source: "lattice-core",
    weight: 1.1,
    quality: 0.9,
    tags: ["sentra", "yawar", "bind"],
    text: `SENTRA is the detection overlay. It watches Guard verdicts, Cover reserve spikes, Serve prompt injections, and Quant leverage-like drawdowns. YAWAR is the response overlay. Actions: isolate a cell so its mutating engines refuse work; throttle Serve max tokens; redact through Guard; human so Cover cannot close without a note; observe so Observe logs a warn span. Binds are directed: Guard to Lattice is SENTRA, Lattice to Serve is YAWAR, Mosaic to Retrieve is data, Graph to Cover is control. The immune lattice is the set of enabled binds. Isolating Serve also stalls Graph nodes of type serve.`,
  }),
  doc({
    id: "doc_lean",
    title: "LEAN Strategy Notes",
    source: "quant-core",
    weight: 0.9,
    quality: 0.86,
    tags: ["quant", "sma", "momentum"],
    text: `SMA crossover: buy when fast SMA exceeds slow SMA, flatten when it crosses back. Default 10 / 30 on SPY. Mean reversion: fade z-score beyond 1.2 on a 20-day window, flatten on the opposite extreme. Momentum: hold when 60-day return is positive. Buy and hold is the baseline. Fill at daily close, no shorting, start cash 100000. Sharpe uses daily returns times sqrt 252. Max drawdown is peak to trough on mark-to-market equity. This console uses deterministic synthetic bars seeded per symbol, not a live broker.`,
  }),
  doc({
    id: "doc_memory",
    title: "Retrieval and Memory Protocol",
    source: "retrieve-core",
    weight: 1,
    quality: 0.84,
    tags: ["rag", "letta", "bm25"],
    text: `Chunk about 90 words with 18-word overlap. Retrieve with BM25 over mosaic chunks, boosted by document quality and mix weight. Optional Grok rerank reorders the top hits. Memory threads are Letta-style notes the operator pins: short facts Graph and Serve may read. Never put secrets in memory. A good memory is one sentence, dated, sourced. When chatting with documents, cite titles not chunk ids.`,
  }),
];

export const SEED_POLICIES: CoverPolicy[] = [
  {
    id: "pol_auto",
    number: "POL-AUTO-4412",
    insured: "Jane Ortiz",
    line: "auto",
    premium: 1840,
    limit: 250_000,
    deductible: 500,
    status: "in-force",
    effective: "2026-01-12",
    expiry: "2027-01-12",
    perils: ["collision", "comprehensive", "liability"],
  },
  {
    id: "pol_home",
    number: "POL-HOME-1088",
    insured: "Marcus Chen",
    line: "home",
    premium: 2260,
    limit: 800_000,
    deductible: 2500,
    status: "in-force",
    effective: "2025-09-01",
    expiry: "2026-09-01",
    perils: ["water", "fire", "theft", "wind"],
  },
  {
    id: "pol_cml",
    number: "POL-CML-2201",
    insured: "Harbor Logistics LLC",
    line: "commercial",
    premium: 18400,
    limit: 2_000_000,
    deductible: 10000,
    status: "in-force",
    effective: "2026-03-01",
    expiry: "2027-03-01",
    perils: ["liability", "property", "inland marine", "business interruption"],
  },
];

export const SEED_CLAIMS: CoverClaim[] = [
  {
    id: "clm_1",
    number: "CLM-9001",
    policyId: "pol_auto",
    status: "open",
    cause: "collision",
    narrative:
      "Insured rear-ended at a light on 12th Ave. Other vehicle stopped. Dash cam available. Body shop estimate $12,400 for bumper, condenser, and alignment.",
    lossDate: "2026-08-18",
    reserve: 12400,
    paid: 0,
    notes: [{ ts: Date.parse("2026-08-18T15:04:00Z"), text: "FNOL taken. Photos requested." }],
  },
  {
    id: "clm_2",
    number: "CLM-9002",
    policyId: "pol_home",
    status: "fnol",
    cause: "water",
    narrative:
      "Upstairs supply line failed overnight. Ceiling in kitchen down. Hardwood cupped. Insured turned water off at 06:10. Temporary dry-out started.",
    lossDate: "2026-08-27",
    reserve: 0,
    paid: 0,
    notes: [{ ts: Date.parse("2026-08-27T11:20:00Z"), text: "Waiting coverage confirmation." }],
  },
];

export const SEED_STRATEGIES: QuantStrategy[] = [
  { id: "st_sma", name: "SPY SMA 10/30", kind: "sma", symbol: "SPY", params: { fast: 10, slow: 30 } },
  { id: "st_mr", name: "AAPL mean reversion", kind: "meanrev", symbol: "AAPL", params: { lookback: 20, z: 1.2 } },
  { id: "st_mom", name: "NVDA 60d momentum", kind: "momentum", symbol: "NVDA", params: { mom: 60 } },
  { id: "st_bh", name: "MSFT buy & hold", kind: "buyhold", symbol: "MSFT", params: {} },
];

export const SEED_GRAPHS: GraphDef[] = [
  {
    id: "g_research",
    name: "Research brief",
    blurb: "Retrieve mosaic context, draft on Serve, then Guard the answer.",
    nodes: [
      { id: "n0", type: "input", label: "Question", x: 8, y: 42, config: {} },
      { id: "n1", type: "retrieve", label: "Retrieve", x: 28, y: 42, config: { k: "4" } },
      { id: "n2", type: "serve", label: "Draft", x: 50, y: 42, config: { engine: "sglang" } },
      { id: "n3", type: "guard", label: "Guard", x: 72, y: 42, config: {} },
      { id: "n4", type: "end", label: "Brief", x: 90, y: 42, config: {} },
    ],
    edges: [
      { from: "n0", to: "n1", when: "always" },
      { from: "n1", to: "n2", when: "always" },
      { from: "n2", to: "n3", when: "always" },
      { from: "n3", to: "n4", when: "always" },
    ],
  },
  {
    id: "g_fnol",
    name: "Claims intake",
    blurb: "Guard the FNOL narrative, extract with Schema, open Cover if clean.",
    nodes: [
      { id: "n0", type: "input", label: "Narrative", x: 8, y: 38, config: {} },
      { id: "n1", type: "guard", label: "Guard", x: 28, y: 38, config: {} },
      { id: "n2", type: "condition", label: "Blocked?", x: 48, y: 38, config: { source: "guard" } },
      { id: "n3", type: "schema", label: "Extract", x: 68, y: 18, config: { template: "sch_claim" } },
      { id: "n4", type: "cover", label: "Open claim", x: 86, y: 18, config: {} },
      { id: "n5", type: "end", label: "Stop", x: 68, y: 62, config: {} },
    ],
    edges: [
      { from: "n0", to: "n1", when: "always" },
      { from: "n1", to: "n2", when: "always" },
      { from: "n2", to: "n5", when: "true" },
      { from: "n2", to: "n3", when: "false" },
      { from: "n3", to: "n4", when: "always" },
    ],
  },
  {
    id: "g_trade",
    name: "Trade desk brief",
    blurb: "Run the last Quant posture through Serve for an operator note.",
    nodes: [
      { id: "n0", type: "input", label: "Ask", x: 10, y: 44, config: {} },
      { id: "n1", type: "quant", label: "Quant snapshot", x: 36, y: 44, config: {} },
      { id: "n2", type: "serve", label: "Desk note", x: 62, y: 44, config: { engine: "trtllm" } },
      { id: "n3", type: "end", label: "Note", x: 86, y: 44, config: {} },
    ],
    edges: [
      { from: "n0", to: "n1", when: "always" },
      { from: "n1", to: "n2", when: "always" },
      { from: "n2", to: "n3", when: "always" },
    ],
  },
];

export const SEED_BINDS: LatticeBind[] = [
  { id: "b1", from: "guard", to: "lattice", overlay: "sentra", enabled: true },
  { id: "b2", from: "lattice", to: "serve", overlay: "yawar", enabled: true },
  { id: "b3", from: "mosaic", to: "retrieve", overlay: "data", enabled: true },
  { id: "b4", from: "retrieve", to: "graph", overlay: "data", enabled: true },
  { id: "b5", from: "graph", to: "cover", overlay: "control", enabled: true },
  { id: "b6", from: "quant", to: "observe", overlay: "data", enabled: true },
  { id: "b7", from: "tune", to: "serve", overlay: "control", enabled: true },
  { id: "b8", from: "schema", to: "cover", overlay: "control", enabled: true },
  { id: "b9", from: "serve", to: "observe", overlay: "data", enabled: true },
  { id: "b10", from: "lattice", to: "cover", overlay: "yawar", enabled: true },
  { id: "b11", from: "lyte", to: "lattice", overlay: "control", enabled: true },
];

export const SEED_RULES: LatticeRule[] = [
  {
    id: "r1",
    overlay: "yawar",
    name: "Isolate Serve on jailbreak",
    trigger: "guard.block",
    action: "isolate",
    target: "serve",
    enabled: true,
  },
  {
    id: "r2",
    overlay: "yawar",
    name: "Redact PII into Serve",
    trigger: "guard.redact",
    action: "redact",
    target: "serve",
    enabled: true,
  },
  {
    id: "r3",
    overlay: "sentra",
    name: "Watch large reserves",
    trigger: "cover.reserve>",
    action: "human",
    target: "cover",
    enabled: true,
  },
  {
    id: "r4",
    overlay: "sentra",
    name: "Observe deep drawdown",
    trigger: "quant.drawdown",
    action: "observe",
    target: "quant",
    enabled: true,
  },
  {
    id: "r5",
    overlay: "yawar",
    name: "Throttle Serve on injection",
    trigger: "guard.injection",
    action: "throttle",
    target: "serve",
    enabled: true,
  },
];

export const SEED_SCHEMAS: SchemaTemplate[] = [
  {
    id: "sch_claim",
    name: "Claim extract",
    description: "FNOL fields for Cover",
    schema: {
      type: "object",
      additionalProperties: false,
      required: ["insuredHint", "cause", "lossDate", "severity", "reserveHint", "summary"],
      properties: {
        insuredHint: { type: "string" },
        cause: { type: "string", enum: ["collision", "comprehensive", "water", "fire", "theft", "wind", "liability", "inland marine", "business interruption", "unknown"] },
        lossDate: { type: "string" },
        severity: { type: "string", enum: ["low", "medium", "high"] },
        reserveHint: { type: "number" },
        summary: { type: "string" },
      },
    },
  },
  {
    id: "sch_order",
    name: "Desk order",
    description: "Structured order ticket from a note",
    schema: {
      type: "object",
      additionalProperties: false,
      required: ["symbol", "side", "intent", "rationale"],
      properties: {
        symbol: { type: "string", enum: ["SPY", "AAPL", "MSFT", "NVDA"] },
        side: { type: "string", enum: ["buy", "sell", "hold"] },
        intent: { type: "string" },
        rationale: { type: "string" },
      },
    },
  },
  {
    id: "sch_guard",
    name: "Guard report",
    description: "Judge-style safety report",
    schema: {
      type: "object",
      additionalProperties: false,
      required: ["action", "categories", "rationale"],
      properties: {
        action: { type: "string", enum: ["allow", "redact", "block"] },
        categories: { type: "array", items: { type: "string" } },
        rationale: { type: "string" },
      },
    },
  },
];

export const SEED_MEMORY: MemoryThread[] = [
  {
    id: "mem_ops",
    title: "Operator facts",
    notes: [
      {
        id: "mn1",
        ts: Date.parse("2026-08-28T14:00:00Z"),
        text: "Harbor Logistics is the commercial account. Cargo claims route to inland marine.",
      },
      {
        id: "mn2",
        ts: Date.parse("2026-08-29T09:10:00Z"),
        text: "Serve TensorRT-LLM profile is preferred for extraction. SGLang for JSON.",
      },
    ],
  },
];

export const SEED_ADAPTER: TuneAdapter = {
  id: "ad_desk",
  name: "Claims desk LoRA pack",
  mosaicDocIds: ["doc_claims", "doc_lattice"],
  rank: 16,
  alpha: 32,
  modules: ["q_proj", "k_proj", "v_proj", "o_proj"],
  systemAddendum:
    "You are the LYTE claims and lattice desk. Prefer FNOL language, named perils, and bind overlay terms. Be terse.",
  fewshot: [
    {
      user: "Pipe burst, kitchen ceiling down. What peril?",
      assistant: "Home water — sudden pipe burst is covered; long-term seepage is not. Open FNOL, set a dry-out reserve, confirm the policy is in force.",
    },
  ],
  bound: true,
  jsonlPreview: "",
};

export const ALL_CELL_HEALTH: CellId[] = [...CELL_IDS];
