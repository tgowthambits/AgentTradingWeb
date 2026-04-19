from django.contrib import admin
from .models import BacktestSession, BacktestResult, BacktestTrade, BacktestEquityPoint


@admin.register(BacktestSession)
class BacktestSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "strategy",
        "status",
        "progress",
        "start_date",
        "end_date",
        "created_at",
    )
    list_filter = ("status", "speed")
    search_fields = ("user__email", "strategy__name")
    readonly_fields = ("created_at", "updated_at", "started_at", "completed_at")


@admin.register(BacktestResult)
class BacktestResultAdmin(admin.ModelAdmin):
    list_display = (
        "session",
        "total_trades",
        "win_rate",
        "total_pnl",
        "sharpe_ratio",
        "max_drawdown_pct",
    )
    search_fields = ("session__strategy__name",)


@admin.register(BacktestTrade)
class BacktestTradeAdmin(admin.ModelAdmin):
    list_display = (
        "session",
        "trade_number",
        "symbol",
        "trade_type",
        "entry_price",
        "exit_price",
        "net_pnl",
    )
    list_filter = ("trade_type", "exit_reason")
    search_fields = ("symbol",)


@admin.register(BacktestEquityPoint)
class BacktestEquityPointAdmin(admin.ModelAdmin):
    list_display = ("session", "timestamp", "equity", "drawdown_pct", "open_positions")
