"""
Main Django Ninja API with all endpoints.
"""

from typing import List
from uuid import UUID
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from ninja import NinjaAPI
from ninja.errors import HttpError

from .auth import (
    auth,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    create_user_session,
)
from .schemas import (
    UserRegisterSchema,
    UserLoginSchema,
    TokenSchema,
    TokenRefreshSchema,
    UserSchema,
    UserUpdateSchema,
    UserProfileSchema,
    IndicatorSchema,
    StrategyCreateSchema,
    StrategyUpdateSchema,
    StrategySchema,
    TradingSessionCreateSchema,
    TradingSessionSchema,
    PositionSchema,
    OrderCreateSchema,
    OrderSchema,
    TradeSchema,
    BacktestCreateSchema,
    BacktestSessionSchema,
    BacktestResultSchema,
    BacktestTradeSchema,
    SymbolSchema,
    SymbolCreateSchema,
    CandleSchema,
    MarketDataRequestSchema,
    DashboardSummarySchema,
    ErrorSchema,
    MessageSchema,
)
from core.models import User, UserProfile
from trading.models import (
    Indicator,
    Strategy,
    TradingSession,
    Position,
    Order,
    Trade,
    Symbol,
    MarketData,
)
from backtest.models import BacktestSession, BacktestResult, BacktestTrade


# Initialize API
api = NinjaAPI(
    title="Trading Platform API",
    version="1.0.0",
    description="API for the Trading Platform - Backtesting and Realtime Trading",
)


# ==================== AUTH ENDPOINTS ====================


@api.post("/auth/register", response={201: UserSchema, 400: ErrorSchema}, tags=["Auth"])
def register(request, data: UserRegisterSchema):
    """Register a new user."""
    if User.objects.filter(email=data.email).exists():
        raise HttpError(400, "Email already registered")

    if User.objects.filter(username=data.username).exists():
        raise HttpError(400, "Username already taken")

    user = User.objects.create_user(
        email=data.email,
        username=data.username,
        password=data.password,
        default_capital=data.default_capital,
    )

    # Create user profile
    UserProfile.objects.create(user=user)

    return 201, user


@api.post("/auth/login", response={200: TokenSchema, 401: ErrorSchema}, tags=["Auth"])
def login(request, data: UserLoginSchema):
    """Login and get JWT tokens."""
    user = authenticate(request, username=data.email, password=data.password)

    if not user:
        raise HttpError(401, "Invalid credentials")

    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)

    # Create session record
    create_user_session(user, access_token, refresh_token, request)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@api.post("/auth/refresh", response={200: TokenSchema, 401: ErrorSchema}, tags=["Auth"])
def refresh_token(request, data: TokenRefreshSchema):
    """Refresh access token using refresh token."""
    user = verify_refresh_token(data.refresh_token)

    if not user:
        raise HttpError(401, "Invalid or expired refresh token")

    access_token = create_access_token(user)
    new_refresh_token = create_refresh_token(user)

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@api.get("/auth/me", response=UserSchema, auth=auth, tags=["Auth"])
def get_current_user(request):
    """Get current authenticated user."""
    return request.auth


@api.patch("/auth/me", response=UserSchema, auth=auth, tags=["Auth"])
def update_current_user(request, data: UserUpdateSchema):
    """Update current user."""
    user = request.auth

    for field, value in data.dict(exclude_unset=True).items():
        setattr(user, field, value)

    user.save()
    return user


# ==================== INDICATOR ENDPOINTS ====================


@api.get("/indicators", response=List[IndicatorSchema], auth=auth, tags=["Indicators"])
def list_indicators(request):
    """List all available indicators."""
    return Indicator.objects.filter(is_active=True)


@api.get(
    "/indicators/{indicator_id}",
    response=IndicatorSchema,
    auth=auth,
    tags=["Indicators"],
)
def get_indicator(request, indicator_id: UUID):
    """Get a specific indicator."""
    return get_object_or_404(Indicator, id=indicator_id, is_active=True)


# ==================== STRATEGY ENDPOINTS ====================


@api.get("/strategies", response=List[StrategySchema], auth=auth, tags=["Strategies"])
def list_strategies(request):
    """List all strategies for the current user."""
    return Strategy.objects.filter(user=request.auth)


@api.post("/strategies", response={201: StrategySchema}, auth=auth, tags=["Strategies"])
def create_strategy(request, data: StrategyCreateSchema):
    """Create a new strategy."""
    strategy = Strategy.objects.create(user=request.auth, **data.dict())
    return 201, strategy


