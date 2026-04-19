"""
Base Indicator Abstract Class

All custom indicators must inherit from this class and implement the required methods.
This provides a plug-and-play architecture for adding new indicators.
"""

from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any


class BaseIndicator(ABC):
    """
    Abstract base class for all trading indicators.
    
    Every indicator must:
    1. Inherit from this class
    2. Implement calculate() method
    3. Return a DataFrame with 'signal' column (values: 'BUY', 'SELL', 'HOLD')
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the indicator.
        
        Args:
            config: Configuration parameters for the indicator
        """
        self.config = config if config is not None else {}
        
        # Auto-generate name from class name (e.g., RSIIndicator -> RSI)
        class_name = self.__class__.__name__
        self.name = class_name.replace('Indicator', '')
        
        self.enabled = self.config.get('enabled', True)
        self.weight = self.config.get('weight', 1.0)  # For weighted voting
    
    @abstractmethod
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate the indicator and generate signals.
        
        Args:
            df: DataFrame with OHLCV data (columns: open, high, low, close, volume, date/time)
        
        Returns:
            DataFrame with original data plus:
            - 'signal' column with values: 'BUY', 'SELL', 'HOLD'
            - Any additional indicator columns (optional)
        
        Example:
            df['my_indicator'] = ... # Calculate your indicator
            df['signal'] = 'HOLD'    # Default
            df.loc[df['my_indicator'] > threshold, 'signal'] = 'BUY'
            df.loc[df['my_indicator'] < -threshold, 'signal'] = 'SELL'
            return df
        """
        pass
    
    @abstractmethod
    def get_required_columns(self) -> list:
        """
        Return list of required columns in input DataFrame.
        
        Returns:
            List of column names (e.g., ['open', 'high', 'low', 'close', 'volume'])
        """
        pass
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        Validate that input DataFrame has required columns.
        
        Args:
            df: Input DataFrame
        
        Returns:
            True if valid, False otherwise
        """
        required = self.get_required_columns()
        missing = [col for col in required if col not in df.columns]
        
        if missing:
            print(f"[{self.name}] Warning: Missing columns: {missing}")
            return False
        
        return True
    
    def get_latest_signal(self, df: pd.DataFrame) -> str:
        """
        Get the latest signal from the indicator.
        
        Args:
            df: DataFrame with signal column
        
        Returns:
            Latest signal: 'BUY', 'SELL', or 'HOLD'
        """
        if 'signal' not in df.columns:
            return 'HOLD'
        
        latest = df['signal'].iloc[-1]
        return latest if latest in ['BUY', 'SELL', 'HOLD'] else 'HOLD'
    
    def __str__(self):
        return f"{self.name} (enabled={self.enabled}, weight={self.weight})"
    
    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.name}>"
