"""
Dashboard Updater Module

Handles throttled dashboard updates to prevent UI freezing.
"""

from typing import Dict, Any, Optional, Callable
from datetime import datetime
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFrame, QLabel, QTableWidget
import pandas as pd


class DashboardUpdater:
    """
    Handles throttled dashboard updates.
    
    This class manages:
    - Throttled update scheduling
    - Intraday dashboard updates
    - Backtest dashboard updates
    - Data history management
    
    Attributes:
        config: Configuration dictionary
        intraday_dashboard_data: Data storage for intraday dashboard
        backtest_dashboard_data: Data storage for backtest dashboard
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the DashboardUpdater.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.intraday_dashboard_data = {
            'pnl_history': [],
            'equity_history': [],
            'timestamps': [],
            'update_counter': 0
        }
        self.backtest_dashboard_data = {
            'pnl_history': [],
            'equity_history': [],
            'timestamps': [],
            'update_counter': 0
        }
        
        # Pending updates
        self.pending_dashboard_summary: Optional[Dict] = None
        self.pending_dashboard_type: str = 'intraday'
        
        # Callbacks
        self._update_kpi_tile_func: Optional[Callable] = None
        self._update_pnl_chart_func: Optional[Callable] = None
        self._update_equity_chart_func: Optional[Callable] = None
        self._update_distribution_chart_func: Optional[Callable] = None
        self._update_symbol_table_func: Optional[Callable] = None
        self._update_exit_reasons_func: Optional[Callable] = None
        self._calculate_metrics_func: Optional[Callable] = None
        self._get_closed_orders_func: Optional[Callable] = None
        
        # Widget references
        self.intraday_kpi_tiles: Dict[str, QFrame] = {}
        self.backtest_kpi_tiles: Dict[str, QFrame] = {}
        self.intraday_pnl_chart: Optional[QLabel] = None
        self.intraday_equity_chart: Optional[QLabel] = None
        self.backtest_pnl_chart: Optional[QLabel] = None
        self.backtest_equity_chart: Optional[QLabel] = None
        self.backtest_dist_chart: Optional[QLabel] = None
        self.intraday_symbol_table: Optional[QTableWidget] = None
        self.backtest_symbol_table: Optional[QTableWidget] = None
        self.intraday_exit_reasons_table: Optional[QTableWidget] = None
        self.backtest_exit_reasons_table: Optional[QTableWidget] = None
        
        # Timer
        self.update_timer: Optional[QTimer] = None
    
    def set_update_timer(self, timer: QTimer):
        """Set the update timer."""
        self.update_timer = timer
        if timer:
            timer.timeout.connect(self._process_pending_updates)
    
    def set_callbacks(self, update_kpi_tile: Callable = None, 
                     update_pnl_chart: Callable = None,
                     update_equity_chart: Callable = None,
                     update_distribution_chart: Callable = None,
                     update_symbol_table: Callable = None,
                     update_exit_reasons: Callable = None,
                     calculate_metrics: Callable = None,
                     get_closed_orders: Callable = None):
        """Set callback functions."""
        self._update_kpi_tile_func = update_kpi_tile
        self._update_pnl_chart_func = update_pnl_chart
        self._update_equity_chart_func = update_equity_chart
        self._update_distribution_chart_func = update_distribution_chart
        self._update_symbol_table_func = update_symbol_table
        self._update_exit_reasons_func = update_exit_reasons
        self._calculate_metrics_func = calculate_metrics
        self._get_closed_orders_func = get_closed_orders
    
    def set_intraday_widgets(self, kpi_tiles: Dict[str, QFrame], 
                             pnl_chart: QLabel = None,
                             equity_chart: QLabel = None,
                             symbol_table: QTableWidget = None,
                             exit_reasons_table: QTableWidget = None):
        """Set intraday dashboard widgets."""
        self.intraday_kpi_tiles = kpi_tiles
        self.intraday_pnl_chart = pnl_chart
        self.intraday_equity_chart = equity_chart
        self.intraday_symbol_table = symbol_table
        self.intraday_exit_reasons_table = exit_reasons_table
    
    def set_backtest_widgets(self, kpi_tiles: Dict[str, QFrame],
                             pnl_chart: QLabel = None,
                             equity_chart: QLabel = None,
                             dist_chart: QLabel = None,
                             symbol_table: QTableWidget = None,
                             exit_reasons_table: QTableWidget = None):
        """Set backtest dashboard widgets."""
        self.backtest_kpi_tiles = kpi_tiles
        self.backtest_pnl_chart = pnl_chart
        self.backtest_equity_chart = equity_chart
        self.backtest_dist_chart = dist_chart
        self.backtest_symbol_table = symbol_table
        self.backtest_exit_reasons_table = exit_reasons_table
    
    def schedule_intraday_update(self, summary: Dict):
        """
        Schedule a throttled intraday dashboard update.
        
        Args:
            summary: Summary data to update
        """
        self.pending_dashboard_summary = summary
        self.pending_dashboard_type = 'intraday'
        
        if self.update_timer and not self.update_timer.isActive():
            self.update_timer.start(200)  # 200ms throttle
    
    def schedule_backtest_update(self, summary: Dict):
        """
        Schedule a throttled backtest dashboard update.
        
        Args:
            summary: Summary data to update
        """
        self.pending_dashboard_summary = summary
        self.pending_dashboard_type = 'backtest'
        
        if self.update_timer and not self.update_timer.isActive():
            self.update_timer.start(500)  # 500ms throttle for backtest
    
    def _process_pending_updates(self):
        """Process any pending dashboard updates."""
        if self.pending_dashboard_summary is None:
            return
        
        summary = self.pending_dashboard_summary
        
        if self.pending_dashboard_type == 'intraday':
            self._update_intraday_dashboard(summary)
        elif self.pending_dashboard_type == 'backtest':
            self._update_backtest_dashboard(summary)
        
        self.pending_dashboard_summary = None
    
    def _update_intraday_dashboard(self, summary: Dict):
        """Update intraday dashboard with new data."""
        if not self.intraday_kpi_tiles:
            return
        
        try:
            # Extract metrics
            total_pnl = summary.get('total_pnl', 0)
            win_rate = summary.get('win_rate', 0) * 100
            total_trades = summary.get('closed_orders', 0)
            open_positions = summary.get('open_positions', 0)
            realized_pnl = summary.get('realized_pnl', 0)
            
            # Calculate additional metrics
            closed_orders = None
            if self._get_closed_orders_func:
                closed_orders = self._get_closed_orders_func()
            
            avg_win = 0
            avg_loss = 0
            profit_factor = 0
            
            if closed_orders is not None and not closed_orders.empty:
                winning_trades = closed_orders[closed_orders['pnl'] > 0]
                losing_trades = closed_orders[closed_orders['pnl'] < 0]
                
                if len(winning_trades) > 0:
                    avg_win = winning_trades['pnl'].mean()
                if len(losing_trades) > 0:
                    avg_loss = abs(losing_trades['pnl'].mean())
                
                if avg_loss > 0:
                    total_profit = winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0
                    total_loss = abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else 0
                    profit_factor = total_profit / total_loss if total_loss > 0 else 0
            
            # Update KPI tiles
            if self._update_kpi_tile_func:
                self._update_kpi_tile_func(self.intraday_kpi_tiles.get('total_pnl'), f'₹{total_pnl:,.2f}')
                self._update_kpi_tile_func(self.intraday_kpi_tiles.get('win_rate'), f'{win_rate:.2f}%')
                self._update_kpi_tile_func(self.intraday_kpi_tiles.get('total_trades'), str(total_trades))
                self._update_kpi_tile_func(self.intraday_kpi_tiles.get('open_positions'), str(open_positions))
                self._update_kpi_tile_func(self.intraday_kpi_tiles.get('realized_pnl'), f'₹{realized_pnl:,.2f}')
                self._update_kpi_tile_func(self.intraday_kpi_tiles.get('avg_win'), f'₹{avg_win:,.2f}')
                self._update_kpi_tile_func(self.intraday_kpi_tiles.get('avg_loss'), f'₹{avg_loss:,.2f}')
                self._update_kpi_tile_func(self.intraday_kpi_tiles.get('profit_factor'), f'{profit_factor:.2f}')
            
            # Update charts periodically
            self.intraday_dashboard_data['update_counter'] += 1
            
            if self.intraday_dashboard_data['update_counter'] % 10 == 0:
                current_time = datetime.now()
                self.intraday_dashboard_data['pnl_history'].append(total_pnl)
                self.intraday_dashboard_data['equity_history'].append(summary.get('actual_capital', 0))
                self.intraday_dashboard_data['timestamps'].append(current_time)
                
                # Keep only last 100 points
                if len(self.intraday_dashboard_data['timestamps']) > 100:
                    self.intraday_dashboard_data['pnl_history'] = self.intraday_dashboard_data['pnl_history'][-100:]
                    self.intraday_dashboard_data['equity_history'] = self.intraday_dashboard_data['equity_history'][-100:]
                    self.intraday_dashboard_data['timestamps'] = self.intraday_dashboard_data['timestamps'][-100:]
                
                # Update charts
                if len(self.intraday_dashboard_data['timestamps']) > 1:
                    if self._update_pnl_chart_func and self.intraday_pnl_chart:
                        self._update_pnl_chart_func(
                            self.intraday_pnl_chart,
                            self.intraday_dashboard_data['timestamps'],
                            self.intraday_dashboard_data['pnl_history'],
                            "Intraday PnL Over Time"
                        )
                    
                    if self._update_equity_chart_func and self.intraday_equity_chart:
                        self._update_equity_chart_func(
                            self.intraday_equity_chart,
                            self.intraday_dashboard_data['timestamps'],
                            self.intraday_dashboard_data['equity_history'],
                            "Intraday Equity Curve"
                        )
            
            # Update tables periodically
            if closed_orders is not None and not closed_orders.empty:
                if self.intraday_dashboard_data['update_counter'] % 20 == 0:
                    if self._update_symbol_table_func and self.intraday_symbol_table:
                        self._update_symbol_table_func(self.intraday_symbol_table, closed_orders)
                    if self._update_exit_reasons_func and self.intraday_exit_reasons_table:
                        self._update_exit_reasons_func(self.intraday_exit_reasons_table, closed_orders)
                        
        except Exception as e:
            print(f"Error updating intraday dashboard: {e}")
    
    def _update_backtest_dashboard(self, summary: Dict):
        """Update backtest dashboard with new data."""
        if not self.backtest_kpi_tiles:
            return
        
        try:
            # Get closed orders
            closed_orders = None
            if self._get_closed_orders_func:
                closed_orders = self._get_closed_orders_func()
            
            # Get initial capital
            backtest_config = self.config.get('backtest', {})
            initial_capital = backtest_config.get('initial_capital', 20000)
            
            if closed_orders is not None and not closed_orders.empty and self._calculate_metrics_func:
                metrics = self._calculate_metrics_func(closed_orders, initial_capital)
                
                # Extract values
                total_pnl = summary.get('total_pnl', 0)
                win_rate = float(str(metrics.get('Win Rate', '0%')).replace('%', ''))
                total_trades = summary.get('closed_orders', 0)
                sharpe_ratio = float(str(metrics.get('Sharpe Ratio', '0')).replace('N/A', '0'))
                max_drawdown = float(str(metrics.get('Max Drawdown', '0%')).replace('%', ''))
                profit_factor = float(str(metrics.get('Profit Factor', '0')).replace('N/A', '0'))
                expectancy = float(str(metrics.get('Expectancy', '₹0')).replace('₹', '').replace(',', '').replace('N/A', '0'))
                return_pct = float(str(metrics.get('Return %', '0%')).replace('%', ''))
                
                # Update KPI tiles
                if self._update_kpi_tile_func:
                    self._update_kpi_tile_func(self.backtest_kpi_tiles.get('total_pnl'), f'₹{total_pnl:,.2f}')
                    self._update_kpi_tile_func(self.backtest_kpi_tiles.get('win_rate'), f'{win_rate:.2f}%')
                    self._update_kpi_tile_func(self.backtest_kpi_tiles.get('total_trades'), str(total_trades))
                    self._update_kpi_tile_func(self.backtest_kpi_tiles.get('sharpe_ratio'), f'{sharpe_ratio:.2f}')
                    self._update_kpi_tile_func(self.backtest_kpi_tiles.get('max_drawdown'), f'{max_drawdown:.2f}%')
                    self._update_kpi_tile_func(self.backtest_kpi_tiles.get('profit_factor'), f'{profit_factor:.2f}')
                    self._update_kpi_tile_func(self.backtest_kpi_tiles.get('expectancy'), f'₹{expectancy:,.2f}')
                    self._update_kpi_tile_func(self.backtest_kpi_tiles.get('return_pct'), f'{return_pct:.2f}%')
                
                # Update charts periodically
                self.backtest_dashboard_data['update_counter'] += 1
                
                if self.backtest_dashboard_data['update_counter'] % 20 == 0:
                    current_time = datetime.now()
                    self.backtest_dashboard_data['pnl_history'].append(total_pnl)
                    self.backtest_dashboard_data['equity_history'].append(summary.get('actual_capital', initial_capital))
                    self.backtest_dashboard_data['timestamps'].append(current_time)
                    
                    # Keep only last 500 points
                    if len(self.backtest_dashboard_data['timestamps']) > 500:
                        self.backtest_dashboard_data['pnl_history'] = self.backtest_dashboard_data['pnl_history'][-500:]
                        self.backtest_dashboard_data['equity_history'] = self.backtest_dashboard_data['equity_history'][-500:]
                        self.backtest_dashboard_data['timestamps'] = self.backtest_dashboard_data['timestamps'][-500:]
                    
                    # Update charts
                    if len(self.backtest_dashboard_data['timestamps']) > 1:
                        if self._update_pnl_chart_func and self.backtest_pnl_chart:
                            self._update_pnl_chart_func(
                                self.backtest_pnl_chart,
                                self.backtest_dashboard_data['timestamps'],
                                self.backtest_dashboard_data['pnl_history'],
                                "Backtest PnL Over Time"
                            )
                        
                        if self._update_equity_chart_func and self.backtest_equity_chart:
                            self._update_equity_chart_func(
                                self.backtest_equity_chart,
                                self.backtest_dashboard_data['timestamps'],
                                self.backtest_dashboard_data['equity_history'],
                                "Backtest Equity Curve"
                            )
                    
                    # Update distribution chart
                    if self.backtest_dashboard_data['update_counter'] % 50 == 0:
                        if self._update_distribution_chart_func and self.backtest_dist_chart:
                            self._update_distribution_chart_func(self.backtest_dist_chart, closed_orders)
                
                # Update tables periodically
                if self.backtest_dashboard_data['update_counter'] % 50 == 0:
                    if self._update_symbol_table_func and self.backtest_symbol_table:
                        self._update_symbol_table_func(self.backtest_symbol_table, closed_orders, detailed=True)
                    if self._update_exit_reasons_func and self.backtest_exit_reasons_table:
                        self._update_exit_reasons_func(self.backtest_exit_reasons_table, closed_orders)
                        
        except Exception as e:
            print(f"Error updating backtest dashboard: {e}")
    
    def reset_intraday_data(self):
        """Reset intraday dashboard data."""
        self.intraday_dashboard_data = {
            'pnl_history': [],
            'equity_history': [],
            'timestamps': [],
            'update_counter': 0
        }
    
    def reset_backtest_data(self):
        """Reset backtest dashboard data."""
        self.backtest_dashboard_data = {
            'pnl_history': [],
            'equity_history': [],
            'timestamps': [],
            'update_counter': 0
        }
