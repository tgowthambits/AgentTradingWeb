"""
Celery tasks for backtesting.
"""

import logging
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any
from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def run_backtest(self, session_id: str):
    """
    Run a backtest session asynchronously.

    This task:
    1. Loads the strategy configuration
    2. Fetches historical data
    3. Runs the backtest engine
    4. Saves results to database
    5. Sends progress updates via WebSocket
    """
    from backtest.models import (
        BacktestSession,
        BacktestResult,
        BacktestTrade,
        BacktestEquityPoint,
    )
    from trading.services.backtest_engine import BacktestEngine

    try:
        # Get session
        session = BacktestSession.objects.get(id=session_id)
        session.status = "running"
        session.started_at = timezone.now()
        session.celery_task_id = self.request.id
        session.save()

        # Send initial status
        send_backtest_update(
            session_id,
            {"status": "running", "progress": 0, "message": "Starting backtest..."},
        )

        # Initialize backtest engine
        engine = BacktestEngine(
            strategy=session.strategy,
            start_date=session.start_date,
            end_date=session.end_date,
            initial_capital=float(session.initial_capital),
            entry_slippage=float(session.entry_slippage),
            exit_slippage=float(session.exit_slippage),
            config=session.config_snapshot,
        )

        # Run backtest with progress callback
        def progress_callback(current_bar, total_bars, equity, trade=None):
            progress = int((current_bar / total_bars) * 100) if total_bars > 0 else 0

            # Update session progress
            session.progress = progress
            session.current_bar = current_bar
            session.total_bars = total_bars
            session.save(update_fields=["progress", "current_bar", "total_bars"])

            # Send progress update
            send_backtest_update(
                session_id,
                {
                    "status": "running",
                    "progress": progress,
                    "current_bar": current_bar,
                    "total_bars": total_bars,
                    "equity": equity,
                },
            )

            # Send trade update if there's a new trade
            if trade:
                send_backtest_trade(session_id, trade)

        results = engine.run(progress_callback=progress_callback)

        # Save results
        save_backtest_results(session, results)

        # Update session status
        session.status = "completed"
        session.progress = 100
        session.completed_at = timezone.now()
        session.save()

        # Send completion notification
        send_backtest_update(
            session_id,
            {
                "status": "completed",
                "progress": 100,
                "message": "Backtest completed successfully",
            },
        )

        return {"status": "completed", "session_id": session_id}

    except Exception as e:
        logger.exception(f"Backtest failed for session {session_id}")

        try:
            session = BacktestSession.objects.get(id=session_id)
            session.status = "failed"
            session.error_message = str(e)
            session.save()
        except Exception:
            pass

        # Send error notification
        send_backtest_error(session_id, str(e))

        raise


