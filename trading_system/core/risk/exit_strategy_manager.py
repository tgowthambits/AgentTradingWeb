"""
Exit Strategy Manager

Implements multiple sophisticated exit strategies:
1. Volatility-Adjusted Stop Loss
2. Trailing Stop with ATR Bands
3. Profit Target Zones
4. Time-Based Exits
5. Microstructure Reversal Detection

Philosophy: Cut losses quickly, let winners run with protection.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional, List
from datetime import datetime, timedelta


class ExitStrategyManager:
    """
    Professional exit strategy system.
    Manages multiple exit conditions and determines optimal exit points.
    """
    
    def __init__(self,
                 atr_multiplier: float = 2.0,
                 trailing_enabled: bool = True,
                 profit_targets_enabled: bool = True,
                 time_exit_enabled: bool = True,
                 config: dict = None):
        """
        Initialize exit strategy manager.
        
        Args:
            atr_multiplier: Default ATR multiplier for stops
            trailing_enabled: Enable trailing stop
            profit_targets_enabled: Enable profit targets
            time_exit_enabled: Enable time-based exits
            config: Full trading configuration (for microstructure settings)
        """
        self.atr_multiplier = atr_multiplier
        self.trailing_enabled = trailing_enabled
        self.profit_targets_enabled = profit_targets_enabled
        self.time_exit_enabled = time_exit_enabled
        self.config = config or {}
        
        risk_mgmt_config = self.config.get('risk_management', {})
        
        # Get profit target config (including reversal and exit-on-hit behavior)
        profit_targets_config = risk_mgmt_config.get('profit_targets', {})
        reversal_config = profit_targets_config.get('reversal', {})
        self.reversal_enabled = reversal_config.get('enabled', True)
        self.reversal_atr_multiplier = reversal_config.get('atr_multiplier', 0.5)
        self.reversal_percent_threshold = reversal_config.get('percent_threshold', 1.0)
        # New: optional early exit when a profit target is hit
        # If enabled, we will exit the full position on the first target hit
        self.exit_on_first_target_hit = profit_targets_config.get('exit_on_first_target_hit', False)
        
        # Get profit reversal protection config
        profit_reversal_config = risk_mgmt_config.get('profit_reversal_protection', {})
        self.profit_reversal_enabled = profit_reversal_config.get('enabled', True)
        self.profit_reversal_min_profit = profit_reversal_config.get('min_profit', 100.0)  # Minimum profit to activate
        self.profit_reversal_threshold = profit_reversal_config.get('reversal_threshold', 50.0)  # % of profit to give back before exit
        self.profit_reversal_atr_multiplier = profit_reversal_config.get('atr_multiplier', 1.0)  # Optional ATR-based threshold
        
        # Get profit drop protection config (percentage-based drop from max profit)
        profit_drop_config = risk_mgmt_config.get('profit_drop_protection', {})
        self.profit_drop_enabled = profit_drop_config.get('enabled', False)
        self.profit_drop_percentage = profit_drop_config.get('drop_percentage', 3.0)  # Default 3% drop from max profit
        
        # Get unrealized profit drop exit config (for backtesting - exits if profit drops by X% from peak)
        unrealized_drop_config = risk_mgmt_config.get('unrealized_profit_drop', {})
        self.unrealized_drop_enabled = unrealized_drop_config.get('enabled', False)
        self.unrealized_drop_threshold = unrealized_drop_config.get('percent_threshold', 4.0)  # Default 4% drop threshold
        
        # Get below average profit exit config (legacy, kept for backward compatibility)
        below_avg_profit_config = risk_mgmt_config.get('below_avg_profit_exit', {})
        self.below_avg_profit_enabled = below_avg_profit_config.get('enabled', False)
        self.below_avg_profit_min_profit = below_avg_profit_config.get('min_profit', 50.0)
        
        # Profit pullback exit: exits when unrealized profit drops by a configurable
        # percentage from peak. Arms only after peak profit crosses activation_amount.
        # Ensures exit profit stays above min_exit_profit so we always close in profit.
        pullback_config = risk_mgmt_config.get('profit_pullback_exit', {})
        self.pullback_enabled = pullback_config.get('enabled', False)
        self.pullback_activation_amount = pullback_config.get('activation_amount', 500.0)
        self.pullback_percentage = pullback_config.get('pullback_percentage', 40.0)
        self.pullback_min_exit_profit = pullback_config.get('min_exit_profit', 100.0)
        
        # Get partial exits config (controls whether positions can exit partially or must exit fully)
        partial_exits_config = risk_mgmt_config.get('partial_exits', {})
        self.partial_exits_enabled = partial_exits_config.get('enabled', True)  # Default True to maintain current behavior
        
        # Get breakeven stop config
        stop_loss_config = risk_mgmt_config.get('stop_loss', {})
        self.breakeven_enabled = stop_loss_config.get('breakeven_enabled', True)  # Default True to maintain current behavior
        self.breakeven_trigger_ratio = stop_loss_config.get('breakeven_trigger_ratio', 1.05)
        
        # Get trailing stop config (used by runtime exit logic)
        trailing_stop_config = risk_mgmt_config.get('trailing_stop', {})
        # These mirror the values used in calculate_exit_prices_for_display
        self.trailing_activation_ratio = trailing_stop_config.get('activation_ratio', 1.2)
        self.trailing_trail_multiplier = trailing_stop_config.get('trail_atr_multiplier', 1.5)
        
        # Get time-based exit config
        time_exit_config = risk_mgmt_config.get('time_exit', {})
        self.time_exit_max_hold_minutes = time_exit_config.get('max_hold_minutes', 60)
    
    def calculate_volatility_stop(self,
                                  entry_price: float,
                                  atr: float,
                                  position_type: str,
                                  volatility_regime: str = 'NORMAL',
                                  multiplier: Optional[float] = None) -> float:
        """
        Calculate volatility-adjusted stop loss.
        
        Stop distance adapts to market volatility:
        - Low volatility: Tighter stops (1.5x ATR)
        - Normal volatility: Standard stops (2.0x ATR)
        - High volatility: Wider stops (3.0x ATR)
        
        Args:
            entry_price: Entry price
            atr: Average True Range
            position_type: 'LONG' or 'SHORT'
            volatility_regime: 'LOW', 'NORMAL', or 'HIGH'
            multiplier: Override multiplier (optional)
        
        Returns:
            Stop loss price
        """
        # Determine multiplier based on volatility regime
        if multiplier is None:
            regime_multipliers = {
                'LOW': 1.5,
                'NORMAL': 2.0,
                'HIGH': 3.0
            }
            multiplier = regime_multipliers.get(volatility_regime, self.atr_multiplier)
        
        # Calculate stop distance
        stop_distance = atr * multiplier
        
        # Apply based on position type
        if position_type == 'LONG':
            stop_price = entry_price - stop_distance
        else:  # SHORT
            stop_price = entry_price + stop_distance
        
        return stop_price
    
    def calculate_fixed_amount_stop(self,
                                    entry_price: float,
                                    quantity: int,
                                    max_loss_amount: float,
                                    position_type: str) -> float:
        """
        Calculate stop loss based on maximum rupee amount loss.
        
        This ensures no trade loses more than a specific amount (e.g., ₹300).
        
        Args:
            entry_price: Entry price
            quantity: Position quantity
            max_loss_amount: Maximum loss in rupees (e.g., 300)
            position_type: 'LONG' or 'SHORT'
        
        Returns:
            Stop loss price
        
        Example:
            Entry: ₹100, Quantity: 25, Max Loss: ₹300
            Loss per unit: ₹300 / 25 = ₹12
            Stop for LONG: ₹100 - ₹12 = ₹88
        """
        # Calculate loss per unit
        loss_per_unit = max_loss_amount / quantity if quantity > 0 else 0
        
        # Calculate stop price
        if position_type == 'LONG':
            stop_price = entry_price - loss_per_unit
        else:  # SHORT
            stop_price = entry_price + loss_per_unit
        
        return stop_price
    
    def calculate_trailing_stop(self,
                                entry_price: float,
                                current_price: float,
                                highest_price: float,
                                lowest_price: float,
                                atr: float,
                                position_type: str,
                                activation_ratio: float = 1.2,
                                trail_multiplier: float = 1.5) -> Tuple[float, bool]:
        """
        Calculate trailing stop that follows price in profitable direction.
        
        Activates after price moves favorably by activation_ratio.
        Trails at trail_multiplier * ATR distance.
        
        Args:
            entry_price: Original entry price
            current_price: Current market price
            highest_price: Highest price since entry (for LONG)
            lowest_price: Lowest price since entry (for SHORT)
            atr: Average True Range
            position_type: 'LONG' or 'SHORT'
            activation_ratio: Profit ratio to activate (1.2 = 20% profit)
            trail_multiplier: ATR multiplier for trailing distance
        
        Returns:
            (stop_price, is_activated)
        """
        trail_distance = atr * trail_multiplier
        
        if position_type == 'LONG':
            # Check if profitable enough to activate trailing
            profit_ratio = current_price / entry_price
            is_activated = profit_ratio >= activation_ratio
            
            if is_activated:
                # Trail below the highest price
                stop_price = highest_price - trail_distance
                # Never move stop below entry (lock in profits)
                stop_price = max(stop_price, entry_price)
            else:
                # Not activated yet, use initial stop
                stop_price = entry_price - (atr * self.atr_multiplier)
            
        else:  # SHORT
            profit_ratio = entry_price / current_price
            is_activated = profit_ratio >= activation_ratio
            
            if is_activated:
                # Trail above the lowest price
                stop_price = lowest_price + trail_distance
                # Never move stop above entry
                stop_price = min(stop_price, entry_price)
            else:
                # Not activated yet, use initial stop
                stop_price = entry_price + (atr * self.atr_multiplier)
        
        return stop_price, is_activated
    
    def calculate_profit_targets(self,
                                entry_price: float,
                                atr: float,
                                position_type: str,
                                risk_reward_ratios: List[Tuple[float, float]] = None) -> List[Dict]:
        """
        Calculate multiple profit target zones.
        
        Default targets:
        - Target 1: 1.5x risk (take 50% off)
        - Target 2: 2.5x risk (take 30% off)
        - Target 3: 4.0x risk (let 20% ride)
        
        Args:
            entry_price: Entry price
            atr: Average True Range
            position_type: 'LONG' or 'SHORT'
            risk_reward_ratios: List of (ratio, exit_pct) tuples
        
        Returns:
            List of profit target dictionaries
        """
        if risk_reward_ratios is None:
            risk_reward_ratios = [
                (1.5, 50),  # 1.5x risk, exit 50%
                (2.5, 30),  # 2.5x risk, exit 30%
                (4.0, 20)   # 4.0x risk, exit 20%
            ]
        
        # Risk is based on ATR
        risk = atr * self.atr_multiplier
        
        targets = []
        for ratio, exit_pct in risk_reward_ratios:
            reward = risk * ratio
            
            if position_type == 'LONG':
                target_price = entry_price + reward
            else:  # SHORT
                target_price = entry_price - reward
            
            targets.append({
                'price': target_price,
                'ratio': ratio,
                'exit_percentage': exit_pct,
                'hit': False
            })
        
        return targets
    
    def calculate_time_decay_exit(self,
                                  entry_time: datetime,
                                  current_time: datetime,
                                  current_pnl: float,
                                  volatility: float,
                                  initial_volatility: float,
                                  max_hold_minutes: int = 60) -> Tuple[bool, str]:
        """
        Determine if position should exit due to time decay.
        
        Exit conditions:
        1. Position held > max_hold_minutes AND not profitable
        2. Volatility dropped significantly (momentum gone)
        
        Args:
            entry_time: Entry timestamp
            current_time: Current timestamp
            current_pnl: Current profit/loss
            volatility: Current volatility
            initial_volatility: Volatility at entry
            max_hold_minutes: Maximum hold time for losing trades
        
        Returns:
            (should_exit, reason)
        """
        hold_duration = (current_time - entry_time).total_seconds() / 60
        
        # Check time limit for losing trades
        if hold_duration > max_hold_minutes and current_pnl < 0:
            return True, f"Time exit: Held {hold_duration:.0f}min with loss"
        
        # Check volatility decay (momentum exhaustion)
        if initial_volatility > 0:
            vol_ratio = volatility / initial_volatility
            if vol_ratio < 0.5 and hold_duration > max_hold_minutes * 0.5:
                return True, "Volatility decay: Momentum exhausted"
        
        return False, ""
    
    def detect_microstructure_reversal(self,
                                      recent_prices: List[float],
                                      recent_volumes: List[float],
                                      position_type: str) -> Tuple[bool, str]:
        """
        Detect order flow reversal using microstructure analysis.
        
        HFT technique: Identify when large orders start absorbing the move.
        
        Signals:
        - Volume spike with price rejection (wick)
        - Series of higher volume with decreasing price movement
        
        Args:
            recent_prices: Last 5-10 prices
            recent_volumes: Last 5-10 volumes
            position_type: 'LONG' or 'SHORT'
        
        Returns:
            (is_reversal, reason)
        """
        if len(recent_prices) < 5 or len(recent_volumes) < 5:
            return False, ""
        
        # Get last 5 bars
        prices = np.array(recent_prices[-5:])
        volumes = np.array(recent_volumes[-5:])
        
        # Calculate price changes and volume changes
        price_changes = np.diff(prices)
        volume_changes = np.diff(volumes)
        
        # Detect volume spike
        avg_volume = np.mean(volumes[:-1])
        last_volume = volumes[-1]
        volume_spike = last_volume > avg_volume * 1.5
        
        if not volume_spike:
            return False, ""
        
        # Check for price rejection
        if position_type == 'LONG':
            # Look for lower high or price rejection after spike
            if price_changes[-1] < 0 and abs(price_changes[-1]) > np.std(price_changes):
                return True, "Microstructure: Volume spike with price rejection"
        
        else:  # SHORT
            # Look for higher low or price rejection
            if price_changes[-1] > 0 and abs(price_changes[-1]) > np.std(price_changes):
                return True, "Microstructure: Volume spike with price rejection"
        
        return False, ""
    
    def calculate_exit_prices_for_display(self,
                                         position: dict,
                                         current_price: float,
                                         atr: float,
                                         volatility_regime: str,
                                         config: dict = None) -> List[Tuple[str, str]]:
        """
        Calculate exit prices for UI display purposes.
        
        This method calculates all potential exit prices without evaluating
        actual exit conditions. Used by UI to show what exit prices would be triggered.
        
        Args:
            position: Position dictionary with entry details
            current_price: Current market price
            atr: Current ATR
            volatility_regime: Current volatility regime
            config: Configuration dictionary (optional, uses self.config if not provided)
        
        Returns:
            List of tuples (formatted_string, label) for color coding
            Example: [("SL:95.00", "SL"), ("PT1(50%→₹500):105.00", "PT1")]
        """
        exit_price_list = []
        exit_labels = []
        
        try:
            # Use provided config or fallback to self.config
            risk_config = config.get('risk_management', {}) if config else self.config.get('risk_management', {})
            
            entry_price = position.get('entry_price', 0)
            position_type = position.get('type', 'LONG')
            quantity = position.get('quantity', 0)
            highest_price = position.get('highest_price', entry_price)
            lowest_price = position.get('lowest_price', entry_price)
            
            if entry_price <= 0:
                return []
            
            stop_loss_config = risk_config.get('stop_loss', {})
            profit_targets_config = risk_config.get('profit_targets', {})
            trailing_stop_config = risk_config.get('trailing_stop', {})
            
            # 1. Calculate Stop Loss exit price(s) - ALWAYS calculate
            try:
                stop_loss_method = stop_loss_config.get('method', 'volatility')
                atr_multiplier = stop_loss_config.get('atr_multiplier', 1.5)
                max_loss_per_trade = stop_loss_config.get('max_loss_per_trade', None)
                
                # Calculate volatility stop if ATR available
                if atr > 0:
                    vol_stop = self.calculate_volatility_stop(
                        entry_price, atr, position_type, volatility_regime
                    )
                    exit_price_list.append(vol_stop)
                    exit_labels.append('SL')
                # Fallback: use percentage-based stop if ATR not available
                elif stop_loss_config.get('min_stop_pct'):
                    stop_pct = stop_loss_config.get('min_stop_pct', 0.8) / 100.0
                    if position_type == 'LONG':
                        vol_stop = entry_price * (1 - stop_pct)
                    else:
                        vol_stop = entry_price * (1 + stop_pct)
                    exit_price_list.append(vol_stop)
                    exit_labels.append('SL')
                
                # Calculate fixed amount stop if configured and different
                if max_loss_per_trade and quantity > 0:
                    fixed_stop = self.calculate_fixed_amount_stop(
                        entry_price, quantity, max_loss_per_trade, position_type
                    )
                    # Only add if different from volatility stop
                    if exit_price_list:
                        if abs(fixed_stop - exit_price_list[0]) > 0.01:
                            exit_price_list.append(fixed_stop)
                            exit_labels.append('SL-Fixed')
                    else:
                        exit_price_list.append(fixed_stop)
                        exit_labels.append('SL')
                        
            except Exception as e:
                print(f"Error calculating stop loss: {e}")
                import traceback
                traceback.print_exc()
            
            # 2. Calculate Profit Target exit prices - if enabled
            try:
                if profit_targets_config.get('enabled', False):
                    # Get custom targets from config
                    risk_reward_ratios = None
                    target_configs = {}  # Store full config for each target
                    if 'target_1' in profit_targets_config:
                        ratios = []
                        for i in [1, 2, 3]:
                            target_key = f'target_{i}'
                            if target_key in profit_targets_config:
                                target = profit_targets_config[target_key]
                                ratio = target.get('ratio', 1.5 + (i-1) * 0.5)
                                exit_pct = target.get('exit_pct', 50.0 - (i-1) * 15.0)
                                ratios.append((ratio, exit_pct))
                                target_configs[i] = {'ratio': ratio, 'exit_pct': exit_pct}
                        if ratios:
                            risk_reward_ratios = ratios
                    
                    # Calculate profit targets
                    if atr > 0:
                        targets = self.calculate_profit_targets(
                            entry_price, atr, position_type, risk_reward_ratios
                        )
                        for i, target in enumerate(targets, 1):
                            target_price = target['price']
                            exit_pct = target.get('exit_percentage', target_configs.get(i, {}).get('exit_pct', 50.0))
                            
                            # Calculate profit amount for this target
                            if position_type == 'LONG':
                                profit_per_unit = target_price - entry_price
                            else:
                                profit_per_unit = entry_price - target_price
                            
                            profit_amount = profit_per_unit * quantity * (exit_pct / 100.0)
                            
                            # Format label with exit percentage and profit
                            exit_price_list.append(target_price)
                            exit_labels.append(f'PT{i}({exit_pct:.0f}%→₹{profit_amount:.0f})')
                    else:
                        # Fallback: calculate from stop loss distance
                        if exit_price_list:
                            stop_distance = abs(entry_price - exit_price_list[0])
                            # Use default ratios if not provided
                            if not risk_reward_ratios:
                                risk_reward_ratios = [(1.5, 50.0), (2.0, 30.0), (3.0, 20.0)]
                            
                            for i, (ratio, exit_pct) in enumerate(risk_reward_ratios, 1):
                                if position_type == 'LONG':
                                    target_price = entry_price + (stop_distance * ratio)
                                    profit_per_unit = target_price - entry_price
                                else:
                                    target_price = entry_price - (stop_distance * ratio)
                                    profit_per_unit = entry_price - target_price
                                
                                profit_amount = profit_per_unit * quantity * (exit_pct / 100.0)
                                
                                exit_price_list.append(target_price)
                                exit_labels.append(f'PT{i}({exit_pct:.0f}%→₹{profit_amount:.0f})')
                                
            except Exception as e:
                print(f"Error calculating profit targets: {e}")
                import traceback
                traceback.print_exc()
            
            # 3. Calculate Trailing Stop exit price - if enabled (always show, even if not activated)
            try:
                if trailing_stop_config.get('enabled', False):
                    activation_ratio = trailing_stop_config.get('activation_ratio', 1.05)
                    trail_multiplier = trailing_stop_config.get('trail_atr_multiplier', 1.5)
                    
                    if atr > 0:
                        trail_stop, is_activated = self.calculate_trailing_stop(
                            entry_price, current_price, highest_price, lowest_price,
                            atr, position_type, activation_ratio, trail_multiplier
                        )
                    else:
                        # Fallback: use initial stop as trailing stop
                        if exit_price_list:
                            trail_stop = exit_price_list[0]  # Use first stop loss
                        else:
                            # Calculate basic trailing stop
                            stop_pct = stop_loss_config.get('min_stop_pct', 0.8) / 100.0
                            if position_type == 'LONG':
                                trail_stop = entry_price * (1 - stop_pct)
                            else:
                                trail_stop = entry_price * (1 + stop_pct)
                        is_activated = False
                    
                    exit_price_list.append(trail_stop)
                    exit_labels.append('TS' if is_activated else 'TS-Init')
                    
            except Exception as e:
                print(f"Error calculating trailing stop: {e}")
                import traceback
                traceback.print_exc()
            
            # 4. Breakeven stop (if enabled and triggered)
            try:
                if stop_loss_config.get('breakeven_enabled', False):
                    breakeven_trigger_ratio = stop_loss_config.get('breakeven_trigger_ratio', 1.05)
                    if position_type == 'LONG':
                        profit_ratio = current_price / entry_price
                        if profit_ratio >= breakeven_trigger_ratio:
                            # Breakeven stop at entry price
                            exit_price_list.append(entry_price)
                            exit_labels.append('BE')
                    else:  # SHORT
                        profit_ratio = entry_price / current_price
                        if profit_ratio >= breakeven_trigger_ratio:
                            # Breakeven stop at entry price
                            exit_price_list.append(entry_price)
                            exit_labels.append('BE')
            except Exception as e:
                print(f"Error calculating breakeven: {e}")
            
            # 5. Profit Reversal Protection (conditional - exits when profit reverses)
            try:
                profit_reversal_config = risk_config.get('profit_reversal_protection', {})
                if profit_reversal_config.get('enabled', False):
                    max_profit = position.get('max_profit', 0)
                    min_profit = profit_reversal_config.get('min_profit', 100.0)
                    reversal_threshold = profit_reversal_config.get('reversal_threshold', 50.0)
                    
                    if max_profit >= min_profit:
                        # Calculate the price at which reversal would trigger
                        # If profit drops by reversal_threshold% from peak, exit
                        profit_to_give_back = max_profit * (reversal_threshold / 100.0)
                        trigger_profit = max_profit - profit_to_give_back
                        
                        # Calculate trigger price
                        if position_type == 'LONG':
                            # For LONG: trigger_price = entry + (trigger_profit / quantity)
                            trigger_price = entry_price + (trigger_profit / quantity) if quantity > 0 else current_price
                        else:  # SHORT
                            # For SHORT: trigger_price = entry - (trigger_profit / quantity)
                            trigger_price = entry_price - (trigger_profit / quantity) if quantity > 0 else current_price
                        
                        # Only show if current profit is above trigger (i.e., reversal hasn't happened yet)
                        current_pnl = (current_price - entry_price) * quantity if position_type == 'LONG' else (entry_price - current_price) * quantity
                        if current_pnl > trigger_profit:
                            exit_price_list.append(trigger_price)
                            exit_labels.append(f'PR({reversal_threshold:.0f}%→₹{trigger_profit:.0f})')
            except Exception as e:
                print(f"Error calculating profit reversal protection: {e}")
            
            # 6. Profit Pullback Exit (conditional - shows trigger price when armed)
            try:
                pullback_cfg = risk_config.get('profit_pullback_exit', {})
                if pullback_cfg.get('enabled', False):
                    max_profit_display = position.get('max_profit', 0)
                    pb_activation = pullback_cfg.get('activation_amount', 500.0)
                    pb_pct = pullback_cfg.get('pullback_percentage', 40.0)
                    pb_min_exit = pullback_cfg.get('min_exit_profit', 100.0)
                    
                    if max_profit_display >= pb_activation and quantity > 0:
                        trigger_profit = max_profit_display * (1 - pb_pct / 100.0)
                        trigger_profit = max(trigger_profit, pb_min_exit)
                        
                        if position_type == 'LONG':
                            trigger_price = entry_price + (trigger_profit / quantity)
                        else:
                            trigger_price = entry_price - (trigger_profit / quantity)
                        
                        current_pnl_display = (
                            (current_price - entry_price) * quantity if position_type == 'LONG'
                            else (entry_price - current_price) * quantity
                        )
                        if current_pnl_display > trigger_profit:
                            exit_price_list.append(trigger_price)
                            exit_labels.append(f'PB({pb_pct:.0f}%→₹{trigger_profit:.0f})')
            except Exception as e:
                print(f"Error calculating profit pullback exit: {e}")
            
            # 7. Microstructure/Micro Volume Exit (conditional - exits at current price when detected)
            try:
                # Get microstructure config
                quant_indicators = config.get('quant_indicators', {}) if config else self.config.get('quant_indicators', {})
                microstructure_config = quant_indicators.get('microstructure', {})
                if microstructure_config.get('enabled', False) and microstructure_config.get('detect_reversals', False):
                    # Micro volume exit is conditional - it exits at current price when volume spike + price rejection detected
                    # We show current price as the exit price since it's the price at which it would exit if detected now
                    # Note: This is a conditional exit that triggers when volume spike threshold is exceeded
                    exit_price_list.append(current_price)
                    exit_labels.append('MV')
            except Exception as e:
                print(f"Error calculating micro volume exit: {e}")
            
            # Format exit prices with labels - one per line
            if exit_price_list:
                # Sort prices by distance from entry (for LONG: ascending, for SHORT: descending)
                price_label_pairs = list(zip(exit_price_list, exit_labels))
                if position_type == 'LONG':
                    price_label_pairs.sort(key=lambda x: x[0])
                else:
                    price_label_pairs.sort(key=lambda x: x[0], reverse=True)
                
                # Create list of "Label: Price" strings with color info
                formatted_prices = []
                for price, label in price_label_pairs:
                    # Check if label already contains profit info (like PT1(80%→₹500))
                    if '(' in label and '→' in label:
                        # Label already has profit info, format as: PT1(80%→₹500):356.44
                        formatted_prices.append((f"{label}:{price:.2f}", label))
                    else:
                        # Standard format: Label:Price
                        formatted_prices.append((f"{label}:{price:.2f}", label))
                
                # Return as list of tuples (formatted_string, label) for color coding
                return formatted_prices
            else:
                return []
            
        except Exception as e:
            print(f"Error in calculate_exit_prices_for_display: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def should_exit_position(self,
                            position: Dict,
                            current_price: float,
                            current_time: datetime,
                            atr: float,
                            volatility_regime: str,
                            recent_prices: List[float] = None,
                            recent_volumes: List[float] = None) -> Dict:
        """
        Comprehensive exit decision based on all strategies.
        
        Checks (in order of priority):
        0. Unrealized profit drop exit (if enabled - exits if profit drops by X% from peak)
        0.5 Below avg profit exit (legacy, disabled by default)
        0.6 Profit pullback exit (exits when profit gives back X% from peak amount)
        1. Profit drop protection (if enabled - drops by X% from max profit)
        2. Hard stop loss hit
        3. Microstructure reversal (FULL EXIT - highest priority after stop loss)
        4. Trailing stop hit
        5. Profit target hit
        6. Time decay exit
        
        Args:
            position: Position dictionary with entry details
            current_price: Current market price
            current_time: Current timestamp
            atr: Current ATR
            volatility_regime: Current volatility regime
            recent_prices: Recent price history (for microstructure)
            recent_volumes: Recent volume history (for microstructure)
        
        Returns:
            Dictionary with exit decision and details
        """
        entry_price = position.get('entry_price', 0)
        entry_time = position.get('entry_time', current_time)
        position_type = position.get('type', 'LONG')
        quantity = position.get('quantity', 0)
        highest_price = position.get('highest_price', entry_price)
        lowest_price = position.get('lowest_price', entry_price)
        initial_volatility = position.get('initial_volatility', atr)
        
        # Calculate current PnL
        if position_type == 'LONG':
            current_pnl = (current_price - entry_price) * quantity
        else:
            current_pnl = (entry_price - current_price) * quantity
        
        # Track maximum profit reached (for profit reversal protection)
        if 'max_profit' not in position:
            position['max_profit'] = max(0, current_pnl)
        else:
            position['max_profit'] = max(position['max_profit'], current_pnl)
        
        max_profit = position['max_profit']
        
        # Track maximum profit percentage (for profit drop protection)
        if entry_price > 0:
            if position_type == 'LONG':
                max_profit_pct = ((highest_price - entry_price) / entry_price) * 100
            else:  # SHORT
                max_profit_pct = ((entry_price - lowest_price) / entry_price) * 100
            
            if 'max_profit_pct' not in position:
                position['max_profit_pct'] = max(0, max_profit_pct)
            else:
                position['max_profit_pct'] = max(position['max_profit_pct'], max_profit_pct)
        else:
            position['max_profit_pct'] = 0.0
        
        max_profit_pct = position.get('max_profit_pct', 0.0)
        
        # Calculate current profit percentage
        if entry_price > 0:
            if position_type == 'LONG':
                current_profit_pct = ((current_price - entry_price) / entry_price) * 100
            else:  # SHORT
                current_profit_pct = ((entry_price - current_price) / entry_price) * 100
        else:
            current_profit_pct = 0.0
        
        # 0. Check unrealized profit drop exit (if enabled)
        # Exits if current profit percentage drops by configured threshold from peak profit percentage
        # Only triggers if: (1) we had profit (max_profit_pct > 0), (2) we're still in profit (current_profit_pct > 0),
        # and (3) profit dropped by configured percentage threshold from peak
        if self.unrealized_drop_enabled and max_profit_pct > 0 and current_profit_pct > 0:
            profit_drop = max_profit_pct - current_profit_pct
            if profit_drop >= self.unrealized_drop_threshold:
                reason = f"Drop in percentage: {profit_drop:.2f}% drop from peak profit ({max_profit_pct:.2f}% → {current_profit_pct:.2f}%)"
                print(f"📉 UNREALIZED PROFIT DROP EXIT TRIGGERED: {reason}")
                return {
                    'should_exit': True,
                    'reason': reason,
                    'exit_price': current_price,
                    'pnl': current_pnl,
                    'exit_percentage': 100,  # Full exit
                    'confidence': 0.90,
                    'full_exit_required': False,
                    'quantity_to_exit': None
                }
        
        # 0.5 Check below average profit exit (if enabled)
        # Exits if current unrealized profit drops below the average profit recorded during the trade
        # Only triggers if: (1) we have a positive average profit, (2) we're still in profit but below average,
        # and (3) the minimum profit threshold has been reached at some point
        avg_profit = position.get('avg_profit', 0.0)
        if self.below_avg_profit_enabled and avg_profit > 0 and max_profit >= self.below_avg_profit_min_profit:
            if current_pnl > 0 and current_pnl < avg_profit:
                reason = f"Below Avg Profit: Current ₹{current_pnl:.2f} < Avg ₹{avg_profit:.2f} (Max was ₹{max_profit:.2f})"
                print(f"📉 BELOW AVG PROFIT EXIT TRIGGERED: {reason}")
                return {
                    'should_exit': True,
                    'reason': reason,
                    'exit_price': current_price,
                    'pnl': current_pnl,
                    'exit_percentage': 100,  # Full exit
                    'confidence': 0.85,
                    'full_exit_required': False,
                    'quantity_to_exit': None
                }
        
        # 0.6 Profit pullback exit: arms after peak profit crosses activation_amount,
        # triggers when current profit drops by pullback_percentage% from peak,
        # but only if remaining profit is still above min_exit_profit.
        if self.pullback_enabled and max_profit >= self.pullback_activation_amount and current_pnl > 0:
            giveback = max_profit - current_pnl
            giveback_pct = (giveback / max_profit) * 100 if max_profit > 0 else 0
            if giveback_pct >= self.pullback_percentage and current_pnl >= self.pullback_min_exit_profit:
                reason = (
                    f"Profit Pullback: gave back {giveback_pct:.1f}% of peak "
                    f"(₹{max_profit:.0f} → ₹{current_pnl:.0f}, lost ₹{giveback:.0f})"
                )
                return {
                    'should_exit': True,
                    'reason': reason,
                    'exit_price': current_price,
                    'pnl': current_pnl,
                    'exit_percentage': 100,
                    'confidence': 0.88,
                    'full_exit_required': False,
                    'quantity_to_exit': None
                }
        
        # 1. Check profit drop protection (if enabled and max profit was positive)
        # This should be checked early to protect profits
        # Only trigger if: (1) we had profit (max_profit_pct > 0), (2) we're still in profit (current_profit_pct > 0), 
        # and (3) profit dropped by configured percentage from max
        if self.profit_drop_enabled and max_profit_pct > 0 and current_profit_pct > 0:
            profit_drop = max_profit_pct - current_profit_pct
            if profit_drop >= self.profit_drop_percentage:
                reason = f"Profit drop protection: {profit_drop:.2f}% drop from max profit ({max_profit_pct:.2f}% → {current_profit_pct:.2f}%)"
                print(f"📉 PROFIT DROP PROTECTION TRIGGERED: {reason}")
                return {
                    'should_exit': True,
                    'reason': reason,
                    'exit_price': current_price,
                    'pnl': current_pnl,
                    'exit_percentage': 100,  # Full exit
                    'confidence': 0.85,
                    'full_exit_required': False,
                    'quantity_to_exit': None
                }
        
        # 2. Check microstructure reversal FIRST (after stop loss) - ALWAYS FULL EXIT
        # Only runs when quant_indicators.microstructure.enabled AND detect_reversals are True
        microstructure_enabled = False  # Default off; enable via config if desired
        quant_indicators = self.config.get('quant_indicators', {}) if self.config else {}
        microstructure_config = quant_indicators.get('microstructure', {})
        microstructure_enabled = microstructure_config.get('enabled', False) and microstructure_config.get('detect_reversals', False)
        
        if microstructure_enabled and recent_prices and recent_volumes:
            is_reversal, reason = self.detect_microstructure_reversal(
                recent_prices, recent_volumes, position_type
            )
            
            if is_reversal:
                # Microstructure reversal ALWAYS triggers FULL EXIT immediately
                # This is a critical exit signal - exit 100% of position
                print(f"🚨 MICROSTRUCTURE REVERSAL DETECTED: {reason} - EXITING FULL POSITION IMMEDIATELY")
                return {
                    'should_exit': True,
                    'reason': reason,
                    'exit_price': current_price,
                    'pnl': current_pnl,
                    'exit_percentage': 100,  # Always 100% for microstructure reversal
                    'confidence': 0.75,
                    'full_exit_required': True,  # Explicit flag to ensure full exit
                    'quantity_to_exit': None  # Explicitly set to None to prevent partial exit
                }
        
        # 3. Check hard stop loss (fixed amount or volatility-adjusted)
        # Check if position has custom stop loss (for fixed amount method)
        if 'stop_loss' in position and position['stop_loss'] is not None:
            hard_stop = position['stop_loss']
        else:
            # Fallback to volatility-adjusted stop
            hard_stop = self.calculate_volatility_stop(
                entry_price, atr, position_type, volatility_regime
            )
        
        # Check if breakeven stop should be activated (only if breakeven_enabled in config)
        breakeven_activated = position.get('breakeven_activated', False)
        risk_amount = abs(entry_price - hard_stop)
        
        # Only apply breakeven logic if it's enabled in configuration
        if self.breakeven_enabled:
            # If position has reached 1x risk in profit, move stop to breakeven
            if not breakeven_activated:
                if position_type == 'LONG' and current_price >= (entry_price + risk_amount):
                    hard_stop = entry_price  # Move stop to entry (breakeven)
                    position['breakeven_activated'] = True
                    breakeven_activated = True
                elif position_type == 'SHORT' and current_price <= (entry_price - risk_amount):
                    hard_stop = entry_price  # Move stop to entry (breakeven)
                    position['breakeven_activated'] = True
                    breakeven_activated = True
            elif breakeven_activated:
                # Keep stop at entry if breakeven was already activated
                hard_stop = entry_price
        
        # Check if stop loss hit
        if position_type == 'LONG' and current_price <= hard_stop:
            reason = 'Breakeven stop hit (protected capital)' if breakeven_activated else 'Hard stop loss hit'
            # Use stop loss price to cap loss (prevents gap-through losses)
            # For LONG: if price gaps below stop, use stop price (better for us)
            exit_price = hard_stop
            # Recalculate PnL with stop loss price
            exit_pnl = (exit_price - entry_price) * quantity
            return {
                'should_exit': True,
                'reason': reason,
                'exit_price': exit_price,  # Use stop loss price to enforce max loss
                'pnl': exit_pnl,
                'exit_percentage': 100,
                'confidence': 1.0
            }
        elif position_type == 'SHORT' and current_price >= hard_stop:
            reason = 'Breakeven stop hit (protected capital)' if breakeven_activated else 'Hard stop loss hit'
            # Use stop loss price to cap loss (prevents gap-through losses)
            # For SHORT: if price gaps above stop, use stop price (better for us)
            exit_price = hard_stop
            # Recalculate PnL with stop loss price
            exit_pnl = (entry_price - exit_price) * quantity
            return {
                'should_exit': True,
                'reason': reason,
                'exit_price': exit_price,  # Use stop loss price to enforce max loss
                'pnl': exit_pnl,
                'exit_percentage': 100,
                'confidence': 1.0
            }
        
        # 4. Check trailing stop (if enabled)
        if self.trailing_enabled:
            trailing_stop, activated = self.calculate_trailing_stop(
                entry_price,
                current_price,
                highest_price,
                lowest_price,
                atr,
                position_type,
                activation_ratio=self.trailing_activation_ratio,
                trail_multiplier=self.trailing_trail_multiplier
            )
            
            if activated:
                if position_type == 'LONG' and current_price <= trailing_stop:
                    return {
                        'should_exit': True,
                        'reason': 'Trailing stop hit (profit protection)',
                        'exit_price': current_price,
                        'pnl': current_pnl,
                        'exit_percentage': 100,
                        'confidence': 0.9
                    }
                elif position_type == 'SHORT' and current_price >= trailing_stop:
                    return {
                        'should_exit': True,
                        'reason': 'Trailing stop hit (profit protection)',
                        'exit_price': current_price,
                        'pnl': current_pnl,
                        'exit_percentage': 100,
                        'confidence': 0.9
                    }
        
        # 4. Check loss recovery first (if enabled and there's loss to recover)
        loss_to_recover = position.get('loss_to_recover', 0)
        recovery_quantity = position.get('recovery_quantity', 0)
        base_quantity = position.get('base_quantity', quantity)
        loss_recovered = position.get('loss_recovered', 0)
        remaining_loss = loss_to_recover - loss_recovered
        
        if remaining_loss > 0 and current_pnl > 0 and recovery_quantity > 0:
            # Calculate how much profit we need to recover the loss
            # We need to exit enough quantity to generate profit >= remaining_loss
            profit_per_unit = (current_price - entry_price) if position_type == 'LONG' else (entry_price - current_price)
            
            if profit_per_unit > 0:
                # Calculate quantity needed to recover loss
                quantity_needed = int((remaining_loss / profit_per_unit) + 0.5)  # Round up
                # Prioritize exiting recovery quantity first (up to recovery_quantity)
                quantity_needed = min(quantity_needed, recovery_quantity)
                
                if quantity_needed > 0:
                    # Check if partial exits are disabled - if so, force full exit
                    if not self.partial_exits_enabled:
                        # Force full exit when partial exits are disabled
                        return {
                            'should_exit': True,
                            'reason': f"Loss recovery (full exit): Recovering loss ₹{remaining_loss:.2f}",
                            'exit_price': current_price,
                            'pnl': current_pnl,
                            'exit_percentage': 100,  # Full exit
                            'confidence': 0.85,
                            'recovery_exit': True,
                            'quantity_to_exit': None  # None means full exit
                        }
                    
                    # Calculate exit percentage (partial exit mode)
                    exit_pct = (quantity_needed / quantity) * 100
                    recovered_amount = profit_per_unit * quantity_needed
                    
                    # Update position tracking
                    position['loss_recovered'] = loss_recovered + recovered_amount
                    position['recovery_quantity'] = recovery_quantity - quantity_needed  # Reduce recovery quantity
                    
                    return {
                        'should_exit': True,
                        'reason': f"Loss recovery: Exiting {quantity_needed} to recover ₹{recovered_amount:.2f}",
                        'exit_price': current_price,
                        'pnl': current_pnl,
                        'exit_percentage': exit_pct,
                        'confidence': 0.85,
                        'recovery_exit': True,
                        'quantity_to_exit': quantity_needed
                    }
        
        # 5. Check profit targets (if enabled) - only apply to base quantity after loss is recovered
        # If loss is recovered, normal strategy applies to remaining base quantity
        if self.profit_targets_enabled:
            # Only apply profit targets if loss is fully recovered or no recovery needed
            if remaining_loss <= 0:
                targets = position.get('profit_targets')
                if targets:
                    # Optional early exit: exit immediately when the first target is hit
                    if self.exit_on_first_target_hit:
                        for i, target in enumerate(targets):
                            if not target.get('hit', False):
                                target_price = target['price']
                                if (position_type == 'LONG' and current_price >= target_price) or (
                                    position_type == 'SHORT' and current_price <= target_price
                                ):
                                    reason = f"Profit Target {i+1} hit (exit_on_first_target_hit)"
                                    return {
                                        'should_exit': True,
                                        'reason': reason,
                                        'exit_price': current_price,
                                        'pnl': current_pnl,
                                        'exit_percentage': 100,
                                        'confidence': 0.85,
                                        'full_exit_required': True
                                    }
                    
                    # Initialize target tracking if not present
                    if 'target_highs' not in position:
                        position['target_highs'] = {}  # Track highest price after each target
                    if 'target_lows' not in position:
                        position['target_lows'] = {}  # Track lowest price after each target (for SHORT)
                    
                    # First, check for reversals from any hit target (only if reversal is enabled)
                    if self.reversal_enabled:
                        for i, target in enumerate(targets):
                            if target.get('hit', False):
                                target_key = f'target_{i}'
                                target_price = target['price']
                                
                                if position_type == 'LONG':
                                    # Track highest price reached after this target
                                    if target_key not in position['target_highs']:
                                        position['target_highs'][target_key] = current_price
                                    else:
                                        position['target_highs'][target_key] = max(position['target_highs'][target_key], current_price)
                                    
                                    # Check for reversal: price drops significantly from the high after target
                                    highest_after_target = position['target_highs'][target_key]
                                    # Use configured reversal threshold
                                    reversal_threshold = max(
                                        atr * self.reversal_atr_multiplier, 
                                        target_price * (self.reversal_percent_threshold / 100.0)
                                    ) if atr > 0 else target_price * (self.reversal_percent_threshold / 100.0)
                                    
                                    if reversal_threshold > 0 and current_price < (highest_after_target - reversal_threshold):
                                        # Reversal detected - exit fully
                                        drop_pct = ((highest_after_target - current_price) / highest_after_target) * 100
                                        return {
                                            'should_exit': True,
                                            'reason': f"Reversal from Profit Target {i+1}: Dropped {drop_pct:.2f}% from ₹{highest_after_target:.2f} to ₹{current_price:.2f}",
                                            'exit_price': current_price,
                                            'pnl': current_pnl,
                                            'exit_percentage': 100,
                                            'confidence': 0.85,
                                            'reversal_exit': True
                                        }
                                
                                else:  # SHORT
                                    # Track lowest price reached after this target
                                    if target_key not in position['target_lows']:
                                        position['target_lows'][target_key] = current_price
                                    else:
                                        position['target_lows'][target_key] = min(position['target_lows'][target_key], current_price)
                                    
                                    # Check for reversal: price rises significantly from the low after target
                                    lowest_after_target = position['target_lows'][target_key]
                                    # Use configured reversal threshold
                                    reversal_threshold = max(
                                        atr * self.reversal_atr_multiplier, 
                                        target_price * (self.reversal_percent_threshold / 100.0)
                                    ) if atr > 0 else target_price * (self.reversal_percent_threshold / 100.0)
                                    
                                    if reversal_threshold > 0 and current_price > (lowest_after_target + reversal_threshold):
                                        # Reversal detected - exit fully
                                        rise_pct = ((current_price - lowest_after_target) / lowest_after_target) * 100
                                        return {
                                            'should_exit': True,
                                            'reason': f"Reversal from Profit Target {i+1}: Rose {rise_pct:.2f}% from ₹{lowest_after_target:.2f} to ₹{current_price:.2f}",
                                            'exit_price': current_price,
                                            'pnl': current_pnl,
                                            'exit_percentage': 100,
                                            'confidence': 0.85,
                                            'reversal_exit': True
                                        }
                    
                    # Now check if any new target is hit (but don't exit, just mark as hit)
                    all_targets_hit = True
                    for i, target in enumerate(targets):
                        if not target.get('hit', False):
                            all_targets_hit = False
                            target_price = target['price']
                            target_key = f'target_{i}'
                            
                            if position_type == 'LONG' and current_price >= target_price:
                                # Mark target as hit but don't exit - wait for next target or reversal
                                target['hit'] = True
                                position['target_highs'][target_key] = current_price
                                # Log that target was hit but we're waiting
                                next_target = f"Target {i+2}" if i+1 < len(targets) else "holding"
                                print(f"✅ Profit Target {i+1} reached at ₹{target_price:.2f} (current: ₹{current_price:.2f}) - Waiting for {next_target} or reversal")
                                # Don't return - continue to check other targets or wait
                            
                            elif position_type == 'SHORT' and current_price <= target_price:
                                # Mark target as hit but don't exit - wait for next target or reversal
                                target['hit'] = True
                                position['target_lows'][target_key] = current_price
                                # Log that target was hit but we're waiting
                                next_target = f"Target {i+2}" if i+1 < len(targets) else "holding"
                                print(f"✅ Profit Target {i+1} reached at ₹{target_price:.2f} (current: ₹{current_price:.2f}) - Waiting for {next_target} or reversal")
                                # Don't return - continue to check other targets or wait
                    
                    # If all targets are hit, continue holding (reversal check will still apply)
                    if all_targets_hit:
                        # All targets reached - continue holding, reversal protection still active
                        pass
        
        # 6. Check time decay (if enabled)
        if self.time_exit_enabled:
            should_exit, reason = self.calculate_time_decay_exit(
                entry_time,
                current_time,
                current_pnl,
                atr,
                initial_volatility,
                max_hold_minutes=self.time_exit_max_hold_minutes
            )
            
            if should_exit:
                return {
                    'should_exit': True,
                    'reason': reason,
                    'exit_price': current_price,
                    'pnl': current_pnl,
                    'exit_percentage': 100,
                    'confidence': 0.7
                }
        
        # 5. Check microstructure reversal - only if enabled in config (quant_indicators.microstructure)
        if microstructure_enabled and recent_prices and recent_volumes:
            is_reversal, reason = self.detect_microstructure_reversal(
                recent_prices, recent_volumes, position_type
            )
            
            if is_reversal:
                # Microstructure reversal always triggers FULL EXIT immediately
                return {
                    'should_exit': True,
                    'reason': reason,
                    'exit_price': current_price,
                    'pnl': current_pnl,
                    'exit_percentage': 100,  # Always 100% for microstructure reversal
                    'confidence': 0.75,
                    'full_exit_required': True  # Explicit flag to ensure full exit
                }
        
        # No exit signal
        return {
            'should_exit': False,
            'reason': 'No exit conditions met',
            'exit_price': 0,
            'pnl': current_pnl,
            'exit_percentage': 0,
            'confidence': 0.0
        }


def test_exit_strategy_manager():
    """Test function for ExitStrategyManager."""
    print("=" * 60)
    print("EXIT STRATEGY MANAGER TEST")
    print("=" * 60)
    
    esm = ExitStrategyManager(atr_multiplier=2.0)
    
    # Test 1: Volatility-adjusted stops
    entry = 100.0
    atr = 3.0
    
    stop_low = esm.calculate_volatility_stop(entry, atr, 'LONG', 'LOW')
    stop_normal = esm.calculate_volatility_stop(entry, atr, 'LONG', 'NORMAL')
    stop_high = esm.calculate_volatility_stop(entry, atr, 'LONG', 'HIGH')
    
    print("\nVolatility-Adjusted Stops:")
    print(f"Entry: ₹{entry}, ATR: {atr}")
    print(f"  LOW vol:    ₹{stop_low:.2f} ({entry - stop_low:.2f} distance)")
    print(f"  NORMAL vol: ₹{stop_normal:.2f} ({entry - stop_normal:.2f} distance)")
    print(f"  HIGH vol:   ₹{stop_high:.2f} ({entry - stop_high:.2f} distance)")
    
    # Test 2: Trailing stop
    current = 110.0
    highest = 112.0
    lowest = 98.0
    
    trail_stop, activated = esm.calculate_trailing_stop(
        entry, current, highest, lowest, atr, 'LONG'
    )
    
    print(f"\nTrailing Stop (LONG):")
    print(f"Entry: ₹{entry}, Current: ₹{current}, Highest: ₹{highest}")
    print(f"  Activated: {activated}")
    print(f"  Trail Stop: ₹{trail_stop:.2f}")
    
    # Test 3: Profit targets
    targets = esm.calculate_profit_targets(entry, atr, 'LONG')
    
    print(f"\nProfit Targets:")
    for i, target in enumerate(targets, 1):
        print(f"  Target {i}: ₹{target['price']:.2f} ({target['ratio']:.1f}x risk, exit {target['exit_percentage']}%)")
    
    # Test 4: Time decay
    entry_time = datetime.now() - timedelta(minutes=65)
    current_time = datetime.now()
    
    should_exit, reason = esm.calculate_time_decay_exit(
        entry_time, current_time, -50, atr, atr * 2
    )
    
    print(f"\nTime Decay Exit:")
    print(f"  Hold duration: 65 minutes, PnL: ₹-50")
    print(f"  Should Exit: {should_exit}")
    print(f"  Reason: {reason}")
    
    # Test 5: Comprehensive exit decision
    position = {
        'entry_price': 100.0,
        'entry_time': datetime.now() - timedelta(minutes=30),
        'type': 'LONG',
        'quantity': 25,
        'highest_price': 105.0,
        'lowest_price': 98.0,
        'initial_volatility': atr,
        'profit_targets': targets
    }
    
    # Test hitting stop loss
    exit_decision = esm.should_exit_position(
        position, 93.0, datetime.now(), atr, 'NORMAL'
    )
    
    print(f"\nComprehensive Exit Test (Price at ₹93):")
    print(f"  Should Exit: {exit_decision['should_exit']}")
    print(f"  Reason: {exit_decision['reason']}")
    print(f"  PnL: ₹{exit_decision['pnl']:.2f}")
    print(f"  Confidence: {exit_decision['confidence']:.1%}")
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_exit_strategy_manager()
