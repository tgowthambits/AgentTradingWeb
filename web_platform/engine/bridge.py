"""
Bridge between Django views/tasks and the standalone trading engine.

Provides factory functions that create and configure engine instances
using the local engine package (no external dependencies).
"""
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

import pandas as pd

from engine.core.trading_engine import TradingEngine
from engine.core.indicator_loader import IndicatorLoader
from engine.data.data_loader import DataLoader, BacktestDataGenerator
from engine.core.signal_aggregator import SignalAggregator

ENGINE_DIR = Path(__file__).resolve().parent
DEFAULT_INDICATORS_CONFIG = str(ENGINE_DIR / "config" / "indicators_config.yaml")
DEFAULT_TRADING_CONFIG = str(ENGINE_DIR / "config" / "trading_config.yaml")

logger = logging.getLogger("engine.bridge")


def build_engine(config: Dict[str, Any]) -> TradingEngine:
    """Create a TradingEngine from a config dict."""
    aggregation_strategy = config.get("aggregation_strategy", "weighted")
    min_agreement = config.get("min_agreement", 0.5)

    engine = TradingEngine(
        aggregation_strategy=aggregation_strategy,
        config=config,
        min_agreement=min_agreement,
    )
    return engine


def load_indicators_into_engine(engine: TradingEngine, config: Dict[str, Any]):
    """Load indicators from a config dict into the engine's indicator manager."""
    indicators_conf = config.get("indicators", {})
    for name, ind_cfg in indicators_conf.items():
        if not ind_cfg.get("enabled", False):
            continue
        try:
            loader = IndicatorLoader(
                config_path=DEFAULT_INDICATORS_CONFIG,
                trading_config_path=DEFAULT_TRADING_CONFIG,
                auto_sync=False,
            )
            loaded = loader.load_indicators(verbose=False)
            for ind in loaded:
                engine.indicator_manager.register_indicator(ind)
            break
        except Exception as e:
            logger.warning("Indicator load via IndicatorLoader failed: %s", e)
            break


def load_indicators_from_config_paths(engine: TradingEngine,
                                       indicators_config_path: str,
                                       trading_config_path: str):
    """Load indicators using file-based config paths."""
    try:
        loader = IndicatorLoader(
            config_path=indicators_config_path,
            trading_config_path=trading_config_path,
            auto_sync=False,
        )
        loaded = loader.load_indicators(verbose=False)
        for ind in loaded:
            engine.indicator_manager.register_indicator(ind)
        logger.info("Loaded %d indicators", len(loaded))
    except Exception as e:
        logger.error("Failed to load indicators: %s", e)


def create_backtest_generators(
    symbols: List[str],
    start_date: str,
    end_date: str,
    resolution: str,
    data_dir: str = None,
    dataframes: Dict[str, pd.DataFrame] = None,
) -> Dict[str, BacktestDataGenerator]:
    """
    Create BacktestDataGenerator instances for each symbol.

    Data resolution order:
      1. dataframes dict (if provided)
      2. CSV file in data_dir
      3. Fyers API fetch (same as original trading_system)
    """
    generators = {}

    for symbol in symbols:
        try:
            df = None

            if dataframes and symbol in dataframes:
                df = dataframes[symbol]

            if df is None and data_dir:
                for name in [symbol, symbol.replace(":", "_").replace("/", "_")]:
                    csv_path = Path(data_dir) / f"{name}.csv"
                    if csv_path.exists():
                        loader = DataLoader()
                        df = loader.load_from_csv(str(csv_path))
                        break

            if df is not None and not df.empty:
                gen = BacktestDataGenerator(symbol=symbol, data=df)
            else:
                gen = BacktestDataGenerator(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    resolution=resolution,
                )

            generators[symbol] = gen
            logger.info("Created generator for %s with %d bars", symbol, len(gen.full_data))
        except Exception as e:
            logger.error("Failed to create generator for %s: %s", symbol, e)

    return generators


