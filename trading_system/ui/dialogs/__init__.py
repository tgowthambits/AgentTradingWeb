"""
Dialogs Module

Contains dialog classes for various UI interactions:
- ChartDialogs: Interactive Plotly chart popups
- BacktestResultsDialog: Detailed backtest results display
- BacktestComparisonDialog: Compare multiple backtest runs
- BacktestExportDialog: Export options for backtest data
- ChartViewerDialog: TradingView Lightweight Charts viewer for candlestick data
- MultiSymbolChartDialog: Multi-symbol chart viewer with dropdown selector
"""

from .chart_dialogs import ChartDialogs
from .backtest_dialogs import (
    BacktestResultsDialog,
    BacktestComparisonDialog,
    BacktestExportDialog
)

try:
    from .chart_viewer_dialog import ChartViewerDialog, MultiSymbolChartDialog
    from .live_chart_dialog import LiveChartDialog
    CHART_VIEWER_AVAILABLE = True
except ImportError:
    CHART_VIEWER_AVAILABLE = False
    ChartViewerDialog = None
    MultiSymbolChartDialog = None
    LiveChartDialog = None

__all__ = [
    'ChartDialogs',
    'BacktestResultsDialog',
    'BacktestComparisonDialog',
    'BacktestExportDialog',
    'ChartViewerDialog',
    'MultiSymbolChartDialog',
    'LiveChartDialog',
    'CHART_VIEWER_AVAILABLE'
]
