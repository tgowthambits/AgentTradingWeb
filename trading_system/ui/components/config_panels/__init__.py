"""
Configuration Panels Module

Contains configuration panel classes for different settings sections:
- SymbolsConfigPanel: Symbol and lot size configuration
- TradingConfigPanel: Trading settings (auto-trade, intervals, etc.)
- IndicatorsConfigPanel: Indicator enable/disable and weights
- RiskConfigPanel: Risk management settings
- ExitStrategyConfigPanel: Exit strategy and profit target settings
- BacktestConfigPanel: Backtest-specific settings
"""

from .symbols_config import SymbolsConfigPanel
from .trading_config import TradingConfigPanel
from .indicators_config import IndicatorsConfigPanel
from .risk_config import RiskConfigPanel
from .exit_strategy_config import ExitStrategyConfigPanel
from .backtest_config import BacktestConfigPanel

__all__ = [
    'SymbolsConfigPanel',
    'TradingConfigPanel',
    'IndicatorsConfigPanel',
    'RiskConfigPanel',
    'ExitStrategyConfigPanel',
    'BacktestConfigPanel'
]
