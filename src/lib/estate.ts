export const ESTATE = {
  org: "szl-holdings",
  product: "https://a-11-oy.com",
  productBind: "https://a-11-oy.com/lyte",
  proof: "https://a11oy.net",
  source: "https://github.com/szl-holdings/lyte-lattice",
  flagship: "https://github.com/szl-holdings/a11oy",
  factory: "https://github.com/szl-holdings/a11oy-factory",
  lyteWindow: "https://github.com/szl-holdings/lyte-services",
  hub: "https://huggingface.co/SZLHOLDINGS",
  hubSpace: "https://huggingface.co/spaces/SZLHOLDINGS/lyte-lattice",
  bind: "BIND_AS_A11OY_PACKAGE",
  lambda: "Conjecture 1",
  doctrine: "v11 LOCKED",
  order: "AO-2026-08-29-001",
  slsa: "L1 honest \u00b7 L2 attested \u00b7 L3 roadmap",
} as const;

export const FRONTIERS: Array<{
  n: string;
  title: string;
  cited: string;
  honesty: "STRUCTURAL-ONLY" | "LIVE" | "ROADMAP" | "UNAVAILABLE" | "REPORTED";
  inConsole: boolean;
  note?: string;
}> = [
  { n: "lyte", title: "Lyte", cited: "owner-admitted design-partner cell", honesty: "STRUCTURAL-ONLY", inConsole: true },
  { n: "N1", title: "Serve", cited: "vLLM / SGLang / Ollama / TensorRT-LLM", honesty: "LIVE", inConsole: true },
  { n: "N2", title: "Graph", cited: "LangGraph", honesty: "LIVE", inConsole: true },
  { n: "N3", title: "Guard", cited: "Llama Guard", honesty: "LIVE", inConsole: true },
  { n: "N4", title: "Mosaic", cited: "MosaicML / Databricks", honesty: "LIVE", inConsole: true },
  { n: "N5", title: "Lattice", cited: "SENTRA / YAWAR", honesty: "LIVE", inConsole: true },
  { n: "N6", title: "Cover", cited: "Guidewire P&C", honesty: "LIVE", inConsole: true },
  { n: "N7", title: "Quant", cited: "QuantConnect LEAN", honesty: "LIVE", inConsole: true },
  {
    n: "N8",
    title: "Title",
    cited: "Zillow / public records",
    honesty: "LIVE",
    inConsole: true,
    note: "PLUTO Kings/Queens MEASURED. Occupancy UNAVAILABLE. Not MLS.",
  },
  { n: "N9", title: "Retrieve", cited: "LlamaIndex / Haystack / Letta", honesty: "LIVE", inConsole: true },
  { n: "N10", title: "Observe", cited: "Phoenix / LangSmith / Langfuse / DeepEval", honesty: "LIVE", inConsole: true },
  { n: "N11", title: "Tune", cited: "Unsloth LoRA / QLoRA", honesty: "LIVE", inConsole: true },
  { n: "N12", title: "Schema", cited: "Outlines / Instructor", honesty: "LIVE", inConsole: true },
  {
    n: "N13",
    title: "Energy",
    cited: "RAPL / NVML joule channel",
    honesty: "LIVE",
    inConsole: true,
    note: "Probe LIVE. Joule UNAVAILABLE unless RAPL energy_uj is read. Watts are not joules.",
  },
  { n: "N14", title: "Tool", cited: "Anthropic MCP", honesty: "LIVE", inConsole: true },
  { n: "N15", title: "Memory", cited: "Mem0 / Zep Graphiti", honesty: "LIVE", inConsole: true },
  { n: "N16", title: "Eval", cited: "RAGAS / HELM / LMSYS Arena", honesty: "LIVE", inConsole: true },
  { n: "N17", title: "Mesh", cited: "NVIDIA Dynamo / Ray Serve / llm-d", honesty: "LIVE", inConsole: true },
  { n: "N18", title: "Route", cited: "LiteLLM / OpenRouter / RouteLLM", honesty: "LIVE", inConsole: true },
  { n: "N19", title: "Cache", cited: "LMCache / Mooncake / GPTCache", honesty: "LIVE", inConsole: true },
  { n: "N20", title: "Voice", cited: "LiveKit / Cartesia / Deepgram", honesty: "LIVE", inConsole: true },
  { n: "N21", title: "Sandbox", cited: "Daytona / E2B", honesty: "LIVE", inConsole: true },
  { n: "N22", title: "Identity", cited: "SPIFFE / SPIRE / Astrix NHI", honesty: "LIVE", inConsole: true },
  { n: "N23", title: "Rails", cited: "NVIDIA NeMo Guardrails", honesty: "LIVE", inConsole: true },
  { n: "N24", title: "Browser", cited: "Playwright / Stagehand / Browserbase", honesty: "LIVE", inConsole: true },
  { n: "N25", title: "Policy", cited: "AWS Cedar / Open Policy Agent", honesty: "LIVE", inConsole: true },
  {
    n: "N26",
    title: "Inference",
    cited: "szl-command-lab NVML/RAPL wrap",
    honesty: "REPORTED",
    inConsole: false,
    note: "Wrap joule REPORTED from command-lab. Never MEASURED here. Never a fabricated joule.",
  },
  {
    n: "N27",
    title: "Train",
    cited: "szl-forge Unsloth QLoRA; szl-gpu-bridge",
    honesty: "UNAVAILABLE",
    inConsole: false,
    note: "GPU train UNAVAILABLE. CUDA absent. gpu-bridge NEVER_DISPATCH. Not Unsloth.",
  },
];
