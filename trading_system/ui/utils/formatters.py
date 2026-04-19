"""
Formatters Module

Contains utility functions for formatting values for display.
"""

import pandas as pd
from datetime import datetime
from typing import Union, Optional


def format_time(time_val: Union[str, datetime, pd.Timestamp, None]) -> str:
    """
    Format time value for display.
    
    Args:
        time_val: Time value to format (string, datetime, Timestamp, or None)
    
    Returns:
        Formatted time string or "N/A" if invalid
    """
    if pd.isna(time_val) or time_val is None:
        return "N/A"
    try:
        if isinstance(time_val, str):
            return time_val
        elif hasattr(time_val, 'strftime'):
            return time_val.strftime("%Y-%m-%d %H:%M:%S")
        else:
            return pd.to_datetime(time_val).strftime("%Y-%m-%d %H:%M:%S")
    except:
        return str(time_val)[:19] if time_val else "N/A"


def format_currency(value: Union[float, int, None], symbol: str = "₹", decimals: int = 2) -> str:
    """
    Format a numeric value as currency.
    
    Args:
        value: Numeric value to format
        symbol: Currency symbol (default: ₹)
        decimals: Number of decimal places
    
    Returns:
        Formatted currency string
    """
    if value is None or pd.isna(value):
        return f"{symbol}0.00"
    
    try:
        return f"{symbol}{value:,.{decimals}f}"
    except:
        return f"{symbol}0.00"


def format_percentage(value: Union[float, int, None], decimals: int = 2, include_sign: bool = False) -> str:
    """
    Format a numeric value as a percentage.
    
    Args:
        value: Numeric value to format (0.5 = 50%, not 0.5%)
        decimals: Number of decimal places
        include_sign: Include + sign for positive values
    
    Returns:
        Formatted percentage string
    """
    if value is None or pd.isna(value):
        return "0.00%"
    
    try:
        if include_sign and value > 0:
            return f"+{value:.{decimals}f}%"
        return f"{value:.{decimals}f}%"
    except:
        return "0.00%"


def format_pnl(value: Union[float, int, None], symbol: str = "₹") -> str:
    """
    Format PnL value with color indicator (+ or -).
    
    Args:
        value: PnL value
        symbol: Currency symbol
    
    Returns:
        Formatted PnL string with sign
    """
    if value is None or pd.isna(value):
        return f"{symbol}0.00"
    
    try:
        if value >= 0:
            return f"+{symbol}{value:,.2f}"
        else:
            return f"-{symbol}{abs(value):,.2f}"
    except:
        return f"{symbol}0.00"


def format_quantity(value: Union[float, int, None]) -> str:
    """
    Format quantity value.
    
    Args:
        value: Quantity value
    
    Returns:
        Formatted quantity string
    """
    if value is None or pd.isna(value):
        return "0"
    
    try:
        return f"{int(value):,}"
    except:
        return "0"


def format_change(change: float, change_pct: float) -> str:
    """
    Format price change with percentage.
    
    Args:
        change: Absolute change value
        change_pct: Percentage change
    
    Returns:
        Formatted change string like "+0.50 (+0.25%)"
    """
    try:
        return f"{change:+.2f} ({change_pct:+.2f}%)"
    except:
        return "+0.00 (+0.00%)"


def format_signal(signal: str) -> str:
    """
    Format trading signal for display.
    
    Args:
        signal: Signal string (BUY, SELL, HOLD)
    
    Returns:
        Formatted signal string
    """
    if signal is None:
        return "HOLD"
    return str(signal).upper()


def format_ratio(value: Union[float, int, None], decimals: int = 2) -> str:
    """
    Format a ratio value.
    
    Args:
        value: Ratio value
        decimals: Number of decimal places
    
    Returns:
        Formatted ratio string
    """
    if value is None or pd.isna(value):
        return "0.00"
    
    try:
        return f"{value:.{decimals}f}"
    except:
        return "0.00"


def truncate_string(text: str, max_length: int = 20, suffix: str = "...") -> str:
    """
    Truncate a string to a maximum length.
    
    Args:
        text: String to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated
    
    Returns:
        Truncated string
    """
    if text is None:
        return ""
    
    text = str(text)
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix
