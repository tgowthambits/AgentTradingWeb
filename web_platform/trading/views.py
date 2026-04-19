import yaml
from pathlib import Path

from django.shortcuts import render, get_object_or_404
from django.conf import settings

from .models import TradingConfig, BacktestRun, LiveSession


def _load_default_config():
    """Load the default YAML config as a dict."""
    config = {}
    if settings.TRADING_CONFIG_PATH.exists():
        with open(settings.TRADING_CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f) or {}
    return config


def _load_indicators_config():
    """Load the indicators config as a dict."""
    config = {}
    if settings.INDICATORS_CONFIG_PATH.exists():
        with open(settings.INDICATORS_CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f) or {}
    return config


def dashboard(request):
    recent_runs = BacktestRun.objects.all()[:5]
    active_sessions = LiveSession.objects.filter(status="running")
    configs_count = TradingConfig.objects.count()
    runs_count = BacktestRun.objects.count()

    return render(request, "pages/dashboard.html", {
        "recent_runs": recent_runs,
        "active_sessions": active_sessions,
        "configs_count": configs_count,
        "runs_count": runs_count,
    })


def backtest_page(request):
    config = _load_default_config()
    configs = TradingConfig.objects.all()
    indicators_config = _load_indicators_config()

    symbols = config.get("symbols", [])
    date_range = config.get("date_range", {})
    resolution = config.get("resolution", "1")
    indicators = config.get("indicators", {})

    data_dir = settings.BASE_DIR / "data"
    data_files = []
    if data_dir.exists():
        data_files = [
            {"name": f.stem, "filename": f.name, "size_kb": round(f.stat().st_size / 1024, 1)}
            for f in sorted(data_dir.glob("*.csv"))
        ]

    resolutions = [
        ("1S", "1 Second"), ("5S", "5 Seconds"), ("10S", "10 Seconds"),
        ("15S", "15 Seconds"), ("30S", "30 Seconds"),
        ("1", "1 Minute"), ("2", "2 Minutes"), ("3", "3 Minutes"),
        ("5", "5 Minutes"), ("10", "10 Minutes"), ("15", "15 Minutes"),
        ("30", "30 Minutes"), ("60", "1 Hour"), ("120", "2 Hours"),
        ("240", "4 Hours"), ("D", "Daily"),
    ]

    return render(request, "pages/backtest.html", {
        "config": config,
        "configs": configs,
        "symbols": symbols,
        "date_range": date_range,
        "resolution": resolution,
        "indicators": indicators,
        "indicators_config": indicators_config,
        "resolutions": resolutions,
        "data_files": data_files,
    })


def backtest_results_page(request):
    runs = BacktestRun.objects.all()
    return render(request, "pages/backtest_results.html", {
        "runs": runs,
    })


def backtest_detail_page(request, run_id):
    run = get_object_or_404(BacktestRun, pk=run_id)
    trades = run.trades.all()
    return render(request, "pages/backtest_detail.html", {
        "run": run,
        "trades": trades,
    })


def live_sessions_page(request):
    return render(request, "pages/live_sessions.html")


def live_session_detail_page(request, session_id):
    session = get_object_or_404(LiveSession, pk=session_id)
    trades = session.trades.all()
    return render(request, "pages/live_session_detail.html", {
        "session": session,
        "trades": trades,
    })


def live_trading_page(request):
    config = _load_default_config()
    configs = TradingConfig.objects.all()
    sessions = LiveSession.objects.all()[:10]

    symbols = config.get("symbols", [])
    resolutions = [
        ("1S", "1 Second"), ("5S", "5 Seconds"), ("10S", "10 Seconds"),
        ("30S", "30 Seconds"), ("1", "1 Minute"), ("5", "5 Minutes"),
        ("15", "15 Minutes"), ("30", "30 Minutes"),
    ]

    return render(request, "pages/live_trading.html", {
        "config": config,
        "configs": configs,
        "sessions": sessions,
        "symbols": symbols,
        "resolutions": resolutions,
    })


def config_page(request):
    config = _load_default_config()
    indicators_config = _load_indicators_config()
    saved_configs = TradingConfig.objects.all()

    return render(request, "pages/config.html", {
        "config": config,
        "indicators_config": indicators_config,
        "saved_configs": saved_configs,
    })
