"""
Bollinger Bands Indicator

Generates BUY/SELL/HOLD signals based on price position relative to bands.
"""

import pandas as pd
import numpy as np
from trading_system.core.base_indicator import BaseIndicator


class BollingerBandsIndicator(BaseIndicator):
    """
    Bollinger Bands Indicator
    
    Signals:
    - BUY: Price crosses below lower band (oversold)
    - SELL: Price crosses above upper band (overbought)
    - HOLD: Price within bands
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize Bollinger Bands indicator.
        
        Config parameters:
            period (int): MA period for middle band (default: 20)
            std_dev (float): Standard deviations for bands (default: 2.0)
            enabled (bool): Whether indicator is enabled (default: True)
            weight (float): Indicator weight for voting (default: 1.0)
        """
        super().__init__(config)
        
        self.period = self.config.get('period', 20)
        self.std_dev = self.config.get('std_dev', 2.0)
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Bollinger Bands and generate signals.
        
        Args:
            df: DataFrame with 'close' column
        
        Returns:
            DataFrame with 'bb_middle', 'bb_upper', 'bb_lower', and 'signal' columns
        """
        # Calculate middle band (SMA)
        df['bb_middle'] = df['close'].rolling(window=self.period).mean()
        
        # Calculate standard deviation
        std = df['close'].rolling(window=self.period).std()
        
        # Calculate upper and lower bands
        df['bb_upper'] = df['bb_middle'] + (std * self.std_dev)
        df['bb_lower'] = df['bb_middle'] - (std * self.std_dev)
        
        # Calculate %B (position within bands)
        df['bb_percent'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Generate signals
        df['signal'] = 'HOLD'
        
        # BUY: Price at or below lower band (oversold)
        df.loc[df['close'] <= df['bb_lower'], 'signal'] = 'BUY'
        
        # SELL: Price at or above upper band (overbought)
        df.loc[df['close'] >= df['bb_upper'], 'signal'] = 'SELL'
        
        return df
    
    def get_required_columns(self) -> list:
        """Required columns for Bollinger Bands calculation."""
        return ['close']

