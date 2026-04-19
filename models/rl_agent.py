from stable_baselines3 import PPO
import os
import numpy as np
from typing import Dict, Any, Optional


class RLAgent:

    def __init__(self, model_path=None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize RL Agent
        
        Args:
            model_path: Path to trained PPO model file
            config: Configuration dictionary with RL parameters
        """
        self.config = config or {}
        self.model = None
        
        # Load model if path provided
        model_path = model_path or self.config.get("model_path")
        if model_path and os.path.exists(model_path):
            try:
                self.model = PPO.load(model_path)
            except Exception as e:
                print(f"Warning: Could not load RL model from {model_path}: {e}")
                self.model = None
        
        # Rule-based prediction parameters (from config or defaults)
        rule_based_config = self.config.get("rule_based", {})
        self.recent_window = rule_based_config.get("recent_window", 5)
        self.buy_recent_threshold = rule_based_config.get("buy_recent_threshold", 0.6)
        self.buy_overall_threshold = rule_based_config.get("buy_overall_threshold", 0.5)
        self.sell_recent_threshold = rule_based_config.get("sell_recent_threshold", 0.4)
        self.sell_overall_threshold = rule_based_config.get("sell_overall_threshold", 0.5)

    def train(self, env, timesteps=100_000):
        self.model = PPO("MlpPolicy", env, verbose=0)
        self.model.learn(total_timesteps=timesteps)

    def save(self, path):
        """Save the trained model"""
        if self.model is not None:
            self.model.save(path)
        else:
            raise ValueError("No model to save. Train the model first.")

    def _rule_based_predict(self, obs, has_position=False):
        """
        Rule-based prediction when no trained model is available.
        Analyzes recent price patterns to generate trading signals.
        
        Args:
            obs: Observation array (state sequence: 1=up, 0=down)
            has_position: Boolean indicating if a position currently exists
        
        Returns:
            int: Action (0=buy, 1=sell, 2=hold)
        """
        obs = np.array(obs).flatten()
        
        if len(obs) == 0:
            return 2  # HOLD if no observation
        
        # Calculate statistics
        up_count = np.sum(obs == 1)
        down_count = np.sum(obs == 0)
        total = len(obs)
        
        if total == 0:
            return 2
        
        up_ratio = up_count / total
        
        # Analyze recent trend (configurable window)
        recent_window = min(self.recent_window, len(obs))
        recent_obs = obs[-recent_window:]
        recent_up_ratio = np.sum(recent_obs == 1) / len(recent_obs) if len(recent_obs) > 0 else 0.5
        
        # Rule-based logic:
        # 1. Strong uptrend (recent and overall) → BUY
        # 2. Strong downtrend (recent and overall) → SELL
        # 3. Mixed/neutral → HOLD
        
        # BUY conditions: Recent uptrend and overall positive (configurable thresholds)
        if recent_up_ratio >= self.buy_recent_threshold and up_ratio >= self.buy_overall_threshold:
            if not has_position:
                return 0  # BUY
            else:
                return 2  # HOLD (already in position)
        
        # SELL conditions: Recent downtrend and overall negative (configurable thresholds)
        elif recent_up_ratio <= self.sell_recent_threshold and up_ratio <= self.sell_overall_threshold:
            if has_position:
                return 1  # SELL
            else:
                return 2  # HOLD (can't sell without position)
        
        # HOLD for mixed/neutral patterns
        return 2
    
    def predict(self, obs, has_position=False):
        """
        Predict action based on observation and position status.
        
        Args:
            obs: Observation array (state sequence)
            has_position: Boolean indicating if a position currently exists
        
        Returns:
            int: Action (0=buy, 1=sell, 2=hold)
        """
        if self.model is None:
            # Use rule-based prediction when no model is loaded
            # This makes the RL agent trade more actively
            return self._rule_based_predict(obs, has_position)
        
        # Ensure obs is the right shape (should be 1D array of length window)
        obs = np.array(obs).flatten()
        action, _ = self.model.predict(obs, deterministic=True)
        action = int(action)
        
        # Position-aware logic:
        # - If no position and action is SELL, convert to HOLD (can't sell without position)
        # - If has position and action is BUY, convert to HOLD (already in position)
        if not has_position and action == 1:  # SELL but no position
            return 2  # HOLD
        elif has_position and action == 0:  # BUY but already in position
            return 2  # HOLD
        
        return action
