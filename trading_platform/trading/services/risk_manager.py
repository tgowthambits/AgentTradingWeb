"""
Risk Manager - Position sizing, risk limits, and capital management.
Ported from trading_system/core/risk_manager.py
"""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal
import math

logger = logging.getLogger(__name__)


class RiskManager:
    """
    Manages risk parameters for trading.

    Features:
    - Position sizing based on risk per trade
    - Kelly criterion position sizing
    - Daily loss limits
    - Maximum positions management
    - Volatility-adjusted sizing
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the risk manager.

        Args:
            config: Risk configuration dictionary
        """
        self.config = config or {}

        # Capital
        self.initial_capital: float = self.config.get("initial_capital", 100000.0)
        self.current_capital: float = self.initial_capital

        # Risk parameters
        self.risk_per_trade_pct: float = self.config.get("risk_per_trade_pct", 2.0)
        self.max_position_size: int = self.config.get("max_position_size", 10000)
        self.capital_percentage_per_trade: float = self.config.get(
            "capital_percentage_per_trade", 80.0
        )

        # Daily limits
        self.max_daily_loss_pct: float = self.config.get("max_daily_loss_pct", 5.0)
        self.max_daily_loss_amount: float = self.config.get(
            "max_daily_loss_amount", 4000.0
        )
        self.max_trades_per_day: int = self.config.get("max_trades_per_day", 50)
        self.max_positions: int = self.config.get("max_positions", 3)

        # Tracking
        self.daily_pnl: float = 0.0
        self.trades_today: int = 0
        self.current_positions: int = 0

    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        atr: Optional[float] = None,
        volatility_regime: str = "normal",
    ) -> int:
        """
        Calculate position size based on risk parameters.

        Args:
            entry_price: Entry price for the trade
            stop_loss: Stop loss price
            atr: Average True Range (optional)
            volatility_regime: Market volatility regime ('low', 'normal', 'high')

        Returns:
            Calculated position size (quantity)
        """
        if entry_price <= 0 or stop_loss <= 0:
            return 0

        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss)

        if risk_per_share <= 0:
            return 0

        # Calculate max risk amount
        risk_amount = self.current_capital * (self.risk_per_trade_pct / 100.0)

        # Calculate base position size
        position_size = int(risk_amount / risk_per_share)

        # Adjust for volatility regime
        volatility_multiplier = {"low": 1.2, "normal": 1.0, "high": 0.7}.get(
            volatility_regime, 1.0
        )

        position_size = int(position_size * volatility_multiplier)

        # Apply maximum limits
        max_by_capital = int(
            (self.current_capital * self.capital_percentage_per_trade / 100.0)
            / entry_price
        )

        position_size = min(position_size, max_by_capital, self.max_position_size)

        return max(0, position_size)

    def calculate_kelly_position_size(
        self, win_rate: float, avg_win: float, avg_loss: float, entry_price: float
    ) -> int:
        """
        Calculate position size using Kelly Criterion.

        Args:
            win_rate: Historical win rate (0.0 to 1.0)
            avg_win: Average winning trade amount
            avg_loss: Average losing trade amount (positive value)
            entry_price: Entry price for the trade

        Returns:
            Calculated position size
        """
        if avg_loss <= 0 or entry_price <= 0:
            return 0

        # Kelly fraction: f* = (bp - q) / b
        # where b = avg_win/avg_loss, p = win_rate, q = 1 - win_rate

        b = avg_win / avg_loss
        p = win_rate
        q = 1 - win_rate

        kelly_fraction = (b * p - q) / b

        # Use half-Kelly for safety
        half_kelly = kelly_fraction / 2.0

        # Ensure fraction is within bounds
        half_kelly = max(0.0, min(half_kelly, 0.25))  # Max 25% of capital

        # Calculate position size
        risk_capital = self.current_capital * half_kelly
        position_size = int(risk_capital / entry_price)

        return min(position_size, self.max_position_size)

    def check_daily_loss_limit(self, current_pnl: float) -> bool:
        """
        Check if daily loss limit has been reached.

        Args:
            current_pnl: Current day's P&L

        Returns:
            True if trading should stop, False otherwise
        """
        self.daily_pnl = current_pnl

        # Check percentage limit
        pct_loss = abs(current_pnl) / self.initial_capital * 100.0
        if current_pnl < 0 and pct_loss >= self.max_daily_loss_pct:
            logger.warning(f"Daily loss limit reached: {pct_loss:.2f}%")
            return True

        # Check absolute amount limit
        if current_pnl < 0 and abs(current_pnl) >= self.max_daily_loss_amount:
            logger.warning(f"Daily loss amount limit reached: {abs(current_pnl):.2f}")
            return True

        return False

    def can_open_position(self, current_positions: int = None) -> bool:
        """
        Check if a new position can be opened.

        Args:
            current_positions: Number of current open positions

        Returns:
            True if a new position can be opened, False otherwise
        """
        if current_positions is not None:
            self.current_positions = current_positions

        # Check position limit
        if self.current_positions >= self.max_positions:
            logger.info(
                f"Max positions reached: {self.current_positions}/{self.max_positions}"
            )
            return False

        # Check daily trade limit
        if self.trades_today >= self.max_trades_per_day:
            logger.info(
                f"Max daily trades reached: {self.trades_today}/{self.max_trades_per_day}"
            )
            return False

        return True

    def record_trade(self, pnl: float):
        """Record a completed trade."""
        self.trades_today += 1
        self.daily_pnl += pnl
        self.current_capital += pnl

    def update_capital(self, new_capital: float):
        """Update current capital."""
        self.current_capital = new_capital

    def reset_daily_stats(self):
        """Reset daily statistics (call at market open)."""
        self.daily_pnl = 0.0
        self.trades_today = 0

    def get_risk_metrics(self) -> Dict[str, Any]:
        """Get current risk metrics."""
        return {
            "initial_capital": self.initial_capital,
            "current_capital": self.current_capital,
            "daily_pnl": self.daily_pnl,
            "daily_pnl_pct": (self.daily_pnl / self.initial_capital) * 100
            if self.initial_capital
            else 0,
            "trades_today": self.trades_today,
            "current_positions": self.current_positions,
            "max_positions": self.max_positions,
            "risk_per_trade_pct": self.risk_per_trade_pct,
        }

    def __repr__(self):
        return (
            f"RiskManager(capital={self.current_capital:.2f}, "
            f"risk_pct={self.risk_per_trade_pct}%, "
            f"positions={self.current_positions}/{self.max_positions})"
        )
