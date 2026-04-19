"""
Helpers Module

Contains helper functions for UI operations.
"""

from typing import Dict, List, Any, Optional


def get_enabled_indicators(config: Dict[str, Any]) -> List[str]:
    """
    Get list of enabled indicator names from config.
    
    Args:
        config: Trading configuration dictionary
    
    Returns:
        Sorted list of enabled indicator names
    """
    indicators_config = config.get('indicators', {})
    enabled = []
    
    for ind_name, ind_config in indicators_config.items():
        if isinstance(ind_config, dict) and ind_config.get('enabled', False):
            enabled.append(ind_name)
    
    return sorted(enabled)  # Sort for consistent column order


def map_config_name_to_indicator_name(config_name: str, indicator_signals: Dict[str, str]) -> str:
    """
    Map config indicator name to actual indicator class name.
    
    Config uses: rsi, ma_crossover, macd, bollinger_bands, mystic_pulse, super_regression
    Indicator classes use: RSI, MACrossover, MACD, BollingerBands, MysticPulse, SuperRegression
    
    Args:
        config_name: Name from config file
        indicator_signals: Dictionary of indicator signals (keys are class names)
    
    Returns:
        The actual key from indicator_signals dict, or config_name if not found
    """
    # Direct match first
    if config_name in indicator_signals:
        return config_name
    
    # Try common mappings
    name_mappings = {
        'rsi': 'RSI',
        'ma_crossover': 'MACrossover',
        'macd': 'MACD',
        'bollinger_bands': 'BollingerBands',
        'mystic_pulse': 'MysticPulse',
        'super_regression': 'SuperRegression'
    }
    
    # Try mapped name
    mapped_name = name_mappings.get(config_name)
    if mapped_name and mapped_name in indicator_signals:
        return mapped_name
    
    # Try case-insensitive search
    config_lower = config_name.lower()
    for key in indicator_signals.keys():
        if key.lower() == config_lower or key.lower().replace('_', '') == config_lower.replace('_', ''):
            return key
    
    # Try converting config_name to class name format
    # rsi -> RSI, ma_crossover -> MACrossover
    parts = config_name.split('_')
    class_name = ''.join(word.capitalize() for word in parts)
    if class_name in indicator_signals:
        return class_name
    
    # If nothing matches, return config_name (will default to HOLD)
    return config_name


def get_signal_color(signal: str) -> str:
    """
    Get color code for a trading signal.
    
    Args:
        signal: Trading signal (BUY, SELL, HOLD)
    
    Returns:
        Color hex code
    """
    signal_colors = {
        'BUY': '#228B22',   # Forest green
        'SELL': '#DC143C',  # Crimson red
        'HOLD': '#FFD700',  # Gold
    }
    return signal_colors.get(str(signal).upper(), '#FFFFFF')


def get_pnl_color(pnl: float) -> str:
    """
    Get color code for a PnL value.
    
    Args:
        pnl: Profit/Loss value
    
    Returns:
        Color hex code
    """
    if pnl > 0:
        return '#228B22'  # Green for profit
    elif pnl < 0:
        return '#DC143C'  # Red for loss
    else:
        return '#FFFFFF'  # White for zero


def get_confidence_color(confidence: float) -> str:
    """
    Get color code for a confidence/agreement score.
    
    Args:
        confidence: Confidence score (0.0 to 1.0)
    
    Returns:
        Color hex code
    """
    if confidence >= 0.70:
        return '#228B22'  # Green for high confidence
    elif confidence >= 0.50:
        return '#FFD700'  # Gold for medium confidence
    else:
        return '#DC143C'  # Red for low confidence


def create_html_colored_text(text: str, color: str) -> str:
    """
    Create HTML-formatted colored text.
    
    Args:
        text: Text to color
        color: Color hex code
    
    Returns:
        HTML string with colored text
    """
    return f"<span style='color:{color}'>{text}</span>"


def format_table_cell_html(value: Any, color: Optional[str] = None, bold: bool = False) -> str:
    """
    Format a value for display in a table cell with optional styling.
    
    Args:
        value: Value to format
        color: Optional color hex code
        bold: Whether to make text bold
    
    Returns:
        HTML string for the cell
    """
    text = str(value)
    
    if bold:
        text = f"<b>{text}</b>"
    
    if color:
        text = f"<span style='color:{color}'>{text}</span>"
    
    return text


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert a value to float.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
    
    Returns:
        Float value or default
    """
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """
    Safely convert a value to int.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
    
    Returns:
        Int value or default
    """
    try:
        if value is None:
            return default
        return int(float(value))
    except (ValueError, TypeError):
        return default
