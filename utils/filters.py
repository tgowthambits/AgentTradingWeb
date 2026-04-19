"""
Precision filters for trading signals
These filters help improve signal quality by adding additional confirmation criteria
"""

import numpy as np
import pandas as pd


def volatility_filter(df, threshold=0.01, min_volatility=None):
    """
    Filter: Only trade when volatility exceeds threshold
    
    Args:
        df: DataFrame with price data
        threshold: Minimum volatility threshold (default 0.01 = 1%)
        min_volatility: Optional minimum volatility value (overrides threshold if provided)
    
    Returns:
        bool: True if volatility filter passes
    """
    if "volatility" not in df.columns:
        volatility = df["close"].pct_change().rolling(20).std().iloc[-1]
    else:
        volatility = df["volatility"].iloc[-1]
    
    if min_volatility is not None:
        return volatility >= min_volatility
    
    return volatility >= threshold


def trend_confirmation_filter(df, use_sma50_200=True):
    """
    Filter: Confirm trend using moving averages
    MA50 > MA200 = bullish, MA50 < MA200 = bearish
    
    Args:
        df: DataFrame with price data
        use_sma50_200: If True, use SMA50/200, else use SMA5/20
    
    Returns:
        int: 1 for bullish, -1 for bearish, 0 for neutral
    """
    if use_sma50_200:
        if "sma_50" not in df.columns or "sma_200" not in df.columns:
            return 0
        ma_fast = df["sma_50"].iloc[-1]
        ma_slow = df["sma_200"].iloc[-1]
    else:
        if "sma_5" not in df.columns or "sma_20" not in df.columns:
            return 0
        ma_fast = df["sma_5"].iloc[-1]
        ma_slow = df["sma_20"].iloc[-1]
    
    if pd.isna(ma_fast) or pd.isna(ma_slow):
        return 0
    
    if ma_fast > ma_slow:
        return 1  # Bullish
    elif ma_fast < ma_slow:
        return -1  # Bearish
    return 0  # Neutral


def breakout_filter(df, lookback=20):
    """
    Filter: Detect breakout patterns
    HH/HL → bullish (long), LL/LH → bearish (short)
    
    Args:
        df: DataFrame with price data
        lookback: Number of periods to look back
    
    Returns:
        int: 1 for bullish breakout, -1 for bearish breakdown, 0 for no breakout
    """
    if len(df) < lookback:
        return 0
    
    recent = df.tail(lookback)
    
    # Check for higher highs and higher lows (bullish)
    if "hh" in df.columns and "hl" in df.columns:
        hh_count = recent["hh"].sum()
        hl_count = recent["hl"].sum()
        if hh_count > 0 or hl_count > 0:
            return 1
    
    # Check for lower lows and lower highs (bearish)
    if "ll" in df.columns and "lh" in df.columns:
        ll_count = recent["ll"].sum()
        lh_count = recent["lh"].sum()
        if ll_count > 0 or lh_count > 0:
            return -1
    
    return 0


def momentum_filter(df, rsi_buy=55, rsi_sell=45):
    """
    Filter: Use RSI for momentum confirmation
    RSI > rsi_buy → BUY signal, RSI < rsi_sell → SELL signal
    
    Args:
        df: DataFrame with price data
        rsi_buy: RSI threshold for buy signal (default 55)
        rsi_sell: RSI threshold for sell signal (default 45)
    
    Returns:
        int: 1 for buy, -1 for sell, 0 for hold
    """
    if "rsi" not in df.columns:
        return 0
    
    rsi = df["rsi"].iloc[-1]
    
    if pd.isna(rsi):
        return 0
    
    if rsi > rsi_buy:
        return 1  # Buy momentum
    elif rsi < rsi_sell:
        return -1  # Sell momentum
    
    return 0  # Neutral


def confidence_filter(daily_prob, threshold=0.6, intraday_prob=None):
    """
    Filter: Only trade if confidence exceeds threshold
    Uses the higher of daily or intraday probability if both provided
    
    Args:
        daily_prob: Probability from daily model (0-1)
        threshold: Minimum confidence threshold (default 0.6)
        intraday_prob: Probability from intraday model (0-1, optional)
    
    Returns:
        bool: True if confidence filter passes
    """
    if intraday_prob is not None:
        # Use the higher of daily or intraday probability
        max_prob = max(daily_prob, intraday_prob)
        return max_prob >= threshold
    return daily_prob >= threshold


