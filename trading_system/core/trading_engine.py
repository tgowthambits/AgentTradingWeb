"""
Trading Engine

Main engine that coordinates data loading, indicator execution,
signal aggregation, and order management.

Now includes advanced exit strategies and risk management.

This module serves as a facade that coordinates multiple specialized components:
- PositionManager: Manages open trading positions
- OrderManager: Handles order history and execution tracking
- QuantityCalculator: Calculates dynamic trading quantities
- SlippageHandler: Applies slippage to entry/exit prices
- CircuitBreaker: Paper trading mode after consecutive losses
- LossRecovery: Tracks and manages loss recovery per symbol
- SignalAnalyzer: Generates trading signals from market data
"""

import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
import sys
import os

# Add parent directory to path for utils import
# trading_system/core/trading_engine.py -> need to go up to root to access utils/
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
try:
    from utils.charges_calculation import calculate_option_charges
    CHARGES_CALCULATION_AVAILABLE = True
except ImportError:
    CHARGES_CALCULATION_AVAILABLE = False
    print("[WARNING] Charges calculation module not found. Charges will not be calculated.")

# Core component imports
from trading_system.core.indicator_manager import IndicatorManager
from trading_system.core.signal_aggregator import SignalAggregator
from trading_system.data.data_loader import DataLoader

# New modular components
from trading_system.core.position_manager import PositionManager
from trading_system.core.order_manager import OrderManager
from trading_system.core.quantity_calculator import QuantityCalculator
from trading_system.core.slippage_handler import SlippageHandler
from trading_system.core.signal_analyzer import SignalAnalyzer
from trading_system.core.risk.circuit_breaker import CircuitBreaker
from trading_system.core.risk.loss_recovery import LossRecovery

# Advanced risk management modules
try:
    from trading_system.core.volatility_analyzer import VolatilityAnalyzer
    from trading_system.core.risk_manager import RiskManager
    from trading_system.core.risk.exit_strategy_manager import ExitStrategyManager
    from trading_system.indicators.quant_indicators import QuantIndicators
    ADVANCED_FEATURES_AVAILABLE = True
except ImportError:
    ADVANCED_FEATURES_AVAILABLE = False
    print("[WARNING] Advanced risk management modules not found. Running with basic features.")


