"""
Signal Aggregator

Combines signals from multiple indicators using various strategies
(majority voting, weighted voting, unanimous, etc.)
"""

import pandas as pd
from typing import List, Dict
from collections import Counter


class SignalAggregator:
    """
    Aggregates signals from multiple indicators into a final trading signal.
    """
    
    def __init__(self, strategy: str = 'majority', min_agreement: float = 0.5, 
                 threshold_config: dict = None):
        """
        Initialize the signal aggregator.
        
        Args:
            strategy: Aggregation strategy
                - 'majority': Majority voting
                - 'weighted': Weighted voting (uses indicator weights)
                - 'unanimous': All indicators must agree
                - 'conservative': Requires stronger agreement (configurable)
                - 'threshold': Minimum number of indicators must agree
            min_agreement: Minimum fraction of indicators that must agree (for conservative)
            threshold_config: Configuration for threshold-based aggregation
        """
        self.strategy = strategy
        self.min_agreement = min_agreement
        self.threshold_config = threshold_config or {
            'min_indicators_buy': 2,
            'min_indicators_sell': 2,
            'min_agreement_percent': 50
        }
    
    def aggregate(self, signals: Dict[str, str], weights: Dict[str, float] = None) -> str:
        """
        Aggregate multiple indicator signals into final signal.
        
        Args:
            signals: Dict mapping indicator name to signal ('BUY', 'SELL', 'HOLD')
            weights: Dict mapping indicator name to weight (optional)
        
        Returns:
            Final aggregated signal: 'BUY', 'SELL', or 'HOLD'
        """
        if not signals:
            return 'HOLD'
        
        if self.strategy == 'majority':
            return self._majority_vote(signals)
        
        elif self.strategy == 'weighted':
            return self._weighted_vote(signals, weights or {})
        
        elif self.strategy == 'unanimous':
            return self._unanimous_vote(signals)
        
        elif self.strategy == 'conservative':
            return self._conservative_vote(signals)
        
        elif self.strategy == 'threshold':
            return self._threshold_vote(signals)
        
        else:
            return self._majority_vote(signals)
    
    def _majority_vote(self, signals: Dict[str, str]) -> str:
        """
        Simple majority voting.
        
        Returns signal with most votes. If tie, returns HOLD.
        """
        signal_list = list(signals.values())
        counts = Counter(signal_list)
        
        # Get most common signal
        most_common = counts.most_common(1)[0]
        signal, count = most_common
        
        # Check if it's actually a majority
        if count > len(signal_list) / 2:
            return signal
        
        # No clear majority, check if BUY or SELL has plurality
        if signal in ['BUY', 'SELL']:
            return signal
        
        return 'HOLD'
    
    def _weighted_vote(self, signals: Dict[str, str], weights: Dict[str, float]) -> str:
        """
        Weighted voting using indicator weights.
        
        Each indicator's vote is multiplied by its weight.
        Requires both weighted average strength AND minimum percentage of
        active (non-HOLD) indicators agreeing before generating a signal.
        """
        signal_values = {'BUY': 1, 'SELL': -1, 'HOLD': 0}
        
        total_weight = 0
        weighted_sum = 0
        
        buy_count = sum(1 for s in signals.values() if s == 'BUY')
        sell_count = sum(1 for s in signals.values() if s == 'SELL')
        total_indicators = len(signals)
        
        for indicator, signal in signals.items():
            weight = weights.get(indicator, 1.0)
            value = signal_values.get(signal, 0)
            weighted_sum += value * weight
            total_weight += weight
        
        if total_weight == 0:
            return 'HOLD'
        
        avg = weighted_sum / total_weight
        
        # Require weighted average to clear a meaningful threshold
        threshold = max(0.20, self.min_agreement * 0.35)
        
        # Calculate directional percentages among ALL indicators
        buy_percent = (buy_count / total_indicators) if total_indicators > 0 else 0
        sell_percent = (sell_count / total_indicators) if total_indicators > 0 else 0
        
        # BUY/SELL must be the dominant directional signal (more than opposing)
        # and must meet minimum percentage of total indicators
        min_directional_pct = self.min_agreement * 0.55
        
        if (avg > threshold 
                and buy_percent >= min_directional_pct
                and buy_count > sell_count):
            return 'BUY'
        elif (avg < -threshold 
                and sell_percent >= min_directional_pct
                and sell_count > buy_count):
            return 'SELL'
        
        return 'HOLD'
    
    def _unanimous_vote(self, signals: Dict[str, str]) -> str:
        """
        Unanimous voting - all indicators must agree.
        
        If any indicator disagrees, returns HOLD.
        """
        unique_signals = set(signals.values())
        
        # Remove HOLD from unique signals for checking
        unique_without_hold = unique_signals - {'HOLD'}
        
        # If all agree on BUY or SELL
        if len(unique_without_hold) == 1:
            return list(unique_without_hold)[0]
        
        # If all are HOLD
        if unique_signals == {'HOLD'}:
            return 'HOLD'
        
        # Mixed signals
        return 'HOLD'
    
    def _conservative_vote(self, signals: Dict[str, str]) -> str:
        """
        Conservative voting - requires min_agreement fraction to agree.
        
        More conservative than majority, requires stronger consensus.
        """
        signal_list = list(signals.values())
        counts = Counter(signal_list)
        total = len(signal_list)
        
        for signal in ['BUY', 'SELL']:
            if counts[signal] >= (total * self.min_agreement):
                return signal
        
        return 'HOLD'
    
    def _threshold_vote(self, signals: Dict[str, str]) -> str:
        """
        Threshold-based voting - requires minimum number of indicators to agree.
        
        Uses configuration from threshold_config:
        - min_indicators_buy: Minimum indicators for BUY
        - min_indicators_sell: Minimum indicators for SELL
        - min_agreement_percent: Minimum agreement percentage
        """
        signal_list = list(signals.values())
        counts = Counter(signal_list)
        total = len(signal_list)
        
        min_buy = self.threshold_config.get('min_indicators_buy', 2)
        min_sell = self.threshold_config.get('min_indicators_sell', 2)
        min_percent = self.threshold_config.get('min_agreement_percent', 50)
        
        # Check BUY threshold
        buy_count = counts.get('BUY', 0)
        buy_percent = (buy_count / total * 100) if total > 0 else 0
        
        if buy_count >= min_buy and buy_percent >= min_percent:
            return 'BUY'
        
        # Check SELL threshold
        sell_count = counts.get('SELL', 0)
        sell_percent = (sell_count / total * 100) if total > 0 else 0
        
        if sell_count >= min_sell and sell_percent >= min_percent:
            return 'SELL'
        
        return 'HOLD'
    
    def get_signal_breakdown(self, signals: Dict[str, str]) -> Dict[str, int]:
        """
        Get breakdown of signals for analysis.
        
        Args:
            signals: Dict mapping indicator name to signal
        
        Returns:
            Dict with counts: {'BUY': 2, 'SELL': 1, 'HOLD': 3}
        """
        return dict(Counter(signals.values()))
    
    def get_agreement_score(self, signals: Dict[str, str]) -> float:
        """
        Calculate agreement score (0-1).
        
        Returns fraction of indicators agreeing with the majority.
        """
        if not signals:
            return 0.0
        
        signal_list = list(signals.values())
        counts = Counter(signal_list)
        most_common_count = counts.most_common(1)[0][1]
        
        return most_common_count / len(signal_list)

