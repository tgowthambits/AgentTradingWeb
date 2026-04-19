"""
RSI (Relative Strength Index) Indicator

Generates BUY/SELL/HOLD signals based on RSI values.
"""

import pandas as pd
import numpy as np
from engine.core.base_indicator import BaseIndicator


class RSIIndicator(BaseIndicator):
    """
    RSI Indicator
    
    Signals:
    - BUY: RSI < oversold_threshold (default 30)
    - SELL: RSI > overbought_threshold (default 70)
    - HOLD: Otherwise
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize RSI indicator.
        
        Config parameters:
            period (int): RSI period (default: 14)
            oversold (float): Oversold threshold (default: 30)
            overbought (float): Overbought threshold (default: 70)
            enabled (bool): Whether indicator is enabled (default: True)
            weight (float): Indicator weight for voting (default: 1.0)
        """
        super().__init__(config)
        
        self.period = self.config.get('period', 14)
        self.oversold = self.config.get('oversold', 30)
        self.overbought = self.config.get('overbought', 70)
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate RSI and generate signals.
        
        Args:
            df: DataFrame with 'close' column
        
        Returns:
            DataFrame with 'rsi' and 'signal' columns
        """
        # Calculate price changes
        delta = df['close'].diff()
        
        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Calculate average gain and loss
        avg_gain = gain.rolling(window=self.period).mean()
        avg_loss = loss.rolling(window=self.period).mean()
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        df['rsi'] = rsi
        
        # Generate signals
        df['signal'] = 'HOLD'
        df.loc[df['rsi'] < self.oversold, 'signal'] = 'BUY'
        df.loc[df['rsi'] > self.overbought, 'signal'] = 'SELL'
        
        return df
    
    def get_required_columns(self) -> list:
        """Required columns for RSI calculation."""
        return ['close']
