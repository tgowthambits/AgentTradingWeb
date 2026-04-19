"""
MACD (Moving Average Convergence Divergence) Indicator

Generates BUY/SELL/HOLD signals based on MACD crossovers.
"""

import pandas as pd
from trading_system.core.base_indicator import BaseIndicator


class MACDIndicator(BaseIndicator):
    """
    MACD Indicator
    
    Signals:
    - BUY: MACD crosses above signal line
    - SELL: MACD crosses below signal line
    - HOLD: No crossover
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize MACD indicator.
        
        Config parameters:
            fast_period (int): Fast EMA period (default: 12)
            slow_period (int): Slow EMA period (default: 26)
            signal_period (int): Signal line period (default: 9)
            enabled (bool): Whether indicator is enabled (default: True)
            weight (float): Indicator weight for voting (default: 1.0)
        """
        super().__init__(config)
        
        self.fast_period = self.config.get('fast_period', 12)
        self.slow_period = self.config.get('slow_period', 26)
        self.signal_period = self.config.get('signal_period', 9)
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate MACD and generate signals.
        
        Args:
            df: DataFrame with 'close' column
        
        Returns:
            DataFrame with 'macd', 'macd_signal', 'macd_histogram', and 'signal' columns
        """
        # Calculate EMAs
        ema_fast = df['close'].ewm(span=self.fast_period, adjust=False).mean()
        ema_slow = df['close'].ewm(span=self.slow_period, adjust=False).mean()
        
        # Calculate MACD line
        df['macd'] = ema_fast - ema_slow
        
        # Calculate signal line
        df['macd_signal'] = df['macd'].ewm(span=self.signal_period, adjust=False).mean()
        
        # Calculate histogram
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Generate signals based on MACD position relative to signal line
        df['signal'] = 'HOLD'
        
        # BUY: MACD above signal line and positive
        df.loc[(df['macd'] > df['macd_signal']) & (df['macd'] > 0), 'signal'] = 'BUY'
        
        # SELL: MACD below signal line and negative
        df.loc[(df['macd'] < df['macd_signal']) & (df['macd'] < 0), 'signal'] = 'SELL'
        
        return df
    
    def get_required_columns(self) -> list:
        """Required columns for MACD calculation."""
        return ['close']

