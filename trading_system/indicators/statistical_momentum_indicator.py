"""
Statistical Momentum Indicator

Uses Rate of Change (ROC), acceleration, and velocity to identify momentum opportunities.
"""

import pandas as pd
import numpy as np
from trading_system.core.base_indicator import BaseIndicator


class StatisticalMomentumIndicator(BaseIndicator):
    """
    Statistical Momentum Indicator
    
    Signals:
    - BUY: Strong positive momentum with acceleration
    - SELL: Strong negative momentum with deceleration
    - HOLD: Weak or conflicting momentum
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize Statistical Momentum indicator.
        
        Config parameters:
            roc_period (int): Rate of change period (default: 10)
            velocity_period (int): Velocity calculation period (default: 5)
            acceleration_period (int): Acceleration calculation period (default: 3)
            momentum_threshold (float): Minimum momentum threshold (default: 0.02)
            divergence_lookback (int): Lookback for divergence detection (default: 20)
            enabled (bool): Whether indicator is enabled (default: True)
            weight (float): Indicator weight for voting (default: 1.5)
        """
        super().__init__(config)
        
        self.roc_period = self.config.get('roc_period', 10)
        self.velocity_period = self.config.get('velocity_period', 5)
        self.acceleration_period = self.config.get('acceleration_period', 3)
        self.momentum_threshold = self.config.get('momentum_threshold', 0.02)
        self.divergence_lookback = self.config.get('divergence_lookback', 20)
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate momentum signals.
        
        Args:
            df: DataFrame with 'close' column
        
        Returns:
            DataFrame with momentum metrics and 'signal' column
        """
        if len(df) < max(self.roc_period, self.velocity_period, self.acceleration_period) + 5:
            df['signal'] = 'HOLD'
            return df
        
        # Rate of Change (ROC)
        df['roc'] = df['close'].pct_change(periods=self.roc_period) * 100
        
        # Price velocity (first derivative - rate of change of price)
        df['velocity'] = df['close'].diff(periods=self.velocity_period) / self.velocity_period
        
        # Price acceleration (second derivative - rate of change of velocity)
        df['acceleration'] = df['velocity'].diff(periods=self.acceleration_period) / self.acceleration_period
        
        # Normalize acceleration by price to get percentage acceleration
        df['acceleration_pct'] = (df['acceleration'] / df['close']) * 100
        
        # Momentum strength (combination of ROC and velocity)
        df['momentum_strength'] = (df['roc'].abs() + df['velocity'].abs() / df['close'] * 100) / 2
        
        # Momentum divergence detection
        # Bullish divergence: Price makes lower low, momentum makes higher low
        # Bearish divergence: Price makes higher high, momentum makes lower high
        df['momentum_divergence'] = 0
        
        if len(df) >= self.divergence_lookback:
            # Find recent price and momentum peaks/troughs
            price_highs = df['close'].rolling(window=5, center=True).max() == df['close']
            price_lows = df['close'].rolling(window=5, center=True).min() == df['close']
            momentum_highs = df['momentum_strength'].rolling(window=5, center=True).max() == df['momentum_strength']
            momentum_lows = df['momentum_strength'].rolling(window=5, center=True).min() == df['momentum_strength']
            
            # Bullish divergence: price low but momentum higher
            bullish_div = price_lows & (df['momentum_strength'] > df['momentum_strength'].shift(5))
            df.loc[bullish_div, 'momentum_divergence'] = 1
            
            # Bearish divergence: price high but momentum lower
            bearish_div = price_highs & (df['momentum_strength'] < df['momentum_strength'].shift(5))
            df.loc[bearish_div, 'momentum_divergence'] = -1
        
        # Generate signals
        df['signal'] = 'HOLD'
        
        # BUY conditions: Strong positive momentum with acceleration
        buy_conditions = (
            (df['roc'] > self.momentum_threshold * 100) &  # Positive ROC above threshold
            (df['velocity'] > 0) &  # Positive velocity
            (df['acceleration_pct'] > 0) &  # Positive acceleration
            (df['momentum_strength'] > self.momentum_threshold * 50) &  # Strong momentum
            (df['momentum_divergence'] != -1)  # No bearish divergence
        )
        
        df.loc[buy_conditions, 'signal'] = 'BUY'
        
        # SELL conditions: Strong negative momentum with deceleration
        sell_conditions = (
            (df['roc'] < -self.momentum_threshold * 100) &  # Negative ROC below threshold
            (df['velocity'] < 0) &  # Negative velocity
            (df['acceleration_pct'] < 0) &  # Negative acceleration
            (df['momentum_strength'] > self.momentum_threshold * 50) &  # Strong momentum
            (df['momentum_divergence'] != 1)  # No bullish divergence
        )
        
        df.loc[sell_conditions, 'signal'] = 'SELL'
        
        # Fill NaN values with HOLD
        df['signal'] = df['signal'].fillna('HOLD')
        
        return df
    
    def get_required_columns(self) -> list:
        """Required columns for momentum calculation."""
        return ['close']

