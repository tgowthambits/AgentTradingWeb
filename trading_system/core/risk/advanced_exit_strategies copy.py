"""
Advanced Exit Strategies Module

Implements sophisticated exit strategies using:
1. Statistical Methods: Mean reversion exits, momentum exhaustion, profit trend analysis
2. Arbitrage Methods: Spread convergence, arbitrage opportunity exits
3. HFT Methods: Order flow reversal, microstructure signals, tick-based exits

Focus: Save capital and book profit as big as possible by monitoring profit trends.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional, List
from datetime import datetime, timedelta
from collections import deque

try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    # Fallback linear regression implementation
    def linregress(x, y):
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] * x[i] for i in range(n))
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) if (n * sum_x2 - sum_x * sum_x) != 0 else 0
        intercept = (sum_y - slope * sum_x) / n
        
        # Calculate R-squared
        y_mean = sum_y / n
        ss_tot = sum((y[i] - y_mean) ** 2 for i in range(n))
        ss_res = sum((y[i] - (slope * x[i] + intercept)) ** 2 for i in range(n))
        r_value = (1 - ss_res / ss_tot) ** 0.5 if ss_tot > 0 else 0
        
        class LinregressResult:
            def __init__(self, slope, intercept, rvalue, pvalue, stderr):
                self.slope = slope
                self.intercept = intercept
                self.rvalue = rvalue
                self.pvalue = pvalue
                self.stderr = stderr
        
        return LinregressResult(slope, intercept, r_value, 0.0, 0.0)
    
    class stats:
        @staticmethod
        def linregress(x, y):
            return linregress(x, y)


class StatisticalExitStrategy:
    """
    Statistical exit strategies based on price patterns and profit trends.
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        stat_config = self.config.get('risk_management', {}).get('statistical_exits', {})
        
        # Mean reversion exit config - OPTIMIZED for profit protection
        self.mean_reversion_enabled = stat_config.get('mean_reversion', {}).get('enabled', True)
        self.mean_reversion_z_threshold = stat_config.get('mean_reversion', {}).get('z_threshold', 2.0)  # Lower threshold
        self.mean_reversion_lookback = stat_config.get('mean_reversion', {}).get('lookback_period', 15)  # Faster detection
        
        # Momentum exhaustion exit config - OPTIMIZED for early detection
        self.momentum_exhaustion_enabled = stat_config.get('momentum_exhaustion', {}).get('enabled', True)
        self.momentum_exhaustion_threshold = stat_config.get('momentum_exhaustion', {}).get('threshold', -0.1)  # More sensitive
        self.momentum_exhaustion_lookback = stat_config.get('momentum_exhaustion', {}).get('lookback_period', 5)  # Faster detection
        
        # Profit trend analysis config - OPTIMIZED for aggressive profit protection
        self.profit_trend_enabled = stat_config.get('profit_trend', {}).get('enabled', True)
        self.profit_trend_min_samples = stat_config.get('profit_trend', {}).get('min_samples', 3)  # Reduced for faster detection
        self.profit_trend_decline_threshold = stat_config.get('profit_trend', {}).get('decline_threshold', 0.1)  # More sensitive
        self.profit_trend_acceleration_threshold = stat_config.get('profit_trend', {}).get('acceleration_threshold', -0.1)  # More sensitive
        self.profit_trend_peak_drop_pct = stat_config.get('profit_trend', {}).get('peak_drop_pct', 5.0)  # Exit if profit drops 5% from peak
        
        # Statistical profit target config - OPTIMIZED for earlier profit booking
        self.stat_profit_target_enabled = stat_config.get('stat_profit_target', {}).get('enabled', True)
        self.stat_profit_target_std_multiplier = stat_config.get('stat_profit_target', {}).get('std_multiplier', 1.5)  # Lower threshold
        self.stat_profit_target_min_profit = stat_config.get('stat_profit_target', {}).get('min_profit', 30.0)  # Lower minimum
    
    def check_mean_reversion_exit(self, 
                                   position: Dict,
                                   current_price: float,
                                   price_history: List[float],
                                   position_type: str) -> Optional[Dict]:
        """
        Exit when price deviates significantly from mean (mean reversion signal).
        
        For LONG: Exit when price is significantly above mean (overbought)
        For SHORT: Exit when price is significantly below mean (oversold)
        """
        if not self.mean_reversion_enabled or len(price_history) < self.mean_reversion_lookback:
            return None
        
        recent_prices = price_history[-self.mean_reversion_lookback:]
        mean_price = np.mean(recent_prices)
        std_price = np.std(recent_prices)
        
        if std_price == 0:
            return None
        
        z_score = (current_price - mean_price) / std_price
        
        entry_price = position.get('entry_price', current_price)
        current_pnl = (current_price - entry_price) * position.get('quantity', 0) if position_type == 'LONG' else (entry_price - current_price) * position.get('quantity', 0)
        
        # Only exit if we're in profit and mean reversion signal is strong
        if current_pnl > 0:
            if position_type == 'LONG' and z_score >= self.mean_reversion_z_threshold:
                reason = f"Mean reversion exit (LONG): Price {z_score:.2f}σ above mean (overbought)"
                return {
                    'should_exit': True,
                    'reason': reason,
                    'exit_price': current_price,
                    'confidence': min(0.85, 0.6 + abs(z_score) / 10),
                    'exit_percentage': 100
                }
            elif position_type == 'SHORT' and z_score <= -self.mean_reversion_z_threshold:
                reason = f"Mean reversion exit (SHORT): Price {abs(z_score):.2f}σ below mean (oversold)"
                return {
                    'should_exit': True,
                    'reason': reason,
                    'exit_price': current_price,
                    'confidence': min(0.85, 0.6 + abs(z_score) / 10),
                    'exit_percentage': 100
                }
        
        return None
    
    def check_momentum_exhaustion_exit(self,
                                       position: Dict,
                                       current_price: float,
                                       price_history: List[float],
                                       position_type: str) -> Optional[Dict]:
        """
        Exit when momentum shows signs of exhaustion (negative acceleration).
        """
        if not self.momentum_exhaustion_enabled or len(price_history) < self.momentum_exhaustion_lookback + 2:
            return None
        
        recent_prices = price_history[-self.momentum_exhaustion_lookback:]
        
        # Calculate rate of change (momentum)
        if len(recent_prices) < 2:
            return None
        
        roc = [(recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1] for i in range(1, len(recent_prices))]
        
        if len(roc) < 2:
            return None
        
        # Calculate momentum acceleration (change in ROC)
        momentum_acceleration = roc[-1] - roc[-2]
        
        entry_price = position.get('entry_price', current_price)
        current_pnl = (current_price - entry_price) * position.get('quantity', 0) if position_type == 'LONG' else (entry_price - current_price) * position.get('quantity', 0)
        
        # Exit if momentum is decelerating significantly and we're in profit
        if current_pnl > 0 and momentum_acceleration <= self.momentum_exhaustion_threshold:
            reason = f"Momentum exhaustion: Acceleration {momentum_acceleration:.4f} (decelerating)"
            return {
                'should_exit': True,
                'reason': reason,
                'exit_price': current_price,
                'confidence': 0.75,
                'exit_percentage': 100
            }
        
        return None
    
    def check_profit_trend_exit(self,
                                position: Dict,
                                current_price: float,
                                position_type: str) -> Optional[Dict]:
        """
        Monitor profit trend and exit when trend shows significant decline or negative acceleration.
        OPTIMIZED: More aggressive profit protection with early exit signals.
        """
        if not self.profit_trend_enabled:
            return None
        
        entry_price = position.get('entry_price', current_price)
        quantity = position.get('quantity', 0)
        
        # Calculate current profit
        if position_type == 'LONG':
            current_pnl = (current_price - entry_price) * quantity
        else:
            current_pnl = (entry_price - current_price) * quantity
        
        # Get profit history from position
        profit_history = position.get('profit_history', [])
        
        # Track max profit reached
        max_profit = position.get('max_profit', current_pnl)
        if current_pnl > max_profit:
            max_profit = current_pnl
            position['max_profit'] = max_profit
        
        # Add current profit to history
        profit_history.append(current_pnl)
        position['profit_history'] = profit_history[-30:]  # Keep last 30 samples for better analysis
        
        # EARLY EXIT: If profit drops significantly from peak, exit immediately
        if current_pnl > 0 and max_profit > 0:
            profit_drop_pct = ((max_profit - current_pnl) / max_profit) * 100 if max_profit > 0 else 0
            if profit_drop_pct >= self.profit_trend_peak_drop_pct:
                reason = f"Profit drop from peak: {profit_drop_pct:.2f}% (Peak: ₹{max_profit:.2f} → Current: ₹{current_pnl:.2f})"
                return {
                    'should_exit': True,
                    'reason': reason,
                    'exit_price': current_price,
                    'confidence': 0.95,  # High confidence for peak drop
                    'exit_percentage': 100
                }
        
        if len(profit_history) < self.profit_trend_min_samples:
            return None
        
        recent_profits = profit_history[-self.profit_trend_min_samples:]
        
        # Calculate profit trend using linear regression
        x = np.arange(len(recent_profits))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, recent_profits)
        
        # Calculate profit acceleration (second derivative)
        if len(recent_profits) >= 3:
            first_diff = np.diff(recent_profits)
            acceleration = np.diff(first_diff)[-1] if len(first_diff) > 1 else 0
        else:
            acceleration = 0
        
        # Calculate profit velocity (first derivative - rate of change)
        if len(recent_profits) >= 2:
            velocity = recent_profits[-1] - recent_profits[-2]
        else:
            velocity = 0
        
        # Exit conditions (OPTIMIZED for aggressive profit protection):
        # 1. Profit trend is declining (even slightly)
        # 2. Profit acceleration is negative (decelerating)
        # 3. Profit velocity is negative (profit decreasing)
        # 4. Only if we're still in profit
        
        if current_pnl > 0:
            # Check for declining trend (more sensitive threshold)
            if slope < 0 and abs(slope) > self.profit_trend_decline_threshold:
                reason = f"Profit trend decline: Slope {slope:.2f} (trending down)"
                return {
                    'should_exit': True,
                    'reason': reason,
                    'exit_price': current_price,
                    'confidence': min(0.95, 0.75 + abs(slope) / 5),  # Higher confidence
                    'exit_percentage': 100
                }
            
            # Check for negative acceleration (more sensitive)
            if acceleration < self.profit_trend_acceleration_threshold:
                reason = f"Profit acceleration negative: {acceleration:.2f} (decelerating)"
                return {
                    'should_exit': True,
                    'reason': reason,
                    'exit_price': current_price,
                    'confidence': 0.85,  # Higher confidence
                    'exit_percentage': 100
                }
            
            # Check for negative velocity (profit decreasing in last period)
            if velocity < 0 and abs(velocity) > (max_profit * 0.01):  # Drop of 1% of max profit
                reason = f"Profit velocity negative: {velocity:.2f} (profit decreasing)"
                return {
                    'should_exit': True,
                    'reason': reason,
                    'exit_price': current_price,
                    'confidence': 0.80,
                    'exit_percentage': 100
                }
        
        return None
    
    def check_statistical_profit_target(self,
                                         position: Dict,
                                         current_price: float,
                                         price_history: List[float],
                                         position_type: str) -> Optional[Dict]:
        """
        Exit when profit reaches statistical target based on historical price distribution.
        """
        if not self.stat_profit_target_enabled or len(price_history) < 20:
            return None
        
        entry_price = position.get('entry_price', current_price)
        quantity = position.get('quantity', 0)
        
        if position_type == 'LONG':
            current_pnl = (current_price - entry_price) * quantity
            price_move = current_price - entry_price
            price_move_pct = (price_move / entry_price) * 100 if entry_price > 0 else 0
        else:
            current_pnl = (entry_price - current_price) * quantity
            price_move = entry_price - current_price
            price_move_pct = (price_move / entry_price) * 100 if entry_price > 0 else 0
        
        # Only consider if we have minimum profit
        if current_pnl < self.stat_profit_target_min_profit:
            return None
        
        # Calculate historical price move distribution
        recent_prices = price_history[-20:]
        price_changes = [abs(recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1] * 100 
                        for i in range(1, len(recent_prices))]
        
        if len(price_changes) < 10:
            return None
        
        mean_move = np.mean(price_changes)
        std_move = np.std(price_changes)
        
        if std_move == 0:
            return None
        
        # Check if current move exceeds statistical threshold
        z_score = price_move_pct / std_move if std_move > 0 else 0
        
        if z_score >= self.stat_profit_target_std_multiplier:
            reason = f"Statistical profit target: {price_move_pct:.2f}% move ({z_score:.2f}σ above mean)"
            return {
                'should_exit': True,
                'reason': reason,
                'exit_price': current_price,
                'confidence': min(0.90, 0.7 + z_score / 10),
                'exit_percentage': 100
            }
        
        return None


