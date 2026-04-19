"""
Slippage Handler Module

Handles entry and exit slippage calculations for backtesting.
Slippage simulates the difference between expected and actual execution prices.
"""

from typing import Dict, Any


class SlippageHandler:
    """
    Manages slippage calculations for entry and exit trades.
    
    Slippage is applied only in backtesting mode to simulate real-world
    market conditions where execution prices may differ from expected prices.
    
    Attributes:
        entry_slippage_pct: Percentage slippage applied to entry prices
        exit_slippage_pct: Percentage slippage applied to exit prices
        config: Trading configuration dictionary
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the SlippageHandler.
        
        Args:
            config: Trading configuration dictionary containing backtest settings
        """
        self.config = config or {}
        self.entry_slippage_pct = 0.0
        self.exit_slippage_pct = 0.0
        self._load_slippage_config()
    
    def _load_slippage_config(self):
        """Load slippage configuration from config (backtesting only)."""
        backtest_config = self.config.get('backtest', {})
        self.entry_slippage_pct = backtest_config.get('entry_slippage', 0.0)
        self.exit_slippage_pct = backtest_config.get('exit_slippage', 0.0)
    
    def reload_config(self, config: Dict[str, Any]):
        """
        Reload slippage configuration with new config.
        
        Args:
            config: New trading configuration dictionary
        """
        self.config = config
        self._load_slippage_config()
    
    def apply_entry_slippage(self, price: float, position_type: str) -> float:
        """
        Apply entry slippage to price (backtesting only).
        
        For LONG positions: slippage increases entry price (buy at higher price)
        For SHORT positions: slippage decreases entry price (sell at lower price)
        
        Args:
            price: Original entry price
            position_type: 'LONG' or 'SHORT'
        
        Returns:
            Price with slippage applied
        """
        backtest_mode = self.config.get('backtest', {}).get('enabled', False)
        if not backtest_mode or self.entry_slippage_pct <= 0:
            return price
        
        slippage_amount = price * (self.entry_slippage_pct / 100.0)
        if position_type == 'LONG':
            return price + slippage_amount
        else:  # SHORT
            return price - slippage_amount
    
    def apply_exit_slippage(self, price: float, position_type: str) -> float:
        """
        Apply exit slippage to price (backtesting only).
        
        For LONG positions: slippage decreases exit price (sell at lower price)
        For SHORT positions: slippage increases exit price (buy at higher price)
        
        Args:
            price: Original exit price
            position_type: 'LONG' or 'SHORT'
        
        Returns:
            Price with slippage applied
        """
        backtest_mode = self.config.get('backtest', {}).get('enabled', False)
        if not backtest_mode or self.exit_slippage_pct <= 0:
            return price
        
        slippage_amount = price * (self.exit_slippage_pct / 100.0)
        if position_type == 'LONG':
            return price - slippage_amount
        else:  # SHORT
            return price + slippage_amount
    
    def get_slippage_info(self) -> Dict[str, float]:
        """
        Get current slippage configuration.
        
        Returns:
            Dictionary with entry and exit slippage percentages
        """
        return {
            'entry_slippage_pct': self.entry_slippage_pct,
            'exit_slippage_pct': self.exit_slippage_pct
        }
    
    def is_slippage_enabled(self) -> bool:
        """
        Check if slippage is enabled.
        
        Returns:
            True if either entry or exit slippage is configured
        """
        return self.entry_slippage_pct > 0 or self.exit_slippage_pct > 0
