"""Celery tasks for backtests and live trading.

All progress, log lines and closed trades are pushed to the frontend through
Channels groups (Redis-backed), so a worker running in a separate process
streams updates in real time to the Django/ASGI process that serves the
WebSocket. Task control (pause / resume / stop) is coordinated through the DB
`control` field on the run/session model, which the task re-reads on every
loop iteration.
"""
import logging
import threading
import time
import traceback
from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple

from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone

logger = logging.getLogger("trading.tasks")


# ── channels helpers ───────────────────────────────────────────

def _send(group: str, data: Dict[str, Any]) -> None:
    """Broadcast a JSON payload to a channels group (blocking)."""
    try:
        layer = get_channel_layer()
        if layer is None:
            return
        async_to_sync(layer.group_send)(
            group,
            {"type": "broadcast_message", "data": data},
        )
    except Exception as exc:  # noqa: BLE001
        # Don't use `logger.warning` here: that would be captured by the log
        # handler which calls back into `_send` and recurses.
        print(f"channel_layer.group_send failed: {exc}")


class LogBatcher:
    """Collects log entries and drains them synchronously when asked.

    Why no background thread: under the Celery gevent pool every greenlet
    shares one asyncio event loop, so `async_to_sync(group_send)` from a
    secondary greenlet collides with the main one ("AsyncToSync in the same
    thread as an async event loop"). Instead, `emit()` just appends to a
    bounded deque and the task's main loop calls `flush()` at a throttled
    cadence - all channel I/O happens from the main greenlet.
    """

    def __init__(
        self,
        group: str,
        max_per_flush: int = 100,
        max_buffered: int = 2000,
    ) -> None:
        self.group = group
        self.max_per_flush = max_per_flush
        self._buf: deque = deque(maxlen=max_buffered)
        self._lock = threading.Lock()

    def append(self, entry: Dict[str, Any]) -> None:
        with self._lock:
            self._buf.append(entry)

    def _drain_one_batch(self) -> List[Dict[str, Any]]:
        batch: List[Dict[str, Any]] = []
        with self._lock:
            while self._buf and len(batch) < self.max_per_flush:
                batch.append(self._buf.popleft())
        return batch

    def __len__(self) -> int:
        with self._lock:
            return len(self._buf)

    def flush(self, max_batches: int = 5) -> int:
        """Send up to `max_batches * max_per_flush` buffered lines.

        Cheap when the buffer is empty. Call on every iteration of the task's
        main loop so logs never trail more than one iteration behind.
        """
        sent = 0
        for _ in range(max_batches):
            batch = self._drain_one_batch()
            if not batch:
                break
            _send(self.group, {"type": "logs", "entries": batch})
            sent += len(batch)
        return sent

    def drain_all(self) -> None:
        """Flush every remaining entry (called on task teardown)."""
        while True:
            batch = self._drain_one_batch()
            if not batch:
                return
            _send(self.group, {"type": "logs", "entries": batch})


class ChannelsLogHandler(logging.Handler):
    """Pushes log records into a `LogBatcher`. Emit is always non-blocking."""

    _in_flight = False

    def __init__(self, batcher: LogBatcher, level: int = logging.INFO):
        super().__init__(level=level)
        self.batcher = batcher
        self.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        if ChannelsLogHandler._in_flight:
            return
        ChannelsLogHandler._in_flight = True
        try:
            self.batcher.append({
                "level": record.levelname,
                "logger": record.name,
                "message": self.format(record),
                "ts": timezone.now().isoformat(),
            })
        except Exception:  # noqa: BLE001
            pass
        finally:
            ChannelsLogHandler._in_flight = False


# Only attach to loggers we care about; DO NOT include "" (root) or "celery"
# because raising those to INFO drags in noise from django/urllib3/etc.
_LOG_TARGETS = ("trading", "engine", "trading_system")


