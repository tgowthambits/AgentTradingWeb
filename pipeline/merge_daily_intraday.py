def merge_daily_intraday(daily, intraday):
    """
    Combines:
        daily VOMC + daily HMM + XGB → macro bias
        intraday VOMC + RL agent → execution
    """

    macro_bias = daily["vomc_daily_signal"]

    # If HMM says regime = crash, reduce risk
    if daily["daily_regime"] == 2:     # e.g. crash regime
        macro_bias = -1

    # If XGB forecasts positive return, lean long
    if daily["daily_return_prediction"] > 0:
        macro_bias = 1

    # Intraday micro entry/exit
    micro = intraday["vomc_intraday_signal"]
    rl = intraday["rl_intraday_action"]

    # Merge logic
    if rl == 0:      # buy
        final = 1
    elif rl == 1:    # sell
        final = -1
    else:
        final = micro * macro_bias

    return final
