"""N8 Title — cited Zillow / public records. Not MLS. Occupancy is never fabricated."""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Mapping

from lyte_lattice.organ import seal, text

# PLUTO-style sample. MEASURED fields only. Occupancy stays UNAVAILABLE.
# Kings borough code 3, Queens borough code 4. Not a live NYC open-data feed.
LOTS: list[dict[str, Any]] = [
    {
        "bbl": "3000470001",
        "borough": "Kings",
        "address": "120 SCHERMERHORN STREET",
        "zonedist1": "C6-2.5",
        "bldgclass": "O4",
        "landuse": "05",
        "ownername": "CITY OF NEW YORK",
        "numfloors": 8,
        "yearbuilt": 1958,
        "assessland": 4_275_000,
        "lotarea": 20_150,
        "occupancy": None,
        "occupancy_honesty": "UNAVAILABLE",
    },
    {
        "bbl": "4000860001",
        "borough": "Queens",
        "address": "1 COURT SQUARE",
        "zonedist1": "C5-3",
        "bldgclass": "O4",
        "landuse": "05",
        "ownername": "ONE COURT SQUARE OWNER LLC",
        "numfloors": 50,
        "yearbuilt": 1990,
        "assessland": 52_650_000,
        "lotarea": 81_225,
        "occupancy": None,
        "occupancy_honesty": "UNAVAILABLE",
    },
    {
        "bbl": "3064210025",
        "borough": "Kings",
        "address": "1847 EAST 28 STREET",
        "zonedist1": "R4",
        "bldgclass": "A1",
        "landuse": "01",
        "ownername": "1847 E 28 ST LLC",
        "numfloors": 2,
        "yearbuilt": 1931,
        "assessland": 24_480,
        "lotarea": 2_000,
        "occupancy": None,
        "occupancy_honesty": "UNAVAILABLE",
    },
    {
        "bbl": "3018760033",
        "borough": "Kings",
        "address": "185 BERGEN STREET",
        "zonedist1": "R6B",
        "bldgclass": "C1",
        "landuse": "02",
        "ownername": "185 BERGEN ST LLC",
        "numfloors": 4,
        "yearbuilt": 1930,
        "assessland": 148_500,
        "lotarea": 2_500,
        "occupancy": None,
        "occupancy_honesty": "UNAVAILABLE",
    },
    {
        "bbl": "4000067501",
        "borough": "Queens",
        "address": "4-75 48 AVENUE",
        "zonedist1": "R6",
        "bldgclass": "R4",
        "landuse": "03",
        "ownername": "CITYLIGHTS CONDOMINIUM",
        "numfloors": 27,
        "yearbuilt": 1996,
        "assessland": 2_160_000,
        "lotarea": 54_000,
        "occupancy": None,
        "occupancy_honesty": "UNAVAILABLE",
    },
    {
        "bbl": "3039880022",
        "borough": "Kings",
        "address": "585 SUTTER AVENUE",
        "zonedist1": "R6",
        "bldgclass": "V1",
        "landuse": "11",
        "ownername": "CITY OF NEW YORK",
        "numfloors": 0,
        "yearbuilt": 0,
        "assessland": 72_000,
        "lotarea": 5_000,
        "occupancy": None,
        "occupancy_honesty": "UNAVAILABLE",
    },
    {
        "bbl": "4098120045",
        "borough": "Queens",
        "address": "89-31 161 STREET",
        "zonedist1": "C4-2",
        "bldgclass": "O5",
        "landuse": "05",
        "ownername": "JAMAICA CENTER LLC",
        "numfloors": 6,
        "yearbuilt": 1964,
        "assessland": 891_000,
        "lotarea": 12_400,
        "occupancy": None,
        "occupancy_honesty": "UNAVAILABLE",
    },
    {
        "bbl": "3000460012",
        "borough": "Kings",
        "address": "100 SCHERMERHORN STREET",
        "zonedist1": "C6-1",
        "bldgclass": "O3",
        "landuse": "05",
        "ownername": "100 SCHERMERHORN LLC",
        "numfloors": 6,
        "yearbuilt": 1924,
        "assessland": 1_890_000,
        "lotarea": 9_800,
        "occupancy": None,
        "occupancy_honesty": "UNAVAILABLE",
    },
]

_BOROUGH_ALIAS = {
    "kings": "Kings",
    "brooklyn": "Kings",
    "bk": "Kings",
    "3": "Kings",
    "queens": "Queens",
    "qn": "Queens",
    "qns": "Queens",
    "4": "Queens",
    "manhattan": "Manhattan",
    "new york": "Manhattan",
    "mn": "Manhattan",
    "1": "Manhattan",
    "bronx": "Bronx",
    "bx": "Bronx",
    "2": "Bronx",
    "staten island": "Staten Island",
    "si": "Staten Island",
    "richmond": "Staten Island",
    "5": "Staten Island",
}
_SAMPLE = {"Kings", "Queens"}
_DIGIT_BOROUGH = {"1": "Manhattan", "2": "Bronx", "3": "Kings", "4": "Queens", "5": "Staten Island"}
_SOURCE = "PLUTO-style sample (not NYC open data live feed)"
_NOTE_HIT = "Not MLS. Occupancy UNAVAILABLE."
_NOTE_MISS = "No lot in the Kings/Queens sample."
_REASON_OTHER = "Sample is Kings/Queens only."