@api.get(
    "/strategies/{strategy_id}", response=StrategySchema, auth=auth, tags=["Strategies"]
)
def get_strategy(request, strategy_id: UUID):
    """Get a specific strategy."""
    return get_object_or_404(Strategy, id=strategy_id, user=request.auth)


@api.patch(
    "/strategies/{strategy_id}", response=StrategySchema, auth=auth, tags=["Strategies"]
)
def update_strategy(request, strategy_id: UUID, data: StrategyUpdateSchema):
    """Update a strategy."""
    strategy = get_object_or_404(Strategy, id=strategy_id, user=request.auth)

    for field, value in data.dict(exclude_unset=True).items():
        setattr(strategy, field, value)

    strategy.save()
    return strategy


@api.delete(
    "/strategies/{strategy_id}", response={204: None}, auth=auth, tags=["Strategies"]
)
def delete_strategy(request, strategy_id: UUID):
    """Delete a strategy."""
    strategy = get_object_or_404(Strategy, id=strategy_id, user=request.auth)
    strategy.delete()
    return 204, None


@api.post(
    "/strategies/{strategy_id}/duplicate",
    response={201: StrategySchema},
    auth=auth,
    tags=["Strategies"],
)
def duplicate_strategy(request, strategy_id: UUID):
    """Duplicate a strategy."""
    original = get_object_or_404(Strategy, id=strategy_id, user=request.auth)

    strategy = Strategy.objects.create(
        user=request.auth,
        name=f"{original.name} (Copy)",
        description=original.description,
        symbols=original.symbols,
        lot_sizes=original.lot_sizes,
        indicators_config=original.indicators_config,
        aggregation_strategy=original.aggregation_strategy,
        min_agreement=original.min_agreement,
        allow_buy=original.allow_buy,
        allow_sell=original.allow_sell,
        default_quantity=original.default_quantity,
        risk_config=original.risk_config,
        exit_config=original.exit_config,
        flow_config=original.flow_config,
    )

    return 201, strategy


# ==================== TRADING SESSION ENDPOINTS ====================


@api.get("/sessions", response=List[TradingSessionSchema], auth=auth, tags=["Trading"])
def list_sessions(request):
    """List all trading sessions."""
    sessions = TradingSession.objects.filter(user=request.auth).select_related(
        "strategy"
    )
    return [
        {
            **session.__dict__,
            "strategy_id": session.strategy_id,
            "strategy_name": session.strategy.name,
        }
        for session in sessions
    ]


@api.post(
    "/sessions", response={201: TradingSessionSchema}, auth=auth, tags=["Trading"]
)
def create_session(request, data: TradingSessionCreateSchema):
    """Create a new trading session."""
    strategy = get_object_or_404(Strategy, id=data.strategy_id, user=request.auth)

    session = TradingSession.objects.create(
        user=request.auth,
        strategy=strategy,
        session_type=data.session_type,
        initial_capital=data.initial_capital,
        current_capital=data.initial_capital,
        config_snapshot=strategy.indicators_config,
    )

    return 201, {
        **session.__dict__,
        "strategy_id": session.strategy_id,
        "strategy_name": strategy.name,
    }


@api.post(
    "/sessions/{session_id}/start", response=MessageSchema, auth=auth, tags=["Trading"]
)
def start_session(request, session_id: UUID):
    """Start a trading session."""
    session = get_object_or_404(TradingSession, id=session_id, user=request.auth)

    if session.status == "running":
        raise HttpError(400, "Session is already running")

    session.status = "running"
    session.save()

    # TODO: Trigger Celery task to start trading

    return {"message": "Session started"}


@api.post(
    "/sessions/{session_id}/stop", response=MessageSchema, auth=auth, tags=["Trading"]
)
def stop_session(request, session_id: UUID):
    """Stop a trading session."""
    session = get_object_or_404(TradingSession, id=session_id, user=request.auth)

    session.status = "stopped"
    session.save()

    # TODO: Stop Celery task

    return {"message": "Session stopped"}


# ==================== POSITION ENDPOINTS ====================


@api.get(
    "/sessions/{session_id}/positions",
    response=List[PositionSchema],
    auth=auth,
    tags=["Trading"],
)
def list_positions(request, session_id: UUID):
    """List all positions for a session."""
    session = get_object_or_404(TradingSession, id=session_id, user=request.auth)
    return Position.objects.filter(session=session)


