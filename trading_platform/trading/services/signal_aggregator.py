"""
Signal Aggregator - Combines signals from multiple indicators.
Ported from trading_system/core/signal_aggregator.py
"""

import logging
from typing import Dict, Optional, Any
from collections import Counter

logger = logging.getLogger(__name__)


class SignalAggregator:
    """
    Combines signals from multiple indicators using various strategies.

    Supported strategies:
    - majority: Simple majority voting
    - weighted: Weighted voting based on indicator weights
    - unanimous: All indicators must agree
    - conservative: Requires strong agreement for BUY/SELL
    - threshold: Configurable threshold-based aggregation
    """

    VALID_STRATEGIES = [
        "majority",
        "weighted",
        "unanimous",
        "conservative",
        "threshold",
    ]

    def __init__(
        self,
        strategy: str = "weighted",
        min_agreement: float = 0.6,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the signal aggregator.

        Args:
            strategy: Aggregation strategy name
            min_agreement: Minimum agreement ratio (0.0 to 1.0)
            config: Additional configuration options
        """
        if strategy not in self.VALID_STRATEGIES:
            raise ValueError(
                f"Invalid strategy: {strategy}. Must be one of {self.VALID_STRATEGIES}"
            )

        self.strategy = strategy
        self.min_agreement = min_agreement
        self.config = config or {}

        # Threshold configuration
        self.buy_threshold = self.config.get("buy_threshold", 0.6)
        self.sell_threshold = self.config.get("sell_threshold", 0.6)

    def aggregate(
        self, signals: Dict[str, str], weights: Optional[Dict[str, float]] = None
    ) -> str:
        """
        Aggregate signals from multiple indicators.

        Args:
            signals: Dictionary mapping indicator names to signals
            weights: Optional dictionary mapping indicator names to weights

        Returns:
            Aggregated signal: 'BUY', 'SELL', or 'HOLD'
        """
        if not signals:
            return "HOLD"

        # Filter out invalid signals
        valid_signals = {
            k: v for k, v in signals.items() if v in ["BUY", "SELL", "HOLD"]
        }

        if not valid_signals:
            return "HOLD"

        # Default weights to 1.0 if not provided
        if weights is None:
            weights = {k: 1.0 for k in valid_signals}

        # Call appropriate strategy method
        strategy_method = getattr(self, f"_aggregate_{self.strategy}")
        return strategy_method(valid_signals, weights)

    def _aggregate_majority(
        self, signals: Dict[str, str], weights: Dict[str, float]
    ) -> str:
        """Simple majority voting."""
        signal_counts = Counter(signals.values())

        if not signal_counts:
            return "HOLD"

        # Get the most common signal
        most_common = signal_counts.most_common(1)[0]
        total_signals = len(signals)

        # Check if majority is achieved
        if most_common[1] / total_signals >= self.min_agreement:
            return most_common[0]

        return "HOLD"

    def _aggregate_weighted(
        self, signals: Dict[str, str], weights: Dict[str, float]
    ) -> str:
        """Weighted voting based on indicator weights."""
        weighted_scores = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0}
        total_weight = 0.0

        for indicator, signal in signals.items():
            weight = weights.get(indicator, 1.0)
            weighted_scores[signal] += weight
            total_weight += weight

        if total_weight == 0:
            return "HOLD"

        # Normalize scores
        for signal in weighted_scores:
            weighted_scores[signal] /= total_weight

        # Check for BUY signal
        if weighted_scores["BUY"] >= self.buy_threshold:
            return "BUY"

        # Check for SELL signal
        if weighted_scores["SELL"] >= self.sell_threshold:
            return "SELL"

        return "HOLD"

    def _aggregate_unanimous(
        self, signals: Dict[str, str], weights: Dict[str, float]
    ) -> str:
        """All indicators must agree."""
        unique_signals = set(signals.values())

        if len(unique_signals) == 1:
            signal = unique_signals.pop()
            if signal in ["BUY", "SELL"]:
                return signal

        return "HOLD"

    def _aggregate_conservative(
        self, signals: Dict[str, str], weights: Dict[str, float]
    ) -> str:
        """
        Conservative approach: requires strong agreement and no opposing signals.
        """
        signal_counts = Counter(signals.values())
        total = len(signals)

        # No opposing signals allowed
        if signal_counts.get("BUY", 0) > 0 and signal_counts.get("SELL", 0) > 0:
            return "HOLD"

        # Require high agreement (80%)
        conservative_threshold = self.config.get("conservative_threshold", 0.8)

        if signal_counts.get("BUY", 0) / total >= conservative_threshold:
            return "BUY"

        if signal_counts.get("SELL", 0) / total >= conservative_threshold:
            return "SELL"

        return "HOLD"

    def _aggregate_threshold(
        self, signals: Dict[str, str], weights: Dict[str, float]
    ) -> str:
        """
        Threshold-based aggregation with separate thresholds for BUY and SELL.
        """
        weighted_scores = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0}
        total_weight = 0.0

        for indicator, signal in signals.items():
            weight = weights.get(indicator, 1.0)
            weighted_scores[signal] += weight
            total_weight += weight

        if total_weight == 0:
            return "HOLD"

        buy_ratio = weighted_scores["BUY"] / total_weight
        sell_ratio = weighted_scores["SELL"] / total_weight

        # Check custom thresholds
        if buy_ratio >= self.buy_threshold and buy_ratio > sell_ratio:
            return "BUY"

        if sell_ratio >= self.sell_threshold and sell_ratio > buy_ratio:
            return "SELL"

        return "HOLD"

    def get_signal_breakdown(
        self, signals: Dict[str, str], weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Get detailed breakdown of signal aggregation.

        Returns:
            Dictionary with signal counts, weighted scores, and final signal
        """
        if weights is None:
            weights = {k: 1.0 for k in signals}

        signal_counts = Counter(signals.values())

        weighted_scores = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0}
        total_weight = sum(weights.get(k, 1.0) for k in signals)

        for indicator, signal in signals.items():
            weight = weights.get(indicator, 1.0)
            if signal in weighted_scores:
                weighted_scores[signal] += weight

        # Normalize
        if total_weight > 0:
            weighted_scores = {k: v / total_weight for k, v in weighted_scores.items()}

        return {
            "counts": dict(signal_counts),
            "weighted_scores": weighted_scores,
            "total_indicators": len(signals),
            "total_weight": total_weight,
            "final_signal": self.aggregate(signals, weights),
            "strategy": self.strategy,
        }

    def __repr__(self):
        return f"SignalAggregator(strategy='{self.strategy}', min_agreement={self.min_agreement})"
