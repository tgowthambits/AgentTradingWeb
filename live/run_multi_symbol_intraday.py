"""
Multi-Symbol Intraday Trading Script
====================================
This script runs the complete intraday trading pipeline for multiple symbols
and stores results in a CSV file after each iteration.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from loguru import logger
import sys
import traceback
import yaml
from pathlib import Path

try:
    from tabulate import tabulate
except ImportError:
    logger.warning("tabulate not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tabulate"])
    from tabulate import tabulate

from pipeline.live_inference import live_inference
from data.loaders import load_daily, load_intraday
from Data.fyers_data_final import FyersDataScanner
from utils.features import add_technical_features, add_advanced_features


# ============================================================
# CONFIGURATION
# ============================================================

def load_config(config_path="configs/symbols_config.yaml"):
    """Load configuration from YAML file"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# Load configuration
CONFIG = load_config()

# List of symbols to analyze
SYMBOLS = CONFIG['symbols']

# Date range
START_DATE = CONFIG['date_range']['start_date']
END_DATE = CONFIG['date_range']['end_date']

# Output file
RESULTS_CSV = CONFIG['output']['results_csv']

# Position status
HAS_POSITION = CONFIG.get('has_position', False)

# Performance settings
PERFORMANCE = CONFIG.get('performance', {})
PARAMS_CONFIG = PERFORMANCE.get('params_config', 'configs/params.yaml')
MAX_INTRADAY_ROWS = PERFORMANCE.get('max_intraday_rows', 1000)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def format_signal(signal):
    """Convert signal number to readable string"""
    signal_map = {1: "BUY", -1: "SELL", 0: "HOLD"}
    return signal_map.get(signal, "UNKNOWN")


def format_bool(value):
    """Format boolean/numpy bool to readable string"""
    if value is None:
        return "N/A"
    return "✓" if bool(value) else "✗"


def format_trend(trend):
    """Format trend value to readable string"""
    if trend is None:
        return "N/A"
    trend_map = {1: "BULLISH", -1: "BEARISH", 0: "NEUTRAL"}
    return trend_map.get(trend, "UNKNOWN")


def load_symbol_data(symbol, start_date, end_date, max_intraday_rows=1000):
    """
    Load both daily and intraday data for a specific symbol
    
    Args:
        symbol: Trading symbol
        start_date: Start date
        end_date: End date
        max_intraday_rows: Maximum intraday rows to use (for performance)
    
    Returns:
        daily_df: Daily timeframe data with technical indicators
        intraday_df: Intraday timeframe data (sampled if needed)
        prices: Close prices array for intraday
    """
    scanner = FyersDataScanner()
    
    # Load Daily Data
    logger.info(f"Loading daily data for {symbol}...")
    scanner.start_date = start_date
    scanner.end_date = end_date
    scanner.symbol = symbol
    scanner.resolution = '1'
    
    daily_df = scanner.get_data()
    daily_df = daily_df.rename(columns={
        'Time': 'time',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'TradeVol': 'tradevol',
        'date': 'date',
        'datetime': 'datetime',
        'daily_return_open_close': 'daily_return_open_close',
        'daily_return': 'daily_return',
        'state': 'state'
    })
    
    daily_df["daily_return"] = daily_df["close"].pct_change().fillna(0)
    logger.info(f"Adding technical features to daily data...")
    daily_df = add_technical_features(daily_df)
    daily_df = add_advanced_features(daily_df)
    
    # Load Intraday Data
    logger.info(f"Loading intraday data for {symbol}...")
    scanner.start_date = start_date
    scanner.end_date = end_date
    scanner.symbol = symbol
    scanner.resolution = '5S'
    
    intraday_df = scanner.get_data()
    intraday_df = intraday_df.rename(columns={
        'Time': 'time',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'TradeVol': 'tradevol',
        'date': 'date',
        'datetime': 'datetime',
        'daily_return_open_close': 'daily_return_open_close',
        'daily_return': 'daily_return',
        'state': 'state'
    })
    intraday_df["return"] = intraday_df["close"].pct_change().fillna(0)
    
    # Sample intraday data if too large (for performance)
    original_rows = len(intraday_df)
    if original_rows > max_intraday_rows:
        logger.warning(f"Intraday data has {original_rows} rows. Sampling to {max_intraday_rows} for performance...")
        # Use the most recent data
        intraday_df = intraday_df.tail(max_intraday_rows).reset_index(drop=True)
        logger.info(f"Sampled intraday data: {len(intraday_df)} rows (most recent)")
    
    prices = intraday_df["close"].values
    
    return daily_df, intraday_df, prices


