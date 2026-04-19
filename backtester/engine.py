# import numpy as np
# from .portfolio import Portfolio


# class BacktestEngine:

#     def __init__(self, prices, signals, initial_capital=100000, max_pos_size=1):
#         """
#         prices: array of prices (daily or intraday)
#         signals: array of -1, 0, +1 actions
#         """
#         self.prices = prices
#         self.signals = signals
#         self.portfolio = Portfolio(initial_capital, max_pos_size)

#     def run(self):
#         results = []

#         for i in range(1, len(self.prices)):
#             price_change = self.prices[i] - self.prices[i-1]

#             # update position
#             self.portfolio.trade(self.signals[i-1])

#             pnl = self.portfolio.update(price_change)

#             results.append({
#                 "price": self.prices[i],
#                 "signal": self.signals[i-1],
#                 "pnl": pnl,
#                 "equity": self.portfolio.capital
#             })

#         return results

import numpy as np
import pandas as pd


class BacktestEngine:

    def __init__(self, prices, signals, initial_capital=100000, max_pos_size=1):
        self.prices = np.array(prices)
        self.signals = np.array(signals)
        self.initial_capital = initial_capital
        self.max_pos_size = max_pos_size

    def run(self):
        # compute price changes
        price_diff = np.diff(self.prices)

        # align signals
        sig = self.signals[:-1]

        # vectorized PNL
        pnl = sig * price_diff * self.max_pos_size

        equity = self.initial_capital + np.cumsum(pnl)

        df = pd.DataFrame({
            "price": self.prices[1:],
            "signal": sig,
            "pnl": pnl,
            "equity": equity
        })

        return df
