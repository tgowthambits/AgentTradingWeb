"""
HFT Market Microstructure Indicator

Uses tick analysis, liquidity scoring, and reversal detection.
"""

import pandas as pd
import numpy as np
from engine.core.base_indicator import BaseIndicator


class HFTMicrostructureIndicator(BaseIndicator):
    """
    HFT Market Microstructure Indicator
    
    Signals:
    - BUY: Low liquidity + price drop (oversold bounce expected)
    - SELL: Low liquidity + price spike (overbought reversal expected)
    - HOLD: Normal microstructure conditions
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize HFT Microstructure indicator.
        
        Config parameters:
            lookback_period (int): Period for microstructure analysis (default: 20)
            liquidity_threshold (float): Low liquidity threshold (default: 0.2)
            price_impact_period (int): Period for price impact calculation (default: 10)
            reversal_threshold (float): Reversal detection threshold (default: 0.03)
            min_price_drop (float): Minimum price drop for BUY signal (default: 0.03)
            min_price_spike (float): Minimum price spike for SELL signal (default: 0.03)
            volume_confirmation (bool): Require volume confirmation (default: True)
            trend_confirmation (bool): Require trend confirmation (default: True)
            enabled (bool): Whether indicator is enabled (default: True)
            weight (float): Indicator weight for voting (default: 1.2)
        """
        super().__init__(config)
        
        self.lookback_period = self.config.get('lookback_period', 20)
        self.liquidity_threshold = self.config.get('liquidity_threshold', 0.2)  # More strict
        self.price_impact_period = self.config.get('price_impact_period', 10)
        self.reversal_threshold = self.config.get('reversal_threshold', 0.03)  # More strict
        self.min_price_drop = self.config.get('min_price_drop', 0.03)  # 3% minimum
        self.min_price_spike = self.config.get('min_price_spike', 0.03)  # 3% minimum
        self.volume_confirmation = self.config.get('volume_confirmation', True)
        self.trend_confirmation = self.config.get('trend_confirmation', True)
    
    def _calculate_bid_ask_bounce(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate bid-ask bounce using high-low range as proxy.
        
        Higher bounce = wider spreads = lower liquidity.
        """
        hl_range = df['high'] - df['low']
        avg_range = hl_range.rolling(window=self.lookback_period).mean()
        bounce = hl_range / (avg_range + 1e-10)
        return bounce
    
    def _calculate_price_impact(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate price impact per unit volume.
        
        Higher impact = lower liquidity.
        """
        if 'volume' not in df.columns:
            return pd.Series(0, index=df.index)
        
        price_changes = df['close'].diff().abs()
        volumes = df['volume'].replace(0, np.nan)
        
        # Price impact = |price_change| / volume
        price_impact = price_changes / (volumes + 1e-10)
        
        # Rolling average
        price_impact_ma = price_impact.rolling(window=self.price_impact_period).mean()
        
        return price_impact_ma
    
    def _calculate_liquidity_score(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate liquidity score (inverse of price impact).
        
        Higher score = better liquidity.
        """
        price_impact = self._calculate_price_impact(df)
        
        # Normalize price impact
        max_impact = price_impact.rolling(window=self.lookback_period).max()
        min_impact = price_impact.rolling(window=self.lookback_period).min()
        impact_range = max_impact - min_impact
        
        # Liquidity score (inverse, normalized to 0-1)
        liquidity = 1.0 - ((price_impact - min_impact) / (impact_range + 1e-10))
        liquidity = liquidity.clip(0, 1)
        
        return liquidity
    
    def _detect_reversal_patterns(self, df: pd.DataFrame) -> pd.Series:
        """
        Detect microstructure reversal patterns with stronger confirmation.
        
        Looks for patterns like:
        - Price spike with low volume (likely reversal)
        - Price drop with low volume (likely bounce)
        """
        if 'volume' not in df.columns:
            return pd.Series(0, index=df.index)
        
        # Price change (multiple timeframes for confirmation)
        price_change = df['close'].pct_change()
        price_change_2 = df['close'].pct_change(periods=2)  # 2-period change
        price_change_3 = df['close'].pct_change(periods=3)  # 3-period change
        
        # Volume relative to average
        avg_volume = df['volume'].rolling(window=self.lookback_period).mean()
        volume_ratio = df['volume'] / (avg_volume + 1e-10)
        
        # Volume trend (decreasing volume on move = stronger reversal signal)
        volume_trend = df['volume'].rolling(window=3).mean() / df['volume'].rolling(window=10).mean()
        
        # Reversal signal: large price move with low volume and confirmation
        reversal_signal = pd.Series(0, index=df.index)
        
        # Bullish reversal: price drop with low volume (oversold bounce)
        # Require: significant drop, low volume, and volume decreasing
        bullish_reversal = (
            (price_change < -self.reversal_threshold) &  # Current drop
            (price_change_2 < -self.reversal_threshold * 1.5) &  # Cumulative drop
            (volume_ratio < 0.6) &  # Very low volume (more strict)
            (volume_trend < 0.9)  # Volume decreasing
        )
        reversal_signal.loc[bullish_reversal] = 1
        
        # Bearish reversal: price spike with low volume (overbought reversal)
        # Require: significant spike, low volume, and volume decreasing
        bearish_reversal = (
            (price_change > self.reversal_threshold) &  # Current spike
            (price_change_2 > self.reversal_threshold * 1.5) &  # Cumulative spike
            (volume_ratio < 0.6) &  # Very low volume (more strict)
            (volume_trend < 0.9)  # Volume decreasing
        )
        reversal_signal.loc[bearish_reversal] = -1
        
        return reversal_signal
    
    def _check_trend_confirmation(self, df: pd.DataFrame) -> tuple:
        """
        Check trend confirmation using moving averages.
        
        Returns:
            (bullish_trend, bearish_trend) - boolean series
        """
        if len(df) < 20:
            return pd.Series(False, index=df.index), pd.Series(False, index=df.index)
        
        # Short and long term moving averages
        sma_short = df['close'].rolling(window=5).mean()
        sma_long = df['close'].rolling(window=20).mean()
        
        # Price above both MAs = bullish trend
        bullish_trend = (df['close'] > sma_short) & (sma_short > sma_long)
        
        # Price below both MAs = bearish trend
        bearish_trend = (df['close'] < sma_short) & (sma_short < sma_long)
        
        return bullish_trend, bearish_trend
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate microstructure signals.
        
        Args:
            df: DataFrame with 'open', 'high', 'low', 'close', 'volume' columns
        
        Returns:
            DataFrame with microstructure metrics and 'signal' column
        """
        if len(df) < self.lookback_period:
            df['signal'] = 'HOLD'
            return df
        
        # Calculate bid-ask bounce
        df['bid_ask_bounce'] = self._calculate_bid_ask_bounce(df)
        
        # Calculate price impact
        df['price_impact'] = self._calculate_price_impact(df)
        
        # Calculate liquidity score
        df['liquidity_score'] = self._calculate_liquidity_score(df)
        
        # Detect reversal patterns
        df['reversal_pattern'] = self._detect_reversal_patterns(df)
        
        # Low liquidity flag (more strict threshold)
        df['low_liquidity'] = df['liquidity_score'] < self.liquidity_threshold
        
        # Price change for reversal detection
        df['price_change_pct'] = df['close'].pct_change()
        df['price_change_2p'] = df['close'].pct_change(periods=2)
        
        # Volume confirmation
        if 'volume' in df.columns and self.volume_confirmation:
            avg_volume = df['volume'].rolling(window=self.lookback_period).mean()
            df['volume_ratio'] = df['volume'] / (avg_volume + 1e-10)
            df['volume_decreasing'] = df['volume'].rolling(window=3).mean() < df['volume'].rolling(window=10).mean()
        else:
            df['volume_ratio'] = 1.0
            df['volume_decreasing'] = True
        
        # Trend confirmation
        if self.trend_confirmation:
            bullish_trend, bearish_trend = self._check_trend_confirmation(df)
            df['bullish_trend'] = bullish_trend
            df['bearish_trend'] = bearish_trend
        else:
            df['bullish_trend'] = True
            df['bearish_trend'] = True
        
        # Generate signals
        df['signal'] = 'HOLD'
        
        # BUY conditions: Multiple confirmations required
        buy_conditions = (
            (df['low_liquidity']) &  # Low liquidity (very strict)
            (df['price_change_pct'] < -self.min_price_drop) &  # Significant price drop
            (df['price_change_2p'] < -self.min_price_drop * 1.5) &  # Cumulative drop
            (df['reversal_pattern'] == 1) &  # Bullish reversal pattern
            (df['volume_decreasing']) &  # Volume decreasing (confirmation)
            (df['volume_ratio'] < 0.7) &  # Low volume relative to average
            (df['bullish_trend'] | (~df['bearish_trend']))  # Not in strong downtrend
        )
        
        df.loc[buy_conditions, 'signal'] = 'BUY'
        
        # SELL conditions: Multiple confirmations required
        sell_conditions = (
            (df['low_liquidity']) &  # Low liquidity (very strict)
            (df['price_change_pct'] > self.min_price_spike) &  # Significant price spike
            (df['price_change_2p'] > self.min_price_spike * 1.5) &  # Cumulative spike
            (df['reversal_pattern'] == -1) &  # Bearish reversal pattern
            (df['volume_decreasing']) &  # Volume decreasing (confirmation)
            (df['volume_ratio'] < 0.7) &  # Low volume relative to average
            (df['bearish_trend'] | (~df['bullish_trend']))  # Not in strong uptrend
        )
        
        df.loc[sell_conditions, 'signal'] = 'SELL'
        
        # Fill NaN values with HOLD
        df['signal'] = df['signal'].fillna('HOLD')
        
        return df
    
    def get_required_columns(self) -> list:
        """Required columns for microstructure calculation."""
        cols = ['open', 'high', 'low', 'close']
        # Volume is optional but recommended
        return cols
