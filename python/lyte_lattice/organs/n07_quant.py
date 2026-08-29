"""N7 Quant — cited QuantConnect LEAN. Not a live broker. Not QuantConnect Cloud."""
from __future__ import annotations

import datetime as dt
import hashlib
import math
import random
from typing import Any, Mapping

from lyte_lattice.organ import num, seal, text

KINDS = ("sma", "meanrev", "momentum", "buyhold")
SYMBOLS = ("SPY", "AAPL", "MSFT", "NVDA")
CASH0 = 100_000.0
BARS_N = 252
_NOTE = "Deterministic synthetic bars. Not a live broker."


def _seed(symbol: str) -> int:
    # builtin hash() is salted per process; sha256 keeps bars deterministic.
    return int(hashlib.sha256(symbol.encode("utf-8")).hexdigest()[:16], 16)


def _session_days(n: int, end: dt.date) -> list[dt.date]:
    days: list[dt.date] = []
    d = end
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d -= dt.timedelta(days=1)
    days.reverse()
    return days


def _bars(symbol: str, n: int = BARS_N) -> list[dict[str, Any]]:
    seed = _seed(symbol)
    rng = random.Random(seed)
    vol = 0.008 + (seed % 1500) / 100_000.0
    drift = 0.00025
    px = 100.0
    out: list[dict[str, Any]] = []
    for day in _session_days(n, dt.date(2026, 8, 28)):
        z = rng.gauss(0.0, 1.0)
        nxt = max(1.0, px * math.exp(drift - 0.5 * vol * vol + vol * z))
        out.append({"d": day.isoformat(), "c": round(nxt, 6)})
        px = nxt
    return out


def _sma(values: list[float], window: int) -> list[float | None]:
    out: list[float | None] = []
    acc = 0.0
    for i, v in enumerate(values):
        acc += v
        if i >= window:
            acc -= values[i - window]
        out.append(acc / window if i >= window - 1 else None)
    return out


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _stdev(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    var = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    return math.sqrt(var) if var > 0 else 0.0


def _maxdd(equity: list[float]) -> float:
    peak = equity[0] if equity else 1.0
    dd = 0.0
    for v in equity:
        if v > peak:
            peak = v
        if peak:
            dd = min(dd, v / peak - 1.0)
    return dd


def _backtest(
    bars: list[dict[str, Any]],
    kind: str,
    fast_n: int,
    slow_n: int,
    lookback: int,
    z_enter: float,
    mom_n: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    closes = [float(b["c"]) for b in bars]
    cash = CASH0
    qty = 0
    trades: list[dict[str, Any]] = []
    equity: list[float] = []
    fast = _sma(closes, fast_n)
    slow = _sma(closes, slow_n)

    for i, bar in enumerate(bars):
        px = closes[i]
        target = qty
        if kind == "buyhold":
            target = math.floor(CASH0 / px) if i == 0 else qty
        elif kind == "sma":
            f, s = fast[i], slow[i]
            if f is not None and s is not None:
                target = math.floor((cash + qty * px) * 0.99 / px) if f > s else 0
        elif kind == "meanrev":
            if i >= lookback:
                window = closes[i - lookback : i]
                m = _mean(window)
                sd = _stdev(window) or 1e-9
                z = (px - m) / sd
                if z < -z_enter:
                    target = math.floor((cash + qty * px) * 0.95 / px)
                elif z > z_enter:
                    target = 0
        elif kind == "momentum":
            if i >= mom_n:
                ret = px / closes[i - mom_n] - 1.0
                target = math.floor((cash + qty * px) * 0.99 / px) if ret > 0 else 0
        if target < 0:
            target = 0
        if target != qty:
            delta = target - qty
            side = "buy" if delta > 0 else "sell"
            cash -= delta * px
            qty = target
            trades.append({"d": bar["d"], "side": side, "px": round(px, 4), "qty": abs(delta)})
        equity.append(cash + qty * px)

    rets: list[float] = []
    for i in range(1, len(equity)):
        prev = equity[i - 1]
        if prev:
            rets.append(equity[i] / prev - 1.0)
    last = equity[-1] if equity else CASH0
    first = equity[0] if equity else CASH0
    ret = last / first - 1.0 if first else 0.0
    years = max(1 / 252.0, len(equity) / 252.0)
    cagr = (last / first) ** (1.0 / years) - 1.0 if first > 0 else 0.0
    sd = _stdev(rets) or 1e-9
    sharpe = (_mean(rets) / sd) * math.sqrt(252.0)
    if not math.isfinite(sharpe):
        sharpe = 0.0
    wins = 0
    sells = 0
    for idx, t in enumerate(trades):
        if t["side"] != "sell":
            continue
        sells += 1
        buy = next((x for x in reversed(trades[:idx]) if x["side"] == "buy"), None)
        if buy and t["px"] > buy["px"]:
            wins += 1
    stats = {
        "ret": round(ret, 6),
        "sharpe": round(sharpe, 6),
        "maxdd": round(_maxdd(equity), 6),
        "win": round((wins / sells) if sells else 0.0, 6),
        "trades": len(trades),
        "cagr": round(cagr, 6),
    }
    return trades, stats


def act(payload: Mapping[str, Any]) -> dict[str, Any]:
    kind = text(payload, "kind", "strategy", default="sma").strip().lower().replace("-", "").replace("_", "")
    if kind in {"buyandhold", "bh"}:
        kind = "buyhold"
    if kind in {"meanreversion", "mr"}:
        kind = "meanrev"
    if kind in {"mom"}:
        kind = "momentum"
    status = "ok"
    if kind not in KINDS:
        kind = "sma"
        status = "warn"
    symbol = text(payload, "symbol", "ticker", default="SPY").strip().upper() or "SPY"
    fast = max(1, int(round(num(payload, "fast", 10.0))))
    slow = max(fast + 1, int(round(num(payload, "slow", 30.0))))
    lookback = max(2, int(round(num(payload, "lookback", 20.0))))
    z_enter = float(num(payload, "z", 1.2))
    mom_n = max(2, int(round(num(payload, "mom", 60.0))))

    bars = _bars(symbol, BARS_N)
    trades, stats = _backtest(bars, kind, fast, slow, lookback, z_enter, mom_n)
    if stats["maxdd"] < -0.2:
        status = "warn"
    output = {
        "kind": kind,
        "symbol": symbol,
        "bars": len(bars),
        "trades": trades[-8:],
        "stats": stats,
        "params": {"fast": fast, "slow": slow, "lookback": lookback, "z": z_enter, "mom": mom_n, "cash0": CASH0},
        "note": _NOTE,
    }
    return seal(cell="N7", status=status, payload=payload, output=output)
