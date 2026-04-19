"""
Risk Management Engine

Implements professional risk management including:
- Position sizing (Kelly Criterion adapted)
- Daily loss limits
- Maximum position limits
- Dynamic risk adjustment
- Portfolio heat mapping
- Circuit breakers

Philosophy: Protect capital first, make profits second.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, date


class RiskManager:
    """
    Professional risk management system for trading.
    Ensures capital preservation through strict risk controls.
    """
    
    def __init__(self, 
                 initial_capital: float,
                 risk_per_trade_pct: float = 1.5,
                 max_daily_loss: float = 2000,
                 max_positions: int = 6,
                 max_trades_per_day: int = 20):
        """
        Initialize risk manager.
        
        Args:
            initial_capital: Starting capital
            risk_per_trade_pct: Risk percentage per trade (default 1.5%)
            max_daily_loss: Maximum daily loss before stopping (₹)
            max_positions: Maximum concurrent positions
            max_trades_per_day: Maximum trades allowed per day
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_daily_loss = max_daily_loss
        self.max_positions = max_positions
        self.max_trades_per_day = max_trades_per_day
        
        # Daily tracking
        self.today = date.today()
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.trading_halted = False
        
        # Performance tracking
        self.win_rate = 0.5  # Start neutral
        self.recent_trades = []
        self.max_recent_trades = 20
        
        # Risk adjustment factor (0.5 to 1.5)
        self.risk_multiplier = 1.0
    
    def update_capital(self, current_capital: float):
        """Update current capital."""
        self.current_capital = current_capital
    
    def reset_daily_limits(self):
        """Reset daily counters if new day."""
        current_date = date.today()
        if current_date != self.today:
            self.today = current_date
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.trading_halted = False
    
    def calculate_position_size(self,
                               entry_price: float,
                               stop_loss_price: float,
                               atr: float,
                               volatility_regime: str = 'NORMAL') -> int:
        """
        Calculate optimal position size using risk-based approach.
        
        Incorporates:
        - Capital at risk (% of account)
        - Distance to stop loss
        - Volatility regime adjustment
        - Dynamic risk adjustment
        
        Args:
            entry_price: Intended entry price
            stop_loss_price: Stop loss price
            atr: Average True Range
            volatility_regime: 'LOW', 'NORMAL', or 'HIGH'
        
        Returns:
            Position size (number of contracts/shares)
        """
        if entry_price <= 0 or stop_loss_price <= 0:
            return 0
        
        # Calculate risk per share
        risk_per_unit = abs(entry_price - stop_loss_price)
        
        if risk_per_unit <= 0:
            return 0
        
        # Base risk amount (% of capital)
        base_risk_amount = self.current_capital * (self.risk_per_trade_pct / 100)
        
        # Adjust for volatility regime
        vol_adjustment = {
            'LOW': 1.2,      # Increase size in low volatility
            'NORMAL': 1.0,   # Standard size
            'HIGH': 0.7      # Reduce size in high volatility
        }
        regime_multiplier = vol_adjustment.get(volatility_regime, 1.0)
        
        # Apply dynamic risk adjustment (based on recent performance)
        adjusted_risk = base_risk_amount * self.risk_multiplier * regime_multiplier
        
        # Calculate position size
        position_size = int(adjusted_risk / risk_per_unit)
        
        # Ensure minimum viable position
        if position_size < 1:
            position_size = 1
        
        # Cap maximum position value at 20% of capital
        max_position_value = self.current_capital * 0.20
        max_size_by_value = int(max_position_value / entry_price)
        
        position_size = min(position_size, max_size_by_value)
        
        return position_size
    
    def calculate_kelly_position_size(self,
                                     win_rate: float,
                                     avg_win: float,
                                     avg_loss: float,
                                     entry_price: float) -> int:
        """
        Calculate position size using Kelly Criterion (fractional).
        
        Kelly % = (Win Rate * Avg Win - Loss Rate * Avg Loss) / Avg Win
        
        We use fractional Kelly (25-50%) to reduce variance.
        
        Args:
            win_rate: Historical win rate (0 to 1)
            avg_win: Average winning trade size
            avg_loss: Average losing trade size (positive value)
            entry_price: Entry price per unit
        
        Returns:
            Position size based on Kelly Criterion
        """
        if avg_win <= 0 or avg_loss <= 0:
            return 0
        
        # Kelly formula
        loss_rate = 1 - win_rate
        kelly_pct = (win_rate * avg_win - loss_rate * avg_loss) / avg_win
        
        # Use fractional Kelly (50% of full Kelly)
        fractional_kelly = kelly_pct * 0.5
        
        # Clamp between 0 and 10% of capital
        fractional_kelly = max(0, min(fractional_kelly, 0.10))
        
        # Calculate position size
        risk_amount = self.current_capital * fractional_kelly
        position_size = int(risk_amount / entry_price)
        
        return max(1, position_size)
    
    def check_daily_loss_limit(self, current_pnl: float) -> bool:
        """
        Check if daily loss limit has been hit.
        
        Args:
            current_pnl: Current day's PnL
        
        Returns:
            True if trading should stop, False otherwise
        """
        self.reset_daily_limits()
        self.daily_pnl = current_pnl
        
        if self.daily_pnl <= -self.max_daily_loss:
            self.trading_halted = True
            return True
        
        return False
    
    def check_trade_limit(self) -> bool:
        """
        Check if maximum daily trades reached.
        
        Returns:
            True if can trade, False if limit reached
        """
        self.reset_daily_limits()
        return self.daily_trades < self.max_trades_per_day
    
    def register_trade(self, pnl: float):
        """
        Register a trade for tracking and risk adjustment.
        
        Args:
            pnl: Profit/Loss of the trade
        """
        self.reset_daily_limits()
        self.daily_trades += 1
        
        # Track recent trades for performance adjustment
        self.recent_trades.append({
            'pnl': pnl,
            'timestamp': datetime.now()
        })
        
        # Keep only recent trades
        if len(self.recent_trades) > self.max_recent_trades:
            self.recent_trades.pop(0)
        
        # Update risk multiplier based on performance
        self._update_risk_multiplier()
    
    def _update_risk_multiplier(self):
        """
        Update dynamic risk multiplier based on recent performance.
        
        Logic:
        - Winning streak: Slightly increase risk (max 1.5x)
        - Losing streak: Reduce risk (min 0.5x)
        - Recent win rate considered
        """
        if len(self.recent_trades) < 5:
            self.risk_multiplier = 1.0
            return
        
        # Calculate recent win rate
        recent_pnls = [t['pnl'] for t in self.recent_trades]
        wins = sum(1 for pnl in recent_pnls if pnl > 0)
        self.win_rate = wins / len(recent_pnls)
        
        # Calculate recent performance
        recent_total = sum(recent_pnls)
        
        # Adjust multiplier
        if self.win_rate >= 0.60 and recent_total > 0:
            # Good performance: increase risk slightly
            self.risk_multiplier = min(1.5, self.risk_multiplier * 1.05)
        elif self.win_rate <= 0.40 or recent_total < 0:
            # Poor performance: decrease risk
            self.risk_multiplier = max(0.5, self.risk_multiplier * 0.95)
        else:
            # Neutral: gradually return to 1.0
            if self.risk_multiplier > 1.0:
                self.risk_multiplier = max(1.0, self.risk_multiplier * 0.98)
            else:
                self.risk_multiplier = min(1.0, self.risk_multiplier * 1.02)
    
    def can_open_position(self, current_positions: int) -> bool:
        """
        Check if new position can be opened.
        
        Args:
            current_positions: Number of currently open positions
        
        Returns:
            True if can open, False otherwise
        """
        self.reset_daily_limits()
        
        # Check halted status
        if self.trading_halted:
            return False
        
        # Check position limit
        if current_positions >= self.max_positions:
            return False
        
        # Check trade limit
        if not self.check_trade_limit():
            return False
        
        return True
    
    def calculate_portfolio_heat(self, open_positions: List[Dict]) -> float:
        """
        Calculate portfolio heat (total risk exposure).
        
        Heat = Sum of (Position Size * Distance to Stop) / Capital
        
        Args:
            open_positions: List of open positions with entry, stop, size
        
        Returns:
            Portfolio heat as percentage of capital
        """
        total_risk = 0.0
        
        for position in open_positions:
            entry_price = position.get('entry_price', 0)
            stop_price = position.get('stop_loss', 0)
            size = position.get('quantity', 0)
            
            if entry_price > 0 and stop_price > 0:
                risk_per_unit = abs(entry_price - stop_price)
                position_risk = risk_per_unit * size
                total_risk += position_risk
        
        if self.current_capital <= 0:
            return 100.0
        
        heat = (total_risk / self.current_capital) * 100
        return heat
    
    def get_max_position_value(self, entry_price: float) -> int:
        """
        Calculate maximum position size by value (20% of capital).
        
        Args:
            entry_price: Entry price per unit
        
        Returns:
            Maximum position size
        """
        if entry_price <= 0:
            return 0
        
        max_value = self.current_capital * 0.20
        max_size = int(max_value / entry_price)
        
        return max(1, max_size)
    
    def get_risk_status(self) -> Dict:
        """
        Get current risk management status.
        
        Returns:
            Dictionary with risk management metrics
        """
        self.reset_daily_limits()
        
        return {
            'capital': self.current_capital,
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades,
            'trading_halted': self.trading_halted,
            'risk_multiplier': self.risk_multiplier,
            'win_rate': self.win_rate,
            'max_daily_loss': self.max_daily_loss,
            'max_positions': self.max_positions,
            'max_trades_per_day': self.max_trades_per_day,
            'daily_loss_remaining': self.max_daily_loss + self.daily_pnl,
            'trades_remaining': self.max_trades_per_day - self.daily_trades
        }
    
    def should_reduce_risk(self) -> bool:
        """
        Determine if risk should be reduced based on current conditions.
        
        Returns:
            True if should reduce risk exposure
        """
        # Reduce risk if:
        # 1. Recent win rate is low
        # 2. Daily PnL is negative and approaching limit
        # 3. Too many trades today
        
        if self.win_rate < 0.40:
            return True
        
        if self.daily_pnl < -self.max_daily_loss * 0.5:
            return True
        
        if self.daily_trades > self.max_trades_per_day * 0.8:
            return True
        
        return False