def _attach_log_stream(group: str) -> Tuple[ChannelsLogHandler, LogBatcher]:
    batcher = LogBatcher(group)
    handler = ChannelsLogHandler(batcher, level=logging.INFO)
    for name in _LOG_TARGETS:
        lg = logging.getLogger(name)
        lg.addHandler(handler)
        # Only relax level if it's more restrictive than INFO.
        if lg.level == logging.NOTSET or lg.level > logging.INFO:
            lg.setLevel(logging.INFO)
    return handler, batcher


def _detach_log_stream(state: Tuple[ChannelsLogHandler, LogBatcher]) -> None:
    handler, batcher = state
    for name in _LOG_TARGETS:
        logging.getLogger(name).removeHandler(handler)
    batcher.drain_all()


# ── backtest task ─────────────────────────────────────────────

@shared_task(bind=True, max_retries=0, name="trading.tasks.run_backtest_task")
def run_backtest_task(self, run_id: int) -> None:
    """Execute a backtest run, streaming progress over channels."""
    from trading.models import BacktestRun, BacktestTrade

    group = f"backtest_{run_id}"
    log_handler = _attach_log_stream(group)

    try:
        run = BacktestRun.objects.get(pk=run_id)
    except BacktestRun.DoesNotExist:
        logger.error("BacktestRun %s missing", run_id)
        _detach_log_stream(log_handler)
        return

    run.status = "running"
    run.control = "run"
    run.celery_task_id = self.request.id or ""
    run.save(update_fields=["status", "control", "celery_task_id"])

    _send(group, {
        "type": "status",
        "status": "running",
        "message": "Initializing engine...",
    })

    saved_order_ids: Set[int] = set()

    try:
        from django.conf import settings
        from engine.bridge import (
            build_engine,
            create_backtest_generators,
            get_backtest_summary,
            load_indicators_from_config_paths,
            run_backtest_iteration,
        )

        config = dict(run.config_snapshot or {})
        if not config:
            raise ValueError("No config snapshot found on run")

        config["symbols"] = run.symbols
        config.setdefault("date_range", {})
        config["date_range"]["start_date"] = run.start_date
        config["date_range"]["end_date"] = run.end_date
        config["resolution"] = run.resolution
        config.setdefault("backtest", {})
        config["backtest"]["enabled"] = True
        config["backtest"]["resolution"] = run.resolution
        config["backtest"]["start_date"] = run.start_date
        config["backtest"]["end_date"] = run.end_date

        engine = build_engine(config)
        load_indicators_from_config_paths(
            engine,
            str(settings.INDICATORS_CONFIG_PATH),
            str(settings.TRADING_CONFIG_PATH),
        )

        _send(group, {
            "type": "status",
            "status": "running",
            "message": "Fetching market data...",
        })

        data_dir = config.get("data_dir", str(settings.BASE_DIR / "data"))
        generators = create_backtest_generators(
            run.symbols, run.start_date, run.end_date, run.resolution,
            data_dir=data_dir,
        )
        if not generators:
            raise ValueError("No data generators created. Check symbols and date range.")

        total_bars = sum(len(g.full_data) for g in generators.values())
        run.total_bars = total_bars
        run.save(update_fields=["total_bars"])

        _send(group, {
            "type": "status",
            "status": "running",
            "message": f"Starting backtest ({total_bars} bars)",
            "total_bars": total_bars,
        })

        allow_buy = config.get("trading", {}).get("allow_buy", True)
        allow_sell = config.get("trading", {}).get("allow_sell", False)

        iteration = 0
        stopped_by_user = False
        last_push = 0.0
        PUSH_EVERY_SEC = 0.5

        # Buffer bars produced between throttled progress pushes so the chart
        # doesn't drop any candles (one new bar per symbol per iteration).
        bars_buffer: Dict[str, List[Dict[str, Any]]] = {}

        # Unpack log streamer so we can flush from the loop.
        _, log_batcher = log_handler  # type: ignore[misc]

        while True:
            # Drain buffered log records on every iteration - the engine emits
            # logs synchronously during `run_backtest_iteration`, so without
            # this the log panel would lag behind the actual work.
            log_batcher.flush()

            control = _read_control(BacktestRun, run_id)
            if control == "stop":
                stopped_by_user = True
                run.status = "stopping"
                run.save(update_fields=["status"])
                _send(group, {"type": "status", "status": "stopping", "message": "Stop requested"})
                break
            if control == "pause":
                if run.status != "paused":
                    run.status = "paused"
                    run.save(update_fields=["status"])
                    _send(group, {"type": "status", "status": "paused", "message": "Paused"})
                time.sleep(0.5)
                continue
            if run.status == "paused":
                run.status = "running"
                run.save(update_fields=["status"])
                _send(group, {"type": "status", "status": "running", "message": "Resumed"})

            iteration += 1
            results = run_backtest_iteration(
                engine, generators, config,
                allow_buy=allow_buy, allow_sell=allow_sell,
            )

            # Buffer one candle per symbol that produced a bar this iteration
            # so every candle ends up on the chart, even when progress is
            # throttled.
            for r in results:
                sym = r.get("symbol")
                cb = r.get("current_bar")
                if not sym or not cb:
                    continue
                aware = _to_aware(cb.get("time"))
                if aware is None:
                    continue
                bars_buffer.setdefault(sym, []).append({
                    "time": int(aware.timestamp()),
                    "open": cb["open"],
                    "high": cb["high"],
                    "low": cb["low"],
                    "close": cb["close"],
                    "volume": cb["volume"],
                })

            processed = sum(g.current_index for g in generators.values())
            all_done = all(g.is_complete() for g in generators.values())

            now = time.monotonic()
            should_push = all_done or (now - last_push) >= PUSH_EVERY_SEC
            if should_push:
                last_push = now
                run.processed_bars = processed
                run.save(update_fields=["processed_bars"])

                new_trades = _persist_new_trades(
                    run=run,
                    engine=engine,
                    saved_order_ids=saved_order_ids,
                )

                open_df = engine.get_open_positions()

                # Live summary + metrics (same shape as the final payload so the
                # frontend can reuse a single renderer).
                try:
                    live = get_backtest_summary(engine)
                    live_summary = live["summary"]
                    live_metrics = live["metrics"]
                    running_pnl = float(live_summary.get("total_pnl", 0))
                    trade_count = int(live_metrics.get("total_trades", 0))
                except Exception as exc:  # noqa: BLE001
                    logger.debug("live summary failed: %s", exc)
                    live_summary = None
                    live_metrics = None
                    closed = engine.get_closed_orders()
                    running_pnl = float(closed["pnl"].sum()) if not closed.empty else 0.0
                    trade_count = len(closed) if not closed.empty else 0

                open_positions = _serialize_open_positions(open_df)

                pct = (processed / total_bars * 100) if total_bars else 0.0

                # Per-symbol ticker (LTP + current bar time) for the Run Info
                # panel - the UI shows one line per symbol that refreshes each
                # progress push.
                symbol_ticks = []
                latest_bar_time: Optional[str] = None
                for r in results:
                    ct_iso = None
                    ct_raw = r.get("current_time")
                    if ct_raw is not None:
                        aware = _to_aware(ct_raw)
                        if aware is not None:
                            ct_iso = aware.isoformat()
                            if latest_bar_time is None or ct_iso > latest_bar_time:
                                latest_bar_time = ct_iso
                    symbol_ticks.append({
                        "symbol": r.get("symbol", ""),
                        "signal": r.get("final_signal", "HOLD"),
                        "price": float(r.get("current_price", 0) or 0),
                        "time": ct_iso,
                    })

                payload = {
                    "type": "progress",
                    "iteration": iteration,
                    "processed_bars": processed,
                    "total_bars": total_bars,
                    "progress_pct": round(pct, 1),
                    "running_pnl": round(running_pnl, 2),
                    "trade_count": trade_count,
                    "open_positions": open_positions,
                    "bar_time": latest_bar_time,
                    "latest_results": symbol_ticks,
                }
                if bars_buffer:
                    try:
                        from trading.bar_store import append_bars
                        append_bars(run_id, bars_buffer)
                    except Exception as exc:  # noqa: BLE001
                        logger.debug("bar_store.append_bars failed: %s", exc)
                    payload["bars"] = bars_buffer
                    bars_buffer = {}
                if live_summary is not None:
                    payload["summary"] = live_summary
                if live_metrics is not None:
                    payload["metrics"] = live_metrics
                if new_trades:
                    payload["new_trades"] = new_trades
                _send(group, payload)

            if all_done:
                break

        _persist_new_trades(run=run, engine=engine, saved_order_ids=saved_order_ids)

        summary_data = get_backtest_summary(engine)

        run.status = "stopped" if stopped_by_user else "completed"
        run.summary_json = summary_data["summary"]
        run.metrics_json = summary_data["metrics"]
        run.processed_bars = sum(g.current_index for g in generators.values())
        run.completed_at = timezone.now()
        run.save()

        _send(group, {
            "type": "completed" if not stopped_by_user else "stopped",
            "status": run.status,
            "summary": summary_data["summary"],
            "metrics": summary_data["metrics"],
            "trade_count": len(summary_data["trades"]),
        })

        logger.info("Backtest #%d %s. PnL: %s", run_id, run.status,
                    summary_data["summary"].get("total_pnl"))

    except Exception as exc:  # noqa: BLE001
        logger.error("Backtest #%d failed: %s\n%s", run_id, exc, traceback.format_exc())
        try:
            run.refresh_from_db()
            run.status = "failed"
            run.error_message = str(exc)
            run.save(update_fields=["status", "error_message"])
        except Exception:  # noqa: BLE001
            pass
        _send(group, {"type": "error", "message": str(exc)})

    finally:
        _detach_log_stream(log_handler)


