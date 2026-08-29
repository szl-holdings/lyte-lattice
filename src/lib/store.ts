import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { CellId } from "./cells";
import { DEFAULT_GUARD_POLICY } from "./engines/guard";
import { buildChunks } from "./engines/chunk";
import { evaluateLattice, type LatticeEvent } from "./engines/lattice";
import {
  SEED_ADAPTER,
  SEED_BINDS,
  SEED_CLAIMS,
  SEED_DOCS,
  SEED_GRAPHS,
  SEED_MEMORY,
  SEED_POLICIES,
  SEED_RULES,
  SEED_SCHEMAS,
  SEED_STRATEGIES,
} from "./seed";
import type {
  ChatMessage,
  CoverClaim,
  CoverPolicy,
  EngineId,
  EvalRun,
  GraphDef,
  GraphRun,
  GuardPolicy,
  GuardVerdict,
  LatticeBind,
  LatticeRule,
  MemoryThread,
  MosaicDoc,
  QuantRun,
  QuantStrategy,
  RagTurn,
  SchemaTemplate,
  ServeState,
  TraceSpan,
  TuneAdapter,
} from "./types";
import { uid } from "./utils";

export const ENGINE_PROFILES: Record<
  EngineId,
  {
    name: string;
    cited: string;
    temperature: number;
    maxTokens: number;
    topP: number;
    system: string;
    jsonBias: boolean;
    stop?: string[];
  }
> = {
  vllm: {
    name: "vLLM",
    cited: "Paged attention · continuous batching",
    temperature: 0.7,
    maxTokens: 520,
    topP: 0.95,
    jsonBias: false,
    system:
      "You are LYTE Serve on the vLLM profile: high-throughput mixed chat. Precise. Cite cell names when relevant.",
  },
  sglang: {
    name: "SGLang",
    cited: "Radix attention · constrained decoding",
    temperature: 0.4,
    maxTokens: 480,
    topP: 0.9,
    jsonBias: true,
    system:
      "You are LYTE Serve on the SGLang profile. Prefer structured, tool-shaped answers. JSON when asked. No fluff.",
  },
  ollama: {
    name: "Ollama",
    cited: "Local-first conversational",
    temperature: 0.8,
    maxTokens: 420,
    topP: 1,
    jsonBias: false,
    system: "You are LYTE Serve on the Ollama profile: conversational, local-first tone. Short paragraphs.",
  },
  trtllm: {
    name: "TensorRT-LLM",
    cited: "Low-latency extraction",
    temperature: 0.2,
    maxTokens: 280,
    topP: 0.8,
    jsonBias: false,
    stop: ["\n\n\n"],
    system: "You are LYTE Serve on the TensorRT-LLM profile: terse, extractive, low latency. No preamble.",
  },
};