# ==================== ORDER ENDPOINTS ====================


@api.get(
    "/sessions/{session_id}/orders",
    response=List[OrderSchema],
    auth=auth,
    tags=["Trading"],
)
def list_orders(request, session_id: UUID):
    """List all orders for a session."""
    session = get_object_or_404(TradingSession, id=session_id, user=request.auth)
    return Order.objects.filter(session=session)


@api.post(
    "/sessions/{session_id}/orders",
    response={201: OrderSchema},
    auth=auth,
    tags=["Trading"],
)
def create_order(request, session_id: UUID, data: OrderCreateSchema):
    """Create a manual order."""
    session = get_object_or_404(TradingSession, id=session_id, user=request.auth)

    if session.status != "running":
        raise HttpError(400, "Session is not running")

    order = Order.objects.create(
        session=session,
        symbol=data.symbol,
        side=data.side,
        order_type=data.order_type,
        quantity=data.quantity,
        price=data.price,
        reason="Manual order",
    )

    # TODO: Execute order via broker

    return 201, order


# ==================== TRADE ENDPOINTS ====================


@api.get(
    "/sessions/{session_id}/trades",
    response=List[TradeSchema],
    auth=auth,
    tags=["Trading"],
)
def list_trades(request, session_id: UUID):
    """List all completed trades for a session."""
    session = get_object_or_404(TradingSession, id=session_id, user=request.auth)
    return Trade.objects.filter(session=session)


# ==================== BACKTEST ENDPOINTS ====================


@api.get(
    "/backtests", response=List[BacktestSessionSchema], auth=auth, tags=["Backtest"]
)
def list_backtests(request):
    """List all backtest sessions."""
    sessions = BacktestSession.objects.filter(user=request.auth).select_related(
        "strategy"
    )
    return [
        {
            **session.__dict__,
            "strategy_id": session.strategy_id,
            "strategy_name": session.strategy.name,
        }
        for session in sessions
    ]


@api.post(
    "/backtests", response={201: BacktestSessionSchema}, auth=auth, tags=["Backtest"]
)
def create_backtest(request, data: BacktestCreateSchema):
    """Create and start a new backtest."""
    strategy = get_object_or_404(Strategy, id=data.strategy_id, user=request.auth)

    session = BacktestSession.objects.create(
        user=request.auth,
        strategy=strategy,
        name=data.name or f"Backtest {strategy.name}",
        description=data.description,
        start_date=data.start_date,
        end_date=data.end_date,
        initial_capital=data.initial_capital,
        speed=data.speed,
        entry_slippage=data.entry_slippage,
        exit_slippage=data.exit_slippage,
        config_snapshot={
            "indicators": strategy.indicators_config,
            "risk": strategy.risk_config,
            "exit": strategy.exit_config,
        },
    )

    # TODO: Trigger Celery task to run backtest
    # from backtest.tasks import run_backtest
    # task = run_backtest.delay(str(session.id))
    # session.celery_task_id = task.id
    # session.save()

    return 201, {
        **session.__dict__,
        "strategy_id": session.strategy_id,
        "strategy_name": strategy.name,
    }


@api.get(
    "/backtests/{session_id}",
    response=BacktestSessionSchema,
    auth=auth,
    tags=["Backtest"],
)
def get_backtest(request, session_id: UUID):
    """Get a specific backtest session."""
    session = get_object_or_404(BacktestSession, id=session_id, user=request.auth)
    return {
        **session.__dict__,
        "strategy_id": session.strategy_id,
        "strategy_name": session.strategy.name,
    }


@api.get(
    "/backtests/{session_id}/result",
    response=BacktestResultSchema,
    auth=auth,
    tags=["Backtest"],
)
def get_backtest_result(request, session_id: UUID):
    """Get backtest results."""
    session = get_object_or_404(BacktestSession, id=session_id, user=request.auth)
    result = get_object_or_404(BacktestResult, session=session)
    return {**result.__dict__, "session_id": session.id}


@api.get(
    "/backtests/{session_id}/trades",
    response=List[BacktestTradeSchema],
    auth=auth,
    tags=["Backtest"],
)
def get_backtest_trades(request, session_id: UUID):
    """Get all trades from a backtest."""
    session = get_object_or_404(BacktestSession, id=session_id, user=request.auth)
    return BacktestTrade.objects.filter(session=session)


