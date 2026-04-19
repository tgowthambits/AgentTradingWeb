import numpy as np
import pandas as pd
from models.vomc_intraday import VOMCIntraday
from models.hmm_intraday import HMMIntraday
from models.xgb_returns_intraday import XGBIntradayReturns
from models.rl_agent import RLAgent
import json
import yaml


def run_intraday(df, prices, config_path="configs/params.yaml", has_position=False):

    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)

    # Intraday up/down state
    states = (df["return"] > 0).astype(int).values

    # ----- VOMC Intraday -----
    with open("configs/patterns_intraday.json", "r") as f:
        patterns = json.load(f)

    vomc = VOMCIntraday(pattern_list=patterns)
    vomc.fit(states)

    history = states[-max(len(p) for p in patterns):]
    vomc_prob = vomc.predict_proba(history)
    
    # Get thresholds from config (default: buy=0.3, sell=0.7)
    vomc_config = cfg.get("vomc", {})
    buy_threshold = vomc_config.get("buy_threshold", 0.3)
    sell_threshold = vomc_config.get("sell_threshold", 0.7)
    
    # Position-aware signal logic with configurable thresholds
    if vomc_prob >= buy_threshold:
        raw_signal = 1  # BUY
    elif vomc_prob <= (1 - sell_threshold):
        raw_signal = -1  # SELL
    else:
        raw_signal = 0  # HOLD (neutral zone)
    
    # Apply position-aware logic
    if not has_position and raw_signal == -1:
        # Can't sell without a position
        vomc_signal = 0  # HOLD
    elif has_position and raw_signal == 1:
        # Already in position, don't buy again
        vomc_signal = 0  # HOLD
    else:
        vomc_signal = raw_signal

    # ----- HMM Intraday -----
    hmm_config = cfg.get("hmm", {})
    hmm = HMMIntraday(
        n_regimes=hmm_config.get("n_regimes", 3),
        n_iter=hmm_config.get("n_iter", 100),
        tol=hmm_config.get("tol", 0.01),
        min_covar=hmm_config.get("min_covar", 1e-6),
        covariance_type=hmm_config.get("covariance_type", "diag")
    )
    hmm.fit(df)
    regime = hmm.predict_regime(df)[-1]

    # ----- XGBoost Regression Intraday -----
    xgb_config = cfg.get("xgboost", {})
    xgb = XGBIntradayReturns(
        n_estimators=xgb_config.get("n_estimators", 300),
        max_depth=xgb_config.get("max_depth", 5),
        learning_rate=xgb_config.get("learning_rate", 0.03),
        n_jobs=xgb_config.get("n_jobs", 1)
    )
    features = cfg.get("intraday_features", ["return"])
    xgb.fit(df, features)
    xgb_pred = xgb.predict(df.tail(1), features)[0]

    # ----- RL agent -----
    # Initialize RL agent with config parameters
    # Pass position information so RL agent can make position-aware decisions
    rl_config = cfg.get("rl", {})
    agent = RLAgent(model_path=rl_config.get("model_path"), config=rl_config)
    obs = states[-rl_config.get("window", 10):]
    rl_action = agent.predict(obs, has_position=has_position)

    return {
        "vomc_intraday_signal": int(vomc_signal),
        "vomc_intraday_prob": float(vomc_prob),
        "intraday_regime": int(regime),
        "intraday_return_prediction": float(xgb_pred),
        "rl_intraday_action": int(rl_action)
    }
