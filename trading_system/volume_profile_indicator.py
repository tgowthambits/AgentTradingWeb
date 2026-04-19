"""
Volume Profile - Density of Density [DAFE] Indicator

Advanced volume profile indicator with delta analysis, entropy metrics,
and Bayesian probability calculations for institutional-level trading signals.

Based on the Pine Script VP-DoD [DAFE] indicator.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, List
from trading_system.core.base_indicator import BaseIndicator


class VolumeProfileIndicator(BaseIndicator):
    """
    Volume Profile - Density of Density [DAFE] Indicator
    
    This indicator provides:
    - Volume Profile with POC (Point of Control) and Value Area
    - Delta analysis (buying vs selling pressure)
    - HVN/LVN detection (High/Low Volume Nodes)
    - Market regime classification
    - Entropy calculations
    - Bayesian confidence scores
    - Multiple trading signals
    
    Signals:
    - BUY: POC cross up, VA breakout up, absorption, coiling setup
    - SELL: POC cross down, VA breakout down, distribution, delta extreme bear
    - HOLD: Otherwise
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize Volume Profile indicator.
        
        Config parameters:
            profile_length (int): Profile lookback period (default: 100)
            num_rows (int): Number of price rows for profile (default: 70)
            value_area_pct (float): Value area percentage (default: 70.0)
            delta_method (str): Delta calculation method (default: 'microstructure_hybrid')
            hvn_threshold (float): HVN threshold in standard deviations (default: 1.3)
            lvn_threshold (float): LVN threshold in standard deviations (default: 0.4)
            use_htf (bool): Use higher timeframe data (default: False)
            htf_resolution (str): Higher timeframe resolution (default: '240')
            volume_filter (float): Min volume filter % (default: 3.0)
            price_buffer (float): Price buffer % (default: 2.0)
            enabled (bool): Whether indicator is enabled (default: True)
            weight (float): Indicator weight for voting (default: 2.0)
        """
        super().__init__(config)
        
        # Profile parameters
        self.profile_length = self.config.get('profile_length', 100)
        self.num_rows = self.config.get('num_rows', 70)
        self.value_area_pct = self.config.get('value_area_pct', 70.0)
        
        # Delta parameters
        self.delta_method = self.config.get('delta_method', 'microstructure_hybrid')
        
        # Node detection
        self.hvn_threshold = self.config.get('hvn_threshold', 1.3)
        self.lvn_threshold = self.config.get('lvn_threshold', 0.4)
        
        # Higher timeframe
        self.use_htf = self.config.get('use_htf', False)
        self.htf_resolution = self.config.get('htf_resolution', '240')
        
        # Filters
        self.volume_filter = self.config.get('volume_filter', 3.0) / 100.0
        self.price_buffer = self.config.get('price_buffer', 2.0) / 100.0
        
        # Signal parameters
        self.poc_cross_enabled = self.config.get('poc_cross_signal', True)
        self.va_break_enabled = self.config.get('va_breakout_signal', True)
        self.delta_extreme_enabled = self.config.get('delta_extreme_signal', True)
        self.absorption_enabled = self.config.get('absorption_signal', True)
        self.coiling_enabled = self.config.get('coiling_signal', True)
        
        # History tracking
        self.poc_history = []
        self.va_width_history = []
        self.delta_imbalance_history = []
        
        # Constants
        self.EPS = 1e-10
        
    def _safe_div(self, num: float, den: float, fallback: float = 0.0) -> float:
        """Safe division with epsilon check."""
        return num / den if abs(den) > self.EPS else fallback
    
    def _zscore(self, x: pd.Series, window: int) -> pd.Series:
        """Calculate z-score."""
        mean = x.rolling(window=window).mean()
        std = x.rolling(window=window).std()
        return (x - mean) / std.replace(0, self.EPS)
    
    def _calc_bar_delta(self, h: float, l: float, o: float, c: float, v: float) -> float:
        """
        Calculate buy/sell delta for a single bar.
        
        Supports multiple methods:
        - close_position: Based on close position in range
        - wicks_analysis: Analyzes wick rejection vs body
        - open_close_ratio: Uses body size and direction
        - microstructure_hybrid: Weighted fusion (recommended)
        """
        if v <= 0 or abs(h - l) < self.EPS:
            return 0.0
        
        range_val = h - l
        
        if self.delta_method == 'close_position':
            buy_ratio = self._safe_div(c - l, range_val, 0.5)
            return v * (2 * buy_ratio - 1)
        
        elif self.delta_method == 'wicks_analysis':
            upper_wick = h - max(o, c)
            lower_wick = min(o, c) - l
            body = abs(c - o)
            buy_pressure = lower_wick + (body if c > o else 0)
            sell_pressure = upper_wick + (body if c < o else 0)
            total_pressure = buy_pressure + sell_pressure
            if total_pressure < self.EPS:
                return 0.0
            return self._safe_div(buy_pressure - sell_pressure, total_pressure, 0) * v
        
        elif self.delta_method == 'open_close_ratio':
            body_ratio = self._safe_div(abs(c - o), range_val, 0)
            direction = 1.0 if c >= o else -1.0
            return v * direction * (0.5 + 0.5 * body_ratio)
        
        else:  # microstructure_hybrid (default)
            close_pos = self._safe_div(c - l, range_val, 0.5)
            upper_wick = h - max(o, c)
            lower_wick = min(o, c) - l
            body = abs(c - o)
            body_ratio = self._safe_div(body, range_val, 0)
            
            # Dynamic weights based on body ratio
            if body_ratio > 0.7:
                wick_weight = 0.2
                close_weight = 0.6
            elif body_ratio < 0.3:
                wick_weight = 0.5
                close_weight = 0.2
            else:
                wick_weight = 0.3
                close_weight = 0.4
            
            body_weight = 1.0 - wick_weight - close_weight
            
            # Components
            close_comp = 2 * close_pos - 1
            buy_press = lower_wick + (body if c > o else 0)
            sell_press = upper_wick + (body if c < o else 0)
            total_press = buy_press + sell_press
            wick_comp = self._safe_div(buy_press - sell_press, total_press, 0) if total_press > self.EPS else 0
            body_comp = (1.0 if c >= o else -1.0) * body_ratio
            
            return v * (close_weight * close_comp + wick_weight * wick_comp + body_weight * body_comp)
    
    def _build_profile(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, 
                                                          float, float, float, float]:
        """
        Build volume profile from recent bars.
        
        Returns:
            volume_profile: Array of volume per price row
            delta_profile: Array of delta per price row
            buy_profile: Array of buy volume per price row
            sell_profile: Array of sell volume per price row
            profile_high: Highest price in profile
            profile_low: Lowest price in profile
            total_volume: Total volume processed
            total_delta: Total delta processed
        """
        # Get recent data
        recent_df = df.tail(self.profile_length).copy()
        
        if len(recent_df) == 0:
            return (np.zeros(self.num_rows), np.zeros(self.num_rows), 
                   np.zeros(self.num_rows), np.zeros(self.num_rows),
                   0.0, 0.0, 0.0, 0.0)
        
        # Calculate price range
        highest_high = recent_df['high'].max()
        lowest_low = recent_df['low'].min()
        price_range = highest_high - lowest_low
        
        if price_range < self.EPS:
            price_range = highest_high * 0.01  # Fallback to 1% of price
        
        # Add buffer
        buffer_amount = price_range * self.price_buffer
        profile_high = highest_high + buffer_amount
        profile_low = lowest_low - buffer_amount
        profile_range = profile_high - profile_low
        
        # Calculate row height
        row_height = profile_range / self.num_rows
        
        # Initialize arrays
        volume_profile = np.zeros(self.num_rows)
        delta_profile = np.zeros(self.num_rows)
        buy_profile = np.zeros(self.num_rows)
        sell_profile = np.zeros(self.num_rows)
        
        total_volume = 0.0
        total_delta = 0.0
        
        # Process each bar
        for idx, row in recent_df.iterrows():
            h = row['high']
            l = row['low']
            o = row['open']
            c = row['close']
            v = row['volume']
            
            if pd.isna(v) or v <= 0 or pd.isna(h) or pd.isna(l):
                continue
            
            # Calculate delta
            bar_delta = self._calc_bar_delta(h, l, o, c, v)
            bar_buy_vol = max(0, (v + bar_delta) / 2)
            bar_sell_vol = max(0, (v - bar_delta) / 2)
            
            # Find rows this bar spans
            low_row = int(np.floor(self._safe_div(l - profile_low, row_height, 0)))
            high_row = int(np.floor(self._safe_div(h - profile_low, row_height, 0)))
            
            low_row = max(0, min(self.num_rows - 1, low_row))
            high_row = max(0, min(self.num_rows - 1, high_row))
            
            if high_row >= low_row:
                rows_spanned = high_row - low_row + 1
                vol_per_row = self._safe_div(v, rows_spanned, 0)
                delta_per_row = self._safe_div(bar_delta, rows_spanned, 0)
                buy_per_row = self._safe_div(bar_buy_vol, rows_spanned, 0)
                sell_per_row = self._safe_div(bar_sell_vol, rows_spanned, 0)
                
                for row_idx in range(low_row, high_row + 1):
                    volume_profile[row_idx] += vol_per_row
                    delta_profile[row_idx] += delta_per_row
                    buy_profile[row_idx] += buy_per_row
                    sell_profile[row_idx] += sell_per_row
                
                total_volume += v
                total_delta += bar_delta
        
        return (volume_profile, delta_profile, buy_profile, sell_profile,
                profile_high, profile_low, total_volume, total_delta)
    
    def _find_poc(self, volume_profile: np.ndarray, profile_low: float, row_height: float) -> Tuple[int, float, float]:
        """Find Point of Control (POC)."""
        poc_row = int(np.argmax(volume_profile))
        poc_price = profile_low + (poc_row + 0.5) * row_height
        poc_volume = volume_profile[poc_row]
        return poc_row, poc_price, poc_volume
    
    def _calc_value_area(self, volume_profile: np.ndarray, poc_row: int, 
                        profile_low: float, row_height: float) -> Tuple[float, float, float, int, int]:
        """Calculate Value Area."""
        total_vol = volume_profile.sum()
        if total_vol < self.EPS:
            return (0.0, 0.0, 0.0, poc_row, poc_row)
        
        target_vol = total_vol * (self.value_area_pct / 100.0)
        accumulated_vol = volume_profile[poc_row]
        
        va_high_row = poc_row
        va_low_row = poc_row
        
        iterations = 0
        max_iterations = self.num_rows * 2
        
        while accumulated_vol < target_vol and iterations < max_iterations:
            iterations += 1
            
            vol_above = volume_profile[va_high_row + 1] if va_high_row < self.num_rows - 1 else 0.0
            vol_below = volume_profile[va_low_row - 1] if va_low_row > 0 else 0.0
            
            if vol_above == 0 and vol_below == 0:
                break
            
            if vol_above >= vol_below and va_high_row < self.num_rows - 1:
                va_high_row += 1
                accumulated_vol += volume_profile[va_high_row]
            elif va_low_row > 0:
                va_low_row -= 1
                accumulated_vol += volume_profile[va_low_row]
            elif va_high_row < self.num_rows - 1:
                va_high_row += 1
                accumulated_vol += volume_profile[va_high_row]
            else:
                break
        
        va_high = profile_low + (va_high_row + 1) * row_height
        va_low = profile_low + va_low_row * row_height
        va_width = va_high - va_low
        
        return (va_high, va_low, va_width, va_high_row, va_low_row)
    
    def _calc_entropy(self, volume_profile: np.ndarray) -> float:
        """Calculate profile entropy."""
        total_vol = volume_profile.sum()
        if total_vol < self.EPS:
            return 0.0
        
        entropy = 0.0
        for vol in volume_profile:
            if vol > 0.0001:
                p = vol / total_vol
                entropy -= p * np.log2(p)
        
        return entropy
    
    def _detect_nodes(self, volume_profile: np.ndarray) -> Tuple[List[int], List[int]]:
        """Detect HVN (High Volume Nodes) and LVN (Low Volume Nodes)."""
        mean_vol = volume_profile.mean()
        std_vol = volume_profile.std()
        
        if std_vol < self.EPS:
            return ([], [])
        
        hvn_threshold_val = mean_vol + (self.hvn_threshold * std_vol)
        lvn_threshold_val = max(0, mean_vol - (self.lvn_threshold * std_vol))
        
        hvn_rows = []
        lvn_rows = []
        
        for i, vol in enumerate(volume_profile):
            if vol >= hvn_threshold_val:
                hvn_rows.append(i)
            elif vol <= lvn_threshold_val and vol > 0:
                lvn_rows.append(i)
        
        return (hvn_rows, lvn_rows)
    
    def _calc_regime(self, df: pd.DataFrame) -> Tuple[int, str]:
        """Detect market regime."""
        if len(df) < 30:
            return (2, "RANGING")
        
        sma10 = df['close'].rolling(10).mean()
        sma30 = df['close'].rolling(30).mean()
        atr = df['high'].rolling(14).apply(lambda x: x.max() - x.min()) / 14.0
        atr_sma = atr.rolling(50).mean()
        
        trend_strength = abs(sma10.iloc[-1] - sma30.iloc[-1]) / (atr.iloc[-1] + self.EPS)
        volatility_level = atr.iloc[-1] / (atr_sma.iloc[-1] + self.EPS)
        
        if trend_strength > 1.5 and volatility_level < 1.3:
            return (1, "TRENDING")
        elif trend_strength < 0.5 and volatility_level < 0.8:
            return (0, "QUIET")
        elif volatility_level > 1.5:
            return (3, "VOLATILE")
        else:
            return (2, "RANGING")
    
    def _calc_bayesian_confidence(self, delta_imbalance: float, poc_velocity: float,
                                  close: float, poc_price: float, va_high: float, va_low: float,
                                  vol_skew_z: float) -> Tuple[float, float]:
        """Calculate Bayesian confidence scores."""
        # Prior probabilities
        prior_bull = 0.5
        prior_bear = 0.5
        
        # Delta likelihood
        delta_likelihood_bull = 0.5 + min(0.4, abs(delta_imbalance) / 100) if delta_imbalance > 0 else 0.5 - min(0.4, abs(delta_imbalance) / 100)
        delta_likelihood_bull = max(0.1, min(0.9, delta_likelihood_bull))
        delta_likelihood_bear = 1 - delta_likelihood_bull
        
        # POC velocity likelihood
        poc_likelihood_bull = 0.5 + min(0.3, abs(poc_velocity) / 5) if poc_velocity > 0 else 0.5 - min(0.3, abs(poc_velocity) / 5)
        poc_likelihood_bull = max(0.1, min(0.9, poc_likelihood_bull))
        poc_likelihood_bear = 1 - poc_likelihood_bull
        
        # Position likelihood
        if close > va_high:
            position_likelihood_bull = 0.75
        elif close > poc_price:
            position_likelihood_bull = 0.6
        elif close < va_low:
            position_likelihood_bull = 0.25
        else:
            position_likelihood_bull = 0.4
        position_likelihood_bear = 1 - position_likelihood_bull
        
        # Skew likelihood
        skew_likelihood_bull = 0.5 + min(0.2, abs(vol_skew_z) / 5) if vol_skew_z < 0 else 0.5 - min(0.2, abs(vol_skew_z) / 5)
        skew_likelihood_bull = max(0.1, min(0.9, skew_likelihood_bull))
        skew_likelihood_bear = 1 - skew_likelihood_bull
        
        # Combined evidence
        combined_bull = (delta_likelihood_bull * poc_likelihood_bull * 
                         position_likelihood_bull * skew_likelihood_bull * prior_bull)
        combined_bear = (delta_likelihood_bear * poc_likelihood_bear * 
                         position_likelihood_bear * skew_likelihood_bear * prior_bear)
        
        total_evidence = combined_bull + combined_bear
        if total_evidence < self.EPS:
            return (0.5, 0.5)
        
        bullish_conf = combined_bull / total_evidence
        bearish_conf = combined_bear / total_evidence
        
        return (bullish_conf, bearish_conf)
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Volume Profile indicator and generate signals.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with volume profile metrics and signals
        """
        df = df.copy()
        
        # Initialize columns
        df['vp_poc'] = np.nan
        df['vp_va_high'] = np.nan
        df['vp_va_low'] = np.nan
        df['vp_delta_imbalance'] = np.nan
        df['vp_entropy'] = np.nan
        df['vp_regime'] = ''
        df['vp_bullish_conf'] = np.nan
        df['vp_bearish_conf'] = np.nan
        df['vp_signal'] = 'HOLD'
        
        # Need minimum data
        if len(df) < self.profile_length:
            df['signal'] = 'HOLD'
            return df
        
        # Calculate for each bar (rolling window)
        for i in range(self.profile_length, len(df)):
            window_df = df.iloc[:i+1]
            
            # Build profile
            (volume_profile, delta_profile, buy_profile, sell_profile,
             profile_high, profile_low, total_volume, total_delta) = self._build_profile(window_df)
            
            if total_volume < self.EPS:
                continue
            
            # Calculate row height
            profile_range = profile_high - profile_low
            row_height = profile_range / self.num_rows
            
            # Find POC
            poc_row, poc_price, poc_volume = self._find_poc(volume_profile, profile_low, row_height)
            
            # Calculate Value Area
            va_high, va_low, va_width, va_high_row, va_low_row = self._calc_value_area(
                volume_profile, poc_row, profile_low, row_height)
            
            # Calculate delta imbalance
            total_buy = buy_profile.sum()
            total_sell = sell_profile.sum()
            total_vol = total_buy + total_sell
            if total_vol > self.EPS:
                buy_pct = (total_buy / total_vol) * 100
                sell_pct = (total_sell / total_vol) * 100
                delta_imbalance = buy_pct - sell_pct
            else:
                delta_imbalance = 0.0
            
            # Calculate entropy
            entropy = self._calc_entropy(volume_profile)
            max_entropy = np.log2(self.num_rows)
            normalized_entropy = self._safe_div(entropy, max_entropy, 0)
            
            # Detect regime
            regime_id, regime_name = self._calc_regime(window_df)
            
            # Calculate volatility skew
            returns = np.log(window_df['close'] / window_df['close'].shift(1))
            up_returns = returns.where(returns > 0, 0)
            down_returns = returns.where(returns < 0, 0)
            up_vol = up_returns.rolling(14).std().iloc[-1] * np.sqrt(252)
            down_vol = abs(down_returns.rolling(14).std().iloc[-1]) * np.sqrt(252)
            vol_skew = self._safe_div(down_vol - up_vol, (up_vol + down_vol) / 2, 0) * 100 if (up_vol + down_vol) > self.EPS else 0
            vol_skew_z = self._zscore(pd.Series([vol_skew]), 50).iloc[-1] if len(window_df) >= 50 else 0
            
            # POC velocity (simplified - compare to previous POC)
            poc_velocity = 0.0
            if len(self.poc_history) > 0:
                poc_velocity = poc_price - self.poc_history[-1]
            
            # Bayesian confidence
            bullish_conf, bearish_conf = self._calc_bayesian_confidence(
                delta_imbalance, poc_velocity, window_df['close'].iloc[-1],
                poc_price, va_high, va_low, vol_skew_z)
            
            # Store values
            df.loc[df.index[i], 'vp_poc'] = poc_price
            df.loc[df.index[i], 'vp_va_high'] = va_high
            df.loc[df.index[i], 'vp_va_low'] = va_low
            df.loc[df.index[i], 'vp_delta_imbalance'] = delta_imbalance
            df.loc[df.index[i], 'vp_entropy'] = normalized_entropy * 100
            df.loc[df.index[i], 'vp_regime'] = regime_name
            df.loc[df.index[i], 'vp_bullish_conf'] = bullish_conf * 100
            df.loc[df.index[i], 'vp_bearish_conf'] = bearish_conf * 100
            
            # Update history
            self.poc_history.append(poc_price)
            self.va_width_history.append(va_width)
            self.delta_imbalance_history.append(delta_imbalance)
            
            # Keep history limited
            if len(self.poc_history) > 500:
                self.poc_history.pop(0)
                self.va_width_history.pop(0)
                self.delta_imbalance_history.pop(0)
        
        # Generate signals based on latest values
        df['signal'] = 'HOLD'
        
        # Get latest values
        latest_idx = df['vp_poc'].last_valid_index()
        if latest_idx is None:
            return df
        
        latest = df.loc[latest_idx]
        current_close = latest['close']
        poc_price = latest['vp_poc']
        va_high = latest['vp_va_high']
        va_low = latest['vp_va_low']
        delta_imbalance = latest['vp_delta_imbalance']
        bullish_conf = latest['vp_bullish_conf']
        bearish_conf = latest['vp_bearish_conf']
        
        # Previous bar values for cross detection
        if latest_idx != df.index[0]:
            prev_idx = df.index[df.index.get_loc(latest_idx) - 1]
            prev_close = df.loc[prev_idx, 'close']
            prev_poc = df.loc[prev_idx, 'vp_poc'] if not pd.isna(df.loc[prev_idx, 'vp_poc']) else poc_price
            prev_va_high = df.loc[prev_idx, 'vp_va_high'] if not pd.isna(df.loc[prev_idx, 'vp_va_high']) else va_high
            prev_va_low = df.loc[prev_idx, 'vp_va_low'] if not pd.isna(df.loc[prev_idx, 'vp_va_low']) else va_low
        else:
            prev_close = current_close
            prev_poc = poc_price
            prev_va_high = va_high
            prev_va_low = va_low
        
        # Volume check
        avg_volume = df['volume'].rolling(50).mean().iloc[-1] if len(df) >= 50 else df['volume'].mean()
        current_volume = latest['volume']
        volume_confirmation = current_volume > avg_volume * 1.2
        
        # Signal generation
        # POC Cross
        if self.poc_cross_enabled:
            if prev_close <= prev_poc and current_close > poc_price and volume_confirmation:
                df.loc[latest_idx, 'signal'] = 'BUY'
            elif prev_close >= prev_poc and current_close < poc_price and volume_confirmation:
                df.loc[latest_idx, 'signal'] = 'SELL'
        
        # VA Breakout
        if self.va_break_enabled:
            if prev_close <= prev_va_high and current_close > va_high and volume_confirmation:
                df.loc[latest_idx, 'signal'] = 'BUY'
            elif prev_close >= prev_va_low and current_close < va_low and volume_confirmation:
                df.loc[latest_idx, 'signal'] = 'SELL'
        
        # Delta Extreme
        if self.delta_extreme_enabled:
            if abs(delta_imbalance) > 25:
                if delta_imbalance > 15 and current_close > poc_price and current_close > va_high:
                    df.loc[latest_idx, 'signal'] = 'BUY'
                elif delta_imbalance < -15 and current_close < poc_price and current_close < va_low:
                    df.loc[latest_idx, 'signal'] = 'SELL'
        
        # Absorption/Distribution
        if self.absorption_enabled:
            # Simplified: high volume with low price movement
            price_change_pct = abs((current_close - prev_close) / prev_close * 100) if prev_close > 0 else 0
            if current_volume > avg_volume * 2.0:
                if delta_imbalance > 20 and price_change_pct < 0.5:
                    df.loc[latest_idx, 'signal'] = 'BUY'  # Absorption
                elif delta_imbalance < -20 and price_change_pct < 0.5:
                    df.loc[latest_idx, 'signal'] = 'SELL'  # Distribution
        
        # Coiling Setup
        if self.coiling_enabled:
            if len(self.va_width_history) >= 5:
                recent_va_widths = self.va_width_history[-5:]
                va_width_sma = np.mean(recent_va_widths)
                current_va_width = latest['vp_va_high'] - latest['vp_va_low']
                va_ratio = self._safe_div(current_va_width, va_width_sma, 1.0)
                
                if va_ratio < 0.8 and abs(delta_imbalance) < 5 and current_volume < avg_volume * 0.8:
                    # Coiling - prepare for breakout
                    if bullish_conf > 60:
                        df.loc[latest_idx, 'signal'] = 'BUY'
                    elif bearish_conf > 60:
                        df.loc[latest_idx, 'signal'] = 'SELL'
        
        # Bayesian confidence override
        if bullish_conf > 70 and current_close > poc_price:
            df.loc[latest_idx, 'signal'] = 'BUY'
        elif bearish_conf > 70 and current_close < poc_price:
            df.loc[latest_idx, 'signal'] = 'SELL'
        
        return df
    
    def get_required_columns(self) -> list:
        """Required columns for Volume Profile calculation."""
        return ['open', 'high', 'low', 'close', 'volume']

