import numpy as np

class Metrics:

    @staticmethod
    def compute(results):
        df = results.copy()

        total_return = df["equity"].iloc[-1] - df["equity"].iloc[0]

        returns = df["equity"].pct_change().dropna()
        sharpe = np.sqrt(252) * (returns.mean() / returns.std()) if returns.std() != 0 else 0

        max_equity = df["equity"].cummax()
        drawdown = (df["equity"] - max_equity) / max_equity
        max_dd = drawdown.min()

        return {
            "total_return": total_return,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd
        }
