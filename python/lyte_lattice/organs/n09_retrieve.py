"""N9 Retrieve — cited LlamaIndex / Haystack / Letta. Not those products."""
from __future__ import annotations

import math
import re
from typing import Any, Mapping

from lyte_lattice.organ import num, seal, text

# Same five-doc mosaic spirit as N4. Chunk ~90 words. Not MosaicML.
DOCS: list[dict[str, Any]] = [
    {
        "id": "doc_claims",
        "title": "P&C Claims Desk Manual",
        "weight": 1.2,
        "quality": 0.92,
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
        "weight": 1.0,
        "quality": 0.88,
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
        "weight": 1.1,
        "quality": 0.9,
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
        "weight": 0.9,
        "quality": 0.86,
        "text": (
            "SMA crossover: buy when fast SMA exceeds slow SMA, flatten when it crosses back. Default "
            "10 / 30 on SPY. Mean reversion: fade z-score beyond 1.2 on a 20-day window, flatten on the "
            "opposite extreme. Momentum: hold when 60-day return is positive. Buy and hold is the baseline. "
            "Fill at daily close, no shorting, start cash 100000. Sharpe uses daily returns times sqrt 252. "
            "Max drawdown is peak to trough on mark-to-market equity. This console uses deterministic "
            "synthetic bars seeded per symbol, not a live broker."
        ),
    },
    {
        "id": "doc_memory",
        "title": "Retrieval and Memory Protocol",
        "weight": 1.0,
        "quality": 0.84,
        "text": (
            "Chunk about 90 words with 18-word overlap. Retrieve with BM25 over mosaic chunks, boosted by "
            "document quality and mix weight. Optional Grok rerank reorders the top hits. Memory threads "
            "are Letta-style notes the operator pins: short facts Graph and Serve may read. Never put "
            "secrets in memory. A good memory is one sentence, dated, sourced. When chatting with "
            "documents, cite titles not chunk ids."
        ),
    },
]

MEMORY_THREAD = {
    "title": "Operator facts",
    "notes": [
        "Harbor Logistics is the commercial account. Cargo claims route to inland marine.",
        "Serve TensorRT-LLM profile is preferred for extraction. SGLang for JSON.",
    ],
}

_TOKEN = re.compile(r"\w+", re.UNICODE)
_K1 = 1.5
_B = 0.75
_NOTE = "Cited LlamaIndex / Haystack / Letta. Not those products. BM25 over a baked mosaic."


def _tokenize(s: str) -> list[str]:
    return [t.casefold() for t in _TOKEN.findall(s)]


def _chunk(text_body: str, size: int = 90, overlap: int = 18) -> list[str]:
    words = text_body.split()
    if not words:
        return []
    chunks: list[str] = []
    i = 0
    while i < len(words):
        chunks.append(" ".join(words[i : i + size]))
        if i + size >= len(words):
            break
        i += max(1, size - overlap)
    return chunks


def _mosaic() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for doc in DOCS:
        for i, chunk in enumerate(_chunk(doc["text"])):
            rows.append(
                {
                    "docId": doc["id"],
                    "title": doc["title"],
                    "text": chunk,
                    "quality": float(doc["quality"]),
                    "weight": float(doc["weight"]),
                    "chunkId": f"{doc['id']}_c{i}",
                    "tokens": _tokenize(chunk),
                }
            )
    return rows


_CHUNKS = _mosaic()


def _bm25(query: str, k: int) -> list[dict[str, Any]]:
    q_tokens = _tokenize(query)
    if not q_tokens or not _CHUNKS:
        return []
    n_docs = len(_CHUNKS)
    df: dict[str, int] = {}
    for ch in _CHUNKS:
        for tok in set(ch["tokens"]):
            df[tok] = df.get(tok, 0) + 1
    avgdl = sum(len(ch["tokens"]) for ch in _CHUNKS) / n_docs
    scored: list[dict[str, Any]] = []
    for ch in _CHUNKS:
        tf_map: dict[str, int] = {}
        for tok in ch["tokens"]:
            tf_map[tok] = tf_map.get(tok, 0) + 1
        dl = len(ch["tokens"]) or 1
        score = 0.0
        for qt in q_tokens:
            f = tf_map.get(qt, 0)
            if not f:
                continue
            n = df.get(qt, 0)
            idf = math.log((n_docs - n + 0.5) / (n + 0.5) + 1.0)
            tf = (f * (_K1 + 1.0)) / (f + _K1 * (1.0 - _B + _B * (dl / avgdl)))
            score += idf * tf
        score *= ch["quality"] * ch["weight"]
        if score > 0:
            scored.append(
                {
                    "title": ch["title"],
                    "text": ch["text"],
                    "score": round(score, 6),
                    "docId": ch["docId"],
                }
            )
    scored.sort(key=lambda h: h["score"], reverse=True)
    return scored[:k]


def _memory_hits(query: str) -> list[str]:
    q = set(_tokenize(query))
    if not q:
        return []
    hits: list[str] = []
    for note in MEMORY_THREAD["notes"]:
        toks = set(_tokenize(note))
        if q & toks:
            hits.append(note)
    return hits


def act(payload: Mapping[str, Any]) -> dict[str, Any]:
    query = text(payload, "query", "q", "text", default="FNOL reserve pipe burst")
    k_raw = num(payload, "k", 4.0)
    k = int(k_raw) if k_raw == k_raw else 4
    k = max(1, min(12, k))
    hits = _bm25(query, k)
    mem = _memory_hits(query)
    output = {
        "query": query,
        "hits": hits,
        "memory": {"title": MEMORY_THREAD["title"], "notes": mem},
        "k": k,
        "note": _NOTE,
    }
    return seal(cell="N9", status="ok", payload=payload, output=output)