# ── live task ────────────────────────────────────────────────

@shared_task(bind=True, max_retries=0, name="trading.tasks.run_live_task")
def run_live_task(self, session_id: int) -> None:
    """Execute a live trading session, streaming updates over channels."""
    from trading.models import LiveSession

    group = f"live_{session_id}"
    log_handler = _attach_log_stream(group)

    try:
        session = LiveSession.objects.get(pk=session_id)
    except LiveSession.DoesNotExist:
        logger.error("LiveSession %s missing", session_id)
        _detach_log_stream(log_handler)
        return

    session.status = "running"
    session.control = "run"
    session.celery_task_id = self.request.id or ""
    if not session.started_at:
        session.started_at = timezone.now()
    session.save(update_fields=["status", "control", "celery_task_id", "started_at"])

    saved_order_ids: Set[int] = set()

    try:
        from django.conf import settings
        from engine.bridge import (
            build_engine,
            get_backtest_summary as get_engine_summary,
            load_indicators_from_config_paths,
        )
        from engine.data.data_loader import DataLoader

        config = dict(session.config_snapshot or {})
        if not config:
            raise ValueError("No config snapshot on session")

        engine = build_engine(config)
        load_indicators_from_config_paths(
            engine,
            str(settings.INDICATORS_CONFIG_PATH),
            str(settings.TRADING_CONFIG_PATH),
        )

        data_loader = DataLoader()
        symbols = session.symbols
        allow_buy = config.get("trading", {}).get("allow_buy", True)
        allow_sell = config.get("trading", {}).get("allow_sell", False)
        refresh_interval = float(config.get("trading", {}).get("refresh_interval", 5))
        try:
            live_lookback = int((config.get("trading") or {}).get("lookback_bars") or 0)
        except (TypeError, ValueError):
            live_lookback = 0

        _send(group, {"type": "status", "status": "running", "message": "Live session started"})

        _, log_batcher = log_handler  # type: ignore[misc]

        iteration = 0
        stopped_by_user = False

        last_bar_ts: Dict[str, int] = {}
        try:
            from trading.bar_store import list_symbols as _ls_live, read_bars as _rb_live
            for _sym in _ls_live(session_id, kind="live"):
                _prev = _rb_live(session_id, _sym, kind="live")
                if _prev:
                    last_bar_ts[_sym] = int(_prev[-1]["time"])
        except Exception as exc:  # noqa: BLE001
            logger.debug("bar_store: could not recover last_bar_ts for session %s: %s", session_id, exc)

        while True:
            log_batcher.flush()
            control = _read_control(LiveSession, session_id)
            if control == "stop":
                stopped_by_user = True
                session.status = "stopping"
                session.save(update_fields=["status"])
                _send(group, {"type": "status", "status": "stopping", "message": "Stop requested"})
                break
            if control == "pause":
                if session.status != "paused":
                    session.status = "paused"
                    session.save(update_fields=["status"])
                    _send(group, {"type": "status", "status": "paused", "message": "Paused"})
                time.sleep(1.0)
                continue
            if session.status == "paused":
                session.status = "running"
                session.save(update_fields=["status"])
                _send(group, {"type": "status", "status": "running", "message": "Resumed"})

            iteration += 1
            results: List[Dict[str, Any]] = []
            live_bars: Dict[str, List[Dict[str, Any]]] = {}
            persist_bars: Dict[str, List[Dict[str, Any]]] = {}
            symbol_ticks: List[Dict[str, Any]] = []
            latest_bar_time: Optional[str] = None

            for symbol in symbols:
                try:
                    df = data_loader.load_symbol_data(
                        symbol,
                        config.get("date_range", {}).get("start_date", ""),
                        config.get("date_range", {}).get("end_date", ""),
                        config.get("resolution", "1"),
                    )
                    if df is None or df.empty:
                        continue
                    df = data_loader.prepare_for_indicators(df)
                    if live_lookback > 0 and len(df) > live_lookback:
                        df = df.tail(live_lookback)
                    result = engine.analyze_symbol(df, symbol, verbose=False)

                    current_price = float(df["close"].iloc[-1])
                    signal = result.get("final_signal", "HOLD")

                    bar_time = None
                    for col in ("datetime", "date", "timestamp", "time"):
                        if col in df.columns:
                            val = df[col].iloc[-1]
                            aware = _to_aware(val)
                            if aware is not None:
                                bar_time = aware
                                break
                    if bar_time is None:
                        bar_time = timezone.now()
                    bar_iso = bar_time.isoformat()
                    if latest_bar_time is None or bar_iso > latest_bar_time:
                        latest_bar_time = bar_iso

                    bars_all = _df_to_bars(df)
                    if bars_all:
                        prev_ts = last_bar_ts.get(symbol, 0)
                        fresh = [b for b in bars_all if b["time"] > prev_ts]
                        payload_list = list(fresh)
                        if not payload_list or payload_list[-1]["time"] != bars_all[-1]["time"]:
                            payload_list.append(bars_all[-1])
                        live_bars[symbol] = payload_list
                        if fresh:
                            persist_bars[symbol] = fresh
                            last_bar_ts[symbol] = fresh[-1]["time"]

                    # TradingEngine exposes a single entry-point that handles
                    # entries, position checks and exit-strategy evaluation.
                    # analyze_symbol already ran the exit logic, so we only
                    # need to gate unwanted entries here and call the
                    # decision executor once.
                    gated = signal
                    if gated == "BUY" and not allow_buy:
                        gated = "HOLD"
                    elif gated == "SELL" and not allow_sell:
                        gated = "HOLD"

                    decision = dict(result)
                    decision["symbol"] = symbol
                    decision["final_signal"] = gated
                    decision["latest_price"] = current_price
                    decision["current_price"] = current_price
                    decision["current_time"] = bar_time

                    lot_sizes = config.get("trading", {}).get("lot_sizes", {})
                    qty = lot_sizes.get(symbol, config.get("trading", {}).get("default_quantity", 20))
                    engine.execute_trading_decision(
                        decision,
                        quantity=qty,
                        df=df,
                        current_timestamp=bar_time,
                    )

                    results.append({
                        "symbol": symbol,
                        "signal": signal,
                        "price": current_price,
                        "time": bar_iso,
                        "indicators": result.get("indicator_signals", {}),
                    })
                    symbol_ticks.append({
                        "symbol": symbol,
                        "signal": signal,
                        "price": current_price,
                        "time": bar_iso,
                    })
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Live analysis error for %s: %s", symbol, exc)

            # Persist newly closed trades + cache bars.
            new_trades = _persist_new_live_trades(
                session=session, engine=engine, saved_order_ids=saved_order_ids,
            )
            if persist_bars:
                try:
                    from trading.bar_store import append_bars
                    append_bars(session_id, persist_bars, kind="live")
                except Exception as exc:  # noqa: BLE001
                    logger.debug("bar_store.append_bars failed: %s", exc)

            # Live summary + metrics (same shape as the backtest payload so the
            # frontend can share one renderer).
            try:
                live = get_engine_summary(engine)
                live_summary = live["summary"]
                live_metrics = live["metrics"]
                total_pnl = float(live_summary.get("total_pnl", 0))
                trade_count = int(live_metrics.get("total_trades", 0))
            except Exception as exc:  # noqa: BLE001
                logger.debug("live summary failed: %s", exc)
                live_summary = None
                live_metrics = None
                closed = engine.get_closed_orders()
                total_pnl = float(closed["pnl"].sum()) if not closed.empty else 0.0
                trade_count = len(closed) if not closed.empty else 0

            session.total_pnl = total_pnl
            session.total_trades = trade_count
            session.iterations = iteration
            if live_summary is not None:
                session.summary_json = live_summary
            if live_metrics is not None:
                session.metrics_json = live_metrics
            session.save(update_fields=[
                "total_pnl", "total_trades", "iterations",
                "summary_json", "metrics_json",
            ])

            open_positions = _serialize_open_positions(engine.get_open_positions())

            update_payload: Dict[str, Any] = {
                "type": "update",
                "iteration": iteration,
                "results": results,
                "total_pnl": round(total_pnl, 2),
                "running_pnl": round(total_pnl, 2),
                "trade_count": trade_count,
                "open_positions": open_positions,
                "bar_time": latest_bar_time,
                "latest_results": symbol_ticks,
            }
            if live_bars:
                update_payload["bars"] = live_bars
            if live_summary is not None:
                update_payload["summary"] = live_summary
            if live_metrics is not None:
                update_payload["metrics"] = live_metrics
            if new_trades:
                update_payload["new_trades"] = new_trades
            _send(group, update_payload)

            time.sleep(refresh_interval)

        # Final persist + summary refresh.
        _persist_new_live_trades(session=session, engine=engine, saved_order_ids=saved_order_ids)
        try:
            final = get_engine_summary(engine)
            session.summary_json = final["summary"]
            session.metrics_json = final["metrics"]
        except Exception:  # noqa: BLE001
            pass

        session.status = "stopped" if stopped_by_user else "stopped"
        session.stopped_at = timezone.now()
        session.save()

        _send(group, {
            "type": "stopped",
            "status": session.status,
            "summary": session.summary_json,
            "metrics": session.metrics_json,
            "trade_count": session.total_trades,
            "total_pnl": round(session.total_pnl, 2),
            "message": "Live session stopped",
        })

    except Exception as exc:  # noqa: BLE001
        logger.error("Live session #%d failed: %s\n%s", session_id, exc, traceback.format_exc())
        try:
            session.refresh_from_db()
            session.status = "error"
            session.error_message = str(exc)
            session.save(update_fields=["status", "error_message"])
        except Exception:  # noqa: BLE001
            pass
        _send(group, {"type": "error", "message": str(exc)})

    finally:
        _detach_log_stream(log_handler)


