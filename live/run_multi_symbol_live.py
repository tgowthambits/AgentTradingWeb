"""
Live Multi-Symbol Monitoring with Color-Coded Output
====================================================
Simplified, color-coded display that updates every 5 seconds
"""

import pandas as pd
import numpy as np
from datetime import datetime
from loguru import logger
import sys
import time
import yaml
from pathlib import Path

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    from rich import box
    from rich.text import Text
    console = Console()
except ImportError:
    logger.warning("rich not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich"])
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    from rich import box
    from rich.text import Text
    console = Console()

from pipeline.live_inference import live_inference
from Data.fyers_data_final import FyersDataScanner
from utils.features import add_technical_features, add_advanced_features


# ============================================================
# CONFIGURATION
# ============================================================

def load_config(config_path="configs/symbols_config.yaml"):
    """Load configuration from YAML file"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

CONFIG = load_config()
SYMBOLS = CONFIG['symbols']
START_DATE = CONFIG['date_range']['start_date']
END_DATE = CONFIG['date_range']['end_date']
RESULTS_CSV = CONFIG['output']['results_csv']
HAS_POSITION = CONFIG.get('has_position', False)
PERFORMANCE = CONFIG.get('performance', {})
PARAMS_CONFIG = PERFORMANCE.get('params_config', 'configs/params.yaml')
MAX_INTRADAY_ROWS = PERFORMANCE.get('max_intraday_rows', 1000)
REFRESH_INTERVAL = 5  # seconds

# Trading tracker (persists across refreshes)
TRADING_TRACKER = {}
ORDER_HISTORY = []  # List of all orders with details
ORDER_ID_COUNTER = 1


# ============================================================
# RICH FORMATTING
# ============================================================

def get_signal_style(signal):
    """Get rich style for signal"""
    if signal == 1 or signal == "BUY":
        return "bold green"
    elif signal == -1 or signal == "SELL":
        return "bold red"
    else:
        return "bold yellow"

def format_signal(signal):
    """Format signal with rich styling"""
    signal_map = {1: "BUY", -1: "SELL", 0: "HOLD"}
    signal_str = signal_map.get(signal, "UNKNOWN")
    return signal_str


# ============================================================
# DATA LOADING
# ============================================================

def load_symbol_data(symbol, start_date, end_date, max_intraday_rows=1000):
    """Load data for a symbol"""
    scanner = FyersDataScanner()
    
    # Load Daily Data
    scanner.start_date = start_date
    scanner.end_date = end_date
    scanner.symbol = symbol
    scanner.resolution = '1'
    
    daily_df = scanner.get_data().sort_values(by='date')
    print(daily_df.tail(1).to_string())
    daily_df = daily_df.rename(columns={
        'Time': 'time', 'Open': 'open', 'High': 'high', 'Low': 'low',
        'Close': 'close', 'TradeVol': 'tradevol', 'date': 'date',
        'datetime': 'datetime', 'daily_return_open_close': 'daily_return_open_close',
        'daily_return': 'daily_return', 'state': 'state'
    })
    
    daily_df["daily_return"] = daily_df["close"].pct_change().fillna(0)
    daily_df = add_technical_features(daily_df)
    daily_df = add_advanced_features(daily_df)
    
    # Load Intraday Data
    scanner.start_date = start_date
    scanner.end_date = end_date
    scanner.symbol = symbol
    scanner.resolution = '5S'
    
    intraday_df = scanner.get_data()
    intraday_df = intraday_df.rename(columns={
        'Time': 'time', 'Open': 'open', 'High': 'high', 'Low': 'low',
        'Close': 'close', 'TradeVol': 'tradevol', 'date': 'date',
        'datetime': 'datetime', 'daily_return_open_close': 'daily_return_open_close',
        'daily_return': 'daily_return', 'state': 'state'
    })
    intraday_df["return"] = intraday_df["close"].pct_change().fillna(0)
    
    # Sample intraday data if too large
    if len(intraday_df) > max_intraday_rows:
        intraday_df = intraday_df.tail(max_intraday_rows).reset_index(drop=True).sort_values(by='date')
    
    prices = intraday_df["close"].values
    return daily_df, intraday_df, prices


def update_trading_tracker(symbol, final_signal, latest_price):
    """Update trading tracker with detailed order history - prevents duplicate orders"""
    global TRADING_TRACKER, ORDER_HISTORY, ORDER_ID_COUNTER
    from datetime import datetime
    
    if symbol not in TRADING_TRACKER:
        TRADING_TRACKER[symbol] = {
            'orders': 0,
            'realized_pnl': 0.0,
            'last_signal': 0,
            'last_price': latest_price,
            'position': 0,  # 0=no position, 1=long, -1=short
            'entry_price': 0,
            'entry_time': None,
            'quantity': 1,  # Default quantity
            'current_order_id': None
        }
    
    tracker = TRADING_TRACKER[symbol]
    current_time = datetime.now()
    
    # PREVENT DUPLICATE ORDERS:
    # Only process if signal actually changed OR if we need to close a position
    signal_changed = final_signal != tracker['last_signal']
    has_open_position = tracker['position'] != 0
    same_direction_signal = (final_signal == 1 and tracker['position'] == 1) or \
                           (final_signal == -1 and tracker['position'] == -1)
    
    # Skip if signal is same as current position (prevents re-entry)
    if same_direction_signal:
        # Position already exists in this direction, just update unrealized PnL
        pass
    elif signal_changed or (final_signal == 0 and has_open_position):
        # Close existing position if any (when signal changes)
        if has_open_position and tracker['current_order_id'] is not None:
            # Find and update the order in history
            for order in ORDER_HISTORY:
                if order['order_id'] == tracker['current_order_id'] and order['status'] == 'OPEN':
                    realized_pnl = (latest_price - tracker['entry_price']) * tracker['position'] * tracker['quantity']
                    order['exit_price'] = latest_price
                    order['exit_time'] = current_time
                    order['pnl'] = realized_pnl
                    order['status'] = 'CLOSED'
                    tracker['realized_pnl'] += realized_pnl
                    tracker['orders'] += 1
                    break
            
            tracker['position'] = 0
            tracker['entry_price'] = 0
            tracker['current_order_id'] = None
        
        # Open new position ONLY if no position exists OR position is in opposite direction
        if final_signal == 1 and tracker['position'] != 1:  # BUY (only if not already LONG)
            new_order = {
                'order_id': ORDER_ID_COUNTER,
                'symbol': symbol,
                'type': 'LONG',
                'entry_price': latest_price,
                'entry_time': current_time,
                'exit_price': None,
                'exit_time': None,
                'quantity': tracker['quantity'],
                'pnl': 0.0,
                'status': 'OPEN'
            }
            ORDER_HISTORY.append(new_order)
            
            tracker['position'] = 1
            tracker['entry_price'] = latest_price
            tracker['entry_time'] = current_time
            tracker['current_order_id'] = ORDER_ID_COUNTER
            tracker['orders'] += 1
            
            ORDER_ID_COUNTER += 1
            
        elif final_signal == -1 and tracker['position'] != -1:  # SELL (only if not already SHORT)
            new_order = {
                'order_id': ORDER_ID_COUNTER,
                'symbol': symbol,
                'type': 'SHORT',
                'entry_price': latest_price,
                'entry_time': current_time,
                'exit_price': None,
                'exit_time': None,
                'quantity': tracker['quantity'],
                'pnl': 0.0,
                'status': 'OPEN'
            }
            ORDER_HISTORY.append(new_order)
            
            tracker['position'] = -1
            tracker['entry_price'] = latest_price
            tracker['entry_time'] = current_time
            tracker['current_order_id'] = ORDER_ID_COUNTER
            tracker['orders'] += 1
            
            ORDER_ID_COUNTER += 1
    
    # Calculate unrealized PnL for open position
    unrealized_pnl = 0.0
    if tracker['position'] != 0 and tracker['entry_price'] > 0:
        unrealized_pnl = (latest_price - tracker['entry_price']) * tracker['position'] * tracker['quantity']
        
        # Update current order's unrealized PnL
        if tracker['current_order_id'] is not None:
            for order in ORDER_HISTORY:
                if order['order_id'] == tracker['current_order_id'] and order['status'] == 'OPEN':
                    order['pnl'] = unrealized_pnl
                    break
    
    # Total PnL = realized + unrealized
    total_pnl = tracker['realized_pnl'] + unrealized_pnl
    
    # Update last signal and price
    tracker['last_signal'] = final_signal
    tracker['last_price'] = latest_price
    
    return tracker['orders'], total_pnl, unrealized_pnl

def analyze_symbol(symbol, start_date, end_date):
    """Analyze single symbol and return simplified results"""
    try:
        daily_df, intraday_df, prices = load_symbol_data(
            symbol, start_date, end_date, 
            max_intraday_rows=MAX_INTRADAY_ROWS
        )
        
        output = live_inference(
            daily_df, intraday_df, prices, 
            config_path=PARAMS_CONFIG,
            has_position=HAS_POSITION
        )
        
        daily = output["daily_models"]
        intraday = output["intraday_models"]
        filters = output["filters_applied"]
        confirmations = output["confirmations"]
        
        # Get latest price from intraday data
        latest_price = intraday_df['close'].iloc[-1] if len(intraday_df) > 0 else 0
        
        # Update trading tracker
        orders, pnl, unrealized_pnl = update_trading_tracker(symbol, output['final_signal'], float(latest_price))
        
        return {
            'symbol': symbol,
            'status': 'SUCCESS',
            'latest_price': float(latest_price),
            'final_signal': output['final_signal'],
            'raw_signal': output['raw_signal'],
            'daily_signal': daily['vomc_daily_signal'],
            'daily_prob': daily['vomc_daily_prob'],
            'daily_regime': daily['daily_regime'],
            'daily_return_pred': daily['daily_return_prediction'],
            'intraday_signal': intraday['vomc_intraday_signal'],
            'intraday_prob': intraday['vomc_intraday_prob'],
            'intraday_regime': intraday['intraday_regime'],
            'intraday_return_pred': intraday['intraday_return_prediction'],
            'rl_action': intraday['rl_intraday_action'],
            'volatility': output['volatility_value'],
            'volatility_pos': output['volatility_positive'],
            'volatility_neg': output['volatility_negative'],
            'trend_filter': filters['trend'],
            'breakout_filter': filters['breakout'],
            'momentum_filter': filters['momentum'],
            'volatility_filter': filters['volatility'],
            'confidence_filter': filters['confidence'],
            'trend_conf': confirmations['trend'],
            'breakout_conf': confirmations['breakout'],
            'momentum_conf': confirmations['momentum'],
            'confirmations': sum(confirmations.values()),
            'orders': orders,
            'pnl': pnl,
            'unrealized_pnl': unrealized_pnl
        }
    except Exception as e:
        return {
            'symbol': symbol,
            'status': 'ERROR',
            'error': str(e),
            'final_signal': 0,
            'latest_price': 0,
            'orders': 0,
            'pnl': 0.0,
            'unrealized_pnl': 0.0
        }


# ============================================================
# DISPLAY
# ============================================================

def clear_screen():
    """Clear terminal screen"""
    console.clear()

def print_header():
    """Print header with timestamp"""
    clear_screen()
    header_text = f"Real-time Multi-Symbol Monitor\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    console.print(Panel(header_text, style="bold blue", expand=False))

def print_symbol_results(results):
    """Print single combined table with ALL symbols and detailed order tables"""
    print_combined_table(results)
    print_open_positions()
    print_closed_orders()

def print_open_positions():
    """Print table of open positions with unrealized PnL"""
    open_orders = [o for o in ORDER_HISTORY if o['status'] == 'OPEN']
    
    if not open_orders:
        return
    
    table = Table(
        title="[bold yellow]📊 Open Positions (Unrealized PnL)[/bold yellow]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("ID", style="dim", width=5)
    table.add_column("Symbol", style="cyan", width=20)
    table.add_column("Type", style="white", width=8)
    table.add_column("Entry Price", style="white", width=12)
    table.add_column("Current Price", style="white", width=12)
    table.add_column("Entry Time", style="dim white", width=19)
    table.add_column("Qty", style="white", width=5)
    table.add_column("Unrealized PnL", style="white", width=14)
    
    total_unrealized = 0.0
    
    for order in open_orders:
        symbol_short = order['symbol'].split(':')[-1]
        entry_time_str = order['entry_time'].strftime("%Y-%m-%d %H:%M:%S")
        
        # Get current price from tracker
        current_price = TRADING_TRACKER.get(order['symbol'], {}).get('last_price', order['entry_price'])
        
        pnl = order['pnl']
        total_unrealized += pnl
        
        pnl_str = f"₹{pnl:+.2f}"
        pnl_color = "green" if pnl > 0 else "red" if pnl < 0 else "white"
        
        order_type_color = "green" if order['type'] == 'LONG' else "red"
        
        table.add_row(
            str(order['order_id']),
            symbol_short,
            Text(order['type'], style=order_type_color),
            f"₹{order['entry_price']:.2f}",
            f"₹{current_price:.2f}",
            entry_time_str,
            str(order['quantity']),
            Text(pnl_str, style=pnl_color)
        )
    
    # Add total row
    total_color = "green" if total_unrealized > 0 else "red" if total_unrealized < 0 else "white"
    table.add_row(
        "",
        "[bold]TOTAL[/bold]",
        "",
        "",
        "",
        "",
        "",
        Text(f"₹{total_unrealized:+.2f}", style=f"bold {total_color}")
    )
    
    console.print(table)
    console.print()

def print_closed_orders():
    """Print table of closed orders with realized PnL"""
    closed_orders = [o for o in ORDER_HISTORY if o['status'] == 'CLOSED']
    
    if not closed_orders:
        return
    
    table = Table(
        title="[bold green]✅ Completed Orders (Realized PnL)[/bold green]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("ID", style="dim", width=5)
    table.add_column("Symbol", style="cyan", width=20)
    table.add_column("Type", style="white", width=8)
    table.add_column("Entry Price", style="white", width=12)
    table.add_column("Exit Price", style="white", width=12)
    table.add_column("Entry Time", style="dim white", width=19)
    table.add_column("Exit Time", style="dim white", width=19)
    table.add_column("Qty", style="white", width=5)
    table.add_column("Realized PnL", style="white", width=14)
    
    total_realized = 0.0
    
    for order in closed_orders:
        symbol_short = order['symbol'].split(':')[-1]
        entry_time_str = order['entry_time'].strftime("%Y-%m-%d %H:%M:%S")
        exit_time_str = order['exit_time'].strftime("%Y-%m-%d %H:%M:%S") if order['exit_time'] else "N/A"
        
        pnl = order['pnl']
        total_realized += pnl
        
        pnl_str = f"₹{pnl:+.2f}"
        pnl_color = "green" if pnl > 0 else "red" if pnl < 0 else "white"
        
        order_type_color = "green" if order['type'] == 'LONG' else "red"
        
        table.add_row(
            str(order['order_id']),
            symbol_short,
            Text(order['type'], style=order_type_color),
            f"₹{order['entry_price']:.2f}",
            f"₹{order['exit_price']:.2f}" if order['exit_price'] else "N/A",
            entry_time_str,
            exit_time_str,
            str(order['quantity']),
            Text(pnl_str, style=pnl_color)
        )
    
    # Add total row
    total_color = "green" if total_realized > 0 else "red" if total_realized < 0 else "white"
    table.add_row(
        "",
        "[bold]TOTAL[/bold]",
        "",
        "",
        "",
        "",
        "",
        "",
        Text(f"₹{total_realized:+.2f}", style=f"bold {total_color}")
    )
    
    console.print(table)
    console.print()

def print_combined_table(results):
    """Print single table with ALL symbols combined"""
    
    # Create comprehensive table
    table = Table(
        title="[bold cyan]Multi-Symbol Trading Monitor - Complete Analysis[/bold cyan]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta"
    )
    
    # Add columns
    table.add_column("Symbol", style="cyan", width=20)
    table.add_column("LTP (₹)", style="white", width=10)
    table.add_column("Final\nSignal", style="white", width=8)
    table.add_column("Raw\nSignal", style="white", width=8)
    table.add_column("Daily\nVOMC", style="white", width=8)
    table.add_column("Daily\nProb", style="white", width=7)
    table.add_column("Intra\nVOMC", style="white", width=8)
    table.add_column("Intra\nProb", style="white", width=7)
    table.add_column("RL\nAgent", style="white", width=7)
    table.add_column("Regime\nD/I", style="white", width=7)
    table.add_column("Vol\n%", style="white", width=7)
    table.add_column("Filters\nT/B/M", style="white", width=10)
    table.add_column("Conf\n/3", style="white", width=5)
    table.add_column("Orders", style="white", width=7)
    table.add_column("PnL (₹)", style="white", width=10)
    table.add_column("Status", style="white", width=8)
    
    # Add rows for each symbol
    for result in results:
        if result['status'] == 'SUCCESS':
            symbol_short = result['symbol'].split(':')[-1]
            
            # Signals with colors
            final_signal = format_signal(result['final_signal'])
            final_style = get_signal_style(result['final_signal'])
            
            raw_signal = format_signal(result['raw_signal'])
            raw_style = get_signal_style(result['raw_signal'])
            
            daily_signal = format_signal(result['daily_signal'])
            daily_style = get_signal_style(result['daily_signal'])
            
            intra_signal = format_signal(result['intraday_signal'])
            intra_style = get_signal_style(result['intraday_signal'])
            
            # RL Agent
            rl_signal_map = {0: "BUY", 1: "SELL", 2: "HOLD"}
            rl_signal_str = rl_signal_map.get(result['rl_action'], "?")
            
            # Regimes
            regime_str = f"{result['daily_regime']}/{result['intraday_regime']}"
            
            # Filters (Trend/Breakout/Momentum)
            filter_map = {1: "B", -1: "b", 0: "N", None: "-"}  # B=Bullish, b=bearish, N=neutral
            trend_char = filter_map.get(result['trend_filter'], "-")
            breakout_char = filter_map.get(result['breakout_filter'], "-")
            momentum_char = filter_map.get(result['momentum_filter'], "-")
            filters_str = f"{trend_char}/{breakout_char}/{momentum_char}"
            
            # Trading info
            orders = result.get('orders', 0)
            pnl = result.get('pnl', 0.0)
            unrealized = result.get('unrealized_pnl', 0.0)
            
            # Format PnL with indicator for unrealized
            if unrealized != 0:
                pnl_str = f"{pnl:+.2f}*"  # * indicates unrealized
            else:
                pnl_str = f"{pnl:+.2f}" if pnl != 0 else "0.00"
            
            pnl_color = "green" if pnl > 0 else "red" if pnl < 0 else "white"
            
            table.add_row(
                symbol_short,
                f"{result['latest_price']:.2f}",
                Text(final_signal, style=final_style),
                Text(raw_signal, style=raw_style),
                Text(daily_signal, style=daily_style),
                f"{result['daily_prob']:.1%}",
                Text(intra_signal, style=intra_style),
                f"{result['intraday_prob']:.1%}",
                rl_signal_str,
                regime_str,
                f"{result['volatility']:.2%}",
                filters_str,
                f"{result['confirmations']}",
                str(orders),
                Text(pnl_str, style=pnl_color),
                "[green]✓[/green]"
            )
        else:
            symbol_short = result['symbol'].split(':')[-1]
            table.add_row(
                symbol_short,
                "N/A", "ERROR", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", 
                "N/A", "N/A", "N/A", "N/A", "0", "0.00",
                "[red]✗[/red]"
            )
    
    # Add summary row
    total_orders = sum(r.get('orders', 0) for r in results if r['status'] == 'SUCCESS')
    total_pnl = sum(r.get('pnl', 0.0) for r in results if r['status'] == 'SUCCESS')
    pnl_color = "green" if total_pnl > 0 else "red" if total_pnl < 0 else "white"
    
    table.add_row(
        "[bold yellow]TOTAL[/bold yellow]",
        "", "", "", "", "", "", "", "", "", "", "", "",
        f"[bold]{total_orders}[/bold]",
        Text(f"{total_pnl:+.2f}", style=f"bold {pnl_color}"),
        ""
    )
    
    console.print(table)
    
    # Print legend
    console.print("\n[yellow]Legend:[/yellow]")
    console.print("  Signals: [green]BUY[/green] | [red]SELL[/red] | [yellow]HOLD[/yellow]")
    console.print("  Filters (T/B/M): B=Bullish, b=bearish, N=neutral, -=none")
    console.print("  Regime D/I: Daily/Intraday regime (0,1,2)")
    console.print("  Conf: Confirmations out of 3 (Trend, Breakout, Momentum)")
    console.print("  [dim]PnL with * = Unrealized (open position)[/dim]")
    console.print(f"  [bold]Total Orders:[/bold] {total_orders}  |  [bold]Total PnL:[/bold] ₹{total_pnl:+.2f}")
    console.print(f"  [dim]Detailed order tables shown below[/dim]")

def print_comprehensive_table_old(result):
    """Print single comprehensive table with ALL details"""
    symbol_short = result['symbol'].split(':')[-1]
    
    # Create single comprehensive table
    table = Table(
        title=f"[bold cyan]{symbol_short}[/bold cyan] - Complete Analysis",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta"
    )
    
    table.add_column("Category", style="cyan", width=20)
    table.add_column("Metric", style="white", width=25)
    table.add_column("Value", style="white", width=20)
    table.add_column("Details", style="dim white", width=30)
    
    # Market Data Section
    table.add_row(
        "[bold yellow]MARKET DATA[/bold yellow]",
        "Latest Price (LTP)",
        f"[bold white]₹{result['latest_price']:.2f}[/bold white]",
        ""
    )
    table.add_row(
        "",
        "Volatility",
        f"{result['volatility']:.2%}",
        f"+{result['volatility_pos']:.2%} / -{result['volatility_neg']:.2%}"
    )
    
    # Daily Models Section
    daily_signal = format_signal(result['daily_signal'])
    daily_style = get_signal_style(result['daily_signal'])
    table.add_row(
        "[bold yellow]DAILY MODELS[/bold yellow]",
        "VOMC Signal",
        Text(daily_signal, style=daily_style),
        f"Probability: {result['daily_prob']:.2%}"
    )
    table.add_row(
        "",
        "HMM Regime",
        f"Regime {result['daily_regime']}",
        ""
    )
    table.add_row(
        "",
        "XGBoost Prediction",
        f"{result['daily_return_pred']:.4f}",
        "Expected Return"
    )
    
    # Intraday Models Section
    intra_signal = format_signal(result['intraday_signal'])
    intra_style = get_signal_style(result['intraday_signal'])
    table.add_row(
        "[bold yellow]INTRADAY MODELS[/bold yellow]",
        "VOMC Signal",
        Text(intra_signal, style=intra_style),
        f"Probability: {result['intraday_prob']:.2%}"
    )
    table.add_row(
        "",
        "HMM Regime",
        f"Regime {result['intraday_regime']}",
        ""
    )
    table.add_row(
        "",
        "XGBoost Prediction",
        f"{result['intraday_return_pred']:.4f}",
        "Expected Return"
    )
    
    # RL Agent
    rl_signal_map = {0: "BUY", 1: "SELL", 2: "HOLD"}
    rl_signal_str = rl_signal_map.get(result['rl_action'], "UNKNOWN")
    rl_style = get_signal_style(result['rl_action'] if result['rl_action'] == 2 else (1 if result['rl_action'] == 0 else -1))
    table.add_row(
        "",
        "RL Agent",
        Text(rl_signal_str, style=rl_style),
        f"Action: {result['rl_action']}"
    )
    
    # Precision Filters Section
    vol_status = "[green]✓ PASS[/green]" if result['volatility_filter'] else "[red]✗ FAIL[/red]"
    table.add_row(
        "[bold yellow]FILTERS[/bold yellow]",
        "Volatility Filter",
        vol_status,
        f"Threshold: 1.00%"
    )
    
    trend_map = {1: "BULLISH", -1: "BEARISH", 0: "NEUTRAL", None: "N/A"}
    trend_str = trend_map.get(result['trend_filter'], "N/A")
    trend_conf_str = "✓" if result['trend_conf'] else "✗"
    table.add_row(
        "",
        "Trend (MA50/200)",
        trend_str,
        f"Confirms: {trend_conf_str}"
    )
    
    breakout_str = trend_map.get(result['breakout_filter'], "N/A")
    breakout_conf_str = "✓" if result['breakout_conf'] else "✗"
    table.add_row(
        "",
        "Breakout",
        breakout_str,
        f"Confirms: {breakout_conf_str}"
    )
    
    momentum_str = trend_map.get(result['momentum_filter'], "N/A")
    momentum_conf_str = "✓" if result['momentum_conf'] else "✗"
    table.add_row(
        "",
        "Momentum (RSI)",
        momentum_str,
        f"Confirms: {momentum_conf_str}"
    )
    
    conf_status = "[green]✓ PASS[/green]" if result['confidence_filter'] else "[red]✗ FAIL[/red]"
    table.add_row(
        "",
        "Confidence",
        conf_status,
        f"Max: {max(result['daily_prob'], result['intraday_prob']):.2%}"
    )
    
    # Signal Summary Section
    raw_signal = format_signal(result['raw_signal'])
    raw_style = get_signal_style(result['raw_signal'])
    table.add_row(
        "[bold yellow]SIGNALS[/bold yellow]",
        "Raw Signal",
        Text(raw_signal, style=raw_style),
        "Before Filters"
    )
    
    final_signal = format_signal(result['final_signal'])
    final_style = get_signal_style(result['final_signal'])
    table.add_row(
        "",
        "Final Signal",
        Text(final_signal, style=final_style),
        f"After Filters | Conf: {result['confirmations']}/3"
    )
    
    console.print(table)

def print_summary_stats(results, elapsed):
    """Print summary statistics"""
    successful = sum(1 for r in results if r['status'] == 'SUCCESS')
    failed = sum(1 for r in results if r['status'] == 'ERROR')
    
    summary_table = Table(title="Analysis Summary", box=box.ROUNDED, show_header=False)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="white")
    
    summary_table.add_row("✓ Successful", f"[green]{successful}[/green]")
    summary_table.add_row("✗ Failed", f"[red]{failed}[/red]")
    summary_table.add_row("⏱  Time", f"{elapsed:.1f}s")
    summary_table.add_row("📊 Total Symbols", str(len(results)))
    
    console.print(summary_table)


# ============================================================
# MAIN LOOP
# ============================================================

def run_once():
    """Run analysis once for all symbols"""
    results = []
    start_time = time.time()
    
    for symbol in SYMBOLS:
        result = analyze_symbol(symbol, START_DATE, END_DATE)
        results.append(result)
    
    elapsed = time.time() - start_time
    
    # Display results
    print_header()
    print_symbol_results(results)
    print_summary_stats(results, elapsed)
    
    return results

def countdown_sleep(seconds):
    """Sleep with countdown display - simple version"""
    for remaining in range(seconds, 0, -1):
        console.print(f"[yellow]⏱  Next refresh in: {remaining}s  |  Press Ctrl+C to stop[/yellow]", end="\r")
        time.sleep(1)
    console.print(" " * 80, end="\r")  # Clear the line

def main():
    """Main loop - run every N seconds"""
    # Reduce logging verbosity for cleaner output
    logger.remove()
    logger.add(sys.stderr, level="ERROR")
    
    # Show startup info
    console.print("\n[bold green]STARTING LIVE MONITOR[/bold green]")
    info_table = Table(box=box.SIMPLE, show_header=False)
    info_table.add_column("Setting", style="cyan")
    info_table.add_column("Value", style="white")
    info_table.add_row("📊 Symbols", str(len(SYMBOLS)))
    info_table.add_row("🔄 Refresh", f"Every {REFRESH_INTERVAL} seconds")
    info_table.add_row("⚙️  Config", PARAMS_CONFIG)
    info_table.add_row("💾 Output", RESULTS_CSV)
    console.print(info_table)
    console.print()
    
    try:
        iteration = 0
        while True:
            iteration += 1
            
            # Show iteration number
            console.print(Panel(f"[bold blue]REFRESH #{iteration}[/bold blue]", expand=False))
            console.print()
            
            try:
                results = run_once()
                
                # Save to CSV
                if results:
                    df = pd.DataFrame(results)
                    df.to_csv(RESULTS_CSV, index=False)
                
            except KeyboardInterrupt:
                raise
            except Exception as e:
                console.print(f"[red]❌ Error in iteration {iteration}: {str(e)}[/red]")
            
            # Countdown before next refresh
            if iteration == 1:
                console.print("\n[green]✅ Monitor is now running continuously![/green]\n")
            
            countdown_sleep(REFRESH_INTERVAL)
            
    except KeyboardInterrupt:
        console.print("\n\n[yellow]🛑 Monitor stopped by user.[/yellow]")
        console.print(f"[green]💾 Results saved to: {RESULTS_CSV}[/green]\n")

if __name__ == "__main__":
    main()