class ArbitrageExitStrategy:
    """
    Arbitrage-based exit strategies for pairs trading and spread convergence.
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        arb_config = self.config.get('risk_management', {}).get('arbitrage_exits', {})
        
        # Spread convergence exit config
        self.spread_convergence_enabled = arb_config.get('spread_convergence', {}).get('enabled', True)
        self.spread_convergence_threshold = arb_config.get('spread_convergence', {}).get('threshold', 0.5)
        self.spread_convergence_lookback = arb_config.get('spread_convergence', {}).get('lookback_period', 30)
        
        # Arbitrage opportunity exit config
        self.arb_opportunity_enabled = arb_config.get('arbitrage_opportunity', {}).get('enabled', True)
        self.arb_opportunity_min_profit = arb_config.get('arbitrage_opportunity', {}).get('min_profit', 100.0)
        self.arb_opportunity_convergence_pct = arb_config.get('arbitrage_opportunity', {}).get('convergence_pct', 80.0)
    
    def check_spread_convergence_exit(self,
                                       position: Dict,
                                       current_price: float,
                                       price_history: List[float],
                                       position_type: str,
                                       pair_symbol: Optional[str] = None,
                                       pair_price_history: Optional[List[float]] = None) -> Optional[Dict]:
        """
        Exit when spread converges (for pairs trading).
        If pair_symbol is provided, uses actual pair spread.
        Otherwise, uses price deviation from mean.
        """
        if not self.spread_convergence_enabled:
            return None
        
        entry_price = position.get('entry_price', current_price)
        quantity = position.get('quantity', 0)
        
        if position_type == 'LONG':
            current_pnl = (current_price - entry_price) * quantity
        else:
            current_pnl = (entry_price - current_price) * quantity
        
        # If we have a pair, calculate actual spread
        if pair_symbol and pair_price_history and len(pair_price_history) >= self.spread_convergence_lookback:
            if len(price_history) < self.spread_convergence_lookback:
                return None
            
            # Calculate spread (price ratio or difference)
            current_spread = current_price / pair_price_history[-1] if pair_price_history[-1] > 0 else 0
            entry_spread = entry_price / pair_price_history[0] if pair_price_history[0] > 0 else 0
            
            if entry_spread == 0:
                return None
            
            # Calculate spread convergence
            spread_change = abs(current_spread - entry_spread) / entry_spread * 100
            
            # Historical spread for mean reversion
            recent_spreads = []
            for i in range(min(len(price_history), len(pair_price_history), self.spread_convergence_lookback)):
                if pair_price_history[-i-1] > 0:
                    recent_spreads.append(price_history[-i-1] / pair_price_history[-i-1])
            
            if len(recent_spreads) >= 10:
                mean_spread = np.mean(recent_spreads)
                std_spread = np.std(recent_spreads)
                
                if std_spread > 0:
                    z_score = abs(current_spread - mean_spread) / std_spread
                    
                    # Exit if spread has converged significantly and we're in profit
                    if current_pnl > 0 and z_score <= self.spread_convergence_threshold:
                        reason = f"Spread convergence: Spread {z_score:.2f}σ from mean (converged)"
                        return {
                            'should_exit': True,
                            'reason': reason,
                            'exit_price': current_price,
                            'confidence': 0.85,
                            'exit_percentage': 100
                        }
        else:
            # Use price deviation from mean as proxy for spread
            if len(price_history) < self.spread_convergence_lookback:
                return None
            
            recent_prices = price_history[-self.spread_convergence_lookback:]
            mean_price = np.mean(recent_prices)
            std_price = np.std(recent_prices)
            
            if std_price == 0:
                return None
            
            z_score = abs(current_price - mean_price) / std_price
            
            # Exit if price has converged to mean and we're in profit
            if current_pnl > 0 and z_score <= self.spread_convergence_threshold:
                reason = f"Price convergence: {z_score:.2f}σ from mean (converged)"
                return {
                    'should_exit': True,
                    'reason': reason,
                    'exit_price': current_price,
                    'confidence': 0.80,
                    'exit_percentage': 100
                }
        
        return None
    
    def check_arbitrage_opportunity_exit(self,
                                          position: Dict,
                                          current_price: float,
                                          position_type: str) -> Optional[Dict]:
        """
        Exit when arbitrage opportunity has been captured (profit target reached).
        """
        if not self.arb_opportunity_enabled:
            return None
        
        entry_price = position.get('entry_price', current_price)
        quantity = position.get('quantity', 0)
        max_profit = position.get('max_profit', 0.0)
        
        if position_type == 'LONG':
            current_pnl = (current_price - entry_price) * quantity
        else:
            current_pnl = (entry_price - current_price) * quantity
        
        # Exit if we've captured significant profit and it's starting to reverse
        if (current_pnl >= self.arb_opportunity_min_profit and 
            max_profit > 0 and 
            current_pnl < max_profit * (self.arb_opportunity_convergence_pct / 100)):
            reason = f"Arbitrage opportunity captured: ₹{current_pnl:.2f} (was ₹{max_profit:.2f})"
            return {
                'should_exit': True,
                'reason': reason,
                'exit_price': current_price,
                'confidence': 0.85,
                'exit_percentage': 100
            }
        
        return None


class HFTExitStrategy:
    """
    High-Frequency Trading exit strategies based on order flow and microstructure.
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        hft_config = self.config.get('risk_management', {}).get('hft_exits', {})
        
        # Order flow reversal exit config - OPTIMIZED for early detection
        self.order_flow_reversal_enabled = hft_config.get('order_flow_reversal', {}).get('enabled', True)
        self.order_flow_reversal_threshold = hft_config.get('order_flow_reversal', {}).get('threshold', -0.3)  # More sensitive
        self.order_flow_reversal_lookback = hft_config.get('order_flow_reversal', {}).get('lookback_period', 5)  # Faster detection
        
        # Microstructure signal exit config - OPTIMIZED for early detection
        self.microstructure_signal_enabled = hft_config.get('microstructure_signal', {}).get('enabled', True)
        self.microstructure_signal_threshold = hft_config.get('microstructure_signal', {}).get('threshold', 0.5)  # More sensitive
        
        # Tick-based exit config - OPTIMIZED for early detection
        self.tick_based_exit_enabled = hft_config.get('tick_based_exit', {}).get('enabled', True)
        self.tick_based_exit_consecutive = hft_config.get('tick_based_exit', {}).get('consecutive_ticks', 2)  # More sensitive
        self.tick_based_exit_min_profit = hft_config.get('tick_based_exit', {}).get('min_profit', 20.0)  # Lower minimum
    
    def check_order_flow_reversal_exit(self,
                                         position: Dict,
                                         current_price: float,
                                         price_history: List[float],
                                         volume_history: Optional[List[float]],
                                         position_type: str) -> Optional[Dict]:
        """
        Exit when order flow shows reversal (buying pressure turns to selling or vice versa).
        """
        if not self.order_flow_reversal_enabled:
            return None
        
        if len(price_history) < self.order_flow_reversal_lookback + 1:
            return None
        
        entry_price = position.get('entry_price', current_price)
        quantity = position.get('quantity', 0)
        
        if position_type == 'LONG':
            current_pnl = (current_price - entry_price) * quantity
        else:
            current_pnl = (entry_price - current_price) * quantity
        
        # Calculate order flow imbalance (OFI)
        # OFI = (buying volume - selling volume) / total volume
        # Approximate using price and volume
        recent_prices = price_history[-self.order_flow_reversal_lookback-1:]
        recent_volumes = volume_history[-self.order_flow_reversal_lookback-1:] if volume_history else None
        
        if recent_volumes is None or len(recent_volumes) < len(recent_prices):
            # Estimate volume from price movements
            recent_volumes = [abs(recent_prices[i] - recent_prices[i-1]) * 1000 
                             for i in range(1, len(recent_prices))]
            recent_volumes.insert(0, recent_volumes[0] if recent_volumes else 1000)
        
        # Calculate OFI
        ofi_values = []
        for i in range(1, len(recent_prices)):
            price_change = recent_prices[i] - recent_prices[i-1]
            volume = recent_volumes[i] if i < len(recent_volumes) else recent_volumes[-1]
            
            if volume > 0:
                # Positive price change = buying pressure, negative = selling pressure
                ofi = price_change / volume * 1000  # Normalize
                ofi_values.append(ofi)
        
        if len(ofi_values) < 3:
            return None
        
        # Check for reversal in order flow
        recent_ofi = ofi_values[-3:]
        ofi_trend = np.mean(recent_ofi[-2:]) - np.mean(recent_ofi[:-1]) if len(recent_ofi) >= 2 else 0
        
        # For LONG: Exit if order flow turns negative (selling pressure)
        # For SHORT: Exit if order flow turns positive (buying pressure)
        if current_pnl > 0:
            if position_type == 'LONG' and ofi_trend <= self.order_flow_reversal_threshold:
                reason = f"Order flow reversal (LONG): OFI trend {ofi_trend:.4f} (selling pressure)"
                return {
                    'should_exit': True,
                    'reason': reason,
                    'exit_price': current_price,
                    'confidence': 0.80,
                    'exit_percentage': 100
                }
            elif position_type == 'SHORT' and ofi_trend >= -self.order_flow_reversal_threshold:
                reason = f"Order flow reversal (SHORT): OFI trend {ofi_trend:.4f} (buying pressure)"
                return {
                    'should_exit': True,
                    'reason': reason,
                    'exit_price': current_price,
                    'confidence': 0.80,
                    'exit_percentage': 100
                }
        
        return None
    
    def check_microstructure_signal_exit(self,
                                          position: Dict,
                                          current_price: float,
                                          price_history: List[float],
                                          volume_history: Optional[List[float]],
                                          position_type: str) -> Optional[Dict]:
        """
        Exit based on microstructure signals (bid-ask imbalance, liquidity, etc.).
        """
        if not self.microstructure_signal_enabled:
            return None
        
        if len(price_history) < 5:
            return None
        
        entry_price = position.get('entry_price', current_price)
        quantity = position.get('quantity', 0)
        
        if position_type == 'LONG':
            current_pnl = (current_price - entry_price) * quantity
        else:
            current_pnl = (entry_price - current_price) * quantity
        
        # Calculate tick direction (price movement direction)
        recent_prices = price_history[-5:]
        tick_directions = [1 if recent_prices[i] > recent_prices[i-1] else -1 
                          for i in range(1, len(recent_prices))]
        
        # Calculate volume-weighted price movement
        recent_volumes = volume_history[-5:] if volume_history else None
        if recent_volumes and len(recent_volumes) == len(tick_directions):
            volume_weighted_signal = sum(tick_directions[i] * recent_volumes[i] 
                                        for i in range(len(tick_directions))) / sum(recent_volumes) if sum(recent_volumes) > 0 else 0
        else:
            volume_weighted_signal = np.mean(tick_directions)
        
        # Calculate price volatility (spread proxy)
        price_volatility = np.std(recent_prices) / np.mean(recent_prices) if np.mean(recent_prices) > 0 else 0
        
        # Microstructure signal: combination of tick direction and volatility
        microstructure_signal = volume_weighted_signal * (1 - price_volatility)
        
        # Exit conditions:
        # For LONG: Exit if microstructure signal turns negative (selling pressure)
        # For SHORT: Exit if microstructure signal turns positive (buying pressure)
        if current_pnl > 0:
            if position_type == 'LONG' and microstructure_signal <= -self.microstructure_signal_threshold:
                reason = f"Microstructure signal (LONG): {microstructure_signal:.4f} (selling pressure)"
                return {
                    'should_exit': True,
                    'reason': reason,
                    'exit_price': current_price,
                    'confidence': 0.75,
                    'exit_percentage': 100
                }
            elif position_type == 'SHORT' and microstructure_signal >= self.microstructure_signal_threshold:
                reason = f"Microstructure signal (SHORT): {microstructure_signal:.4f} (buying pressure)"
                return {
                    'should_exit': True,
                    'reason': reason,
                    'exit_price': current_price,
                    'confidence': 0.75,
                    'exit_percentage': 100
                }
        
        return None
    
    def check_tick_based_exit(self,
                               position: Dict,
                               current_price: float,
                               price_history: List[float],
                               position_type: str) -> Optional[Dict]:
        """
        Exit based on consecutive tick movements against position.
        """
        if not self.tick_based_exit_enabled:
            return None
        
        if len(price_history) < self.tick_based_exit_consecutive + 1:
            return None
        
        entry_price = position.get('entry_price', current_price)
        quantity = position.get('quantity', 0)
        
        if position_type == 'LONG':
            current_pnl = (current_price - entry_price) * quantity
        else:
            current_pnl = (entry_price - current_price) * quantity
        
        # Only exit if we have minimum profit
        if current_pnl < self.tick_based_exit_min_profit:
            return None
        
        # Check for consecutive ticks against position
        recent_prices = price_history[-self.tick_based_exit_consecutive-1:]
        consecutive_against = 0
        
        for i in range(1, len(recent_prices)):
            if position_type == 'LONG':
                # For LONG, count consecutive down ticks
                if recent_prices[i] < recent_prices[i-1]:
                    consecutive_against += 1
                else:
                    consecutive_against = 0
            else:
                # For SHORT, count consecutive up ticks
                if recent_prices[i] > recent_prices[i-1]:
                    consecutive_against += 1
                else:
                    consecutive_against = 0
        
        # Exit if we have consecutive ticks against position
        if consecutive_against >= self.tick_based_exit_consecutive:
            reason = f"Tick-based exit: {consecutive_against} consecutive ticks against position"
            return {
                'should_exit': True,
                'reason': reason,
                'exit_price': current_price,
                'confidence': 0.70,
                'exit_percentage': 100
            }
        
        return None