def run_symbol_analysis(symbol, start_date, end_date, has_position=False):
    """
    Run complete trading analysis for a single symbol
    
    Args:
        symbol: Trading symbol to analyze
        start_date: Start date for data
        end_date: End date for data
        has_position: Whether currently holding a position
    
    Returns:
        dict: Complete analysis results or error information
    """
    from time import time
    
    result = {
        'symbol': symbol,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'start_date': start_date,
        'end_date': end_date,
        'status': 'PENDING',
        'error': None
    }
    
    try:
        # Track timing
        start_time = time()
        
        # Load data
        data_start = time()
        daily_df, intraday_df, prices = load_symbol_data(
            symbol, start_date, end_date, 
            max_intraday_rows=MAX_INTRADAY_ROWS
        )
        data_time = time() - data_start
        logger.info(f"Data loading took {data_time:.2f}s (Daily: {len(daily_df)} rows, Intraday: {len(intraday_df)} rows)")
        
        # Run inference
        logger.info(f"Running inference for {symbol} using config: {PARAMS_CONFIG}...")
        inference_start = time()
        output = live_inference(
            daily_df, intraday_df, prices, 
            config_path=PARAMS_CONFIG,
            has_position=has_position
        )
        inference_time = time() - inference_start
        logger.info(f"Inference took {inference_time:.2f}s")
        
        # Extract results
        daily = output["daily_models"]
        intraday = output["intraday_models"]
        filters = output["filters_applied"]
        confirmations = output["confirmations"]
        
        # Populate result dictionary
        result.update({
            # Daily signals
            'daily_vomc_signal': int(daily['vomc_daily_signal']),
            'daily_vomc_signal_str': format_signal(daily['vomc_daily_signal']),
            'daily_vomc_prob': float(daily['vomc_daily_prob']),
            'daily_regime': int(daily['daily_regime']),
            'daily_return_prediction': float(daily['daily_return_prediction']),
            
            # Intraday signals
            'intraday_vomc_signal': int(intraday['vomc_intraday_signal']),
            'intraday_vomc_signal_str': format_signal(intraday['vomc_intraday_signal']),
            'intraday_vomc_prob': float(intraday['vomc_intraday_prob']),
            'intraday_regime': int(intraday['intraday_regime']),
            'intraday_return_prediction': float(intraday['intraday_return_prediction']),
            
            # RL agent
            'rl_action': int(intraday['rl_intraday_action']),
            'rl_action_str': format_signal({0: 1, 1: -1, 2: 0}.get(intraday['rl_intraday_action'], 0)),
            
            # Signal fusion
            'raw_signal': int(output['raw_signal']),
            'raw_signal_str': format_signal(output['raw_signal']),
            'final_signal': int(output['final_signal']),
            'final_signal_str': format_signal(output['final_signal']),
            
            # Filters
            'volatility_filter': bool(filters['volatility']),
            'volatility_filter_str': 'PASS' if filters['volatility'] else 'FAIL',
            'trend_filter': int(filters['trend']) if filters['trend'] is not None else None,
            'trend_filter_str': format_trend(filters['trend']),
            'breakout_filter': int(filters['breakout']) if filters['breakout'] is not None else None,
            'breakout_filter_str': format_trend(filters['breakout']),
            'momentum_filter': int(filters['momentum']) if filters['momentum'] is not None else None,
            'momentum_filter_str': format_trend(filters['momentum']),
            'confidence_filter': bool(filters['confidence']),
            'confidence_filter_str': 'PASS' if filters['confidence'] else 'FAIL',
            
            # Volatility details
            'volatility_value': float(output['volatility_value']),
            'volatility_positive': float(output['volatility_positive']),
            'volatility_negative': float(output['volatility_negative']),
            
            # Confirmations
            'trend_confirmation': bool(confirmations['trend']),
            'trend_confirmation_str': 'PASS' if confirmations['trend'] else 'FAIL',
            'breakout_confirmation': bool(confirmations['breakout']),
            'breakout_confirmation_str': 'PASS' if confirmations['breakout'] else 'FAIL',
            'momentum_confirmation': bool(confirmations['momentum']),
            'momentum_confirmation_str': 'PASS' if confirmations['momentum'] else 'FAIL',
            
            'status': 'SUCCESS'
        })
        
        total_time = time() - start_time
        result['processing_time'] = total_time
        logger.success(f"Successfully analyzed {symbol} in {total_time:.2f}s")
        
    except Exception as e:
        total_time = time() - start_time
        logger.error(f"Error analyzing {symbol} after {total_time:.2f}s: {str(e)}")
        result['status'] = 'ERROR'
        result['error'] = str(e)
        result['error_traceback'] = traceback.format_exc()
        result['processing_time'] = total_time
    
    return result


