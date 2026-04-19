"""
Statistical Cointegration Indicator

Uses Engle-Granger cointegration test and spread analysis for pairs trading (CE/PE).
"""

import pandas as pd
import numpy as np
from engine.core.base_indicator import BaseIndicator
from scipy import stats


class StatisticalCointegrationIndicator(BaseIndicator):
    """
    Statistical Cointegration Indicator
    
    Signals:
    - BUY: Spread significantly below mean (pairs trading opportunity)
    - SELL: Spread significantly above mean
    - HOLD: No cointegration or spread near mean
    
    Note: This indicator requires access to related symbols (e.g., CE/PE pairs).
    For single-symbol analysis, it will use price vs its own moving average as a proxy.
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize Statistical Cointegration indicator.
        
        Config parameters:
            lookback_period (int): Period for spread analysis (default: 60)
            z_score_threshold (float): Z-score threshold for signals (default: 2.0)
            cointegration_window (int): Window for cointegration test (default: 100)
            hedge_ratio_period (int): Period for hedge ratio calculation (default: 60)
            min_cointegration_pvalue (float): Max p-value for cointegration (default: 0.05)
            enabled (bool): Whether indicator is enabled (default: True)
            weight (float): Indicator weight for voting (default: 1.2)
        """
        super().__init__(config)
        
        self.lookback_period = self.config.get('lookback_period', 60)
        self.z_score_threshold = self.config.get('z_score_threshold', 2.0)
        self.cointegration_window = self.config.get('cointegration_window', 100)
        self.hedge_ratio_period = self.config.get('hedge_ratio_period', 60)
        self.min_cointegration_pvalue = self.config.get('min_cointegration_pvalue', 0.05)
    
    def _engle_granger_test(self, x: np.ndarray, y: np.ndarray) -> tuple:
        """
        Simplified Engle-Granger cointegration test.
        
        Args:
            x: First time series
            y: Second time series
        
        Returns:
            (is_cointegrated, p_value, hedge_ratio)
        """
        if len(x) != len(y) or len(x) < 10:
            return False, 1.0, 1.0
        
        # Calculate hedge ratio using OLS regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        hedge_ratio = slope
        
        # Calculate spread
        spread = y - (hedge_ratio * x + intercept)
        
        # Test spread for stationarity (ADF test approximation)
        # Simplified: check if spread is mean-reverting
        spread_diff = np.diff(spread)
        spread_mean = np.mean(spread)
        spread_std = np.std(spread)
        
        # If spread is stationary, it should have mean near 0 and low variance
        # Check if spread is significantly different from mean
        z_scores = (spread - spread_mean) / (spread_std + 1e-10)
        mean_reversion_score = 1.0 - np.mean(np.abs(z_scores)) / 3.0  # Higher = more mean-reverting
        
        # Cointegrated if mean_reversion_score > 0.5
        is_cointegrated = mean_reversion_score > 0.5
        p_value_approx = 1.0 - mean_reversion_score
        
        return is_cointegrated, p_value_approx, hedge_ratio
    
    def _calculate_spread_vs_ma(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate spread between price and its moving average as a proxy for pairs trading.
        
        This is used when we don't have access to a paired instrument.
        """
        # Use price vs its own moving average as spread proxy
        ma = df['close'].rolling(window=self.hedge_ratio_period).mean()
        spread = df['close'] - ma
        
        # Calculate spread statistics
        spread_mean = spread.rolling(window=self.lookback_period).mean()
        spread_std = spread.rolling(window=self.lookback_period).std()
        spread_z_score = (spread - spread_mean) / (spread_std + 1e-10)
        
        return spread, spread_mean, spread_std, spread_z_score
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate cointegration signals.
        
        Args:
            df: DataFrame with 'close' column
        
        Returns:
            DataFrame with cointegration metrics and 'signal' column
        """
        if len(df) < self.lookback_period:
            df['signal'] = 'HOLD'
            return df
        
        # For now, use price vs moving average as proxy for spread
        # In a full implementation, this would compare CE vs PE prices
        spread, spread_mean, spread_std, spread_z_score = self._calculate_spread_vs_ma(df)
        
        df['spread'] = spread
        df['spread_mean'] = spread_mean
        df['spread_std'] = spread_std
        df['spread_z_score'] = spread_z_score
        
        # Calculate half-life of mean reversion (how long spread takes to revert)
        # Simplified: use autocorrelation of spread
        if len(df) >= self.lookback_period * 2:
            spread_diff = spread.diff().dropna()
            if len(spread_diff) > 10:
                autocorr = spread_diff.autocorr(lag=1)
                # Negative autocorr indicates mean reversion
                df['mean_reversion_strength'] = -autocorr if autocorr < 0 else 0
            else:
                df['mean_reversion_strength'] = 0
        else:
            df['mean_reversion_strength'] = 0
        
        # Cointegration test (simplified for single symbol)
        # In real implementation, would test CE vs PE
        df['is_cointegrated'] = df['mean_reversion_strength'] > 0.3
        
        # Generate signals
        df['signal'] = 'HOLD'
        
        # BUY conditions: Spread significantly below mean (expect reversion up)
        buy_conditions = (
            (df['spread_z_score'] < -self.z_score_threshold) &  # Spread below mean
            (df['is_cointegrated']) &  # Cointegration exists
            (df['mean_reversion_strength'] > 0.2)  # Strong mean reversion
        )
        
        df.loc[buy_conditions, 'signal'] = 'BUY'
        
        # SELL conditions: Spread significantly above mean (expect reversion down)
        sell_conditions = (
            (df['spread_z_score'] > self.z_score_threshold) &  # Spread above mean
            (df['is_cointegrated']) &  # Cointegration exists
            (df['mean_reversion_strength'] > 0.2)  # Strong mean reversion
        )
        
        df.loc[sell_conditions, 'signal'] = 'SELL'
        
        # Fill NaN values with HOLD
        df['signal'] = df['signal'].fillna('HOLD')
        
        return df
    
    def get_required_columns(self) -> list:
        """Required columns for cointegration calculation."""
        return ['close']
