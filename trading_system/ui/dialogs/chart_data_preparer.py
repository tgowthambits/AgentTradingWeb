"""
Chart Data Preparation Module

Provides utility functions to prepare chart data without instantiating dialogs.
"""

import pandas as pd
from typing import Dict, List, Any


class ChartDataPreparer:
    """
    Utility class for preparing chart data.
    Does not create any UI elements - pure data processing.
    """
    
    @staticmethod
    def prepare_candle_data(candle_data: pd.DataFrame) -> List[Dict]:
        """
        Convert DataFrame to format required by Lightweight Charts.
        
        Args:
            candle_data: DataFrame with OHLCV data
            
        Returns:
            List of dictionaries with time, open, high, low, close, volume
        """
        if candle_data.empty:
            return []
        
        data = []
        df = candle_data.copy()
        
        # Ensure we have a datetime column
        time_col = None
        for col in ['datetime', 'date', 'time', 'timestamp']:
            if col in df.columns:
                time_col = col
                break
        
        if time_col is None:
            # Try to use index if it's datetime
            if isinstance(df.index, pd.DatetimeIndex):
                df['datetime'] = df.index
                time_col = 'datetime'
            else:
                print("Warning: No datetime column found in candle data")
                return []
        
        for _, row in df.iterrows():
            try:
                # Convert timestamp to Unix timestamp
                timestamp = row[time_col]
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                
                unix_time = int(timestamp.timestamp())
                
                candle = {
                    'time': unix_time,
                    'open': float(row.get('open', 0)),
                    'high': float(row.get('high', 0)),
                    'low': float(row.get('low', 0)),
                    'close': float(row.get('close', 0)),
                    'volume': float(row.get('volume', 0))
                }
                data.append(candle)
            except Exception as e:
                print(f"Error processing candle data row: {e}")
                continue
        
        # Sort by time
        data.sort(key=lambda x: x['time'])
        return data
    
    @staticmethod
    def prepare_trade_markers(trades: List[Dict], candle_data: pd.DataFrame) -> List[Dict]:
        """
        Convert trades to marker format for Lightweight Charts.
        
        Args:
            trades: List of trade dictionaries
            candle_data: DataFrame with candlestick data
            
        Returns:
            List of marker dictionaries
        """
        if not trades:
            return []
        
        # Get available candle timestamps
        candle_timestamps = set()
        if not candle_data.empty:
            time_col = None
            for col in ['datetime', 'date', 'time', 'timestamp']:
                if col in candle_data.columns:
                    time_col = col
                    break
            
            if time_col:
                for _, row in candle_data.iterrows():
                    try:
                        ts = row[time_col]
                        if isinstance(ts, str):
                            ts = pd.to_datetime(ts)
                        candle_timestamps.add(int(ts.timestamp()))
                    except:
                        continue
        
        def find_nearest_candle_time(trade_time):
            """Find the nearest available candle timestamp."""
            if not candle_timestamps:
                if isinstance(trade_time, str):
                    trade_time = pd.to_datetime(trade_time)
                return int(trade_time.timestamp())
            
            if isinstance(trade_time, str):
                trade_time = pd.to_datetime(trade_time)
            
            trade_timestamp = int(trade_time.timestamp())
            nearest = min(candle_timestamps, key=lambda x: abs(x - trade_timestamp))
            return nearest
        
        markers = []
        
        for trade in trades:
            try:
                # Entry marker (Buy)
                entry_time = trade.get('entry_time') or trade.get('entry_datetime')
                if entry_time:
                    entry_timestamp = find_nearest_candle_time(entry_time)
                    
                    entry_marker = {
                        'time': entry_timestamp,
                        'position': 'belowBar',
                        'color': '#26a69a',
                        'shape': 'arrowUp',
                        'text': 'BUY',
                        'size': 1
                    }
                    markers.append(entry_marker)
                
                # Exit marker (Sell)
                exit_time = trade.get('exit_time') or trade.get('exit_datetime')
                if exit_time:
                    exit_timestamp = find_nearest_candle_time(exit_time)
                    
                    pnl = trade.get('pnl', 0)
                    quantity = trade.get('quantity', 0)
                    try:
                        quantity = int(quantity)
                    except Exception:
                        quantity = 0
                    try:
                        pnl_value = float(pnl)
                    except Exception:
                        pnl_value = 0.0
                    pnl_text = f"{pnl_value:.2f}"
                    marker_color = '#26a69a' if pnl >= 0 else '#ef5350'
                    
                    exit_marker = {
                        'time': exit_timestamp,
                        'position': 'aboveBar',
                        'color': marker_color,
                        'shape': 'arrowDown',
                        'text': f"SELL q={quantity} pl={pnl_text}",
                        'size': 1
                    }
                    markers.append(exit_marker)
                    
            except Exception as e:
                print(f"Error processing trade marker: {e}")
                continue
        
        # Sort by time and remove duplicates
        markers.sort(key=lambda x: x['time'])
        
        unique_markers = []
        seen = set()
        
        for marker in markers:
            key = (marker['time'], marker['position'])
            if key not in seen:
                unique_markers.append(marker)
                seen.add(key)
        
        return unique_markers
    
    @staticmethod
    def prepare_trade_data_for_js(trades: List[Dict], candle_data: pd.DataFrame) -> List[Dict]:
        """
        Prepare trade data for JavaScript with aligned timestamps.
        
        Args:
            trades: List of trade dictionaries
            candle_data: DataFrame with candlestick data
            
        Returns:
            List of trade dictionaries with Unix timestamps
        """
        if not trades:
            return []
        
        # Get available candle timestamps
        candle_timestamps = set()
        if not candle_data.empty:
            time_col = None
            for col in ['datetime', 'date', 'time', 'timestamp']:
                if col in candle_data.columns:
                    time_col = col
                    break
            
            if time_col:
                for _, row in candle_data.iterrows():
                    try:
                        ts = row[time_col]
                        if isinstance(ts, str):
                            ts = pd.to_datetime(ts)
                        candle_timestamps.add(int(ts.timestamp()))
                    except:
                        continue
        
        def find_nearest_candle_time(trade_time):
            """Find the nearest available candle timestamp."""
            if not candle_timestamps:
                if isinstance(trade_time, str):
                    trade_time = pd.to_datetime(trade_time)
                return int(trade_time.timestamp())
            
            if isinstance(trade_time, str):
                trade_time = pd.to_datetime(trade_time)
            
            trade_timestamp = int(trade_time.timestamp())
            nearest = min(candle_timestamps, key=lambda x: abs(x - trade_timestamp))
            return nearest
        
        trade_data = []
        for trade in trades:
            try:
                entry_time = trade.get('entry_time') or trade.get('entry_datetime')
                exit_time = trade.get('exit_time') or trade.get('exit_datetime')
                
                trade_dict = {
                    'entry_time': find_nearest_candle_time(entry_time) if entry_time else None,
                    'exit_time': find_nearest_candle_time(exit_time) if exit_time else None,
                    'entry_price': float(trade.get('entry_price', 0)),
                    'exit_price': float(trade.get('exit_price', 0)),
                    'quantity': int(trade.get('quantity', 0)),
                    'pnl': float(trade.get('pnl', 0)),
                    'exit_reason': str(trade.get('exit_reason', 'N/A')),
                    'paper_trade': bool(trade.get('paper_trade', False))
                }
                trade_data.append(trade_dict)
            except Exception as e:
                print(f"Error preparing trade data: {e}")
                continue
        
        return trade_data
    
    @staticmethod
    def calculate_symbol_stats(trades: List[Dict]) -> Dict[str, Any]:
        """
        Calculate statistics for the symbol based on trades.
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            Dictionary with totalTrades, winRate, totalPnL
        """
        if not trades:
            return {
                'totalTrades': 0,
                'winRate': 0,
                'totalPnL': 0
            }
        
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        
        return {
            'totalTrades': total_trades,
            'winRate': win_rate,
            'totalPnL': total_pnl
        }
