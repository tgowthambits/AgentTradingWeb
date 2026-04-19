"""
Statistical Arbitrage Indicator

Detects arbitrage opportunities through spread analysis with confidence intervals.
"""

import pandas as pd
import numpy as np
from engine.core.base_indicator import BaseIndicator
from scipy import stats


class ArbitrageStatisticalIndicator(BaseIndicator):
    """
    Statistical Arbitrage Indicator
    
    Signals:
    - BUY: Spread widens beyond 2 std dev, expect reversion
    - SELL: Spread narrows beyond threshold, expect expansion
    - HOLD: Spread within normal range
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize Statistical Arbitrage indicator.
        
        Config parameters:
            lookback_period (int): Period for spread analysis (default: 60)
            std_threshold (float): Standard deviation threshold (default: 2.0)
            confidence_level (float): Confidence level for intervals (default: 0.95)
            half_life_period (int): Period for half-life calculation (default: 20)
            min_spread_change (float): Minimum spread change to trigger signal (default: 0.01)
            enabled (bool): Whether indicator is enabled (default: True)
            weight (float): Indicator weight for voting (default: 1.3)
        """
        super().__init__(config)
        
        self.lookback_period = self.config.get('lookback_period', 60)
        self.std_threshold = self.config.get('std_threshold', 2.0)
        self.confidence_level = self.config.get('confidence_level', 0.95)
        self.half_life_period = self.config.get('half_life_period', 20)
        self.min_spread_change = self.config.get('min_spread_change', 0.01)
    
    def _calculate_half_life(self, spread: pd.Series) -> float:
        """
        Calculate half-life of mean reversion for spread.
        
        Args:
            spread: Spread time series
        
        Returns:
            Half-life in periods (or 0 if not mean-reverting)
        """
        if len(spread) < self.half_life_period:
            return 0.0
        
        # Use OLS regression: spread(t) = alpha + beta * spread(t-1)
        spread_lag = spread.shift(1).dropna()
        spread_current = spread.iloc[1:].values
        
        if len(spread_lag) < 10:
            return 0.0
        
        try:
            slope, intercept, r_value, p_value, std_err = stats.linregress(
                spread_lag.values, spread_current
            )
            
            # Half-life = -log(2) / log(beta)
            if 0 < slope < 1:
                half_life = -np.log(2) / np.log(slope)
                return max(0, min(half_life, 1000))  # Cap at reasonable value
            else:
                return 0.0
        except:
            return 0.0
    
    def _calculate_spread_metrics(self, df: pd.DataFrame) -> tuple:
        """
        Calculate spread metrics for arbitrage detection.
        
        For single symbol, uses price vs its moving average as proxy.
        """
        # Calculate spread (price vs moving average as proxy for CE/PE spread)
        ma = df['close'].rolling(window=self.lookback_period).mean()
        spread = df['close'] - ma
        spread_pct = (spread / ma) * 100  # Percentage spread
        
        # Calculate spread statistics
        spread_mean = spread_pct.rolling(window=self.lookback_period).mean()
        spread_std = spread_pct.rolling(window=self.lookback_period).std()
        
        # Z-score
        spread_z_score = (spread_pct - spread_mean) / (spread_std + 1e-10)
        
        # Confidence intervals
        z_confidence = stats.norm.ppf((1 + self.confidence_level) / 2)
        spread_upper_ci = spread_mean + (z_confidence * spread_std)
        spread_lower_ci = spread_mean - (z_confidence * spread_std)
        
        # Historical spread distribution
        spread_hist = spread_pct.rolling(window=self.lookback_period * 2).apply(
            lambda x: pd.Series(x).quantile(0.95) if len(x) > 10 else np.nan
        )
        spread_hist_lower = spread_pct.rolling(window=self.lookback_period * 2).apply(
            lambda x: pd.Series(x).quantile(0.05) if len(x) > 10 else np.nan
        )
        
        return spread, spread_pct, spread_mean, spread_std, spread_z_score, \
               spread_upper_ci, spread_lower_ci, spread_hist, spread_hist_lower
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate statistical arbitrage signals.
        
        Args:
            df: DataFrame with 'close' column
        
        Returns:
            DataFrame with arbitrage metrics and 'signal' column
        """
        if len(df) < self.lookback_period:
            df['signal'] = 'HOLD'
            return df
        
        # Calculate spread metrics
        spread, spread_pct, spread_mean, spread_std, spread_z_score, \
        spread_upper_ci, spread_lower_ci, spread_hist, spread_hist_lower = \
            self._calculate_spread_metrics(df)
        
        df['spread'] = spread
        df['spread_pct'] = spread_pct
        df['spread_mean'] = spread_mean
        df['spread_std'] = spread_std
        df['spread_z_score'] = spread_z_score
        df['spread_upper_ci'] = spread_upper_ci
        df['spread_lower_ci'] = spread_lower_ci
        
        # Calculate half-life of mean reversion
        if len(df) >= self.lookback_period * 2:
            half_life = self._calculate_half_life(spread_pct)
            df['spread_half_life'] = half_life
            df['mean_reversion_speed'] = 1.0 / (half_life + 1)  # Faster = higher value
        else:
            df['spread_half_life'] = 0
            df['mean_reversion_speed'] = 0
        
        # Spread change rate
        df['spread_change'] = spread_pct.diff()
        df['spread_change_pct'] = spread_pct.pct_change()
        
        # Generate signals
        df['signal'] = 'HOLD'
        
        # BUY conditions: Spread widens beyond threshold, expect reversion
        buy_conditions = (
            (df['spread_z_score'] < -self.std_threshold) &  # Spread below mean by >2 std
            (df['spread_pct'] < df['spread_lower_ci']) &  # Below lower confidence interval
            (df['mean_reversion_speed'] > 0.1) &  # Mean reversion is active
            (df['spread_change'].abs() > self.min_spread_change)  # Significant change
        )
        
        df.loc[buy_conditions, 'signal'] = 'BUY'
        
        # SELL conditions: Spread narrows beyond threshold, expect expansion
        sell_conditions = (
            (df['spread_z_score'] > self.std_threshold) &  # Spread above mean by >2 std
            (df['spread_pct'] > df['spread_upper_ci']) &  # Above upper confidence interval
            (df['mean_reversion_speed'] > 0.1) &  # Mean reversion is active
            (df['spread_change'].abs() > self.min_spread_change)  # Significant change
        )
        
        df.loc[sell_conditions, 'signal'] = 'SELL'
        
        # Fill NaN values with HOLD
        df['signal'] = df['signal'].fillna('HOLD')
        
        return df
    
    def get_required_columns(self) -> list:
        """Required columns for arbitrage calculation."""
        return ['close']
