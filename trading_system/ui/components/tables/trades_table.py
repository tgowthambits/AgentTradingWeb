"""
Trades Table Manager Module

Manages the completed trades table with trade history,
PnL display, and exit reason tracking.
"""

from typing import Dict, Any, List, Optional, Callable
import pandas as pd
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem
from PySide6.QtGui import QColor


class TradesTableManager:
    """
    Manager for completed trades tables.
    
    This class handles:
    - Display of completed trades with entry/exit details
    - PnL and return percentage calculation
    - Max/min profit display
    - Exit reason tracking
    - Paper vs real trade indication
    
    Attributes:
        table: The QTableWidget to manage
        config: Configuration dictionary
    """
    
    def __init__(self, table: QTableWidget = None, config: Dict[str, Any] = None):
        """
        Initialize the TradesTableManager.
        
        Args:
            table: QTableWidget to manage
            config: Configuration dictionary
        """
        self.table = table
        self.config = config or {}
        self._format_time_func: Optional[Callable] = None
        self._log_event_func: Optional[Callable] = None
    
    def set_table(self, table: QTableWidget):
        """Set the table widget."""
        self.table = table
    
    def set_format_time_func(self, func: Callable):
        """Set the time formatting function."""
        self._format_time_func = func
    
    def set_log_event_func(self, func: Callable):
        """Set the event logging function."""
        self._log_event_func = func
    
    def format_time(self, time_val) -> str:
        """Format time value for display."""
        if self._format_time_func:
            return self._format_time_func(time_val)
        if pd.isna(time_val) or time_val is None:
            return "N/A"
        try:
            if isinstance(time_val, str):
                return time_val
            elif hasattr(time_val, 'strftime'):
                return time_val.strftime("%Y-%m-%d %H:%M:%S")
            else:
                return pd.to_datetime(time_val).strftime("%Y-%m-%d %H:%M:%S")
        except:
            return str(time_val)[:19] if time_val else "N/A"
    
    def log_event(self, event_type: str, message: str):
        """Log an event."""
        if self._log_event_func:
            self._log_event_func(event_type, message)
    
    def update(self, trades_df: pd.DataFrame):
        """
        Update completed trades table.
        
        Args:
            trades_df: DataFrame containing completed trade data
        """
        if not self.table:
            return
        
        self.table.setRowCount(0)
        
        if trades_df.empty:
            return
        
        for idx, row in trades_df.iterrows():
            self._add_trade_row(row)
    
    def _add_trade_row(self, row: pd.Series):
        """Add a single trade row to the table."""
        symbol_short = row['symbol'].split(':')[-1]
        
        # Get locked entry price
        locked_entry_price = float(row.get('entry_price', 0.0))
        exit_price = float(row.get('exit_price', 0.0))
        
        if locked_entry_price <= 0:
            self.log_event("ERROR", f"Trade {row.get('order_id', 'unknown')} | Invalid entry_price: {locked_entry_price}")
            locked_entry_price = 0.0
        
        # Calculate return percentage
        if row['type'] == 'LONG':
            return_pct = ((exit_price - locked_entry_price) / locked_entry_price * 100) if locked_entry_price > 0 else 0
        else:
            return_pct = ((locked_entry_price - exit_price) / locked_entry_price * 100) if locked_entry_price > 0 else 0
        
        pnl = row['pnl']
        
        # Get exit reason
        exit_reason = row.get('exit_reason', 'N/A')
        if pd.isna(exit_reason):
            exit_reason = 'N/A'
        exit_reason_short = exit_reason[:40] if len(str(exit_reason)) > 40 else exit_reason
        
        # Format times
        entry_time = self.format_time(row.get('entry_time'))
        exit_time = self.format_time(row.get('exit_time'))
        
        # Add row
        table_row = self.table.rowCount()
        self.table.insertRow(table_row)
        
        # Column 0: Order ID
        self.table.setItem(table_row, 0, QTableWidgetItem(str(row['order_id'])))
        # Column 1: Symbol
        self.table.setItem(table_row, 1, QTableWidgetItem(symbol_short))
        # Column 2: Type
        self.table.setItem(table_row, 2, QTableWidgetItem(row['type']))
        
        # Column 3: Trade Type (PAPER/REAL)
        is_paper_trade = row.get('paper_trade', False)
        if pd.isna(is_paper_trade):
            is_paper_trade = False
        trade_type = "PAPER" if is_paper_trade else "REAL"
        trade_type_item = QTableWidgetItem(trade_type)
        if is_paper_trade:
            trade_type_item.setForeground(QColor(255, 215, 0))  # Gold
        else:
            trade_type_item.setForeground(QColor(255, 255, 255))  # White
        self.table.setItem(table_row, 3, trade_type_item)
        
        # Check if candle prices should be shown
        output_config = self.config.get('output', {})
        candle_config = output_config.get('show_candle_prices', {})
        show_candle_prices = candle_config.get('enabled', True)
        show_entry_high = candle_config.get('show_entry_high', True) if show_candle_prices else False
        show_exit_low = candle_config.get('show_exit_low', True) if show_candle_prices else False
        
        # Column 4: Entry Price
        self.table.setItem(table_row, 4, QTableWidgetItem(f"{locked_entry_price:.2f}"))
        
        # Column 5: Entry Candle High (if enabled)
        col_idx = 5
        if show_entry_high:
            entry_candle_high = row.get('entry_candle_high', None)
            if entry_candle_high is not None and not pd.isna(entry_candle_high):
                high_item = QTableWidgetItem(f"{float(entry_candle_high):.2f}")
                high_item.setForeground(QColor(150, 150, 150))  # Gray for candle prices
                self.table.setItem(table_row, col_idx, high_item)
            else:
                self.table.setItem(table_row, col_idx, QTableWidgetItem("N/A"))
            col_idx += 1
        
        # Column: Exit Price
        self.table.setItem(table_row, col_idx, QTableWidgetItem(f"{exit_price:.2f}"))
        col_idx += 1
        
        # Column: Exit Candle Low (if enabled)
        if show_exit_low:
            exit_candle_low = row.get('exit_candle_low', None)
            if exit_candle_low is not None and not pd.isna(exit_candle_low):
                low_item = QTableWidgetItem(f"{float(exit_candle_low):.2f}")
                low_item.setForeground(QColor(150, 150, 150))  # Gray for candle prices
                self.table.setItem(table_row, col_idx, low_item)
            else:
                self.table.setItem(table_row, col_idx, QTableWidgetItem("N/A"))
            col_idx += 1
        
        # Column: Quantity
        trade_quantity = row.get('quantity', 0)
        if trade_quantity <= 0:
            trade_quantity = row.get('original_quantity', 0)
            if trade_quantity <= 0:
                default_qty = self.config.get('trading', {}).get('default_quantity', None)
                trade_quantity = default_qty if default_qty and default_qty > 0 else 25
                self.log_event("WARNING", f"Trade {row['order_id']} | Quantity was 0, using fallback: {trade_quantity}")
        
        self.table.setItem(table_row, col_idx, QTableWidgetItem(str(int(trade_quantity))))
        col_idx += 1
        
        # Column: PnL
        self.table.setItem(table_row, col_idx, QTableWidgetItem(f"{pnl:+.2f}"))
        col_idx += 1
        
        # Column: Return %
        self.table.setItem(table_row, col_idx, QTableWidgetItem(f"{return_pct:+.2f}%"))
        col_idx += 1
        
        # Calculate max/min profit if not stored
        max_profit, min_profit = self._calculate_profit_extremes(
            row, locked_entry_price, exit_price, trade_quantity
        )
        avg_profit = float(row.get('avg_profit', 0.0))
        avg_loss = float(row.get('avg_loss', 0.0))
        
        # Column: Max Profit
        max_profit_item = QTableWidgetItem(f"{max_profit:+.2f}")
        self._set_pnl_color(max_profit_item, max_profit)
        self.table.setItem(table_row, col_idx, max_profit_item)
        col_idx += 1
        
        # Column: Min Profit
        min_profit_item = QTableWidgetItem(f"{min_profit:+.2f}")
        self._set_pnl_color(min_profit_item, min_profit)
        self.table.setItem(table_row, col_idx, min_profit_item)
        col_idx += 1
        
        # Column: Avg Profit
        avg_profit_item = QTableWidgetItem(f"{avg_profit:+.2f}" if avg_profit != 0 else "-")
        self._set_pnl_color(avg_profit_item, avg_profit)
        self.table.setItem(table_row, col_idx, avg_profit_item)
        col_idx += 1
        
        # Column: Avg Loss
        avg_loss_item = QTableWidgetItem(f"{avg_loss:+.2f}" if avg_loss != 0 else "-")
        self._set_pnl_color(avg_loss_item, avg_loss)
        self.table.setItem(table_row, col_idx, avg_loss_item)
        col_idx += 1
        
        # Column: Capital Used
        capital_used = locked_entry_price * trade_quantity
        capital_item = QTableWidgetItem(f"{int(capital_used)}")
        capital_item.setForeground(QColor(255, 255, 255))
        self.table.setItem(table_row, col_idx, capital_item)
        col_idx += 1
        
        # Column: Total Charges
        total_charges = float(row.get('total_charges', 0.0))
        charges_item = QTableWidgetItem(f"{total_charges:.2f}")
        charges_item.setForeground(QColor(255, 165, 0))  # Orange for charges
        self.table.setItem(table_row, col_idx, charges_item)
        col_idx += 1
        
        # Column: Net Profit
        net_profit = float(row.get('net_profit', pnl))  # Fallback to pnl if not available
        net_profit_item = QTableWidgetItem(f"{net_profit:+.2f}")
        self._set_pnl_color(net_profit_item, net_profit)
        self.table.setItem(table_row, col_idx, net_profit_item)
        col_idx += 1
        
        # Column: Entry Time
        self.table.setItem(table_row, col_idx, QTableWidgetItem(entry_time))
        col_idx += 1
        
        # Column: Exit Time
        self.table.setItem(table_row, col_idx, QTableWidgetItem(exit_time))
        col_idx += 1
        
        # Column: Exit Reason
        self.table.setItem(table_row, col_idx, QTableWidgetItem(str(exit_reason_short)))
        
        # Color code based on PnL
        if pnl > 0:
            color = QColor(34, 139, 34)  # Green
        elif pnl < 0:
            color = QColor(220, 20, 60)  # Red
        else:
            color = QColor(255, 255, 255)  # White
        
        # Apply color to columns without their own colors
        for col in [0, 1, 2, 4, 5, 6, 7, 8, 13, 16, 17, 18]:
            item = self.table.item(table_row, col)
            if item:
                item.setForeground(color)
    
    def _calculate_profit_extremes(self, row: pd.Series, locked_entry_price: float,
                                    exit_price: float, quantity: int) -> tuple:
        """Calculate max and min profit for a trade."""
        max_profit = float(row.get('max_profit', 0.0))
        min_profit = float(row.get('min_profit', 0.0))
        
        if abs(max_profit) < 0.01 and abs(min_profit) < 0.01:
            highest = row.get('highest_price', exit_price)
            lowest = row.get('lowest_price', exit_price)
            
            if row['type'] == 'LONG':
                max_profit = (highest - locked_entry_price) * quantity
                min_profit = (lowest - locked_entry_price) * quantity
            else:
                max_profit = (locked_entry_price - lowest) * quantity
                min_profit = (locked_entry_price - highest) * quantity
        
        return max_profit, min_profit
    
    def _set_pnl_color(self, item: QTableWidgetItem, value: float):
        """Set color based on PnL value."""
        if value > 0:
            item.setForeground(QColor(34, 139, 34))  # Green
        elif value < 0:
            item.setForeground(QColor(220, 20, 60))  # Red
        else:
            item.setForeground(QColor(255, 255, 255))  # White
    
    def clear(self):
        """Clear the table."""
        if self.table:
            self.table.setRowCount(0)
    
    def get_row_count(self) -> int:
        """Get the number of trades in the table."""
        if self.table:
            return self.table.rowCount()
        return 0
