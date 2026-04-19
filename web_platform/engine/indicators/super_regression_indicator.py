"""
Super Regression Trend Strategy Indicator

Converts PineScript "Super Regression Trend Strategy" to Python.
Uses linear regression with RMSE bands and trailing band logic.

Signals:
- BUY: Trend flips to 1 (upward) when price crosses above lower band
- SELL: Trend flips to -1 (downward) when price crosses below upper band
- HOLD: Otherwise
"""

import pandas as pd
import numpy as np
from engine.core.base_indicator import BaseIndicator


class SuperRegressionIndicator(BaseIndicator):
    """
    Super Regression Trend Strategy Indicator
    
    Based on linear regression with RMSE bands and trailing logic.
    
    Signals:
    - BUY: Trend flips to upward (trend == 1)
    - SELL: Trend flips to downward (trend == -1)
    - HOLD: No trend flip
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize Super Regression indicator.
        
        Config parameters:
            len (int): Regression length (default: 20)
            mult (float): RMSE multiplier (default: 2.0)
            source (str): Source column - 'close', 'open', 'high', 'low' (default: 'close')
            enabled (bool): Whether indicator is enabled (default: True)
            weight (float): Indicator weight for voting (default: 1.0)
        """
        super().__init__(config)
        
        self.len = self.config.get('len', 20)
        self.mult = self.config.get('mult', 2.0)
        self.source_col = self.config.get('source', 'close')
        
        # State variables for trailing bands (persist across calculations)
        self._upper_band_state = None
        self._lower_band_state = None
        self._trend_state = 1  # 1 = upward, -1 = downward
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Super Regression Trend indicator and generate signals.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with 'regression', 'upper_band', 'lower_band', 'trend', and 'signal' columns
        """
        if len(df) < self.len:
            df['signal'] = 'HOLD'
            return df
        
        # Get source column
        src = df[self.source_col].values
        
        # Initialize arrays
        n = len(df)
        regression = np.full(n, np.nan)
        rmse = np.full(n, np.nan)
        upper_raw = np.full(n, np.nan)
        lower_raw = np.full(n, np.nan)
        upper = np.full(n, np.nan)
        lower = np.full(n, np.nan)
        trend = np.full(n, 1, dtype=int)  # Default to upward trend
        signal = np.full(n, 'HOLD', dtype=object)
        
        # Calculate for each bar starting from len
        for i in range(self.len - 1, n):
            # Get window of data
            window = src[i - self.len + 1:i + 1]
            x = np.arange(len(window))
            
            # Linear regression: y = ax + b
            slope, intercept = np.polyfit(x, window, 1)
            reg_value = intercept + slope * (len(window) - 1)  # Value at current bar
            regression[i] = reg_value
            
            # Calculate RMSE (Root Mean Squared Error)
            reg_line = intercept + slope * x
            errors = window - reg_line
            mse = np.mean(errors ** 2)
            rmse_value = np.sqrt(mse)
            rmse[i] = rmse_value
            
            # Raw bands
            upper_raw[i] = reg_value + rmse_value * self.mult
            lower_raw[i] = reg_value - rmse_value * self.mult
            
            # Trailing bands logic
            if i == self.len - 1:
                # First calculation
                upper[i] = upper_raw[i]
                lower[i] = lower_raw[i]
                trend[i] = 1
                # Update state
                self._upper_band_state = upper[i]
                self._lower_band_state = lower[i]
                self._trend_state = trend[i]
            else:
                prev_trend = self._trend_state
                prev_upper = self._upper_band_state
                prev_lower = self._lower_band_state
                
                # Update upper band (trailing)
                if prev_trend == -1:
                    # In downward trend, upper band only moves down
                    upper[i] = min(upper_raw[i], prev_upper)
                else:
                    # In upward trend, upper band follows raw
                    upper[i] = upper_raw[i]
                
                # Update lower band (trailing)
                if prev_trend == 1:
                    # In upward trend, lower band only moves up
                    lower[i] = max(lower_raw[i], prev_lower)
                else:
                    # In downward trend, lower band follows raw
                    lower[i] = lower_raw[i]
                
                # Trend flip detection
                current_price = src[i]
                
                if prev_trend == 1 and current_price < lower[i]:
                    # Flip from upward to downward
                    trend[i] = -1
                elif prev_trend == -1 and current_price > upper[i]:
                    # Flip from downward to upward
                    trend[i] = 1
                else:
                    # No flip, maintain previous trend
                    trend[i] = prev_trend
                
                # Update state
                self._upper_band_state = upper[i]
                self._lower_band_state = lower[i]
                self._trend_state = trend[i]
                
                # Detect trend flip for signal generation
                if trend[i] != prev_trend:
                    if trend[i] == 1:
                        signal[i] = 'BUY'
                    elif trend[i] == -1:
                        signal[i] = 'SELL'
                else:
                    signal[i] = 'HOLD'
        
        # Store results in DataFrame
        df['regression'] = regression
        df['rmse'] = rmse
        df['upper_raw'] = upper_raw
        df['lower_raw'] = lower_raw
        df['upper_band'] = upper
        df['lower_band'] = lower
        df['trend'] = trend
        df['signal'] = signal
        
        return df
    
    def get_required_columns(self) -> list:
        """Required columns for Super Regression calculation."""
        return [self.source_col]