def save_results(results_list, output_file):
    """Save results to CSV file"""
    df = pd.DataFrame(results_list)
    df.to_csv(output_file, index=False)
    logger.info(f"Results saved to {output_file}")


def print_summary_table(results_list):
    """Print a comprehensive summary table of all results"""
    
    if not results_list:
        logger.warning("No results to display")
        return
    
    print("\n" + "="*150)
    print(" " * 50 + "MULTI-SYMBOL INTRADAY TRADING RESULTS")
    print("="*150 + "\n")
    
    # Prepare table data
    table_data = []
    
    for result in results_list:
        if result['status'] == 'SUCCESS':
            row = [
                result['symbol'],
                result['final_signal_str'],
                result['raw_signal_str'],
                result['daily_vomc_signal_str'],
                f"{result['daily_vomc_prob']:.2%}",
                result['intraday_vomc_signal_str'],
                f"{result['intraday_vomc_prob']:.2%}",
                result['rl_action_str'],
                result['volatility_filter_str'],
                result['trend_filter_str'],
                result['breakout_filter_str'],
                result['momentum_filter_str'],
                result['confidence_filter_str'],
                f"{result.get('trend_confirmation_str', 'N/A')}/{result.get('breakout_confirmation_str', 'N/A')}/{result.get('momentum_confirmation_str', 'N/A')}",
                result['status']
            ]
        else:
            row = [
                result['symbol'],
                'ERROR',
                'N/A',
                'N/A',
                'N/A',
                'N/A',
                'N/A',
                'N/A',
                'N/A',
                'N/A',
                'N/A',
                'N/A',
                'N/A',
                'N/A',
                result['status']
            ]
        
        table_data.append(row)
    
    headers = [
        "Symbol",
        "Final Signal",
        "Raw Signal",
        "Daily VOMC",
        "Daily Prob",
        "Intra VOMC",
        "Intra Prob",
        "RL Action",
        "Vol Filter",
        "Trend",
        "Breakout",
        "Momentum",
        "Confidence",
        "Confirmations",
        "Status"
    ]
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print("\n")
    
    # Print detailed view for each symbol
    print("="*150)
    print(" " * 50 + "DETAILED ANALYSIS BY SYMBOL")
    print("="*150 + "\n")
    
    for result in results_list:
        if result['status'] == 'SUCCESS':
            print_detailed_symbol_analysis(result)
        else:
            print(f"\n❌ {result['symbol']} - FAILED")
            print(f"   Error: {result.get('error', 'Unknown error')}\n")