# ── helpers ──────────────────────────────────────────────────

def _read_control(model_cls, pk: int) -> Optional[str]:
    """Cheap `control` column read used every iteration."""
    try:
        return model_cls.objects.filter(pk=pk).values_list("control", flat=True).first()
    except Exception as exc:  # noqa: BLE001
        logger.warning("control read failed: %s", exc)
        return "run"


def _serialize_open_positions(open_df) -> List[Dict[str, Any]]:
    """Turn the engine's open-positions DataFrame into ws-safe dicts.

    Enriches each row with ``entry_time`` (ISO) and ``unrealized_pnl``
    so the frontend can show MTM P&L without extra round-trips.
    """
    import pandas as pd  # noqa: PLC0415

    if open_df is None or open_df.empty:
        return []

    out: List[Dict[str, Any]] = []
    for _, row in open_df.iterrows():
        entry_price = float(row.get("entry_price", 0) or 0)
        ltp = float(row.get("ltp", entry_price) or entry_price)
        qty = int(row.get("quantity", 0) or 0)
        ptype = str(row.get("type", "")).upper()
        if ptype == "LONG":
            unreal = (ltp - entry_price) * qty
        elif ptype == "SHORT":
            unreal = (entry_price - ltp) * qty
        else:
            unreal = 0.0
        pct = ((ltp - entry_price) / entry_price * 100) if entry_price else 0.0
        if ptype == "SHORT":
            pct = -pct

        entry_time_raw = row.get("entry_time")
        entry_iso = None
        if entry_time_raw is not None and (not hasattr(pd, "isna") or not pd.isna(entry_time_raw)):
            aware = _to_aware(entry_time_raw)
            if aware is not None:
                entry_iso = aware.isoformat()

        out.append({
            "order_id": int(row.get("order_id", 0) or 0),
            "symbol": str(row.get("symbol", "")),
            "type": ptype,
            "entry_price": entry_price,
            "ltp": ltp,
            "quantity": qty,
            "entry_time": entry_iso,
            "unrealized_pnl": round(unreal, 2),
            "unrealized_pct": round(pct, 2),
        })
    return out


