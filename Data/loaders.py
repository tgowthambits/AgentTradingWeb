import pandas as pd
from utils.features import add_technical_features

from Data.fyers_data_final import FyersDataScanner
import numpy as np
scanner = FyersDataScanner()

symbol = "BSE:SENSEX2610185100PE"
start_date = '2025-12-27 16:15:00'
end_date = '2025-12-29 16:15:00'


def load_daily():
    scanner.start_date = start_date
    scanner.end_date = end_date
    scanner.symbol = symbol
    scanner.resolution = '1'
    df = scanner.get_data()
    df = df.rename(columns={
    'Time': 'time',
    'Open': 'open',
    'High': 'high',
    'Low': 'low',
    'Close': 'close',
    'TradeVol': 'tradevol',
    'date': 'date',
    'datetime': 'datetime',
    'daily_return_open_close': 'daily_return_open_close',
    'daily_return': 'daily_return',
    'state': 'state'
    })
    # daily return
    df["daily_return"] = df["close"].pct_change().fillna(0)

    # add technical indicators
    df = add_technical_features(df)
    
    # add advanced features for precision filtering
    from utils.features import add_advanced_features
    df = add_advanced_features(df)

    return df



# symbol = "BSE:SENSEX25DEC85400PE"
# start_date = '2025-12-10 16:15:00'
# end_date = '2025-12-18 16:15:00'

def load_intraday(path="data/intraday.csv"):
    """
    Loads intraday OHLCV data.
    Required columns:
        timestamp, open, high, low, close, volume

    Returns:
        intraday_df
        price_array
    """
    scanner.start_date = start_date
    scanner.end_date = end_date
    scanner.symbol = symbol
    scanner.resolution = '5S'

    df = scanner.get_data()
    df = df.rename(columns={
    'Time': 'time',
    'Open': 'open',
    'High': 'high',
    'Low': 'low',
    'Close': 'close',
    'TradeVol': 'tradevol',
    'date': 'date',
    'datetime': 'datetime',
    'daily_return_open_close': 'daily_return_open_close',
    'daily_return': 'daily_return',
    'state': 'state'
    })
    df["return"] = df["close"].pct_change().fillna(0)
    return df, df["close"].values




start_date = '2025-12-27 16:15:00'
end_date = '2025-12-29 16:15:00'

def load_intraday_generator(skip_rows=20000):
    """
    Generator version of load_intraday()
    Returns:
        intraday_df  → 1-row DataFrame
        prices       → FULL history of close values (np.array)
    """

    # Configure scanner
    scanner.start_date = start_date
    scanner.end_date = end_date
    scanner.symbol = symbol
    scanner.resolution = "5S"

    # Fetch full dataset
    df = scanner.get_data()

    # Rename columns
    df = df.rename(columns={
        'Time': 'time',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'TradeVol': 'tradevol',
        'date': 'date',
        'datetime': 'datetime',
        'daily_return_open_close': 'daily_return_open_close',
        'daily_return': 'daily_return',
        'state': 'state'
    })

    # Add returns
    df["return"] = df["close"].pct_change().fillna(0)

    # Drop first rows
    df = df.iloc[skip_rows:].reset_index(drop=True)

    # Store full history progressively
    close_history = []

    # Yield row-by-row
    for idx, row in df.iterrows():

        # Update history
        close_history.append(row["close"])

        # Build output
        intraday_df = pd.DataFrame([row.to_dict()])
        prices = np.array(close_history, dtype=float)

        yield intraday_df, prices