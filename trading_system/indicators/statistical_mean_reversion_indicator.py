"""
Statistical Mean Reversion Indicator

Uses Z-score, Bollinger Band squeeze, and VWAP deviation to identify mean reversion opportunities.
"""

import pandas as pd
import numpy as np
from trading_system.core.base_indicator import BaseIndicator


class StatisticalMeanReversionIndicator(BaseIndicator):
    """
    Statistical Mean Reversion Indicator
    
    Signals:
    - BUY: Price significantly below mean (z-score < -2) with oversold confirmation
    - SELL: Price significantly above mean (z-score > 2) with overbought confirmation
    - HOLD: Price near mean or insufficient data
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize Statistical Mean Reversion indicator.
        
        Config parameters:
            lookback_period (int): Period for rolling mean/std (default: 20)
            z_score_threshold (float): Z-score threshold for signals (default: 2.0)
            bollinger_period (int): Bollinger Band period (default: 20)
            bollinger_std (float): Bollinger Band std dev (default: 2.0)
            squeeze_threshold (float): BB squeeze threshold (default: 0.1)
            vwap_enabled (bool): Use VWAP deviation (default: True)
            enabled (bool): Whether indicator is enabled (default: True)
            weight (float): Indicator weight for voting (default: 1.5)
        """
        super().__init__(config)
        
        self.lookback_period = self.config.get('lookback_period', 20)
        self.z_score_threshold = self.config.get('z_score_threshold', 2.0)
        self.bollinger_period = self.config.get('bollinger_period', 20)
        self.bollinger_std = self.config.get('bollinger_std', 2.0)
        self.squeeze_threshold = self.config.get('squeeze_threshold', 0.1)
        self.vwap_enabled = self.config.get('vwap_enabled', True)
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate mean reversion signals.
        
        Args:
            df: DataFrame with 'close', 'high', 'low', 'volume' columns
        
        Returns:
            DataFrame with mean reversion metrics and 'signal' column
        """
        if len(df) < self.lookback_period:
            df['signal'] = 'HOLD'
            return df
        
        # Calculate rolling mean and std
        rolling_mean = df['close'].rolling(window=self.lookback_period).mean()
        rolling_std = df['close'].rolling(window=self.lookback_period).std()
        
        # Calculate Z-score
        df['z_score'] = (df['close'] - rolling_mean) / rolling_std
        
        # Bollinger Bands
        bb_mean = df['close'].rolling(window=self.bollinger_period).mean()
        bb_std = df['close'].rolling(window=self.bollinger_period).std()
        df['bb_upper'] = bb_mean + (bb_std * self.bollinger_std)
        df['bb_lower'] = bb_mean - (bb_std * self.bollinger_std)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / bb_mean
        
        # Bollinger Band squeeze detection
        bb_width_mean = df['bb_width'].rolling(window=self.bollinger_period).mean()
        df['bb_squeeze'] = df['bb_width'] < (bb_width_mean * self.squeeze_threshold)
        
        # VWAP calculation and deviation
        if self.vwap_enabled and 'volume' in df.columns:
            typical_price = (df['high'] + df['low'] + df['close']) / 3
            df['vwap'] = (typical_price * df['volume']).rolling(window=self.lookback_period).sum() / df['volume'].rolling(window=self.lookback_period).sum()
            df['vwap_deviation'] = (df['close'] - df['vwap']) / df['vwap'] * 100
            df['vwap_z_score'] = df['vwap_deviation'] / df['vwap_deviation'].rolling(window=self.lookback_period).std()
        else:
            df['vwap'] = rolling_mean
            df['vwap_deviation'] = 0
            df['vwap_z_score'] = 0
        
        # Generate signals
        df['signal'] = 'HOLD'
        
        # BUY conditions: Price significantly below mean
        buy_conditions = (
            (df['z_score'] < -self.z_score_threshold) &  # Z-score below threshold
            (df['close'] < df['bb_lower']) &  # Price below lower Bollinger Band
            (df['bb_squeeze'] == False)  # Not in squeeze (volatility present)
        )
        
        # Add VWAP confirmation if enabled
        if self.vwap_enabled:
            buy_conditions = buy_conditions & (df['vwap_z_score'] < -1.5)
        
        df.loc[buy_conditions, 'signal'] = 'BUY'
        
        # SELL conditions: Price significantly above mean
        sell_conditions = (
            (df['z_score'] > self.z_score_threshold) &  # Z-score above threshold
            (df['close'] > df['bb_upper']) &  # Price above upper Bollinger Band
            (df['bb_squeeze'] == False)  # Not in squeeze
        )
        
        # Add VWAP confirmation if enabled
        if self.vwap_enabled:
            sell_conditions = sell_conditions & (df['vwap_z_score'] > 1.5)
        
        df.loc[sell_conditions, 'signal'] = 'SELL'
        
        # Fill NaN values with HOLD
        df['signal'] = df['signal'].fillna('HOLD')
        
        return df
    
    def get_required_columns(self) -> list:
        """Required columns for mean reversion calculation."""
        cols = ['close', 'high', 'low']
        if self.vwap_enabled:
            cols.append('volume')
        return cols

