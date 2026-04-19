def split_sessions(df):
    """Splits intraday data into trading sessions."""
    return dict(tuple(df.groupby(df.index.date)))
