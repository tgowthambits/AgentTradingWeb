import re
import yaml
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from ninja import NinjaAPI, Schema, File, UploadedFile
from django.conf import settings
from django.http import JsonResponse

from .models import TradingConfig, BacktestRun, BacktestTrade, LiveSession, LiveTrade

api = NinjaAPI(title="Trading Platform API", version="1.0.0", urls_namespace="trading-api")

DATA_DIR = settings.BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


# ─── Schemas ───────────────────────────────────────────────

class ConfigIn(Schema):
    name: str
    config_json: dict


class ConfigOut(Schema):
    id: int
    name: str
    config_json: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BacktestRunIn(Schema):
    symbols: List[str]
    start_date: str
    end_date: str
    resolution: str = "1"
    config_id: Optional[int] = None
    config_override: Optional[dict] = None


class BacktestRunOut(Schema):
    id: int
    status: str
    symbols: list
    start_date: str
    end_date: str
    resolution: str
    summary_json: Optional[dict] = None
    metrics_json: Optional[dict] = None
    total_bars: int
    processed_bars: int
    error_message: str
    created_at: datetime
    completed_at: Optional[datetime] = None


class TradeOut(Schema):
    id: int
    order_id: int
    symbol: str
    trade_type: str
    entry_price: float
    exit_price: float
    quantity: int
    pnl: float
    return_pct: float
    total_charges: float
    net_profit: float
    is_paper: bool
    duration: str
    entry_reason: str
    exit_reason: str
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None


class BacktestDetailOut(Schema):
    run: BacktestRunOut
    trades: List[TradeOut]


class LiveSessionIn(Schema):
    symbols: List[str]
    config_id: Optional[int] = None


class LiveSessionOut(Schema):
    id: int
    status: str
    symbols: list
    summary_json: Optional[dict] = None
    metrics_json: Optional[dict] = None
    error_message: str = ""
    iterations: int = 0
    total_pnl: float
    total_trades: int
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None


class LiveSessionDetailOut(Schema):
    session: LiveSessionOut
    trades: List[TradeOut]


class IndicatorOut(Schema):
    name: str
    enabled: bool
    weight: float
    module: str
    params: dict


class MessageOut(Schema):
    message: str


class TradingSymbolsApplyIn(Schema):
    put_symbol: str
    call_symbol: str
    lot_put: int = 20
    lot_call: int = 20


_FYERS_SYM_RE = re.compile(r"^[A-Z0-9][A-Z0-9:_\-]{4,120}$")


def _validate_option_leg(symbol: str, leg: str) -> Optional[str]:
    s = (symbol or "").strip()
    if not _FYERS_SYM_RE.match(s):
        return f"Invalid {leg} symbol format"
    if leg == "put" and not s.endswith("PE"):
        return "Put symbol must end with PE"
    if leg == "call" and not s.endswith("CE"):
        return "Call symbol must end with CE"
    return None


def _trading_yaml_write_targets() -> List[Path]:
    """Paths to update with selected symbols (platform YAML + repo trading_system if present)."""
    paths: List[Path] = [settings.TRADING_CONFIG_PATH]
    repo = settings.BASE_DIR.parent
    alt = repo / "trading_system" / "config" / "trading_config.yaml"
    if alt.is_file() and alt.resolve() != settings.TRADING_CONFIG_PATH.resolve():
        paths.append(alt)
    return paths


def _write_symbols_to_trading_yaml(
    path: Path,
    put: str,
    call: str,
    lot_put: int,
    lot_call: int,
) -> None:
    if not path.exists():
        return
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data["symbols"] = [put, call]
    lot_sizes = data.get("lot_sizes")
    if not isinstance(lot_sizes, dict):
        lot_sizes = {}
    lot_sizes[put] = int(lot_put)
    lot_sizes[call] = int(lot_call)
    data["lot_sizes"] = lot_sizes
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(
            data,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=120,
        )


# ─── Config Endpoints ──────────────────────────────────────

@api.get("/configs/", response=List[ConfigOut])
def list_configs(request):
    return list(TradingConfig.objects.all().values(
        "id", "name", "config_json", "is_active", "created_at", "updated_at"
    ))


@api.post("/configs/", response=ConfigOut)
def create_config(request, payload: ConfigIn):
    obj = TradingConfig.objects.create(name=payload.name, config_json=payload.config_json)
    return obj


@api.get("/configs/{config_id}/", response=ConfigOut)
def get_config(request, config_id: int):
    return TradingConfig.objects.get(pk=config_id)


@api.put("/configs/{config_id}/", response=ConfigOut)
def update_config(request, config_id: int, payload: ConfigIn):
    obj = TradingConfig.objects.get(pk=config_id)
    obj.name = payload.name
    obj.config_json = payload.config_json
    obj.save()
    return obj


