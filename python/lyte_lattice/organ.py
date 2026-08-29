"""Organ protocol — fail closed, UNSIGNED-honest, never fabricate joules or signatures.

Cite the leader. Take the job. Do not rehost the code.
Λ = Conjecture 1. proven_trust is always false in this hologram.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from typing import Any, Mapping

LAMBDA = "Conjecture 1"
SLSA = "L1 honest · L2 attested · L3 roadmap"
BIND = "BIND_AS_A11OY_PACKAGE"
PRODUCT = "https://a-11-oy.com"
PROOF = "https://a11oy.net"
DOCTRINE = "v11 LOCKED"
ORDER = "AO-2026-08-29-001"

Honesty = str  # LIVE | STRUCTURAL-ONLY | UNAVAILABLE | MEASURED | REPORTED | ROADMAP
Status = str  # ok | warn | error | blocked

CELLS: dict[str, dict[str, str]] = {
    "N1": {
        "id": "serve",
        "title": "Serve",
        "cited": "vLLM / SGLang / Ollama / TensorRT-LLM",
        "job": "Streaming inference postures. Profiles change decode, system, JSON bias, latency.",
        "not": "Not a local GPU cluster. Not vLLM/SGLang/Ollama/TensorRT-LLM runtimes.",
        "honesty": "LIVE",
        "module": "lyte_lattice.organs.n01_serve",
    },
    "N2": {
        "id": "graph",
        "title": "Graph",
        "cited": "LangGraph agent orchestration",
        "job": "Stateful graphs with Serve, Retrieve, Guard, Schema, Cover, Quant nodes.",
        "not": "Not LangGraph. Not a hosted agent runtime.",
        "honesty": "LIVE",
        "module": "lyte_lattice.organs.n02_graph",
    },
    "N3": {
        "id": "guard",
        "title": "Guard",
        "cited": "Llama Guard prompt/response safeguard",
        "job": "Local classifiers mapped to Llama Guard S-codes. Verdicts feed Lattice.",
        "not": "Not Meta Llama Guard weights. Not a certified safety model.",
        "honesty": "LIVE",
        "module": "lyte_lattice.organs.n03_guard",
    },
    "N4": {
        "id": "mosaic",
        "title": "Mosaic",
        "cited": "MosaicML / Databricks own-data mosaic",
        "job": "Own-data corpus with weights, quality, mix recipes, and streaming draws.",
        "not": "Not MosaicML training. Not Databricks.",
        "honesty": "LIVE",
        "module": "lyte_lattice.organs.n04_mosaic",
    },
    "N5": {
        "id": "lattice",
        "title": "Lattice",
        "cited": "Immune-lattice SENTRA / YAWAR overlay bind",
        "job": "SENTRA detects. YAWAR responds. Isolate, throttle, redact, human, observe.",
        "not": "Not a second Immune flagship. Not Hub-certified.",
        "honesty": "LIVE",
        "module": "lyte_lattice.organs.n05_lattice",
    },
    "N6": {
        "id": "cover",
        "title": "Cover",
        "cited": "Guidewire P&C core",
        "job": "Policies, FNOL, peril matrix, coverage check, reserves, payments.",
        "not": "Not Guidewire InsuranceSuite. Not a live carrier core.",
        "honesty": "LIVE",
        "module": "lyte_lattice.organs.n06_cover",
    },
    "N7": {
        "id": "quant",
        "title": "Quant",
        "cited": "QuantConnect LEAN",
        "job": "LEAN-style backtests on deterministic daily bars. SMA, mean rev, momentum, buy-hold.",
        "not": "Not a live broker. Not QuantConnect Cloud.",
        "honesty": "LIVE",
        "module": "lyte_lattice.organs.n07_quant",
    },
    "N8": {
        "id": "title",
        "title": "Title",
        "cited": "Zillow / public records",
        "job": "Public-records underwriting silhouette. PLUTO Kings/Queens MEASURED. Occupancy UNAVAILABLE.",
        "not": "Not MLS. Not Zillow API. Not a title plant. Occupancy is never fabricated.",
        "honesty": "LIVE",
        "module": "lyte_lattice.organs.n08_title",
    },
    "N9": {
        "id": "retrieve",
        "title": "Retrieve",
        "cited": "LlamaIndex / Haystack / Letta",
        "job": "BM25 over the mosaic plus Letta-style memory threads.",
        "not": "Not LlamaIndex. Not Haystack. Not hosted Letta.",
        "honesty": "LIVE",
        "module": "lyte_lattice.organs.n09_retrieve",
    },
    "N10": {
        "id": "observe",
        "title": "Observe",
        "cited": "Phoenix / LangSmith / Langfuse / DeepEval",
        "job": "Spans, latency by cell, local eval harness.",
        "not": "Not Arize Phoenix Cloud. Not LangSmith. Not Langfuse.",
        "honesty": "LIVE",
        "module": "lyte_lattice.organs.n10_observe",
    },
    "N11": {
        "id": "tune",
        "title": "Tune",
        "cited": "Unsloth LoRA / QLoRA",
        "job": "LoRA / QLoRA job specs, JSONL export, adapter packs that bind into Serve.",
        "not": "Not Unsloth. Not a Hub-certified trainer. No GPU fine-tune.",
        "honesty": "LIVE",
        "module": "lyte_lattice.organs.n11_tune",
    },
    "N12": {
        "id": "schema",
        "title": "Schema",
        "cited": "Outlines / Instructor constrained generation",
        "job": "JSON Schema templates with generate-and-repair until the object validates.",
        "not": "Not Outlines. Not Instructor. No model weights.",
        "honesty": "LIVE",
        "module": "lyte_lattice.organs.n12_schema",
    },
    "N13": {
        "id": "energy",
        "title": "Energy",
        "cited": "RAPL / NVML joule channel",
        "job": "Probe RAPL energy_uj and NVML power.draw. Joule only if RAPL actually reads.",
        "not": "Never convert watts into fabricated joules. Never invent RAPL.",
        "honesty": "LIVE",
        "module": "lyte_lattice.organs.n13_energy",
    },
    "N14": {
        "id": "tool",
        "title": "Tool",
        "cited": "Anthropic MCP",
        "job": "MCP-shaped tools/list and tools/call against a local registry.",
        "not": "Not a live MCP server to Anthropic. Not hosted tools.",
        "honesty": "LIVE",
        "module": "lyte_lattice.organs.n14_tool",
    },
    "N15": {
        "id": "memory",
        "title": "Memory",
        "cited": "Mem0 / Zep Graphiti",
        "job": "Remember, recall, and a tiny entity graph of operator facts.",
        "not": "Not hosted Mem0. Not Zep Cloud. Not Graphiti service.",
        "honesty": "LIVE",
        "module": "lyte_lattice.organs.n15_memory",
    },
    "N16": {
        "id": "eval",
        "title": "Eval",
        "cited": "RAGAS / HELM / LMSYS Arena",
        "job": "Local faithfulness, toxicity, structure, latency scores on cases.",
        "not": "Not RAGAS Cloud. Not HELM leaderboard. Not LMSYS Arena.",
        "honesty": "LIVE",
        "module": "lyte_lattice.organs.n16_eval",
    },
    "N17": {
        "id": "mesh",
        "title": "Mesh",
        "cited": "NVIDIA Dynamo / Ray Serve / llm-d",
        "job": "Replica placement, queue depth, engine mesh plan.",
        "not": "Not NVIDIA Dynamo. Not Ray cluster. Not llm-d. No GPUs.",
        "honesty": "LIVE",
        "module": "lyte_lattice.organs.n17_mesh",
    },
    "N18": {
        "id": "route",
        "title": "Route",
        "cited": "LiteLLM / OpenRouter / RouteLLM",
        "job": "Route a prompt to a serve profile by length, JSON, and latency posture.",
        "not": "Not LiteLLM proxy. Not OpenRouter billing. Not RouteLLM.",
        "honesty": "LIVE",
        "module": "lyte_lattice.organs.n18_route",
    },
    "N19": {
        "id": "cache",
        "title": "Cache",
        "cited": "LMCache / Mooncake / GPTCache",
        "job": "In-process prefix cache: put, get, stats, hash keys.",
        "not": "Not LMCache distributed KV. Not Mooncake. Not GPTCache service.",
        "honesty": "LIVE",
        "module": "lyte_lattice.organs.n19_cache",
    },
    "N20": {
        "id": "voice",
        "title": "Voice",
        "cited": "LiveKit / Cartesia / Deepgram",
        "job": "STT/TTS plan: duration, viseme/phoneme silhouette, room posture.",
        "not": "Not a LiveKit room. Not Cartesia. Not Deepgram. No audio bytes.",
        "honesty": "LIVE",
        "module": "lyte_lattice.organs.n20_voice",
    },
    "N21": {
        "id": "sandbox",
        "title": "Sandbox",
        "cited": "Daytona / E2B",
        "job": "Restricted arithmetic/expression exec with ast whitelist and timeout.",
        "not": "Not Daytona. Not E2B. Not a cloud VM. No shell, no import, no network.",
        "honesty": "LIVE",
        "module": "lyte_lattice.organs.n21_sandbox",
    },
    "N22": {
        "id": "identity",
        "title": "Identity",
        "cited": "SPIFFE / SPIRE / Astrix NHI",
        "job": "Issue unsigned SPIFFE-shaped IDs for lattice workloads. Never sign.",
        "not": "Not SPIRE. Not a trust bundle. proven_trust stays false. Not Astrix.",
        "honesty": "LIVE",
        "module": "lyte_lattice.organs.n22_identity",
    },
    "N23": {
        "id": "rails",
        "title": "Rails",
        "cited": "NVIDIA NeMo Guardrails",
        "job": "Colang-style input/dialog/output rails. Distinct from N3 Llama Guard S-codes.",
        "not": "Not NeMo Guardrails runtime. Not Llama Guard (that is N3).",
        "honesty": "LIVE",
        "module": "lyte_lattice.organs.n23_rails",
    },
    "N24": {
        "id": "browser",
        "title": "Browser",
        "cited": "Playwright / Stagehand / Browserbase",
        "job": "Receipted Playwright plan: goto, wait, snapshot. Does not launch Chromium here.",
        "not": "Not Browserbase. Not Stagehand cloud. Playwright lives in the Node console.",
        "honesty": "LIVE",
        "module": "lyte_lattice.organs.n24_browser",
    },
    "N25": {
        "id": "policy",
        "title": "Policy",
        "cited": "AWS Cedar / Open Policy Agent",
        "job": "Cedar-shaped allow/deny with reasons over lattice principals and resources.",
        "not": "Not AWS Cedar production. Not OPA/Gatekeeper cluster.",
        "honesty": "LIVE",
        "module": "lyte_lattice.organs.n25_policy",
    },
}

ID_TO_N = {meta["id"]: n for n, meta in CELLS.items()}
ALIASES = {**{n: n for n in CELLS}, **{n.lower(): n for n in CELLS}, **ID_TO_N, **{i.upper(): n for i, n in ID_TO_N.items()}}


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def unsigned_hash(*parts: Any) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(canonical(p).encode("utf-8"))
        h.update(b"\n")
    return "UNSIGNED-honest:" + h.hexdigest()


def text(payload: Mapping[str, Any], *keys: str, default: str = "") -> str:
    for k in keys:
        v = payload.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return default


def num(payload: Mapping[str, Any], key: str, default: float = 0.0) -> float:
    v = payload.get(key, default)
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def mapping(payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    v = payload.get(key)
    return dict(v) if isinstance(v, dict) else {}


def read_rapl() -> dict[str, Any]:
    path = "/sys/class/powercap/intel-rapl/intel-rapl:0/energy_uj"
    try:
        with open(path, encoding="utf-8") as f:
            uj = int(f.read().strip())
        if uj < 0:
            raise ValueError("negative")
        return {
            "path": path,
            "energy_uj": uj,
            "joule": uj / 1_000_000.0,
            "honesty": "MEASURED",
        }
    except Exception:
        return {"path": path, "energy_uj": None, "joule": None, "honesty": "UNAVAILABLE"}


def read_nvml() -> dict[str, Any]:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return {"present": False, "power_w": None, "honesty": "UNAVAILABLE", "note": "nvidia-smi not on PATH"}
    try:
        proc = subprocess.run(
            [exe, "--query-gpu=power.draw", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        raw = (proc.stdout or "").strip().splitlines()
        watts: list[float] = []
        for line in raw:
            try:
                watts.append(float(line.strip()))
            except ValueError:
                continue
        if not watts:
            return {"present": True, "power_w": None, "honesty": "UNAVAILABLE", "note": "nvidia-smi returned no parseable watts"}
        return {
            "present": True,
            "power_w": watts,
            "honesty": "MEASURED",
            "note": "Watts are not joules. Do not convert.",
        }
    except Exception as exc:
        return {"present": True, "power_w": None, "honesty": "UNAVAILABLE", "note": str(exc)}


def energy_channel() -> dict[str, Any]:
    rapl = read_rapl()
    nvml = read_nvml()
    joule = rapl.get("joule")
    honesty = "MEASURED" if isinstance(joule, (int, float)) and joule is not None else "UNAVAILABLE"
    return {
        "rapl": rapl,
        "nvml": nvml,
        "joule": joule if honesty == "MEASURED" else None,
        "honesty": honesty,
        "note": "Joule is UNAVAILABLE unless RAPL energy_uj is read. Watts are never converted into joules.",
    }


def normalize_cell(cell: str) -> str | None:
    if not cell:
        return None
    return ALIASES.get(str(cell).strip()) or ALIASES.get(str(cell).strip().upper()) or ALIASES.get(str(cell).strip().lower())


def seal(
    *,
    cell: str,
    status: str,
    payload: Mapping[str, Any],
    output: Any,
    honesty: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    n = normalize_cell(cell)
    if n is None:
        n = str(cell)
        meta = {"id": "unknown", "title": "Unknown", "cited": "", "job": "", "not": "", "honesty": "UNAVAILABLE"}
        status = "blocked"
    else:
        meta = CELLS[n]
    energy = energy_channel()
    body = {
        "cell": n,
        "id": meta["id"],
        "title": meta["title"],
        "cited": meta["cited"],
        "job": meta["job"],
        "not": meta["not"],
        "honesty": honesty or meta["honesty"],
        "status": status,
        "output": output,
        "energy_joule": energy["joule"],
        "energy_honesty": energy["honesty"],
        "lambda": LAMBDA,
        "bind": BIND,
        "doctrine": DOCTRINE,
        "order": ORDER,
        "product": PRODUCT,
        "proof": PROOF,
        "slsa": SLSA,
        "host": os.uname().nodename if hasattr(os, "uname") else "unknown",
    }
    if extra:
        body.update(dict(extra))
    body["receipt"] = {
        "hash": unsigned_hash({"cell": n, "payload": dict(payload), "output": output}),
        "signed": False,
        "lambda": LAMBDA,
        "proven_trust": False,
        "slsa": "L1 honest",
        "kind": "UNSIGNED-honest",
    }
    # Fail closed: organs cannot self-attest.
    body["receipt"]["signed"] = False
    body["receipt"]["proven_trust"] = False
    if n != "N13" or body["energy_joule"] is None:
        # Non-N13 never reports joules. N13 only reports what RAPL actually read.
        if n != "N13":
            body["energy_joule"] = None
            body["energy_honesty"] = "UNAVAILABLE"
    return body


def blocked(cell: str, reason: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    p = dict(payload or {})
    return seal(cell=cell, status="blocked", payload=p, output={"error": reason})
