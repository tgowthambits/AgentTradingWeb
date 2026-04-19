"""
Loss Recovery Module

Tracks and manages loss recovery per symbol, allowing for
increased position sizes to recover previous losses.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


class LossRecovery:
    """
    Manages loss tracking and recovery per trading symbol.
    
    This class tracks cumulative losses per symbol and provides
    methods to determine if additional quantity should be added
    to recover previous losses.
    
    Attributes:
        symbol_losses: Dictionary mapping symbols to their cumulative losses
        loss_recovery_enabled: Whether loss recovery feature is enabled
        recovery_history: List of recovery events
        loss_history: List of loss events
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the LossRecovery manager.
        
        Args:
            config: Trading configuration dictionary
        """
        self.config = config or {}
        self._load_config()
    
    def _load_config(self):
        """Load loss recovery configuration from config."""
        loss_recovery_config = self.config.get('risk_management', {}).get('loss_recovery', {})
        self.loss_recovery_config = loss_recovery_config
        self.loss_recovery_enabled = loss_recovery_config.get('enabled', False)
        self.max_multiplier = loss_recovery_config.get('max_multiplier', 3.0)
        
        # State tracking
        self.symbol_losses = {}  # symbol -> cumulative unrealized loss to recover
        self.recovery_history = []  # List of recovery events
        self.loss_history = []  # List of loss events
    
    def reload_config(self, config: Dict[str, Any]):
        """
        Reload configuration with new config.
        
        Args:
            config: New trading configuration dictionary
        """
        self.config = config
        self._load_config()
    
    def reset(self):
        """Reset all loss recovery state."""
        self.symbol_losses.clear()
        self.recovery_history.clear()
        self.loss_history.clear()
    
    def is_enabled(self) -> bool:
        """Check if loss recovery is enabled."""
        return self.loss_recovery_enabled
    
    def get_loss_to_recover(self, symbol: str) -> float:
        """
        Get the cumulative loss to recover for a symbol.
        
        Args:
            symbol: Trading symbol
        
        Returns:
            Loss amount to recover (0 if no loss)
        """
        return self.symbol_losses.get(symbol, 0.0)
    
    def has_loss_to_recover(self, symbol: str) -> bool:
        """
        Check if a symbol has losses to recover.
        
        Args:
            symbol: Trading symbol
        
        Returns:
            True if there are losses to recover
        """
        return symbol in self.symbol_losses and self.symbol_losses[symbol] > 0
    
    def record_loss(
        self,
        symbol: str,
        loss_amount: float,
        trade_id: Optional[int] = None,
        timestamp: Optional[datetime] = None
    ):
        """
        Record a loss for a symbol.
        
        Args:
            symbol: Trading symbol
            loss_amount: Loss amount (should be positive)
            trade_id: Optional trade/order ID
            timestamp: Optional timestamp (defaults to now)
        """
        if not self.loss_recovery_enabled:
            return
        
        if loss_amount <= 0:
            return
        
        # Track cumulative loss per symbol
        if symbol not in self.symbol_losses:
            self.symbol_losses[symbol] = 0.0
        
        self.symbol_losses[symbol] += loss_amount
        
        # Record in history
        self.loss_history.append({
            'symbol': symbol,
            'trade_id': trade_id,
            'loss_amount': loss_amount,
            'timestamp': timestamp or datetime.now()
        })
        
        print(f"📉 Loss tracked for {symbol}: ₹{loss_amount:.2f} (Total to recover: ₹{self.symbol_losses[symbol]:.2f})")
    
    def record_profit(
        self,
        symbol: str,
        profit_amount: float,
        trade_id: Optional[int] = None,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Record a profit and potentially recover losses.
        
        Args:
            symbol: Trading symbol
            profit_amount: Profit amount (should be positive)
            trade_id: Optional trade/order ID
            timestamp: Optional timestamp (defaults to now)
        
        Returns:
            Dictionary with recovery info
        """
        result = {
            'recovered': 0.0,
            'remaining': 0.0,
            'fully_recovered': False
        }
        
        if not self.loss_recovery_enabled:
            return result
        
        if profit_amount <= 0:
            return result
        
        if symbol not in self.symbol_losses or self.symbol_losses[symbol] <= 0:
            return result
        
        # Calculate recovery
        loss_to_recover = self.symbol_losses[symbol]
        recovered = min(profit_amount, loss_to_recover)
        
        self.symbol_losses[symbol] -= recovered
        
        # Check if fully recovered
        if self.symbol_losses[symbol] <= 0:
            self.symbol_losses[symbol] = 0
            result['fully_recovered'] = True
            print(f"✅ Loss fully recovered for {symbol}! Remaining: ₹0.00")
        else:
            print(f"💰 Partial recovery for {symbol}: ₹{recovered:.2f} (Remaining: ₹{self.symbol_losses[symbol]:.2f})")
        
        result['recovered'] = recovered
        result['remaining'] = self.symbol_losses[symbol]
        
        # Record in history
        self.recovery_history.append({
            'symbol': symbol,
            'trade_id': trade_id,
            'loss_amount': loss_to_recover,
            'recovered_amount': recovered,
            'timestamp': timestamp or datetime.now()
        })
        
        return result
    
    def process_trade_result(
        self,
        symbol: str,
        pnl: float,
        is_paper_trade: bool = False,
        trade_id: Optional[int] = None,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Process a trade result and update loss recovery state.
        
        Args:
            symbol: Trading symbol
            pnl: Profit/loss from the trade
            is_paper_trade: Whether this was a paper trade
            trade_id: Optional trade/order ID
            timestamp: Optional timestamp
        
        Returns:
            Dictionary with processing results
        """
        if not self.loss_recovery_enabled or is_paper_trade:
            return {'processed': False}
        
        if pnl < 0:
            self.record_loss(symbol, abs(pnl), trade_id, timestamp)
            return {
                'processed': True,
                'type': 'loss',
                'amount': abs(pnl),
                'total_to_recover': self.symbol_losses.get(symbol, 0)
            }
        elif pnl > 0:
            recovery_result = self.record_profit(symbol, pnl, trade_id, timestamp)
            return {
                'processed': True,
                'type': 'recovery',
                **recovery_result
            }
        
        return {'processed': False}
    
    def get_recovery_history(self) -> List[Dict[str, Any]]:
        """
        Get recovery history for display.
        
        Returns:
            List of recovery events with serializable timestamps
        """
        history = []
        for item in self.recovery_history:
            item_copy = item.copy()
            if isinstance(item_copy.get('timestamp'), datetime):
                item_copy['timestamp'] = item_copy['timestamp'].isoformat()
            history.append(item_copy)
        return history
    
    def get_loss_history(self) -> List[Dict[str, Any]]:
        """
        Get loss history for display.
        
        Returns:
            List of loss events with serializable timestamps
        """
        history = []
        for item in self.loss_history:
            item_copy = item.copy()
            if isinstance(item_copy.get('timestamp'), datetime):
                item_copy['timestamp'] = item_copy['timestamp'].isoformat()
            history.append(item_copy)
        return history
    
    def get_loss_recovery_status(self) -> Dict[str, Any]:
        """
        Get current loss recovery status per symbol.
        
        Returns:
            Dictionary with current status
        """
        return {
            'enabled': self.loss_recovery_enabled,
            'symbol_losses': self.symbol_losses.copy(),
            'total_unrecovered_loss': sum(self.symbol_losses.values()),
            'symbols_with_loss': list(self.symbol_losses.keys()),
            'max_multiplier': self.max_multiplier
        }
    
    def get_status_summary(self) -> str:
        """
        Get a formatted status summary.
        
        Returns:
            Formatted string for display
        """
        if not self.loss_recovery_enabled:
            return "Loss recovery is disabled"
        
        total = sum(self.symbol_losses.values())
        if total <= 0:
            return "No losses to recover"
        
        lines = [f"📊 Loss Recovery Status (Total: ₹{total:,.2f})"]
        for symbol, loss in self.symbol_losses.items():
            if loss > 0:
                lines.append(f"   {symbol}: ₹{loss:,.2f}")
        
        return "\n".join(lines)
