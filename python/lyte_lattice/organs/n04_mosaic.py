"""N4 Mosaic — cite MosaicML / Databricks. Take the job. Do not rehost.

Not MosaicML training. Not Databricks. Own-data mix with weighted chunk draws.
"""
from __future__ import annotations

import hashlib
import random
from typing import Any, Mapping

from lyte_lattice.organ import num, seal, text

SEED = 20260829
DEFAULT_K = 3
CHUNK_SIZE = 90
CHUNK_OVERLAP = 18

# Baked LYTE seed docs. Cite the leader; do not rehost training code.
CORPUS: list[dict[str, Any]] = [
    {
        "id": "doc_claims",
        "title": "P&C Claims Desk Manual",
        "source": "cover-core",
        "weight": 1.2,
        "quality": 0.92,
        "tags": ["p&c", "fnol", "reserves"],
        "text": (
            "First notice of loss (FNOL) is opened the hour the insured reports. Capture loss date, "
            "location, narrative, and third parties before coverage is confirmed. Auto collision covers "
            "at-fault and not-at-fault impacts with another vehicle or object. Comprehensive covers theft, "
            "hail, flood to the vehicle, and vandalism. Home water covers sudden pipe burst, not long-term "
            "seepage. Fire is covered unless the fire is arson by the insured. Theft requires signs of "
            "forcible entry on homeowners. Wind is covered subject to hurricane deductible in coastal "
            "counties. Commercial inland marine covers cargo in transit. Business interruption requires a "
            "covered property peril first. Reserves should equal expected unpaid loss plus adjustment "
            "expense, never above policy limit. A $12,000 bumper and radiator repair on auto is a typical "
            "collision reserve. Deny when the peril is not on the form or the policy is lapsed. Notes "
            "belong on the claim file, not in email."
        ),
    },
    {
        "id": "doc_serve",
        "title": "Serving Profile Notes",
        "source": "serve-core",
        "weight": 1.0,
        "quality": 0.88,
        "tags": ["inference", "vllm", "sglang"],
        "text": (
            "vLLM profile: continuous batching, paged attention, default temperature 0.7, top_p 0.95, "
            "suited to mixed chat throughput. SGLang profile: radix-attention prefix cache and constrained "
            "decoding, temperature 0.6, prefers JSON and tool-shaped answers. Ollama profile: local-first, "
            "higher temperature 0.8, shorter system, conversational. TensorRT-LLM profile: low latency, "
            "conservative temperature 0.4, tight max tokens, good for extraction. All four profiles in this "
            "console terminate on Grok 4.5; they are serving postures, not separate GPU runtimes. Keep "
            "max_tokens modest. Never loop the model. User initiates every completion."
        ),
    },
    {
        "id": "doc_lattice",
        "title": "SENTRA / YAWAR Bind Spec",
        "source": "lattice-core",
        "weight": 1.1,
        "quality": 0.9,
        "tags": ["sentra", "yawar", "bind"],
        "text": (
            "SENTRA is the detection overlay. It watches Guard verdicts, Cover reserve spikes, Serve prompt "
            "injections, and Quant leverage-like drawdowns. YAWAR is the response overlay. Actions: isolate "
            "a cell so its mutating engines refuse work; throttle Serve max tokens; redact through Guard; "
            "human so Cover cannot close without a note; observe so Observe logs a warn span. Binds are "
            "directed: Guard to Lattice is SENTRA, Lattice to Serve is YAWAR, Mosaic to Retrieve is data, "
            "Graph to Cover is control. The immune lattice is the set of enabled binds. Isolating Serve "
            "also stalls Graph nodes of type serve."
        ),
    },
    {
        "id": "doc_lean",
        "title": "LEAN Strategy Notes",
        "source": "quant-core",
        "weight": 0.9,
        "quality": 0.86,
        "tags": ["quant", "sma", "momentum"],
        "text": (
            "SMA crossover: buy when fast SMA exceeds slow SMA, flatten when it crosses back. Default 10 / 30 "
            "on SPY. Mean reversion: fade z-score beyond 1.2 on a 20-day window, flatten on the opposite "
            "extreme. Momentum: hold when 60-day return is positive. Buy and hold is the baseline. Fill at "
            "daily close, no shorting, start cash 100000. Sharpe uses daily returns times sqrt 252. Max "
            "drawdown is peak to trough on mark-to-market equity. This console uses deterministic synthetic "
            "bars seeded per symbol, not a live broker."
        ),
    },
    {
        "id": "doc_memory",
        "title": "Retrieval and Memory Protocol",
        "source": "retrieve-core",
        "weight": 1.0,
        "quality": 0.84,
        "tags": ["rag", "letta", "bm25"],
        "text": (
            "Chunk about 90 words with 18-word overlap. Retrieve with BM25 over mosaic chunks, boosted by "
            "document quality and mix weight. Optional Grok rerank reorders the top hits. Memory threads "
            "are Letta-style notes the operator pins: short facts Graph and Serve may read. Never put "
            "secrets in memory. A good memory is one sentence, dated, sourced. When chatting with "
            "documents, cite titles not chunk ids."
        ),
    },
]

