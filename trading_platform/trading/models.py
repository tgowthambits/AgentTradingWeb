"""
Trading models for strategies, indicators, trades, orders, and positions.
"""

from django.db import models
from django.conf import settings
import uuid


class Indicator(models.Model):
    """Registry of available indicators."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # Module path for dynamic loading
    module_path = models.CharField(max_length=200)
    class_name = models.CharField(max_length=100)

    # Default configuration
    default_params = models.JSONField(default=dict)

    # Indicator type
    INDICATOR_TYPES = [
        ("trend", "Trend"),
        ("momentum", "Momentum"),
        ("volatility", "Volatility"),
        ("volume", "Volume"),
        ("statistical", "Statistical"),
        ("hft", "HFT"),
        ("custom", "Custom"),
    ]
    indicator_type = models.CharField(
        max_length=20, choices=INDICATOR_TYPES, default="custom"
    )

    # Supported signals
    supports_buy = models.BooleanField(default=True)
    supports_sell = models.BooleanField(default=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "indicators"
        ordering = ["name"]

    def __str__(self):
        return self.display_name


class Strategy(models.Model):
    """User-defined trading strategy."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="strategies"
    )

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # Strategy configuration (React Flow JSON)
    flow_config = models.JSONField(
        default=dict, help_text="React Flow node/edge configuration"
    )

    # Trading configuration
    symbols = models.JSONField(default=list, help_text="List of symbols to trade")
    lot_sizes = models.JSONField(default=dict, help_text="Symbol-specific lot sizes")

    # Indicator configuration
    indicators_config = models.JSONField(default=dict)

    # Signal aggregation
    AGGREGATION_STRATEGIES = [
        ("majority", "Majority Voting"),
        ("weighted", "Weighted Voting"),
        ("unanimous", "Unanimous Agreement"),
        ("conservative", "Conservative"),
        ("threshold", "Threshold-based"),
    ]
    aggregation_strategy = models.CharField(
        max_length=20, choices=AGGREGATION_STRATEGIES, default="weighted"
    )
    min_agreement = models.FloatField(default=0.6)

    # Trading settings
    allow_buy = models.BooleanField(default=True)
    allow_sell = models.BooleanField(default=False)
    default_quantity = models.IntegerField(default=1)

    # Risk management configuration
    risk_config = models.JSONField(default=dict)

    # Exit strategy configuration
    exit_config = models.JSONField(default=dict)

    # Status
    is_active = models.BooleanField(default=True)
    is_live = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "strategies"
        unique_together = ["user", "name"]
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.name} ({self.user.email})"


class TradingSession(models.Model):
    """A trading session (live or paper)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trading_sessions",
    )
    strategy = models.ForeignKey(
        Strategy, on_delete=models.CASCADE, related_name="trading_sessions"
    )

    SESSION_TYPES = [
        ("live", "Live Trading"),
        ("paper", "Paper Trading"),
    ]
    session_type = models.CharField(
        max_length=10, choices=SESSION_TYPES, default="paper"
    )

    # Session state
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("paused", "Paused"),
        ("stopped", "Stopped"),
        ("error", "Error"),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")

    # Capital tracking
    initial_capital = models.DecimalField(max_digits=15, decimal_places=2)
    current_capital = models.DecimalField(max_digits=15, decimal_places=2)

    # Session configuration snapshot
    config_snapshot = models.JSONField(default=dict)

    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "trading_sessions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Session {self.id} - {self.strategy.name}"


class Position(models.Model):
    """Current open positions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        TradingSession, on_delete=models.CASCADE, related_name="positions"
    )

    symbol = models.CharField(max_length=50)

    POSITION_TYPES = [
        ("LONG", "Long"),
        ("SHORT", "Short"),
    ]
    position_type = models.CharField(max_length=5, choices=POSITION_TYPES)

    # Position details
    entry_price = models.DecimalField(max_digits=15, decimal_places=4)
    current_price = models.DecimalField(max_digits=15, decimal_places=4)
    quantity = models.IntegerField()
    initial_quantity = models.IntegerField()

    # Stop loss and targets
    stop_loss = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True
    )
    trailing_stop = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True
    )

    # P&L tracking
    unrealized_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    max_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    max_loss = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Metadata
    entry_signal = models.CharField(max_length=50, blank=True)
    indicator_signals = models.JSONField(default=dict)

    opened_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "positions"
        ordering = ["-opened_at"]

    def __str__(self):
        return f"{self.symbol} {self.position_type} @ {self.entry_price}"


