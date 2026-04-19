"""
HFT Order Flow Indicator

Uses Order Flow Imbalance (OFI), cumulative delta, and volume-weighted order flow.
"""

import pandas as pd
import numpy as np
from trading_system.core.base_indicator import BaseIndicator


class HFTOrderFlowIndicator(BaseIndicator):
    """
    HFT Order Flow Indicator
    
    Signals:
    - BUY: Strong buying pressure (OFI > 0.3) with volume confirmation
    - SELL: Strong selling pressure (OFI < -0.3) with volume confirmation
    - HOLD: Balanced order flow
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize HFT Order Flow indicator.
        
        Config parameters:
            ofi_threshold (float): OFI threshold for signals (default: 0.3)
            lookback_period (int): Period for volume analysis (default: 20)
            cumulative_delta_period (int): Period for cumulative delta (default: 20)
            volume_confirmation_multiplier (float): Volume spike multiplier (default: 1.5)
            enabled (bool): Whether indicator is enabled (default: True)
            weight (float): Indicator weight for voting (default: 1.5)
        """
        super().__init__(config)
        
        self.ofi_threshold = self.config.get('ofi_threshold', 0.3)
        self.lookback_period = self.config.get('lookback_period', 20)
        self.cumulative_delta_period = self.config.get('cumulative_delta_period', 20)
        self.volume_confirmation_multiplier = self.config.get('volume_confirmation_multiplier', 1.5)
    
    def _estimate_buy_sell_volume(self, df: pd.DataFrame) -> tuple:
        """
        Estimate buy and sell volume from OHLCV data.
        
        Uses tick rule: if close > open, more buying; if close < open, more selling.
        """
        # Tick rule: price up = buying pressure, price down = selling pressure
        price_change = df['close'] - df['open']
        price_range = df['high'] - df['low']
        
        # Avoid division by zero
        price_range = price_range.replace(0, np.nan)
        
        # Estimate buy/sell volume based on price movement
        # If price went up, assume more buying; if down, more selling
        buy_volume_ratio = np.where(
            price_range > 0,
            np.maximum(0, np.minimum(1, (price_change + price_range) / (2 * price_range))),
            0.5
        )
        
        buy_volume = df['volume'] * buy_volume_ratio
        sell_volume = df['volume'] * (1 - buy_volume_ratio)
        
        return buy_volume, sell_volume
    
    def _calculate_order_flow_imbalance(self, buy_volume: pd.Series, sell_volume: pd.Series) -> pd.Series:
        """
        Calculate Order Flow Imbalance (OFI).
        
        OFI = (Buy Volume - Sell Volume) / (Buy Volume + Sell Volume)
        """
        total_volume = buy_volume + sell_volume
        ofi = (buy_volume - sell_volume) / (total_volume + 1e-10)
        return ofi
    
    def _calculate_cumulative_delta(self, buy_volume: pd.Series, sell_volume: pd.Series) -> pd.Series:
        """
        Calculate cumulative delta (cumulative buy volume - cumulative sell volume).
        """
        delta = buy_volume - sell_volume
        cumulative_delta = delta.rolling(window=self.cumulative_delta_period).sum()
        return cumulative_delta
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate order flow signals.
        
        Args:
            df: DataFrame with 'open', 'high', 'low', 'close', 'volume' columns
        
        Returns:
            DataFrame with order flow metrics and 'signal' column
        """
        if len(df) < self.lookback_period:
            df['signal'] = 'HOLD'
            return df
        
        if 'volume' not in df.columns:
            df['signal'] = 'HOLD'
            return df
        
        # Estimate buy/sell volume
        buy_volume, sell_volume = self._estimate_buy_sell_volume(df)
        
        df['buy_volume'] = buy_volume
        df['sell_volume'] = sell_volume
        
        # Calculate Order Flow Imbalance (OFI)
        df['ofi'] = self._calculate_order_flow_imbalance(buy_volume, sell_volume)
        
        # Calculate cumulative delta
        df['cumulative_delta'] = self._calculate_cumulative_delta(buy_volume, sell_volume)
        
        # Volume-weighted order flow
        df['volume_weighted_flow'] = df['ofi'] * df['volume']
        df['volume_weighted_flow_ma'] = df['volume_weighted_flow'].rolling(window=self.lookback_period).mean()
        
        # Order flow momentum (rate of change of OFI)
        df['ofi_momentum'] = df['ofi'].diff(periods=3)
        
        # Volume confirmation
        avg_volume = df['volume'].rolling(window=self.lookback_period).mean()
        df['volume_spike'] = df['volume'] > (avg_volume * self.volume_confirmation_multiplier)
        
        # Normalized cumulative delta
        max_delta = df['cumulative_delta'].rolling(window=self.lookback_period).max()
        min_delta = df['cumulative_delta'].rolling(window=self.lookback_period).min()
        delta_range = max_delta - min_delta
        df['normalized_delta'] = (df['cumulative_delta'] - min_delta) / (delta_range + 1e-10)
        
        # Generate signals
        df['signal'] = 'HOLD'
        
        # BUY conditions: Strong buying pressure with volume confirmation
        buy_conditions = (
            (df['ofi'] > self.ofi_threshold) &  # Strong buying pressure
            (df['cumulative_delta'] > 0) &  # Positive cumulative delta
            (df['normalized_delta'] > 0.6) &  # High normalized delta
            (df['ofi_momentum'] > 0) &  # Increasing buying pressure
            (df['volume_spike'])  # Volume confirmation
        )
        
        df.loc[buy_conditions, 'signal'] = 'BUY'
        
        # SELL conditions: Strong selling pressure with volume confirmation
        sell_conditions = (
            (df['ofi'] < -self.ofi_threshold) &  # Strong selling pressure
            (df['cumulative_delta'] < 0) &  # Negative cumulative delta
            (df['normalized_delta'] < 0.4) &  # Low normalized delta
            (df['ofi_momentum'] < 0) &  # Increasing selling pressure
            (df['volume_spike'])  # Volume confirmation
        )
        
        df.loc[sell_conditions, 'signal'] = 'SELL'
        
        # Fill NaN values with HOLD
        df['signal'] = df['signal'].fillna('HOLD')
        
        return df
    
    def get_required_columns(self) -> list:
        """Required columns for order flow calculation."""
        return ['open', 'high', 'low', 'close', 'volume']

