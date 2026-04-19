import numpy as np

class Portfolio:

    def __init__(self, initial_capital=100000, max_pos_size=1):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.position = 0  # -1 short, 0 flat, 1 long
        self.max_pos_size = max_pos_size
        self.equity_curve = []

    def update(self, price_change):
        """
        price_change = today's close - yesterday's close
        """
        pnl = self.position * price_change * self.max_pos_size
        self.capital += pnl
        self.equity_curve.append(self.capital)
        return pnl

    def trade(self, signal):
        """
        signal: -1 = short, 0 = flat, 1 = long
        """
        self.position = signal
