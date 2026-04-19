import pandas as pd
import numpy as np


def resample_intraday(df, timeframe="1min"):
    """
    Resamples raw tick/5-second data into OHLCV bars.
    Example timeframe: "1min", "5min"
    """

    o = df["open"].resample(timeframe).first()
    h = df["high"].resample(timeframe).max()
    l = df["low"].resample(timeframe).min()
    c = df["close"].resample(timeframe).last()
    v = df["volume"].resample(timeframe).sum()

    out = pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": v})
    out = out.dropna()
    out["return"] = out["close"].pct_change().fillna(0)

    return out


def clean_intraday(df):
    """
    Removes gaps, outliers, zero-volume bars, weekend data.
    """

    # remove weekends
    df = df[~df.index.dayofweek.isin([5, 6])]

    # drop zero volume bars
    df = df[df["volume"] > 0]

    # mild outlier clipping
    r = df["return"]
    std = r.std()
    df["return"] = r.clip(-5 * std, 5 * std)

    return df


def sync_daily_intraday(daily_df, intraday_df):
    """
    Ensures daily and intraday data line up cleanly.
    Returns:
        daily_df, intraday_df for the same date windows
    """

    start = intraday_df.index.min().date()
    end = intraday_df.index.max().date()

    daily_df = daily_df.loc[str(start):str(end)]

    return daily_df, intraday_df
