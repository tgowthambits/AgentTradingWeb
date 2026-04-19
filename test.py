import pandas as pd
import numpy as np
from scipy.stats import zscore

def rolling_volatility_split(prices, window):
    """Calculate volatility for first and second half of rolling window"""
    n = len(prices)
    half_window = window // 2
    
    v1_list, v2_list, ratio_list = [], [], []
    
    for i in range(window, n + 1):
        segment = prices[i-window:i]
        first_half = segment[:half_window]
        second_half = segment[half_window:]
        
        v1 = np.std(first_half)
        v2 = np.std(second_half)
        
        ratio = v2 / v1 if v1 != 0 else np.nan
        
        v1_list.append(v1)
        v2_list.append(v2)
        ratio_list.append(ratio)
    
    return np.array(v1_list), np.array(v2_list), np.array(ratio_list)

def classify_regime(ratio):
    """Classify volatility regime"""
    if pd.isna(ratio):
        return "UNDEFINED"
    elif ratio > 1.5:
        return "VOLATILITY_SPIKE"
    elif ratio > 1.0:
        return "EXPANSION"
    elif ratio < 0.7:
        return "COMPRESSION"
    else:
        return "STABLE"

def detect_trend(prices, short_window=5, long_window=10):
    """Detect trend using moving averages and momentum"""
    if len(prices) < long_window:
        return "UNDEFINED", 0, 0
    
    sma_short = np.mean(prices[-short_window:])
    sma_long = np.mean(prices[-long_window:])
    
    # Momentum: rate of change
    momentum = (prices[-1] - prices[-short_window]) / prices[-short_window] * 100
    
    # Trend strength: distance between SMAs
    trend_strength = (sma_short - sma_long) / sma_long * 100
    
    if sma_short > sma_long * 1.02:  # 2% threshold
        trend = "UPTREND"
    elif sma_short < sma_long * 0.98:
        trend = "DOWNTREND"
    else:
        trend = "SIDEWAYS"
    
    return trend, momentum, trend_strength

def detect_trend_change(trends, window=3):
    """Detect if trend has changed in recent window"""
    if len(trends) < window:
        return False, "NONE"
    
    recent = trends[-window:]
    prev = trends[-(window+1)] if len(trends) > window else recent[0]
    
    # Check if trend changed
    if prev != recent[-1] and recent[-1] != "SIDEWAYS":
        return True, f"{prev} → {recent[-1]}"
    
    return False, "NONE"

def generate_trading_signal(trend, regime, momentum, vol_ratio, trend_changed):
    """
    Generate trading signals based on trend and volatility
    
    Strategy Logic:
    - LONG: Uptrend + Low/Stable volatility OR Trend change to up + compression
    - SHORT: Downtrend + Low/Stable volatility OR Trend change to down + compression
    - HOLD: Existing position in trending market with acceptable volatility
    - EXIT: High volatility spike, trend reversal, or sideways with compression
    """
    
    # High volatility - always exit
    if regime == "VOLATILITY_SPIKE":
        return "EXIT", "High volatility spike"
    
    # Uptrend signals
    if trend == "UPTREND":
        if regime in ["COMPRESSION", "STABLE"] and momentum > 1:
            return "LONG", "Uptrend with stable volatility"
        elif regime == "EXPANSION" and momentum > 3:
            return "HOLD_LONG", "Strong uptrend, ride it"
        else:
            return "HOLD_LONG", "Uptrend but watch volatility"
    
    # Downtrend signals
    elif trend == "DOWNTREND":
        if regime in ["COMPRESSION", "STABLE"] and momentum < -1:
            return "SHORT", "Downtrend with stable volatility"
        elif regime == "EXPANSION" and momentum < -3:
            return "HOLD_SHORT", "Strong downtrend, ride it"
        else:
            return "HOLD_SHORT", "Downtrend but watch volatility"
    
    # Sideways market
    elif trend == "SIDEWAYS":
        if trend_changed:
            return "EXIT", "Trend change to sideways"
        elif regime == "COMPRESSION":
            return "WAIT", "Consolidation - wait for breakout"
        else:
            return "NEUTRAL", "No clear direction"
    
    return "NEUTRAL", "Undefined conditions"

def build_enhanced_features(df, price_col="close", vol_window=20, 
                           trend_short=5, trend_long=10):
    """Build comprehensive trading features"""
    prices = df[price_col].values
    
    # Volatility features
    v1, v2, ratio = rolling_volatility_split(prices, vol_window)
    pad = len(df) - len(ratio)
    df_feat = df.iloc[pad:].copy()
    
    df_feat["vol_first"] = v1
    df_feat["vol_second"] = v2
    df_feat["vol_ratio"] = ratio
    df_feat["vol_ratio_z"] = zscore(ratio) if len(ratio) > 1 else np.nan
    df_feat["regime"] = df_feat["vol_ratio"].apply(classify_regime)
    
    # Trend features
    trends = []
    momentums = []
    trend_strengths = []
    
    for i in range(len(df_feat)):
        idx = df_feat.index[i]
        price_history = df.loc[:idx, price_col].values
        trend, momentum, strength = detect_trend(price_history, trend_short, trend_long)
        trends.append(trend)
        momentums.append(momentum)
        trend_strengths.append(strength)
    
    df_feat["trend"] = trends
    df_feat["momentum"] = momentums
    df_feat["trend_strength"] = trend_strengths
    
    # Trend change detection
    trend_changes = []
    change_types = []
    
    for i in range(len(trends)):
        changed, change_type = detect_trend_change(trends[:i+1])
        trend_changes.append(changed)
        change_types.append(change_type)
    
    df_feat["trend_changed"] = trend_changes
    df_feat["change_type"] = change_types
    
    # Generate signals
    signals = []
    reasons = []
    
    for i in range(len(df_feat)):
        signal, reason = generate_trading_signal(
            df_feat.iloc[i]["trend"],
            df_feat.iloc[i]["regime"],
            df_feat.iloc[i]["momentum"],
            df_feat.iloc[i]["vol_ratio"],
            df_feat.iloc[i]["trend_changed"]
        )
        signals.append(signal)
        reasons.append(reason)
    
    df_feat["signal"] = signals
    df_feat["signal_reason"] = reasons
    
    return df_feat

# Example with your data
df = pd.DataFrame({
    "close": [1,2,4,2,4,5,2,4,6,7,5,8,9,10,11,12,13,14,15,16,17,18,19,20]
})

# Build features
features = build_enhanced_features(df, vol_window=6, trend_short=3, trend_long=6)

# Display key columns
print("Enhanced Trading Strategy Output:")
print("="*100)
print(features[["close", "trend", "momentum", "regime", "trend_changed", 
                "change_type", "signal", "signal_reason"]].to_string())

print("\n\nRecent Signals (Last 5 bars):")
print("="*100)
recent = features.tail(5)[["close", "trend", "momentum", "regime", "signal", "signal_reason"]]
print(recent.to_string())

# Strategy summary
print("\n\nStrategy Summary:")
print("="*100)
print(f"Current Trend: {features.iloc[-1]['trend']}")
print(f"Current Regime: {features.iloc[-1]['regime']}")
print(f"Momentum: {features.iloc[-1]['momentum']:.2f}%")
print(f"Signal: {features.iloc[-1]['signal']}")
print(f"Reason: {features.iloc[-1]['signal_reason']}")


"""
For Intraday Use:
Adjust the parameters based on your timeframe:

1-min bars: vol_window=20, trend_short=5, trend_long=15
5-min bars: vol_window=12, trend_short=3, trend_long=9
15-min bars: vol_window=8, trend_short=2, trend_long=6
"""