type LyteState = {
  hydrated: boolean;
  traces: TraceSpan[];
  isolated: CellId[];
  throttled: CellId[];
  humanLock: CellId[];
  serve: ServeState;
  graphs: GraphDef[];
  graphRuns: GraphRun[];
  guardPolicy: GuardPolicy;
  guardLog: GuardVerdict[];
  mosaic: MosaicDoc[];
  binds: LatticeBind[];
  rules: LatticeRule[];
  latticeLog: { ts: number; text: string; action: string }[];
  policies: CoverPolicy[];
  claims: CoverClaim[];
  strategies: QuantStrategy[];
  quantRuns: QuantRun[];
  memory: MemoryThread[];
  ragTurns: RagTurn[];
  adapters: TuneAdapter[];
  schemas: SchemaTemplate[];
  evals: EvalRun[];

  setHydrated: () => void;
  addTrace: (span: Omit<TraceSpan, "id" | "ts"> & { ts?: number; id?: string }) => TraceSpan;
  emitLattice: (event: LatticeEvent) => void;
  isIsolated: (id: CellId) => boolean;
  toggleIsolate: (id: CellId) => void;
  clearHolds: () => void;
  releaseThrottle: (id: CellId) => void;
  releaseHuman: (id: CellId) => void;
  setEngine: (engine: EngineId) => void;
  setServeTemp: (n: number | null) => void;
  pushServe: (msg: ChatMessage) => void;
  patchServe: (id: string, patch: Partial<ChatMessage>) => void;
  clearServe: () => void;
  addGraphRun: (run: GraphRun) => void;
  setGuardPolicy: (p: Partial<GuardPolicy>) => void;
  addGuard: (v: GuardVerdict) => void;
  upsertDoc: (doc: Omit<MosaicDoc, "chunks">) => void;
  removeDoc: (id: string) => void;
  setDocWeight: (id: string, weight: number) => void;
  setDocQuality: (id: string, quality: number) => void;
  toggleBind: (id: string) => void;
  toggleRule: (id: string) => void;
  addRule: (rule: LatticeRule) => void;
  addClaim: (claim: CoverClaim) => void;
  patchClaim: (id: string, patch: Partial<CoverClaim>) => void;
  postPayment: (id: string, amount: number, note?: string) => void;
  addQuantRun: (run: QuantRun) => void;
  updateStrategy: (id: string, patch: Partial<QuantStrategy>) => void;
  addMemory: (threadId: string, text: string) => void;
  addMemoryThread: (title: string) => void;
  addRag: (turn: RagTurn) => void;
  addAdapter: (a: TuneAdapter) => void;
  bindAdapter: (id: string, bound: boolean) => void;
  setSchemaOutput: (id: string, lastOutput: unknown, lastRaw: string, lastAttempts?: number) => void;
  addSchemaTemplate: (t: SchemaTemplate) => void;
  addEval: (run: EvalRun) => void;
  boundAdapter: () => TuneAdapter | undefined;
};

const initial: Pick<
  LyteState,
  | "hydrated"
  | "traces"
  | "isolated"
  | "throttled"
  | "humanLock"
  | "serve"
  | "graphs"
  | "graphRuns"
  | "guardPolicy"
  | "guardLog"
  | "mosaic"
  | "binds"
  | "rules"
  | "latticeLog"
  | "policies"
  | "claims"
  | "strategies"
  | "quantRuns"
  | "memory"
  | "ragTurns"
  | "adapters"
  | "schemas"
  | "evals"
> = {
  hydrated: false,
  traces: [],
  isolated: [],
  throttled: [],
  humanLock: [],
  serve: { engine: "vllm", messages: [], temperatureOverride: null },
  graphs: SEED_GRAPHS,
  graphRuns: [],
  guardPolicy: DEFAULT_GUARD_POLICY,
  guardLog: [],
  mosaic: SEED_DOCS,
  binds: SEED_BINDS,
  rules: SEED_RULES,
  latticeLog: [],
  policies: SEED_POLICIES,
  claims: SEED_CLAIMS,
  strategies: SEED_STRATEGIES,
  quantRuns: [],
  memory: SEED_MEMORY,
  ragTurns: [],
  adapters: [{ ...SEED_ADAPTER, jsonlPreview: buildJsonl(SEED_ADAPTER, SEED_DOCS) }],
  schemas: SEED_SCHEMAS,
  evals: [],
};

function buildJsonl(adapter: TuneAdapter, docs: MosaicDoc[]): string {
  const chosen = docs.filter((d) => adapter.mosaicDocIds.includes(d.id));
  const rows = chosen.flatMap((d) =>
    d.chunks.slice(0, 4).map((c) =>
      JSON.stringify({
        instruction: `Use the ${d.title} desk manual.`,
        input: c.text.slice(0, 280),
        output: c.text.slice(0, 280),
      }),
    ),
  );
  for (const fs of adapter.fewshot) {
    rows.push(JSON.stringify({ instruction: adapter.systemAddendum, input: fs.user, output: fs.assistant }));
  }
  return rows.join("\n");
}

export function adapterJsonl(adapter: TuneAdapter, docs: MosaicDoc[]) {
  return buildJsonl(adapter, docs);
}

