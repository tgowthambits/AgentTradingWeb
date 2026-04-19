"""
UI Components Module

Contains reusable UI component classes organized by function:
- tables: LTPTableManager, PositionsTableManager, TradesTableManager, SummaryTableManager
- dashboard: DashboardPanel, ChartManager, DashboardUpdater
- config_panels: Symbol, Trading, Indicators, Risk, Exit Strategy, Backtest config panels

Usage:
    from trading_system.ui.components.tables import LTPTableManager
    from trading_system.ui.components.dashboard import DashboardPanel
    from trading_system.ui.components.config_panels import SymbolsConfigPanel
"""

# Table components
from .tables import (
    LTPTableManager,
    PositionsTableManager,
    TradesTableManager,
    SummaryTableManager
)

# Dashboard components
from .dashboard import (
    DashboardPanel,
    ChartManager,
    DashboardUpdater
)

# Config panel components
from .config_panels import (
    SymbolsConfigPanel,
    TradingConfigPanel,
    IndicatorsConfigPanel,
    RiskConfigPanel,
    ExitStrategyConfigPanel,
    BacktestConfigPanel
)

__all__ = [
    # Tables
    'LTPTableManager',
    'PositionsTableManager',
    'TradesTableManager',
    'SummaryTableManager',
    
    # Dashboard
    'DashboardPanel',
    'ChartManager',
    'DashboardUpdater',
    
    # Config Panels
    'SymbolsConfigPanel',
    'TradingConfigPanel',
    'IndicatorsConfigPanel',
    'RiskConfigPanel',
    'ExitStrategyConfigPanel',
    'BacktestConfigPanel',
]