def _to_aware(ts):
    """Convert pandas Timestamp / naive datetime / string / unix ts / arrow
    object into a tz-aware ``datetime``. Returns None if it can't be parsed.
    """
    import pandas as pd
    from datetime import datetime

    if ts is None:
        return None
    try:
        if hasattr(pd, "isna") and not isinstance(ts, (str, bytes)) and pd.isna(ts):
            return None
    except (TypeError, ValueError):
        pass

    # arrow.Arrow has a .datetime attribute
    if hasattr(ts, "datetime") and not isinstance(ts, datetime):
        try:
            cand = ts.datetime
            if isinstance(cand, datetime):
                ts = cand
        except Exception:  # noqa: BLE001
            pass

    # pandas Timestamp / numpy datetime64
    if hasattr(ts, "to_pydatetime"):
        try:
            ts = ts.to_pydatetime()
        except Exception:  # noqa: BLE001
            pass

    # Unix epoch (seconds or milliseconds)
    if isinstance(ts, (int, float)):
        try:
            secs = ts / 1000.0 if ts > 10_000_000_000 else float(ts)
            ts = datetime.fromtimestamp(secs)
        except Exception:  # noqa: BLE001
            return None

    # String like "MM-DD-YYYY HH:mm:ss" or ISO-ish
    if isinstance(ts, str):
        try:
            parsed = pd.to_datetime(ts, errors="coerce")
            if parsed is pd.NaT or parsed is None:
                return None
            ts = parsed.to_pydatetime()
        except Exception:  # noqa: BLE001
            return None

    if not isinstance(ts, datetime):
        return None
    if timezone.is_aware(ts):
        return ts
    try:
        return timezone.make_aware(ts, timezone.get_current_timezone())
    except Exception:  # noqa: BLE001
        return ts.replace(tzinfo=timezone.get_current_timezone())


