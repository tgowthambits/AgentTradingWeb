"""
Circuit Breaker Module

Implements paper trading mode activation after consecutive losses
to protect capital during losing streaks.
"""

from typing import Dict, Any, Optional
from datetime import datetime


class CircuitBreaker:
    """
    Circuit breaker for capital protection during losing streaks.
    
    The circuit breaker tracks consecutive losses from ALL exit types:
    - Hard stop loss, Breakeven stop
    - Trailing stop
    - Microstructure reversal
    - Profit target reversal
    - Time-based exits
    - Partial exits (if they result in losses)
    
    When consecutive losses reach the trigger threshold, paper trading mode
    is activated to prevent real capital loss until a profitable trade occurs.
    
    Attributes:
        consecutive_losses: Current count of consecutive losing trades
        paper_trading_mode: Whether paper trading mode is currently active
        paper_mode_enabled: Whether circuit breaker feature is enabled
        paper_mode_trigger: Number of consecutive losses to trigger paper mode
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the CircuitBreaker.
        
        Args:
            config: Trading configuration dictionary
        """
        self.config = config or {}
        self._load_config()
        self._log_initialization()
    
    def _load_config(self):
        """Load circuit breaker configuration from config."""
        paper_mode_config = self.config.get('risk_management', {}).get('paper_trading_mode', {})
        self.paper_mode_config = paper_mode_config
        self.paper_mode_enabled = paper_mode_config.get('enabled', False)
        self.paper_mode_trigger = paper_mode_config.get('consecutive_losses_trigger', 3)
        
        # State tracking
        self.consecutive_losses = 0
        self.paper_trading_mode = False
    
    def _log_initialization(self):
        """Log circuit breaker initialization status."""
        if self.paper_mode_enabled:
            print(f"🛡️  CIRCUIT BREAKER INITIALIZED: Enabled=True, Trigger={self.paper_mode_trigger} consecutive losses")
            print(f"   📊 Tracks losses from ALL exit types (stop loss, trailing stop, microstructure, etc.)")
        else:
            print(f"⚠️  CIRCUIT BREAKER DISABLED: paper_trading_mode.enabled=False in config")
    
    def reload_config(self, config: Dict[str, Any]):
        """
        Reload configuration with new config.
        
        Args:
            config: New trading configuration dictionary
        """
        self.config = config
        self._load_config()
    
    def reset(self):
        """Reset circuit breaker state."""
        self.consecutive_losses = 0
        self.paper_trading_mode = False
    
    def should_use_paper_trade(self) -> bool:
        """
        Determine if the next trade should be a paper trade.
        
        Returns:
            True if paper trading mode is active and enabled
        """
        return self.paper_mode_enabled and self.paper_trading_mode
    
    def process_trade_result(
        self,
        pnl: float,
        is_paper_trade: bool,
        exit_reason: str = ""
    ) -> Dict[str, Any]:
        """
        Process a trade result and update circuit breaker state.
        
        Args:
            pnl: Profit/loss from the trade
            is_paper_trade: Whether this was a paper trade
            exit_reason: The reason for trade exit
        
        Returns:
            Dictionary with state changes and messages
        """
        result = {
            'mode_changed': False,
            'paper_mode_active': self.paper_trading_mode,
            'consecutive_losses': self.consecutive_losses,
            'messages': []
        }
        
        if not self.paper_mode_enabled:
            # Circuit breaker disabled - only log on first loss
            if not is_paper_trade and pnl < 0 and self.consecutive_losses == 0:
                result['messages'].append("⚠️  Loss occurred but paper trading mode is DISABLED")
                result['messages'].append("   Enable it in config: risk_management.paper_trading_mode.enabled = True")
            return result
        
        if not is_paper_trade:
            # Real trade - update consecutive losses
            if pnl < 0:
                self.consecutive_losses += 1
                result['consecutive_losses'] = self.consecutive_losses
                result['messages'].append(
                    f"⚠️  Consecutive losses: {self.consecutive_losses}/{self.paper_mode_trigger} "
                    f"(Exit: {exit_reason}, Paper Mode: {self.paper_trading_mode})"
                )
                result['messages'].append(
                    "   📊 Circuit breaker tracks losses from ALL exit types (stop loss, trailing stop, microstructure, etc.)"
                )
                
                # Check if we should enter paper trading mode
                if self.consecutive_losses >= self.paper_mode_trigger:
                    if not self.paper_trading_mode:
                        self.paper_trading_mode = True
                        result['mode_changed'] = True
                        result['paper_mode_active'] = True
                        result['messages'].extend([
                            f"🛑 PAPER TRADING MODE ACTIVATED after {self.consecutive_losses} consecutive losses!",
                            "   Next orders will be PAPER TRADES until one is profitable",
                            "   This will protect capital by not executing real trades",
                            "   ⚠️  Circuit breaker active for ALL exit conditions (not just stop loss)"
                        ])
                    else:
                        result['messages'].append(
                            f"🛡️  Paper trading mode already active ({self.consecutive_losses} consecutive losses)"
                        )
            else:
                # Winning trade - reset counter and exit paper mode
                if self.consecutive_losses > 0:
                    result['messages'].append(
                        f"✅ Winning trade! Resetting consecutive losses counter (was {self.consecutive_losses})"
                    )
                
                self.consecutive_losses = 0
                result['consecutive_losses'] = 0
                
                # Exit paper mode if it was active
                if self.paper_trading_mode:
                    self.paper_trading_mode = False
                    result['mode_changed'] = True
                    result['paper_mode_active'] = False
                    result['messages'].append("✅ Exiting paper trading mode after profitable REAL trade")
        else:
            # Paper trade - check if profitable to exit paper mode
            if pnl > 0:
                result['messages'].append("✅ Paper trade profitable! Exiting paper trading mode")
                self.paper_trading_mode = False
                self.consecutive_losses = 0
                result['mode_changed'] = True
                result['paper_mode_active'] = False
                result['consecutive_losses'] = 0
            elif pnl < 0:
                result['messages'].append(f"📝 Paper trade loss: ₹{abs(pnl):.2f} (Capital protected - no real loss)")
        
        return result
    
    def get_capital_comparison(
        self,
        actual_capital: float,
        hypothetical_capital: float
    ) -> Dict[str, Any]:
        """
        Get capital comparison between actual and hypothetical (without circuit breaker).
        
        Args:
            actual_capital: Capital with circuit breaker protection
            hypothetical_capital: Capital without circuit breaker (all trades counted)
        
        Returns:
            Dictionary with comparison data
        """
        savings = actual_capital - hypothetical_capital
        
        return {
            'actual_capital': actual_capital,
            'hypothetical_capital': hypothetical_capital,
            'savings': savings,
            'protected': savings > 0
        }
    
    def format_capital_comparison(
        self,
        actual_capital: float,
        hypothetical_capital: float
    ) -> str:
        """
        Format capital comparison for display.
        
        Args:
            actual_capital: Capital with circuit breaker protection
            hypothetical_capital: Capital without circuit breaker
        
        Returns:
            Formatted string for display
        """
        if not self.paper_mode_enabled:
            return ""
        
        savings = actual_capital - hypothetical_capital
        lines = [
            "\n💰 Capital Comparison:",
            f"   WITHOUT Circuit Breaker: ₹{hypothetical_capital:,.2f}",
            f"   WITH Circuit Breaker:    ₹{actual_capital:,.2f}"
        ]
        
        if savings > 0:
            lines.append(f"   💚 Savings: ₹{savings:+,.2f} (Protected by circuit breaker!)")
        elif savings < 0:
            lines.append(f"   ⚪ Difference: ₹{savings:+,.2f}")
        else:
            lines.append("   ⚪ Same capital (no paper trades yet)")
        
        return "\n".join(lines)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current circuit breaker status.
        
        Returns:
            Dictionary with current status
        """
        return {
            'enabled': self.paper_mode_enabled,
            'paper_trading_mode': self.paper_trading_mode,
            'consecutive_losses': self.consecutive_losses,
            'trigger_threshold': self.paper_mode_trigger
        }
    
    def is_enabled(self) -> bool:
        """Check if circuit breaker is enabled."""
        return self.paper_mode_enabled
    
    def is_active(self) -> bool:
        """Check if paper trading mode is currently active."""
        return self.paper_trading_mode