def apply_all_filters(df, signal, daily_prob=None, config=None, intraday_prob=None):
    """
    Apply all precision filters to a trading signal
    
    Args:
        df: DataFrame with price data
        signal: Raw signal from models (-1, 0, 1)
        daily_prob: Probability from daily model (optional)
        config: Configuration dict with filter parameters
        intraday_prob: Probability from intraday model (optional)
    
    Returns:
        dict: Filter results and final filtered signal
    """
    if config is None:
        config = {}
    
    filters = {
        "volatility": True,
        "trend": 0,
        "breakout": 0,
        "momentum": 0,
        "confidence": True
    }
    
    # Volatility filter
    vol_threshold = config.get("volatility_threshold", 0.01)
    # Calculate volatility values for display
    returns = df["close"].pct_change()
    
    # Get last 20 periods of returns
    recent_returns = returns.tail(20)
    
    # Overall volatility (standard deviation of all returns)
    if "volatility" not in df.columns:
        overall_volatility = recent_returns.std()
    else:
        overall_volatility = df["volatility"].iloc[-1]
    
    # Positive volatility (std of positive returns only)
    positive_returns = recent_returns[recent_returns > 0]
    positive_volatility = positive_returns.std() if len(positive_returns) > 0 else 0.0
    
    # Negative volatility (std of negative returns, as positive value)
    negative_returns = recent_returns[recent_returns < 0]
    negative_volatility = abs(negative_returns.std()) if len(negative_returns) > 0 else 0.0
    
    # Ensure we have valid float values
    overall_volatility = float(overall_volatility) if pd.notna(overall_volatility) else 0.0
    positive_volatility = float(positive_volatility) if pd.notna(positive_volatility) else 0.0
    negative_volatility = float(negative_volatility) if pd.notna(negative_volatility) else 0.0
    
    filters["volatility"] = volatility_filter(df, threshold=vol_threshold)
    
    # Trend confirmation
    filters["trend"] = trend_confirmation_filter(df, use_sma50_200=config.get("use_sma50_200", True))
    
    # Breakout detection
    filters["breakout"] = breakout_filter(df, lookback=config.get("breakout_lookback", 20))
    
    # Momentum filter
    rsi_buy = config.get("rsi_buy", 55)
    rsi_sell = config.get("rsi_sell", 45)
    filters["momentum"] = momentum_filter(df, rsi_buy=rsi_buy, rsi_sell=rsi_sell)
    
    # Confidence filter (use higher of daily or intraday probability)
    if daily_prob is not None or intraday_prob is not None:
        conf_threshold = config.get("confidence_threshold", 0.6)
        filters["confidence"] = confidence_filter(
            daily_prob or 0.5, 
            threshold=conf_threshold,
            intraday_prob=intraday_prob
        )
    
    # Calculate filtered signal
    # For BUY signals: ALL filters must pass
    # For SELL signals: Use existing logic (volatility + confidence + at least one confirmation)
    
    filtered_signal = 0
    
    if filters["volatility"] and filters["confidence"]:
        # For BUY signals (signal == 1): Require ALL filters to pass
        if signal == 1:
            # Check if all bullish filters pass
            trend_bullish = filters["trend"] == 1
            breakout_bullish = filters["breakout"] == 1
            momentum_buy = filters["momentum"] == 1
            
            # All filters must pass for BUY
            if trend_bullish and breakout_bullish and momentum_buy:
                filtered_signal = 1  # BUY
            else:
                filtered_signal = 0  # HOLD - not all filters passed
        
        # For SELL signals: Use existing logic (at least one confirmation)
        elif signal == -1:
            # Count confirmations for SELL signal
            confirmations = 0
            
            # Trend confirmation
            if filters["trend"] == -1:
                confirmations += 1
            
            # Breakout confirmation
            if filters["breakout"] == -1:
                confirmations += 1
            
            # Momentum confirmation
            if filters["momentum"] == -1:
                confirmations += 1
            
            # Require at least one confirmation for SELL
            min_confirmations = config.get("min_confirmations", 1)
            if confirmations >= min_confirmations:
                filtered_signal = -1  # SELL
            else:
                filtered_signal = 0  # HOLD
        
        # For HOLD signals: Check for bullish override
        else:  # signal == 0
            # Count bullish confirmations (for override logic)
            bullish_confirmations = 0
            if filters["trend"] == 1:
                bullish_confirmations += 1
            if filters["breakout"] == 1:
                bullish_confirmations += 1
            if filters["momentum"] == 1:
                bullish_confirmations += 1
            
            # Only override to BUY if ALL filters are bullish
            if filters["trend"] == 1 and filters["breakout"] == 1 and filters["momentum"] == 1:
                filtered_signal = 1  # Override to BUY
            else:
                filtered_signal = 0  # HOLD
    
    return {
        "filters": filters,
        "filtered_signal": filtered_signal,
        "volatility_value": overall_volatility,
        "volatility_positive": positive_volatility,
        "volatility_negative": negative_volatility,
        "confirmations": {
            "trend": filters["trend"] == signal if filters["trend"] != 0 else False,
            "breakout": filters["breakout"] == signal if filters["breakout"] != 0 else False,
            "momentum": filters["momentum"] == signal if filters["momentum"] != 0 else False
        }
    }

