"""
Backtest models for tracking backtest sessions and results.
"""

from django.db import models
from django.conf import settings
import uuid


class BacktestSession(models.Model):
    """A backtesting session."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="backtest_sessions",
    )
    strategy = models.ForeignKey(
        "trading.Strategy", on_delete=models.CASCADE, related_name="backtest_sessions"
    )

    name = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)

    # Backtest configuration
    start_date = models.DateField()
    end_date = models.DateField()
    initial_capital = models.DecimalField(max_digits=15, decimal_places=2)

    # Configuration snapshot
    config_snapshot = models.JSONField(default=dict)

    # Execution settings
    SPEED_CHOICES = [
        ("instant", "Instant"),
        ("fast", "Fast"),
        ("normal", "Normal"),
        ("slow", "Slow"),
    ]
    speed = models.CharField(max_length=10, choices=SPEED_CHOICES, default="fast")

    entry_slippage = models.DecimalField(max_digits=5, decimal_places=4, default=0.0005)
    exit_slippage = models.DecimalField(max_digits=5, decimal_places=4, default=0.0005)

    # Status tracking
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("paused", "Paused"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")

    # Progress tracking
    progress = models.IntegerField(default=0)  # 0-100
    current_bar = models.IntegerField(default=0)
    total_bars = models.IntegerField(default=0)

    # Celery task tracking
    celery_task_id = models.CharField(max_length=100, blank=True)

    # Error tracking
    error_message = models.TextField(blank=True)

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "backtest_sessions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Backtest {self.id} - {self.strategy.name}"


class BacktestResult(models.Model):
    """Summary results of a backtest session."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.OneToOneField(
        BacktestSession, on_delete=models.CASCADE, related_name="result"
    )

    # Capital metrics
    final_capital = models.DecimalField(max_digits=15, decimal_places=2)
    total_pnl = models.DecimalField(max_digits=15, decimal_places=2)
    total_return_pct = models.DecimalField(max_digits=10, decimal_places=4)

    # Trade metrics
    total_trades = models.IntegerField(default=0)
    winning_trades = models.IntegerField(default=0)
    losing_trades = models.IntegerField(default=0)
    win_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # P&L metrics
    gross_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    gross_loss = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    avg_win = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    avg_loss = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    largest_win = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    largest_loss = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Risk metrics
    profit_factor = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    sharpe_ratio = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    sortino_ratio = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    max_drawdown = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    max_drawdown_pct = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    calmar_ratio = models.DecimalField(max_digits=10, decimal_places=4, default=0)

    # Time metrics
    avg_hold_time_seconds = models.IntegerField(default=0)
    avg_bars_in_trade = models.IntegerField(default=0)

    # Consecutive metrics
    max_consecutive_wins = models.IntegerField(default=0)
    max_consecutive_losses = models.IntegerField(default=0)

    # Detailed data (stored as JSON)
    equity_curve = models.JSONField(default=list)  # [{timestamp, equity, drawdown}]
    daily_returns = models.JSONField(default=list)  # [{date, return}]
    per_symbol_stats = models.JSONField(default=dict)
    per_indicator_stats = models.JSONField(default=dict)
    exit_reason_breakdown = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "backtest_results"

    def __str__(self):
        return f"Result for {self.session}"


class BacktestTrade(models.Model):
    """Individual trades from a backtest session."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        BacktestSession, on_delete=models.CASCADE, related_name="trades"
    )

    # Trade number in sequence
    trade_number = models.IntegerField()

    symbol = models.CharField(max_length=50)

    TRADE_TYPES = [
        ("LONG", "Long"),
        ("SHORT", "Short"),
    ]
    trade_type = models.CharField(max_length=5, choices=TRADE_TYPES)

    # Entry
    entry_price = models.DecimalField(max_digits=15, decimal_places=4)
    entry_quantity = models.IntegerField()
    entry_time = models.DateTimeField()
    entry_bar = models.IntegerField()

    # Exit
    exit_price = models.DecimalField(max_digits=15, decimal_places=4)
    exit_quantity = models.IntegerField()
    exit_time = models.DateTimeField()
    exit_bar = models.IntegerField()

    EXIT_REASONS = [
        ("signal", "Signal Exit"),
        ("stop_loss", "Stop Loss"),
        ("trailing_stop", "Trailing Stop"),
        ("profit_target", "Profit Target"),
        ("time_exit", "Time Exit"),
        ("manual", "Manual Exit"),
        ("circuit_breaker", "Circuit Breaker"),
        ("microstructure", "Microstructure Reversal"),
        ("end_of_backtest", "End of Backtest"),
    ]
    exit_reason = models.CharField(max_length=20, choices=EXIT_REASONS)

    # P&L
    gross_pnl = models.DecimalField(max_digits=15, decimal_places=2)
    slippage = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_pnl = models.DecimalField(max_digits=15, decimal_places=2)
    pnl_percentage = models.DecimalField(max_digits=10, decimal_places=4)

    # Trade metrics
    max_favorable_excursion = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )
    max_adverse_excursion = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )
    hold_duration_seconds = models.IntegerField(default=0)
    bars_held = models.IntegerField(default=0)

    # Running capital after this trade
    capital_after_trade = models.DecimalField(max_digits=15, decimal_places=2)

    # Signals at entry
    entry_signals = models.JSONField(default=dict)

    class Meta:
        db_table = "backtest_trades"
        ordering = ["trade_number"]
        unique_together = ["session", "trade_number"]

    def __str__(self):
        return f"Trade {self.trade_number}: {self.symbol} {self.trade_type}"


class BacktestEquityPoint(models.Model):
    """Equity curve data points for charting."""

    id = models.BigAutoField(primary_key=True)
    session = models.ForeignKey(
        BacktestSession, on_delete=models.CASCADE, related_name="equity_points"
    )

    timestamp = models.DateTimeField()
    bar_index = models.IntegerField()

    equity = models.DecimalField(max_digits=15, decimal_places=2)
    drawdown = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    drawdown_pct = models.DecimalField(max_digits=10, decimal_places=4, default=0)

    # Current state
    open_positions = models.IntegerField(default=0)
    unrealized_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        db_table = "backtest_equity_points"
        ordering = ["timestamp"]
        indexes = [
            models.Index(fields=["session", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.session} @ {self.timestamp}: {self.equity}"
