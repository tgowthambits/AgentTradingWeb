"""Lightweight per-run/session OHLC bar cache.

Bars produced during a backtest or live session are appended as JSONL under
``<BASE_DIR>/data/<kind>_bars/<id>/<safe_symbol>.jsonl`` so that the detail
page can replay them after a reload without re-running the engine.

``kind`` is one of ``"backtest"`` or ``"live"``. For backwards compatibility,
the module-level ``append_bars``/``read_bars``/``list_symbols``/``delete_run``
functions default to ``"backtest"``; new code should pass ``kind`` explicitly.

Format (one JSON object per line, whitespace-stripped)::

    {"t": 1713540000, "o": 123.4, "h": 124.0, "l": 123.0, "c": 123.7, "v": 0}
"""
from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path
from typing import Dict, Iterable, List

from django.conf import settings

logger = logging.getLogger("trading.bar_store")

_ROOT = Path(settings.BASE_DIR) / "data"
_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]")
_KIND_FOLDER = {"backtest": "backtest_bars", "live": "live_bars"}


def _safe_symbol(symbol: str) -> str:
    return _SAFE_RE.sub("_", symbol) or "sym"


def _kind_root(kind: str) -> Path:
    folder = _KIND_FOLDER.get(kind)
    if not folder:
        raise ValueError(f"Unknown bar_store kind: {kind!r}")
    return _ROOT / folder


def _item_dir(kind: str, item_id: int) -> Path:
    return _kind_root(kind) / str(item_id)


def _sym_file(kind: str, item_id: int, symbol: str) -> Path:
    return _item_dir(kind, item_id) / f"{_safe_symbol(symbol)}.jsonl"


def append_bars(
    item_id: int,
    bars_by_symbol: Dict[str, Iterable[dict]],
    *,
    kind: str = "backtest",
) -> None:
    """Append buffered bars for each symbol; creates folder on first write."""
    if not bars_by_symbol:
        return
    item_dir = _item_dir(kind, item_id)
    try:
        item_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning("bar_store: could not create %s: %s", item_dir, exc)
        return

    for symbol, bars in bars_by_symbol.items():
        bars = list(bars) if not isinstance(bars, list) else bars
        if not bars:
            continue
        path = _sym_file(kind, item_id, symbol)
        try:
            with path.open("a", encoding="utf-8") as f:
                for b in bars:
                    f.write(json.dumps({
                        "t": int(b["time"]),
                        "o": float(b["open"]),
                        "h": float(b["high"]),
                        "l": float(b["low"]),
                        "c": float(b["close"]),
                        "v": float(b.get("volume", 0) or 0),
                    }, separators=(",", ":")))
                    f.write("\n")
        except OSError as exc:
            logger.warning("bar_store: append failed for %s/%s: %s", item_id, symbol, exc)


def read_bars(item_id: int, symbol: str, *, kind: str = "backtest") -> List[dict]:
    """Return all bars for a symbol as chart-ready dicts."""
    path = _sym_file(kind, item_id, symbol)
    if not path.exists():
        return []
    out: List[dict] = []
    seen_t: set = set()
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = int(rec.get("t", 0))
                if t in seen_t:
                    continue
                seen_t.add(t)
                out.append({
                    "time": t,
                    "open": rec.get("o"),
                    "high": rec.get("h"),
                    "low": rec.get("l"),
                    "close": rec.get("c"),
                    "volume": rec.get("v", 0),
                })
    except OSError as exc:
        logger.warning("bar_store: read failed for %s/%s: %s", item_id, symbol, exc)
        return []

    out.sort(key=lambda b: b["time"])
    return out


def list_symbols(item_id: int, *, kind: str = "backtest") -> List[str]:
    item_dir = _item_dir(kind, item_id)
    if not item_dir.exists():
        return []
    return sorted(p.stem for p in item_dir.glob("*.jsonl"))


def delete_run(item_id: int, *, kind: str = "backtest") -> None:
    item_dir = _item_dir(kind, item_id)
    if not item_dir.exists():
        return
    try:
        shutil.rmtree(item_dir)
    except OSError as exc:
        logger.warning("bar_store: delete failed for %s: %s", item_id, exc)
