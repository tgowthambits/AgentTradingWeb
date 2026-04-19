def split_sessions(df):
    """
    Splits intraday dataframe into a dict of daily sessions.
    Key = date, Value = df for that day
    """

    sessions = {}
    for date, session_df in df.groupby(df.index.date):
        sessions[date] = session_df
    return sessions


def filter_market_hours(df, start="09:15", end="15:30"):
    """
    Keeps only intraday bars inside market hours.
    Default matches NSE (India).
    """

    return df.between_time(start, end)


def prepare_intraday_sessions(df):
    """
    Full preparation pipeline:
        1. Trim to market hours
        2. Split into daily sessions
        3. Remove very small sessions (< 50 bars)
    """

    df = filter_market_hours(df)

    sessions = split_sessions(df)

    clean_sessions = {}
    for d, sess in sessions.items():
        if len(sess) > 50:
            clean_sessions[d] = sess

    return clean_sessions