class TradingEngine:
    """
    Main trading engine that coordinates all components.
    """
    
    def __init__(self, aggregation_strategy: str = 'majority', threshold_config: dict = None, config: dict = None, min_agreement: float = None):
        """
        Initialize the trading engine.
        
        Args:
            aggregation_strategy: Strategy for combining indicator signals
                - 'majority': Simple majority voting
                - 'weighted': Weighted by indicator weights
                - 'unanimous': All must agree
                - 'conservative': Requires strong agreement
                - 'threshold': Minimum number of indicators must agree
            threshold_config: Configuration for threshold-based aggregation
            config: Full trading configuration (for risk management)
            min_agreement: Minimum agreement fraction (from config, defaults to 0.5)
        """
        self.indicator_manager = IndicatorManager()
        
        # Get min_agreement from config if not provided
        if min_agreement is None:
            min_agreement = config.get('min_agreement', 0.5) if config else 0.5
        
        self.signal_aggregator = SignalAggregator(
            strategy=aggregation_strategy,
            min_agreement=min_agreement,
            threshold_config=threshold_config
        )
        self.data_loader = DataLoader()
        self.config = config or {}
        
        self.current_positions = {}  # symbol -> position info
        self.order_history = []  # List of all orders
        self.day_open_prices = {}  # symbol -> opening price for the day
        self.next_order_id = 1
        
        # Cooldown after stop-loss: prevents rapid re-entry on adverse price action
        cooldown_config = self.config.get('risk_management', {}).get('entry_cooldown', {})
        self.cooldown_enabled = cooldown_config.get('enabled', True)
        self.cooldown_seconds = cooldown_config.get('seconds', 120)
        self.last_stop_loss_time = {}  # symbol -> datetime of last stop-loss exit
        
        # Track last candle closure time for intraday 30S resolution exit logic
        self.last_candle_closure_time = {}  # symbol -> datetime
        
        # Paper trading mode (circuit breaker after consecutive losses)
        # IMPORTANT: Circuit breaker tracks losses from ALL exit types:
        # - Hard stop loss, Breakeven stop
        # - Trailing stop
        # - Microstructure reversal
        # - Profit target reversal
        # - Time-based exits
        # - Partial exits (if they result in losses)
        # It activates when consecutive losses (regardless of exit reason) reach the threshold
        self.consecutive_losses = 0
        self.paper_trading_mode = False
        self.paper_mode_config = self.config.get('risk_management', {}).get('paper_trading_mode', {})
        self.paper_mode_enabled = self.paper_mode_config.get('enabled', False)
        self.paper_mode_trigger = self.paper_mode_config.get('consecutive_losses_trigger', 3)
        
        # Log paper trading mode initialization
        if self.paper_mode_enabled:
            print(f"🛡️  CIRCUIT BREAKER INITIALIZED: Enabled=True, Trigger={self.paper_mode_trigger} consecutive losses")
            print(f"   📊 Tracks losses from ALL exit types (stop loss, trailing stop, microstructure, etc.)")
        else:
            print(f"⚠️  CIRCUIT BREAKER DISABLED: paper_trading_mode.enabled=False in config")
        
        # Track hypothetical capital without circuit breaker (for comparison)
        self.initial_capital = self.config.get('backtest', {}).get('initial_capital', 20000)
        self.actual_capital = self.initial_capital  # With circuit breaker protection
        self.hypothetical_capital = self.initial_capital  # Without circuit breaker (all trades count)
        
        # Debug: Print capital initialization
        print(f"💰 CAPITAL INITIALIZED: initial_capital=₹{self.initial_capital:,.2f}, actual_capital=₹{self.actual_capital:,.2f}")
        print(f"   Config backtest.initial_capital={self.config.get('backtest', {}).get('initial_capital', 'NOT FOUND')}")
        
        # Slippage configuration (backtesting only)
        self._load_slippage_config()
        
        # Loss recovery tracking per symbol
        self.symbol_losses = {}  # symbol -> cumulative unrealized loss to recover
        self.loss_recovery_config = self.config.get('risk_management', {}).get('loss_recovery', {})
        self.loss_recovery_enabled = self.loss_recovery_config.get('enabled', False)
        
        # Partial exits configuration
        self.partial_exits_config = self.config.get('risk_management', {}).get('partial_exits', {})
        self.partial_exits_enabled = self.partial_exits_config.get('enabled', True)  # Default True for backward compatibility
        
        # Broker integration
        self._init_broker()
        
        # Recovery history tracking
        self.recovery_history = []  # List of recovery events: [{'symbol', 'trade_id', 'loss_amount', 'recovered_amount', 'timestamp'}]
        self.loss_history = []  # List of loss events: [{'symbol', 'trade_id', 'loss_amount', 'timestamp'}]
        
        # Lot size configuration
        self.lot_sizes = self.config.get('lot_sizes', {})
        self.default_lot_size = self.lot_sizes.get('default', 50)
        
        # Initialize advanced risk management (if available)
        self.advanced_features = ADVANCED_FEATURES_AVAILABLE
        if self.advanced_features:
            self._init_advanced_features()
        else:
            print("ℹ️  Running in basic mode without advanced risk management")
        
        # Initialize modular components (for gradual migration)
        # These modules encapsulate logic but we maintain backward compatibility
        # by keeping the existing attributes (current_positions, order_history, etc.)
        self._init_modular_components()
    
    def _init_broker(self):
        """
        Initialize the broker for order execution.
        
        Reads broker configuration from config and initializes the appropriate
        broker implementation (paper or live).
        """
        broker_config = self.config.get('broker', {})
        broker_enabled = broker_config.get('enabled', False)
        broker_type = broker_config.get('type', 'paper')
        
        self._broker = None
        self._broker_enabled = broker_enabled
        
        if broker_enabled:
            try:
                from .broker import PaperBroker, LiveBroker, OrderSide, OrderType
                
                if broker_type.lower() == 'paper':
                    self._broker = PaperBroker({
                        'initial_capital': self.initial_capital,
                        'slippage_pct': self.entry_slippage_pct
                    })
                    print(f"🔌 Broker initialized: Paper Broker (simulation mode)")
                elif broker_type.lower() == 'live':
                    self._broker = LiveBroker(broker_config)
                    print(f"🔌 Broker initialized: Live Broker ({broker_config.get('broker_name', 'unknown')})")
                else:
                    print(f"⚠️  Unknown broker type: {broker_type}")
            except ImportError as e:
                print(f"⚠️  Broker module not available: {e}")
    
    def _init_modular_components(self):
        """
        Initialize modular components for the trading engine.
        
        These components encapsulate specific functionality and can be used
        independently or through the facade methods. The existing attributes
        are maintained for backward compatibility.
        """
        # Slippage handler (uses self.entry_slippage_pct and self.exit_slippage_pct)
        self._slippage_handler = SlippageHandler(self.config)
        
        # Quantity calculator (uses self.lot_sizes and self.default_lot_size)
        self._quantity_calculator = QuantityCalculator(self.config)
        
        # Circuit breaker (uses self.consecutive_losses and self.paper_trading_mode)
        self._circuit_breaker = CircuitBreaker(self.config)
        # Sync state from existing attributes
        self._circuit_breaker.consecutive_losses = self.consecutive_losses
        self._circuit_breaker.paper_trading_mode = self.paper_trading_mode
        
        # Loss recovery (uses self.symbol_losses)
        self._loss_recovery = LossRecovery(self.config)
        
        # Signal analyzer (needs indicator_manager and signal_aggregator)
        self._signal_analyzer = SignalAnalyzer(
            config=self.config,
            indicator_manager=self.indicator_manager,
            signal_aggregator=self.signal_aggregator,
            volatility_analyzer=getattr(self, 'volatility_analyzer', None),
            exit_manager=getattr(self, 'exit_manager', None)
        )
        
        # Position manager and order manager are not fully integrated yet
        # to maintain backward compatibility with direct attribute access
        # They can be used for new code paths
        self._position_manager = PositionManager(self.config)
        self._order_manager = OrderManager(self.config)
    
    def _load_slippage_config(self):
        """Load slippage configuration from config (backtesting only)."""
        backtest_config = self.config.get('backtest', {})
        self.entry_slippage_pct = backtest_config.get('entry_slippage', 0.0)  # Entry slippage percentage
        self.exit_slippage_pct = backtest_config.get('exit_slippage', 0.0)  # Exit slippage percentage
    
    def _init_advanced_features(self):
        """Initialize advanced risk management modules."""
        # Get config values
        backtest_config = self.config.get('backtest', {})
        risk_config = self.config.get('risk_management', {})
        vol_config = self.config.get('volatility', {})
        
        # Initialize volatility analyzer
        self.volatility_analyzer = VolatilityAnalyzer(
            atr_period=vol_config.get('atr_period', 14),
            volatility_window=vol_config.get('lookback_period', 20)
        )
        
        # Initialize risk manager
        initial_capital = backtest_config.get('initial_capital', 20000)
        self.risk_manager = RiskManager(
            initial_capital=initial_capital,
            risk_per_trade_pct=risk_config.get('risk_per_trade_pct', 1.5),
            max_daily_loss=risk_config.get('daily_limits', {}).get('max_loss_amount', 2000),
            max_positions=risk_config.get('daily_limits', {}).get('max_positions', 6),
            max_trades_per_day=risk_config.get('daily_limits', {}).get('max_trades_per_day', 20)
        )
        
        # Initialize exit strategy manager
        stop_loss_config = risk_config.get('stop_loss', {})
        trailing_config = risk_config.get('trailing_stop', {})
        profit_targets_config = risk_config.get('profit_targets', {})
        
        self.exit_manager = ExitStrategyManager(
            atr_multiplier=stop_loss_config.get('atr_multiplier', 2.0),
            trailing_enabled=trailing_config.get('enabled', True),
            profit_targets_enabled=profit_targets_config.get('enabled', True),
            time_exit_enabled=risk_config.get('time_exit', {}).get('enabled', True),
            config=self.config  # Pass config for microstructure settings
        )
        
        # Initialize quant indicators
        self.quant_indicators = QuantIndicators()
        
        print("✅ Advanced risk management features initialized")
        print(f"   - Initial Capital: ₹{initial_capital:,.2f}")
        print(f"   - Risk Per Trade: {risk_config.get('risk_per_trade_pct', 1.5)}%")
        print(f"   - Stop Loss Method: {stop_loss_config.get('method', 'volatility_adjusted')}")
        print(f"   - Max Daily Loss: ₹{risk_config.get('daily_limits', {}).get('max_loss_amount', 2000):,.2f}")
    
    def register_indicators(self, indicators: list):
        """
        Register indicators with the engine.
        
        Args:
            indicators: List of BaseIndicator instances
        """
        self.indicator_manager.register_multiple(indicators)
    
    def analyze_symbol(self, df: pd.DataFrame, symbol: str, verbose: bool = False) -> dict:
        """
        Analyze a single symbol and generate trading decision.
        Includes advanced exit logic checking.
        
        Args:
            df: DataFrame with OHLCV data
            symbol: Trading symbol
            verbose: Print detailed analysis
        
        Returns:
            Dict with analysis results:
                - 'symbol': Symbol name
                - 'latest_price': Current price
                - 'indicator_signals': Dict of individual signals
                - 'final_signal': Aggregated signal
                - 'signal_breakdown': Count of each signal
                - 'agreement_score': Consensus strength
                - 'timestamp': Analysis timestamp
                - 'volatility': Volatility analysis (if advanced features enabled)
                - 'exit_signal': Exit signal info (if position open)
        """
        # Execute all indicators
        indicator_signals = self.indicator_manager.execute_all(df, verbose=verbose)
        
        # Get indicator weights
        weights = self.indicator_manager.get_weights()
        
        # Aggregate signals
        final_signal = self.signal_aggregator.aggregate(indicator_signals, weights)
        
        # Get signal breakdown
        signal_breakdown = self.signal_aggregator.get_signal_breakdown(indicator_signals)
        
        # Get agreement score
        agreement_score = self.signal_aggregator.get_agreement_score(indicator_signals)

        # Get latest price and change
        latest_price = df['close'].iloc[-1]
        day_open_price = self.day_open_prices.get(symbol, df['open'].iloc[0] if 'open' in df.columns and not df.empty else latest_price)
        change = latest_price - day_open_price
        change_pct = (change / day_open_price) * 100 if day_open_price != 0 else 0
        
        # Update broker's price cache if broker is enabled
        if self._broker_enabled and self._broker is not None:
            self._broker.set_price(symbol, latest_price)
        
        # Get timestamp from dataframe 'datetime' column (last row) if available
        # This matches the DATA_SOURCE.py format where datetime is "MM-DD-YYYY HH:mm:ss"
        current_timestamp = datetime.now()
        if not df.empty:
            # Try 'datetime' column first (formatted string from FyersData)
            if 'datetime' in df.columns:
                last_datetime_str = df['datetime'].iloc[-1]
                try:
                    if isinstance(last_datetime_str, str):
                        # Format: "MM-DD-YYYY HH:mm:ss" from DATA_SOURCE.py
                        current_timestamp = pd.to_datetime(last_datetime_str, format='%m-%d-%Y %H:%M:%S').to_pydatetime()
                    elif isinstance(last_datetime_str, pd.Timestamp):
                        current_timestamp = last_datetime_str.to_pydatetime()
                    elif isinstance(last_datetime_str, datetime):
                        current_timestamp = last_datetime_str
                except:
                    pass
            # Fallback to 'date' column (arrow time object)
            elif 'date' in df.columns:
                last_date = df['date'].iloc[-1]
                try:
                    if hasattr(last_date, 'datetime'):
                        current_timestamp = last_date.datetime
                    elif isinstance(last_date, pd.Timestamp):
                        current_timestamp = last_date.to_pydatetime()
                    elif isinstance(last_date, datetime):
                        current_timestamp = last_date
                    else:
                        current_timestamp = pd.to_datetime(last_date).to_pydatetime()
                except:
                    pass
            # Fallback to index if it's datetime-like
            elif hasattr(df.index, '__len__') and len(df.index) > 0:
                last_index = df.index[-1]
                if isinstance(last_index, pd.Timestamp):
                    current_timestamp = last_index.to_pydatetime()
                elif isinstance(last_index, datetime):
                    current_timestamp = last_index
                elif isinstance(last_index, str):
                    try:
                        current_timestamp = pd.to_datetime(last_index).to_pydatetime()
                    except:
                        pass
        
        result = {
            'symbol': symbol,
            'latest_price': latest_price,
            'indicator_signals': indicator_signals,
            'final_signal': final_signal,
            'signal_breakdown': signal_breakdown,
            'agreement_score': agreement_score,
            'change': change,
            'change_pct': change_pct,
            'change': change,
            'change_pct': change_pct,
            'timestamp': current_timestamp
        }
        
        # Advanced features: volatility analysis and exit logic
        if self.advanced_features:
            # Calculate volatility
            vol_method = self.config.get('volatility', {}).get('calculation_method', 'garman_klass')
            vol_analysis = self.volatility_analyzer.get_comprehensive_volatility(df, method=vol_method)
            result['volatility'] = vol_analysis
            
            # Check exit conditions for open positions
            if symbol in self.current_positions:
                position = self.current_positions[symbol]
                
                # Update highest/lowest prices
                self._update_position_extremes(symbol, latest_price)
                
                # Check for candle closure exit (configurable resolution, losing trades)
                backtest_enabled = self.config.get('backtest', {}).get('enabled', False)
                current_time = current_timestamp if backtest_enabled else datetime.now()
                
                # Get candle closure exit configuration
                candle_closure_config = self.config.get('risk_management', {}).get('candle_closure_exit', {})
                candle_closure_enabled = candle_closure_config.get('enabled', True)  # Default enabled
                candle_closure_resolution = candle_closure_config.get('resolution', '30S')  # Default 30S
                candle_closure_loss_limit = float(candle_closure_config.get('loss_limit', 0.0) or 0.0)  # ₹, 0 => any loss
                
                # Get current resolution from root level or date_range section
                current_resolution = self.config.get('resolution', None)
                if current_resolution is None:
                    current_resolution = self.config.get('date_range', {}).get('resolution', '1min')
                
                # Apply candle closure exit logic if enabled and resolution matches (both live and backtest)
                if candle_closure_enabled and current_resolution == candle_closure_resolution:
                    # Calculate candle interval in seconds based on resolution
                    resolution_to_seconds = {
                        '30S': 30,
                        '1': 60,  # 1 minute
                        '5': 300  # 5 minutes
                    }
                    candle_interval = resolution_to_seconds.get(candle_closure_resolution, 30)
                    
                    # Check if we're at candle closure
                    if symbol not in self.last_candle_closure_time:
                        # Initialize with current time rounded down to nearest candle interval
                        if candle_closure_resolution == '30S':
                            current_second = current_time.second
                            rounded_second = (current_second // 30) * 30
                            self.last_candle_closure_time[symbol] = current_time.replace(second=rounded_second, microsecond=0)
                        elif candle_closure_resolution == '1':
                            # Round down to nearest minute
                            self.last_candle_closure_time[symbol] = current_time.replace(second=0, microsecond=0)
                        elif candle_closure_resolution == '5':
                            # Round down to nearest 5 minutes
                            current_minute = current_time.minute
                            rounded_minute = (current_minute // 5) * 5
                            self.last_candle_closure_time[symbol] = current_time.replace(minute=rounded_minute, second=0, microsecond=0)
                    
                    last_closure = self.last_candle_closure_time[symbol]
                    seconds_since_closure = (current_time - last_closure).total_seconds()
                    
                    # Check if candle interval has passed (candle closure)
                    if seconds_since_closure >= candle_interval:
                        # Calculate current PnL
                        entry_price = position.get('entry_price', 0)
                        position_type = position.get('type', 'LONG')
                        quantity = position.get('quantity', 0)
                        
                        if position_type == 'LONG':
                            current_pnl = (latest_price - entry_price) * quantity
                        else:  # SHORT
                            current_pnl = (entry_price - latest_price) * quantity
                        
                        # If position is in loss, force exit at candle closure
                        if current_pnl < 0 and (candle_closure_loss_limit <= 0 or abs(current_pnl) >= candle_closure_loss_limit):
                            print(f"🕯️  Candle closure detected ({candle_closure_resolution}) - Position in loss: ₹{current_pnl:.2f}")
                            print(f"   Forcing exit at candle closure for {symbol}")
                            
                            # Force exit with candle closure reason
                            self._close_position_with_reason(
                                symbol, 
                                latest_price, 
                                f"Candle closure exit (loss) - {candle_closure_resolution}", 
                                exit_timestamp=current_time,
                                df=df
                            )
                            
                            # Update last closure time based on resolution
                            if candle_closure_resolution == '30S':
                                self.last_candle_closure_time[symbol] = current_time.replace(microsecond=0)
                            elif candle_closure_resolution == '1':
                                self.last_candle_closure_time[symbol] = current_time.replace(second=0, microsecond=0)
                            elif candle_closure_resolution == '5':
                                current_minute = current_time.minute
                                rounded_minute = (current_minute // 5) * 5
                                self.last_candle_closure_time[symbol] = current_time.replace(minute=rounded_minute, second=0, microsecond=0)
                            
                            # Skip normal exit logic since we already exited
                            position['current_price'] = latest_price
                            return result
                        else:
                            # Position is in profit - update closure time but continue with normal logic
                            if candle_closure_resolution == '30S':
                                self.last_candle_closure_time[symbol] = current_time.replace(microsecond=0)
                            elif candle_closure_resolution == '1':
                                self.last_candle_closure_time[symbol] = current_time.replace(second=0, microsecond=0)
                            elif candle_closure_resolution == '5':
                                current_minute = current_time.minute
                                rounded_minute = (current_minute // 5) * 5
                                self.last_candle_closure_time[symbol] = current_time.replace(minute=rounded_minute, second=0, microsecond=0)
                
                # Get recent prices and volumes for microstructure
                recent_prices = df['close'].tail(10).tolist()
                recent_volumes = df['volume'].tail(10).tolist() if 'volume' in df.columns else None
                
                # Check if position should exit
                exit_signal = self.exit_manager.should_exit_position(
                    position=position,
                    current_price=latest_price,
                    current_time=current_time,
                    atr=vol_analysis['atr'],
                    volatility_regime=vol_analysis['regime'],
                    recent_prices=recent_prices,
                    recent_volumes=recent_volumes
                )
                
                result['exit_signal'] = exit_signal
                
                # If exit triggered, close the position (or partial exit for loss recovery)
                if exit_signal['should_exit']:
                    exit_percentage = exit_signal.get('exit_percentage', 100)
                    quantity_to_exit = exit_signal.get('quantity_to_exit', None)
                    full_exit_required = exit_signal.get('full_exit_required', False)
                    reversal_exit = exit_signal.get('reversal_exit', False)
                    
                    # Get exit reason - ensure it's not "Manual close" (use fallback if missing)
                    exit_reason = exit_signal.get('reason', 'Exit strategy triggered')
                    if not exit_reason or exit_reason == 'Manual close' or exit_reason.strip() == '':
                        exit_reason = 'Exit strategy triggered'
                    
                    # Use timestamp from result (which comes from dataframe)
                    exit_timestamp = result.get('timestamp', datetime.now())
                    
                    # Force full exit for microstructure reversal or profit target reversal
                    if full_exit_required or reversal_exit:
                        # ALWAYS full exit for microstructure or reversal
                        self._close_position_with_reason(symbol, latest_price, exit_reason, exit_timestamp=exit_timestamp, df=df)
                        print(f"🚪 FULL EXIT TRIGGERED: {exit_reason} (Confidence: {exit_signal['confidence']:.0%})")
                    elif (exit_percentage < 100 or quantity_to_exit) and self.partial_exits_enabled:
                        # Partial exit (loss recovery or profit target) - only if partial exits enabled
                        self._partial_close_position(symbol, latest_price, exit_reason, 
                                                    exit_percentage=exit_percentage, 
                                                    quantity_to_exit=quantity_to_exit,
                                                    exit_timestamp=exit_timestamp)

                        # log the exit reason
                        print(f"🚪 PARTIAL EXIT TRIGGERED: {exit_reason} (Confidence: {exit_signal['confidence']:.0%}) Not activated")
                    else:
                        # Full exit (also used when partial exits are disabled)
                        self._close_position_with_reason(symbol, latest_price, exit_reason, exit_timestamp=exit_timestamp, df=df)
                        print(f"🚪 EXIT TRIGGERED: {exit_reason} (Confidence: {exit_signal['confidence']:.0%})")
                
                # Update current price
                position['current_price'] = latest_price
        else:
            # Basic mode: just update current price
            if symbol in self.current_positions:
                self.current_positions[symbol]['current_price'] = latest_price
        
        if verbose:
            self._print_analysis(result)
        
        return result
    
    def execute_trading_decision(self, analysis: dict, quantity: int = 1, df: Optional[pd.DataFrame] = None, current_timestamp: Optional[datetime] = None) -> dict:
        """
        Execute trading decision based on analysis.
        
        Args:
            analysis: Analysis result from analyze_symbol()
            quantity: Order quantity
            df: Market data DataFrame (for advanced position sizing)
            current_timestamp: Current timestamp from backtesting data (if None, uses datetime.now())
        
        Returns:
            Dict with order information (or None if no action taken)
        """
        symbol = analysis['symbol']
        final_signal = analysis['final_signal']
        latest_price = analysis['latest_price']
        
        # Get indicator signals for storage
        indicator_signals = analysis.get('indicator_signals', {})
        
        # Build entry reason from signal and agreement
        agreement_score = analysis.get('agreement_score', 0)
        signal_breakdown = analysis.get('signal_breakdown', {})
        entry_reason = f"{final_signal} signal ({agreement_score:.0%} agreement)"
        if signal_breakdown:
            buy_count = signal_breakdown.get('BUY', 0)
            sell_count = signal_breakdown.get('SELL', 0)
            hold_count = signal_breakdown.get('HOLD', 0)
            entry_reason = f"{final_signal} ({buy_count}B/{sell_count}S/{hold_count}H, {agreement_score:.0%})"
        
        # Check current position
        current_position = self.current_positions.get(symbol, None)
        
        # Cooldown check: skip entry if recently stopped out
        if self.cooldown_enabled and current_position is None and symbol in self.last_stop_loss_time:
            use_timestamp = current_timestamp or datetime.now()
            elapsed = (use_timestamp - self.last_stop_loss_time[symbol]).total_seconds()
            if elapsed < self.cooldown_seconds:
                remaining = self.cooldown_seconds - elapsed
                print(f"⏳ Cooldown active for {symbol}: {remaining:.0f}s remaining after stop loss — skipping entry")
                return None
        
        # Determine action
        action = None
        
        if final_signal == 'BUY':
            # Only open LONG if no position exists or already LONG
            # Don't close SHORT positions - let exit strategies handle it
            if current_position is None:
                # Pass 0 to indicate dynamic calculation (quantity is calculated based on capital and lot size)
                action = self._open_position(symbol, 'LONG', latest_price, 0, df, entry_reason=entry_reason, entry_timestamp=current_timestamp, indicator_signals=indicator_signals)
            elif current_position['type'] == 'LONG':
                # Already in LONG position, no action needed
                pass
            else:
                # SHORT position exists - don't close it, just skip opening LONG
                print(f"⚠️  BUY signal received but SHORT position exists - skipping (exit strategies will handle close)")
        
        elif final_signal == 'SELL':
            # Check if selling is allowed
            allow_sell = self.config.get('trading', {}).get('allow_sell', True)
            if not allow_sell:
                # Selling is disabled - don't close position, just skip
                print(f"⚠️  SELL signal ignored (allow_sell disabled) - no action taken")
                # Return without opening SHORT position
                return action
            
            # Only open SHORT if no position exists or already SHORT
            # Don't close LONG positions - let exit strategies handle it
            if current_position is None:
                # Pass 0 to indicate dynamic calculation (quantity is calculated based on capital and lot size)
                action = self._open_position(symbol, 'SHORT', latest_price, 0, df, entry_reason=entry_reason, entry_timestamp=current_timestamp, indicator_signals=indicator_signals)
            elif current_position['type'] == 'SHORT':
                # Already in SHORT position, no action needed
                pass
            else:
                # LONG position exists - don't close it, just skip opening SHORT
                print(f"⚠️  SELL signal received but LONG position exists - skipping (exit strategies will handle close)")
        
        elif final_signal == 'HOLD':
            # Don't close positions on HOLD signal - let exit strategies handle it
            if current_position:
                print(f"⚠️  HOLD signal received - keeping position open (exit strategies will handle close)")
        
        return action
    
    def _apply_entry_slippage(self, price: float, position_type: str) -> float:
        """
        Apply entry slippage to price (backtesting only).
        
        Args:
            price: Original entry price
            position_type: 'LONG' or 'SHORT'
        
        Returns:
            Price with slippage applied
        """
        backtest_mode = self.config.get('backtest', {}).get('enabled', False)
        if not backtest_mode or self.entry_slippage_pct <= 0:
            return price
        
        # Apply slippage: LONG positions pay more (slippage increases price), SHORT positions receive less (slippage decreases price)
        slippage_amount = price * (self.entry_slippage_pct / 100.0)
        if position_type == 'LONG':
            # For LONG: slippage increases entry price (buy at higher price)
            return price + slippage_amount
        else:  # SHORT
            # For SHORT: slippage decreases entry price (sell at lower price)
            return price - slippage_amount
    
    def _apply_exit_slippage(self, price: float, position_type: str) -> float:
        """
        Apply exit slippage to price (backtesting only).
        
        Args:
            price: Original exit price
            position_type: 'LONG' or 'SHORT'
        
        Returns:
            Price with slippage applied
        """
        backtest_mode = self.config.get('backtest', {}).get('enabled', False)
        if not backtest_mode or self.exit_slippage_pct <= 0:
            return price
        
        # Apply slippage: LONG positions receive less (slippage decreases exit price), SHORT positions pay more (slippage increases exit price)
        slippage_amount = price * (self.exit_slippage_pct / 100.0)
        if position_type == 'LONG':
            # For LONG: slippage decreases exit price (sell at lower price)
            return price - slippage_amount
        else:  # SHORT
            # For SHORT: slippage increases exit price (buy at higher price)
            return price + slippage_amount
    
    def _open_position(self, symbol: str, position_type: str, price: float, quantity: int, 
                      df: Optional[pd.DataFrame] = None, entry_reason: str = "Signal triggered", 
                      entry_timestamp: Optional[datetime] = None, indicator_signals: Optional[Dict[str, str]] = None) -> dict:
        """
        Open a new position with advanced risk management.
        
        Args:
            symbol: Trading symbol
            position_type: 'LONG' or 'SHORT'
            price: Entry price
            quantity: Base quantity
            df: DataFrame with market data (for advanced features)
        """
        # Check if backtest mode
        backtest_mode = self.config.get('backtest', {}).get('enabled', False)
        
        # Debug: Show capital state when opening position
        print(f"\n{'='*80}")
        print(f"🔍 OPENING POSITION: {symbol} ({position_type}) @ ₹{price:.2f}")
        print(f"   Initial Capital: ₹{self.initial_capital:,.2f}")
        print(f"   Actual Capital: ₹{self.actual_capital:,.2f}")
        print(f"   Config backtest.initial_capital: {self.config.get('backtest', {}).get('initial_capital', 'NOT FOUND')}")
        print(f"   Backtest Mode: {backtest_mode}")
        print(f"{'='*80}")
        
        # Apply entry slippage (backtesting only)
        original_price = price
        price = self._apply_entry_slippage(price, position_type)
        if backtest_mode and self.entry_slippage_pct > 0:
            print(f"📊 Entry slippage applied: {original_price:.2f} → {price:.2f} ({self.entry_slippage_pct}%)")
        
        # Get lot size for symbol
        lot_size = self.get_lot_size(symbol)
        
        # Default quantity is NOT used for sizing when lot sizes exist
        default_qty = self.config.get('trading', {}).get('default_quantity', None)
        
        # If lot size is 0 or invalid, use default lot size for sizing
        if lot_size <= 0:
            lot_size = self.default_lot_size
            if lot_size and lot_size > 0:
                print(f"⚠️  Invalid lot size for {symbol}. Using default lot size: {lot_size}")
            else:
                print(f"⚠️  No valid lot size available for {symbol}. Cannot size position.")
                return None
        else:
            # Calculate base quantity dynamically based on available capital
            # Use actual_capital (current capital after profits/losses) minus capital already used in open positions
            # Calculate capital already tied up in other open positions
            capital_used_in_positions = 0
            for pos_symbol, pos_data in self.current_positions.items():
                if pos_symbol != symbol:  # Don't count current symbol if it's already open
                    pos_entry_price = pos_data.get('entry_price', 0)
                    pos_quantity = pos_data.get('quantity', 0)
                    capital_used_in_positions += pos_entry_price * pos_quantity
            
            # Available capital = capital base - capital already used in other positions
            # In backtesting, cap capital base at initial_capital to avoid using booked profits
            capital_base = self.actual_capital
            if backtest_mode:
                capital_base = min(self.actual_capital, self.initial_capital)
            available_capital = max(0, capital_base - capital_used_in_positions)
            
            print(f"💰 Calculating quantity with capital: ₹{available_capital:,.2f} (base: ₹{capital_base:,.2f}, actual: ₹{self.actual_capital:,.2f}, used in positions: ₹{capital_used_in_positions:,.2f})")
            
            # Calculate dynamic quantity based on available capital and capital percentage
            # This respects the capital_percentage_per_trade setting
            base_quantity = self.calculate_dynamic_quantity(symbol, price, available_capital, position_type)
            
            print(f"📊 Base quantity calculated: {base_quantity} (from available capital ₹{available_capital:,.2f})")
            
            # Ensure base_quantity is a multiple of lot_size
            if lot_size > 0:
                base_lots = max(1, int(base_quantity / lot_size))
                base_quantity = base_lots * lot_size
                print(f"📊 Quantity Calculation: Capital=₹{available_capital:,.2f}, Calculated={base_lots} lots ({base_quantity} units)")
            else:
                # If lot_size is 0, use base_quantity as-is (shouldn't happen after check above, but safety)
                if base_quantity <= 0:
                    base_quantity = default_qty if default_qty and default_qty > 0 else 25
                print(f"📊 Quantity Calculation: Capital=₹{available_capital:,.2f}, Final={base_quantity} (no lot size)")
            
            # Optional max quantity safety cap (if configured)
            # Only apply if explicitly configured and significantly lower than calculated quantity
            max_allowed_qty = self.config.get('trading', {}).get('max_quantity', None)
            if max_allowed_qty and max_allowed_qty > 0 and lot_size > 0:
                max_allowed_lots = max(1, int(max_allowed_qty / lot_size))
                base_lots = int(base_quantity / lot_size)
                
                # Only cap if max_allowed is much smaller than calculated (safety check)
                # Otherwise, let it scale with capital
                # if max_allowed_lots < base_lots * 0.5:  # Only cap if max is less than 50% of calculated
                if max_allowed_lots < base_lots * 0.5:  # Only cap if max is less than 50% of calculated
                    print(f"⚠️  Max allowed quantity ({max_allowed_lots} lots) is limiting calculated quantity ({base_lots} lots)")
                    print(f"   Using max allowed: {max_allowed_lots} lots")
                    base_quantity = max_allowed_lots * lot_size
                else:
                    print(f"✅ Calculated quantity ({base_lots} lots) is within max allowed ({max_allowed_lots} lots), using calculated")
            elif not max_allowed_qty or max_allowed_qty == 0:
                # No max quantity set - allow full scaling with capital
                print(f"✅ No max quantity limit set - allowing full scaling with capital")
        
        # Calculate recovery quantity if loss recovery is enabled
        recovery_quantity = 0
        loss_to_recover = 0
        if self.loss_recovery_enabled and symbol in self.symbol_losses:
            loss_to_recover = self.symbol_losses[symbol]
            if loss_to_recover > 0:
                # Calculate additional quantity needed to recover loss
                # Strategy: Estimate profit per lot needed, then calculate lots
                estimated_profit_pct = 0.05  # 5% profit estimate
                estimated_profit_per_lot = price * lot_size * estimated_profit_pct
                
                if estimated_profit_per_lot > 0:
                    # Calculate lots needed to generate profit >= loss_to_recover
                    lots_needed_for_recovery = int((loss_to_recover / estimated_profit_per_lot) + 0.5)
                    max_recovery_multiplier = self.loss_recovery_config.get('max_multiplier', 3.0)
                    base_lots = int(base_quantity / lot_size)
                    max_recovery_lots = int(base_lots * (max_recovery_multiplier - 1.0))
                    
                    # Recovery lots (will be converted to quantity)
                    recovery_lots = min(lots_needed_for_recovery, max_recovery_lots)
                    recovery_quantity = recovery_lots * lot_size
                    
                    if recovery_quantity > 0:
                        print(f"🔄 Loss Recovery: ₹{loss_to_recover:.2f} to recover")
                        print(f"   Lot size: {lot_size}, Base lots: {int(base_quantity/lot_size)}, Recovery lots: {recovery_lots}")
                        print(f"   Base quantity: {base_quantity}, Recovery quantity: {recovery_quantity}")
                        print(f"   Total quantity: {base_quantity + recovery_quantity}")
        
        # Final quantity (ensure it's a multiple of lot size)
        # Both base_quantity and recovery_quantity should already be multiples of lot_size
        # But ensure final is also a multiple
        final_quantity = base_quantity + recovery_quantity
        
        # If lot_size is valid, round to nearest lot size
        if lot_size > 0:
            final_lots = int(final_quantity / lot_size)
            final_quantity = final_lots * lot_size  # Round down to nearest lot size (never round up)
        else:
            # If lot_size is 0 or invalid, use quantity as-is but ensure it's positive
            if final_quantity <= 0:
                final_quantity = default_qty if default_qty and default_qty > 0 else 25
            final_lots = final_quantity
        
        # CRITICAL: Ensure quantity doesn't exceed capital percentage limit
        # Calculate capital already tied up in other open positions
        capital_used_in_positions = 0
        for pos_symbol, pos_data in self.current_positions.items():
            if pos_symbol != symbol:  # Don't count current symbol if it's already open
                pos_entry_price = pos_data.get('entry_price', 0)
                pos_quantity = pos_data.get('quantity', 0)
                capital_used_in_positions += pos_entry_price * pos_quantity
        
        # Available capital = capital base - capital already used in other positions
        # In backtesting, cap capital base at initial_capital to avoid using booked profits
        capital_base = self.actual_capital
        if backtest_mode:
            capital_base = min(self.actual_capital, self.initial_capital)
        available_capital = max(0, capital_base - capital_used_in_positions)
        
        # Get capital percentage limit from config
        risk_config = self.config.get('risk_management', {})
        if backtest_mode:
            capital_pct = risk_config.get('capital_percentage_per_trade_backtest', 50.0) / 100.0
        else:
            capital_pct = risk_config.get('capital_percentage_per_trade_intraday', 20.0) / 100.0
        
        # Maximum capital allowed for this trade = available_capital * capital_percentage
        max_capital_for_this_trade = available_capital * capital_pct
        
        print(f"\n💰 CAPITAL CALCULATION FOR {symbol}:")
        print(f"   Initial Capital: ₹{self.initial_capital:,.2f}")
        print(f"   Actual Capital: ₹{self.actual_capital:,.2f}")
        print(f"   Capital Base: ₹{capital_base:,.2f}")
        print(f"   Capital Used in Other Positions: ₹{capital_used_in_positions:,.2f}")
        print(f"   Available Capital: ₹{available_capital:,.2f}")
        print(f"   Capital % Per Trade: {capital_pct*100:.0f}% (from config)")
        print(f"   Max Capital for This Trade: ₹{max_capital_for_this_trade:,.2f}")
        print(f"   Config Value: capital_percentage_per_trade_intraday={risk_config.get('capital_percentage_per_trade_intraday', 'NOT FOUND')}")
        
        if lot_size > 0:
            cost_per_lot = price * lot_size
            # Use max_capital_for_this_trade (respects percentage) instead of full available_capital
            max_affordable_lots = int(max_capital_for_this_trade / cost_per_lot) if cost_per_lot > 0 else 0
            max_affordable_quantity = max_affordable_lots * lot_size
            
            if final_quantity > max_affordable_quantity:
                print(f"⚠️  Quantity {final_quantity} exceeds capital limit ₹{max_capital_for_this_trade:.2f} ({capital_pct*100:.0f}% of ₹{available_capital:,.2f})")
                print(f"   Adjusting to affordable quantity: {max_affordable_quantity} (lots: {max_affordable_lots})")
                final_quantity = max_affordable_quantity
                final_lots = max_affordable_lots
            
            # Ensure at least 1 lot if we can afford it (within capital percentage limit)
            if final_quantity < lot_size and max_capital_for_this_trade >= cost_per_lot:
                final_quantity = lot_size
                final_lots = 1
            elif final_quantity < lot_size:
                print(f"⚠️  Cannot afford even 1 lot. Max capital for trade: ₹{max_capital_for_this_trade:.2f}, Required: ₹{cost_per_lot:.2f}")
                return None  # Cannot open position
            
            # Final hard clamp to capital percentage limit (after recovery/default adjustments)
            final_cost = final_quantity * price
            if final_cost > max_capital_for_this_trade:
                clamp_lots = int(max_capital_for_this_trade / cost_per_lot)
                final_quantity = clamp_lots * lot_size
                final_lots = clamp_lots
                if final_quantity <= 0:
                    print(f"⚠️  Cannot afford any quantity within capital limit. Max per trade: ₹{max_capital_for_this_trade:.2f}")
                    return None
        else:
            # If lot_size is 0, check affordability based on price directly (within capital percentage limit)
            total_cost = final_quantity * price
            if total_cost > max_capital_for_this_trade:
                # Reduce quantity to what we can afford
                affordable_quantity = int(max_capital_for_this_trade / price) if price > 0 else 0
                if affordable_quantity <= 0:
                    print(f"⚠️  Cannot afford any quantity. Max capital for trade: ₹{max_capital_for_this_trade:.2f}, Price: ₹{price:.2f}")
                    return None
                final_quantity = affordable_quantity
                final_lots = final_quantity
                print(f"⚠️  Quantity adjusted to affordable: {final_quantity} (cost: ₹{total_cost:.2f} > max: ₹{max_capital_for_this_trade:.2f})")
            
            # Ensure at least default quantity if we can afford it (within capital percentage limit)
            if final_quantity <= 0:
                if default_qty and default_qty > 0 and (default_qty * price) <= max_capital_for_this_trade:
                    final_quantity = default_qty
                    final_lots = final_quantity
                else:
                    print(f"⚠️  Cannot afford default quantity. Max capital for trade: ₹{max_capital_for_this_trade:.2f}")
                    return None
        
        if final_quantity != (base_quantity + recovery_quantity):
            print(f"📦 Quantity adjusted to lot size: {final_quantity} (lots: {final_lots}, lot_size: {lot_size})")
        stop_loss = None
        profit_targets = None
        volatility_regime = 'NORMAL'
        atr = 0
        max_loss_per_trade = None  # Initialize for loss capping
        
        if self.advanced_features and df is not None and len(df) > 0:
            try:
                # Calculate volatility
                vol_method = self.config.get('volatility', {}).get('calculation_method', 'garman_klass')
                vol_analysis = self.volatility_analyzer.get_comprehensive_volatility(df, method=vol_method)
                atr = vol_analysis['atr']
                volatility_regime = vol_analysis['regime']
                
                # Calculate stop loss based on configured method
                stop_loss_config = self.config.get('risk_management', {}).get('stop_loss', {})
                stop_loss_method = stop_loss_config.get('method', 'volatility_adjusted')
                
                if stop_loss_method == 'fixed_amount':
                    # Use fixed rupee amount stop loss
                    max_loss = stop_loss_config.get('max_loss_per_trade', 300)
                    stop_loss = self.exit_manager.calculate_fixed_amount_stop(
                        price, final_quantity, max_loss, position_type
                    )
                    print(f"🛡️  FIXED AMOUNT STOP LOSS: Max loss per trade = ₹{max_loss:.2f}")
                    # Store max_loss for enforcement during exit
                    max_loss_per_trade = max_loss
                else:
                    # Use volatility-adjusted stop loss
                    stop_loss = self.exit_manager.calculate_volatility_stop(
                        price, atr, position_type, volatility_regime
                    )
                    max_loss_per_trade = None
                
                # Calculate position size (skip dynamic sizing in backtest mode)
                if not backtest_mode and self.risk_manager.can_open_position(len(self.current_positions)):
                    optimal_size = self.risk_manager.calculate_position_size(
                        entry_price=price,
                        stop_loss_price=stop_loss,
                        atr=atr,
                        volatility_regime=volatility_regime
                    )
                    # Use smaller of optimal size or requested quantity, but ensure it's a multiple of lot size
                    if optimal_size > 0:
                        optimal_lots = int(optimal_size / lot_size)
                        optimal_quantity = optimal_lots * lot_size
                        final_quantity = min(optimal_quantity, final_quantity)
                    # Ensure final_quantity is still a multiple of lot_size
                    final_lots = int(final_quantity / lot_size)
                    final_quantity = final_lots * lot_size
                elif not backtest_mode:
                    # Only check limits in non-backtest mode
                    if not self.risk_manager.can_open_position(len(self.current_positions)):
                        print(f"⚠️  Position limit reached or trading halted!")
                        return None
                
                # Apply max_position_size limit from config (if set) - applies to both backtest and live
                max_position_size = self.config.get('risk_management', {}).get('max_position_size', None)
                if max_position_size and max_position_size > 0:
                    if final_quantity > max_position_size:
                        print(f"⚠️  Position size {final_quantity} exceeds max_position_size limit {max_position_size}")
                        # Round down to lot size if applicable
                        if lot_size > 0:
                            max_lots = int(max_position_size / lot_size)
                            final_quantity = max_lots * lot_size
                            if final_quantity <= 0:
                                print(f"⚠️  Max position size {max_position_size} is too small for lot size {lot_size}")
                                return None
                        else:
                            final_quantity = max_position_size
                        print(f"   Adjusted to max_position_size: {final_quantity}")
                
                # Calculate profit targets
                profit_targets = self.exit_manager.calculate_profit_targets(
                    price, atr, position_type
                )
                
                print(f"📊 Risk Analysis:")
                print(f"   Volatility Regime: {volatility_regime}")
                print(f"   ATR: ₹{atr:.2f}")
                
                # Show stop loss details
                if stop_loss_method == 'fixed_amount':
                    max_loss = stop_loss_config.get('max_loss_per_trade', 300)
                    loss_per_unit = abs(price - stop_loss)
                    total_risk = loss_per_unit * final_quantity
                    print(f"   Stop Loss Method: FIXED AMOUNT (₹{max_loss:.2f} max)")
                    print(f"   Stop Loss Price: ₹{stop_loss:.2f} (₹{loss_per_unit:.2f} per unit)")
                    print(f"   Max Loss: ₹{total_risk:.2f} ({final_quantity} × ₹{loss_per_unit:.2f})")
                else:
                    print(f"   Stop Loss: ₹{stop_loss:.2f}")
                
                if backtest_mode:
                    print(f"   Position Size: {final_quantity} (fixed for backtest)")
                else:
                    print(f"   Position Size: {final_quantity} (optimal)")
                if profit_targets:
                    print(f"   Profit Targets: ₹{profit_targets[0]['price']:.2f} / ₹{profit_targets[1]['price']:.2f} / ₹{profit_targets[2]['price']:.2f}")
                
            except Exception as e:
                print(f"⚠️  Error in advanced position sizing: {e}")
                # Fallback: use calculated base_quantity (already respects lot size)
                # final_quantity is already set above, just ensure it's still valid
                if final_quantity < lot_size:
                    final_quantity = lot_size
        
        # Check if we're in paper trading mode
        # Circuit breaker should work independently when enabled
        # It protects capital by switching to paper trades after consecutive losses
        if self.paper_mode_enabled:
            # Circuit breaker is enabled - use it to protect capital
            is_paper_trade = self.paper_trading_mode
            if is_paper_trade:
                print(f"📝 Opening position in PAPER TRADING MODE (Circuit breaker active - {self.consecutive_losses} consecutive losses)")
                print(f"   ⚠️  This trade will NOT affect capital - it's a paper trade for testing")
            elif self.consecutive_losses >= self.paper_mode_trigger:
                # Should be in paper mode but isn't - force it
                print(f"⚠️  WARNING: {self.consecutive_losses} consecutive losses but paper mode not active - activating now!")
                self.paper_trading_mode = True
                is_paper_trade = True
        else:
            # Circuit breaker is disabled - check general paper trading setting
            general_paper_trading = self.config.get('trading', {}).get('paper_trading', False)
            is_paper_trade = general_paper_trading
        
        # Debug logging for paper trading mode (only when enabled to reduce spam)
        if self.paper_mode_enabled and (is_paper_trade or self.consecutive_losses > 0):
            print(f"🔍 Paper Trading Status: Enabled={self.paper_mode_enabled}, Active={self.paper_trading_mode}, Consecutive Losses={self.consecutive_losses}/{self.paper_mode_trigger}, This Trade={'PAPER' if is_paper_trade else 'REAL'}")
        
        # Use provided timestamp or get from dataframe 'datetime' column, otherwise use now
        if entry_timestamp is not None:
            entry_time = entry_timestamp
        elif df is not None and not df.empty:
            # Try 'datetime' column first (formatted string from FyersData)
            if 'datetime' in df.columns:
                last_datetime_str = df['datetime'].iloc[-1]
                try:
                    if isinstance(last_datetime_str, str):
                        # Format: "MM-DD-YYYY HH:mm:ss" from DATA_SOURCE.py
                        entry_time = pd.to_datetime(last_datetime_str, format='%m-%d-%Y %H:%M:%S').to_pydatetime()
                    elif isinstance(last_datetime_str, pd.Timestamp):
                        entry_time = last_datetime_str.to_pydatetime()
                    elif isinstance(last_datetime_str, datetime):
                        entry_time = last_datetime_str
                    else:
                        entry_time = datetime.now()
                except:
                    entry_time = datetime.now()
            # Fallback to 'date' column (arrow time object)
            elif 'date' in df.columns:
                last_date = df['date'].iloc[-1]
                try:
                    if hasattr(last_date, 'datetime'):
                        entry_time = last_date.datetime
                    elif isinstance(last_date, pd.Timestamp):
                        entry_time = last_date.to_pydatetime()
                    elif isinstance(last_date, datetime):
                        entry_time = last_date
                    else:
                        entry_time = pd.to_datetime(last_date).to_pydatetime()
                except:
                    entry_time = datetime.now()
            # Fallback to index if it's datetime-like
            elif hasattr(df.index, '__len__') and len(df.index) > 0:
                last_index = df.index[-1]
                if isinstance(last_index, pd.Timestamp):
                    entry_time = last_index.to_pydatetime()
                elif isinstance(last_index, datetime):
                    entry_time = last_index
                elif isinstance(last_index, str):
                    try:
                        entry_time = pd.to_datetime(last_index).to_pydatetime()
                    except:
                        entry_time = datetime.now()
                else:
                    entry_time = datetime.now()
            else:
                entry_time = datetime.now()
        else:
            entry_time = datetime.now()
        
        # Capture entry candle high from DataFrame if available
        entry_candle_high = None
        if df is not None and not df.empty and 'high' in df.columns:
            entry_candle_high = float(df['high'].iloc[-1])
        
        # Create order with unique ID and locked entry price
        # CRITICAL: entry_price must NEVER be modified after order creation
        order = {
            'order_id': self.next_order_id,
            'symbol': symbol,
            'type': position_type,
            'entry_price': float(price),  # Lock entry price at order creation time
            'entry_time': entry_time,
            'exit_price': None,
            'exit_time': None,
            'quantity': final_quantity,
            'original_quantity': final_quantity,  # Store original quantity for completed trades display
            'pnl': 0.0,
            'status': 'OPEN',
            'entry_reason': entry_reason,  # Store entry reason
            'exit_reason': None,
            'paper_trade': is_paper_trade,  # Mark if this is a paper trade
            'indicator_signals': indicator_signals if indicator_signals else {},  # Store indicator signals at entry
            'entry_candle_high': entry_candle_high,  # Store entry candle high price
            '_entry_price_locked': True  # Flag to prevent modification
        }
        
        self.order_history.append(order)
        
        # Validate order ID is unique
        existing_ids = [o['order_id'] for o in self.order_history if o != order]
        if self.next_order_id in existing_ids:
            print(f"⚠️  WARNING: Duplicate order ID detected: {self.next_order_id}. Generating new ID.")
            # Find next available ID
            max_id = max(existing_ids) if existing_ids else 0
            self.next_order_id = max_id + 1
            order['order_id'] = self.next_order_id
        
        # Get max_loss_per_trade from config for fixed amount method
        max_loss_per_trade = None
        if self.advanced_features:
            stop_loss_config = self.config.get('risk_management', {}).get('stop_loss', {})
            if stop_loss_config.get('method') == 'fixed_amount':
                max_loss_per_trade = stop_loss_config.get('max_loss_per_trade', 300)
        
        # Initialize candle closure tracking for this symbol (if candle closure exit is enabled)
        candle_closure_config = self.config.get('risk_management', {}).get('candle_closure_exit', {})
        candle_closure_enabled = candle_closure_config.get('enabled', True)
        candle_closure_resolution = candle_closure_config.get('resolution', '30S')
        backtest_enabled = self.config.get('backtest', {}).get('enabled', False)
        
        if candle_closure_enabled and symbol not in self.last_candle_closure_time:
            init_time = entry_time if backtest_enabled else datetime.now()
            if candle_closure_resolution == '30S':
                current_second = init_time.second
                rounded_second = (current_second // 30) * 30
                self.last_candle_closure_time[symbol] = init_time.replace(second=rounded_second, microsecond=0)
            elif candle_closure_resolution == '1':
                self.last_candle_closure_time[symbol] = init_time.replace(second=0, microsecond=0)
            elif candle_closure_resolution == '5':
                current_minute = init_time.minute
                rounded_minute = (current_minute // 5) * 5
                self.last_candle_closure_time[symbol] = init_time.replace(minute=rounded_minute, second=0, microsecond=0)
        
        # Store position with advanced tracking
        # CRITICAL: entry_price must match order's entry_price and NEVER change
        locked_entry_price = float(price)  # Lock entry price at position creation
        self.current_positions[symbol] = {
            'symbol': symbol,
            'order_id': self.next_order_id,
            'type': position_type,
            'entry_price': locked_entry_price,  # Locked - should NEVER be modified
            'open_price_today': df['open'].iloc[0] if df is not None and not df.empty and 'open' in df.columns else price,
            'quantity': final_quantity,
            'base_quantity': base_quantity,  # Store base quantity
            'recovery_quantity': recovery_quantity,  # Store recovery quantity
            'loss_to_recover': loss_to_recover,  # Store loss amount to recover
            'loss_recovered': 0.0,  # Track how much loss has been recovered
            'entry_time': entry_time,  # Use timestamp from dataframe (backtesting) or datetime.now() (live)
            'current_price': price,
            'highest_price': price,
            'lowest_price': price,
            'max_profit': 0.0,  # Track maximum profit reached (may not be booked)
            'min_profit': 0.0,  # Track minimum profit reached (worst point)
            'avg_profit': 0.0,  # Track average profit when in profit
            'avg_loss': 0.0,  # Track average loss when in loss
            'profit_count': 0,  # Count of profit snapshots
            'loss_count': 0,  # Count of loss snapshots
            'stop_loss': stop_loss,
            'profit_targets': profit_targets,
            'initial_volatility': atr,
            'volatility_regime': volatility_regime,
            'paper_trade': is_paper_trade,
            'max_loss_per_trade': max_loss_per_trade,  # Store for loss capping
            'target_highs': {},  # Track highest price after each profit target (for LONG)
            'target_lows': {}  # Track lowest price after each profit target (for SHORT)
        }
        
        self.next_order_id += 1
        
        # Execute through broker if enabled
        broker_order_id = None
        if self._broker_enabled and self._broker is not None:
            try:
                broker_order = self._execute_broker_entry(symbol, position_type, final_quantity, price)
                if broker_order:
                    broker_order_id = broker_order.order_id
                    order['broker_order_id'] = broker_order_id
                    self.current_positions[symbol]['broker_order_id'] = broker_order_id
                    print(f"🔌 Broker Order Placed: {broker_order_id} | Status: {broker_order.status.value}")
            except Exception as e:
                print(f"⚠️  Broker order failed: {e} (internal order still valid)")
        
        # Log position details for debugging
        capital_used = final_quantity * price
        print(f"\n📊 POSITION OPENED - FINAL DETAILS:")
        print(f"   Symbol: {symbol}")
        print(f"   Type: {position_type}")
        print(f"   Quantity: {final_quantity} units")
        print(f"   Entry Price: ₹{price:.2f}")
        print(f"   Capital Used: ₹{capital_used:,.2f}")
        print(f"   Initial Capital: ₹{self.initial_capital:,.2f}")
        print(f"   Actual Capital (before): ₹{self.actual_capital:,.2f}")
        print(f"   Paper Trade: {is_paper_trade}")
        if broker_order_id:
            print(f"   Broker Order ID: {broker_order_id}")
        print(f"{'='*80}\n")
        
        # Display differently for paper trades
        if is_paper_trade:
            print(f"📝 OPENED {position_type} position (PAPER TRADE): {symbol} @ ₹{price:.2f} x {final_quantity} (Order #{order['order_id']}) [paper_trade={is_paper_trade}]")
            print(f"   [PAPER MODE ACTIVE - {self.consecutive_losses} consecutive losses]")
            print(f"   ⚠️  NOTE: Capital will NOT be affected by this trade")
        else:
            print(f"📈 OPENED {position_type} position (REAL): {symbol} @ ₹{price:.2f} x {final_quantity} (Order #{order['order_id']}) [paper_trade={is_paper_trade}]")
            print(f"   ✅ Capital will be updated when position closes")
        
        return order
    
    # ==================== Broker Integration Methods ====================
    
    def _execute_broker_entry(self, symbol: str, position_type: str, quantity: int, price: float):
        """
        Execute an entry order through the broker.
        
        Args:
            symbol: Trading symbol
            position_type: 'LONG' or 'SHORT'
            quantity: Order quantity
            price: Order price
            
        Returns:
            BrokerOrder object or None
        """
        if not self._broker:
            return None
        
        try:
            from .broker import OrderSide, OrderType
            
            # Update broker's price cache
            self._broker.set_price(symbol, price)
            
            # Determine order side
            side = OrderSide.BUY if position_type == 'LONG' else OrderSide.SELL
            
            # Place market order
            broker_order = self._broker.place_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                order_type=OrderType.MARKET,
                product_type="INTRADAY",
                tag=f"ENTRY_{position_type}"
            )
            
            return broker_order
            
        except Exception as e:
            print(f"⚠️  Broker entry execution error: {e}")
            return None
    
    def _execute_broker_exit(self, symbol: str, position_type: str, quantity: int, price: float, reason: str = ""):
        """
        Execute an exit order through the broker.
        
        Args:
            symbol: Trading symbol
            position_type: 'LONG' or 'SHORT'
            quantity: Quantity to exit
            price: Exit price
            reason: Exit reason for tagging
            
        Returns:
            BrokerOrder object or None
        """
        if not self._broker:
            return None
        
        try:
            from .broker import OrderSide, OrderType
            
            # Update broker's price cache
            self._broker.set_price(symbol, price)
            
            # Exit is opposite of position type
            side = OrderSide.SELL if position_type == 'LONG' else OrderSide.BUY
            
            # Place market order to exit
            broker_order = self._broker.place_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                order_type=OrderType.MARKET,
                product_type="INTRADAY",
                tag=f"EXIT_{reason[:20]}" if reason else "EXIT"
            )
            
            return broker_order
            
        except Exception as e:
            print(f"⚠️  Broker exit execution error: {e}")
            return None
    
    def update_broker_prices(self, symbol: str, price: float):
        """
        Update the broker's price cache for a symbol.
        
        Call this when new price data is available to keep broker in sync.
        
        Args:
            symbol: Trading symbol
            price: Current price
        """
        if self._broker:
            self._broker.set_price(symbol, price)
    
    def get_broker_positions(self) -> dict:
        """
        Get positions from the broker.
        
        Returns:
            Dictionary of broker positions or empty dict if broker not enabled
        """
        if self._broker:
            return self._broker.get_positions()
        return {}
    
    def get_broker_funds(self) -> dict:
        """
        Get funds/margin info from the broker.
        
        Returns:
            Dictionary with fund details or empty dict if broker not enabled
        """
        if self._broker:
            return self._broker.get_funds()
        return {}
    
    def _close_position(self, symbol: str, price: float, df: Optional[pd.DataFrame] = None) -> dict:
        """Close an existing position."""
        # This method should not be used anymore - positions should only close via exit strategies
        # But keeping it for backward compatibility with a non-"Manual close" reason
        return self._close_position_with_reason(symbol, price, "Exit strategy triggered", df=df)
    
    def _close_position_with_reason(self, symbol: str, price: float, reason: str = "Exit strategy triggered", exit_timestamp: Optional[datetime] = None, df: Optional[pd.DataFrame] = None) -> dict:
        """Close an existing position with a specific reason."""
        if symbol not in self.current_positions:
            return None
        
        # Prevent "Manual close" exits - replace with a proper exit reason
        if reason == "Manual close" or reason.lower() == "manual close":
            reason = "Exit strategy triggered"
            print(f"⚠️  'Manual close' reason detected and replaced with '{reason}' for {symbol}")
        
        position = self.current_positions[symbol]
        is_paper_trade = position.get('paper_trade', False)
        position_quantity = position.get('quantity', 0)  # Get actual position quantity
        
        # Find order in history - ALWAYS use order's entry_price as source of truth
        entry_price = None
        order = None
        for o in self.order_history:
            if o['order_id'] == position['order_id'] and o['status'] == 'OPEN':
                order = o
                # CRITICAL: Always use order's entry_price - it should NEVER change after order creation
                entry_price = order.get('entry_price')
                if entry_price is None or entry_price == 0:
                    # Fallback: use position's entry_price if order doesn't have it (shouldn't happen)
                    entry_price = position.get('entry_price', price)
                    # Log warning if this happens
                    print(f"⚠️  WARNING: Order {order['order_id']} missing entry_price, using position entry_price: {entry_price}")
                break
        
        if order is None:
            print(f"⚠️  ERROR: Could not find order with ID {position.get('order_id')} for symbol {symbol}")
            return None
        
        # Use position quantity (actual remaining quantity) instead of order quantity
        # which may have been reduced by partial exits
        exit_quantity = position_quantity if position_quantity > 0 else order.get('quantity', 0)
        
        position_type = position.get('type', 'LONG')
        
        # Execute through broker if enabled
        if self._broker_enabled and self._broker is not None:
            try:
                broker_order = self._execute_broker_exit(symbol, position_type, exit_quantity, price, reason)
                if broker_order:
                    order['broker_exit_order_id'] = broker_order.order_id
                    print(f"🔌 Broker Exit Order: {broker_order.order_id} | Status: {broker_order.status.value}")
            except Exception as e:
                print(f"⚠️  Broker exit failed: {e} (internal close still proceeds)")
        
        # Apply exit slippage (backtesting only)
        original_price = price
        price = self._apply_exit_slippage(price, position_type)
        backtest_mode = self.config.get('backtest', {}).get('enabled', False)
        if backtest_mode and self.exit_slippage_pct > 0:
            print(f"📊 Exit slippage applied: {original_price:.2f} → {price:.2f} ({self.exit_slippage_pct}%)")
        
        # Use provided timestamp or use now
        if exit_timestamp is not None:
            exit_time = exit_timestamp
        else:
            exit_time = datetime.now()
        
        # Capture exit candle low from DataFrame if available
        exit_candle_low = None
        if df is not None and not df.empty and 'low' in df.columns:
            exit_candle_low = float(df['low'].iloc[-1])
        
        # Close the order
        order['exit_price'] = price
        order['exit_time'] = exit_time
        order['status'] = 'CLOSED'
        order['exit_reason'] = reason
        order['paper_trade'] = is_paper_trade  # Explicitly set paper_trade flag
        order['exit_candle_low'] = exit_candle_low  # Store exit candle low price
        
        # Store exit reason in position for UI access before position is removed
        position['last_exit_reason'] = reason
        
        # Store highest and lowest prices for max/min profit calculation
        order['highest_price'] = position.get('highest_price', entry_price)
        order['lowest_price'] = position.get('lowest_price', entry_price)
        
        # Store max and min profit reached during position lifetime
        # Use the position's tracked max/min profit (calculated during position lifetime)
        max_profit = position.get('max_profit', 0.0)
        min_profit = position.get('min_profit', 0.0)
        
        # Store average profit and average loss
        order['avg_profit'] = position.get('avg_profit', 0.0)
        order['avg_loss'] = position.get('avg_loss', 0.0)
        
        # If not set, calculate from highest/lowest prices
        # Use original order quantity for max/min profit (full position performance)
        # CRITICAL: Always use order's entry_price for calculations
        order_entry_price = order.get('entry_price', entry_price)
        if abs(max_profit) < 0.01 and abs(min_profit) < 0.01:
            highest_price = position.get('highest_price', order_entry_price)
            lowest_price = position.get('lowest_price', order_entry_price)
            # Use original order quantity for max/min profit (not exit quantity)
            original_qty = order.get('original_quantity', order.get('quantity', exit_quantity))
            if order['type'] == 'LONG':
                max_profit = (highest_price - order_entry_price) * original_qty
                min_profit = (lowest_price - order_entry_price) * original_qty
            else:  # SHORT
                max_profit = (order_entry_price - lowest_price) * original_qty
                min_profit = (order_entry_price - highest_price) * original_qty
        
        order['max_profit'] = max_profit
        order['min_profit'] = min_profit
        
        # Store the exit quantity (for display in completed trades)
        order['exit_quantity'] = exit_quantity
        
        # Calculate PnL using exit quantity
        # CRITICAL: Always use order's entry_price - it is locked and never changes
        order_entry_price_for_pnl = order.get('entry_price')
        if order_entry_price_for_pnl is None or order_entry_price_for_pnl == 0:
            print(f"⚠️  ERROR: Order {order['order_id']} has invalid entry_price: {order_entry_price_for_pnl}. Using fallback.")
            order_entry_price_for_pnl = entry_price  # Fallback to the entry_price we got earlier
        
        if order['type'] == 'LONG':
            pnl = (price - order_entry_price_for_pnl) * exit_quantity
        else:  # SHORT
            pnl = (order_entry_price_for_pnl - price) * exit_quantity
        
        # ENFORCE MAX LOSS CAP: If stop loss was hit and loss exceeds max, cap it
        max_loss_per_trade = position.get('max_loss_per_trade')
        if max_loss_per_trade is not None and pnl < 0:
            # Check if this was a stop loss exit
            if reason and ('stop loss' in reason.lower() or 'breakeven stop' in reason.lower()):
                # Cap loss at max_loss_per_trade
                if abs(pnl) > max_loss_per_trade:
                    # Calculate exit price that results in exactly max_loss
                    # CRITICAL: Always use order's entry_price
                    order_entry_price_cap = order.get('entry_price', entry_price)
                    if order['type'] == 'LONG':
                        capped_exit_price = order_entry_price_cap - (max_loss_per_trade / exit_quantity)
                    else:  # SHORT
                        capped_exit_price = order_entry_price_cap + (max_loss_per_trade / exit_quantity)
                    
                    # Use capped exit price and recalculate PnL
                    price = capped_exit_price
                    if order['type'] == 'LONG':
                        pnl = (price - order_entry_price_cap) * exit_quantity
                    else:  # SHORT
                        pnl = (order_entry_price_cap - price) * exit_quantity
                    
                    print(f"🛡️  LOSS CAPPED: Actual loss ₹{abs(pnl):.2f} exceeds max ₹{max_loss_per_trade:.2f}, capping at ₹{max_loss_per_trade:.2f}")
        
        order['pnl'] = pnl
        
        # Record cooldown timestamp when exiting on stop loss
        if self.cooldown_enabled and pnl < 0 and reason and ('stop loss' in reason.lower() or 'breakeven stop' in reason.lower()):
            self.last_stop_loss_time[symbol] = exit_time
        
        # Update quantity field for display (use exit quantity, which is the actual quantity closed)
        order['quantity'] = exit_quantity
        
        # Update capital for both profits and losses
        # Hypothetical capital (without circuit breaker) - affected by ALL trades
        self.hypothetical_capital += pnl
        
        # Actual capital (with circuit breaker) - only affected by REAL trades
        # Update capital for both profits and losses (real trades only)
        if not is_paper_trade:
            self.actual_capital += pnl
            if pnl < 0:
                print(f"💰 Capital updated (LOSS): ₹{self.actual_capital:,.2f} (Loss: ₹{abs(pnl):.2f})")
            else:
                print(f"💰 Capital updated (PROFIT): ₹{self.actual_capital:,.2f} (Profit: ₹{pnl:+.2f})")
        else:
            # Paper trade - log but don't affect capital
            if pnl < 0:
                print(f"📝 Paper trade loss: ₹{abs(pnl):.2f} (Capital unchanged: ₹{self.actual_capital:,.2f})")
            else:
                print(f"📝 Paper trade profit: ₹{pnl:+.2f} (Capital unchanged: ₹{self.actual_capital:,.2f})")
        
        # Track loss for recovery strategy (only for real trades)
        if self.loss_recovery_enabled and not is_paper_trade and pnl < 0:
            # Track cumulative loss per symbol
            if symbol not in self.symbol_losses:
                self.symbol_losses[symbol] = 0.0
            self.symbol_losses[symbol] += abs(pnl)  # Add to cumulative loss
            print(f"📉 Loss tracked for {symbol}: ₹{abs(pnl):.2f} (Total to recover: ₹{self.symbol_losses[symbol]:.2f})")
        elif self.loss_recovery_enabled and not is_paper_trade and pnl > 0:
            # If profitable, check if we recovered the loss
            if symbol in self.symbol_losses and self.symbol_losses[symbol] > 0:
                recovered = min(pnl, self.symbol_losses[symbol])
                self.symbol_losses[symbol] -= recovered
                if self.symbol_losses[symbol] <= 0:
                    self.symbol_losses[symbol] = 0
                    print(f"✅ Loss fully recovered for {symbol}! Remaining: ₹0.00")
                else:
                    print(f"💰 Partial recovery for {symbol}: ₹{recovered:.2f} (Remaining: ₹{self.symbol_losses[symbol]:.2f})")
        
        # Capital already updated above, no need to update again
        
        # Update paper trading mode based on consecutive losses
        # Circuit breaker tracks losses from ALL exit types (stop loss, trailing stop, 
        # microstructure reversal, profit target reversal, time-based exit, etc.)
        # It works independently when enabled and protects capital regardless of exit reason
        if self.paper_mode_enabled:
            if not is_paper_trade:
                # Real trade - update consecutive losses for ANY loss, regardless of exit reason
                if pnl < 0:
                    self.consecutive_losses += 1
                    print(f"⚠️  Consecutive losses: {self.consecutive_losses}/{self.paper_mode_trigger} (Exit: {reason}, Paper Mode: {self.paper_trading_mode})")
                    print(f"   📊 Circuit breaker tracks losses from ALL exit types (stop loss, trailing stop, microstructure, etc.)")
                    
                    # Check if we should enter paper trading mode
                    if self.consecutive_losses >= self.paper_mode_trigger:
                        if not self.paper_trading_mode:
                            self.paper_trading_mode = True
                            print(f"🛑 PAPER TRADING MODE ACTIVATED after {self.consecutive_losses} consecutive losses!")
                            print(f"   Next orders will be PAPER TRADES until one is profitable")
                            print(f"   This will protect capital by not executing real trades")
                            print(f"   ⚠️  Circuit breaker active for ALL exit conditions (not just stop loss)")
                        else:
                            print(f"🛡️  Paper trading mode already active ({self.consecutive_losses} consecutive losses)")
                else:
                    # Winning trade - reset counter and exit paper mode
                    if self.consecutive_losses > 0:
                        print(f"✅ Winning trade! Resetting consecutive losses counter (was {self.consecutive_losses})")
                    self.consecutive_losses = 0
                    # Exit paper mode if it was active (only real trades can exit paper mode)
                    if self.paper_trading_mode:
                        self.paper_trading_mode = False
                        print(f"✅ Exiting paper trading mode after profitable REAL trade")
            else:
                # Paper trade - check if profitable to exit paper mode
                if pnl > 0:
                    print(f"✅ Paper trade profitable! Exiting paper trading mode")
                    self.paper_trading_mode = False
                    self.consecutive_losses = 0
                elif pnl < 0:
                    print(f"📝 Paper trade loss: ₹{abs(pnl):.2f} (Capital protected - no real loss)")
        else:
            # Paper mode disabled - log for debugging (only on first loss to avoid spam)
            if not is_paper_trade and pnl < 0 and self.consecutive_losses == 0:
                print(f"⚠️  Loss occurred but paper trading mode is DISABLED")
                print(f"   Enable it in config: risk_management.paper_trading_mode.enabled = True")
        
        # Register trade with risk manager only for real trades
        if self.advanced_features and not is_paper_trade:
            self.risk_manager.register_trade(pnl)
        
        # Display differently for paper trades
        if is_paper_trade:
            print(f"📝 CLOSED {order['type']} position (PAPER TRADE): {symbol} @ ₹{price:.2f} | PnL: ₹{pnl:+.2f} | Reason: {reason} (Order #{order['order_id']}) [paper_trade={is_paper_trade}]")
            if pnl > 0:
                print(f"   ✅ Paper trade profitable - resuming REAL trading!")
            else:
                print(f"   Paper loss (doesn't affect capital) - paper mode continues")
        else:
            print(f"📉 CLOSED {order['type']} position (REAL): {symbol} @ ₹{price:.2f} | PnL: ₹{pnl:+.2f} | Reason: {reason} (Order #{order['order_id']}) [paper_trade={is_paper_trade}]")
        
        # Show capital comparison (with vs without circuit breaker)
        if self.paper_mode_enabled:
            savings = self.actual_capital - self.hypothetical_capital
            print(f"\n💰 Capital Comparison:")
            print(f"   WITHOUT Circuit Breaker: ₹{self.hypothetical_capital:,.2f}")
            print(f"   WITH Circuit Breaker:    ₹{self.actual_capital:,.2f}")
            if savings > 0:
                print(f"   💚 Savings: ₹{savings:+,.2f} (Protected by circuit breaker!)")
            elif savings < 0:
                print(f"   ⚪ Difference: ₹{savings:+,.2f}")
            else:
                print(f"   ⚪ Same capital (no paper trades yet)")
            print()
        
        # Remove from current positions
        del self.current_positions[symbol]
        
        return order
    
    def _partial_close_position(self, symbol: str, price: float, reason: str, 
                                exit_percentage: float = 50, quantity_to_exit: int = None, 
                                exit_timestamp: Optional[datetime] = None) -> dict:
        """
        Partially close a position (for loss recovery or profit targets).
        
        Args:
            symbol: Trading symbol
            price: Exit price
            reason: Exit reason
            exit_percentage: Percentage of position to exit
            quantity_to_exit: Specific quantity to exit (overrides percentage)
        """
        if symbol not in self.current_positions:
            return None
        
        position = self.current_positions[symbol]
        is_paper_trade = position.get('paper_trade', False)
        total_quantity = position['quantity']
        
        # Apply exit slippage (backtesting only)
        position_type = position.get('type', 'LONG')
        original_price = price
        price = self._apply_exit_slippage(price, position_type)
        backtest_mode = self.config.get('backtest', {}).get('enabled', False)
        if backtest_mode and self.exit_slippage_pct > 0:
            print(f"📊 Exit slippage applied (partial): {original_price:.2f} → {price:.2f} ({self.exit_slippage_pct}%)")
        
        # Determine quantity to exit
        if quantity_to_exit is not None:
            exit_qty = min(quantity_to_exit, total_quantity)
        else:
            exit_qty = int(total_quantity * (exit_percentage / 100))
        
        if exit_qty <= 0 or exit_qty >= total_quantity:
            # If exiting all or nothing, use full close
            # Note: df may not be available in partial close context, pass None
            return self._close_position_with_reason(symbol, price, reason, exit_timestamp=exit_timestamp, df=None)
        
        # Execute partial exit through broker if enabled
        if self._broker_enabled and self._broker is not None:
            try:
                broker_order = self._execute_broker_exit(symbol, position_type, exit_qty, price, f"PARTIAL_{reason[:15]}")
                if broker_order:
                    print(f"🔌 Broker Partial Exit: {broker_order.order_id} | Qty: {exit_qty} | Status: {broker_order.status.value}")
            except Exception as e:
                print(f"⚠️  Broker partial exit failed: {e}")
        
        # Find order in history
        for order in self.order_history:
            if order['order_id'] == position['order_id'] and order['status'] == 'OPEN':
                # Calculate PnL for partial exit
                if order['type'] == 'LONG':
                    pnl = (price - order['entry_price']) * exit_qty
                else:  # SHORT
                    pnl = (order['entry_price'] - price) * exit_qty
                
                # Update order quantity (reduce by exit_qty)
                order['quantity'] -= exit_qty
                
                # Update position quantity - ensure it doesn't go below 0
                new_quantity = max(0, position['quantity'] - exit_qty)
                position['quantity'] = new_quantity
                
                # Store exit reason in position for UI access
                position['last_exit_reason'] = reason
                
                # If quantity becomes 0, close the position fully and remove from current_positions
                if new_quantity <= 0:
                    print(f"⚠️  Position quantity reached 0, closing position fully: {symbol}")
                    # Remove from current positions
                    if symbol in self.current_positions:
                        del self.current_positions[symbol]
                    
                    # Clean up candle closure tracking if position is fully closed
                    if symbol in self.last_candle_closure_time:
                        del self.last_candle_closure_time[symbol]
                    
                    # Use provided timestamp or use now
                    if exit_timestamp is not None:
                        exit_time = exit_timestamp
                    else:
                        exit_time = datetime.now()
                    
                    # Mark order as closed
                    order['status'] = 'CLOSED'
                    order['exit_price'] = price
                    order['exit_time'] = exit_time
                    order['exit_reason'] = reason
                    order['highest_price'] = position.get('highest_price', order.get('entry_price', price))
                    order['lowest_price'] = position.get('lowest_price', order.get('entry_price', price))
                    order['max_profit'] = float(position.get('max_profit', 0.0) or 0.0)
                    order['min_profit'] = float(position.get('min_profit', 0.0) or 0.0)
                    order['avg_profit'] = float(position.get('avg_profit', 0.0) or 0.0)
                    order['avg_loss'] = float(position.get('avg_loss', 0.0) or 0.0)
                    # Store exit quantity for display (total quantity that was closed)
                    order['exit_quantity'] = exit_qty
                    # Update quantity field for display
                    order['quantity'] = exit_qty
                    # Return the closed order info
                    return {
                        'order_id': order['order_id'],
                        'symbol': symbol,
                        'exit_price': price,
                        'exit_qty': exit_qty,
                        'pnl': pnl,
                        'reason': reason
                    }
                
                # Update capital for partial exits (both profits and losses)
                self.hypothetical_capital += pnl
                if not is_paper_trade:
                    self.actual_capital += pnl
                    if pnl < 0:
                        print(f"💰 Capital updated (partial exit LOSS): ₹{self.actual_capital:,.2f} (Loss: ₹{abs(pnl):.2f})")
                    else:
                        print(f"💰 Capital updated (partial exit PROFIT): ₹{self.actual_capital:,.2f} (Profit: ₹{pnl:+.2f})")
                else:
                    # Paper trade - log but don't affect capital
                    if pnl < 0:
                        print(f"📝 Paper trade partial exit loss: ₹{abs(pnl):.2f} (Capital unchanged: ₹{self.actual_capital:,.2f})")
                    else:
                        print(f"📝 Paper trade partial exit profit: ₹{pnl:+.2f} (Capital unchanged: ₹{self.actual_capital:,.2f})")
                
                # Return partial exit info
                return {
                    'order_id': order['order_id'],
                    'symbol': symbol,
                    'exit_price': price,
                    'exit_qty': exit_qty,
                    'pnl': pnl,
                    'reason': reason
                }
                
                # Track consecutive losses for partial exits too (circuit breaker works for ALL exit types)
                # This ensures losses from any exit condition (stop loss, trailing stop, microstructure, 
                # profit target reversal, partial exits, etc.) count toward the circuit breaker
                if self.paper_mode_enabled and not is_paper_trade:
                    if pnl < 0:
                        # Partial exit resulted in loss - count toward consecutive losses
                        self.consecutive_losses += 1
                        print(f"⚠️  Consecutive losses: {self.consecutive_losses}/{self.paper_mode_trigger} (Partial Exit: {reason}, Paper Mode: {self.paper_trading_mode})")
                        print(f"   📊 Circuit breaker tracks losses from ALL exit types (stop loss, trailing stop, microstructure, partial exits, etc.)")
                        
                        # Check if we should enter paper trading mode
                        if self.consecutive_losses >= self.paper_mode_trigger:
                            if not self.paper_trading_mode:
                                self.paper_trading_mode = True
                                print(f"🛑 PAPER TRADING MODE ACTIVATED after {self.consecutive_losses} consecutive losses!")
                                print(f"   Next orders will be PAPER TRADES until one is profitable")
                                print(f"   ⚠️  Circuit breaker active for ALL exit conditions (including partial exits)")
                            else:
                                print(f"🛡️  Paper trading mode already active ({self.consecutive_losses} consecutive losses)")
                    elif pnl > 0:
                        # Partial exit resulted in profit - reset counter
                        if self.consecutive_losses > 0:
                            print(f"✅ Partial exit profitable! Resetting consecutive losses counter (was {self.consecutive_losses})")
                        self.consecutive_losses = 0
                        # Exit paper mode if it was active
                        if self.paper_trading_mode:
                            self.paper_trading_mode = False
                            print(f"✅ Exiting paper trading mode after profitable partial exit")
                
                # Update loss recovery tracking
                if self.loss_recovery_enabled and not is_paper_trade and pnl > 0:
                    if symbol in self.symbol_losses and self.symbol_losses[symbol] > 0:
                        recovered = min(pnl, self.symbol_losses[symbol])
                        loss_before = self.symbol_losses[symbol] + recovered
                        self.symbol_losses[symbol] -= recovered
                        position['loss_recovered'] = position.get('loss_recovered', 0) + recovered
                        
                        # Record recovery in history
                        self.recovery_history.append({
                            'symbol': symbol,
                            'trade_id': order['order_id'],
                            'loss_amount': loss_before,
                            'recovered_amount': recovered,
                            'remaining_loss': self.symbol_losses[symbol],
                            'timestamp': datetime.now(),
                            'entry_price': order['entry_price'],
                            'exit_price': price,
                            'quantity': exit_qty,
                            'full_recovery': self.symbol_losses[symbol] <= 0
                        })
                        
                        if self.symbol_losses[symbol] <= 0:
                            self.symbol_losses[symbol] = 0
                            position['loss_to_recover'] = 0
                            position['recovery_quantity'] = 0
                            print(f"✅ Loss fully recovered for {symbol}! Remaining: ₹0.00")
                            print(f"   Remaining position ({position['quantity']} units) will follow normal strategy")
                        else:
                            print(f"💰 Partial recovery: ₹{recovered:.2f} (Remaining: ₹{self.symbol_losses[symbol]:.2f})")
                
                print(f"📊 PARTIAL EXIT: {symbol} @ ₹{price:.2f} | Exited {exit_qty}/{total_quantity} | PnL: ₹{pnl:+.2f} | Reason: {reason}")
                print(f"   Remaining position: {position['quantity']} units")
                
                return {
                    'order_id': order['order_id'],
                    'symbol': symbol,
                    'exit_price': price,
                    'exit_qty': exit_qty,
                    'pnl': pnl,
                    'reason': reason
                }
        
        return None
    
    def _update_position_extremes(self, symbol: str, current_price: float):
        """Update highest and lowest prices for a position (for trailing stop)."""
        if symbol not in self.current_positions:
            return
        
        position = self.current_positions[symbol]
        # CRITICAL: Get entry_price from order, not position (order is source of truth)
        # Find the order to get the locked entry_price
        order_entry_price = None
        for order in self.order_history:
            if order.get('order_id') == position.get('order_id'):
                order_entry_price = order.get('entry_price')
                break
        
        # Use order's entry_price if available, otherwise fallback to position
        if order_entry_price is not None and order_entry_price > 0:
            entry_price = order_entry_price
        else:
            entry_price = position.get('entry_price', current_price)
            if order_entry_price is None:
                print(f"⚠️  WARNING: Could not find order for position {symbol}, using position entry_price: {entry_price}")
        
        quantity = position.get('quantity', 0)
        position_type = position.get('type', 'LONG')
        
        # Update highest price
        if current_price > position.get('highest_price', current_price):
            position['highest_price'] = current_price
        
        # Update lowest price
        if current_price < position.get('lowest_price', current_price):
            position['lowest_price'] = current_price
        
        # Calculate max profit (best profit reached during position lifetime)
        if position_type == 'LONG':
            max_profit_price = position.get('highest_price', entry_price)
            max_profit = (max_profit_price - entry_price) * quantity
            min_profit_price = position.get('lowest_price', entry_price)
            min_profit = (min_profit_price - entry_price) * quantity
            # Calculate max profit percentage
            if entry_price > 0:
                max_profit_pct = ((max_profit_price - entry_price) / entry_price) * 100
            else:
                max_profit_pct = 0.0
        else:  # SHORT
            max_profit_price = position.get('lowest_price', entry_price)
            max_profit = (entry_price - max_profit_price) * quantity
            min_profit_price = position.get('highest_price', entry_price)
            min_profit = (entry_price - min_profit_price) * quantity
            # Calculate max profit percentage
            if entry_price > 0:
                max_profit_pct = ((entry_price - max_profit_price) / entry_price) * 100
            else:
                max_profit_pct = 0.0
        
        # Store max and min profit
        position['max_profit'] = max_profit
        position['min_profit'] = min_profit
        
        # Track max profit percentage (for profit drop protection)
        if 'max_profit_pct' not in position:
            position['max_profit_pct'] = max(0, max_profit_pct)
        else:
            position['max_profit_pct'] = max(position['max_profit_pct'], max_profit_pct)
        
        # Calculate current PnL for average tracking
        # CRITICAL: Always use the locked entry_price from order (already retrieved above)
        if position_type == 'LONG':
            current_pnl = (current_price - entry_price) * quantity
        else:  # SHORT
            current_pnl = (entry_price - current_price) * quantity
        
        # Track average profit (when in profit)
        if current_pnl > 0:
            if 'profit_count' not in position:
                position['profit_count'] = 0
                position['avg_profit'] = 0.0
            
            position['profit_count'] += 1
            # Running average: new_avg = old_avg + (new_value - old_avg) / count
            position['avg_profit'] = position['avg_profit'] + (current_pnl - position['avg_profit']) / position['profit_count']
        
        # Track average loss (when in loss)
        elif current_pnl < 0:
            if 'loss_count' not in position:
                position['loss_count'] = 0
                position['avg_loss'] = 0.0
            
            position['loss_count'] += 1
            # Running average: new_avg = old_avg + (new_value - old_avg) / count
            position['avg_loss'] = position['avg_loss'] + (current_pnl - position['avg_loss']) / position['loss_count']
    
    def get_open_positions(self) -> pd.DataFrame:
        """Get all open positions with LTP and change %."""
        if not self.current_positions:
            return pd.DataFrame()

        positions_list = []
        for position in self.current_positions.values():
            ltp = position['current_price']
            open_today = position.get('open_price_today', position['entry_price'])
            change_pct = ((ltp - open_today) / open_today) * 100 if open_today != 0 else 0

            positions_list.append({
                'order_id': position['order_id'],
                'symbol': position['symbol'],
                'type': position['type'],
                'entry_price': position['entry_price'],
                'ltp': ltp,
                'change_%': f'{change_pct:.2f}%',
                'entry_time': position['entry_time'],
                'quantity': position['quantity'],
                'max_profit': position.get('max_profit', 0.0),
                'min_profit': position.get('min_profit', 0.0),
                'avg_profit': position.get('avg_profit', 0.0),
                'avg_loss': position.get('avg_loss', 0.0)
            })

        df = pd.DataFrame(positions_list)
        
        # Desired column order
        columns = ['order_id', 'symbol', 'type', 'quantity', 'entry_price', 'ltp', 'change_%', 'entry_time', 'max_profit', 'min_profit', 'avg_profit', 'avg_loss']
        
        # Reorder df columns, only including those that exist in the DataFrame
        df_columns = [col for col in columns if col in df.columns]
        
        return df[df_columns]
    
    def get_closed_orders(self) -> pd.DataFrame:
        """Get all closed orders with charges calculation."""
        closed_orders = [o for o in self.order_history if o['status'] == 'CLOSED']
        
        if not closed_orders:
            return pd.DataFrame()
        
        df = pd.DataFrame(closed_orders)
        columns = ['order_id', 'symbol', 'type', 'entry_price', 'exit_price', 
                  'entry_time', 'exit_time', 'pnl', 'max_profit', 'min_profit', 'avg_profit', 'avg_loss']
        
        # Add entry_candle_high and exit_candle_low if they exist
        if 'entry_candle_high' in df.columns:
            columns.append('entry_candle_high')
        if 'exit_candle_low' in df.columns:
            columns.append('exit_candle_low')
        
        # Use exit_quantity if available, otherwise use quantity
        if 'exit_quantity' in df.columns:
            # Use exit_quantity for the actual quantity closed
            df['quantity'] = df['exit_quantity']
        # If exit_quantity doesn't exist, quantity should already be set correctly
        
        columns.append('quantity')
        
        # Calculate charges for each trade if charges calculation is available
        if CHARGES_CALCULATION_AVAILABLE:
            total_charges_list = []
            net_profit_list = []
            
            for idx, row in df.iterrows():
                try:
                    # Get lot size for the symbol
                    lot_size = self.get_lot_size(row['symbol'])
                    if lot_size <= 0:
                        lot_size = self.default_lot_size
                    
                    # Calculate number of lots
                    quantity = row.get('quantity', 0)
                    if lot_size > 0:
                        num_lots = quantity // lot_size
                        if num_lots == 0:
                            num_lots = 1  # At least 1 lot
                    else:
                        num_lots = 1
                    
                    # Get brokerage from config (if available)
                    brokerage_per_order = self.config.get('broker', {}).get('brokerage_per_order', 0.0)
                    include_brokerage = self.config.get('broker', {}).get('include_brokerage', True)
                    
                    # Determine buy_price and sell_price based on trade type
                    entry_price = row['entry_price']
                    exit_price = row['exit_price']
                    trade_type = row['type']
                    
                    if trade_type == 'LONG':
                        buy_price = entry_price
                        sell_price = exit_price
                    else:  # SHORT
                        buy_price = exit_price  # Buy to cover
                        sell_price = entry_price  # Sell short
                    
                    # Calculate charges
                    charges_result = calculate_option_charges(
                        buy_price=buy_price,
                        sell_price=sell_price,
                        lot_size=lot_size,
                        quantity=num_lots,
                        brokerage_per_order=brokerage_per_order,
                        include_brokerage=include_brokerage
                    )
                    
                    total_charges = charges_result.get('total_charges', 0.0)
                    # Net profit = PnL - charges
                    pnl = row.get('pnl', 0.0)
                    net_profit = pnl - total_charges
                    
                except Exception as e:
                    # If calculation fails, use defaults
                    total_charges = 0.0
                    net_profit = row.get('pnl', 0.0)
                    print(f"⚠️  Error calculating charges for order {row.get('order_id', 'N/A')}: {e}")
                
                total_charges_list.append(total_charges)
                net_profit_list.append(net_profit)
            
            # Add charges and net profit columns
            df['total_charges'] = total_charges_list
            df['net_profit'] = net_profit_list
            columns.extend(['total_charges', 'net_profit'])
        else:
            # If charges calculation not available, set defaults
            df['total_charges'] = 0.0
            df['net_profit'] = df['pnl']
            columns.extend(['total_charges', 'net_profit'])
        
        # Add entry_reason if available
        if 'entry_reason' in df.columns:
            columns.append('entry_reason')
        
        # Add exit_reason if available
        if 'exit_reason' in df.columns:
            columns.append('exit_reason')
        
        # Add paper_trade flag if available
        if 'paper_trade' in df.columns:
            columns.append('paper_trade')
        
        # Add indicator_signals if available
        if 'indicator_signals' in df.columns:
            columns.append('indicator_signals')
        
        # Add highest_price and lowest_price if available (for max/min profit calculation)
        if 'highest_price' in df.columns:
            columns.append('highest_price')
        if 'lowest_price' in df.columns:
            columns.append('lowest_price')
        
        # Only include columns that exist in the dataframe
        available_columns = [c for c in columns if c in df.columns]
        return df[available_columns]
    
    def get_total_pnl(self) -> float:
        """Calculate total realized PnL (excluding paper trades)."""
        closed_orders = [o for o in self.order_history if o['status'] == 'CLOSED' and not o.get('paper_trade', False)]
        return sum(o['pnl'] for o in closed_orders)
    
    def _print_analysis(self, result: dict):
        """Print detailed analysis."""
        print(f"\n{'='*70}")
        print(f"📊 ANALYSIS: {result['symbol']}")
        print(f"{'='*70}")
        print(f"💰 Latest Price: ₹{result['latest_price']:.2f}")
        print(f"🎯 Final Signal: {result['final_signal']}")
        print(f"🤝 Agreement: {result['agreement_score']:.1%}")
        print(f"\nSignal Breakdown: {result['signal_breakdown']}")
        print(f"\nIndividual Indicators:")
        for indicator, signal in result['indicator_signals'].items():
            print(f"   {indicator:20s}: {signal}")
        print(f"{'='*70}\n")
    
    def get_recovery_history(self) -> list:
        """Get recovery history for display."""
        # Convert datetime objects to strings for JSON serialization
        history = []
        for item in self.recovery_history:
            item_copy = item.copy()
            if isinstance(item_copy.get('timestamp'), datetime):
                item_copy['timestamp'] = item_copy['timestamp'].isoformat()
            history.append(item_copy)
        return history
    
    def get_loss_history(self) -> list:
        """Get loss history for display."""
        # Convert datetime objects to strings for JSON serialization
        history = []
        for item in self.loss_history:
            item_copy = item.copy()
            if isinstance(item_copy.get('timestamp'), datetime):
                item_copy['timestamp'] = item_copy['timestamp'].isoformat()
            history.append(item_copy)
        return history
    
    def get_loss_recovery_status(self) -> dict:
        """Get current loss recovery status per symbol."""
        return {
            'symbol_losses': self.symbol_losses.copy(),
            'total_unrecovered_loss': sum(self.symbol_losses.values()),
            'symbols_with_loss': list(self.symbol_losses.keys())
        }
    
    def get_lot_size(self, symbol: str) -> int:
        """Get lot size for a symbol."""
        lot_size = self.lot_sizes.get(symbol, self.default_lot_size)
        # Ensure lot_size is valid (positive integer)
        if lot_size is None or lot_size <= 0:
            return 0  # Return 0 to indicate invalid lot size
        return int(lot_size)
    
    def calculate_dynamic_quantity(self, symbol: str, price: float, available_capital: float = None, position_type: str = "LONG") -> int:
        """
        Calculate dynamic quantity based on available capital, lot size, and risk per trade.
        
        Args:
            symbol: Trading symbol
            price: Entry price
            available_capital: Available capital (if None, uses actual_capital)
        
        Returns:
            Quantity in lots (will be multiplied by lot size)
        """
        if available_capital is None:
            available_capital = self.initial_capital
        
        # Ensure available capital is positive
        if available_capital <= 0:
            print(f"⚠️  Warning: Available capital is ₹{available_capital:.2f}, cannot calculate quantity")
            return 0
        
        # Get lot size for symbol
        lot_size = self.get_lot_size(symbol)
        
        # If lot size is 0 or invalid, use default lot size instead of fixed quantity
        if lot_size <= 0:
            lot_size = self.default_lot_size
            if not lot_size or lot_size <= 0:
                print(f"⚠️  Invalid lot size and no default lot size for {symbol}. Cannot calculate quantity.")
                return 0
            print(f"⚠️  Invalid lot size for {symbol}. Using default lot size: {lot_size}")
        
        # Calculate maximum capital we can use for this trade
        # Get configurable capital percentage from config
        backtest_mode_check = self.config.get('backtest', {}).get('enabled', False)
        risk_config = self.config.get('risk_management', {})
        
        if backtest_mode_check:
            # In backtesting, use configured percentage (default 50%)
            capital_pct_raw = risk_config.get('capital_percentage_per_trade_backtest', 50.0)
            capital_percentage = float(capital_pct_raw) / 100.0
            print(f"📊 Backtest mode: Using {capital_pct_raw}% of capital per trade")
        else:
            # In live trading, use configured percentage (default 20%)
            capital_pct_raw = risk_config.get('capital_percentage_per_trade_intraday', 20.0)
            capital_percentage = float(capital_pct_raw) / 100.0
            print(f"📊 Intraday mode: Using {capital_pct_raw}% of capital per trade (from config: {risk_config.get('capital_percentage_per_trade_intraday', 'NOT FOUND')})")
        
        max_capital_per_trade = available_capital * capital_percentage
        print(f"💰 Capital allocation: {capital_percentage*100:.0f}% of ₹{available_capital:,.2f} = ₹{max_capital_per_trade:,.2f} per trade")
        
        # Calculate quantity based on available capital
        # Quantity = (max_capital_per_trade) / (price * lot_size) * lot_size
        cost_per_lot = price * lot_size
        
        if cost_per_lot <= 0:
            print(f"⚠️  Invalid price or lot size: price={price}, lot_size={lot_size}")
            # Fallback to default quantity
            default_qty = self.config.get('trading', {}).get('default_quantity', None)
            if default_qty and default_qty > 0:
                return int(default_qty)
            return 25  # Last resort fallback
        
        # Margin per lot depends on LONG vs SHORT
        if position_type == 'SHORT':
            # Use configured short margin per lot if provided, otherwise fallback to premium cost
            short_margin_per_lot = risk_config.get('short_margin_per_lot', None)
            if short_margin_per_lot is not None:
                margin_per_lot = float(short_margin_per_lot)
            else:
                margin_per_lot = cost_per_lot
        else:
            # LONG (option buying): margin is premium cost per lot
            margin_per_lot = cost_per_lot
        
        if margin_per_lot <= 0:
            print(f"⚠️  Invalid margin per lot: {margin_per_lot}")
            return 0
        
        # Calculate number of lots we can afford (floor)
        max_lots = int(max_capital_per_trade / margin_per_lot)
        
        # Ensure we use at least 1 lot only if it fits within the capital percentage limit
        if max_lots < 1:
            if max_capital_per_trade >= cost_per_lot:
                max_lots = 1
                print(f"📊 Using 1 lot within capital percentage limit: ₹{max_capital_per_trade:.2f}")
            else:
                print(f"⚠️  Insufficient capital for 1 lot. Max per trade: ₹{max_capital_per_trade:.2f}, Required: ₹{cost_per_lot:.2f}")
                return 0
        
        # Calculate final quantity (lots * lot_size)
        if max_lots < 1:
            print(f"⚠️  Insufficient capital for 1 lot. Max per trade: ₹{max_capital_per_trade:.2f}, Required: ₹{margin_per_lot:.2f}")
            return 0
        quantity = max_lots * lot_size
        
        # Verify we don't exceed available capital (safety check)
        total_cost = quantity * price
        if total_cost > available_capital:
            # Reduce to what we can afford
            affordable_lots = int(available_capital / cost_per_lot)
            if affordable_lots >= 1:
                quantity = affordable_lots * lot_size
                print(f"📊 Quantity adjusted to fit available capital: {quantity} lots (from {max_lots} lots)")
            else:
                print(f"⚠️  Cannot afford calculated quantity. Available: ₹{available_capital:.2f}, Required: ₹{total_cost:.2f}")
                return 0
            if quantity == 0:
                print(f"⚠️  Cannot afford any lots. Available: ₹{available_capital:.2f}, Cost per lot: ₹{cost_per_lot:.2f}")
                return 0
        
        return quantity
    
    def get_open_positions_display(self) -> List[Dict]:
        """Get open positions formatted for display, including LTP and change %."""
        positions_list = []
        for symbol, position in self.current_positions.items():
            ltp = position.get('current_price', position['entry_price'])
            day_open = self.day_open_prices.get(symbol, position['entry_price'])
            
            change = ltp - day_open
            change_pct = (change / day_open * 100) if day_open > 0 else 0

            positions_list.append({
                "symbol": symbol,
                "ltp": ltp,
                "change": change,
                "change_pct": change_pct,
                "final_signal": self.signal_aggregator.get_final_signal(symbol), # Requires modification in SignalAggregator
                "agreement_score": self.signal_aggregator.get_agreement_score_for_symbol(symbol), # Requires modification
                "indicator_signals": self.indicator_manager.get_signals_for_symbol(symbol) # Requires modification
            })
        return positions_list

    def get_summary(self) -> dict:
        """Get trading summary with advanced metrics."""
        total_orders = len(self.order_history)
        open_orders = len(self.current_positions)
        closed_orders_list = [o for o in self.order_history if o['status'] == 'CLOSED']
        
        # Separate real and paper trades
        real_closed_orders = [o for o in closed_orders_list if not o.get('paper_trade', False)]
        paper_closed_orders = [o for o in closed_orders_list if o.get('paper_trade', False)]
        
        closed_orders = len(real_closed_orders)
        paper_trades_count = len(paper_closed_orders)
        total_pnl = self.get_total_pnl()  # Already excludes paper trades
        
        # Calculate win rate (real trades only)
        win_rate = 0.0
        realized_pnl = total_pnl
        if closed_orders > 0:
            winning_trades = len([o for o in real_closed_orders if o['pnl'] > 0])
            win_rate = winning_trades / closed_orders
        
        summary = {
            'total_orders': total_orders,
            'open_positions': open_orders,
            'closed_orders': closed_orders,
            'paper_trades': paper_trades_count,
            'total_pnl': total_pnl,
            'realized_pnl': realized_pnl,
            'win_rate': win_rate,
            'indicators_registered': len(self.indicator_manager),
            'consecutive_losses': self.consecutive_losses,
            'paper_trading_mode': self.paper_trading_mode,
            'actual_capital': self.actual_capital,
            'hypothetical_capital': self.hypothetical_capital,
            'circuit_breaker_savings': self.actual_capital - self.hypothetical_capital
        }
        
        # Add advanced metrics if available
        if self.advanced_features:
            risk_status = self.risk_manager.get_risk_status()
            summary.update({
                'risk_multiplier': risk_status['risk_multiplier'],
                'trading_halted': risk_status['trading_halted'],
                'daily_pnl': risk_status['daily_pnl'],
                'daily_trades': risk_status['daily_trades']
            })
        
        return summary
    
    # ========================================================================
    # Modular Component Accessors
    # These properties provide access to the new modular components
    # for use in new code paths while maintaining backward compatibility
    # ========================================================================
    
    @property
    def slippage_handler(self) -> SlippageHandler:
        """Get the slippage handler component."""
        return self._slippage_handler
    
    @property
    def quantity_calculator(self) -> QuantityCalculator:
        """Get the quantity calculator component."""
        return self._quantity_calculator
    
    @property
    def circuit_breaker(self) -> CircuitBreaker:
        """Get the circuit breaker component."""
        return self._circuit_breaker
    
    @property
    def loss_recovery_manager(self) -> LossRecovery:
        """Get the loss recovery manager component."""
        return self._loss_recovery
    
    @property
    def signal_analyzer(self) -> SignalAnalyzer:
        """Get the signal analyzer component."""
        return self._signal_analyzer
    
    @property
    def position_manager(self) -> PositionManager:
        """Get the position manager component."""
        return self._position_manager
    
    @property
    def order_manager_component(self) -> OrderManager:
        """Get the order manager component."""
        return self._order_manager
    
    @property
    def broker(self):
        """
        Get the broker component.
        
        Returns:
            Broker instance (PaperBroker or LiveBroker) or None if not enabled.
        """
        return getattr(self, '_broker', None)
    
    def place_broker_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float = 0.0,
        order_type: str = "MARKET",
        product_type: str = "INTRADAY",
        tag: str = ""
    ) -> dict:
        """
        Place an order through the broker.
        
        This method routes orders through the broker system when enabled.
        Falls back to internal order handling when broker is not available.
        
        Args:
            symbol: Trading symbol
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            price: Order price (0 for market orders)
            order_type: 'MARKET', 'LIMIT', etc.
            product_type: 'INTRADAY', 'DELIVERY', etc.
            tag: Custom tag for tracking
            
        Returns:
            Dictionary with order details
        """
        if self._broker is None:
            # Broker not enabled - return info for internal handling
            return {
                'broker_enabled': False,
                'message': 'Broker not enabled, using internal order management'
            }
        
        try:
            from trading_system.core.broker import OrderSide, OrderType
            
            # Convert string to enums
            broker_side = OrderSide.BUY if side.upper() == 'BUY' else OrderSide.SELL
            
            type_map = {
                'MARKET': OrderType.MARKET,
                'LIMIT': OrderType.LIMIT,
                'STOP_LOSS': OrderType.STOP_LOSS,
                'STOP_LIMIT': OrderType.STOP_LIMIT
            }
            broker_type = type_map.get(order_type.upper(), OrderType.MARKET)
            
            # Place order through broker
            order = self._broker.place_order(
                symbol=symbol,
                side=broker_side,
                quantity=quantity,
                price=price,
                order_type=broker_type,
                product_type=product_type,
                tag=tag
            )
            
            return {
                'broker_enabled': True,
                'order_id': order.order_id,
                'broker_order_id': order.broker_order_id,
                'status': order.status.value,
                'filled_quantity': order.filled_quantity,
                'average_price': order.average_price,
                'order': order.to_dict()
            }
            
        except Exception as e:
            print(f"⚠️  Broker order failed: {e}")
            return {
                'broker_enabled': True,
                'error': str(e),
                'message': 'Broker order failed'
            }
    
    def sync_modular_components(self):
        """
        Synchronize state between legacy attributes and modular components.
        Call this after significant state changes if using both interfaces.
        """
        # Sync circuit breaker state
        self._circuit_breaker.consecutive_losses = self.consecutive_losses
        self._circuit_breaker.paper_trading_mode = self.paper_trading_mode
        
        # Sync loss recovery state
        self._loss_recovery.symbol_losses = self.symbol_losses.copy()
        
        # Sync quantity calculator lot sizes
        self._quantity_calculator.lot_sizes = self.lot_sizes.copy()
        self._quantity_calculator.default_lot_size = self.default_lot_size
