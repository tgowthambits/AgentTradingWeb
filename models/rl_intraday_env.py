import gym
import numpy as np

class IntradayTradingEnv(gym.Env):

    def __init__(self, prices, states, window=10):
        super().__init__()
        self.prices = prices
        self.states = states
        self.window = window
        self.position = 0
        self.reward = 0
        self.current_step = window

        self.observation_space = gym.spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(window,)
        )
        self.action_space = gym.spaces.Discrete(3)  # buy, sell, hold

    def reset(self):
        self.position = 0
        self.reward = 0
        self.current_step = self.window
        return self._get_obs()

    def _get_obs(self):
        return self.states[self.current_step - self.window:self.current_step]

    def step(self, action):
        prev_price = self.prices[self.current_step]

        if action == 0:   # buy
            self.position = 1
        elif action == 1: # sell
            self.position = -1

        self.current_step += 1
        done = self.current_step >= len(self.prices)-1
        
        pnl = (self.prices[self.current_step] - prev_price) * self.position
        self.reward = pnl

        return self._get_obs(), self.reward, done, {}
