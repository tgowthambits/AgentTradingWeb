"""
UI Utilities Module

Contains utility functions and helper classes for the UI.
"""

from .data_generator import (
    combined_data_generator,
    parse_datetime_from_string,
    get_timestamps_from_df
)
from .formatters import (
    format_time,
    format_currency,
    format_percentage,
    format_pnl,
    format_quantity,
    format_change,
    format_signal,
    format_ratio,
    truncate_string
)
from .delegates import HTMLDelegate, ColoredTextDelegate
from .helpers import (
    get_enabled_indicators,
    map_config_name_to_indicator_name,
    get_signal_color,
    get_pnl_color,
    get_confidence_color,
    create_html_colored_text,
    format_table_cell_html,
    safe_float,
    safe_int
)

__all__ = [
    # Data generator
    'combined_data_generator',
    'parse_datetime_from_string',
    'get_timestamps_from_df',
    
    # Formatters
    'format_time',
    'format_currency',
    'format_percentage',
    'format_pnl',
    'format_quantity',
    'format_change',
    'format_signal',
    'format_ratio',
    'truncate_string',
    
    # Delegates
    'HTMLDelegate',
    'ColoredTextDelegate',
    
    # Helpers
    'get_enabled_indicators',
    'map_config_name_to_indicator_name',
    'get_signal_color',
    'get_pnl_color',
    'get_confidence_color',
    'create_html_colored_text',
    'format_table_cell_html',
    'safe_float',
    'safe_int'
]
