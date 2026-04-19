"""
Example: Chart Viewer Usage

This script demonstrates how to use the ChartViewerDialog and MultiSymbolChartDialog
to visualize backtest results with candlestick charts and trade markers.
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from PySide6.QtWidgets import QApplication

from chart_viewer_dialog import ChartViewerDialog, MultiSymbolChartDialog


def generate_sample_data(symbol: str, num_candles: int = 500):
    """Generate sample candlestick data for demonstration."""
    
    # Generate timestamps
    start_time = datetime(2026, 1, 15, 9, 15, 0)
    timestamps = [start_time + timedelta(seconds=30*i) for i in range(num_candles)]
    
    # Generate price data with random walk
    np.random.seed(42)
    base_price = 100.0
    price_changes = np.random.randn(num_candles) * 2
    close_prices = base_price + np.cumsum(price_changes)
    
    # Generate OHLC data
    data = []
    for i, timestamp in enumerate(timestamps):
        close = close_prices[i]
        open_price = close_prices[i-1] if i > 0 else base_price
        
        # Random high/low within reasonable range
        high = max(open_price, close) + abs(np.random.randn()) * 0.5
        low = min(open_price, close) - abs(np.random.randn()) * 0.5
        
        # Volume
        volume = int(np.random.randint(1000, 10000))
        
        data.append({
            'datetime': timestamp,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    return df


def generate_sample_trades(symbol: str, candle_df: pd.DataFrame, num_trades: int = 10):
    """Generate sample trades for demonstration."""
    
    trades = []
    timestamps = candle_df['datetime'].tolist()
    prices = candle_df['close'].tolist()
    
    # Ensure we have enough data
    if len(timestamps) < num_trades * 2:
        return []
    
    for i in range(num_trades):
        # Random entry and exit indices
        entry_idx = np.random.randint(0, len(timestamps) - 20)
        exit_idx = entry_idx + np.random.randint(5, 15)
        
        if exit_idx >= len(timestamps):
            continue
        
        entry_price = prices[entry_idx]
        exit_price = prices[exit_idx]
        
        # Random quantity
        quantity = np.random.randint(5, 20)
        
        # Calculate PnL (assuming long position)
        pnl = (exit_price - entry_price) * quantity
        
        # Random exit reason
        exit_reasons = ['Target Hit', 'Stop Loss', 'Time Exit', 'Trailing Stop']
        exit_reason = np.random.choice(exit_reasons)
        
        trade = {
            'symbol': symbol,
            'entry_time': timestamps[entry_idx],
            'entry_datetime': timestamps[entry_idx],
            'entry_price': entry_price,
            'exit_time': timestamps[exit_idx],
            'exit_datetime': timestamps[exit_idx],
            'exit_price': exit_price,
            'quantity': quantity,
            'pnl': pnl,
            'exit_reason': exit_reason
        }
        
        trades.append(trade)
    
    return trades


def example_single_symbol_chart():
    """Example: Display chart for a single symbol."""
    
    app = QApplication(sys.argv)
    
    # Generate sample data
    symbol = "NSE:NIFTY2612025450PE"
    candle_df = generate_sample_data(symbol, num_candles=500)
    trades = generate_sample_trades(symbol, candle_df, num_trades=10)
    
    # Create and show dialog
    dialog = ChartViewerDialog(
        parent=None,
        symbol=symbol,
        candle_data=candle_df,
        trades=trades
    )
    
    dialog.exec()
    sys.exit(app.exec())


def example_multi_symbol_chart():
    """Example: Display charts for multiple symbols with dropdown selector."""
    
    app = QApplication(sys.argv)
    
    # Generate sample data for multiple symbols
    symbols = [
        "NSE:NIFTY2612025450PE",
        "NSE:NIFTY2612025450CE",
        "BSE:SENSEX2612282800PE",
        "BSE:SENSEX2612282800CE"
    ]
    
    symbol_data = {}
    symbol_trades = {}
    
    for symbol in symbols:
        # Generate candlestick data
        candle_df = generate_sample_data(symbol, num_candles=500)
        symbol_data[symbol] = candle_df
        
        # Generate trades
        trades = generate_sample_trades(symbol, candle_df, num_trades=10)
        symbol_trades[symbol] = trades
    
    # Create and show dialog
    dialog = MultiSymbolChartDialog(
        parent=None,
        symbol_data=symbol_data,
        symbol_trades=symbol_trades
    )
    
    dialog.exec()
    sys.exit(app.exec())


def example_from_csv():
    """Example: Load data from CSV files and display charts."""
    
    app = QApplication(sys.argv)
    
    # Example CSV structure:
    # datetime, open, high, low, close, volume
    # 2026-01-15 09:15:00, 100.0, 101.5, 99.5, 100.5, 5000
    
    try:
        # Load candlestick data from CSV
        candle_df = pd.read_csv('sample_candles.csv')
        candle_df['datetime'] = pd.to_datetime(candle_df['datetime'])
        
        # Load trades from CSV
        trades_df = pd.read_csv('sample_trades.csv')
        trades = trades_df.to_dict('records')
        
        # Create and show dialog
        symbol = "YOUR_SYMBOL"
        dialog = ChartViewerDialog(
            parent=None,
            symbol=symbol,
            candle_data=candle_df,
            trades=trades
        )
        
        dialog.exec()
        sys.exit(app.exec())
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please create sample_candles.csv and sample_trades.csv first")


if __name__ == "__main__":
    print("Chart Viewer Examples")
    print("=" * 50)
    print("1. Single Symbol Chart")
    print("2. Multi-Symbol Chart with Dropdown")
    print("3. Load from CSV")
    print()
    
    choice = input("Select example (1-3): ").strip()
    
    if choice == "1":
        example_single_symbol_chart()
    elif choice == "2":
        example_multi_symbol_chart()
    elif choice == "3":
        example_from_csv()
    else:
        print("Invalid choice. Running multi-symbol example...")
        example_multi_symbol_chart()
