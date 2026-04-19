"""
Chart Dialogs Module

Provides interactive chart popup dialogs using Plotly.
"""

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from PySide6.QtWidgets import QMainWindow, QMessageBox, QWidget
from PySide6.QtWebEngineWidgets import QWebEngineView


class ChartDialogs:
    """
    Manager for chart popup dialogs.
    
    This class provides:
    - Price trend popup charts
    - Metric trend popup charts
    - Plotly chart display in QWebEngineView
    
    Attributes:
        parent: Parent widget for dialogs
        config: Configuration dictionary
        ltp_history: Price history data
        metrics_history: Metrics history data
    """
    
    def __init__(self, parent: QWidget = None, config: Dict[str, Any] = None):
        """
        Initialize the ChartDialogs.
        
        Args:
            parent: Parent widget for dialogs
            config: Configuration dictionary
        """
        self.parent = parent
        self.config = config or {}
        self.ltp_history: Dict[str, List] = {}
        self.metrics_history: Dict[str, List] = {}
    
    def set_ltp_history(self, ltp_history: Dict[str, List]):
        """Set LTP history data."""
        self.ltp_history = ltp_history
    
    def set_metrics_history(self, metrics_history: Dict[str, List]):
        """Set metrics history data."""
        self.metrics_history = metrics_history
    
    def show_price_trend(self, symbol: str):
        """
        Show interactive price trend chart using Plotly.
        
        Args:
            symbol: Symbol to show price trend for
        """
        try:
            import plotly.graph_objects as go
        except ImportError:
            QMessageBox.critical(
                self.parent, "Error",
                "plotly is required for interactive charts.\nInstall it with: pip install plotly"
            )
            return
        
        if symbol not in self.ltp_history or len(self.ltp_history[symbol]) < 2:
            QMessageBox.information(self.parent, "Info", "Insufficient data to show trend.")
            return
        
        # Get data
        timestamps, prices = zip(*self.ltp_history[symbol])
        symbol_short = symbol.split(':')[-1]
        
        # Create chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=prices,
            mode='lines+markers',
            name='Price',
            line=dict(color='#1976d2', width=2),
            fill='tozeroy',
            fillcolor='rgba(25, 118, 210, 0.2)'
        ))
        
        fig.update_layout(
            title=f"Price Trend: {symbol_short}",
            xaxis_title="Time",
            yaxis_title="Price",
            height=600,
            template='plotly_dark'
        )
        
        self._show_plotly_chart(fig, f"Price Trend: {symbol_short}")
    
    def show_metric_trend(self, metric_name: str, metric_key: str):
        """
        Show interactive metric trend chart.
        
        Args:
            metric_name: Display name for the metric
            metric_key: Key to look up in metrics_history
        """
        try:
            import plotly.graph_objects as go
        except ImportError:
            QMessageBox.critical(self.parent, "Error", "plotly is required for interactive charts.")
            return
        
        if metric_key not in self.metrics_history or len(self.metrics_history[metric_key]) < 2:
            QMessageBox.information(self.parent, "Info", "Insufficient data to show trend.")
            return
        
        iterations = self.metrics_history.get('iteration', list(range(len(self.metrics_history[metric_key]))))
        values = self.metrics_history[metric_key]
        
        # Create chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=iterations,
            y=values,
            mode='lines+markers',
            name=metric_name,
            line=dict(color='#2e7d32', width=2),
            fill='tonexty',
            fillcolor='rgba(46, 125, 50, 0.2)'
        ))
        
        fig.update_layout(
            title=f"{metric_name} Trend Over Time",
            xaxis_title="Iteration",
            yaxis_title=metric_name,
            height=600,
            template='plotly_dark'
        )
        
        self._show_plotly_chart(fig, f"Trend: {metric_name}")
    
    def show_equity_curve(self, timestamps: List[datetime], equity_values: List[float], 
                          title: str = "Equity Curve"):
        """
        Show interactive equity curve chart.
        
        Args:
            timestamps: List of timestamps
            equity_values: List of equity values
            title: Chart title
        """
        try:
            import plotly.graph_objects as go
        except ImportError:
            QMessageBox.critical(self.parent, "Error", "plotly is required for interactive charts.")
            return
        
        if len(timestamps) < 2:
            QMessageBox.information(self.parent, "Info", "Insufficient data to show equity curve.")
            return
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=equity_values,
            mode='lines',
            name='Equity',
            line=dict(color='#3b82f6', width=2),
            fill='tozeroy',
            fillcolor='rgba(59, 130, 246, 0.2)'
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Time",
            yaxis_title="Equity",
            height=600,
            template='plotly_dark'
        )
        
        self._show_plotly_chart(fig, title)
    
    def show_pnl_distribution(self, pnl_values: List[float], title: str = "PnL Distribution"):
        """
        Show PnL distribution histogram.
        
        Args:
            pnl_values: List of PnL values
            title: Chart title
        """
        try:
            import plotly.graph_objects as go
        except ImportError:
            QMessageBox.critical(self.parent, "Error", "plotly is required for interactive charts.")
            return
        
        if len(pnl_values) < 2:
            QMessageBox.information(self.parent, "Info", "Insufficient data to show distribution.")
            return
        
        # Create histogram with separate colors for wins and losses
        wins = [p for p in pnl_values if p > 0]
        losses = [p for p in pnl_values if p <= 0]
        
        fig = go.Figure()
        
        if wins:
            fig.add_trace(go.Histogram(
                x=wins,
                name='Wins',
                marker_color='#22c55e',
                opacity=0.7
            ))
        
        if losses:
            fig.add_trace(go.Histogram(
                x=losses,
                name='Losses',
                marker_color='#ef4444',
                opacity=0.7
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title="PnL",
            yaxis_title="Count",
            barmode='overlay',
            height=600,
            template='plotly_dark'
        )
        
        self._show_plotly_chart(fig, title)
    
    def show_drawdown_chart(self, timestamps: List[datetime], drawdown_values: List[float],
                            title: str = "Drawdown"):
        """
        Show drawdown chart.
        
        Args:
            timestamps: List of timestamps
            drawdown_values: List of drawdown percentages (negative values)
            title: Chart title
        """
        try:
            import plotly.graph_objects as go
        except ImportError:
            QMessageBox.critical(self.parent, "Error", "plotly is required for interactive charts.")
            return
        
        if len(timestamps) < 2:
            QMessageBox.information(self.parent, "Info", "Insufficient data to show drawdown.")
            return
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=drawdown_values,
            mode='lines',
            name='Drawdown',
            line=dict(color='#ef4444', width=2),
            fill='tozeroy',
            fillcolor='rgba(239, 68, 68, 0.3)'
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Time",
            yaxis_title="Drawdown (%)",
            height=600,
            template='plotly_dark'
        )
        
        self._show_plotly_chart(fig, title)
    
    def _show_plotly_chart(self, fig, title: str):
        """
        Display Plotly chart in a popup window.
        
        Args:
            fig: Plotly figure object
            title: Window title
        """
        try:
            html_content = fig.to_html(include_plotlyjs='cdn')
            
            # Create popup window
            chart_window = QMainWindow(self.parent)
            chart_window.setWindowTitle(title)
            chart_window.setGeometry(100, 100, 1000, 700)
            
            # Create web view
            web_view = QWebEngineView()
            web_view.setHtml(html_content)
            
            chart_window.setCentralWidget(web_view)
            chart_window.show()
            
        except Exception as e:
            QMessageBox.critical(self.parent, "Error", f"Failed to create chart: {str(e)}")
    
    def get_metric_map(self) -> Dict[str, str]:
        """
        Get mapping of metric display names to keys.
        
        Returns:
            Dictionary mapping display names to metric keys
        """
        return {
            "Total PnL": "total_pnl",
            "Return %": "returns_pct",
            "Win Rate": "win_rate",
            "Sharpe Ratio": "sharpe_ratio",
            "Max Drawdown": "max_drawdown",
            "Profit Factor": "profit_factor",
            "Sortino Ratio": "sortino_ratio",
            "Calmar Ratio": "calmar_ratio",
            "Final Capital": "equity",
            "Average Win": "avg_win",
            "Average Loss": "avg_loss",
            "Expectancy per Trade": "expectancy"
        }
