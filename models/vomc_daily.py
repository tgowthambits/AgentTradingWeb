import pandas as pd
import numpy as np
from collections import Counter


class VOMCDaily:
    
    def __init__(self, pattern_list, alpha=1):
        """
        pattern_list: list of state sequences like:
            [[1], [1,1], [1,1,1], [1,0,1], ...]
        """
        self.pattern_list = [tuple(p) for p in pattern_list]
        self.alpha = alpha
        self.model = {}

    def _states(self, df):
        """Convert daily return to Up(1) / Down(0)."""
        return (df["daily_return"] > 0).astype(int).values

    def fit(self, df):
        """Train VOMC on daily data."""
        states = self._states(df)

        for pattern in self.pattern_list:
            L = len(pattern)
            counts = Counter()

            for i in range(len(states) - L):
                if tuple(states[i:i+L]) == pattern:
                    nxt = states[i + L]
                    counts[nxt] += 1

            up = counts[1]
            down = counts[0]
            total = up + down

            p_up = (up + self.alpha) / (total + 2*self.alpha)
            p_down = (down + self.alpha) / (total + 2*self.alpha)

            self.model[pattern] = {
                "counts": {"up": up, "down": down},
                "probs": {"up": p_up, "down": p_down}
            }

    def predict_proba(self, history):
        """
        history: list of trailing states.
        Returns probability of Up next day.
        """
        # longest-suffix strategy
        for L in range(len(history), 0, -1):
            suffix = tuple(history[-L:])
            if suffix in self.model:
                return self.model[suffix]["probs"]["up"]

        return 0.5  # fallback

    def predict(self, history):
        """Return Up(1) or Down(0)."""
        p_up = self.predict_proba(history)
        return 1 if p_up >= 0.5 else 0