@api.delete("/configs/{config_id}/", response=MessageOut)
def delete_config(request, config_id: int):
    TradingConfig.objects.filter(pk=config_id).delete()
    return {"message": "Deleted"}


@api.get("/configs/default/", response=dict)
def get_default_config(request):
    """Load the current YAML config files and return as JSON."""
    config = {}
    trading_path = settings.TRADING_CONFIG_PATH
    indicators_path = settings.INDICATORS_CONFIG_PATH

    if trading_path.exists():
        with open(trading_path, "r") as f:
            config["trading"] = yaml.safe_load(f)

    if indicators_path.exists():
        with open(indicators_path, "r") as f:
            config["indicators"] = yaml.safe_load(f)

    return config


# ─── Data Upload Endpoints ─────────────────────────────────

class DataFileOut(Schema):
    symbol: str
    filename: str
    rows: int
    columns: List[str]


@api.post("/data/upload/", response=DataFileOut)
def upload_csv(request, symbol: str, file: UploadedFile = File(...)):
    """Upload a CSV file for a trading symbol."""
    import pandas as pd
    import io

    content = file.read().decode("utf-8")
    df = pd.read_csv(io.StringIO(content))

    if df.empty:
        return api.create_response(request, {"message": "CSV file is empty"}, status=400)

    clean_name = symbol.replace(":", "_").replace("/", "_")
    dest = DATA_DIR / f"{clean_name}.csv"
    dest.write_text(content, encoding="utf-8")

    return {
        "symbol": symbol,
        "filename": f"{clean_name}.csv",
        "rows": len(df),
        "columns": list(df.columns),
    }


@api.post("/data/upload-multi/")
def upload_multiple_csvs(request):
    """Upload multiple CSV files. Each file name (without .csv) becomes the symbol."""
    import pandas as pd
    import io

    files = request.FILES.getlist("files")
    if not files:
        return api.create_response(request, {"message": "No files provided"}, status=400)

    results = []
    for f in files:
        content = f.read().decode("utf-8")
        df = pd.read_csv(io.StringIO(content))
        fname = f.name
        if fname.lower().endswith(".csv"):
            fname = fname[:-4]
        clean_name = fname.replace(":", "_").replace("/", "_")
        dest = DATA_DIR / f"{clean_name}.csv"
        dest.write_text(content, encoding="utf-8")
        results.append({
            "symbol": fname,
            "filename": f"{clean_name}.csv",
            "rows": len(df),
            "columns": list(df.columns),
        })

    return results


@api.get("/data/files/")
def list_data_files(request):
    """List all uploaded CSV data files."""
    files = []
    for p in sorted(DATA_DIR.glob("*.csv")):
        files.append({
            "filename": p.name,
            "symbol": p.stem,
            "size_kb": round(p.stat().st_size / 1024, 1),
        })
    return files


@api.delete("/data/files/{filename}/", response=MessageOut)
def delete_data_file(request, filename: str):
    """Delete an uploaded data file."""
    target = DATA_DIR / filename
    if target.exists() and target.suffix == ".csv":
        target.unlink()
        return {"message": f"Deleted {filename}"}
    return api.create_response(request, {"message": "File not found"}, status=404)


# ─── Fyers options chain + trading YAML symbols ─────────────

def _fyers_client():
    try:
        from engine.data.fyers_provider import FyersData, is_available, normalize_options_chain

        if not is_available():
            return None, None
        return FyersData(), normalize_options_chain
    except Exception:  # noqa: BLE001
        return None, None


@api.get("/fyers/options-chain/")
def fyers_options_chain(
    request,
    symbol: str,
    timestamp: Optional[str] = None,
    strikecount: Optional[int] = None,
):
    """
    Proxy Fyers ``/indus/data/v1/options-chain`` using engine ``FyersData`` auth.
    Returns normalized ``strikes`` rows for the option-chain UI.
    """
    client, normalize_fn = _fyers_client()
    if client is None or normalize_fn is None:
        return api.create_response(
            request,
            {"ok": False, "error": "Fyers is not configured (engine/config/fyers_config.yaml)."},
            status=503,
        )
    ts = (timestamp or "").strip() or None
    try:
        raw = client.fetch_options_chain_raw(symbol, timestamp=ts, strikecount=strikecount)
    except Exception as exc:  # noqa: BLE001
        return api.create_response(
            request,
            {"ok": False, "error": str(exc)},
            status=502,
        )
    normalized = normalize_fn(raw)
    normalized["raw_code"] = raw.get("code")
    return normalized


