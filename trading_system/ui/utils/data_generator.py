"""
Data Generator Module

Contains utilities for generating sequential data from multiple symbol DataFrames.
"""

import pandas as pd
from typing import Dict, Generator, Tuple, Any, List
from datetime import datetime


def combined_data_generator(data: Dict[str, pd.DataFrame]) -> Generator[Tuple[datetime, Dict[str, Any], List[datetime]], None, None]:
    """
    Generator that yields data timestamp by timestamp for all symbols.
    Uses the 'datetime' column from the dataframe for timestamps.
    
    This generator is useful for backtesting and simulation where data
    needs to be processed sequentially across multiple symbols.
    
    Args:
        data: Dictionary mapping symbol names to DataFrames with OHLCV data
    
    Yields:
        Tuple of (timestamp, current_data_dict, all_timestamps_list)
        - timestamp: Current datetime being processed
        - current_data: Dict mapping symbol to its row data at this timestamp
        - all_timestamps: List of all timestamps in sorted order
    
    Example:
        >>> data = {'NIFTY': df_nifty, 'BANKNIFTY': df_banknifty}
        >>> for timestamp, symbol_data, all_ts in combined_data_generator(data):
        ...     for symbol, row in symbol_data.items():
        ...         process_symbol(symbol, row)
    """
    # Collect all datetime values from all symbols
    all_datetimes = set()
    for symbol, df in data.items():
        if df is not None and not df.empty:
            if 'datetime' in df.columns:
                # Convert datetime string to datetime object for sorting
                for dt_str in df['datetime']:
                    try:
                        if isinstance(dt_str, str):
                            dt_obj = pd.to_datetime(dt_str, format='%m-%d-%Y %H:%M:%S')
                        elif isinstance(dt_str, pd.Timestamp):
                            dt_obj = dt_str.to_pydatetime()
                        else:
                            dt_obj = pd.to_datetime(dt_str)
                        all_datetimes.add(dt_obj)
                    except:
                        pass
            elif 'date' in df.columns:
                # Fallback to 'date' column (arrow time object)
                for dt in df['date']:
                    try:
                        if hasattr(dt, 'datetime'):
                            all_datetimes.add(dt.datetime)
                        elif isinstance(dt, pd.Timestamp):
                            all_datetimes.add(dt.to_pydatetime())
                        else:
                            all_datetimes.add(pd.to_datetime(dt))
                    except:
                        pass
    
    # Sort all timestamps
    all_timestamps = sorted(list(all_datetimes))
    
    # Create a mapping: symbol -> {datetime: row_index}
    symbol_datetime_map = {}
    for symbol, df in data.items():
        if df is not None and not df.empty:
            symbol_datetime_map[symbol] = {}
            if 'datetime' in df.columns:
                for idx, dt_str in enumerate(df['datetime']):
                    try:
                        if isinstance(dt_str, str):
                            dt_obj = pd.to_datetime(dt_str, format='%m-%d-%Y %H:%M:%S')
                        elif isinstance(dt_str, pd.Timestamp):
                            dt_obj = dt_str.to_pydatetime()
                        else:
                            dt_obj = pd.to_datetime(dt_str)
                        symbol_datetime_map[symbol][dt_obj] = idx
                    except:
                        pass
            elif 'date' in df.columns:
                for idx, dt in enumerate(df['date']):
                    try:
                        if hasattr(dt, 'datetime'):
                            dt_obj = dt.datetime
                        elif isinstance(dt, pd.Timestamp):
                            dt_obj = dt.to_pydatetime()
                        else:
                            dt_obj = pd.to_datetime(dt)
                        symbol_datetime_map[symbol][dt_obj] = idx
                    except:
                        pass

    # Yield data for each timestamp
    for timestamp in all_timestamps:
        current_data = {}
        for symbol, df in data.items():
            if df is not None and not df.empty and symbol in symbol_datetime_map:
                if timestamp in symbol_datetime_map[symbol]:
                    row_idx = symbol_datetime_map[symbol][timestamp]
                    current_data[symbol] = df.iloc[row_idx]
        yield timestamp, current_data, all_timestamps


def parse_datetime_from_string(dt_str: str, format_str: str = '%m-%d-%Y %H:%M:%S') -> datetime:
    """
    Parse a datetime string to a datetime object.
    
    Args:
        dt_str: Datetime string to parse
        format_str: Format string (default matches FyersData format)
    
    Returns:
        Parsed datetime object or None on failure
    """
    try:
        if isinstance(dt_str, str):
            return pd.to_datetime(dt_str, format=format_str).to_pydatetime()
        elif isinstance(dt_str, pd.Timestamp):
            return dt_str.to_pydatetime()
        elif isinstance(dt_str, datetime):
            return dt_str
        else:
            return pd.to_datetime(dt_str).to_pydatetime()
    except:
        return None


def get_timestamps_from_df(df: pd.DataFrame) -> List[datetime]:
    """
    Extract all timestamps from a DataFrame.
    
    Looks for 'datetime' column first, then 'date' column.
    
    Args:
        df: DataFrame with time data
    
    Returns:
        List of datetime objects
    """
    timestamps = []
    
    if df is None or df.empty:
        return timestamps
    
    if 'datetime' in df.columns:
        for dt_str in df['datetime']:
            dt = parse_datetime_from_string(dt_str)
            if dt:
                timestamps.append(dt)
    elif 'date' in df.columns:
        for dt in df['date']:
            try:
                if hasattr(dt, 'datetime'):
                    timestamps.append(dt.datetime)
                elif isinstance(dt, pd.Timestamp):
                    timestamps.append(dt.to_pydatetime())
                elif isinstance(dt, datetime):
                    timestamps.append(dt)
                else:
                    timestamps.append(pd.to_datetime(dt).to_pydatetime())
            except:
                pass
    
    return timestamps
