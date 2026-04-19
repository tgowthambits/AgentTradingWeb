"""
Indicator Manager - Manages and executes all indicators.
Ported from trading_system/core/indicator_manager.py
"""

import importlib
import logging
from typing import Dict, List, Any, Optional, Type
import pandas as pd

from .base_indicator import BaseIndicator, IndicatorResult

logger = logging.getLogger(__name__)


class IndicatorManager:
    """
    Manages indicator instances and coordinates their execution.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the indicator manager.

        Args:
            config: Configuration dictionary with indicator settings
        """
        self.indicators: List[BaseIndicator] = []
        self.results: Dict[str, pd.DataFrame] = {}
        self.signals: Dict[str, str] = {}
        self.weights: Dict[str, float] = {}
        self.config = config or {}

    def add_indicator(self, indicator: BaseIndicator):
        """Add an indicator to the manager."""
        self.indicators.append(indicator)
        self.weights[indicator.name] = indicator.weight
        logger.info(f"Added indicator: {indicator.name}")

    def remove_indicator(self, name: str):
        """Remove an indicator by name."""
        self.indicators = [i for i in self.indicators if i.name != name]
        self.weights.pop(name, None)
        self.signals.pop(name, None)
        self.results.pop(name, None)

    def get_indicator(self, name: str) -> Optional[BaseIndicator]:
        """Get an indicator by name."""
        for indicator in self.indicators:
            if indicator.name == name:
                return indicator
        return None

    def load_indicator_from_config(
        self, indicator_config: Dict[str, Any]
    ) -> Optional[BaseIndicator]:
        """
        Dynamically load an indicator from configuration.

        Args:
            indicator_config: Configuration dictionary with module, class, params

        Returns:
            Instantiated indicator or None if failed
        """
        try:
            module_path = indicator_config.get("module")
            class_name = indicator_config.get("class_name")
            params = indicator_config.get("params", {})
            name = indicator_config.get("name", class_name)
            enabled = indicator_config.get("enabled", True)
            weight = indicator_config.get("weight", 1.0)

            if not module_path or not class_name:
                logger.error(
                    f"Missing module or class_name in config: {indicator_config}"
                )
                return None

            # Import the module
            module = importlib.import_module(module_path)
            indicator_class: Type[BaseIndicator] = getattr(module, class_name)

            # Instantiate the indicator
            indicator = indicator_class(
                name=name, enabled=enabled, weight=weight, config=params
            )

            return indicator

        except Exception as e:
            logger.error(f"Failed to load indicator: {e}")
            return None

    def load_indicators_from_config(self, indicators_config: Dict[str, Any]):
        """
        Load multiple indicators from configuration dictionary.

        Args:
            indicators_config: Dictionary mapping indicator names to their config
        """
        for name, config in indicators_config.items():
            if not config.get("enabled", True):
                continue

            config["name"] = name
            indicator = self.load_indicator_from_config(config)

            if indicator:
                self.add_indicator(indicator)

    def execute_all(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Execute all enabled indicators and return their signals.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Dictionary mapping indicator names to signals
        """
        self.signals = {}
        self.results = {}

        for indicator in self.indicators:
            if not indicator.enabled:
                continue

            try:
                signal = indicator.get_signal(df)
                self.signals[indicator.name] = signal

                if indicator._last_calculation is not None:
                    self.results[indicator.name] = indicator._last_calculation

            except Exception as e:
                logger.error(f"Error executing {indicator.name}: {e}")
                self.signals[indicator.name] = "HOLD"

        return self.signals

    def get_weighted_signals(self) -> List[IndicatorResult]:
        """
        Get list of indicator results with weights.

        Returns:
            List of IndicatorResult objects
        """
        results = []

        for indicator in self.indicators:
            if not indicator.enabled:
                continue

            signal = self.signals.get(indicator.name, "HOLD")
            values = (
                indicator.get_indicator_values(pd.DataFrame())
                if indicator._last_calculation is not None
                else {}
            )

            results.append(
                IndicatorResult(
                    name=indicator.name,
                    signal=signal,
                    values=values,
                    weight=indicator.weight,
                )
            )

        return results

    def get_signals(self) -> Dict[str, str]:
        """Get current signals from all indicators."""
        return self.signals.copy()

    def get_weights(self) -> Dict[str, float]:
        """Get weights for all indicators."""
        return self.weights.copy()

    def get_enabled_indicators(self) -> List[BaseIndicator]:
        """Get list of enabled indicators."""
        return [i for i in self.indicators if i.enabled]

    def reset_all(self):
        """Reset all indicators."""
        for indicator in self.indicators:
            indicator.reset()
        self.signals = {}
        self.results = {}

    def update_indicator_config(self, name: str, config: Dict[str, Any]):
        """Update configuration for a specific indicator."""
        indicator = self.get_indicator(name)
        if indicator:
            indicator.config.update(config)
            if "enabled" in config:
                indicator.enabled = config["enabled"]
            if "weight" in config:
                indicator.weight = config["weight"]
                self.weights[name] = config["weight"]

    def __len__(self):
        return len(self.indicators)

    def __repr__(self):
        enabled_count = len(self.get_enabled_indicators())
        return f"IndicatorManager(total={len(self)}, enabled={enabled_count})"