@api.post("/trading-config/symbols/", response=dict)
def persist_trading_symbols(request, payload: TradingSymbolsApplyIn):
    """Write selected put/call symbols into trading YAML (platform + ``trading_system`` when present)."""
    err = _validate_option_leg(payload.put_symbol, "put")
    if err:
        return api.create_response(request, {"ok": False, "error": err}, status=400)
    err = _validate_option_leg(payload.call_symbol, "call")
    if err:
        return api.create_response(request, {"ok": False, "error": err}, status=400)

    targets = [p for p in _trading_yaml_write_targets() if p.exists()]
    if not targets:
        return api.create_response(
            request,
            {"ok": False, "error": f"Trading config not found: {settings.TRADING_CONFIG_PATH}"},
            status=404,
        )

    put = payload.put_symbol.strip()
    call = payload.call_symbol.strip()
    lot_put = int(payload.lot_put)
    lot_call = int(payload.lot_call)
    written: List[str] = []
    for path in targets:
        _write_symbols_to_trading_yaml(path, put, call, lot_put, lot_call)
        written.append(str(path))

    return {
        "ok": True,
        "symbols": [put, call],
        "paths": written,
    }


# ─── Backtest Endpoints ────────────────────────────────────

@api.post("/backtest/run/", response=BacktestRunOut)
def start_backtest(request, payload: BacktestRunIn):
    config_snapshot = {}

    if payload.config_id:
        try:
            tc = TradingConfig.objects.get(pk=payload.config_id)
            config_snapshot = tc.config_json
        except TradingConfig.DoesNotExist:
            pass

    if payload.config_override:
        config_snapshot.update(payload.config_override)

    if not config_snapshot:
        trading_path = settings.TRADING_CONFIG_PATH
        if trading_path.exists():
            with open(trading_path, "r") as f:
                config_snapshot = yaml.safe_load(f)

    run = BacktestRun.objects.create(
        config_id=payload.config_id,
        config_snapshot=config_snapshot,
        symbols=payload.symbols,
        start_date=payload.start_date,
        end_date=payload.end_date,
        resolution=payload.resolution,
        status="pending",
        control="run",
    )

    from .tasks import run_backtest_task
    task = run_backtest_task.delay(run.id)
    if task and task.id:
        run.celery_task_id = task.id
        run.save(update_fields=["celery_task_id"])

    run.refresh_from_db()
    return run


@api.get("/backtest/runs/", response=List[BacktestRunOut])
def list_backtest_runs(request):
    return list(BacktestRun.objects.all())


@api.get("/backtest/runs/{run_id}/", response=BacktestDetailOut)
def get_backtest_detail(request, run_id: int):
    run = BacktestRun.objects.get(pk=run_id)
    trades = list(run.trades.all())
    return {"run": run, "trades": trades}


@api.get("/backtest/runs/{run_id}/status/")
def get_backtest_status(request, run_id: int):
    """Poll endpoint for backtest progress (fallback when WS unavailable)."""
    run = BacktestRun.objects.get(pk=run_id)
    result = {
        "id": run.id,
        "status": run.status,
        "processed_bars": run.processed_bars,
        "total_bars": run.total_bars,
        "progress_pct": run.progress_pct,
        "error_message": run.error_message,
    }
    if run.status == "completed":
        result["summary"] = run.summary_json
        result["metrics"] = run.metrics_json
        result["trade_count"] = run.trades.count()
    return result


@api.delete("/backtest/runs/{run_id}/", response=MessageOut)
def delete_backtest_run(request, run_id: int):
    BacktestRun.objects.filter(pk=run_id).delete()
    try:
        from .bar_store import delete_run as _delete_bars
        _delete_bars(run_id)
    except Exception:  # noqa: BLE001
        pass
    return {"message": "Deleted"}


@api.get("/backtest/runs/{run_id}/bars/")
def get_backtest_bars(request, run_id: int, symbol: str):
    """Return cached OHLC bars for a (run, symbol) - used to seed the chart on
    page reload. Returns ``{"bars": [{time, open, high, low, close, volume}]}``
    sorted by ascending time.
    """
    from .bar_store import read_bars
    BacktestRun.objects.only("pk").get(pk=run_id)
    return {"symbol": symbol, "bars": read_bars(run_id, symbol)}


def _set_backtest_control(run_id: int, control: str) -> BacktestRun:
    run = BacktestRun.objects.get(pk=run_id)
    run.control = control
    run.save(update_fields=["control"])
    return run


@api.post("/backtest/runs/{run_id}/pause/", response=BacktestRunOut)
def pause_backtest(request, run_id: int):
    return _set_backtest_control(run_id, "pause")


@api.post("/backtest/runs/{run_id}/resume/", response=BacktestRunOut)
def resume_backtest(request, run_id: int):
    return _set_backtest_control(run_id, "run")


