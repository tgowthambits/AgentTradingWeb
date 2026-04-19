"""
Position Tracker for Real-time Trading
Tracks active positions, PnL, and order history
"""

from datetime import datetime
from typing import Optional, Dict, List
import pandas as pd


class PositionTracker:
    """Track trading positions and calculate PnL"""
    
    def __init__(self, stop_loss_amount: float = 2.0):
        """
        Initialize position tracker
        
        Args:
            stop_loss_amount: Stop loss amount in ₹ per order (default: 2.0)
        """
        self.position = 0  # 0 = no position, 1 = long position
        self.entry_price: Optional[float] = None
        self.entry_time: Optional[datetime] = None
        self.quantity: int = 0
        self.orders: List[Dict] = []
        self.total_pnl: float = 0.0
        self.unrealized_pnl: float = 0.0
        self.stop_loss_amount = stop_loss_amount
        self.stop_loss_price: Optional[float] = None
        self.stop_loss_hits: int = 0  # Count of stop loss hits
        self.stop_loss_orders: List[Dict] = []  # Track stop loss orders
        
    def has_position(self) -> bool:
        """Check if we have an active position"""
        return self.position > 0
    
    def buy(self, price: float, quantity: int, timestamp: Optional[datetime] = None) -> Dict:
        """
        Record a buy order
        
        Args:
            price: Entry price
            quantity: Number of shares/units
            timestamp: Order timestamp
            
        Returns:
            Order details dict
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        if self.has_position():
            return {
                "status": "error",
                "message": "Already have a position. Close existing position first.",
                "current_position": self.position,
                "entry_price": self.entry_price
            }
        
        self.position = 1
        self.entry_price = price
        self.entry_time = timestamp
        self.quantity = quantity
        
        # Set stop loss price (entry price - stop loss amount)
        self.stop_loss_price = price - self.stop_loss_amount
        
        order = {
            "action": "BUY",
            "price": price,
            "quantity": quantity,
            "timestamp": timestamp,
            "status": "filled",
            "stop_loss_price": self.stop_loss_price,
            "stop_loss_amount": self.stop_loss_amount
        }
        
        self.orders.append(order)
        
        return {
            "status": "success",
            "action": "BUY",
            "price": price,
            "quantity": quantity,
            "timestamp": timestamp,
            "stop_loss_price": self.stop_loss_price,
            "stop_loss_amount": self.stop_loss_amount
        }
    
    def sell(self, price: float, timestamp: Optional[datetime] = None, reason: str = "Manual") -> Dict:
        """
        Record a sell order and calculate realized PnL
        
        Args:
            price: Exit price
            timestamp: Order timestamp
            reason: Reason for sell (e.g., "Manual", "Stop Loss", "RL Agent")
            
        Returns:
            Order details dict with PnL
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        if not self.has_position():
            return {
                "status": "error",
                "message": "No position to sell.",
                "current_position": self.position
            }
        
        # Store values before resetting
        entry_price = self.entry_price
        entry_time = self.entry_time
        quantity_sold = self.quantity
        stop_loss_price = self.stop_loss_price
        
        # Calculate PnL
        pnl = (price - entry_price) * quantity_sold
        
        # Check if stop loss was hit
        is_stop_loss = reason == "Stop Loss" or (stop_loss_price and price <= stop_loss_price)
        if is_stop_loss:
            self.stop_loss_hits += 1
        
        self.total_pnl += pnl
        
        order = {
            "action": "SELL",
            "entry_price": entry_price,
            "exit_price": price,
            "quantity": quantity_sold,
            "pnl": pnl,
            "timestamp": timestamp,
            "duration": (timestamp - entry_time).total_seconds() if entry_time else 0,
            "status": "filled",
            "reason": reason,
            "is_stop_loss": is_stop_loss,
            "stop_loss_price": stop_loss_price
        }
        
        self.orders.append(order)
        
        if is_stop_loss:
            self.stop_loss_orders.append(order)
        
        # Reset position
        self.position = 0
        self.entry_price = None
        self.entry_time = None
        self.quantity = 0
        self.unrealized_pnl = 0.0
        self.stop_loss_price = None
        
        return {
            "status": "success",
            "action": "SELL",
            "entry_price": entry_price,
            "exit_price": price,
            "quantity": quantity_sold,
            "pnl": pnl,
            "timestamp": timestamp,
            "reason": reason,
            "is_stop_loss": is_stop_loss,
            "stop_loss_price": stop_loss_price
        }
    
    def check_stop_loss(self, current_price: float) -> Optional[str]:
        """
        Check if stop loss should be triggered
        
        Args:
            current_price: Current market price
            
        Returns:
            "Stop Loss" if triggered, None otherwise
        """
        if self.has_position() and self.stop_loss_price and current_price <= self.stop_loss_price:
            return "Stop Loss"
        return None
    
    def update_pnl(self, current_price: float) -> float:
        """
        Update unrealized PnL for current position
        
        Args:
            current_price: Current market price
            
        Returns:
            Unrealized PnL
        """
        if self.has_position() and self.entry_price:
            self.unrealized_pnl = (current_price - self.entry_price) * self.quantity
        else:
            self.unrealized_pnl = 0.0
        
        return self.unrealized_pnl
    
    def get_status(self, current_price: Optional[float] = None) -> Dict:
        """
        Get current position status
        
        Args:
            current_price: Current market price (optional, for PnL calculation)
            
        Returns:
            Status dictionary
        """
        if current_price and self.has_position():
            self.update_pnl(current_price)
        
        return {
            "has_position": self.has_position(),
            "position": self.position,
            "entry_price": self.entry_price,
            "entry_time": self.entry_time,
            "quantity": self.quantity,
            "current_price": current_price,
            "unrealized_pnl": self.unrealized_pnl,
            "total_realized_pnl": self.total_pnl,
            "total_pnl": self.total_pnl + self.unrealized_pnl,
            "total_orders": len(self.orders),
            "closed_trades": len([o for o in self.orders if o.get("action") == "SELL"]),
            "stop_loss_amount": self.stop_loss_amount,
            "stop_loss_price": self.stop_loss_price,
            "stop_loss_hits": self.stop_loss_hits,
            "stop_loss_orders": len(self.stop_loss_orders)
        }
    
    def get_order_history(self) -> pd.DataFrame:
        """Get order history as DataFrame"""
        if not self.orders:
            return pd.DataFrame()
        
        return pd.DataFrame(self.orders)
    
    def reset(self):
        """Reset position tracker (use with caution)"""
        self.position = 0
        self.entry_price = None
        self.entry_time = None
        self.quantity = 0
        self.unrealized_pnl = 0.0
        # Keep order history but reset current position

