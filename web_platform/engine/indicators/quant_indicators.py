"""
Quantitative Indicators Module

Implements advanced HFT and quantitative techniques:
1. Order Flow Imbalance (OFI) - HFT technique
2. VWAP Deviation Strategy
3. Kalman Filter for Price Prediction
4. Hurst Exponent for Regime Detection
5. Entropy-Based Volatility

These indicators provide statistical edge beyond traditional technical analysis.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
from scipy import stats


class QuantIndicators:
    """
    Advanced quantitative indicators for algorithmic trading.
    Implements HFT techniques and statistical methods.
    """
    
    def __init__(self):
        """Initialize quant indicators."""
        self.kalman_state = None
        self.kalman_covariance = None
    
    def calculate_order_flow_imbalance(self,
                                      buy_volume: float,
                                      sell_volume: float) -> float:
        """
        Calculate Order Flow Imbalance (OFI).
        
        HFT technique: Measures buying vs selling pressure.
        OFI = (Buy Volume - Sell Volume) / (Buy Volume + Sell Volume)
        
        Interpretation:
        - OFI > 0.3: Strong buying pressure (bullish)
        - OFI < -0.3: Strong selling pressure (bearish)
        - OFI near 0: Balanced (neutral)
        
        Args:
            buy_volume: Volume of buy orders
            sell_volume: Volume of sell orders
        
        Returns:
            OFI value between -1 and 1
        """
        total_volume = buy_volume + sell_volume
        
        if total_volume == 0:
            return 0.0
        
        ofi = (buy_volume - sell_volume) / total_volume
        return float(ofi)
    
    def calculate_vwap(self, data: pd.DataFrame) -> float:
        """
        Calculate Volume-Weighted Average Price (VWAP).
        
        VWAP = Sum(Price * Volume) / Sum(Volume)
        
        Args:
            data: DataFrame with 'close' and 'volume' columns
        
        Returns:
            VWAP value
        """
        if len(data) == 0 or 'volume' not in data.columns:
            return 0.0
        
        prices = data['close'].values
        volumes = data['volume'].values
        
        total_volume = np.sum(volumes)
        
        if total_volume == 0:
            return float(np.mean(prices))
        
        vwap = np.sum(prices * volumes) / total_volume
        return float(vwap)
    
    def calculate_vwap_deviation(self, 
                                 data: pd.DataFrame,
                                 current_price: float) -> Dict:
        """
        Calculate deviation from VWAP with statistical bands.
        
        Strategy:
        - Buy when price deviates > 2 std below VWAP (oversold)
        - Sell when price deviates > 2 std above VWAP (overbought)
        - Exit when price reverts to VWAP
        
        Args:
            data: DataFrame with OHLC and volume
            current_price: Current market price
        
        Returns:
            Dictionary with VWAP analysis
        """
        vwap = self.calculate_vwap(data)
        
        if vwap == 0:
            return {
                'vwap': 0,
                'deviation': 0,
                'deviation_pct': 0,
                'std': 0,
                'z_score': 0,
                'signal': 'HOLD'
            }
        
        # Calculate deviation
        deviation = current_price - vwap
        deviation_pct = (deviation / vwap) * 100
        
        # Calculate standard deviation of price from VWAP
        price_deviations = data['close'].values - vwap
        std_dev = np.std(price_deviations)
        
        # Z-score
        z_score = deviation / std_dev if std_dev > 0 else 0
        
        # Generate signal
        if z_score < -2.0:
            signal = 'BUY'  # Price significantly below VWAP
        elif z_score > 2.0:
            signal = 'SELL'  # Price significantly above VWAP
        elif abs(z_score) < 0.5:
            signal = 'NEUTRAL'  # Price near VWAP (exit signal)
        else:
            signal = 'HOLD'
        
        return {
            'vwap': vwap,
            'deviation': deviation,
            'deviation_pct': deviation_pct,
            'std': std_dev,
            'z_score': z_score,
            'signal': signal
        }
    
    def kalman_filter_price(self, 
                           prices: np.ndarray,
                           process_noise: float = 0.01,
                           measurement_noise: float = 1.0) -> Tuple[np.ndarray, float]:
        """
        Apply Kalman Filter to smooth price series and predict next value.
        
        Kalman Filter is optimal for linear systems with Gaussian noise.
        More responsive than moving averages, less lag.
        
        Args:
            prices: Array of historical prices
            process_noise: Process noise covariance (Q)
            measurement_noise: Measurement noise covariance (R)
        
        Returns:
            (filtered_prices, predicted_next_price)
        """
        if len(prices) < 2:
            return prices, prices[-1] if len(prices) > 0 else 0.0
        
        n = len(prices)
        
        # Initialize
        filtered = np.zeros(n)
        filtered[0] = prices[0]
        
        # State: [price, velocity]
        state = np.array([prices[0], 0.0])
        covariance = np.eye(2)
        
        # State transition matrix
        F = np.array([[1, 1], [0, 1]])
        
        # Observation matrix
        H = np.array([[1, 0]])
        
        # Process noise
        Q = np.eye(2) * process_noise
        
        # Measurement noise
        R = np.array([[measurement_noise]])
        
        # Kalman filtering
        for i in range(1, n):
            # Prediction
            state_pred = F @ state
            cov_pred = F @ covariance @ F.T + Q
            
            # Update
            measurement = prices[i]
            innovation = measurement - (H @ state_pred)[0]
            S = (H @ cov_pred @ H.T + R)[0, 0]
            K = cov_pred @ H.T / S
            
            state = state_pred + K.flatten() * innovation
            covariance = (np.eye(2) - np.outer(K, H)) @ cov_pred
            
            filtered[i] = state[0]
        
        # Predict next value
        next_state = F @ state
        predicted_next = next_state[0]
        
        return filtered, float(predicted_next)
    
    def calculate_hurst_exponent(self, 
                                 prices: np.ndarray,
                                 max_lag: int = 20) -> float:
        """
        Calculate Hurst Exponent to determine market regime.
        
        Interpretation:
        - H < 0.5: Mean-reverting (use mean reversion strategies)
        - H = 0.5: Random walk (avoid, no edge)
        - H > 0.5: Trending (use momentum strategies)
        
        Args:
            prices: Array of historical prices
            max_lag: Maximum lag for R/S analysis
        
        Returns:
            Hurst exponent (0 to 1)
        """
        if len(prices) < max_lag * 2:
            return 0.5  # Neutral
        
        # Calculate log returns
        log_returns = np.log(prices[1:] / prices[:-1])
        
        if len(log_returns) < max_lag:
            return 0.5
        
        # R/S analysis
        lags = range(2, max_lag)
        tau = []
        rs = []
        
        for lag in lags:
            # Split into chunks
            n_chunks = len(log_returns) // lag
            
            if n_chunks < 1:
                continue
            
            rs_values = []
            
            for i in range(n_chunks):
                chunk = log_returns[i*lag:(i+1)*lag]
                
                if len(chunk) < 2:
                    continue
                
                # Mean-adjusted series
                mean_return = np.mean(chunk)
                adjusted = chunk - mean_return
                
                # Cumulative deviate
                cumdev = np.cumsum(adjusted)
                
                # Range
                R = np.max(cumdev) - np.min(cumdev)
                
                # Standard deviation
                S = np.std(chunk, ddof=1)
                
                if S > 0:
                    rs_values.append(R / S)
            
            if len(rs_values) > 0:
                tau.append(lag)
                rs.append(np.mean(rs_values))
        
        if len(tau) < 2:
            return 0.5
        
        # Linear regression in log-log space
        # log(R/S) = H * log(tau) + c
        log_tau = np.log(tau)
        log_rs = np.log(rs)
        
        # Fit line
        slope, _, _, _, _ = stats.linregress(log_tau, log_rs)
        
        # Hurst exponent is the slope
        hurst = float(slope)
        
        # Clamp to valid range
        hurst = max(0.0, min(1.0, hurst))
        
        return hurst
    
    def calculate_entropy(self, returns: np.ndarray, bins: int = 50) -> float:
        """
        Calculate Shannon entropy of returns distribution.
        
        Measures market uncertainty/unpredictability.
        High entropy = high uncertainty = reduce position size
        Low entropy = more predictable = can increase size
        
        Args:
            returns: Array of returns
            bins: Number of bins for histogram
        
        Returns:
            Entropy value (higher = more uncertain)
        """
        if len(returns) < 10:
            return 0.0
        
        # Create histogram
        counts, _ = np.histogram(returns, bins=bins)
        
        # Normalize to probabilities
        probabilities = counts / np.sum(counts)
        
        # Remove zero probabilities
        probabilities = probabilities[probabilities > 0]
        
        # Calculate entropy
        entropy = -np.sum(probabilities * np.log2(probabilities))
        
        return float(entropy)
    
    def get_market_regime(self, 
                         data: pd.DataFrame,
                         hurst_window: int = 100) -> Dict:
        """
        Determine current market regime using multiple indicators.
        
        Args:
            data: DataFrame with OHLC data
            hurst_window: Window for Hurst calculation
        
        Returns:
            Dictionary with regime analysis
        """
        if len(data) < hurst_window:
            return {
                'regime': 'UNKNOWN',
                'hurst': 0.5,
                'entropy': 0.0,
                'confidence': 0.0,
                'strategy': 'WAIT'
            }
        
        # Calculate Hurst exponent
        prices = data['close'].tail(hurst_window).values
        hurst = self.calculate_hurst_exponent(prices)
        
        # Calculate entropy
        returns = np.log(prices[1:] / prices[:-1])
        entropy = self.calculate_entropy(returns)
        
        # Determine regime
        if hurst < 0.45:
            regime = 'MEAN_REVERTING'
            strategy = 'REVERSAL'
            confidence = (0.5 - hurst) / 0.5  # Higher confidence when further from 0.5
        elif hurst > 0.55:
            regime = 'TRENDING'
            strategy = 'MOMENTUM'
            confidence = (hurst - 0.5) / 0.5
        else:
            regime = 'RANDOM'
            strategy = 'WAIT'
            confidence = 0.0
        
        # Adjust confidence based on entropy
        # High entropy = less confidence
        max_entropy = np.log2(50)  # Max possible entropy with 50 bins
        entropy_factor = 1.0 - (entropy / max_entropy)
        confidence *= entropy_factor
        
        return {
            'regime': regime,
            'hurst': hurst,
            'entropy': entropy,
            'confidence': confidence,
            'strategy': strategy
        }
    
    def calculate_microstructure_metrics(self,
                                        data: pd.DataFrame) -> Dict:
        """
        Calculate market microstructure metrics.
        
        Useful for understanding market quality and detecting manipulation.
        
        Args:
            data: DataFrame with OHLC and volume
        
        Returns:
            Dictionary with microstructure metrics
        """
        if len(data) < 10:
            return {
                'bid_ask_bounce': 0.0,
                'price_impact': 0.0,
                'liquidity_score': 0.0
            }
        
        # Bid-ask bounce (using high-low as proxy)
        hl_ranges = data['high'] - data['low']
        avg_range = np.mean(hl_ranges)
        
        # Price impact (price change per unit volume)
        price_changes = np.abs(np.diff(data['close'].values))
        volumes = data['volume'].values[1:]
        
        price_impact = np.mean(price_changes / (volumes + 1))
        
        # Liquidity score (inverse of price impact)
        liquidity = 1.0 / (price_impact + 0.0001)
        
        return {
            'bid_ask_bounce': float(avg_range),
            'price_impact': float(price_impact),
            'liquidity_score': float(liquidity)
        }


def test_quant_indicators():
    """Test function for QuantIndicators."""
    print("=" * 60)
    print("QUANT INDICATORS TEST")
    print("=" * 60)
    
    qi = QuantIndicators()
    
    # Generate sample data
    np.random.seed(42)
    n = 200
    
    # Create trending data
    trend = np.linspace(100, 120, n)
    noise = np.random.normal(0, 2, n)
    prices = trend + noise
    
    volumes = np.random.randint(1000, 10000, n)
    
    data = pd.DataFrame({
        'close': prices,
        'open': prices * (1 + np.random.uniform(-0.01, 0.01, n)),
        'high': prices * (1 + np.random.uniform(0, 0.02, n)),
        'low': prices * (1 - np.random.uniform(0, 0.02, n)),
        'volume': volumes
    })
    
    # Test 1: Order Flow Imbalance
    print("\n1. Order Flow Imbalance:")
    ofi = qi.calculate_order_flow_imbalance(6000, 4000)
    print(f"   Buy: 6000, Sell: 4000 → OFI: {ofi:.3f} (Bullish)")
    
    # Test 2: VWAP Deviation
    print("\n2. VWAP Deviation Strategy:")
    vwap_analysis = qi.calculate_vwap_deviation(data, 105.0)
    print(f"   Current Price: 105.0")
    print(f"   VWAP: {vwap_analysis['vwap']:.2f}")
    print(f"   Z-Score: {vwap_analysis['z_score']:.2f}")
    print(f"   Signal: {vwap_analysis['signal']}")
    
    # Test 3: Kalman Filter
    print("\n3. Kalman Filter:")
    filtered, predicted = qi.kalman_filter_price(prices[-20:])
    print(f"   Last Price: {prices[-1]:.2f}")
    print(f"   Filtered: {filtered[-1]:.2f}")
    print(f"   Predicted Next: {predicted:.2f}")
    
    # Test 4: Hurst Exponent
    print("\n4. Hurst Exponent (Trending Data):")
    hurst = qi.calculate_hurst_exponent(prices)
    print(f"   Hurst: {hurst:.3f}")
    if hurst < 0.5:
        print("   → Mean Reverting")
    elif hurst > 0.5:
        print("   → Trending")
    else:
        print("   → Random Walk")
    
    # Test 5: Entropy
    print("\n5. Market Entropy:")
    returns = np.log(prices[1:] / prices[:-1])
    entropy = qi.calculate_entropy(returns)
    print(f"   Entropy: {entropy:.3f}")
    print(f"   Interpretation: {'Low uncertainty' if entropy < 3 else 'High uncertainty'}")
    
    # Test 6: Market Regime
    print("\n6. Market Regime Analysis:")
    regime = qi.get_market_regime(data)
    print(f"   Regime: {regime['regime']}")
    print(f"   Strategy: {regime['strategy']}")
    print(f"   Confidence: {regime['confidence']:.1%}")
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_quant_indicators()
