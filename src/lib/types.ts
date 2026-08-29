import type { CellId } from "./cells";

export type TraceStatus = "ok" | "warn" | "error" | "blocked";

export type TraceSpan = {
  id: string;
  ts: number;
  cell: CellId;
  kind: string;
  name: string;
  status: TraceStatus;
  durationMs: number;
  input?: string;
  output?: string;
  meta?: Record<string, unknown>;
};

export type EngineId = "vllm" | "sglang" | "ollama" | "trtllm";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  engine: EngineId;
  ts: number;
  usage?: { prompt: number; completion: number };
  metrics?: { ttftMs: number; tokPerSec: number };
};

export type GraphNodeType =
  | "input"
  | "serve"
  | "retrieve"
  | "guard"
  | "schema"
  | "condition"
  | "cover"
  | "quant"
  | "end";

export type GraphNode = {
  id: string;
  type: GraphNodeType;
  label: string;
  x: number;
  y: number;
  config: Record<string, string>;
};

export type GraphEdge = {
  from: string;
  to: string;
  when: "always" | "true" | "false";
};

export type GraphDef = {
  id: string;
  name: string;
  blurb: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
};

export type GraphStep = {
  nodeId: string;
  label: string;
  output: string;
  status: TraceStatus;
  durationMs: number;
};

export type GraphRun = {
  id: string;
  graphId: string;
  ts: number;
  status: TraceStatus;
  input: string;
  steps: GraphStep[];
  result: string;
};

export type GuardCategoryId =
  | "pii"
  | "secrets"
  | "jailbreak"
  | "harm"
  | "injection";

export type GuardHit = {
  id: GuardCategoryId;
  label: string;
  hit: boolean;
  score: number;
  evidence: string;
  llama?: string;
};

export type GuardAction = "allow" | "redact" | "block";

export type GuardVerdict = {
  id: string;
  ts: number;
  text: string;
  direction: "prompt" | "response";
  action: GuardAction;
  categories: GuardHit[];
  redacted: string;
  reason: string;
};

export type GuardPolicy = {
  pii: GuardAction;
  secrets: GuardAction;
  jailbreak: GuardAction;
  harm: GuardAction;
  injection: GuardAction;
};

export type MosaicDoc = {
  id: string;
  title: string;
  source: string;
  text: string;
  weight: number;
  quality: number;
  tags: string[];
  chunks: MosaicChunk[];
};

export type MosaicChunk = {
  id: string;
  docId: string;
  text: string;
  tokens: number;
};

export type RetrieveHit = {
  chunkId: string;
  docId: string;
  title: string;
  text: string;
  score: number;
  rerank?: number;
};

export type MemoryNote = {
  id: string;
  text: string;
  ts: number;
};

export type MemoryThread = {
  id: string;
  title: string;
  notes: MemoryNote[];
};

export type OverlayKind = "sentra" | "yawar" | "data" | "control";

export type LatticeBind = {
  id: string;
  from: CellId;
  to: CellId;
  overlay: OverlayKind;
  enabled: boolean;
};

export type YawarAction = "isolate" | "throttle" | "redact" | "human" | "observe";

export type LatticeRule = {
  id: string;
  overlay: "sentra" | "yawar";
  name: string;
  trigger: string;
  action: YawarAction;
  target: CellId;
  enabled: boolean;
};

export type CoverLine = "auto" | "home" | "commercial";

export type CoverPolicy = {
  id: string;
  number: string;
  insured: string;
  line: CoverLine;
  premium: number;
  limit: number;
  deductible: number;
  status: "in-force" | "lapsed";
  effective: string;
  expiry: string;
  perils: string[];
};

export type ClaimStatus = "fnol" | "open" | "reserved" | "closed" | "denied";

export type CoverClaim = {
  id: string;
  number: string;
  policyId: string;
  status: ClaimStatus;
  cause: string;
  narrative: string;
  lossDate: string;
  reserve: number;
  paid: number;
  extracted?: Record<string, string>;
  notes: { ts: number; text: string }[];
};

export type Bar = {
  d: string;
  o: number;
  h: number;
  l: number;
  c: number;
  v: number;
};

export type QuantKind = "sma" | "meanrev" | "momentum" | "buyhold";

export type QuantStrategy = {
  id: string;
  name: string;
  kind: QuantKind;
  symbol: string;
  params: Record<string, number>;
};

export type QuantTrade = {
  d: string;
  side: "buy" | "sell";
  px: number;
  qty: number;
};

export type QuantRun = {
  id: string;
  strategyId: string;
  ts: number;
  equity: { d: string; v: number }[];
  trades: QuantTrade[];
  stats: {
    ret: number;
    sharpe: number;
    maxdd: number;
    win: number;
    trades: number;
    cagr: number;
  };
};

export type TuneAdapter = {
  id: string;
  name: string;
  mosaicDocIds: string[];
  rank: number;
  alpha: number;
  modules: string[];
  systemAddendum: string;
  fewshot: { user: string; assistant: string }[];
  bound: boolean;
  jsonlPreview: string;
  qlora?: boolean;
};

export type SchemaTemplate = {
  id: string;
  name: string;
  description: string;
  schema: Record<string, unknown>;
  lastOutput?: unknown;
  lastRaw?: string;
  lastAttempts?: number;
};

export type EvalCase = {
  input: string;
  output: string;
  scores: Record<string, number>;
};

export type EvalRun = {
  id: string;
  ts: number;
  name: string;
  cases: EvalCase[];
};

export type ServeState = {
  engine: EngineId;
  messages: ChatMessage[];
  temperatureOverride: number | null;
};

export type RagTurn = {
  id: string;
  q: string;
  a: string;
  hits: RetrieveHit[];
  ts: number;
};
