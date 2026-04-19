"""
Order Manager Module

Handles order history tracking, order creation, updates, and queries.
"""

import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional


class OrderManager:
    """
    Manages trading order history and execution tracking.
    
    This class handles:
    - Order creation and ID generation
    - Order history tracking
    - Order status updates (OPEN -> CLOSED)
    - Order queries (open, closed, by symbol)
    - PnL calculations
    
    Attributes:
        order_history: List of all orders
        next_order_id: Counter for generating unique order IDs
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the OrderManager.
        
        Args:
            config: Trading configuration dictionary
        """
        self.config = config or {}
        self.order_history = []  # List of all orders
        self.next_order_id = 1  # Counter for order IDs
    
    def reload_config(self, config: Dict[str, Any]):
        """
        Reload configuration with new config.
        
        Args:
            config: New trading configuration dictionary
        """
        self.config = config
    
    def reset(self):
        """Reset order history and ID counter."""
        self.order_history.clear()
        self.next_order_id = 1
    
    def get_next_order_id(self) -> int:
        """
        Get the next order ID and increment counter.
        
        Returns:
            Next unique order ID
        """
        order_id = self.next_order_id
        self.next_order_id += 1
        return order_id
    
    def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new order and add to history.
        
        Args:
            order_data: Order data dictionary (without order_id)
        
        Returns:
            Complete order with order_id
        """
        order = {
            'order_id': self.get_next_order_id(),
            **order_data
        }
        self.order_history.append(order)
        return order
    
    def add_order(self, order: Dict[str, Any]):
        """
        Add an existing order to history.
        
        Args:
            order: Complete order dictionary
        """
        self.order_history.append(order)
        
        # Update next_order_id if needed
        if 'order_id' in order:
            self.next_order_id = max(self.next_order_id, order['order_id'] + 1)
    
    def get_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        """
        Get an order by ID.
        
        Args:
            order_id: Order ID to find
        
        Returns:
            Order dictionary or None
        """
        for order in self.order_history:
            if order.get('order_id') == order_id:
                return order
        return None
    
    def get_open_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        """
        Get an open order by ID.
        
        Args:
            order_id: Order ID to find
        
        Returns:
            Order dictionary or None
        """
        for order in self.order_history:
            if order.get('order_id') == order_id and order.get('status') == 'OPEN':
                return order
        return None
    
    def get_order_by_symbol(self, symbol: str, status: str = None) -> Optional[Dict[str, Any]]:
        """
        Get an order by symbol.
        
        Args:
            symbol: Trading symbol
            status: Optional status filter ('OPEN' or 'CLOSED')
        
        Returns:
            Order dictionary or None
        """
        for order in self.order_history:
            if order.get('symbol') == symbol:
                if status is None or order.get('status') == status:
                    return order
        return None
    
    def update_order(self, order_id: int, updates: Dict[str, Any]) -> bool:
        """
        Update an order by ID.
        
        Args:
            order_id: Order ID to update
            updates: Dictionary of fields to update
        
        Returns:
            True if order was found and updated
        """
        for order in self.order_history:
            if order.get('order_id') == order_id:
                order.update(updates)
                return True
        return False
    
    def close_order(
        self,
        order_id: int,
        exit_price: float,
        exit_time: datetime,
        exit_reason: str,
        pnl: float,
        **additional_fields
    ) -> Optional[Dict[str, Any]]:
        """
        Close an order.
        
        Args:
            order_id: Order ID to close
            exit_price: Exit price
            exit_time: Exit timestamp
            exit_reason: Reason for exit
            pnl: Profit/loss
            **additional_fields: Additional fields to update
        
        Returns:
            Updated order or None
        """
        order = self.get_order(order_id)
        if order is None:
            return None
        
        order.update({
            'exit_price': exit_price,
            'exit_time': exit_time,
            'exit_reason': exit_reason,
            'pnl': pnl,
            'status': 'CLOSED',
            **additional_fields
        })
        
        return order
    
    def get_all_orders(self) -> List[Dict[str, Any]]:
        """
        Get all orders.
        
        Returns:
            List of all orders
        """
        return self.order_history.copy()
    
    def get_open_orders(self) -> List[Dict[str, Any]]:
        """
        Get all open orders.
        
        Returns:
            List of open orders
        """
        return [o for o in self.order_history if o.get('status') == 'OPEN']
    
    def get_closed_orders(self) -> List[Dict[str, Any]]:
        """
        Get all closed orders.
        
        Returns:
            List of closed orders
        """
        return [o for o in self.order_history if o.get('status') == 'CLOSED']
    
    def get_real_closed_orders(self) -> List[Dict[str, Any]]:
        """
        Get all closed real (non-paper) trades.
        
        Returns:
            List of real closed orders
        """
        return [o for o in self.order_history 
                if o.get('status') == 'CLOSED' and not o.get('paper_trade', False)]
    
    def get_paper_closed_orders(self) -> List[Dict[str, Any]]:
        """
        Get all closed paper trades.
        
        Returns:
            List of paper closed orders
        """
        return [o for o in self.order_history 
                if o.get('status') == 'CLOSED' and o.get('paper_trade', False)]
    
    def get_closed_orders_dataframe(self) -> pd.DataFrame:
        """
        Get all closed orders as a DataFrame.
        
        Returns:
            DataFrame with closed order details
        """
        closed_orders = self.get_closed_orders()
        
        if not closed_orders:
            return pd.DataFrame()
        
        df = pd.DataFrame(closed_orders)
        columns = ['order_id', 'symbol', 'type', 'entry_price', 'exit_price',
                   'entry_time', 'exit_time', 'pnl', 'max_profit', 'min_profit', 
                   'avg_profit', 'avg_loss']
        
        # Use exit_quantity if available
        if 'exit_quantity' in df.columns:
            df['quantity'] = df['exit_quantity']
        
        columns.append('quantity')
        
        # Add optional columns if available
        for col in ['entry_reason', 'exit_reason', 'paper_trade', 'highest_price', 'lowest_price']:
            if col in df.columns:
                columns.append(col)
        
        # Only include columns that exist
        available_columns = [c for c in columns if c in df.columns]
        
        return df[available_columns]
    
    def get_total_pnl(self) -> float:
        """
        Calculate total realized PnL (excluding paper trades).
        
        Returns:
            Total PnL from real trades
        """
        real_closed = self.get_real_closed_orders()
        return sum(o.get('pnl', 0) for o in real_closed)
    
    def get_paper_pnl(self) -> float:
        """
        Calculate total PnL from paper trades.
        
        Returns:
            Total PnL from paper trades
        """
        paper_closed = self.get_paper_closed_orders()
        return sum(o.get('pnl', 0) for o in paper_closed)
    
    def get_order_count(self) -> int:
        """
        Get total number of orders.
        
        Returns:
            Total order count
        """
        return len(self.order_history)
    
    def get_closed_order_count(self) -> int:
        """
        Get number of closed orders.
        
        Returns:
            Closed order count
        """
        return len(self.get_closed_orders())
    
    def get_real_trade_count(self) -> int:
        """
        Get number of real (non-paper) closed trades.
        
        Returns:
            Real trade count
        """
        return len(self.get_real_closed_orders())
    
    def get_paper_trade_count(self) -> int:
        """
        Get number of paper trades.
        
        Returns:
            Paper trade count
        """
        return len(self.get_paper_closed_orders())
    
    def get_win_rate(self) -> float:
        """
        Calculate win rate for real trades.
        
        Returns:
            Win rate as decimal (0.0 to 1.0)
        """
        real_closed = self.get_real_closed_orders()
        if not real_closed:
            return 0.0
        
        winning_trades = len([o for o in real_closed if o.get('pnl', 0) > 0])
        return winning_trades / len(real_closed)
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Get summary statistics for orders.
        
        Returns:
            Dictionary with summary stats
        """
        real_closed = self.get_real_closed_orders()
        paper_closed = self.get_paper_closed_orders()
        
        # Calculate win rate
        winning_trades = len([o for o in real_closed if o.get('pnl', 0) > 0])
        win_rate = winning_trades / len(real_closed) if real_closed else 0.0
        
        return {
            'total_orders': len(self.order_history),
            'open_orders': len(self.get_open_orders()),
            'closed_orders': len(real_closed),
            'paper_trades': len(paper_closed),
            'total_pnl': self.get_total_pnl(),
            'paper_pnl': self.get_paper_pnl(),
            'win_rate': win_rate
        }
