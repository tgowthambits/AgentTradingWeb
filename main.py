from pipeline.live_inference import live_inference
from data.loaders import load_daily, load_intraday
from loguru import logger


def format_signal(signal):
    """Convert signal number to readable string"""
    signal_map = {1: "BUY", -1: "SELL", 0: "HOLD"}
    return signal_map.get(signal, "UNKNOWN")


def format_bool(value):
    """Format boolean/numpy bool to readable string"""
    if isinstance(value, bool):
        return "✓" if value else "✗"
    return "✓" if bool(value) else "✗"


def format_trend(trend):
    """Format trend value to readable string"""
    trend_map = {1: "BULLISH", -1: "BEARISH", 0: "NEUTRAL"}
    return trend_map.get(trend, "UNKNOWN")


def print_trading_signal(output):
    """Print trading signal output as a readable table"""
    print("\n" + "="*70)
    print(" " * 20 + "HYBRID TRADING SIGNAL")
    print("="*70 + "\n")
    
    # Model Signals Section
    print("┌─ MODEL SIGNALS ─" + "─"*53 + "┐")
    daily = output["daily_models"]
    intra = output["intraday_models"]
    
    print(f"│ Daily VOMC Signal:     {format_signal(daily['vomc_daily_signal']):<10} "
          f"(Probability: {daily['vomc_daily_prob']:.2%})" + " " * 10 + "│")
    print(f"│ Daily Regime:          {daily['daily_regime']:<10} "
          f"(Predicted Return: {daily['daily_return_prediction']:.4f})" + " " * 8 + "│")
    print(f"│ Intraday VOMC Signal:  {format_signal(intra['vomc_intraday_signal']):<10} " + " " * 30 + "│")
    print(f"│ RL Agent Action:       {format_signal({0: 1, 1: -1, 2: 0}.get(intra['rl_intraday_action'], 0)):<10} " + " " * 30 + "│")
    print("└" + "─"*68 + "┘\n")
    
    # Raw Signal
    print("┌─ SIGNAL FUSION ─" + "─"*52 + "┐")
    print(f"│ Raw Signal (Before Filters): {format_signal(output['raw_signal']):<10} " + " " * 25 + "│")
    print("└" + "─"*68 + "┘\n")
    
    # Filters Section
    print("┌─ PRECISION FILTERS ─" + "─"*48 + "┐")
    filters = output["filters_applied"]
    confirmations = output["confirmations"]
    
    print(f"│ Volatility Filter:      {format_bool(filters['volatility']):<3} "
          f"(Min volatility threshold passed)" + " " * 20 + "│")
    print(f"│ Trend Confirmation:    {format_trend(filters['trend']):<10} "
          f"({format_bool(confirmations['trend'])} Confirms signal)" + " " * 15 + "│")
    print(f"│ Breakout Detection:    {format_trend(filters['breakout']):<10} "
          f"({format_bool(confirmations['breakout'])} Confirms signal)" + " " * 15 + "│")
    print(f"│ Momentum (RSI):        {format_trend(filters['momentum']):<10} "
          f"({format_bool(confirmations['momentum'])} Confirms signal)" + " " * 15 + "│")
    print(f"│ Confidence Threshold:  {format_bool(filters['confidence']):<3} "
          f"(Daily prob > threshold)" + " " * 25 + "│")
    print("└" + "─"*68 + "┘\n")
    
    # Final Decision
    final_signal = output["final_signal"]
    signal_str = format_signal(final_signal)
    
    print("┌─ FINAL DECISION ─" + "─"*51 + "┐")
    if final_signal == 1:
        print(f"│ {' '*15} 🟢 {signal_str} SIGNAL {' '*15} │")
    elif final_signal == -1:
        print(f"│ {' '*15} 🔴 {signal_str} SIGNAL {' '*15} │")
    else:
        print(f"│ {' '*15} ⚪ {signal_str} SIGNAL {' '*15} │")
    print("└" + "─"*68 + "┘\n")
    
    # Summary
    print("─"*70)
    print(f"Summary: Raw signal was {format_signal(output['raw_signal'])}, "
          f"but after applying precision filters, final signal is {signal_str}.")
    
    # Count confirmations
    conf_count = sum(confirmations.values())
    print(f"Filter Confirmations: {conf_count}/3 (Trend: {confirmations['trend']}, "
          f"Breakout: {confirmations['breakout']}, Momentum: {confirmations['momentum']})")
    print("─"*70 + "\n")


def main():
    daily_df = load_daily()
    intraday_df, prices = load_intraday()

    output = live_inference(daily_df, intraday_df, prices)

    print_trading_signal(output)

if __name__ == "__main__":
    main()
