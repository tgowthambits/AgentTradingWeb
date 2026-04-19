"""
Core Trading System Module

This module contains the core trading logic components including:
- TradingEngine: Main coordinator/facade for all trading operations
- PositionManager: Manages open trading positions
- OrderManager: Handles order history and execution tracking
- QuantityCalculator: Calculates dynamic trading quantities
- SlippageHandler: Applies slippage to entry/exit prices
- SignalAnalyzer: Generates trading signals from market data
- Risk modules: CircuitBreaker and LossRecovery

All components are designed to work together through the TradingEngine facade,
which maintains backward compatibility while delegating to specialized modules.
"""

# Main trading engine (facade)
from .trading_engine import TradingEngine

# Core components
from .position_manager import PositionManager
from .order_manager import OrderManager
from .quantity_calculator import QuantityCalculator
from .slippage_handler import SlippageHandler
from .signal_analyzer import SignalAnalyzer

# Risk management components
from .risk import CircuitBreaker, LossRecovery

# Existing components (for backward compatibility)
from .indicator_manager import IndicatorManager
from .signal_aggregator import SignalAggregator
from .indicator_loader import IndicatorLoader

# Optional advanced components (may not be available)
try:
    from .volatility_analyzer import VolatilityAnalyzer
    from .risk_manager import RiskManager
    from .risk.exit_strategy_manager import ExitStrategyManager
except ImportError:
    VolatilityAnalyzer = None
    RiskManager = None
    ExitStrategyManager = None

__all__ = [
    # Main facade
    'TradingEngine',
    
    # Core components
    'PositionManager',
    'OrderManager',
    'QuantityCalculator',
    'SlippageHandler',
    'SignalAnalyzer',
    
    # Risk management
    'CircuitBreaker',
    'LossRecovery',
    
    # Existing components
    'IndicatorManager',
    'SignalAggregator',
    'IndicatorLoader',
    
    # Optional advanced components
    'VolatilityAnalyzer',
    'RiskManager',
    'ExitStrategyManager',
]