@api.post(
    "/backtests/{session_id}/cancel",
    response=MessageSchema,
    auth=auth,
    tags=["Backtest"],
)
def cancel_backtest(request, session_id: UUID):
    """Cancel a running backtest."""
    session = get_object_or_404(BacktestSession, id=session_id, user=request.auth)

    if session.status not in ["pending", "running"]:
        raise HttpError(400, "Backtest is not running")

    session.status = "cancelled"
    session.save()

    # TODO: Cancel Celery task

    return {"message": "Backtest cancelled"}


@api.delete(
    "/backtests/{session_id}", response={204: None}, auth=auth, tags=["Backtest"]
)
def delete_backtest(request, session_id: UUID):
    """Delete a backtest session."""
    session = get_object_or_404(BacktestSession, id=session_id, user=request.auth)
    session.delete()
    return 204, None


# ==================== SYMBOL ENDPOINTS ====================


@api.get("/symbols", response=List[SymbolSchema], auth=auth, tags=["Symbols"])
def list_symbols(request):
    """List all available symbols."""
    return Symbol.objects.filter(is_active=True)


@api.post("/symbols", response={201: SymbolSchema}, auth=auth, tags=["Symbols"])
def create_symbol(request, data: SymbolCreateSchema):
    """Create a new symbol."""
    if Symbol.objects.filter(symbol=data.symbol).exists():
        raise HttpError(400, "Symbol already exists")

    symbol = Symbol.objects.create(**data.dict())
    return 201, symbol


@api.get("/symbols/{symbol}", response=SymbolSchema, auth=auth, tags=["Symbols"])
def get_symbol(request, symbol: str):
    """Get a specific symbol."""
    return get_object_or_404(Symbol, symbol=symbol.upper(), is_active=True)


# ==================== MARKET DATA ENDPOINTS ====================


@api.post(
    "/market-data/candles", response=List[CandleSchema], auth=auth, tags=["Market Data"]
)
def get_candles(request, data: MarketDataRequestSchema):
    """Get candle data for a symbol."""
    symbol_obj = get_object_or_404(Symbol, symbol=data.symbol.upper(), is_active=True)

    queryset = MarketData.objects.filter(symbol=symbol_obj, timeframe=data.timeframe)

    if data.start_date:
        queryset = queryset.filter(timestamp__gte=data.start_date)
    if data.end_date:
        queryset = queryset.filter(timestamp__lte=data.end_date)

    queryset = queryset.order_by("-timestamp")[: data.limit]

    return [
        {
            "timestamp": md.timestamp,
            "open": md.open,
            "high": md.high,
            "low": md.low,
            "close": md.close,
            "volume": md.volume,
        }
        for md in reversed(list(queryset))
    ]


# ==================== DASHBOARD ENDPOINTS ====================


@api.get(
    "/dashboard/summary", response=DashboardSummarySchema, auth=auth, tags=["Dashboard"]
)
def get_dashboard_summary(request):
    """Get dashboard summary for the current user."""
    from django.db.models import Sum, Count, Q
    from django.utils import timezone
    from datetime import timedelta

    user = request.auth
    today = timezone.now().date()

    # Get active sessions
    active_sessions = TradingSession.objects.filter(user=user, status="running")

    # Calculate totals
    total_capital = (
        sum(s.current_capital for s in active_sessions) or user.default_capital
    )
    initial_capital = (
        sum(s.initial_capital for s in active_sessions) or user.default_capital
    )
    total_pnl = float(total_capital - initial_capital)
    total_pnl_pct = (total_pnl / float(initial_capital)) * 100 if initial_capital else 0

    # Count open positions
    open_positions = Position.objects.filter(
        session__user=user, session__status="running"
    ).count()

    # Today's trades
    today_trades = Trade.objects.filter(session__user=user, exit_time__date=today)

    total_trades_today = today_trades.count()
    winning_trades_today = today_trades.filter(net_pnl__gt=0).count()
    win_rate_today = (
        (winning_trades_today / total_trades_today * 100)
        if total_trades_today > 0
        else 0
    )

    return {
        "total_capital": total_capital,
        "total_pnl": total_pnl,
        "total_pnl_pct": total_pnl_pct,
        "open_positions": open_positions,
        "total_trades_today": total_trades_today,
        "winning_trades_today": winning_trades_today,
        "win_rate_today": win_rate_today,
    }
