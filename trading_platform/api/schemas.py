"""
Pydantic schemas for Django Ninja API.
"""

from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID
from ninja import Schema


# Auth Schemas
class UserRegisterSchema(Schema):
    email: str
    username: str
    password: str
    default_capital: Optional[Decimal] = 100000.00


class UserLoginSchema(Schema):
    email: str
    password: str


class TokenSchema(Schema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshSchema(Schema):
    refresh_token: str


class UserSchema(Schema):
    id: UUID
    email: str
    username: str
    default_capital: Decimal
    broker_type: str
    timezone: str
    created_at: datetime


class UserProfileSchema(Schema):
    risk_per_trade_pct: Decimal
    max_daily_loss_pct: Decimal
    max_positions: int
    chart_theme: str
    default_chart_interval: str
    trading_start_time: time
    trading_end_time: time


class UserUpdateSchema(Schema):
    username: Optional[str] = None
    default_capital: Optional[Decimal] = None
    broker_type: Optional[str] = None
    timezone: Optional[str] = None


# Indicator Schemas
class IndicatorSchema(Schema):
    id: UUID
    name: str
    display_name: str
    description: str
    module_path: str
    class_name: str
    default_params: Dict[str, Any]
    indicator_type: str
    supports_buy: bool
    supports_sell: bool
    is_active: bool


class IndicatorConfigSchema(Schema):
    indicator_id: UUID
    enabled: bool = True
    weight: float = 1.0
    params: Dict[str, Any] = {}


# Strategy Schemas
class StrategyCreateSchema(Schema):
    name: str
    description: Optional[str] = ""
    symbols: List[str] = []
    lot_sizes: Dict[str, int] = {}
    indicators_config: Dict[str, Any] = {}
    aggregation_strategy: str = "weighted"
    min_agreement: float = 0.6
    allow_buy: bool = True
    allow_sell: bool = False
    default_quantity: int = 1
    risk_config: Dict[str, Any] = {}
    exit_config: Dict[str, Any] = {}
    flow_config: Dict[str, Any] = {}


class StrategyUpdateSchema(Schema):
    name: Optional[str] = None
    description: Optional[str] = None
    symbols: Optional[List[str]] = None
    lot_sizes: Optional[Dict[str, int]] = None
    indicators_config: Optional[Dict[str, Any]] = None
    aggregation_strategy: Optional[str] = None
    min_agreement: Optional[float] = None
    allow_buy: Optional[bool] = None
    allow_sell: Optional[bool] = None
    default_quantity: Optional[int] = None
    risk_config: Optional[Dict[str, Any]] = None
    exit_config: Optional[Dict[str, Any]] = None
    flow_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class StrategySchema(Schema):
    id: UUID
    name: str
    description: str
    symbols: List[str]
    lot_sizes: Dict[str, int]
    indicators_config: Dict[str, Any]
    aggregation_strategy: str
    min_agreement: float
    allow_buy: bool
    allow_sell: bool
    default_quantity: int
    risk_config: Dict[str, Any]
    exit_config: Dict[str, Any]
    flow_config: Dict[str, Any]
    is_active: bool
    is_live: bool
    created_at: datetime
    updated_at: datetime


# Trading Session Schemas
class TradingSessionCreateSchema(Schema):
    strategy_id: UUID
    session_type: str = "paper"
    initial_capital: Decimal


class TradingSessionSchema(Schema):
    id: UUID
    strategy_id: UUID
    strategy_name: str
    session_type: str
    status: str
    initial_capital: Decimal
    current_capital: Decimal
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    created_at: datetime


# Position Schemas
class PositionSchema(Schema):
    id: UUID
    symbol: str
    position_type: str
    entry_price: Decimal
    current_price: Decimal
    quantity: int
    initial_quantity: int
    stop_loss: Optional[Decimal]
    trailing_stop: Optional[Decimal]
    unrealized_pnl: Decimal
    max_profit: Decimal
    max_loss: Decimal
    entry_signal: str
    indicator_signals: Dict[str, str]
    opened_at: datetime


# Order Schemas
class OrderCreateSchema(Schema):
    symbol: str
    side: str
    order_type: str = "MARKET"
    quantity: int
    price: Optional[Decimal] = None


class OrderSchema(Schema):
    id: UUID
    broker_order_id: str
    symbol: str
    order_type: str
    side: str
    quantity: int
    price: Optional[Decimal]
    filled_price: Optional[Decimal]
    filled_quantity: int
    status: str
    slippage: Decimal
    reason: str
    created_at: datetime
    filled_at: Optional[datetime]


# Trade Schemas
class TradeSchema(Schema):
    id: UUID
    symbol: str
    trade_type: str
    entry_price: Decimal
    entry_quantity: int
    entry_time: datetime
    exit_price: Decimal
    exit_quantity: int
    exit_time: datetime
    exit_reason: str
    gross_pnl: Decimal
    commission: Decimal
    net_pnl: Decimal
    pnl_percentage: Decimal
    max_favorable_excursion: Decimal
    max_adverse_excursion: Decimal
    hold_duration_seconds: int
    entry_signals: Dict[str, str]


# Backtest Schemas
class BacktestCreateSchema(Schema):
    strategy_id: UUID
    name: Optional[str] = ""
    description: Optional[str] = ""
    start_date: date
    end_date: date
    initial_capital: Decimal
    speed: str = "fast"
    entry_slippage: Decimal = Decimal("0.0005")
    exit_slippage: Decimal = Decimal("0.0005")


class BacktestSessionSchema(Schema):
    id: UUID
    strategy_id: UUID
    strategy_name: str
    name: str
    description: str
    start_date: date
    end_date: date
    initial_capital: Decimal
    speed: str
    entry_slippage: Decimal
    exit_slippage: Decimal
    status: str
    progress: int
    current_bar: int
    total_bars: int
    error_message: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime


class BacktestResultSchema(Schema):
    id: UUID
    session_id: UUID
    final_capital: Decimal
    total_pnl: Decimal
    total_return_pct: Decimal
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal
    gross_profit: Decimal
    gross_loss: Decimal
    avg_win: Decimal
    avg_loss: Decimal
    largest_win: Decimal
    largest_loss: Decimal
    profit_factor: Decimal
    sharpe_ratio: Decimal
    sortino_ratio: Decimal
    max_drawdown: Decimal
    max_drawdown_pct: Decimal
    calmar_ratio: Decimal
    avg_hold_time_seconds: int
    max_consecutive_wins: int
    max_consecutive_losses: int
    equity_curve: List[Dict[str, Any]]
    per_symbol_stats: Dict[str, Any]
    per_indicator_stats: Dict[str, Any]
    exit_reason_breakdown: Dict[str, int]


class BacktestTradeSchema(Schema):
    id: UUID
    trade_number: int
    symbol: str
    trade_type: str
    entry_price: Decimal
    entry_quantity: int
    entry_time: datetime
    entry_bar: int
    exit_price: Decimal
    exit_quantity: int
    exit_time: datetime
    exit_bar: int
    exit_reason: str
    gross_pnl: Decimal
    slippage: Decimal
    commission: Decimal
    net_pnl: Decimal
    pnl_percentage: Decimal
    capital_after_trade: Decimal


# Symbol Schemas
class SymbolSchema(Schema):
    id: UUID
    symbol: str
    display_name: str
    exchange: str
    instrument_type: str
    lot_size: int
    tick_size: Decimal
    market_open: time
    market_close: time
    is_active: bool


class SymbolCreateSchema(Schema):
    symbol: str
    display_name: str
    exchange: str = "NSE"
    instrument_type: str = "EQ"
    lot_size: int = 1
    tick_size: Decimal = Decimal("0.05")


# Market Data Schemas
class CandleSchema(Schema):
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class MarketDataRequestSchema(Schema):
    symbol: str
    timeframe: str = "5m"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 500


# Dashboard Schemas
class DashboardSummarySchema(Schema):
    total_capital: Decimal
    total_pnl: Decimal
    total_pnl_pct: Decimal
    open_positions: int
    total_trades_today: int
    winning_trades_today: int
    win_rate_today: Decimal


class PositionSummarySchema(Schema):
    symbol: str
    position_type: str
    quantity: int
    entry_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    pnl_pct: Decimal


# Error Schemas
class ErrorSchema(Schema):
    detail: str


class MessageSchema(Schema):
    message: str