# Recipe multipliers applied to base weights.
RECIPES: dict[str, dict[str, float]] = {
    "balanced": {
        "doc_claims": 1.0,
        "doc_serve": 1.0,
        "doc_lattice": 1.0,
        "doc_lean": 1.0,
        "doc_memory": 1.0,
    },
    "claims-heavy": {
        "doc_claims": 2.4,
        "doc_serve": 0.55,
        "doc_lattice": 0.55,
        "doc_lean": 0.5,
        "doc_memory": 0.5,
    },
    "serve-heavy": {
        "doc_claims": 0.55,
        "doc_serve": 2.4,
        "doc_lattice": 0.55,
        "doc_lean": 0.5,
        "doc_memory": 0.5,
    },
    "lattice-heavy": {
        "doc_claims": 0.55,
        "doc_serve": 0.55,
        "doc_lattice": 2.4,
        "doc_lean": 0.5,
        "doc_memory": 0.5,
    },
}


def _chunk_text(text_in: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    words = [w for w in text_in.replace("\n", " ").split(" ") if w]
    if not words:
        return []
    chunks: list[str] = []
    i = 0
    step = max(1, size - overlap)
    while i < len(words):
        chunks.append(" ".join(words[i : i + size]))
        if i + size >= len(words):
            break
        i += step
    return chunks


def _docs_with_chunks() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for doc in CORPUS:
        chunks = [
            {"id": f"{doc['id']}_c{i}", "text": ch} for i, ch in enumerate(_chunk_text(str(doc["text"])))
        ]
        row = dict(doc)
        row["chunks"] = chunks
        out.append(row)
    return out


def _draw(pool: list[dict[str, Any]], k: int, rng: random.Random) -> list[dict[str, Any]]:
    remaining = [dict(p) for p in pool if float(p.get("score") or 0) > 0]
    picked: list[dict[str, Any]] = []
    n = max(0, min(k, len(remaining)))
    for _ in range(n):
        total = sum(float(p["score"]) for p in remaining)
        if total <= 0:
            break
        r = rng.random() * total
        acc = 0.0
        idx = len(remaining) - 1
        for i, item in enumerate(remaining):
            acc += float(item["score"])
            if r <= acc:
                idx = i
                break
        chosen = remaining.pop(idx)
        picked.append(
            {
                "docId": chosen["docId"],
                "title": chosen["title"],
                "text": chosen["text"],
                "score": round(float(chosen["score"]), 6),
                "_id": chosen["id"],
            }
        )
    return picked


def act(payload: Mapping[str, Any]) -> dict[str, Any]:
    raw_recipe = text(payload, "recipe", default="balanced").lower()
    status = "ok"
    recipe = raw_recipe
    if recipe not in RECIPES:
        recipe = "balanced"
        status = "warn"

    k_raw = num(payload, "k", float(DEFAULT_K))
    k = int(k_raw)
    if k < 0:
        k = 0
        status = "warn"

    mix = RECIPES[recipe]
    baked = _docs_with_chunks()
    docs_out: list[dict[str, Any]] = []
    pool: list[dict[str, Any]] = []
    for doc in baked:
        weight = float(doc["weight"]) * float(mix.get(doc["id"], 1.0))
        quality = float(doc["quality"])
        docs_out.append(
            {
                "id": doc["id"],
                "title": doc["title"],
                "weight": round(weight, 6),
                "quality": quality,
                "chunk_count": len(doc["chunks"]),
            }
        )
        score = max(0.0, weight) * quality
        for ch in doc["chunks"]:
            pool.append(
                {
                    "id": ch["id"],
                    "docId": doc["id"],
                    "title": doc["title"],
                    "text": ch["text"],
                    "score": score,
                }
            )

    rng = random.Random(SEED)
    drawn_raw = _draw(pool, k, rng)
    mix_hash = hashlib.sha256("|".join(d["_id"] for d in drawn_raw).encode("utf-8")).hexdigest()
    draw = [{k: v for k, v in row.items() if k != "_id"} for row in drawn_raw]

    output: dict[str, Any] = {
        "recipe": recipe,
        "docs": docs_out,
        "draw": draw,
        "mix_hash": mix_hash,
    }
    if raw_recipe not in RECIPES:
        output["note"] = f"unknown recipe {raw_recipe!r}; fell back to balanced"
    return seal(cell="N4", status=status, payload=payload, output=output)