def _df_to_bars(df) -> List[Dict[str, Any]]:
    """Convert a DataFrame into chart-ready OHLCV dicts sorted ascending.

    Picks the first available time column (datetime / date / timestamp / time)
    or falls back to a DatetimeIndex. Rows whose time cannot be parsed are
    skipped. Duplicate timestamps keep the later value.
    """
    import pandas as pd

    if df is None or getattr(df, "empty", True):
        return []

    time_col = None
    for col in ("datetime", "date", "timestamp", "time"):
        if col in df.columns:
            time_col = col
            break
    use_index = time_col is None and isinstance(df.index, pd.DatetimeIndex)

    by_t: Dict[int, Dict[str, Any]] = {}
    for idx, row in df.iterrows():
        raw_t = row[time_col] if time_col is not None else (idx if use_index else None)
        aware = _to_aware(raw_t)
        if aware is None:
            continue
        try:
            t = int(aware.timestamp())
        except (ValueError, OSError):
            continue
        close_v = row.get("close", None)
        if close_v is None or (hasattr(pd, "isna") and pd.isna(close_v)):
            continue
        try:
            close_f = float(close_v)
        except (TypeError, ValueError):
            continue
        by_t[t] = {
            "time": t,
            "open": float(row.get("open", close_f) or close_f),
            "high": float(row.get("high", close_f) or close_f),
            "low": float(row.get("low", close_f) or close_f),
            "close": close_f,
            "volume": float(row.get("volume", 0) or 0),
        }
    return sorted(by_t.values(), key=lambda b: b["time"])


