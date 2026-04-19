import pandas as pd

def backtest(df, signal_col="signal", price_col="close"):

    df = df.copy()

    df["position"] = df[signal_col].shift(1).fillna(0)
    df["return"] = df[price_col].pct_change()
    df["strategy_return"] = df["position"] * df["return"]

    df["equity"] = (1 + df["strategy_return"]).cumprod()

    stats = {
        "total_return": df["equity"].iloc[-1] - 1,
        "max_drawdown": (df["equity"].cummax() - df["equity"]).max(),
        "sharpe": df["strategy_return"].mean() / df["strategy_return"].std() * (252*78*5)**0.5
    }

    return df, stats
