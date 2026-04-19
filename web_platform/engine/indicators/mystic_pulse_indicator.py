"""
Mystic Pulse V2.0 Indicator

Refactored from Pine Script by chervolino.
Based on ADX with directional movement tracking and trend counting.

Original: https://www.tradingview.com/script/...
"""

import pandas as pd
import numpy as np
from engine.core.base_indicator import BaseIndicator


class MysticPulseIndicator(BaseIndicator):
    """
    Mystic Pulse V2.0 - ADX-based trend counter indicator.
    
    Tracks positive and negative trend counts based on directional
    movement indicators (DI+ and DI-) to generate trading signals.
    
    Signal Logic:
    - BUY: When positive_count dominates (positive trend)
    - SELL: When negative_count dominates (negative trend)
    - HOLD: When trend is weak or transitioning
    """
    
    def __init__(self, config=None):
        super().__init__(config)
        
        # Smoothing parameters (use self.config which is set by BaseIndicator)
        self.adx_length = self.config.get('adx_length', 9)
        self.smoothing_factor = self.config.get('smoothing_factor', 1)
        
        # Signal thresholds
        self.buy_threshold = self.config.get('buy_threshold', 2)
        self.sell_threshold = self.config.get('sell_threshold', 2)
        self.min_trend_score = self.config.get('min_trend_score', 3)
        
        # Gradient/normalization window
        self.collect_length = self.config.get('collect_length', 100)
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Mystic Pulse indicator and generate signals.
        
        Args:
            df: DataFrame with OHLC data
        
        Returns:
            DataFrame with indicator columns and signals
        """
        df = df.copy()
        
        # Step 1: Pre-smooth OHLC data
        df['open_s'] = df['open'].rolling(window=self.smoothing_factor).mean()
        df['high_s'] = df['high'].rolling(window=self.smoothing_factor).mean()
        df['low_s'] = df['low'].rolling(window=self.smoothing_factor).mean()
        df['close_s'] = df['close'].rolling(window=self.smoothing_factor).mean()
        
        # Step 2: Calculate True Range and Directional Movement
        df['tr'] = self._calculate_true_range(df)
        df['dm_plus'] = self._calculate_dm_plus(df)
        df['dm_minus'] = self._calculate_dm_minus(df)
        
        # Step 3: Wilder smoothing (exponential moving average)
        df['smoothed_tr'] = self._wilder_smoothing(df['tr'], self.adx_length)
        df['smoothed_dm_plus'] = self._wilder_smoothing(df['dm_plus'], self.adx_length)
        df['smoothed_dm_minus'] = self._wilder_smoothing(df['dm_minus'], self.adx_length)
        
        # Step 4: Calculate Directional Indicators (DI+ and DI-)
        df['di_plus'] = (df['smoothed_dm_plus'] / df['smoothed_tr']) * 100
        df['di_minus'] = (df['smoothed_dm_minus'] / df['smoothed_tr']) * 100
        
        # Step 5: Calculate trend counts (core logic)
        df = self._calculate_trend_counts(df)
        
        # Step 6: Calculate trend score
        df['trend_score'] = df['positive_count'] - df['negative_count']
        
        # Step 7: Generate signals
        df['signal'] = self._generate_signals(df)
        
        return df
    
    def _calculate_true_range(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate True Range (TR).
        
        TR = max(high - low, abs(high - prev_close), abs(low - prev_close))
        """
        prev_close = df['close_s'].shift(1)
        
        tr1 = df['high_s'] - df['low_s']
        tr2 = (df['high_s'] - prev_close).abs()
        tr3 = (df['low_s'] - prev_close).abs()
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        return true_range
    
    def _calculate_dm_plus(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate Positive Directional Movement (DM+).
        
        DM+ = (high - prev_high) if (high - prev_high) > (prev_low - low) else 0
        """
        high_diff = df['high_s'] - df['high_s'].shift(1)
        low_diff = df['low_s'].shift(1) - df['low_s']
        
        dm_plus = np.where(
            high_diff > low_diff,
            np.maximum(high_diff, 0),
            0
        )
        
        return pd.Series(dm_plus, index=df.index)
    
    def _calculate_dm_minus(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate Negative Directional Movement (DM-).
        
        DM- = (prev_low - low) if (prev_low - low) > (high - prev_high) else 0
        """
        high_diff = df['high_s'] - df['high_s'].shift(1)
        low_diff = df['low_s'].shift(1) - df['low_s']
        
        dm_minus = np.where(
            low_diff > high_diff,
            np.maximum(low_diff, 0),
            0
        )
        
        return pd.Series(dm_minus, index=df.index)
    
    def _wilder_smoothing(self, series: pd.Series, period: int) -> pd.Series:
        """
        Apply Wilder's smoothing (modified exponential moving average).
        
        Wilder's smoothing: new_value = prev_smooth - (prev_smooth / period) + current_value
        This is equivalent to EMA with alpha = 1/period
        """
        # Using EMA with alpha = 1/period is equivalent to Wilder smoothing
        alpha = 1.0 / period
        return series.ewm(alpha=alpha, adjust=False).mean()
    
    def _calculate_trend_counts(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate positive and negative trend counts.
        
        Core logic from Pine Script:
        - If DI+ is rising and DI+ > DI-: increment positive_count, reset negative_count
        - If DI- is rising and DI- > DI+: increment negative_count, reset positive_count
        """
        positive_count = []
        negative_count = []
        
        pos_cnt = 0
        neg_cnt = 0
        
        for i in range(len(df)):
            if i == 0:
                positive_count.append(0)
                negative_count.append(0)
                continue
            
            di_plus_curr = df['di_plus'].iloc[i]
            di_plus_prev = df['di_plus'].iloc[i-1]
            di_minus_curr = df['di_minus'].iloc[i]
            di_minus_prev = df['di_minus'].iloc[i-1]
            
            # Check if DI+ is rising and dominant
            if (not pd.isna(di_plus_curr) and not pd.isna(di_plus_prev) and
                di_plus_curr > di_plus_prev and di_plus_curr > di_minus_curr):
                pos_cnt += 1
                neg_cnt = 0
            
            # Check if DI- is rising and dominant
            elif (not pd.isna(di_minus_curr) and not pd.isna(di_minus_prev) and
                  di_minus_curr > di_minus_prev and di_minus_curr > di_plus_curr):
                neg_cnt += 1
                pos_cnt = 0
            
            positive_count.append(pos_cnt)
            negative_count.append(neg_cnt)
        
        df['positive_count'] = positive_count
        df['negative_count'] = negative_count
        
        return df
    
    def _generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate BUY/SELL/HOLD signals based on trend counts and trend score.
        
        Logic:
        - BUY: positive_count >= buy_threshold AND trend_score > min_trend_score
        - SELL: negative_count >= sell_threshold AND trend_score < -min_trend_score
        - HOLD: Otherwise
        """
        signals = []
        
        for i in range(len(df)):
            pos_cnt = df['positive_count'].iloc[i]
            neg_cnt = df['negative_count'].iloc[i]
            trend_score = df['trend_score'].iloc[i]
            
            # BUY signal: strong positive trend
            if pos_cnt >= self.buy_threshold and trend_score > self.min_trend_score:
                signals.append('BUY')
            
            # SELL signal: strong negative trend
            elif neg_cnt >= self.sell_threshold and trend_score < -self.min_trend_score:
                signals.append('SELL')
            
            # HOLD: weak or transitioning trend
            else:
                signals.append('HOLD')
        
        return pd.Series(signals, index=df.index)
    
    def get_required_columns(self) -> list:
        """Return list of required DataFrame columns."""
        return ['open', 'high', 'low', 'close']
    
    def get_indicator_values(self, df: pd.DataFrame) -> dict:
        """
        Get current indicator values for display.
        
        Args:
            df: DataFrame with calculated indicators
        
        Returns:
            Dict with current values
        """
        if len(df) == 0:
            return {}
        
        last_row = df.iloc[-1]
        
        return {
            'di_plus': round(last_row.get('di_plus', 0), 2),
            'di_minus': round(last_row.get('di_minus', 0), 2),
            'positive_count': int(last_row.get('positive_count', 0)),
            'negative_count': int(last_row.get('negative_count', 0)),
            'trend_score': int(last_row.get('trend_score', 0)),
            'signal': last_row.get('signal', 'HOLD')
        }
    
    def __str__(self):
        return f"MysticPulse(adx={self.adx_length}, smooth={self.smoothing_factor})"
    
    def __repr__(self):
        return (f"<MysticPulseIndicator: adx_length={self.adx_length}, "
                f"smoothing_factor={self.smoothing_factor}, "
                f"buy_threshold={self.buy_threshold}, "
                f"sell_threshold={self.sell_threshold}>")
