from django.contrib import admin
from .models import TradingConfig, BacktestRun, BacktestTrade, LiveSession


@admin.register(TradingConfig)
class TradingConfigAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "created_at", "updated_at"]
    list_filter = ["is_active"]


@admin.register(BacktestRun)
class BacktestRunAdmin(admin.ModelAdmin):
    list_display = ["id", "status", "symbols", "start_date", "end_date", "created_at"]
    list_filter = ["status"]


@admin.register(BacktestTrade)
class BacktestTradeAdmin(admin.ModelAdmin):
    list_display = ["order_id", "symbol", "trade_type", "pnl", "net_profit"]
    list_filter = ["trade_type", "is_paper"]


@admin.register(LiveSession)
class LiveSessionAdmin(admin.ModelAdmin):
    list_display = ["id", "status", "started_at", "total_pnl"]
    list_filter = ["status"]
