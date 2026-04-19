from django.contrib import admin
from .models import (
    Indicator,
    Strategy,
    TradingSession,
    Position,
    Order,
    Trade,
    Symbol,
    MarketData,
)


@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = ("name", "display_name", "indicator_type", "is_active")
    list_filter = ("indicator_type", "is_active")
    search_fields = ("name", "display_name")


@admin.register(Strategy)
class StrategyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "aggregation_strategy",
        "is_active",
        "is_live",
        "updated_at",
    )
    list_filter = ("is_active", "is_live", "aggregation_strategy")
    search_fields = ("name", "user__email")
    readonly_fields = ("created_at", "updated_at")


@admin.register(TradingSession)
class TradingSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "strategy",
        "session_type",
        "status",
        "initial_capital",
        "current_capital",
    )
    list_filter = ("session_type", "status")
    search_fields = ("user__email", "strategy__name")


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = (
        "symbol",
        "position_type",
        "entry_price",
        "current_price",
        "quantity",
        "unrealized_pnl",
    )
    list_filter = ("position_type",)
    search_fields = ("symbol",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "symbol",
        "side",
        "order_type",
        "quantity",
        "price",
        "status",
        "created_at",
    )
    list_filter = ("side", "order_type", "status")
    search_fields = ("symbol", "broker_order_id")


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = (
        "symbol",
        "trade_type",
        "entry_price",
        "exit_price",
        "net_pnl",
        "exit_reason",
    )
    list_filter = ("trade_type", "exit_reason")
    search_fields = ("symbol",)


@admin.register(Symbol)
class SymbolAdmin(admin.ModelAdmin):
    list_display = (
        "symbol",
        "display_name",
        "exchange",
        "instrument_type",
        "lot_size",
        "is_active",
    )
    list_filter = ("exchange", "instrument_type", "is_active")
    search_fields = ("symbol", "display_name")


@admin.register(MarketData)
class MarketDataAdmin(admin.ModelAdmin):
    list_display = (
        "symbol",
        "timestamp",
        "timeframe",
        "open",
        "high",
        "low",
        "close",
        "volume",
    )
    list_filter = ("timeframe",)
    search_fields = ("symbol__symbol",)