def run_backtest_iteration(
    engine: TradingEngine,
    generators: Dict[str, BacktestDataGenerator],
    config: Dict[str, Any],
    allow_buy: bool = True,
    allow_sell: bool = False,
) -> List[Dict[str, Any]]:
    """
    Run one backtest iteration across all symbols.

    Returns list of result dicts (one per symbol).
    """
    results = []
    data_loader = DataLoader()
    try:
        lookback = int((config.get("backtest") or {}).get("lookback_bars") or 0)
    except (TypeError, ValueError):
        lookback = 0

    for symbol, gen in generators.items():
        df = gen.next_slice()
        if df is None or df.empty:
            continue

        df = data_loader.prepare_for_indicators(df)
        if lookback > 0 and len(df) > lookback:
            df = df.tail(lookback)
        result = engine.analyze_symbol(df, symbol, verbose=False)

        current_price = df["close"].iloc[-1]
        # Timestamp of the bar we just processed. Depending on data source the
        # row may carry an epoch int ("time"/"Time"), an arrow object ("date"),
        # a pre-formatted string ("datetime"), or a DatetimeIndex. We try each
        # in order of precision and let the task layer normalise it.
        current_time = None
        for col in ("datetime", "date", "timestamp", "time"):
            if col in df.columns:
                val = df[col].iloc[-1]
                if val is not None and not (isinstance(val, float) and pd.isna(val)):
                    current_time = val
                    break
        if current_time is None and isinstance(df.index, pd.DatetimeIndex):
            current_time = df.index[-1]

        last = df.iloc[-1]
        current_bar = {
            "open": float(last.get("open", current_price)),
            "high": float(last.get("high", current_price)),
            "low": float(last.get("low", current_price)),
            "close": float(current_price),
            "volume": float(last.get("volume", 0) or 0),
            "time": current_time,
        }

        result["symbol"] = symbol
        result["current_price"] = current_price
        result["current_time"] = current_time
        result["current_bar"] = current_bar

        quantity = _get_quantity(engine, config, symbol, current_price)
        engine.execute_trading_decision(result, quantity=quantity, df=df)

        results.append(result)

    return results


def _get_quantity(engine, config, symbol, price):
    """Get trade quantity for a symbol."""
    lot_sizes = config.get("lot_sizes", config.get("trading", {}).get("lot_sizes", {}))
    default_lot = config.get("trading", {}).get("default_lot_size", 20)
    return lot_sizes.get(symbol, default_lot)


def get_backtest_summary(engine: TradingEngine) -> Dict[str, Any]:
    """Extract a JSON-serializable summary from the engine after backtest."""
    summary = engine.get_summary()
    closed_orders = engine.get_closed_orders()

    trades = []
    if not closed_orders.empty:
        for _, row in closed_orders.iterrows():
            trade_type = row["type"]
            entry_price = float(row["entry_price"])
            exit_price = float(row["exit_price"])

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

            trades.append({
                "order_id": int(row["order_id"]),
                "symbol": str(row["symbol"]),
                "type": str(trade_type),
                "entry_price": entry_price,
                "exit_price": exit_price,
                "quantity": int(row["quantity"]),
                "pnl": float(row["pnl"]),
                "return_pct": round(return_pct, 2),
                "total_charges": float(row.get("total_charges", 0.0)),
                "net_profit": float(row.get("net_profit", row["pnl"])),
                "is_paper": bool(row.get("paper_trade", False)),
                "duration": duration,
                "entry_reason": str(row.get("entry_reason", "N/A")),
                "exit_reason": str(row.get("exit_reason", "N/A")),
                "entry_time": str(entry_time) if pd.notna(entry_time) else None,
                "exit_time": str(exit_time) if pd.notna(exit_time) else None,
            })

    initial_capital = engine.initial_capital

    # Include paper trades in backtest stats - in a simulated run there is no
    # meaningful distinction between "paper" and "real" from the user's point
    # of view; the paper-mode gate is a live-trading safety mechanic.
    total_pnl_all = sum(t["pnl"] for t in trades)
    final_capital = initial_capital + total_pnl_all
    returns_pct = (total_pnl_all / initial_capital * 100) if initial_capital > 0 else 0

    winning = [t for t in trades if t["pnl"] > 0]
    losing = [t for t in trades if t["pnl"] < 0]
    win_rate = len(winning) / len(trades) if trades else 0

    avg_win = sum(t["pnl"] for t in winning) / len(winning) if winning else 0
    avg_loss = sum(t["pnl"] for t in losing) / len(losing) if losing else 0
    max_win = max((t["pnl"] for t in trades), default=0)
    max_loss = min((t["pnl"] for t in trades), default=0)

    gross_profit = sum(t["pnl"] for t in winning)
    gross_loss = abs(sum(t["pnl"] for t in losing))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    if profit_factor == float("inf"):
        profit_factor = 999.99

    expectancy = (win_rate * avg_win) - ((1 - win_rate) * abs(avg_loss))

    return {
        "summary": {
            "initial_capital": initial_capital,
            "final_capital": round(final_capital, 2),
            "total_pnl": round(total_pnl_all, 2),
            "returns_pct": round(returns_pct, 2),
        },
        "metrics": {
            "total_trades": len(trades),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": round(win_rate * 100, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "max_win": round(max_win, 2),
            "max_loss": round(max_loss, 2),
            "profit_factor": round(profit_factor, 2),
            "expectancy": round(expectancy, 2),
            "total_charges": round(summary.get("total_charges", 0), 2),
        },
        "trades": trades,
    }