def save_backtest_results(session, results: Dict[str, Any]):
    """Save backtest results to database."""
    from backtest.models import BacktestResult, BacktestTrade, BacktestEquityPoint

    # Create result summary
    BacktestResult.objects.create(
        session=session,
        final_capital=Decimal(str(results.get("final_capital", 0))),
        total_pnl=Decimal(str(results.get("total_pnl", 0))),
        total_return_pct=Decimal(str(results.get("total_return_pct", 0))),
        total_trades=results.get("total_trades", 0),
        winning_trades=results.get("winning_trades", 0),
        losing_trades=results.get("losing_trades", 0),
        win_rate=Decimal(str(results.get("win_rate", 0))),
        gross_profit=Decimal(str(results.get("gross_profit", 0))),
        gross_loss=Decimal(str(results.get("gross_loss", 0))),
        avg_win=Decimal(str(results.get("avg_win", 0))),
        avg_loss=Decimal(str(results.get("avg_loss", 0))),
        largest_win=Decimal(str(results.get("largest_win", 0))),
        largest_loss=Decimal(str(results.get("largest_loss", 0))),
        profit_factor=Decimal(str(results.get("profit_factor", 0))),
        sharpe_ratio=Decimal(str(results.get("sharpe_ratio", 0))),
        sortino_ratio=Decimal(str(results.get("sortino_ratio", 0))),
        max_drawdown=Decimal(str(results.get("max_drawdown", 0))),
        max_drawdown_pct=Decimal(str(results.get("max_drawdown_pct", 0))),
        calmar_ratio=Decimal(str(results.get("calmar_ratio", 0))),
        avg_hold_time_seconds=results.get("avg_hold_time_seconds", 0),
        max_consecutive_wins=results.get("max_consecutive_wins", 0),
        max_consecutive_losses=results.get("max_consecutive_losses", 0),
        equity_curve=results.get("equity_curve", []),
        per_symbol_stats=results.get("per_symbol_stats", {}),
        per_indicator_stats=results.get("per_indicator_stats", {}),
        exit_reason_breakdown=results.get("exit_reason_breakdown", {}),
    )

    # Save trades
    trades = results.get("trades", [])
    for i, trade in enumerate(trades):
        BacktestTrade.objects.create(
            session=session,
            trade_number=i + 1,
            symbol=trade["symbol"],
            trade_type=trade["trade_type"],
            entry_price=Decimal(str(trade["entry_price"])),
            entry_quantity=trade["entry_quantity"],
            entry_time=trade["entry_time"],
            entry_bar=trade.get("entry_bar", 0),
            exit_price=Decimal(str(trade["exit_price"])),
            exit_quantity=trade["exit_quantity"],
            exit_time=trade["exit_time"],
            exit_bar=trade.get("exit_bar", 0),
            exit_reason=trade["exit_reason"],
            gross_pnl=Decimal(str(trade["gross_pnl"])),
            slippage=Decimal(str(trade.get("slippage", 0))),
            commission=Decimal(str(trade.get("commission", 0))),
            net_pnl=Decimal(str(trade["net_pnl"])),
            pnl_percentage=Decimal(str(trade["pnl_percentage"])),
            capital_after_trade=Decimal(str(trade.get("capital_after_trade", 0))),
            entry_signals=trade.get("entry_signals", {}),
        )

    # Save equity points (sample to reduce storage)
    equity_curve = results.get("equity_curve", [])
    sample_rate = max(1, len(equity_curve) // 1000)  # Max 1000 points

    for i, point in enumerate(equity_curve):
        if i % sample_rate == 0:
            BacktestEquityPoint.objects.create(
                session=session,
                timestamp=point["timestamp"],
                bar_index=point.get("bar_index", i),
                equity=Decimal(str(point["equity"])),
                drawdown=Decimal(str(point.get("drawdown", 0))),
                drawdown_pct=Decimal(str(point.get("drawdown_pct", 0))),
                open_positions=point.get("open_positions", 0),
                unrealized_pnl=Decimal(str(point.get("unrealized_pnl", 0))),
            )


def send_backtest_update(session_id: str, data: Dict[str, Any]):
    """Send backtest progress update via WebSocket."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"backtest_{session_id}", {"type": "backtest_progress", "data": data}
    )


def send_backtest_trade(session_id: str, trade: Dict[str, Any]):
    """Send backtest trade update via WebSocket."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"backtest_{session_id}", {"type": "backtest_trade", "data": trade}
    )


def send_backtest_error(session_id: str, error: str):
    """Send backtest error via WebSocket."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"backtest_{session_id}", {"type": "backtest_error", "data": {"error": error}}
    )


@shared_task
def cleanup_old_backtests(days: int = 30):
    """Clean up backtest sessions older than specified days."""
    from backtest.models import BacktestSession
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(days=days)
    old_sessions = BacktestSession.objects.filter(
        created_at__lt=cutoff, status__in=["completed", "failed", "cancelled"]
    )

    count = old_sessions.count()
    old_sessions.delete()

    logger.info(f"Cleaned up {count} old backtest sessions")
    return {"deleted": count}