def _persist_new_trades(run, engine, saved_order_ids: Set[int]) -> List[Dict[str, Any]]:
    from trading.models import BacktestTrade
    return _persist_trades_generic(
        parent=run, engine=engine, saved_order_ids=saved_order_ids,
        trade_model=BacktestTrade, parent_field="run",
    )


def _persist_new_live_trades(
    session, engine, saved_order_ids: Set[int]
) -> List[Dict[str, Any]]:
    from trading.models import LiveTrade
    return _persist_trades_generic(
        parent=session, engine=engine, saved_order_ids=saved_order_ids,
        trade_model=LiveTrade, parent_field="session",
    )


def _persist_trades_generic(
    *,
    parent,
    engine,
    saved_order_ids: Set[int],
    trade_model,
    parent_field: str,
) -> List[Dict[str, Any]]:
    """Save newly closed trades to ``trade_model`` and return ws-ready dicts.

    Idempotent: tracks ``saved_order_ids`` so we don't insert the same trade
    twice across iterations.
    """
    import pandas as pd

    closed = engine.get_closed_orders()
    if closed is None or closed.empty:
        return []

    new_rows: List[Dict[str, Any]] = []
    for _, row in closed.iterrows():
        order_id = int(row["order_id"])
        if order_id in saved_order_ids:
            continue

        trade_type = str(row["type"])
        entry_price = float(row["entry_price"])
        exit_price = float(row["exit_price"])
        pnl = float(row["pnl"])
        quantity = int(row["quantity"])

        if trade_type == "LONG":
            return_pct = ((exit_price - entry_price) / entry_price) * 100 if entry_price else 0
        else:
            return_pct = ((entry_price - exit_price) / entry_price) * 100 if entry_price else 0

        entry_time = row.get("entry_time")
        exit_time = row.get("exit_time")
        if pd.notna(entry_time) and pd.notna(exit_time):
            secs = int((exit_time - entry_time).total_seconds())
            h, rem = divmod(abs(secs), 3600)
            m, s = divmod(rem, 60)
            duration = f"{h:02d}:{m:02d}:{s:02d}"
        else:
            duration = "N/A"

        entry_dt = _to_aware(entry_time)
        exit_dt = _to_aware(exit_time)

        trade_payload = {
            "order_id": order_id,
            "symbol": str(row["symbol"]),
            "trade_type": trade_type,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "quantity": quantity,
            "pnl": pnl,
            "return_pct": round(return_pct, 2),
            "total_charges": float(row.get("total_charges", 0.0)),
            "net_profit": float(row.get("net_profit", pnl)),
            "is_paper": bool(row.get("paper_trade", False)),
            "duration": duration,
            "entry_reason": str(row.get("entry_reason", "N/A")),
            "exit_reason": str(row.get("exit_reason", "N/A")),
            "entry_time": entry_dt,
            "exit_time": exit_dt,
        }

        trade_model.objects.create(**{parent_field: parent}, **trade_payload)
        saved_order_ids.add(order_id)

        ws_row = dict(trade_payload)
        ws_row["entry_time"] = entry_dt.isoformat() if entry_dt else None
        ws_row["exit_time"] = exit_dt.isoformat() if exit_dt else None
        new_rows.append(ws_row)

    return new_rows
