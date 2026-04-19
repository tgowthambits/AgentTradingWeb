"""
Base indicator class for all trading indicators.
Ported from trading_system/core/base_indicator.py
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class BaseIndicator(ABC):
    """
    Abstract base class for all trading indicators.

    All indicators must implement:
    - calculate(): Returns a DataFrame with a 'signal' column
    - get_required_columns(): Returns list of required DataFrame columns
    """

    def __init__(
        self,
        name: str,
        enabled: bool = True,
        weight: float = 1.0,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the indicator.

        Args:
            name: Unique identifier for the indicator
            enabled: Whether the indicator is active
            weight: Weight for signal aggregation (0.0 to 1.0+)
            config: Configuration parameters specific to the indicator
        """
        self.name = name
        self.enabled = enabled
        self.weight = weight
        self.config = config or {}
        self._last_signal: Optional[str] = None
        self._last_calculation: Optional[pd.DataFrame] = None

    @abstractmethod
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate indicator values and generate signals.

        Args:
            df: DataFrame with OHLCV data (must contain required columns)

        Returns:
            DataFrame with indicator columns and 'signal' column
            Signal values: 'BUY', 'SELL', or 'HOLD'
        """
        pass

    @abstractmethod
    def get_required_columns(self) -> List[str]:
        """
        Get list of required DataFrame columns.

        Returns:
            List of column names required for calculation
        """
        pass

    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        Validate that the DataFrame has required columns.

        Args:
            df: DataFrame to validate

        Returns:
            True if valid, raises ValueError otherwise
        """
        required = self.get_required_columns()
        missing = [col for col in required if col not in df.columns]

        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        if len(df) == 0:
            raise ValueError("DataFrame is empty")

        return True

    def get_signal(self, df: pd.DataFrame) -> str:
        """
        Get the current signal from the indicator.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Signal string: 'BUY', 'SELL', or 'HOLD'
        """
        if not self.enabled:
            return "HOLD"

        try:
            self.validate_data(df)
            result = self.calculate(df)

            if result is None or len(result) == 0:
                return "HOLD"

            if "signal" not in result.columns:
                logger.warning(f"{self.name}: No 'signal' column in result")
                return "HOLD"

            signal = result["signal"].iloc[-1]
            self._last_signal = signal
            self._last_calculation = result

            return signal if signal in ["BUY", "SELL", "HOLD"] else "HOLD"

        except Exception as e:
            logger.error(f"{self.name}: Error calculating signal: {e}")
            return "HOLD"

    def get_indicator_values(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get the current indicator values (for display/debugging).

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Dictionary with indicator values
        """
        if self._last_calculation is None:
            try:
                self.calculate(df)
            except Exception:
                pass

        if self._last_calculation is None:
            return {}

        # Get last row values (excluding standard columns)
        last_row = self._last_calculation.iloc[-1]
        exclude_cols = ["open", "high", "low", "close", "volume", "timestamp", "signal"]

        return {
            col: last_row[col]
            for col in self._last_calculation.columns
            if col not in exclude_cols
        }

    def reset(self):
        """Reset indicator state."""
        self._last_signal = None
        self._last_calculation = None

    def __repr__(self):
        return f"{self.__class__.__name__}(name='{self.name}', enabled={self.enabled}, weight={self.weight})"


class IndicatorResult:
    """Container for indicator calculation results."""

    def __init__(
        self,
        name: str,
        signal: str,
        values: Dict[str, Any],
        weight: float,
        timestamp: Optional[pd.Timestamp] = None,
    ):
        self.name = name
        self.signal = signal
        self.values = values
        self.weight = weight
        self.timestamp = timestamp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "signal": self.signal,
            "values": self.values,
            "weight": self.weight,
            "timestamp": str(self.timestamp) if self.timestamp else None,
        }
