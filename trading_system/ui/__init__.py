"""
Trading System UI Package

This package contains the GUI components for the trading system.

Main Components:
- TradingGUI: Main application window (in gui_app.py)
- BotThread: Background thread for trading operations (in threads/)

Sub-packages:
- threads: Background thread classes
- components: Reusable UI components (tables, dashboard, config panels)
- services: Service classes (config manager, metrics calculator)
- dialogs: Popup dialogs
- utils: Utility functions and helpers

For backward compatibility, the main TradingGUI class and BotThread
are still available from gui_app.py. New code should import from
the modular structure for better organization.
"""

# Backward compatibility - import from original gui_app.py
# This ensures existing code continues to work
from trading_system.ui.gui_app import TradingGUI

# Import BotThread from both locations for compatibility
try:
    from trading_system.ui.threads.bot_thread import BotThread
except ImportError:
    # Fallback to gui_app if threads module not available
    from trading_system.ui.gui_app import BotThread

# Import utilities for easy access
from trading_system.ui.utils import (
    combined_data_generator,
    format_time,
    format_currency,
    format_percentage,
    HTMLDelegate,
    get_enabled_indicators,
    map_config_name_to_indicator_name
)

# Import services
from trading_system.ui.services import (
    ConfigManager,
    MetricsCalculator
)

__all__ = [
    # Main classes
    'TradingGUI',
    'BotThread',
    
    # Utilities
    'combined_data_generator',
    'format_time',
    'format_currency',
    'format_percentage',
    'HTMLDelegate',
    'get_enabled_indicators',
    'map_config_name_to_indicator_name',
    
    # Services
    'ConfigManager',
    'MetricsCalculator',
]
