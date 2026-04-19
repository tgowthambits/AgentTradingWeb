"""
Position Manager Module

Handles tracking and management of open trading positions,
including position updates, extremes tracking, and position queries.
"""

import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional


class PositionManager:
    """
    Manages open trading positions.
    
    This class tracks:
    - Current open positions by symbol
    - Position entry details (price, time, quantity)
    - Position extremes (highest/lowest prices reached)
    - Max/min profit tracking during position lifetime
    - Day open prices for change calculations
    
    Attributes:
        current_positions: Dictionary mapping symbols to position data
        day_open_prices: Dictionary mapping symbols to their day open prices
        last_candle_closure_time: Dictionary mapping symbols to last candle closure time
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the PositionManager.
        
        Args:
            config: Trading configuration dictionary
        """
        self.config = config or {}
        self.current_positions = {}  # symbol -> position info
        self.day_open_prices = {}  # symbol -> opening price for the day
        self.last_candle_closure_time = {}  # symbol -> datetime
    
    def reload_config(self, config: Dict[str, Any]):
        """
        Reload configuration with new config.
        
        Args:
            config: New trading configuration dictionary
        """
        self.config = config
    
    def reset(self):
        """Reset all position tracking state."""
        self.current_positions.clear()
        self.day_open_prices.clear()
        self.last_candle_closure_time.clear()
    
    def has_position(self, symbol: str) -> bool:
        """
        Check if there's an open position for a symbol.
        
        Args:
            symbol: Trading symbol
        
        Returns:
            True if position exists
        """
        return symbol in self.current_positions
    
    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get position data for a symbol.
        
        Args:
            symbol: Trading symbol
        
        Returns:
            Position dictionary or None
        """
        return self.current_positions.get(symbol)
    
    def get_all_positions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all current positions.
        
        Returns:
            Dictionary of all positions
        """
        return self.current_positions.copy()
    
    def get_position_count(self) -> int:
        """
        Get the number of open positions.
        
        Returns:
            Count of open positions
        """
        return len(self.current_positions)
    
    def add_position(self, symbol: str, position_data: Dict[str, Any]):
        """
        Add a new position.
        
        Args:
            symbol: Trading symbol
            position_data: Position data dictionary
        """
        self.current_positions[symbol] = position_data
        
        # Initialize candle closure time if needed
        resolution = self.config.get('backtest', {}).get('resolution', '30S')
        if resolution == '30S':
            self.last_candle_closure_time[symbol] = position_data.get('entry_time', datetime.now())
    
    def remove_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Remove and return a position.
        
        Args:
            symbol: Trading symbol
        
        Returns:
            Removed position data or None
        """
        return self.current_positions.pop(symbol, None)
    
    def update_position(self, symbol: str, updates: Dict[str, Any]):
        """
        Update position data.
        
        Args:
            symbol: Trading symbol
            updates: Dictionary of fields to update
        """
        if symbol in self.current_positions:
            self.current_positions[symbol].update(updates)
    
    def update_position_extremes(
        self,
        symbol: str,
        current_price: float,
        order_entry_price: Optional[float] = None
    ):
        """
        Update highest and lowest prices for a position (for trailing stop).
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            order_entry_price: Entry price from order (source of truth)
        """
        if symbol not in self.current_positions:
            return
        
        position = self.current_positions[symbol]
        
        # Use order's entry_price if available, otherwise fallback to position
        if order_entry_price is not None and order_entry_price > 0:
            entry_price = order_entry_price
        else:
            entry_price = position.get('entry_price', current_price)
        
        quantity = position.get('quantity', 0)
        position_type = position.get('type', 'LONG')
        
        # Update highest price
        if current_price > position.get('highest_price', current_price):
            position['highest_price'] = current_price
        
        # Update lowest price
        if current_price < position.get('lowest_price', current_price):
            position['lowest_price'] = current_price
        
        # Calculate max profit (best profit reached during position lifetime)
        if position_type == 'LONG':
            max_profit_price = position.get('highest_price', entry_price)
            max_profit = (max_profit_price - entry_price) * quantity
            min_profit_price = position.get('lowest_price', entry_price)
            min_profit = (min_profit_price - entry_price) * quantity
            max_profit_pct = ((max_profit_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0.0
        else:  # SHORT
            max_profit_price = position.get('lowest_price', entry_price)
            max_profit = (entry_price - max_profit_price) * quantity
            min_profit_price = position.get('highest_price', entry_price)
            min_profit = (entry_price - min_profit_price) * quantity
            max_profit_pct = ((entry_price - max_profit_price) / entry_price) * 100 if entry_price > 0 else 0.0
        
        # Store max and min profit
        position['max_profit'] = max_profit
        position['min_profit'] = min_profit
        
        # Track max profit percentage (for profit drop protection)
        if 'max_profit_pct' not in position:
            position['max_profit_pct'] = max(0, max_profit_pct)
        else:
            position['max_profit_pct'] = max(position['max_profit_pct'], max_profit_pct)
        
        # Calculate current PnL for average tracking
        if position_type == 'LONG':
            current_pnl = (current_price - entry_price) * quantity
        else:  # SHORT
            current_pnl = (entry_price - current_price) * quantity
        
        # Track average profit (when in profit)
        if current_pnl > 0:
            if 'profit_count' not in position:
                position['profit_count'] = 0
                position['avg_profit'] = 0.0
            
            position['profit_count'] += 1
            position['avg_profit'] = position['avg_profit'] + (current_pnl - position['avg_profit']) / position['profit_count']
        
        # Track average loss (when in loss)
        elif current_pnl < 0:
            if 'loss_count' not in position:
                position['loss_count'] = 0
                position['avg_loss'] = 0.0
            
            position['loss_count'] += 1
            position['avg_loss'] = position['avg_loss'] + (current_pnl - position['avg_loss']) / position['loss_count']
    
    def update_current_price(self, symbol: str, current_price: float):
        """
        Update current price for a position.
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
        """
        if symbol in self.current_positions:
            self.current_positions[symbol]['current_price'] = current_price
    
    def get_capital_used_in_positions(self, exclude_symbol: str = None) -> float:
        """
        Calculate capital currently tied up in open positions.
        
        Args:
            exclude_symbol: Optional symbol to exclude from calculation
        
        Returns:
            Total capital used
        """
        capital_used = 0.0
        for sym, pos_data in self.current_positions.items():
            if exclude_symbol and sym == exclude_symbol:
                continue
            entry_price = pos_data.get('entry_price', 0)
            quantity = pos_data.get('quantity', 0)
            capital_used += entry_price * quantity
        return capital_used
    
    def set_day_open_price(self, symbol: str, price: float):
        """
        Set the day open price for a symbol.
        
        Args:
            symbol: Trading symbol
            price: Day opening price
        """
        self.day_open_prices[symbol] = price
    
    def get_day_open_price(self, symbol: str) -> Optional[float]:
        """
        Get the day open price for a symbol.
        
        Args:
            symbol: Trading symbol
        
        Returns:
            Day open price or None
        """
        return self.day_open_prices.get(symbol)
    
    def get_open_positions_dataframe(self) -> pd.DataFrame:
        """
        Get all open positions as a DataFrame.
        
        Returns:
            DataFrame with position details
        """
        if not self.current_positions:
            return pd.DataFrame()
        
        positions_list = []
        for position in self.current_positions.values():
            ltp = position.get('current_price', position['entry_price'])
            open_today = position.get('open_price_today', position['entry_price'])
            change_pct = ((ltp - open_today) / open_today) * 100 if open_today != 0 else 0
            
            positions_list.append({
                'order_id': position['order_id'],
                'symbol': position['symbol'],
                'type': position['type'],
                'entry_price': position['entry_price'],
                'ltp': ltp,
                'change_%': f'{change_pct:.2f}%',
                'entry_time': position['entry_time'],
                'quantity': position['quantity'],
                'max_profit': position.get('max_profit', 0.0),
                'min_profit': position.get('min_profit', 0.0),
                'avg_profit': position.get('avg_profit', 0.0),
                'avg_loss': position.get('avg_loss', 0.0)
            })
        
        df = pd.DataFrame(positions_list)
        
        # Desired column order
        columns = ['order_id', 'symbol', 'type', 'quantity', 'entry_price', 'ltp', 
                   'change_%', 'entry_time', 'max_profit', 'min_profit', 'avg_profit', 'avg_loss']
        
        # Only include columns that exist
        df_columns = [col for col in columns if col in df.columns]
        
        return df[df_columns]
    
    def get_open_positions_display(
        self,
        signal_aggregator=None,
        indicator_manager=None
    ) -> List[Dict]:
        """
        Get open positions formatted for display, including LTP and change %.
        
        Args:
            signal_aggregator: Optional SignalAggregator for signal info
            indicator_manager: Optional IndicatorManager for indicator signals
        
        Returns:
            List of position dictionaries for display
        """
        positions_list = []
        for symbol, position in self.current_positions.items():
            ltp = position.get('current_price', position['entry_price'])
            day_open = self.day_open_prices.get(symbol, position['entry_price'])
            
            change = ltp - day_open
            change_pct = (change / day_open * 100) if day_open > 0 else 0
            
            pos_data = {
                "symbol": symbol,
                "ltp": ltp,
                "change": change,
                "change_pct": change_pct,
                "final_signal": None,
                "agreement_score": None,
                "indicator_signals": {}
            }
            
            # Add signal info if available
            if signal_aggregator is not None:
                try:
                    pos_data["final_signal"] = signal_aggregator.get_final_signal(symbol)
                    pos_data["agreement_score"] = signal_aggregator.get_agreement_score_for_symbol(symbol)
                except:
                    pass
            
            if indicator_manager is not None:
                try:
                    pos_data["indicator_signals"] = indicator_manager.get_signals_for_symbol(symbol)
                except:
                    pass
            
            positions_list.append(pos_data)
        
        return positions_list
