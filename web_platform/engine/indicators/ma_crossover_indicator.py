"""
Moving Average Crossover Indicator

Generates BUY/SELL/HOLD signals based on MA crossovers.
"""

import pandas as pd
from engine.core.base_indicator import BaseIndicator


class MACrossoverIndicator(BaseIndicator):
    """
    Moving Average Crossover Indicator
    
    Signals:
    - BUY: Fast MA crosses above Slow MA
    - SELL: Fast MA crosses below Slow MA
    - HOLD: No crossover
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize MA Crossover indicator.
        
        Config parameters:
            fast_period (int): Fast MA period (default: 50)
            slow_period (int): Slow MA period (default: 200)
            ma_type (str): MA type - 'sma' or 'ema' (default: 'sma')
            enabled (bool): Whether indicator is enabled (default: True)
            weight (float): Indicator weight for voting (default: 1.0)
        """
        super().__init__(config)
        
        self.fast_period = self.config.get('fast_period', 50)
        self.slow_period = self.config.get('slow_period', 200)
        self.ma_type = self.config.get('ma_type', 'sma')
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate MA crossover and generate signals.
        
        Args:
            df: DataFrame with 'close' column
        
        Returns:
            DataFrame with 'ma_fast', 'ma_slow', and 'signal' columns
        """
        # Calculate moving averages
        if self.ma_type == 'ema':
            df['ma_fast'] = df['close'].ewm(span=self.fast_period, adjust=False).mean()
            df['ma_slow'] = df['close'].ewm(span=self.slow_period, adjust=False).mean()
        else:  # sma
            df['ma_fast'] = df['close'].rolling(window=self.fast_period).mean()
            df['ma_slow'] = df['close'].rolling(window=self.slow_period).mean()
        
        # Calculate crossover
        df['ma_diff'] = df['ma_fast'] - df['ma_slow']
        df['ma_diff_prev'] = df['ma_diff'].shift(1)
        
        # Generate signals based on trend (not just crossover)
        df['signal'] = 'HOLD'
        
        # BUY: Fast MA above Slow MA (bullish trend)
        df.loc[df['ma_fast'] > df['ma_slow'], 'signal'] = 'BUY'
        
        # SELL: Fast MA below Slow MA (bearish trend)
        df.loc[df['ma_fast'] < df['ma_slow'], 'signal'] = 'SELL'
        
        return df
    
    def get_required_columns(self) -> list:
        """Required columns for MA crossover calculation."""
        return ['close']