export const useLyte = create<LyteState>()(
  persist(
    (set, get) => ({
      ...initial,
      setHydrated: () => set({ hydrated: true }),
      addTrace: (span) => {
        const full: TraceSpan = {
          id: span.id ?? uid("tr"),
          ts: span.ts ?? Date.now(),
          cell: span.cell,
          kind: span.kind,
          name: span.name,
          status: span.status,
          durationMs: span.durationMs,
          input: span.input,
          output: span.output,
          meta: span.meta,
        };
        set((s) => ({ traces: [full, ...s.traces].slice(0, 360) }));
        return full;
      },
      emitLattice: (event) => {
        const decisions = evaluateLattice(get().rules, event);
        if (!decisions.length) {
          set((s) => ({
            latticeLog: [
              { ts: Date.now(), text: `SENTRA saw ${event.trigger} from ${event.cell}`, action: "observe" },
              ...s.latticeLog,
            ].slice(0, 80),
          }));
          return;
        }
        set((s) => {
          let isolated = [...s.isolated];
          let throttled = [...s.throttled];
          let humanLock = [...s.humanLock];
          const log = [...s.latticeLog];
          for (const d of decisions) {
            if (d.action === "isolate" && !isolated.includes(d.target)) isolated.push(d.target);
            if (d.action === "throttle" && !throttled.includes(d.target)) throttled.push(d.target);
            if (d.action === "human" && !humanLock.includes(d.target)) humanLock.push(d.target);
            log.unshift({ ts: Date.now(), text: d.reason, action: d.action });
          }
          return { isolated, throttled, humanLock, latticeLog: log.slice(0, 80) };
        });
        for (const d of decisions) {
          get().addTrace({
            cell: "lattice",
            kind: d.action,
            name: d.ruleName,
            status: d.action === "isolate" ? "blocked" : "warn",
            durationMs: 1,
            output: d.reason,
            meta: { target: d.target, trigger: event.trigger },
          });
        }
      },
      isIsolated: (id) => get().isolated.includes(id),
      toggleIsolate: (id) =>
        set((s) => ({
          isolated: s.isolated.includes(id) ? s.isolated.filter((x) => x !== id) : [...s.isolated, id],
        })),
      clearHolds: () => set({ isolated: [], throttled: [], humanLock: [] }),
      releaseThrottle: (id) => set((s) => ({ throttled: s.throttled.filter((x) => x !== id) })),
      releaseHuman: (id) => set((s) => ({ humanLock: s.humanLock.filter((x) => x !== id) })),
      setEngine: (engine) => set((s) => ({ serve: { ...s.serve, engine } })),
      setServeTemp: (n) => set((s) => ({ serve: { ...s.serve, temperatureOverride: n } })),
      pushServe: (msg) =>
        set((s) => ({ serve: { ...s.serve, messages: [...s.serve.messages, msg].slice(-40) } })),
      patchServe: (id, patch) =>
        set((s) => ({
          serve: {
            ...s.serve,
            messages: s.serve.messages.map((m) => (m.id === id ? { ...m, ...patch } : m)),
          },
        })),
      clearServe: () => set((s) => ({ serve: { ...s.serve, messages: [] } })),
      addGraphRun: (run) => set((s) => ({ graphRuns: [run, ...s.graphRuns].slice(0, 40) })),
      setGuardPolicy: (p) => set((s) => ({ guardPolicy: { ...s.guardPolicy, ...p } })),
      addGuard: (v) => set((s) => ({ guardLog: [v, ...s.guardLog].slice(0, 80) })),
      upsertDoc: (doc) =>
        set((s) => {
          const next: MosaicDoc = { ...doc, chunks: buildChunks(doc.id, doc.text) };
          const i = s.mosaic.findIndex((d) => d.id === doc.id);
          if (i < 0) return { mosaic: [next, ...s.mosaic] };
          const mosaic = s.mosaic.slice();
          mosaic[i] = next;
          return { mosaic };
        }),
      removeDoc: (id) => set((s) => ({ mosaic: s.mosaic.filter((d) => d.id !== id) })),
      setDocWeight: (id, weight) =>
        set((s) => ({ mosaic: s.mosaic.map((d) => (d.id === id ? { ...d, weight } : d)) })),
      setDocQuality: (id, quality) =>
        set((s) => ({ mosaic: s.mosaic.map((d) => (d.id === id ? { ...d, quality } : d)) })),
      toggleBind: (id) =>
        set((s) => ({ binds: s.binds.map((b) => (b.id === id ? { ...b, enabled: !b.enabled } : b)) })),
      toggleRule: (id) =>
        set((s) => ({ rules: s.rules.map((r) => (r.id === id ? { ...r, enabled: !r.enabled } : r)) })),
      addRule: (rule) => set((s) => ({ rules: [rule, ...s.rules] })),
      addClaim: (claim) => set((s) => ({ claims: [claim, ...s.claims] })),
      patchClaim: (id, patch) =>
        set((s) => ({ claims: s.claims.map((c) => (c.id === id ? { ...c, ...patch } : c)) })),
      postPayment: (id, amount, note) =>
        set((s) => ({
          claims: s.claims.map((c) => {
            if (c.id !== id) return c;
            const paid = Math.max(0, c.paid + amount);
            const reserve = Math.max(0, c.reserve - amount);
            return {
              ...c,
              paid,
              reserve,
              status: reserve === 0 && paid > 0 ? "closed" : c.status === "fnol" ? "open" : c.status,
              notes: [
                { ts: Date.now(), text: note?.trim() || `Payment ${amount} posted. Paid ${paid}, reserve ${reserve}.` },
                ...c.notes,
              ],
            };
          }),
        })),
      addQuantRun: (run) => set((s) => ({ quantRuns: [run, ...s.quantRuns].slice(0, 24) })),
      updateStrategy: (id, patch) =>
        set((s) => ({
          strategies: s.strategies.map((st) =>
            st.id === id ? { ...st, ...patch, params: { ...st.params, ...(patch.params ?? {}) } } : st,
          ),
        })),
      addMemory: (threadId, text) =>
        set((s) => ({
          memory: s.memory.map((t) =>
            t.id === threadId
              ? { ...t, notes: [{ id: uid("mn"), text, ts: Date.now() }, ...t.notes] }
              : t,
          ),
        })),
      addMemoryThread: (title) =>
        set((s) => ({
          memory: [{ id: uid("mem"), title, notes: [] }, ...s.memory],
        })),
      addRag: (turn) => set((s) => ({ ragTurns: [turn, ...s.ragTurns].slice(0, 30) })),
      addAdapter: (a) => set((s) => ({ adapters: [a, ...s.adapters] })),
      bindAdapter: (id, bound) =>
        set((s) => ({
          adapters: s.adapters.map((a) => ({ ...a, bound: a.id === id ? bound : bound ? false : a.bound })),
        })),
      setSchemaOutput: (id, lastOutput, lastRaw, lastAttempts) =>
        set((s) => ({
          schemas: s.schemas.map((t) =>
            t.id === id ? { ...t, lastOutput, lastRaw, lastAttempts: lastAttempts ?? t.lastAttempts } : t,
          ),
        })),
      addSchemaTemplate: (t) => set((s) => ({ schemas: [t, ...s.schemas] })),
      addEval: (run) => set((s) => ({ evals: [run, ...s.evals].slice(0, 20) })),
      boundAdapter: () => get().adapters.find((a) => a.bound),
    }),
    {
      name: "lyte-lattice-v3",
      storage: createJSONStorage(() => localStorage),
      skipHydration: true,
      partialize: (s) => ({
        traces: s.traces.slice(0, 80),
        isolated: s.isolated,
        throttled: s.throttled,
        humanLock: s.humanLock,
        serve: s.serve,
        graphs: s.graphs,
        graphRuns: s.graphRuns.slice(0, 12),
        guardPolicy: s.guardPolicy,
        guardLog: s.guardLog.slice(0, 24),
        mosaic: s.mosaic,
        binds: s.binds,
        rules: s.rules,
        latticeLog: s.latticeLog.slice(0, 24),
        policies: s.policies,
        claims: s.claims,
        strategies: s.strategies,
        quantRuns: s.quantRuns.slice(0, 8),
        memory: s.memory,
        ragTurns: s.ragTurns.slice(0, 12),
        adapters: s.adapters,
        schemas: s.schemas,
        evals: s.evals.slice(0, 8),
      }),
    },
  ),
);
