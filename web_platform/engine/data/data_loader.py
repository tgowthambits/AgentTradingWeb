"""
Data Loader

Handles loading and preprocessing of market data.
Uses the Fyers API provider for data fetching (same as the original trading_system).
Also supports loading from CSV files or pre-loaded DataFrames.
"""

import logging
import pandas as pd
from pathlib import Path

logger = logging.getLogger("engine.data")

COLUMN_MAP = {
    'Time': 'time',
    'Open': 'open',
    'High': 'high',
    'Low': 'low',
    'Close': 'close',
    'TradeVol': 'volume',
    'date': 'date',
    'datetime': 'datetime',
}

REQUIRED_OHLC = ['open', 'high', 'low', 'close']

try:
    from engine.data.fyers_provider import FyersDataFetcher, is_available as _fyers_available
    if _fyers_available():
        _scanner = FyersDataFetcher()
    else:
        _scanner = None
except Exception:
    _scanner = None


class BacktestDataGenerator:
    """
    Generates progressive data slices for backtesting.
    Each call returns one more row than the previous call.
    """

    def __init__(self, symbol: str, start_date: str = None,
                 end_date: str = None, resolution: str = "1",
                 data: pd.DataFrame = None):
        """
        Initialize backtest data generator.

        Accepts EITHER:
          - (symbol, start_date, end_date, resolution) to fetch from Fyers API
          - (symbol, data=df) to use a pre-loaded DataFrame
        """
        self.symbol = symbol
        self.full_data = None
        self.current_index = 0

        if data is not None:
            self.full_data = data.copy()
        elif start_date and end_date:
            if _scanner is None:
                raise RuntimeError(
                    f"No data source available for {symbol}. "
                    "Install arrow/requests/omegaconf and provide fyers_config.yaml, "
                    "or pass data= directly."
                )
            print(f"Fetching all data for {symbol}...")
            self.full_data = _scanner.fetch(symbol, start_date, end_date, resolution)
            print(f"Loaded {len(self.full_data)} rows for backtesting")
        else:
            raise ValueError("Provide either (start_date, end_date) or data=DataFrame")

        self.full_data = self.full_data.rename(columns=COLUMN_MAP)

    def next_slice(self) -> pd.DataFrame | None:
        if self.current_index >= len(self.full_data):
            return None
        self.current_index += 1
        return self.full_data.iloc[:self.current_index].copy()

    get_next_slice = next_slice

    def reset(self):
        self.current_index = 0

    def is_complete(self) -> bool:
        return self.current_index >= len(self.full_data)

    def get_full_data(self) -> pd.DataFrame:
        return self.full_data.copy() if self.full_data is not None else pd.DataFrame()

    def progress(self) -> dict:
        total = len(self.full_data)
        return {
            'current': self.current_index,
            'total': total,
            'percent': (self.current_index / total * 100) if total > 0 else 0,
        }


class DataLoader:
    """
    Loads market data for trading analysis.
    Supports both real-time and backtest modes.
    """

    def __init__(self, backtest_mode=False, backtest_config=None):
        self.backtest_mode = backtest_mode
        self.backtest_config = backtest_config or {}
        self.generators: dict[str, BacktestDataGenerator] = {}

    def load_from_csv(self, filepath: str) -> pd.DataFrame:
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {filepath}")

        df = pd.read_csv(filepath)
        df = df.rename(columns=COLUMN_MAP)

        missing = [col for col in REQUIRED_OHLC if col not in df.columns]
        if missing:
            raise ValueError(f"CSV missing required columns: {missing}")

        if 'date' in df.columns:
            df = df.sort_values(by='date').reset_index(drop=True)
        elif 'time' in df.columns:
            df = df.sort_values(by='time').reset_index(drop=True)

        return df

    def load_from_dataframe(self, symbol: str, df: pd.DataFrame):
        self.generators[symbol] = BacktestDataGenerator(symbol=symbol, data=df)

    def load_symbol_data(self, symbol: str, start_date: str = None,
                         end_date: str = None, resolution: str = '5S') -> pd.DataFrame:
        """
        Load data for a single symbol.
        In backtest mode, returns progressive slices. In live mode, returns latest data.
        """
        if self.backtest_mode:
            if symbol not in self.generators:
                bt_start = self.backtest_config.get('start_date', start_date)
                bt_end = self.backtest_config.get('end_date', end_date)
                self.generators[symbol] = BacktestDataGenerator(
                    symbol=symbol,
                    start_date=bt_start,
                    end_date=bt_end,
                    resolution=resolution,
                )

            df = self.generators[symbol].get_next_slice()
            if df is None:
                raise StopIteration(f"Backtest complete for {symbol}")
            return df

        if symbol in self.generators:
            return self.generators[symbol].get_full_data()

        if _scanner is None:
            raise KeyError(
                f"No data loaded for symbol '{symbol}'. "
                "Call load_from_dataframe() or load_from_csv() first."
            )

        df = _scanner.fetch(symbol, start_date, end_date, resolution)
        df = df.rename(columns=COLUMN_MAP)

        if 'date' in df.columns:
            df = df.sort_values(by='date').reset_index(drop=True)

        return df

    def load_multiple_symbols(self, symbols: list, start_date: str = None,
                              end_date: str = None, resolution: str = '1') -> dict:
        data = {}
        for symbol in symbols:
            try:
                df = self.load_symbol_data(symbol, start_date, end_date, resolution)
                data[symbol] = df
            except Exception as e:
                print(f"Error loading {symbol}: {e}")
                data[symbol] = None
        return data

    def get_all_backtest_data(self, symbols: list, start_date: str = None,
                              end_date: str = None, resolution: str = '1') -> dict:
        data = {}
        for symbol in symbols:
            try:
                gen = BacktestDataGenerator(symbol, start_date, end_date, resolution)
                data[symbol] = gen.get_full_data()
            except Exception as e:
                print(f"Error loading all data for {symbol}: {e}")
                data[symbol] = None
        return data

    def prepare_for_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.dropna(subset=['open', 'high', 'low', 'close'])
        if 'volume' not in df.columns:
            df['volume'] = 0
        df = df.reset_index(drop=True)
        return df
