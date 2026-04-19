"""
Positions Table Manager Module

Manages the open positions table with real-time PnL updates,
position tracking, and color-coded display.
"""

from typing import Dict, Any, List, Optional, Callable
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem
from PySide6.QtGui import QColor


class PositionsTableManager:
    """
    Manager for open positions tables.
    
    This class handles:
    - Display of open positions with entry price, quantity, current price
    - Real-time PnL calculation and display
    - Max/min profit tracking
    - Paper vs real trade type indication
    - Position change detection
    
    Attributes:
        table: The QTableWidget to manage
        config: Configuration dictionary
        previous_positions: Dictionary tracking positions for change detection
        last_results: Latest results for LTP lookup
    """
    
    def __init__(self, table: QTableWidget = None, config: Dict[str, Any] = None):
        """
        Initialize the PositionsTableManager.
        
        Args:
            table: QTableWidget to manage
            config: Configuration dictionary
        """
        self.table = table
        self.config = config or {}
        self.previous_positions: Dict[str, Dict] = {}
        self.last_results: List[Dict] = []
        self._format_time_func: Optional[Callable] = None
        self._log_event_func: Optional[Callable] = None
        self._get_engine_func: Optional[Callable] = None
    
    def set_table(self, table: QTableWidget):
        """Set the table widget."""
        self.table = table
    
    def set_format_time_func(self, func: Callable):
        """Set the time formatting function."""
        self._format_time_func = func
    
    def set_log_event_func(self, func: Callable):
        """Set the event logging function."""
        self._log_event_func = func
    
    def set_get_engine_func(self, func: Callable):
        """Set the function to get the trading engine."""
        self._get_engine_func = func
    
    def set_last_results(self, results: List[Dict]):
        """Set the latest results for LTP lookup."""
        self.last_results = results
    
    def format_time(self, time_val) -> str:
        """Format time value for display."""
        if self._format_time_func:
            return self._format_time_func(time_val)
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
    
    def log_event(self, event_type: str, message: str):
        """Log an event."""
        if self._log_event_func:
            self._log_event_func(event_type, message)
    
    def _get_engine(self):
        """Get the trading engine instance."""
        if self._get_engine_func:
            return self._get_engine_func()
        return None
    
    def update(self, positions: Dict[str, Dict]):
        """
        Update positions table with current positions.
        
        Args:
            positions: Dictionary of symbol -> position data
        """
        if not self.table:
            return
        
        # Filter out positions with 0 quantity
        valid_positions = {k: v for k, v in positions.items() if v.get('quantity', 0) > 0}
        
        # Detect position changes
        self._detect_position_changes(valid_positions)
        
        self.table.setRowCount(0)
        
        for symbol, position in valid_positions.items():
            self._add_position_row(symbol, position)
        
        # Update previous positions for next comparison
        self.previous_positions = valid_positions.copy()
    
    def _add_position_row(self, symbol: str, position: Dict):
        """Add a single position row to the table."""
        symbol_short = symbol.split(':')[-1]
        
        # Get locked entry price
        locked_entry_price = self._get_locked_entry_price(symbol, position)
        
        # Get current price and calculate PnL
        ltp, pnl_val, current_price = self._calculate_position_pnl(
            symbol, position, locked_entry_price
        )
        
        # Add row
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        quantity = position.get('quantity', 0)
        if quantity <= 0:
            return
        
        # Verify quantity is valid
        engine = self._get_engine()
        if engine and hasattr(engine, 'get_lot_size'):
            lot_size = engine.get_lot_size(symbol)
            if lot_size > 0 and quantity % lot_size != 0:
                lots = max(1, int(quantity / lot_size))
                quantity = lots * lot_size
                position['quantity'] = quantity
        
        # Column 0: Symbol
        self.table.setItem(row, 0, QTableWidgetItem(symbol_short))
        # Column 1: Type (LONG/SHORT)
        self.table.setItem(row, 1, QTableWidgetItem(position['type']))
        
        # Column 2: Trade Type (PAPER/REAL)
        is_paper_trade = position.get('paper_trade', False)
        trade_type = "PAPER" if is_paper_trade else "REAL"
        trade_type_item = QTableWidgetItem(trade_type)
        if is_paper_trade:
            trade_type_item.setForeground(QColor(255, 215, 0))  # Gold
        else:
            trade_type_item.setForeground(QColor(255, 255, 255))  # White
        self.table.setItem(row, 2, trade_type_item)
        
        # Column 3: Entry Price
        self.table.setItem(row, 3, QTableWidgetItem(f"{locked_entry_price:.2f}"))
        # Column 4: Quantity
        self.table.setItem(row, 4, QTableWidgetItem(str(quantity)))
        # Column 5: LTP
        self.table.setItem(row, 5, QTableWidgetItem(f"{ltp:.2f}" if ltp > 0 else "N/A"))
        # Column 6: PnL
        self.table.setItem(row, 6, QTableWidgetItem(f"{pnl_val:+.2f}" if pnl_val != 0 else "N/A"))
        
        # Max/min profit columns
        max_profit, min_profit = self._calculate_profit_extremes(
            position, locked_entry_price, current_price, quantity
        )
        avg_profit = position.get('avg_profit', 0.0)
        avg_loss = position.get('avg_loss', 0.0)
        
        # Column 7: Max Profit
        max_profit_item = QTableWidgetItem(f"{max_profit:+.2f}")
        self._set_pnl_color(max_profit_item, max_profit)
        self.table.setItem(row, 7, max_profit_item)
        
        # Column 8: Min Profit
        min_profit_item = QTableWidgetItem(f"{min_profit:+.2f}")
        self._set_pnl_color(min_profit_item, min_profit)
        self.table.setItem(row, 8, min_profit_item)
        
        # Column 9: Avg Profit
        avg_profit_item = QTableWidgetItem(f"{avg_profit:+.2f}" if avg_profit != 0 else "-")
        self._set_pnl_color(avg_profit_item, avg_profit)
        self.table.setItem(row, 9, avg_profit_item)
        
        # Column 10: Avg Loss
        avg_loss_item = QTableWidgetItem(f"{avg_loss:+.2f}" if avg_loss != 0 else "-")
        self._set_pnl_color(avg_loss_item, avg_loss)
        self.table.setItem(row, 10, avg_loss_item)
        
        # Column 11: Capital Used
        capital_used = locked_entry_price * quantity
        capital_item = QTableWidgetItem(f"{int(capital_used)}")
        capital_item.setForeground(QColor(255, 255, 255))
        self.table.setItem(row, 11, capital_item)
        
        # Column 12: Entry Time
        entry_time = position.get('entry_time')
        entry_time_str = self.format_time(entry_time) if entry_time else "N/A"
        self.table.setItem(row, 12, QTableWidgetItem(entry_time_str))
        
        # Set row height
        self.table.setRowHeight(row, 25)
        
        # Color code based on PnL
        if pnl_val > 0:
            color = QColor(34, 139, 34)  # Green
        elif pnl_val < 0:
            color = QColor(220, 20, 60)  # Red
        else:
            color = QColor(255, 255, 255)  # White
        
        # Apply color to columns without their own colors
        for col in [0, 1, 3, 4, 5, 6, 11, 12]:
            item = self.table.item(row, col)
            if item:
                item.setForeground(color)
    
    def _get_locked_entry_price(self, symbol: str, position: Dict) -> float:
        """Get the locked entry price from order history or position."""
        locked_entry_price = position.get('entry_price', 0.0)
        
        engine = self._get_engine()
        if engine:
            order_id = position.get('order_id')
            if order_id and hasattr(engine, 'order_history'):
                for order in engine.order_history:
                    if order.get('order_id') == order_id:
                        order_entry_price = order.get('entry_price')
                        if order_entry_price is not None and order_entry_price > 0:
                            locked_entry_price = float(order_entry_price)
                            break
        
        locked_entry_price = float(locked_entry_price)
        if locked_entry_price <= 0:
            locked_entry_price = float(position.get('entry_price', 0.0))
        
        return locked_entry_price
    
    def _calculate_position_pnl(self, symbol: str, position: Dict, 
                                 locked_entry_price: float) -> tuple:
        """Calculate PnL for a position."""
        ltp = 0.0
        pnl_val = 0.0
        current_price = locked_entry_price
        
        for result in self.last_results:
            if result.get('symbol') == symbol:
                ltp = result.get('latest_price', 0)
                current_price = result.get('latest_price', 0)
                if position['type'] == 'LONG':
                    pnl_val = (current_price - locked_entry_price) * position['quantity']
                else:
                    pnl_val = (locked_entry_price - current_price) * position['quantity']
                break
        
        return ltp, pnl_val, current_price
    
    def _calculate_profit_extremes(self, position: Dict, locked_entry_price: float,
                                    current_price: float, quantity: int) -> tuple:
        """Calculate max and min profit for a position."""
        max_profit = position.get('max_profit', 0.0)
        min_profit = position.get('min_profit', 0.0)
        
        if abs(max_profit) < 0.01 and abs(min_profit) < 0.01:
            highest_price = position.get('highest_price', current_price)
            lowest_price = position.get('lowest_price', current_price)
            
            if position['type'] == 'LONG':
                max_profit = (highest_price - locked_entry_price) * quantity
                min_profit = (lowest_price - locked_entry_price) * quantity
            else:
                max_profit = (locked_entry_price - lowest_price) * quantity
                min_profit = (locked_entry_price - highest_price) * quantity
        
        return max_profit, min_profit
    
    def _set_pnl_color(self, item: QTableWidgetItem, value: float):
        """Set color based on PnL value."""
        if value > 0:
            item.setForeground(QColor(34, 139, 34))  # Green
        elif value < 0:
            item.setForeground(QColor(220, 20, 60))  # Red
        else:
            item.setForeground(QColor(255, 255, 255))  # White
    
    def _detect_position_changes(self, current_positions: Dict[str, Dict]):
        """Detect and log position changes."""
        # Check for new positions
        for symbol, position in current_positions.items():
            if symbol not in self.previous_positions:
                entry_price = position.get('entry_price', 0)
                quantity = position.get('quantity', 0)
                pos_type = position.get('type', 'LONG')
                order_id = position.get('order_id', 'N/A')
                
                lot_info = ""
                engine = self._get_engine()
                if engine and hasattr(engine, 'get_lot_size'):
                    lot_size = engine.get_lot_size(symbol)
                    lots = int(quantity / lot_size) if lot_size > 0 else 0
                    available_capital = getattr(engine, 'actual_capital', 0)
                    lot_info = f" | Lots: {lots} (lot_size: {lot_size}) | Capital: {available_capital:,.2f}"
                
                self.log_event("ENTRY", 
                    f"{symbol} | {pos_type} @ {entry_price:.2f} x {quantity}{lot_info} | Order #{order_id}")
        
        # Check for closed positions
        for symbol, prev_position in self.previous_positions.items():
            if symbol not in current_positions:
                entry_price = prev_position.get('entry_price', 0)
                quantity = prev_position.get('quantity', 0)
                pos_type = prev_position.get('type', 'LONG')
                order_id = prev_position.get('order_id', 'N/A')
                exit_reason = prev_position.get('last_exit_reason', 'Position closed')
                self.log_event("EXIT", 
                    f"{symbol} | {pos_type} | Entry: {entry_price:.2f} | Qty: {quantity} | Reason: {exit_reason} | Order #{order_id}")
        
        # Check for partial exits
        for symbol, position in current_positions.items():
            if symbol in self.previous_positions:
                prev_qty = self.previous_positions[symbol].get('quantity', 0)
                curr_qty = position.get('quantity', 0)
                
                if curr_qty < prev_qty:
                    exit_qty = prev_qty - curr_qty
                    entry_price = position.get('entry_price', 0)
                    pos_type = position.get('type', 'LONG')
                    order_id = position.get('order_id', 'N/A')
                    exit_reason = position.get('last_exit_reason', 'Partial Exit')
                    self.log_event("PARTIAL_EXIT",
                        f"{symbol} | {pos_type} | Entry: {entry_price:.2f} | Exited: {exit_qty} | Remaining: {curr_qty} | Reason: {exit_reason} | Order #{order_id}")
    
    def clear(self):
        """Clear the table and reset tracking."""
        if self.table:
            self.table.setRowCount(0)
        self.previous_positions = {}
    
    def get_previous_positions(self) -> Dict[str, Dict]:
        """Get the previous positions dictionary."""
        return self.previous_positions.copy()
