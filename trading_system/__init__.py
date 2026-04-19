"""
Trading System - Plug-and-Play Indicator Architecture

A modular, extensible trading system with clean architecture.
"""

__version__ = "1.0.0"
__author__ = "Markov Market Team"

from trading_system.core.trading_engine import TradingEngine
from trading_system.core.indicator_manager import IndicatorManager
from trading_system.core.signal_aggregator import SignalAggregator
from trading_system.core.base_indicator import BaseIndicator
from trading_system.data.data_loader import DataLoader

__all__ = [
    'TradingEngine',
    'IndicatorManager',
    'SignalAggregator',
    'BaseIndicator',
    'DataLoader'
]

