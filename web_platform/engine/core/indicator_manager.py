"""
Indicator Manager

Loads, manages, and executes all indicators in the system.
Provides plug-and-play functionality for indicators.
"""

import pandas as pd
from typing import List, Dict, Any
from engine.core.base_indicator import BaseIndicator


class IndicatorManager:
    """
    Manages all indicators and executes them on data.
    """
    
    def __init__(self):
        """Initialize the indicator manager."""
        self.indicators: List[BaseIndicator] = []
        self.results: Dict[str, pd.DataFrame] = {}
        self.signals: Dict[str, str] = {}
        self.weights: Dict[str, float] = {}
    
    def register_indicator(self, indicator: BaseIndicator):
        """
        Register a new indicator.
        
        Args:
            indicator: Instance of BaseIndicator subclass
        """
        if not isinstance(indicator, BaseIndicator):
            raise TypeError(f"{indicator} must be an instance of BaseIndicator")
        
        self.indicators.append(indicator)
        self.weights[indicator.name] = indicator.weight
        print(f"✅ Registered indicator: {indicator}")
    
    def register_multiple(self, indicators: List[BaseIndicator]):
        """
        Register multiple indicators at once.
        
        Args:
            indicators: List of BaseIndicator instances
        """
        for indicator in indicators:
            self.register_indicator(indicator)
    
    def remove_indicator(self, name: str):
        """
        Remove an indicator by name.
        
        Args:
            name: Name of the indicator to remove
        """
        self.indicators = [ind for ind in self.indicators if ind.name != name]
        if name in self.weights:
            del self.weights[name]
        print(f"❌ Removed indicator: {name}")
    
    def get_indicator(self, name: str) -> BaseIndicator:
        """
        Get an indicator by name.
        
        Args:
            name: Name of the indicator
        
        Returns:
            BaseIndicator instance or None
        """
        for indicator in self.indicators:
            if indicator.name == name:
                return indicator
        return None
    
    def list_indicators(self) -> List[str]:
        """
        Get list of all registered indicator names.
        
        Returns:
            List of indicator names
        """
        return [ind.name for ind in self.indicators if ind.enabled]
    
    def execute_all(self, df: pd.DataFrame, verbose: bool = False) -> Dict[str, str]:
        """
        Execute all enabled indicators on the data.
        
        Args:
            df: DataFrame with OHLCV data
            verbose: Print detailed execution info
        
        Returns:
            Dict mapping indicator name to latest signal
        """
        self.results = {}
        self.signals = {}
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"🔍 Executing {len([i for i in self.indicators if i.enabled])} indicators...")
            print(f"{'='*60}\n")
        
        for indicator in self.indicators:
            if not indicator.enabled:
                if verbose:
                    print(f"⏭️  Skipping disabled indicator: {indicator.name}")
                continue
            
            try:
                # Validate data
                if not indicator.validate_data(df):
                    if verbose:
                        print(f"⚠️  {indicator.name}: Data validation failed")
                    continue
                
                # Execute indicator
                if verbose:
                    print(f"⚙️  Calculating: {indicator.name}...")
                
                result_df = indicator.calculate(df.copy())
                
                # Store results
                self.results[indicator.name] = result_df
                
                # Get latest signal
                signal = indicator.get_latest_signal(result_df)
                self.signals[indicator.name] = signal
                
                if verbose:
                    print(f"   ✅ {indicator.name}: {signal} (weight: {indicator.weight})")
                
            except Exception as e:
                print(f"❌ Error in {indicator.name}: {str(e)}")
                self.signals[indicator.name] = 'HOLD'
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"✅ Execution complete!")
            print(f"{'='*60}\n")
        
        return self.signals
    
    def get_results(self, indicator_name: str = None) -> pd.DataFrame:
        """
        Get execution results for an indicator.
        
        Args:
            indicator_name: Name of specific indicator, or None for all
        
        Returns:
            DataFrame with indicator results
        """
        if indicator_name:
            return self.results.get(indicator_name)
        return self.results
    
    def get_signals(self) -> Dict[str, str]:
        """
        Get all latest signals.
        
        Returns:
            Dict mapping indicator name to signal
        """
        return self.signals
    
    def get_weights(self) -> Dict[str, float]:
        """
        Get all indicator weights.
        
        Returns:
            Dict mapping indicator name to weight
        """
        return self.weights
    
    def get_signal_summary(self) -> pd.DataFrame:
        """
        Get summary of all indicator signals.
        
        Returns:
            DataFrame with indicator signals and weights
        """
        data = []
        for name, signal in self.signals.items():
            data.append({
                'Indicator': name,
                'Signal': signal,
                'Weight': self.weights.get(name, 1.0)
            })
        
        return pd.DataFrame(data)
    
    def clear(self):
        """Clear all indicators and results."""
        self.indicators = []
        self.results = {}
        self.signals = {}
        self.weights = {}
        print("🧹 Cleared all indicators")
    
    def __len__(self):
        return len([i for i in self.indicators if i.enabled])
    
    def __str__(self):
        enabled = len([i for i in self.indicators if i.enabled])
        total = len(self.indicators)
        return f"IndicatorManager ({enabled}/{total} enabled)"
