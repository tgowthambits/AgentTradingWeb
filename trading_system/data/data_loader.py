
"""
Data Loader

Handles loading and preprocessing of market data from various sources.
"""

import pandas as pd
import sys
import os

# Add parent directory to path to import from existing modules
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

try:
    from Data.fyers_data_final import FyersDataScanner
except ImportError:
    print("Warning: Could not import FyersDataScanner. Data loading may not work.")
    FyersDataScanner = None


class BacktestDataGenerator:
    """
    Generates progressive data slices for backtesting.
    Each call returns one more row than previous call.
    """
    
    def __init__(self, symbol: str, start_date: str, end_date: str, resolution: str):
        """Initialize backtest data generator."""
        self.symbol = symbol
        self.full_data = None  # Cached full dataset
        self.current_index = 0  # Current iteration
        
        if not FyersDataScanner:
            raise RuntimeError("FyersDataScanner not available for backtesting")
        
        self.scanner = FyersDataScanner()
        
        # Fetch all data once at initialization
        self.scanner.start_date = start_date
        self.scanner.end_date = end_date
        self.scanner.symbol = symbol
        self.scanner.resolution = resolution
        
        print(f"📥 Fetching all data for {symbol}...")
        self.full_data = self.scanner.get_data()
        
        # Standardize columns
        self.full_data = self.full_data.rename(columns={
            'Time': 'time',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'TradeVol': 'volume',
            'date': 'date',
            'datetime': 'datetime'
        })
        
        print(f"✅ Loaded {len(self.full_data)} rows for backtesting")
    
    def get_next_slice(self) -> pd.DataFrame:
        """
        Returns progressively larger slices of data.
        Call 1: rows 0:1, Call 2: rows 0:2, etc.
        
        Returns:
            DataFrame with rows from 0 to current_index, or None if complete
        """
        if self.current_index >= len(self.full_data):
            return None  # Backtest complete
        
        self.current_index += 1
        return self.full_data.iloc[:self.current_index].copy()
    
    def reset(self):
        """Reset generator to start."""
        self.current_index = 0
    
    def is_complete(self) -> bool:
        """Check if backtest is complete."""
        return self.current_index >= len(self.full_data)

    def get_full_data(self) -> pd.DataFrame:
        """Return the full cached dataset."""
        return self.full_data.copy() if self.full_data is not None else pd.DataFrame()
    
    def progress(self) -> dict:
        """Return backtest progress information."""
        total = len(self.full_data)
        return {
            'current': self.current_index,
            'total': total,
            'percent': (self.current_index / total * 100) if total > 0 else 0
        }


class DataLoader:
    """
    Loads market data for trading analysis.
    Supports both real-time and backtest modes.
    """
    
    def __init__(self, backtest_mode=False, backtest_config=None):
        """
        Initialize the data loader.
        
        Args:
            backtest_mode: If True, use progressive data slicing for backtesting
            backtest_config: Dict with backtest configuration (start_date, end_date, etc.)
        """
        self.backtest_mode = backtest_mode
        self.backtest_config = backtest_config or {}
        self.generators = {}  # Symbol -> BacktestDataGenerator mapping
        
        if FyersDataScanner:
            self.scanner = FyersDataScanner()
        else:
            self.scanner = None
    
    def load_symbol_data(self, symbol: str, start_date: str, end_date: str, 
                        resolution: str = '5S') -> pd.DataFrame:
        """
        Load data for a single symbol.
        In backtest mode, returns progressive slices. In live mode, returns latest data.
        
        Args:
            symbol: Trading symbol (e.g., "BSE:SENSEX2610185100PE")
            start_date: Start date/time (e.g., '2025-12-27 16:15:00')
            end_date: End date/time (e.g., '2025-12-29 16:15:00')
            resolution: Data resolution ('1'=daily, '5S'=5-second, etc.)
        
        Returns:
            DataFrame with OHLCV data and standardized column names
        """
        if self.backtest_mode:
            # Backtest mode: progressive data slicing
            # Initialize generator if not exists
            if symbol not in self.generators:
                bt_start = self.backtest_config.get('start_date', start_date)
                bt_end = self.backtest_config.get('end_date', end_date)
                
                self.generators[symbol] = BacktestDataGenerator(
                    symbol=symbol,
                    start_date=bt_start,
                    end_date=bt_end,
                    resolution=resolution
                )
            
            # Get next progressive slice
            df = self.generators[symbol].get_next_slice()
            if df is None:
                raise StopIteration(f"Backtest complete for {symbol}")
            
            return df
        else:
            # Live mode: fetch latest data from API
            if not self.scanner:
                raise RuntimeError("FyersDataScanner not available")
            
            # Configure scanner
            self.scanner.start_date = start_date
            self.scanner.end_date = end_date
            self.scanner.symbol = symbol
            self.scanner.resolution = resolution
            
            # Get data
            df = self.scanner.get_data()
            
            # Standardize column names
            df = df.rename(columns={
                'Time': 'time',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'TradeVol': 'volume',
                'date': 'date',
                'datetime': 'datetime'
            })
            
            # Ensure we have required columns
            required_cols = ['open', 'high', 'low', 'close']
            missing = [col for col in required_cols if col not in df.columns]
            if missing:
                raise ValueError(f"Missing required columns: {missing}")
            
            # Sort by date if available
            if 'date' in df.columns:
                df = df.sort_values(by='date').reset_index(drop=True)
            
            return df
    
    def load_multiple_symbols(self, symbols: list, start_date: str, end_date: str,
                             resolution: str = '1') -> dict:
        """
        Load data for multiple symbols.
        
        Args:
            symbols: List of trading symbols
            start_date: Start date/time
            end_date: End date/time
            resolution: Data resolution
        
        Returns:
            Dict mapping symbol to DataFrame
        """
        data = {}
        
        for symbol in symbols:
            try:
                df = self.load_symbol_data(symbol, start_date, end_date, resolution)
                data[symbol] = df
                print(f"✅ Loaded {len(df)} rows for {symbol}")
            except Exception as e:
                print(f"❌ Error loading {symbol}: {str(e)}")
                data[symbol] = None
        
        return data

    def get_all_backtest_data(self, symbols: list, start_date: str, end_date: str, resolution: str = '1') -> dict:
        """
        Load all historical data for backtesting at once.
        
        Returns:
            Dict mapping symbol to full DataFrame.
        """
        data = {}
        for symbol in symbols:
            try:
                generator = BacktestDataGenerator(symbol, start_date, end_date, resolution)
                data[symbol] = generator.get_full_data()
            except Exception as e:
                print(f"Error loading all data for {symbol}: {e}")
                data[symbol] = None
        return data
    
    def prepare_for_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare DataFrame for indicator calculation.
        
        Ensures all required columns exist and data is clean.
        
        Args:
            df: Raw DataFrame
        
        Returns:
            Cleaned DataFrame ready for indicators
        """
        # Drop NaN values in OHLC columns
        df = df.dropna(subset=['open', 'high', 'low', 'close'])
        
        # Add volume if missing
        if 'volume' not in df.columns:
            df['volume'] = 0
        
        # Reset index
        df = df.reset_index(drop=True)
        
        return df

