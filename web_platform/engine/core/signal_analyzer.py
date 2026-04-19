"""
Signal Analyzer Module

Handles symbol analysis, signal generation, and exit logic coordination.
"""

import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, List


class SignalAnalyzer:
    """
    Analyzes symbols and generates trading signals.
    
    This class coordinates:
    - Indicator signal execution
    - Signal aggregation
    - Exit condition checking
    - Timestamp parsing from dataframes
    
    Attributes:
        config: Trading configuration dictionary
        indicator_manager: Reference to IndicatorManager
        signal_aggregator: Reference to SignalAggregator
        volatility_analyzer: Reference to VolatilityAnalyzer (optional)
        exit_manager: Reference to ExitStrategyManager (optional)
    """
    
    def __init__(
        self,
        config: Dict[str, Any] = None,
        indicator_manager=None,
        signal_aggregator=None,
        volatility_analyzer=None,
        exit_manager=None
    ):
        """
        Initialize the SignalAnalyzer.
        
        Args:
            config: Trading configuration dictionary
            indicator_manager: IndicatorManager instance
            signal_aggregator: SignalAggregator instance
            volatility_analyzer: VolatilityAnalyzer instance (optional)
            exit_manager: ExitStrategyManager instance (optional)
        """
        self.config = config or {}
        self.indicator_manager = indicator_manager
        self.signal_aggregator = signal_aggregator
        self.volatility_analyzer = volatility_analyzer
        self.exit_manager = exit_manager
        
        # Track day open prices
        self.day_open_prices = {}
    
    def reload_config(self, config: Dict[str, Any]):
        """
        Reload configuration with new config.
        
        Args:
            config: New trading configuration dictionary
        """
        self.config = config
    
    def set_day_open_price(self, symbol: str, price: float):
        """
        Set the day open price for a symbol.
        
        Args:
            symbol: Trading symbol
            price: Day opening price
        """
        self.day_open_prices[symbol] = price
    
    def get_day_open_price(self, symbol: str, df: pd.DataFrame = None) -> float:
        """
        Get the day open price for a symbol.
        
        Args:
            symbol: Trading symbol
            df: Optional DataFrame to get open price from if not cached
        
        Returns:
            Day open price
        """
        if symbol in self.day_open_prices:
            return self.day_open_prices[symbol]
        
        if df is not None and not df.empty and 'open' in df.columns:
            return df['open'].iloc[0]
        
        return 0.0
    
    def parse_timestamp_from_df(self, df: pd.DataFrame) -> datetime:
        """
        Parse timestamp from a DataFrame's last row.
        
        Tries multiple sources:
        1. 'datetime' column (string format from FyersData)
        2. 'date' column (arrow time object)
        3. DataFrame index
        
        Args:
            df: DataFrame with time data
        
        Returns:
            Parsed datetime or current time
        """
        current_timestamp = datetime.now()
        
        if df.empty:
            return current_timestamp
        
        # Try 'datetime' column first (formatted string from FyersData)
        if 'datetime' in df.columns:
            last_datetime_str = df['datetime'].iloc[-1]
            try:
                if isinstance(last_datetime_str, str):
                    # Format: "MM-DD-YYYY HH:mm:ss" from DATA_SOURCE.py
                    current_timestamp = pd.to_datetime(
                        last_datetime_str, 
                        format='%m-%d-%Y %H:%M:%S'
                    ).to_pydatetime()
                elif isinstance(last_datetime_str, pd.Timestamp):
                    current_timestamp = last_datetime_str.to_pydatetime()
                elif isinstance(last_datetime_str, datetime):
                    current_timestamp = last_datetime_str
            except:
                pass
            else:
                return current_timestamp
        
        # Fallback to 'date' column (arrow time object)
        if 'date' in df.columns:
            last_date = df['date'].iloc[-1]
            try:
                if hasattr(last_date, 'datetime'):
                    current_timestamp = last_date.datetime
                elif isinstance(last_date, pd.Timestamp):
                    current_timestamp = last_date.to_pydatetime()
                elif isinstance(last_date, datetime):
                    current_timestamp = last_date
                else:
                    current_timestamp = pd.to_datetime(last_date).to_pydatetime()
            except:
                pass
            else:
                return current_timestamp
        
        # Fallback to index if it's datetime-like
        if hasattr(df.index, '__len__') and len(df.index) > 0:
            last_index = df.index[-1]
            try:
                if isinstance(last_index, pd.Timestamp):
                    current_timestamp = last_index.to_pydatetime()
                elif isinstance(last_index, datetime):
                    current_timestamp = last_index
                elif isinstance(last_index, str):
                    current_timestamp = pd.to_datetime(last_index).to_pydatetime()
            except:
                pass
        
        return current_timestamp
    
    def generate_signals(
        self,
        df: pd.DataFrame,
        symbol: str,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Generate trading signals from DataFrame.
        
        Args:
            df: DataFrame with OHLCV data
            symbol: Trading symbol
            verbose: Print detailed analysis
        
        Returns:
            Dictionary with signal results
        """
        if self.indicator_manager is None or self.signal_aggregator is None:
            raise ValueError("indicator_manager and signal_aggregator must be set")
        
        # Execute all indicators
        indicator_signals = self.indicator_manager.execute_all(df, verbose=verbose)
        
        # Get indicator weights
        weights = self.indicator_manager.get_weights()
        
        # Aggregate signals
        final_signal = self.signal_aggregator.aggregate(indicator_signals, weights)
        
        # Get signal breakdown
        signal_breakdown = self.signal_aggregator.get_signal_breakdown(indicator_signals)
        
        # Get agreement score
        agreement_score = self.signal_aggregator.get_agreement_score(indicator_signals)
        
        # Get latest price and change
        latest_price = df['close'].iloc[-1]
        day_open_price = self.get_day_open_price(symbol, df)
        change = latest_price - day_open_price
        change_pct = (change / day_open_price) * 100 if day_open_price != 0 else 0
        
        # Get timestamp from dataframe
        current_timestamp = self.parse_timestamp_from_df(df)
        
        result = {
            'symbol': symbol,
            'latest_price': latest_price,
            'indicator_signals': indicator_signals,
            'final_signal': final_signal,
            'signal_breakdown': signal_breakdown,
            'agreement_score': agreement_score,
            'change': change,
            'change_pct': change_pct,
            'timestamp': current_timestamp
        }
        
        return result
    
    def add_volatility_analysis(
        self,
        result: Dict[str, Any],
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Add volatility analysis to signal results.
        
        Args:
            result: Existing signal results dictionary
            df: DataFrame with OHLCV data
        
        Returns:
            Updated result dictionary with volatility data
        """
        if self.volatility_analyzer is None:
            return result
        
        vol_method = self.config.get('volatility', {}).get('calculation_method', 'garman_klass')
        vol_analysis = self.volatility_analyzer.get_comprehensive_volatility(df, method=vol_method)
        result['volatility'] = vol_analysis
        
        return result
    
    def check_exit_conditions(
        self,
        position: Dict[str, Any],
        current_price: float,
        df: pd.DataFrame = None
    ) -> Optional[Dict[str, Any]]:
        """
        Check if a position should exit.
        
        Args:
            position: Position data dictionary
            current_price: Current market price
            df: Optional DataFrame for additional analysis
        
        Returns:
            Exit signal dictionary or None
        """
        if self.exit_manager is None or self.volatility_analyzer is None:
            return None
        
        # Calculate volatility
        vol_method = self.config.get('volatility', {}).get('calculation_method', 'garman_klass')
        vol_analysis = self.volatility_analyzer.get_comprehensive_volatility(df, method=vol_method)
        
        # Get recent prices and volumes for microstructure
        recent_prices = df['close'].tail(10).tolist() if df is not None else []
        recent_volumes = None
        if df is not None and 'volume' in df.columns:
            recent_volumes = df['volume'].tail(10).tolist()
        
        # Check if position should exit
        exit_signal = self.exit_manager.should_exit_position(
            position=position,
            current_price=current_price,
            current_time=datetime.now(),
            atr=vol_analysis['atr'],
            volatility_regime=vol_analysis['regime'],
            recent_prices=recent_prices,
            recent_volumes=recent_volumes
        )
        
        return exit_signal
    
    def check_candle_closure_exit(
        self,
        symbol: str,
        position: Dict[str, Any],
        latest_price: float,
        last_candle_closure_time: Dict[str, datetime]
    ) -> Optional[Dict[str, Any]]:
        """
        Check if candle closure exit should trigger.
        
        Args:
            symbol: Trading symbol
            position: Position data dictionary
            latest_price: Current price
            last_candle_closure_time: Dict tracking last closure times
        
        Returns:
            Exit info dictionary or None if no exit
        """
        current_time = datetime.now()
        backtest_enabled = self.config.get('backtest', {}).get('enabled', False)
        
        # Get candle closure exit configuration
        candle_closure_config = self.config.get('risk_management', {}).get('candle_closure_exit', {})
        candle_closure_enabled = candle_closure_config.get('enabled', True)
        candle_closure_resolution = candle_closure_config.get('resolution', '30S')
        candle_closure_loss_limit = float(candle_closure_config.get('loss_limit', 0.0) or 0.0)
        
        # Get current resolution
        current_resolution = self.config.get('resolution', None)
        if current_resolution is None:
            current_resolution = self.config.get('date_range', {}).get('resolution', '1min')
        
        # Only apply in intraday mode if enabled and resolution matches
        if backtest_enabled or not candle_closure_enabled:
            return None
        
        if current_resolution != candle_closure_resolution:
            return None
        
        # Calculate candle interval in seconds
        resolution_to_seconds = {'30S': 30, '1': 60, '5': 300}
        candle_interval = resolution_to_seconds.get(candle_closure_resolution, 30)
        
        # Initialize closure time if needed
        if symbol not in last_candle_closure_time:
            last_candle_closure_time[symbol] = self._round_to_candle_time(
                current_time, 
                candle_closure_resolution
            )
        
        last_closure = last_candle_closure_time[symbol]
        seconds_since_closure = (current_time - last_closure).total_seconds()
        
        # Check if candle interval has passed
        if seconds_since_closure < candle_interval:
            return None
        
        # Calculate current PnL
        entry_price = position.get('entry_price', 0)
        position_type = position.get('type', 'LONG')
        quantity = position.get('quantity', 0)
        
        if position_type == 'LONG':
            current_pnl = (latest_price - entry_price) * quantity
        else:
            current_pnl = (entry_price - latest_price) * quantity
        
        # Check if in loss and meets limit
        if current_pnl < 0 and (candle_closure_loss_limit <= 0 or abs(current_pnl) >= candle_closure_loss_limit):
            # Update closure time
            last_candle_closure_time[symbol] = self._round_to_candle_time(
                current_time, 
                candle_closure_resolution
            )
            
            return {
                'should_exit': True,
                'reason': f"Candle closure exit (loss) - {candle_closure_resolution}",
                'pnl': current_pnl,
                'timestamp': current_time
            }
        else:
            # Update closure time but no exit
            last_candle_closure_time[symbol] = self._round_to_candle_time(
                current_time, 
                candle_closure_resolution
            )
            return None
    
    def _round_to_candle_time(self, time: datetime, resolution: str) -> datetime:
        """
        Round time down to nearest candle boundary.
        
        Args:
            time: Time to round
            resolution: Candle resolution ('30S', '1', '5')
        
        Returns:
            Rounded datetime
        """
        if resolution == '30S':
            rounded_second = (time.second // 30) * 30
            return time.replace(second=rounded_second, microsecond=0)
        elif resolution == '1':
            return time.replace(second=0, microsecond=0)
        elif resolution == '5':
            rounded_minute = (time.minute // 5) * 5
            return time.replace(minute=rounded_minute, second=0, microsecond=0)
        else:
            return time.replace(microsecond=0)
    
    def print_analysis(self, result: Dict[str, Any]):
        """
        Print detailed analysis results.
        
        Args:
            result: Analysis result dictionary
        """
        print(f"\n{'='*70}")
        print(f"📊 ANALYSIS: {result['symbol']}")
        print(f"{'='*70}")
        print(f"💰 Latest Price: ₹{result['latest_price']:.2f}")
        print(f"🎯 Final Signal: {result['final_signal']}")
        print(f"🤝 Agreement: {result['agreement_score']:.1%}")
        print(f"\nSignal Breakdown: {result['signal_breakdown']}")
        print(f"\nIndividual Indicators:")
        for indicator, signal in result['indicator_signals'].items():
            print(f"   {indicator:20s}: {signal}")
        print(f"{'='*70}\n")
    
    def get_entry_reason(self, result: Dict[str, Any]) -> str:
        """
        Generate entry reason string from analysis result.
        
        Args:
            result: Analysis result dictionary
        
        Returns:
            Entry reason string
        """
        signal = result.get('final_signal', 'HOLD')
        agreement = result.get('agreement_score', 0)
        breakdown = result.get('signal_breakdown', {})
        
        buy_count = breakdown.get('BUY', 0)
        sell_count = breakdown.get('SELL', 0)
        total = buy_count + sell_count + breakdown.get('HOLD', 0)
        
        if signal == 'BUY':
            return f"BUY signal ({buy_count}/{total} indicators, {agreement:.0%} agreement)"
        elif signal == 'SELL':
            return f"SELL signal ({sell_count}/{total} indicators, {agreement:.0%} agreement)"
        else:
            return f"{signal} signal ({agreement:.0%} agreement)"