class Order(models.Model):
    """Order history."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        TradingSession, on_delete=models.CASCADE, related_name="orders"
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )

    # Broker order ID
    broker_order_id = models.CharField(max_length=100, blank=True)

    symbol = models.CharField(max_length=50)

    ORDER_TYPES = [
        ("MARKET", "Market"),
        ("LIMIT", "Limit"),
        ("STOP", "Stop"),
        ("STOP_LIMIT", "Stop Limit"),
    ]
    order_type = models.CharField(max_length=15, choices=ORDER_TYPES, default="MARKET")

    SIDES = [
        ("BUY", "Buy"),
        ("SELL", "Sell"),
    ]
    side = models.CharField(max_length=4, choices=SIDES)

    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    filled_price = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True
    )
    filled_quantity = models.IntegerField(default=0)

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("submitted", "Submitted"),
        ("partial", "Partially Filled"),
        ("filled", "Filled"),
        ("cancelled", "Cancelled"),
        ("rejected", "Rejected"),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")

    # Slippage
    slippage = models.DecimalField(max_digits=10, decimal_places=4, default=0)

    # Reason/Notes
    reason = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    filled_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.side} {self.quantity} {self.symbol} @ {self.price or 'MARKET'}"


class Trade(models.Model):
    """Completed trades (position entry + exit)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        TradingSession, on_delete=models.CASCADE, related_name="trades"
    )

    symbol = models.CharField(max_length=50)

    TRADE_TYPES = [
        ("LONG", "Long"),
        ("SHORT", "Short"),
    ]
    trade_type = models.CharField(max_length=5, choices=TRADE_TYPES)

    # Entry details
    entry_price = models.DecimalField(max_digits=15, decimal_places=4)
    entry_quantity = models.IntegerField()
    entry_time = models.DateTimeField()
    entry_order = models.ForeignKey(
        Order, on_delete=models.SET_NULL, null=True, related_name="entry_trades"
    )

    # Exit details
    exit_price = models.DecimalField(max_digits=15, decimal_places=4)
    exit_quantity = models.IntegerField()
    exit_time = models.DateTimeField()
    exit_order = models.ForeignKey(
        Order, on_delete=models.SET_NULL, null=True, related_name="exit_trades"
    )

    EXIT_REASONS = [
        ("signal", "Signal Exit"),
        ("stop_loss", "Stop Loss"),
        ("trailing_stop", "Trailing Stop"),
        ("profit_target", "Profit Target"),
        ("time_exit", "Time Exit"),
        ("manual", "Manual Exit"),
        ("circuit_breaker", "Circuit Breaker"),
        ("microstructure", "Microstructure Reversal"),
    ]
    exit_reason = models.CharField(max_length=20, choices=EXIT_REASONS)

    # P&L
    gross_pnl = models.DecimalField(max_digits=15, decimal_places=2)
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

    # Signals at entry
    entry_signals = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "trades"
        ordering = ["-exit_time"]

    def __str__(self):
        return f"{self.symbol} {self.trade_type} PnL: {self.net_pnl}"

    @property
    def is_winner(self):
        return self.net_pnl > 0


class Symbol(models.Model):
    """Tradeable symbols configuration."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    symbol = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    exchange = models.CharField(max_length=20, default="NSE")

    INSTRUMENT_TYPES = [
        ("EQ", "Equity"),
        ("FUT", "Futures"),
        ("OPT", "Options"),
        ("IDX", "Index"),
    ]
    instrument_type = models.CharField(
        max_length=3, choices=INSTRUMENT_TYPES, default="EQ"
    )

    # Trading settings
    lot_size = models.IntegerField(default=1)
    tick_size = models.DecimalField(max_digits=10, decimal_places=4, default=0.05)

    # Market hours
    market_open = models.TimeField(default="09:15:00")
    market_close = models.TimeField(default="15:30:00")

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "symbols"
        ordering = ["symbol"]

    def __str__(self):
        return self.symbol


class MarketData(models.Model):
    """Cached market data for symbols."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    symbol = models.ForeignKey(
        Symbol, on_delete=models.CASCADE, related_name="market_data"
    )

    timestamp = models.DateTimeField()

    open = models.DecimalField(max_digits=15, decimal_places=4)
    high = models.DecimalField(max_digits=15, decimal_places=4)
    low = models.DecimalField(max_digits=15, decimal_places=4)
    close = models.DecimalField(max_digits=15, decimal_places=4)
    volume = models.BigIntegerField()

    TIMEFRAMES = [
        ("1m", "1 Minute"),
        ("5m", "5 Minutes"),
        ("15m", "15 Minutes"),
        ("30m", "30 Minutes"),
        ("1h", "1 Hour"),
        ("1d", "1 Day"),
    ]
    timeframe = models.CharField(max_length=5, choices=TIMEFRAMES, default="5m")

    class Meta:
        db_table = "market_data"
        unique_together = ["symbol", "timestamp", "timeframe"]
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["symbol", "timestamp"]),
            models.Index(fields=["symbol", "timeframe", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.symbol} {self.timestamp} {self.timeframe}"