@api.post("/backtest/runs/{run_id}/stop/", response=BacktestRunOut)
def stop_backtest(request, run_id: int):
    run = _set_backtest_control(run_id, "stop")
    if run.celery_task_id:
        # Soft stop via the control flag; ask Celery to revoke as a backstop if
        # the task is stuck in a blocking call.
        try:
            from web_platform.celery import app as celery_app
            celery_app.control.revoke(run.celery_task_id, terminate=False)
        except Exception:  # noqa: BLE001
            pass
    return run


# ─── Live Trading Endpoints ────────────────────────────────

@api.post("/live/start/", response=LiveSessionOut)
def start_live_session(request, payload: LiveSessionIn):
    config_snapshot = {}
    if payload.config_id:
        try:
            tc = TradingConfig.objects.get(pk=payload.config_id)
            config_snapshot = tc.config_json or {}
        except TradingConfig.DoesNotExist:
            pass

    if not config_snapshot:
        trading_path = settings.TRADING_CONFIG_PATH
        if trading_path.exists():
            with open(trading_path, "r") as f:
                config_snapshot = yaml.safe_load(f) or {}

    if not config_snapshot:
        return api.create_response(
            request,
            {"message": "No trading config available. Save a preset or provide trading_config.yaml."},
            status=400,
        )

    session = LiveSession.objects.create(
        config_id=payload.config_id,
        config_snapshot=config_snapshot,
        symbols=payload.symbols,
        status="idle",
        control="run",
    )

    from .tasks import run_live_task
    task = run_live_task.delay(session.id)
    if task and task.id:
        session.celery_task_id = task.id
        session.save(update_fields=["celery_task_id"])

    session.refresh_from_db()
    return session


def _set_live_control(session_id: int, control: str) -> LiveSession:
    session = LiveSession.objects.get(pk=session_id)
    session.control = control
    session.save(update_fields=["control"])
    return session


@api.post("/live/pause/{session_id}/", response=LiveSessionOut)
def pause_live_session(request, session_id: int):
    return _set_live_control(session_id, "pause")


@api.post("/live/resume/{session_id}/", response=LiveSessionOut)
def resume_live_session(request, session_id: int):
    return _set_live_control(session_id, "run")


@api.post("/live/stop/{session_id}/", response=LiveSessionOut)
def stop_live_session(request, session_id: int):
    session = _set_live_control(session_id, "stop")
    if session.celery_task_id:
        try:
            from web_platform.celery import app as celery_app
            celery_app.control.revoke(session.celery_task_id, terminate=False)
        except Exception:  # noqa: BLE001
            pass
    return session


@api.get("/live/sessions/", response=List[LiveSessionOut])
def list_live_sessions(request):
    return list(LiveSession.objects.all())


@api.get("/live/sessions/{session_id}/", response=LiveSessionDetailOut)
def get_live_session(request, session_id: int):
    session = LiveSession.objects.get(pk=session_id)
    trades = list(session.trades.all().values(
        "id", "order_id", "symbol", "trade_type", "entry_price", "exit_price",
        "quantity", "pnl", "return_pct", "total_charges", "net_profit",
        "is_paper", "duration", "entry_reason", "exit_reason",
        "entry_time", "exit_time",
    ))
    return {"session": session, "trades": trades}


@api.delete("/live/sessions/{session_id}/", response=MessageOut)
def delete_live_session(request, session_id: int):
    LiveSession.objects.filter(pk=session_id).delete()
    try:
        from .bar_store import delete_run as _delete_bars
        _delete_bars(session_id, kind="live")
    except Exception:  # noqa: BLE001
        pass
    return {"message": "Deleted"}


@api.get("/live/sessions/{session_id}/bars/")
def get_live_bars(request, session_id: int, symbol: str):
    """Return cached OHLC bars for a (session, symbol) - used to seed the chart
    on page reload."""
    from .bar_store import read_bars
    LiveSession.objects.only("pk").get(pk=session_id)
    return {"symbol": symbol, "bars": read_bars(session_id, symbol, kind="live")}


# ─── Indicators Endpoint ───────────────────────────────────

@api.get("/indicators/", response=List[IndicatorOut])
def list_indicators(request):
    indicators_path = settings.INDICATORS_CONFIG_PATH
    if not indicators_path.exists():
        return []

    with open(indicators_path, "r") as f:
        conf = yaml.safe_load(f)

    result = []
    for name, data in conf.get("indicators", {}).items():
        result.append({
            "name": name,
            "enabled": data.get("enabled", False),
            "weight": data.get("weight", 1.0),
            "module": data.get("module", ""),
            "params": data.get("params", {}),
        })
    return result