def print_detailed_symbol_analysis(result):
    """Print detailed analysis for a single symbol"""
    
    symbol = result['symbol']
    final_signal = result['final_signal']
    signal_str = result['final_signal_str']
    
    print("\n" + "─"*100)
    print(f"📊 SYMBOL: {symbol}")
    print("─"*100)
    
    # Model Signals
    print("\n┌─ MODEL SIGNALS " + "─"*82 + "┐")
    print(f"│ Daily VOMC Signal:     {result['daily_vomc_signal_str']:<10} (Probability: {result['daily_vomc_prob']:.2%})" + " "*40 + "│")
    print(f"│ Daily Regime:          {result['daily_regime']:<10} (Predicted Return: {result['daily_return_prediction']:.4f})" + " "*35 + "│")
    print(f"│ Intraday VOMC Signal:  {result['intraday_vomc_signal_str']:<10} (Probability: {result['intraday_vomc_prob']:.2%})" + " "*40 + "│")
    print(f"│ Intraday Regime:       {result['intraday_regime']:<10} (Predicted Return: {result['intraday_return_prediction']:.4f})" + " "*35 + "│")
    print(f"│ RL Agent Action:       {result['rl_action_str']:<10}" + " "*69 + "│")
    print("└" + "─"*98 + "┘")
    
    # Signal Fusion
    print("\n┌─ SIGNAL FUSION " + "─"*82 + "┐")
    print(f"│ Raw Signal (Before Filters): {result['raw_signal_str']:<10}" + " "*58 + "│")
    print("└" + "─"*98 + "┘")
    
    # Precision Filters
    print("\n┌─ PRECISION FILTERS " + "─"*78 + "┐")
    print(f"│ Volatility Filter:      {result['volatility_filter_str']:<10} (Value: {result['volatility_value']:.4f})" + " "*47 + "│")
    print(f"│ Trend Filter:          {result['trend_filter_str']:<10} (Confirmation: {result['trend_confirmation_str']})" + " "*43 + "│")
    print(f"│ Breakout Filter:       {result['breakout_filter_str']:<10} (Confirmation: {result['breakout_confirmation_str']})" + " "*43 + "│")
    print(f"│ Momentum Filter:       {result['momentum_filter_str']:<10} (Confirmation: {result['momentum_confirmation_str']})" + " "*43 + "│")
    print(f"│ Confidence Filter:     {result['confidence_filter_str']:<10}" + " "*69 + "│")
    print("└" + "─"*98 + "┘")
    
    # Final Decision
    print("\n┌─ FINAL DECISION " + "─"*81 + "┐")
    if final_signal == 1:
        print(f"│ {' '*35} 🟢 {signal_str} SIGNAL {' '*35} │")
    elif final_signal == -1:
        print(f"│ {' '*35} 🔴 {signal_str} SIGNAL {' '*35} │")
    else:
        print(f"│ {' '*35} ⚪ {signal_str} SIGNAL {' '*35} │")
    print("└" + "─"*98 + "┘\n")


# ============================================================
# MAIN EXECUTION
# ============================================================

def main():
    """Main execution function"""
    from time import time
    
    logger.info(f"Starting multi-symbol intraday analysis for {len(SYMBOLS)} symbols")
    logger.info(f"Date range: {START_DATE} to {END_DATE}")
    logger.info(f"Model config: {PARAMS_CONFIG}")
    logger.info(f"Max intraday rows: {MAX_INTRADAY_ROWS}")
    logger.info(f"Results will be saved to: {RESULTS_CSV}")
    
    total_start_time = time()
    results_list = []
    
    # Process each symbol
    for idx, symbol in enumerate(SYMBOLS, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"Processing symbol {idx}/{len(SYMBOLS)}: {symbol}")
        logger.info(f"{'='*80}\n")
        
        # Run analysis
        result = run_symbol_analysis(symbol, START_DATE, END_DATE, has_position=HAS_POSITION)
        results_list.append(result)
        
        # Save after each iteration (incremental save)
        save_results(results_list, RESULTS_CSV)
        
        logger.info(f"Progress: {idx}/{len(SYMBOLS)} symbols completed\n")
    
    # Print final summary
    print_summary_table(results_list)
    
    # Final statistics
    total_elapsed = time() - total_start_time
    successful = sum(1 for r in results_list if r['status'] == 'SUCCESS')
    failed = sum(1 for r in results_list if r['status'] == 'ERROR')
    
    # Calculate average time per symbol
    avg_time = total_elapsed / len(SYMBOLS) if SYMBOLS else 0
    successful_times = [r.get('processing_time', 0) for r in results_list if r['status'] == 'SUCCESS']
    avg_success_time = sum(successful_times) / len(successful_times) if successful_times else 0
    
    print("\n" + "="*100)
    print(f"SUMMARY: {successful} successful, {failed} failed out of {len(SYMBOLS)} total symbols")
    print(f"Total time: {total_elapsed:.2f}s | Avg per symbol: {avg_time:.2f}s | Avg successful: {avg_success_time:.2f}s")
    print(f"Results saved to: {RESULTS_CSV}")
    print("="*100 + "\n")
    
    logger.success(f"Multi-symbol analysis complete in {total_elapsed:.2f}s!")


if __name__ == "__main__":
    main()

