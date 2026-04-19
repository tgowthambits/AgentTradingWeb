"""
Summary Table Manager Module

Manages the performance summary tables for intraday and backtest results,
displaying key trading metrics and statistics.
"""

from typing import Dict, Any, Optional, Callable
import pandas as pd
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem
from PySide6.QtGui import QColor


class SummaryTableManager:
    """
    Manager for performance summary tables.
    
    This class handles:
    - Display of trading performance metrics
    - Win rate, profit factor, and other statistics
    - Color-coded metric values
    - Intraday vs backtest summary formatting
    
    Attributes:
        table: The QTableWidget to manage
        config: Configuration dictionary
    """
    
    def __init__(self, table: QTableWidget = None, config: Dict[str, Any] = None):
        """
        Initialize the SummaryTableManager.
        
        Args:
            table: QTableWidget to manage
            config: Configuration dictionary
        """
        self.table = table
        self.config = config or {}
        self._calculate_metrics_func: Optional[Callable] = None
        self._get_closed_orders_func: Optional[Callable] = None
    
    def set_table(self, table: QTableWidget):
        """Set the table widget."""
        self.table = table
    
    def set_calculate_metrics_func(self, func: Callable):
        """Set the metrics calculation function."""
        self._calculate_metrics_func = func
    
    def set_get_closed_orders_func(self, func: Callable):
        """Set the function to get closed orders."""
        self._get_closed_orders_func = func
    
    def update_intraday_summary(self, summary: Dict[str, Any]):
        """
        Update intraday performance summary table.
        
        Args:
            summary: Dictionary containing summary statistics
        """
        if not self.table:
            return
        
        self.table.setRowCount(0)
        
        # Get initial capital
        backtest_config = self.config.get('backtest', {})
        initial_capital = backtest_config.get('initial_capital', 20000)
        
        # Get closed orders for detailed metrics
        closed_orders = None
        if self._get_closed_orders_func:
            closed_orders = self._get_closed_orders_func()
        
        # Calculate metrics if we have closed orders
        metrics = {}
        if closed_orders is not None and not closed_orders.empty and self._calculate_metrics_func:
            metrics = self._calculate_metrics_func(closed_orders, initial_capital)
        
        # Add summary data
        actual_capital = summary.get('actual_capital', initial_capital)
        hypothetical_capital = summary.get('hypothetical_capital', initial_capital)
        circuit_breaker_savings = summary.get('circuit_breaker_savings', 0)
        paper_trades = summary.get('paper_trades', 0)
        consecutive_losses = summary.get('consecutive_losses', 0)
        
        # Build summary rows
        summary_data = [
            ("Total PnL", metrics.get('Total PnL', f"₹{summary.get('total_pnl', 0):,.2f}")),
            ("Realized PnL", f"₹{summary.get('realized_pnl', 0):,.2f}"),
            ("Win Rate", metrics.get('Win Rate', f"{summary.get('win_rate', 0)*100:.2f}%")),
            ("Total Trades", str(summary.get('closed_orders', 0))),
            ("Open Positions", str(summary.get('open_positions', 0))),
            ("Winning Trades", metrics.get('Winning Trades', '0')),
            ("Losing Trades", metrics.get('Losing Trades', '0')),
            ("Average Win", metrics.get('Average Win', '₹0')),
            ("Average Loss", metrics.get('Average Loss', '₹0')),
            ("Profit Factor", metrics.get('Profit Factor', 'N/A')),
            ("Expectancy", metrics.get('Expectancy', '₹0')),
            ("", ""),  # Separator
            ("Actual Capital", f"₹{actual_capital:,.2f}"),
            ("Hypothetical Capital", f"₹{hypothetical_capital:,.2f}"),
            ("Circuit Breaker Savings", f"₹{circuit_breaker_savings:,.2f}"),
            ("Paper Trades", str(paper_trades)),
            ("Consecutive Losses", str(consecutive_losses)),
        ]
        
        for metric_name, metric_value in summary_data:
            self._add_metric_row(metric_name, metric_value)
    
    def update_backtest_summary(self, summary: Dict[str, Any], metrics: Dict[str, Any] = None):
        """
        Update backtest performance summary table.
        
        Args:
            summary: Dictionary containing summary statistics
            metrics: Pre-calculated metrics dictionary
        """
        if not self.table:
            return
        
        self.table.setRowCount(0)
        
        if metrics is None:
            metrics = {}
        
        # Build summary rows
        summary_data = [
            ("Total PnL", metrics.get('Total PnL', f"₹{summary.get('total_pnl', 0):,.2f}")),
            ("Return %", metrics.get('Return %', '0%')),
            ("Win Rate", metrics.get('Win Rate', '0%')),
            ("", ""),  # Separator
            ("Total Trades", metrics.get('Total Trades', str(summary.get('closed_orders', 0)))),
            ("Winning Trades", metrics.get('Winning Trades', '0')),
            ("Losing Trades", metrics.get('Losing Trades', '0')),
            ("", ""),  # Separator
            ("Average Win", metrics.get('Average Win', '₹0')),
            ("Average Loss", metrics.get('Average Loss', '₹0')),
            ("Largest Win", metrics.get('Largest Win', '₹0')),
            ("Largest Loss", metrics.get('Largest Loss', '₹0')),
            ("", ""),  # Separator
            ("Profit Factor", metrics.get('Profit Factor', 'N/A')),
            ("Expectancy", metrics.get('Expectancy', '₹0')),
            ("Sharpe Ratio", metrics.get('Sharpe Ratio', 'N/A')),
            ("Sortino Ratio", metrics.get('Sortino Ratio', 'N/A')),
            ("Calmar Ratio", metrics.get('Calmar Ratio', 'N/A')),
            ("", ""),  # Separator
            ("Max Drawdown", metrics.get('Max Drawdown', '0%')),
            ("Max Drawdown Amount", metrics.get('Max Drawdown Amount', '₹0')),
            ("Recovery Factor", metrics.get('Recovery Factor', 'N/A')),
            ("", ""),  # Separator
            ("Initial Capital", metrics.get('Initial Capital', f"₹{self.config.get('backtest', {}).get('initial_capital', 20000):,.2f}")),
            ("Final Capital", metrics.get('Final Capital', f"₹{summary.get('actual_capital', 0):,.2f}")),
            ("", ""),  # Separator
            ("Paper Trades", str(summary.get('paper_trades', 0))),
            ("Real Trades", str(summary.get('real_trades', 0))),
            ("Circuit Breaker Savings", f"₹{summary.get('circuit_breaker_savings', 0):,.2f}"),
        ]
        
        for metric_name, metric_value in summary_data:
            self._add_metric_row(metric_name, metric_value)
    
    def _add_metric_row(self, metric_name: str, metric_value: str):
        """Add a metric row to the table."""
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Metric name column
        name_item = QTableWidgetItem(metric_name)
        name_item.setForeground(QColor(200, 200, 200))  # Light gray
        self.table.setItem(row, 0, name_item)
        
        # Metric value column
        value_item = QTableWidgetItem(str(metric_value))
        
        # Color code based on metric type and value
        color = self._get_metric_color(metric_name, metric_value)
        value_item.setForeground(color)
        
        self.table.setItem(row, 1, value_item)
    
    def _get_metric_color(self, metric_name: str, metric_value: str) -> QColor:
        """Get color based on metric type and value."""
        value_str = str(metric_value)
        
        # PnL-related metrics
        if any(x in metric_name.lower() for x in ['pnl', 'profit', 'win', 'savings']):
            if '₹' in value_str:
                try:
                    amount = float(value_str.replace('₹', '').replace(',', ''))
                    if amount > 0:
                        return QColor(34, 139, 34)  # Green
                    elif amount < 0:
                        return QColor(220, 20, 60)  # Red
                except:
                    pass
        
        # Percentage-related metrics
        if '%' in value_str:
            try:
                pct = float(value_str.replace('%', '').replace('+', ''))
                if 'drawdown' in metric_name.lower():
                    # Drawdown is negative, lower is better
                    if pct > 20:
                        return QColor(220, 20, 60)  # Red - high drawdown
                    elif pct > 10:
                        return QColor(255, 215, 0)  # Yellow - medium drawdown
                    else:
                        return QColor(34, 139, 34)  # Green - low drawdown
                elif 'win rate' in metric_name.lower():
                    if pct >= 50:
                        return QColor(34, 139, 34)  # Green
                    else:
                        return QColor(220, 20, 60)  # Red
                elif 'return' in metric_name.lower():
                    if pct > 0:
                        return QColor(34, 139, 34)  # Green
                    elif pct < 0:
                        return QColor(220, 20, 60)  # Red
            except:
                pass
        
        # Ratio metrics
        if 'ratio' in metric_name.lower() or 'factor' in metric_name.lower():
            try:
                ratio = float(value_str.replace('N/A', '0'))
                if 'profit factor' in metric_name.lower():
                    if ratio >= 1.5:
                        return QColor(34, 139, 34)  # Green
                    elif ratio >= 1.0:
                        return QColor(255, 215, 0)  # Yellow
                    else:
                        return QColor(220, 20, 60)  # Red
                elif 'sharpe' in metric_name.lower():
                    if ratio >= 1.0:
                        return QColor(34, 139, 34)  # Green
                    elif ratio >= 0:
                        return QColor(255, 215, 0)  # Yellow
                    else:
                        return QColor(220, 20, 60)  # Red
            except:
                pass
        
        # Default color
        return QColor(255, 255, 255)  # White
    
    def clear(self):
        """Clear the table."""
        if self.table:
            self.table.setRowCount(0)
    
    def get_row_count(self) -> int:
        """Get the number of rows in the table."""
        if self.table:
            return self.table.rowCount()
        return 0
