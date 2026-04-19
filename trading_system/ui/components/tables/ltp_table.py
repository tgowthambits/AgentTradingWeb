"""
LTP Table Manager Module

Manages the Live Trade Price (LTP) table with real-time updates,
indicator signals, price changes, and color coding.
"""

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem
from PySide6.QtGui import QColor


class LTPTableManager:
    """
    Manager for LTP (Live Trade Price) tables.
    
    This class handles:
    - Real-time price updates with change tracking
    - Indicator signal display and color coding
    - Symbol-to-row mapping for efficient updates
    - Price history tracking
    - Confidence/agreement score display
    
    Attributes:
        table: The QTableWidget to manage
        config: Configuration dictionary
        ltp_symbol_map: Mapping of row index to symbol
        previous_prices: Dictionary tracking previous prices for change calculation
        ltp_history: Dictionary storing price history per symbol
        enabled_indicators_list: List of currently enabled indicators
    """
    
    def __init__(self, table: QTableWidget = None, config: Dict[str, Any] = None):
        """
        Initialize the LTPTableManager.
        
        Args:
            table: QTableWidget to manage
            config: Configuration dictionary
        """
        self.table = table
        self.config = config or {}
        self.ltp_symbol_map: Dict[int, str] = {}
        self.previous_prices: Dict[str, float] = {}
        self.ltp_history: Dict[str, List] = {}
        self.enabled_indicators_list: List[str] = []
        self._format_time_func: Optional[Callable] = None
        self._get_enabled_indicators_func: Optional[Callable] = None
        self._map_config_name_func: Optional[Callable] = None
    
    def set_table(self, table: QTableWidget):
        """Set the table widget."""
        self.table = table
    
    def set_format_time_func(self, func: Callable):
        """Set the time formatting function."""
        self._format_time_func = func
    
    def set_get_enabled_indicators_func(self, func: Callable):
        """Set the function to get enabled indicators."""
        self._get_enabled_indicators_func = func
    
    def set_map_config_name_func(self, func: Callable):
        """Set the function to map config names to indicator names."""
        self._map_config_name_func = func
    
    def format_time(self, time_val) -> str:
        """Format time value for display."""
        if self._format_time_func:
            return self._format_time_func(time_val)
        # Default implementation
        if time_val is None:
            return "N/A"
        try:
            if isinstance(time_val, str):
                return time_val
            elif hasattr(time_val, 'strftime'):
                return time_val.strftime("%Y-%m-%d %H:%M:%S")
            else:
                return str(time_val)[:19]
        except:
            return "N/A"
    
    def _get_enabled_indicators(self) -> List[str]:
        """Get list of enabled indicators."""
        if self._get_enabled_indicators_func:
            return self._get_enabled_indicators_func()
        return self.enabled_indicators_list
    
    def _map_config_name_to_indicator_name(self, config_name: str, indicator_signals: Dict) -> str:
        """Map config name to actual indicator name in signals dict."""
        if self._map_config_name_func:
            return self._map_config_name_func(config_name, indicator_signals)
        return config_name
    
    def update(self, results: list):
        """
        Update LTP table with real-time prices and indicator signals.
        
        Updates existing rows without clearing the table, preserving
        change values until the next price change.
        
        Args:
            results: List of result dictionaries containing symbol data
        """
        if not self.table:
            return
        
        # Refresh enabled indicators list
        enabled_indicators = self._get_enabled_indicators()
        num_indicator_cols = len(enabled_indicators)
        num_base_cols = 6  # Symbol, LTP, Signal, Change, Confidence, DateTime
        total_cols = num_base_cols + num_indicator_cols
        
        # Update table columns if needed
        if self.table.columnCount() != total_cols:
            self.table.setColumnCount(total_cols)
            headers = ["Symbol", "LTP", "Signal", "Change", "Confidence", "DateTime"] + \
                      [ind.replace('_', ' ').title() for ind in enabled_indicators]
            self.table.setHorizontalHeaderLabels(headers)
            self.enabled_indicators_list = enabled_indicators
            self.table.setRowCount(0)
            self.ltp_symbol_map = {}
        
        current_time = datetime.now()
        
        # Build reverse mapping: symbol -> row index
        symbol_to_row = {}
        for row_idx, symbol in self.ltp_symbol_map.items():
            symbol_to_row[symbol] = row_idx
        
        # Process each result
        for result in results:
            symbol = result.get('symbol', '')
            if not symbol:
                continue
            
            symbol_short = symbol.split(':')[-1]
            ltp = result.get('latest_price', 0)
            signal = result.get('final_signal', 'HOLD')
            indicator_signals = result.get('indicator_signals', {})
            agreement_score = result.get('agreement_score', 0.0)
            
            # Get timestamp from result
            timestamp = result.get('timestamp', current_time)
            datetime_str = self.format_time(timestamp)
            
            # Store LTP history
            if symbol not in self.ltp_history:
                self.ltp_history[symbol] = []
            self.ltp_history[symbol].append((current_time, ltp))
            if len(self.ltp_history[symbol]) > 1000:
                self.ltp_history[symbol] = self.ltp_history[symbol][-1000:]
            
            if symbol in symbol_to_row:
                # Update existing row
                row = symbol_to_row[symbol]
                self._update_existing_row(
                    row, symbol, ltp, signal, indicator_signals,
                    agreement_score, datetime_str, enabled_indicators, num_base_cols
                )
            else:
                # Add new row
                row = self._add_new_row(
                    symbol, symbol_short, ltp, signal, indicator_signals,
                    agreement_score, datetime_str, enabled_indicators, num_base_cols
                )
                self.ltp_symbol_map[row] = symbol
                symbol_to_row[symbol] = row
    
    def _update_existing_row(self, row: int, symbol: str, ltp: float, signal: str,
                             indicator_signals: Dict, agreement_score: float,
                             datetime_str: str, enabled_indicators: List[str],
                             num_base_cols: int):
        """Update an existing row with new data."""
        # Get previous price from table
        prev_ltp_item = self.table.item(row, 1)
        if prev_ltp_item:
            try:
                prev_price = float(prev_ltp_item.text())
            except:
                prev_price = self.previous_prices.get(symbol, ltp)
        else:
            prev_price = self.previous_prices.get(symbol, ltp)
        
        ltp_changed = abs(ltp - prev_price) > 0.001
        
        # Update LTP
        ltp_item = self.table.item(row, 1)
        if ltp_item:
            ltp_item.setText(f"{ltp:.2f}")
        else:
            self.table.setItem(row, 1, QTableWidgetItem(f"{ltp:.2f}"))
        
        # Update Signal
        signal_item = self.table.item(row, 2)
        if signal_item:
            signal_item.setText(signal)
        else:
            signal_item = QTableWidgetItem(signal)
            self.table.setItem(row, 2, signal_item)
        
        # Update Change column only if LTP changed
        if ltp_changed:
            change = ltp - prev_price
            change_pct = (change / prev_price * 100) if prev_price > 0 else 0
            change_str = f"{change:+.2f} ({change_pct:+.2f}%)"
            
            change_item = self.table.item(row, 3)
            if change_item:
                change_item.setText(change_str)
            else:
                change_item = QTableWidgetItem(change_str)
                self.table.setItem(row, 3, change_item)
            
            # Color coding for change
            if change > 0:
                change_color = QColor(34, 139, 34)  # Green
            elif change < 0:
                change_color = QColor(220, 20, 60)  # Red
            else:
                change_color = QColor(255, 255, 255)  # White
            
            for col in [0, 1, 3]:
                item = self.table.item(row, col)
                if item:
                    item.setForeground(change_color)
        
        # Update Confidence
        confidence_str = f"{agreement_score:.0%}"
        confidence_item = self.table.item(row, 4)
        if confidence_item:
            confidence_item.setText(confidence_str)
        else:
            confidence_item = QTableWidgetItem(confidence_str)
            self.table.setItem(row, 4, confidence_item)
        
        # Update DateTime
        datetime_item = self.table.item(row, 5)
        if datetime_item:
            datetime_item.setText(datetime_str)
        else:
            self.table.setItem(row, 5, QTableWidgetItem(datetime_str))
        
        # Color code confidence
        if agreement_score >= 0.70:
            confidence_color = QColor(34, 139, 34)
        elif agreement_score >= 0.50:
            confidence_color = QColor(255, 215, 0)
        else:
            confidence_color = QColor(220, 20, 60)
        confidence_item.setForeground(confidence_color)
        
        # Color code signal
        if signal_item:
            if signal == 'BUY':
                signal_item.setForeground(QColor(34, 139, 34))
            elif signal == 'SELL':
                signal_item.setForeground(QColor(220, 20, 60))
            else:
                signal_item.setForeground(QColor(128, 128, 128))
        
        # Update indicator columns
        for idx, ind_name in enumerate(enabled_indicators):
            col_idx = num_base_cols + idx
            actual_ind_name = self._map_config_name_to_indicator_name(ind_name, indicator_signals)
            ind_signal = indicator_signals.get(actual_ind_name, 'HOLD')
            
            ind_item = self.table.item(row, col_idx)
            if ind_item:
                ind_item.setText(ind_signal)
            else:
                ind_item = QTableWidgetItem(ind_signal)
                self.table.setItem(row, col_idx, ind_item)
            
            # Color code indicator signals
            if ind_signal == 'BUY':
                ind_item.setForeground(QColor(34, 139, 34))
            elif ind_signal == 'SELL':
                ind_item.setForeground(QColor(220, 20, 60))
            else:
                ind_item.setForeground(QColor(128, 128, 128))
        
        self.previous_prices[symbol] = ltp
    
    def _add_new_row(self, symbol: str, symbol_short: str, ltp: float, signal: str,
                     indicator_signals: Dict, agreement_score: float,
                     datetime_str: str, enabled_indicators: List[str],
                     num_base_cols: int) -> int:
        """Add a new row and return the row index."""
        prev_price = self.previous_prices.get(symbol, ltp)
        change = ltp - prev_price
        change_pct = (change / prev_price * 100) if prev_price > 0 else 0
        change_str = f"{change:+.2f} ({change_pct:+.2f}%)"
        confidence_str = f"{agreement_score:.0%}"
        
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Base columns
        self.table.setItem(row, 0, QTableWidgetItem(symbol_short))
        self.table.setItem(row, 1, QTableWidgetItem(f"{ltp:.2f}"))
        self.table.setItem(row, 2, QTableWidgetItem(signal))
        self.table.setItem(row, 3, QTableWidgetItem(change_str))
        
        # Confidence column
        confidence_item = QTableWidgetItem(confidence_str)
        self.table.setItem(row, 4, confidence_item)
        
        # DateTime column
        self.table.setItem(row, 5, QTableWidgetItem(datetime_str))
        
        # Color code confidence
        if agreement_score >= 0.70:
            confidence_color = QColor(34, 139, 34)
        elif agreement_score >= 0.50:
            confidence_color = QColor(255, 215, 0)
        else:
            confidence_color = QColor(220, 20, 60)
        confidence_item.setForeground(confidence_color)
        
        # Color code for price change
        if change > 0:
            change_color = QColor(34, 139, 34)
        elif change < 0:
            change_color = QColor(220, 20, 60)
        else:
            change_color = QColor(255, 255, 255)
        
        for col in [0, 1, 3]:
            item = self.table.item(row, col)
            if item:
                item.setForeground(change_color)
        
        # Color code signal
        signal_item = self.table.item(row, 2)
        if signal_item:
            if signal == 'BUY':
                signal_item.setForeground(QColor(34, 139, 34))
            elif signal == 'SELL':
                signal_item.setForeground(QColor(220, 20, 60))
            else:
                signal_item.setForeground(QColor(128, 128, 128))
        
        # Add indicator columns
        for idx, ind_name in enumerate(enabled_indicators):
            col_idx = num_base_cols + idx
            actual_ind_name = self._map_config_name_to_indicator_name(ind_name, indicator_signals)
            ind_signal = indicator_signals.get(actual_ind_name, 'HOLD')
            
            signal_item = QTableWidgetItem(ind_signal)
            if ind_signal == 'BUY':
                signal_item.setForeground(QColor(34, 139, 34))
            elif ind_signal == 'SELL':
                signal_item.setForeground(QColor(220, 20, 60))
            else:
                signal_item.setForeground(QColor(128, 128, 128))
            
            self.table.setItem(row, col_idx, signal_item)
        
        self.previous_prices[symbol] = ltp
        return row
    
    def clear(self):
        """Clear the table and reset tracking dictionaries."""
        if self.table:
            self.table.setRowCount(0)
        self.ltp_symbol_map = {}
        self.previous_prices = {}
    
    def get_ltp_history(self, symbol: str) -> List:
        """Get price history for a symbol."""
        return self.ltp_history.get(symbol, [])
    
    def get_all_ltp_history(self) -> Dict[str, List]:
        """Get all price history."""
        return self.ltp_history.copy()
