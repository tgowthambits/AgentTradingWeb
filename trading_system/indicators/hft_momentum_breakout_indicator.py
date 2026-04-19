"""
HFT Momentum Breakout Indicator

Detects momentum breakouts with volume spike and price acceleration.
"""

import pandas as pd
import numpy as np
from trading_system.core.base_indicator import BaseIndicator


class HFTMomentumBreakoutIndicator(BaseIndicator):
    """
    HFT Momentum Breakout Indicator
    
    Signals:
    - BUY: Volume spike + upward price acceleration
    - SELL: Volume spike + downward price acceleration
    - HOLD: No clear breakout pattern
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize HFT Momentum Breakout indicator.
        
        Config parameters:
            volume_spike_multiplier (float): Volume spike threshold (default: 2.0)
            lookback_period (int): Period for volume analysis (default: 20)
            acceleration_period (int): Period for acceleration calculation (default: 5)
            min_acceleration (float): Minimum acceleration for signal (default: 0.001)
            false_breakout_filter (bool): Filter false breakouts (default: True)
            enabled (bool): Whether indicator is enabled (default: True)
            weight (float): Indicator weight for voting (default: 1.5)
        """
        super().__init__(config)
        
        self.volume_spike_multiplier = self.config.get('volume_spike_multiplier', 2.0)
        self.lookback_period = self.config.get('lookback_period', 20)
        self.acceleration_period = self.config.get('acceleration_period', 5)
        self.min_acceleration = self.config.get('min_acceleration', 0.001)
        self.false_breakout_filter = self.config.get('false_breakout_filter', True)
    
    def _detect_volume_spike(self, df: pd.DataFrame) -> pd.Series:
        """
        Detect volume spikes.
        
        Volume spike = current volume > N * average volume
        """
        if 'volume' not in df.columns:
            return pd.Series(False, index=df.index)
        
        avg_volume = df['volume'].rolling(window=self.lookback_period).mean()
        volume_spike = df['volume'] > (avg_volume * self.volume_spike_multiplier)
        
        return volume_spike
    
    def _calculate_price_acceleration(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate price acceleration (second derivative of price).
        
        Acceleration = rate of change of velocity
        """
        # Price velocity (first derivative)
        velocity = df['close'].diff(periods=self.acceleration_period) / self.acceleration_period
        
        # Price acceleration (second derivative)
        acceleration = velocity.diff(periods=self.acceleration_period) / self.acceleration_period
        
        # Normalize by price
        acceleration_pct = (acceleration / df['close']) * 100
        
        return acceleration_pct
    
    def _detect_false_breakout(self, df: pd.DataFrame, breakout_direction: str) -> pd.Series:
        """
        Filter false breakouts.
        
        False breakout = breakout that quickly reverses.
        """
        if not self.false_breakout_filter:
            return pd.Series(False, index=df.index)
        
        false_breakout = pd.Series(False, index=df.index)
        
        # Look for reversals within 3 periods after breakout
        if breakout_direction == 'BUY':
            # Check if price drops significantly after breakout
            future_price = df['close'].shift(-3)
            price_drop = (df['close'] - future_price) / df['close']
            false_breakout = price_drop > 0.01  # 1% drop = false breakout
        elif breakout_direction == 'SELL':
            # Check if price rises significantly after breakout
            future_price = df['close'].shift(-3)
            price_rise = (future_price - df['close']) / df['close']
            false_breakout = price_rise > 0.01  # 1% rise = false breakout
        
        return false_breakout
    
    def _calculate_breakout_strength(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate breakout strength (combination of volume and acceleration).
        """
        if 'volume' not in df.columns:
            return pd.Series(0, index=df.index)
        
        # Normalize volume
        avg_volume = df['volume'].rolling(window=self.lookback_period).mean()
        volume_ratio = df['volume'] / (avg_volume + 1e-10)
        
        # Normalize acceleration
        acceleration = self._calculate_price_acceleration(df)
        acceleration_abs = acceleration.abs()
        max_acceleration = acceleration_abs.rolling(window=self.lookback_period).max()
        acceleration_normalized = acceleration_abs / (max_acceleration + 1e-10)
        
        # Breakout strength = weighted combination
        breakout_strength = (volume_ratio * 0.6) + (acceleration_normalized * 0.4)
        
        return breakout_strength
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate momentum breakout signals.
        
        Args:
            df: DataFrame with 'close', 'volume' columns
        
        Returns:
            DataFrame with breakout metrics and 'signal' column
        """
        if len(df) < max(self.lookback_period, self.acceleration_period * 2):
            df['signal'] = 'HOLD'
            return df
        
        # Detect volume spikes
        df['volume_spike'] = self._detect_volume_spike(df)
        
        # Calculate price acceleration
        df['price_acceleration'] = self._calculate_price_acceleration(df)
        df['price_acceleration_abs'] = df['price_acceleration'].abs()
        
        # Calculate breakout strength
        df['breakout_strength'] = self._calculate_breakout_strength(df)
        
        # Price velocity for confirmation
        df['price_velocity'] = df['close'].pct_change(periods=self.acceleration_period)
        
        # Generate signals
        df['signal'] = 'HOLD'
        
        # BUY conditions: Volume spike + upward price acceleration
        buy_conditions = (
            (df['volume_spike']) &  # Volume spike
            (df['price_acceleration'] > self.min_acceleration) &  # Positive acceleration
            (df['price_velocity'] > 0) &  # Positive velocity
            (df['breakout_strength'] > 0.7)  # Strong breakout
        )
        
        # Filter false breakouts
        if self.false_breakout_filter:
            false_breakouts = self._detect_false_breakout(df, 'BUY')
            buy_conditions = buy_conditions & (~false_breakouts)
        
        df.loc[buy_conditions, 'signal'] = 'BUY'
        
        # SELL conditions: Volume spike + downward price acceleration
        sell_conditions = (
            (df['volume_spike']) &  # Volume spike
            (df['price_acceleration'] < -self.min_acceleration) &  # Negative acceleration
            (df['price_velocity'] < 0) &  # Negative velocity
            (df['breakout_strength'] > 0.7)  # Strong breakout
        )
        
        # Filter false breakouts
        if self.false_breakout_filter:
            false_breakouts = self._detect_false_breakout(df, 'SELL')
            sell_conditions = sell_conditions & (~false_breakouts)
        
        df.loc[sell_conditions, 'signal'] = 'SELL'
        
        # Fill NaN values with HOLD
        df['signal'] = df['signal'].fillna('HOLD')
        
        return df
    
    def get_required_columns(self) -> list:
        """Required columns for breakout calculation."""
        cols = ['close']
        # Volume is optional but recommended
        return cols

