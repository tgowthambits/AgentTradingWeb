# def live_inference(daily_df, intraday_df, intraday_prices):
#     from .run_daily_models import run_daily_models
#     from .run_intraday_models import run_intraday
#     from .merge_daily_intraday import merge_daily_intraday

#     daily = run_daily_models(daily_df)
#     intraday = run_intraday(intraday_df, intraday_prices)

#     final_signal = merge_daily_intraday(daily, intraday)

#     return {
#         "daily_models": daily,
#         "intraday_models": intraday,
#         "final_signal": final_signal
#     }
# pipeline/live_inference.py

from pipeline.run_daily_models import run_daily_models
from pipeline.run_intraday_models import run_intraday
from utils.filters import apply_all_filters
import yaml


# -------------------------------------------
# FUSION LOGIC (Enhanced with filters)
# -------------------------------------------
def fuse_signals(daily, intraday, rl, strict=False):
    """
    Combine daily + intraday + RL signals using majority voting.
    BUY = 1, SELL = -1, HOLD = 0
    
    Args:
        daily: Daily signal (-1, 0, 1)
        intraday: Intraday signal (-1, 0, 1)
        rl: RL agent action (0, 1, 2) - needs mapping to (-1, 0, 1)
        strict: If True, require unanimous agreement
    
    Returns:
        int: Fused signal (-1, 0, 1)
    """
    # Map RL action to signal format (-1, 0, 1)
    # From rl_intraday_env.py: action 0=buy(1), action 1=sell(-1), action 2=hold(0)
    rl_mapped = {0: 1, 1: -1, 2: 0}.get(rl, 0)
    
    votes = [daily, intraday, rl_mapped]
    vote_sum = sum(votes)

    if strict:
        # Unanimous agreement required
        if all(v == 1 for v in votes if v != 0):
            return 1
        elif all(v == -1 for v in votes if v != 0):
            return -1
        return 0
    else:
        # Majority voting
        if vote_sum >= 2:
            return 1      # BUY
        elif vote_sum <= -2:
            return -1     # SELL
        return 0           # HOLD


# -------------------------------------------
# MAIN LIVE INFERENCE PIPELINE (Enhanced)
# -------------------------------------------
def live_inference(daily_df, intraday_df, price_df, config_path="configs/params.yaml", has_position=False):

    # Load configuration
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)
    
    filter_config = cfg.get("filters", {})

    # Run models (pass position status for position-aware signals)
    daily_out = run_daily_models(daily_df, config_path=config_path, has_position=has_position)     # regime + daily signal
    intra_out = run_intraday(intraday_df, price_df, config_path=config_path, has_position=has_position)  # vwap/rsi + rl

    # Extract raw signals
    daily_sig  = daily_out["vomc_daily_signal"]
    intra_sig  = intra_out["vomc_intraday_signal"]
    rl_sig     = intra_out["rl_intraday_action"]
    daily_prob = daily_out.get("vomc_daily_prob", 0.5)
    intraday_prob = intra_out.get("vomc_intraday_prob", 0.5)

    # Fuse signals (basic fusion)
    raw_signal = fuse_signals(daily_sig, intra_sig, rl_sig, strict=False)

    # Apply precision filters
    # Use daily_df for filters (has more historical data)
    filter_results = apply_all_filters(
        df=daily_df,
        signal=raw_signal,
        daily_prob=daily_prob,
        config=filter_config,
        intraday_prob=intraday_prob
    )

    # Get filtered signal
    final_sig = filter_results["filtered_signal"]

    return {
        "daily_models": daily_out,
        "intraday_models": intra_out,
        "raw_signal": raw_signal,
        "filter_results": filter_results,
        "final_signal": final_sig,
        "filters_applied": {
            "volatility": filter_results["filters"]["volatility"],
            "trend": filter_results["filters"]["trend"],
            "breakout": filter_results["filters"]["breakout"],
            "momentum": filter_results["filters"]["momentum"],
            "confidence": filter_results["filters"]["confidence"]
        },
        "volatility_value": filter_results.get("volatility_value", 0.0),
        "volatility_positive": filter_results.get("volatility_positive", 0.0),
        "volatility_negative": filter_results.get("volatility_negative", 0.0),
        "confirmations": filter_results["confirmations"]
    }
