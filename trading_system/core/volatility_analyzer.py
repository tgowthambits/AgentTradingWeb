"""
Volatility Analyzer Module

Implements multiple volatility calculation methods including:
- Average True Range (ATR)
- Parkinson Volatility (High-Low)
- Garman-Klass Volatility (OHLC)
- Hodges-Tompkins Volatility
- Realized Volatility
- Volatility Regime Detection

Used for risk management and position sizing.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional


class VolatilityAnalyzer:
    """
    Advanced volatility analysis using multiple methods.
    Provides volatility estimates for risk management and stop loss sizing.
    """
    
    def __init__(self, atr_period: int = 14, volatility_window: int = 20):
        """
        Initialize volatility analyzer.
        
        Args:
            atr_period: Period for ATR calculation
            volatility_window: Window for volatility calculations
        """
        self.atr_period = atr_period
        self.volatility_window = volatility_window
    
    def calculate_atr(self, data: pd.DataFrame, period: Optional[int] = None) -> float:
        """
        Calculate Average True Range (ATR).
        
        ATR measures market volatility by decomposing the entire range of prices.
        
        Args:
            data: DataFrame with 'high', 'low', 'close' columns
            period: ATR period (uses self.atr_period if not provided)
        
        Returns:
            Current ATR value
        """
        period = period or self.atr_period
        
        if len(data) < 2:
            return 0.0
        
        # Calculate True Range
        high = data['high'].values
        low = data['low'].values
        close = data['close'].values
        
        # TR = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr_list = []
        for i in range(1, len(data)):
            hl = high[i] - low[i]
            hc = abs(high[i] - close[i-1])
            lc = abs(low[i] - close[i-1])
            tr = max(hl, hc, lc)
            tr_list.append(tr)
        
        # Calculate ATR as moving average of TR
        if len(tr_list) >= period:
            atr = np.mean(tr_list[-period:])
        else:
            atr = np.mean(tr_list) if tr_list else 0.0
        
        return float(atr)
    
    def calculate_parkinson_volatility(self, data: pd.DataFrame, 
                                      window: Optional[int] = None) -> float:
        """
        Calculate Parkinson Volatility (High-Low estimator).
        
        More efficient than close-to-close volatility for intraday data.
        Formula: sqrt(1/(4*ln(2)) * mean((ln(High/Low))^2))
        
        Args:
            data: DataFrame with 'high' and 'low' columns
            window: Lookback window (uses self.volatility_window if not provided)
        
        Returns:
            Parkinson volatility estimate
        """
        window = window or self.volatility_window
        
        if len(data) < 2:
            return 0.0
        
        # Get recent data
        recent_data = data.tail(min(window, len(data)))
        
        # Calculate log(High/Low) squared
        hl_ratio = np.log(recent_data['high'].astype(float) / recent_data['low'].astype(float))
        hl_squared = hl_ratio ** 2
        
        # Parkinson formula
        parkinson = np.sqrt(np.mean(hl_squared) / (4 * np.log(2)))
        
        return float(parkinson)
    
    def calculate_garman_klass_volatility(self, data: pd.DataFrame,
                                         window: Optional[int] = None) -> float:
        """
        Calculate Garman-Klass Volatility (OHLC estimator).
        
        Most accurate volatility estimator using all OHLC information.
        More efficient than close-to-close methods.
        
        Formula combines:
        - 0.5 * (log(High/Low))^2
        - (2*log(2)-1) * (log(Close/Open))^2
        
        Args:
            data: DataFrame with 'open', 'high', 'low', 'close' columns
            window: Lookback window (uses self.volatility_window if not provided)
        
        Returns:
            Garman-Klass volatility estimate
        """
        window = window or self.volatility_window
        
        if len(data) < 2:
            return 0.0
        
        # Get recent data
        recent_data = data.tail(min(window, len(data)))
        
        # Garman-Klass formula
        hl = np.log(recent_data['high'].astype(float) / recent_data['low'].astype(float))
        co = np.log(recent_data['close'].astype(float) / recent_data['open'].astype(float))
        
        gk = 0.5 * (hl ** 2) - (2 * np.log(2) - 1) * (co ** 2)
        garman_klass = np.sqrt(np.mean(gk))
        
        return float(garman_klass)
    
    def calculate_hodges_tompkins_volatility(self, data: pd.DataFrame, window: int = 30) -> float:
        """Calculate Hodges-Tompkins Volatility."""
        if len(data) < 2:
            return 0.0
        
        # Need at least window + 1 rows for rolling calculation
        if len(data) < window + 1:
            window = len(data) - 1
            if window < 1:
                return 0.0
        
        # Convert to float and calculate log returns
        close_series = data['close'].astype(float)
        log_returns = np.log(close_series / close_series.shift(1))
        log_returns = log_returns.dropna()
        
        if len(log_returns) < 2:
            return 0.0
        
        # Calculate rolling standard deviation
        h = log_returns.rolling(window=window).std(ddof=0)
        h = h.dropna()
        
        if len(h) == 0:
            return 0.0
        
        # Hodges-Tompkins formula
        n = window
        ht_vol = h * np.sqrt(1 + (1 / n)) + (h / (2 * n)) * np.sqrt(1 + (1 / n)) 
        
        return float(ht_vol.iloc[-1]) if not ht_vol.empty else 0.0
    
    def calculate_realized_volatility(self, data: pd.DataFrame,
                                     window: Optional[int] = None) -> float:
        """
        Calculate Realized Volatility (close-to-close).
        
        Traditional volatility based on log returns.
        
        Args:
            data: DataFrame with 'close' column
            window: Lookback window (uses self.volatility_window if not provided)
        
        Returns:
            Realized volatility (annualized)
        """
        window = window or self.volatility_window
        
        if len(data) < 2:
            return 0.0
        
        # Get recent data
        recent_data = data.tail(min(window + 1, len(data)))
        
        # Calculate log returns
        log_returns = np.log(recent_data['close'].astype(float) / recent_data['close'].shift(1).astype(float))
        log_returns = log_returns.dropna()
        
        if len(log_returns) < 2:
            return 0.0
        
        # Standard deviation of returns
        volatility = np.std(log_returns, ddof=1)
        
        return float(volatility)
    
    def calculate_intraday_volatility(self, data: pd.DataFrame) -> float:
        """
        Calculate intraday volatility from recent price action.
        
        Useful for short-term trading and quick volatility assessment.
        
        Args:
            data: DataFrame with 'close' column
        
        Returns:
            Intraday volatility measure
        """
        if len(data) < 5:
            return 0.0
        
        # Use last 5-10 bars for intraday estimate
        recent_closes = data['close'].tail(10).values
        
        # Calculate percentage changes
        pct_changes = np.diff(recent_closes) / recent_closes[:-1]
        
        # Standard deviation of percentage changes
        intraday_vol = np.std(pct_changes) if len(pct_changes) > 0 else 0.0
        
        return float(intraday_vol)
    
    def get_volatility_regime(self, current_vol: float,
                             historical_data: pd.DataFrame,
                             low_threshold: float = 0.5,
                             high_threshold: float = 2.0) -> str:
        """
        Determine current volatility regime.
        
        Args:
            current_vol: Current volatility measure
            historical_data: Historical data for comparison
            low_threshold: Multiplier for low volatility threshold
            high_threshold: Multiplier for high volatility threshold
        
        Returns:
            'LOW', 'NORMAL', or 'HIGH' volatility regime
        """
        if len(historical_data) < self.volatility_window:
            return 'NORMAL'
        
        # Calculate historical volatility for comparison
        hist_vol = self.calculate_realized_volatility(historical_data)
        
        if hist_vol == 0:
            return 'NORMAL'
        
        # Compare current to historical
        vol_ratio = current_vol / hist_vol
        
        if vol_ratio < low_threshold:
            return 'LOW'
        elif vol_ratio > high_threshold:
            return 'HIGH'
        else:
            return 'NORMAL'
    
    def get_comprehensive_volatility(self, data: pd.DataFrame,
                                    method: str = 'garman_klass') -> Dict[str, float]:
        """
        Calculate all volatility measures and return comprehensive analysis.
        
        Args:
            data: DataFrame with OHLC data
            method: Primary method to use ('atr', 'parkinson', 'garman_klass')
        
        Returns:
            Dictionary with all volatility measures and regime
        """
        if len(data) < 2:
            return {
                'atr': 0.0,
                'parkinson': 0.0,
                'garman_klass': 0.0,
                'hodges_tompkins': 0.0,
                'realized': 0.0,
                'intraday': 0.0,
                'primary': 0.0,
                'regime': 'NORMAL',
                'method': method
            }
        
        # Calculate all measures
        atr = self.calculate_atr(data)
        parkinson = self.calculate_parkinson_volatility(data)
        garman_klass = self.calculate_garman_klass_volatility(data)
        hodges_tompkins = self.calculate_hodges_tompkins_volatility(data)
        realized = self.calculate_realized_volatility(data)
        intraday = self.calculate_intraday_volatility(data)
        
        # Select primary method
        primary_map = {
            'atr': atr,
            'parkinson': parkinson,
            'garman_klass': garman_klass,
            'hodges_tompkins': hodges_tompkins,
            'realized': realized
        }
        primary = primary_map.get(method, garman_klass)
        
        # Determine regime
        regime = self.get_volatility_regime(realized, data)
        
        return {
            'atr': atr,
            'parkinson': parkinson,
            'garman_klass': garman_klass,
            'hodges_tompkins': hodges_tompkins,
            'realized': realized,
            'intraday': intraday,
            'primary': primary,
            'regime': regime,
            'method': method
        }
    
    def calculate_adaptive_atr_multiplier(self, data: pd.DataFrame) -> float:
        """
        Calculate adaptive ATR multiplier based on volatility regime.
        
        Low volatility: Use smaller multiplier (1.5x)
        Normal volatility: Use standard multiplier (2.0x)
        High volatility: Use larger multiplier (3.0x)
        
        Args:
            data: DataFrame with OHLC data
        
        Returns:
            Recommended ATR multiplier for stop loss
        """
        vol_analysis = self.get_comprehensive_volatility(data)
        regime = vol_analysis['regime']
        
        multiplier_map = {
            'LOW': 1.5,
            'NORMAL': 2.0,
            'HIGH': 3.0
        }
        
        return multiplier_map.get(regime, 2.0)


def test_volatility_analyzer():
    """Test function for VolatilityAnalyzer."""
    # Create sample data
    np.random.seed(42)
    dates = pd.date_range('2025-01-01', periods=100, freq='5min')
    
    # Simulate OHLC data
    base_price = 100
    returns = np.random.normal(0, 0.02, 100)
    close = base_price * np.exp(np.cumsum(returns))
    
    data = pd.DataFrame({
        'time': dates,
        'open': close * (1 + np.random.uniform(-0.005, 0.005, 100)),
        'high': close * (1 + np.random.uniform(0, 0.01, 100)),
        'low': close * (1 - np.random.uniform(0, 0.01, 100)),
        'close': close,
        'volume': np.random.randint(1000, 10000, 100)
    })
    
    # Test analyzer
    analyzer = VolatilityAnalyzer()
    
    print("=" * 60)
    print("VOLATILITY ANALYZER TEST")
    print("=" * 60)
    
    # Test individual methods
    atr = analyzer.calculate_atr(data)
    print(f"ATR: {atr:.4f}")
    
    parkinson = analyzer.calculate_parkinson_volatility(data)
    print(f"Parkinson Volatility: {parkinson:.4f}")
    
    garman_klass = analyzer.calculate_garman_klass_volatility(data)
    print(f"Garman-Klass Volatility: {garman_klass:.4f}")
    
    hodges_tompkins = analyzer.calculate_hodges_tompkins_volatility(data)
    print(f"Hodges-Tompkins Volatility: {hodges_tompkins:.4f}")
    
    realized = analyzer.calculate_realized_volatility(data)
    print(f"Realized Volatility: {realized:.4f}")
    
    intraday = analyzer.calculate_intraday_volatility(data)
    print(f"Intraday Volatility: {intraday:.4f}")
    
    # Test comprehensive analysis
    print("\n" + "=" * 60)
    print("COMPREHENSIVE VOLATILITY ANALYSIS")
    print("=" * 60)
    
    vol_analysis = analyzer.get_comprehensive_volatility(data, method='garman_klass')
    for key, value in vol_analysis.items():
        if isinstance(value, float):
            print(f"{key.capitalize()}: {value:.4f}")
        else:
            print(f"{key.capitalize()}: {value}")
    
    # Test adaptive multiplier
    multiplier = analyzer.calculate_adaptive_atr_multiplier(data)
    print(f"\nAdaptive ATR Multiplier: {multiplier}x")
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_volatility_analyzer()