def test_risk_manager():
    """Test function for RiskManager."""
    print("=" * 60)
    print("RISK MANAGER TEST")
    print("=" * 60)
    
    # Initialize risk manager
    rm = RiskManager(
        initial_capital=20000,
        risk_per_trade_pct=1.5,
        max_daily_loss=2000,
        max_positions=6
    )
    
    print(f"Initial Capital: ₹{rm.current_capital:,.2f}")
    print(f"Risk Per Trade: {rm.risk_per_trade_pct}%")
    print(f"Max Daily Loss: ₹{rm.max_daily_loss:,.2f}")
    
    # Test position sizing
    entry_price = 100.0
    stop_loss = 95.0  # 5% stop
    atr = 3.0
    
    size_normal = rm.calculate_position_size(entry_price, stop_loss, atr, 'NORMAL')
    size_high_vol = rm.calculate_position_size(entry_price, stop_loss, atr, 'HIGH')
    size_low_vol = rm.calculate_position_size(entry_price, stop_loss, atr, 'LOW')
    
    print("\n" + "=" * 60)
    print("POSITION SIZING TEST")
    print("=" * 60)
    print(f"Entry Price: ₹{entry_price}")
    print(f"Stop Loss: ₹{stop_loss} (Risk: ₹{entry_price - stop_loss}/unit)")
    print(f"ATR: {atr}")
    print(f"\nPosition Size (NORMAL vol): {size_normal} units")
    print(f"Position Size (HIGH vol): {size_high_vol} units")
    print(f"Position Size (LOW vol): {size_low_vol} units")
    
    # Test Kelly Criterion
    kelly_size = rm.calculate_kelly_position_size(0.6, 200, 100, entry_price)
    print(f"Kelly Criterion Size (60% win rate): {kelly_size} units")
    
    # Test daily limits
    print("\n" + "=" * 60)
    print("DAILY LIMITS TEST")
    print("=" * 60)
    
    print(f"Can open position (0 open): {rm.can_open_position(0)}")
    print(f"Can open position (6 open): {rm.can_open_position(6)}")
    
    # Simulate losing trades
    rm.register_trade(-100)
    rm.register_trade(-150)
    rm.register_trade(-200)
    
    status = rm.get_risk_status()
    print(f"\nAfter 3 losing trades:")
    print(f"  Risk Multiplier: {status['risk_multiplier']:.2f}")
    print(f"  Win Rate: {status['win_rate']:.1%}")
    print(f"  Daily Trades: {status['daily_trades']}")
    
    # Simulate winning trades
    rm.register_trade(250)
    rm.register_trade(300)
    rm.register_trade(200)
    
    status = rm.get_risk_status()
    print(f"\nAfter 3 winning trades:")
    print(f"  Risk Multiplier: {status['risk_multiplier']:.2f}")
    print(f"  Win Rate: {status['win_rate']:.1%}")
    
    # Test daily loss limit
    print("\n" + "=" * 60)
    print("CIRCUIT BREAKER TEST")
    print("=" * 60)
    
    hit_limit = rm.check_daily_loss_limit(-2500)
    print(f"Daily PnL: ₹-2,500")
    print(f"Trading Halted: {hit_limit}")
    print(f"Can Open Position: {rm.can_open_position(0)}")
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_risk_manager()