def _digits(s: str) -> str:
    return "".join(c for c in s if c.isdigit())


def _norm(s: str) -> str:
    return " ".join(s.casefold().replace(",", " ").split())


def _canon_borough(raw: str) -> str | None:
    if not raw:
        return None
    return _BOROUGH_ALIAS.get(_norm(raw))


def _record(lot: dict[str, Any]) -> dict[str, Any]:
    rec = dict(lot)
    rec["occupancy"] = None
    rec["occupancy_honesty"] = "UNAVAILABLE"
    return rec


def _closest(query: str, pool: list[dict[str, Any]], n: int = 3) -> list[str]:
    q = _norm(query) if query else ""
    scored = sorted(
        pool,
        key=lambda lot: SequenceMatcher(None, q, _norm(lot["address"])).ratio(),
        reverse=True,
    )
    return [lot["address"] for lot in scored[:n]]


def _hit_output(lot: dict[str, Any]) -> dict[str, Any]:
    rec = _record(lot)
    return {
        "record": rec,
        "pluto_honesty": "MEASURED",
        "occupancy": None,
        "occupancy_honesty": "UNAVAILABLE",
        "source": _SOURCE,
        "note": _NOTE_HIT,
    }


def _miss_output(query: str, pool: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "record": None,
        "candidates": _closest(query, pool, 3),
        "pluto_honesty": "MEASURED",
        "occupancy": None,
        "occupancy_honesty": "UNAVAILABLE",
        "source": _SOURCE,
        "note": _NOTE_MISS,
    }


def _other_output(reason: str = _REASON_OTHER) -> dict[str, Any]:
    return {
        "record": None,
        "reason": reason,
        "occupancy": None,
        "occupancy_honesty": "UNAVAILABLE",
        "source": _SOURCE,
        "note": _NOTE_HIT,
        "pluto_honesty": "LIVE",
    }


def act(payload: Mapping[str, Any]) -> dict[str, Any]:
    bbl_raw = text(payload, "bbl", "BBL", "lot", default="")
    address = text(payload, "address", "addr", "street", default="")
    borough_raw = text(payload, "borough", "boro", "borough_name", default="")
    if not bbl_raw and not address and not borough_raw:
        address = "120 Schermerhorn Street"
        borough_raw = "Kings"

    bbl = _digits(bbl_raw)
    borough = _canon_borough(borough_raw)

    if bbl:
        digit = bbl[0]
        named = _DIGIT_BOROUGH.get(digit)
        if named and named not in _SAMPLE:
            return seal(cell="N8", status="warn", payload=payload, output=_other_output(), honesty="LIVE")
        for lot in LOTS:
            if lot["bbl"] == bbl or lot["bbl"] == bbl_raw.strip():
                return seal(cell="N8", status="ok", payload=payload, output=_hit_output(lot))
        pool = [lot for lot in LOTS if not named or lot["borough"] == named]
        return seal(cell="N8", status="warn", payload=payload, output=_miss_output(address or bbl, pool or LOTS))

    if borough and borough not in _SAMPLE:
        return seal(cell="N8", status="warn", payload=payload, output=_other_output(), honesty="LIVE")

    pool = [lot for lot in LOTS if borough is None or lot["borough"] == borough]
    if not address:
        return seal(cell="N8", status="warn", payload=payload, output=_miss_output("", pool or LOTS))

    q = _norm(address)
    exact = [lot for lot in pool if _norm(lot["address"]) == q]
    if exact:
        return seal(cell="N8", status="ok", payload=payload, output=_hit_output(exact[0]))

    subs = [lot for lot in pool if q in _norm(lot["address"]) or _norm(lot["address"]) in q]
    if len(subs) == 1:
        return seal(cell="N8", status="ok", payload=payload, output=_hit_output(subs[0]))
    if len(subs) > 1:
        ranked = sorted(subs, key=lambda lot: SequenceMatcher(None, q, _norm(lot["address"])).ratio(), reverse=True)
        best, second = ranked[0], ranked[1]
        br = SequenceMatcher(None, q, _norm(best["address"])).ratio()
        sr = SequenceMatcher(None, q, _norm(second["address"])).ratio()
        if br >= 0.72 and br - sr >= 0.08:
            return seal(cell="N8", status="ok", payload=payload, output=_hit_output(best))
        return seal(cell="N8", status="warn", payload=payload, output=_miss_output(address, ranked))

    # Token overlap: house number + street token can still unique-hit.
    q_toks = set(q.replace("-", " ").split())
    scored: list[tuple[float, dict[str, Any]]] = []
    for lot in pool:
        addr = _norm(lot["address"])
        toks = set(addr.replace("-", " ").split())
        if not q_toks or not toks:
            continue
        overlap = len(q_toks & toks) / len(q_toks)
        ratio = SequenceMatcher(None, q, addr).ratio()
        scored.append((max(overlap, ratio), lot))
    scored.sort(key=lambda t: t[0], reverse=True)
    if scored and scored[0][0] >= 0.72 and (len(scored) == 1 or scored[0][0] - scored[1][0] >= 0.08):
        return seal(cell="N8", status="ok", payload=payload, output=_hit_output(scored[0][1]))

    return seal(cell="N8", status="warn", payload=payload, output=_miss_output(address, pool or LOTS))