class AdvancedExitStrategies:
    """
    Main class that coordinates all advanced exit strategies.
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.statistical = StatisticalExitStrategy(config)
        self.arbitrage = ArbitrageExitStrategy(config)
        self.hft = HFTExitStrategy(config)
    
    def check_all_exits(self,
                        position: Dict,
                        current_price: float,
                        current_time: datetime,
                        price_history: List[float],
                        volume_history: Optional[List[float]] = None,
                        position_type: str = 'LONG',
                        pair_symbol: Optional[str] = None,
                        pair_price_history: Optional[List[float]] = None) -> Optional[Dict]:
        """
        Check all advanced exit strategies and return the highest priority exit signal.
        
        OPTIMIZED Priority order (profit protection first):
        1. Profit trend decline (HIGHEST PRIORITY - protects profits)
        2. Statistical profit target (book profits early)
        3. Order flow reversal (early warning)
        4. Momentum exhaustion (early warning)
        5. Mean reversion (overbought/oversold)
        6. Microstructure signal (HFT signal)
        7. Tick-based exit (quick reversal)
        8. Spread convergence (arbitrage)
        """
        exit_signals = []
        
        # PRIORITY 1: Profit trend decline - CHECK FIRST (most important for profit protection)
        profit_trend = self.statistical.check_profit_trend_exit(
            position, current_price, position_type
        )
        if profit_trend:
            # Boost confidence for profit protection
            profit_trend['confidence'] = min(0.98, profit_trend['confidence'] + 0.05)
            exit_signals.append((profit_trend['confidence'], profit_trend))
        
        # IMMEDIATE PROFIT PROTECTION: Exit if profit drops from peak (even small drops)
        entry_price = position.get('entry_price', current_price)
        quantity = position.get('quantity', 0)
        if position_type == 'LONG':
            current_pnl = (current_price - entry_price) * quantity
        else:
            current_pnl = (entry_price - current_price) * quantity
        
        max_profit = position.get('max_profit', current_pnl)
        if current_pnl > 0 and max_profit > current_pnl:
            # If profit dropped from peak, check if we should exit
            profit_drop = max_profit - current_pnl
            profit_drop_pct = (profit_drop / max_profit * 100) if max_profit > 0 else 0
            
            # Exit if profit dropped by 3% or more from peak (aggressive protection)
            if profit_drop_pct >= 3.0:
                reason = f"Immediate profit protection: {profit_drop_pct:.2f}% drop from peak (₹{max_profit:.2f} → ₹{current_pnl:.2f})"
                immediate_exit = {
                    'should_exit': True,
                    'reason': reason,
                    'exit_price': current_price,
                    'confidence': 0.95,
                    'exit_percentage': 100
                }
                exit_signals.append((0.95, immediate_exit))
        
        # PRIORITY 2: Statistical profit target (book profits early)
        stat_profit_target = self.statistical.check_statistical_profit_target(
            position, current_price, price_history, position_type
        )
        if stat_profit_target:
            exit_signals.append((stat_profit_target['confidence'], stat_profit_target))
        
        # PRIORITY 3: Order flow reversal (early warning of trend change)
        order_flow = self.hft.check_order_flow_reversal_exit(
            position, current_price, price_history, volume_history, position_type
        )
        if order_flow:
            exit_signals.append((order_flow['confidence'], order_flow))
        
        # PRIORITY 4: Momentum exhaustion (early warning)
        momentum_exhaustion = self.statistical.check_momentum_exhaustion_exit(
            position, current_price, price_history, position_type
        )
        if momentum_exhaustion:
            exit_signals.append((momentum_exhaustion['confidence'], momentum_exhaustion))
        
        # PRIORITY 5: Mean reversion (overbought/oversold)
        mean_reversion = self.statistical.check_mean_reversion_exit(
            position, current_price, price_history, position_type
        )
        if mean_reversion:
            exit_signals.append((mean_reversion['confidence'], mean_reversion))
        
        # PRIORITY 6: Microstructure signal (HFT signal)
        microstructure = self.hft.check_microstructure_signal_exit(
            position, current_price, price_history, volume_history, position_type
        )
        if microstructure:
            exit_signals.append((microstructure['confidence'], microstructure))
        
        # PRIORITY 7: Tick-based exit (quick reversal)
        tick_based = self.hft.check_tick_based_exit(
            position, current_price, price_history, position_type
        )
        if tick_based:
            exit_signals.append((tick_based['confidence'], tick_based))
        
        # PRIORITY 8: Spread convergence (arbitrage)
        spread_conv = self.arbitrage.check_spread_convergence_exit(
            position, current_price, price_history, position_type, pair_symbol, pair_price_history
        )
        if spread_conv:
            exit_signals.append((spread_conv['confidence'], spread_conv))
        
        # Return highest confidence exit signal
        if exit_signals:
            exit_signals.sort(key=lambda x: x[0], reverse=True)
            return exit_signals[0][1]
        
        return None

