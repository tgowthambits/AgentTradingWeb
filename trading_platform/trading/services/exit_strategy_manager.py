"""
Exit Strategy Manager - Manages all exit strategies for positions.
Ported from trading_system/core/risk/exit_strategy_manager.py
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ExitStrategyManager:
    """
    Manages exit strategies for trading positions.

    Exit strategies:
    - Fixed stop loss
    - Volatility-adjusted stop loss
    - Trailing stop
    - Profit targets (multiple levels)
    - Time-based exit
    - Breakeven stop
    - Microstructure reversal detection
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the exit strategy manager.

        Args:
            config: Exit strategy configuration
        """
        self.config = config or {}

        # Stop loss configuration
        stop_loss_config = self.config.get("stop_loss", {})
        self.stop_loss_method = stop_loss_config.get("method", "fixed_amount")
        self.max_loss_per_trade = stop_loss_config.get("max_loss_per_trade", 2000.0)
        self.atr_multiplier = stop_loss_config.get("atr_multiplier", 1.5)
        self.breakeven_enabled = stop_loss_config.get("breakeven_enabled", False)
        self.breakeven_trigger_ratio = stop_loss_config.get(
            "breakeven_trigger_ratio", 1.0
        )

        # Profit targets configuration
        profit_targets_config = self.config.get("profit_targets", {})
        self.profit_targets_enabled = profit_targets_config.get("enabled", True)
        self.profit_targets = []
        for i in range(1, 4):
            target_config = profit_targets_config.get(f"target_{i}", {})
            if target_config:
                self.profit_targets.append(
                    {
                        "ratio": target_config.get("ratio", 1.0 + i * 0.5),
                        "exit_pct": target_config.get("exit_pct", 33.33),
                    }
                )

        # Trailing stop configuration
        trailing_config = self.config.get("trailing_stop", {})
        self.trailing_enabled = trailing_config.get("enabled", True)
        self.trailing_activation_ratio = trailing_config.get("activation_ratio", 1.05)
        self.trailing_atr_multiplier = trailing_config.get("trail_atr_multiplier", 1.5)

        # Time exit configuration
        time_config = self.config.get("time_exit", {})
        self.time_exit_enabled = time_config.get("enabled", False)
        self.max_hold_minutes = time_config.get("max_hold_minutes", 60)

        # Profit protection
        self.profit_drop_exit_enabled = self.config.get(
            "profit_drop_exit_enabled", True
        )
        self.profit_drop_threshold_pct = self.config.get(
            "profit_drop_threshold_pct", 50.0
        )

    def calculate_stop_loss(
        self,
        entry_price: float,
        position_type: str,
        atr: Optional[float] = None,
        quantity: int = 1,
    ) -> float:
        """
        Calculate the stop loss price.

        Args:
            entry_price: Entry price
            position_type: 'LONG' or 'SHORT'
            atr: Average True Range (optional)
            quantity: Position quantity

        Returns:
            Stop loss price
        """
        if self.stop_loss_method == "fixed_amount":
            # Calculate stop based on max loss amount
            loss_per_share = (
                self.max_loss_per_trade / quantity
                if quantity > 0
                else self.max_loss_per_trade
            )

            if position_type == "LONG":
                return entry_price - loss_per_share
            else:
                return entry_price + loss_per_share

        elif self.stop_loss_method == "atr" and atr is not None:
            # ATR-based stop loss
            stop_distance = atr * self.atr_multiplier

            if position_type == "LONG":
                return entry_price - stop_distance
            else:
                return entry_price + stop_distance

        elif self.stop_loss_method == "percentage":
            # Percentage-based stop loss
            stop_pct = self.config.get("stop_loss", {}).get("percentage", 2.0) / 100.0

            if position_type == "LONG":
                return entry_price * (1 - stop_pct)
            else:
                return entry_price * (1 + stop_pct)

        # Default: fixed amount
        loss_per_share = (
            self.max_loss_per_trade / quantity
            if quantity > 0
            else self.max_loss_per_trade
        )

        if position_type == "LONG":
            return entry_price - loss_per_share
        else:
            return entry_price + loss_per_share

    def calculate_trailing_stop(
        self,
        entry_price: float,
        current_price: float,
        highest_price: float,
        lowest_price: float,
        atr: Optional[float],
        position_type: str,
        current_stop: Optional[float] = None,
    ) -> Tuple[float, bool]:
        """
        Calculate trailing stop and check if it should be updated.

        Args:
            entry_price: Entry price
            current_price: Current market price
            highest_price: Highest price since entry (for LONG)
            lowest_price: Lowest price since entry (for SHORT)
            atr: Average True Range
            position_type: 'LONG' or 'SHORT'
            current_stop: Current stop loss price

        Returns:
            Tuple of (new_stop_price, should_update)
        """
        if not self.trailing_enabled:
            return current_stop or 0.0, False

        trail_distance = (
            atr * self.trailing_atr_multiplier if atr else entry_price * 0.02
        )

        if position_type == "LONG":
            # Check if trailing should be activated
            profit_ratio = current_price / entry_price

            if profit_ratio >= self.trailing_activation_ratio:
                new_stop = highest_price - trail_distance

                # Only update if new stop is higher than current
                if current_stop is None or new_stop > current_stop:
                    return new_stop, True

        else:  # SHORT
            profit_ratio = entry_price / current_price

            if profit_ratio >= self.trailing_activation_ratio:
                new_stop = lowest_price + trail_distance

                # Only update if new stop is lower than current
                if current_stop is None or new_stop < current_stop:
                    return new_stop, True

        return current_stop or 0.0, False

    def calculate_profit_targets(
        self, entry_price: float, atr: Optional[float], position_type: str
    ) -> List[Dict[str, Any]]:
        """
        Calculate profit target levels.

        Args:
            entry_price: Entry price
            atr: Average True Range
            position_type: 'LONG' or 'SHORT'

        Returns:
            List of profit target dictionaries
        """
        if not self.profit_targets_enabled or not self.profit_targets:
            return []

        targets = []

        for target in self.profit_targets:
            ratio = target["ratio"]
            exit_pct = target["exit_pct"]

            if position_type == "LONG":
                target_price = entry_price * ratio
            else:
                target_price = entry_price * (2 - ratio)  # Inverse for SHORT

            targets.append(
                {
                    "price": target_price,
                    "exit_pct": exit_pct,
                    "ratio": ratio,
                    "hit": False,
                }
            )

        return targets

    def check_time_exit(
        self, entry_time: datetime, current_time: datetime, current_pnl: float
    ) -> Tuple[bool, str]:
        """
        Check if position should be exited based on time.

        Args:
            entry_time: Time position was opened
            current_time: Current time
            current_pnl: Current unrealized P&L

        Returns:
            Tuple of (should_exit, reason)
        """
        if not self.time_exit_enabled:
            return False, ""

        hold_duration = (current_time - entry_time).total_seconds() / 60.0

        # Only time exit losing trades
        if hold_duration >= self.max_hold_minutes and current_pnl <= 0:
            return True, "time_exit"

        return False, ""

    def should_exit_position(
        self,
        position: Dict[str, Any],
        current_price: float,
        atr: Optional[float] = None,
        volatility_regime: str = "normal",
        recent_prices: Optional[List[float]] = None,
        recent_volumes: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """
        Determine if a position should be exited and why.

        Args:
            position: Position dictionary with entry details
            current_price: Current market price
            atr: Average True Range
            volatility_regime: Market volatility regime
            recent_prices: Recent price history
            recent_volumes: Recent volume history

        Returns:
            Dictionary with exit decision and details
        """
        entry_price = position.get("entry_price", 0)
        position_type = position.get("position_type", "LONG")
        quantity = position.get("quantity", 1)
        stop_loss = position.get("stop_loss")
        trailing_stop = position.get("trailing_stop")
        max_profit = position.get("max_profit", 0)
        entry_time = position.get("entry_time")

        # Calculate current P&L
        if position_type == "LONG":
            unrealized_pnl = (current_price - entry_price) * quantity
        else:
            unrealized_pnl = (entry_price - current_price) * quantity

        result = {
            "should_exit": False,
            "exit_reason": None,
            "exit_quantity": 0,
            "exit_type": None,  # 'full' or 'partial'
            "new_stop_loss": stop_loss,
            "new_trailing_stop": trailing_stop,
            "unrealized_pnl": unrealized_pnl,
        }

        # 1. Check hard stop loss
        if stop_loss:
            hit_stop = (position_type == "LONG" and current_price <= stop_loss) or (
                position_type == "SHORT" and current_price >= stop_loss
            )

            if hit_stop:
                result["should_exit"] = True
                result["exit_reason"] = "stop_loss"
                result["exit_quantity"] = quantity
                result["exit_type"] = "full"
                return result

        # 2. Check trailing stop
        if trailing_stop:
            hit_trailing = (
                position_type == "LONG" and current_price <= trailing_stop
            ) or (position_type == "SHORT" and current_price >= trailing_stop)

            if hit_trailing:
                result["should_exit"] = True
                result["exit_reason"] = "trailing_stop"
                result["exit_quantity"] = quantity
                result["exit_type"] = "full"
                return result

        # 3. Check profit drop protection
        if self.profit_drop_exit_enabled and max_profit > 0 and unrealized_pnl > 0:
            profit_drop_pct = ((max_profit - unrealized_pnl) / max_profit) * 100

            if profit_drop_pct >= self.profit_drop_threshold_pct:
                result["should_exit"] = True
                result["exit_reason"] = "profit_protection"
                result["exit_quantity"] = quantity
                result["exit_type"] = "full"
                return result

        # 4. Check time-based exit
        if entry_time and self.time_exit_enabled:
            current_time = datetime.now()
            if isinstance(entry_time, str):
                entry_time = datetime.fromisoformat(entry_time)

            should_time_exit, reason = self.check_time_exit(
                entry_time, current_time, unrealized_pnl
            )
            if should_time_exit:
                result["should_exit"] = True
                result["exit_reason"] = reason
                result["exit_quantity"] = quantity
                result["exit_type"] = "full"
                return result

        # 5. Update trailing stop if needed
        if self.trailing_enabled and atr:
            highest = position.get("highest_price", entry_price)
            lowest = position.get("lowest_price", entry_price)

            new_trailing, should_update = self.calculate_trailing_stop(
                entry_price,
                current_price,
                highest,
                lowest,
                atr,
                position_type,
                trailing_stop,
            )

            if should_update:
                result["new_trailing_stop"] = new_trailing

        return result

    def __repr__(self):
        return (
            f"ExitStrategyManager("
            f"stop_method={self.stop_loss_method}, "
            f"trailing={self.trailing_enabled}, "
            f"targets={len(self.profit_targets)})"
        )
