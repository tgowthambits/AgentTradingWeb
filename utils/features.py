import pandas as pd
import numpy as np

def add_technical_features(df):
    """Add basic technical indicators"""
    df["sma_5"] = df["close"].rolling(5).mean()
    df["sma_20"] = df["close"].rolling(20).mean()
    df["volatility"] = df["close"].pct_change().rolling(10).std()
    df = df.fillna(0)
    return df

def add_advanced_features(df):
    """Add advanced technical indicators for precision filtering"""
    # Moving averages
    df["sma_50"] = df["close"].rolling(50).mean()
    df["sma_200"] = df["close"].rolling(200).mean()
    
    # RSI (Relative Strength Index)
    df["rsi"] = calculate_rsi(df["close"], period=14)
    
    # Volatility (ATR-like)
    df["volatility_20"] = df["close"].pct_change().rolling(20).std()
    
    # Breakout detection (Higher Highs/Lower Lows)
    df["hh"] = detect_higher_highs(df)
    df["hl"] = detect_higher_lows(df)
    df["ll"] = detect_lower_lows(df)
    df["lh"] = detect_lower_highs(df)
    
    # Fill NaN values
    df = df.bfill().fillna(0)
    
    return df

def calculate_rsi(prices, period=14):
    """Calculate Relative Strength Index"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def detect_higher_highs(df, window=5):
    """Detect Higher Highs pattern (bullish breakout)"""
    highs = df["high"].rolling(window).max()
    return (df["high"] == highs) & (df["high"] > df["high"].shift(window))

def detect_higher_lows(df, window=5):
    """Detect Higher Lows pattern (bullish)"""
    lows = df["low"].rolling(window).min()
    return (df["low"] == lows) & (df["low"] > df["low"].shift(window))

def detect_lower_lows(df, window=5):
    """Detect Lower Lows pattern (bearish breakdown)"""
    lows = df["low"].rolling(window).min()
    return (df["low"] == lows) & (df["low"] < df["low"].shift(window))

def detect_lower_highs(df, window=5):
    """Detect Lower Highs pattern (bearish)"""
    highs = df["high"].rolling(window).max()
    return (df["high"] == highs) & (df["high"] < df["high"].shift(window))
