from django.db import models
from django.utils import timezone


class TradingConfig(models.Model):
    name = models.CharField(max_length=200)
    config_json = models.JSONField()
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.name} ({'active' if self.is_active else 'inactive'})"


class BacktestRun(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("paused", "Paused"),
        ("stopping", "Stopping"),
        ("stopped", "Stopped"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    CONTROL_CHOICES = [
        ("run", "Run"),
        ("pause", "Pause"),
        ("stop", "Stop"),
    ]

    config = models.ForeignKey(
        TradingConfig, on_delete=models.SET_NULL, null=True, blank=True
    )
    config_snapshot = models.JSONField(
        help_text="Full config at time of run"
    )
    symbols = models.JSONField()
    start_date = models.CharField(max_length=50)
    end_date = models.CharField(max_length=50)
    resolution = models.CharField(max_length=10, default="1")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    control = models.CharField(
        max_length=10,
        choices=CONTROL_CHOICES,
        default="run",
        help_text="Cross-process control flag read by the Celery task every iteration",
    )
    celery_task_id = models.CharField(max_length=255, blank=True, default="")
    summary_json = models.JSONField(null=True, blank=True)
    metrics_json = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")
    total_bars = models.IntegerField(default=0)
    processed_bars = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        syms = ", ".join(self.symbols[:2]) if self.symbols else "N/A"
        return f"Backtest #{self.pk} [{self.status}] {syms}"

    @property
    def progress_pct(self):
        if self.total_bars == 0:
            return 0
        return round(self.processed_bars / self.total_bars * 100, 1)

    @property
    def duration(self):
        if self.completed_at and self.created_at:
            delta = self.completed_at - self.created_at
            return str(delta).split(".")[0]
        return None


class BacktestTrade(models.Model):
    run = models.ForeignKey(BacktestRun, on_delete=models.CASCADE, related_name="trades")
    order_id = models.IntegerField()
    symbol = models.CharField(max_length=100)
    trade_type = models.CharField(max_length=10)
    entry_price = models.FloatField()
    exit_price = models.FloatField()
    quantity = models.IntegerField()
    pnl = models.FloatField()
    return_pct = models.FloatField(default=0.0)
    total_charges = models.FloatField(default=0.0)
    net_profit = models.FloatField(default=0.0)
    is_paper = models.BooleanField(default=False)
    duration = models.CharField(max_length=20, default="")
    entry_reason = models.CharField(max_length=200, default="")
    exit_reason = models.CharField(max_length=200, default="")
    entry_time = models.DateTimeField(null=True, blank=True)
    exit_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["order_id"]

    def __str__(self):
        return f"Trade #{self.order_id} {self.symbol} {self.trade_type} PnL={self.pnl}"


class LiveSession(models.Model):
    STATUS_CHOICES = [
        ("idle", "Idle"),
        ("pending", "Pending"),
        ("running", "Running"),
        ("paused", "Paused"),
        ("stopping", "Stopping"),
        ("stopped", "Stopped"),
        ("error", "Error"),
    ]

    CONTROL_CHOICES = [
        ("run", "Run"),
        ("pause", "Pause"),
        ("stop", "Stop"),
    ]

    config = models.ForeignKey(
        TradingConfig, on_delete=models.SET_NULL, null=True, blank=True
    )
    config_snapshot = models.JSONField(default=dict)
    symbols = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="idle")
    control = models.CharField(
        max_length=10,
        choices=CONTROL_CHOICES,
        default="run",
        help_text="Cross-process control flag read by the Celery task every iteration",
    )
    celery_task_id = models.CharField(max_length=255, blank=True, default="")
    summary_json = models.JSONField(null=True, blank=True)
    metrics_json = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")
    iterations = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    stopped_at = models.DateTimeField(null=True, blank=True)
    total_pnl = models.FloatField(default=0.0)
    total_trades = models.IntegerField(default=0)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"LiveSession #{self.pk} [{self.status}]"

    @property
    def duration(self):
        if self.stopped_at and self.started_at:
            return str(self.stopped_at - self.started_at).split(".")[0]
        if self.started_at:
            return str(timezone.now() - self.started_at).split(".")[0]
        return None


class LiveTrade(models.Model):
    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name="trades")
    order_id = models.IntegerField()
    symbol = models.CharField(max_length=100)
    trade_type = models.CharField(max_length=10)
    entry_price = models.FloatField()
    exit_price = models.FloatField()
    quantity = models.IntegerField()
    pnl = models.FloatField()
    return_pct = models.FloatField(default=0.0)
    total_charges = models.FloatField(default=0.0)
    net_profit = models.FloatField(default=0.0)
    is_paper = models.BooleanField(default=False)
    duration = models.CharField(max_length=20, default="")
    entry_reason = models.CharField(max_length=200, default="")
    exit_reason = models.CharField(max_length=200, default="")
    entry_time = models.DateTimeField(null=True, blank=True)
    exit_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["order_id"]
        unique_together = [("session", "order_id")]

    def __str__(self):
        return f"LiveTrade #{self.order_id} {self.symbol} {self.trade_type} PnL={self.pnl}"
