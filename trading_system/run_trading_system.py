"""
Main Trading System Runner

This script demonstrates how to use the plug-and-play trading system.
Simply add/remove indicators and the system will automatically use them!
"""

import sys
import os
import yaml
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich import box

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading_system.core.trading_engine import TradingEngine
from trading_system.data.data_loader import DataLoader

# Import indicators
from trading_system.indicators.rsi_indicator import RSIIndicator
from trading_system.indicators.ma_crossover_indicator import MACrossoverIndicator
from trading_system.indicators.macd_indicator import MACDIndicator
from trading_system.indicators.bollinger_indicator import BollingerBandsIndicator


console = Console()


def load_config(config_path="trading_system/config/trading_config.yaml"):
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def initialize_indicators(config):
    """
    Initialize all indicators based on configuration.
    
    TO ADD A NEW INDICATOR:
    1. Create indicator class inheriting from BaseIndicator
    2. Implement calculate() and get_required_columns()
    3. Add configuration to trading_config.yaml
    4. Import and add to this function
    """
    indicators = []
    
    # RSI Indicator
    if config['indicators']['rsi']['enabled']:
        indicators.append(RSIIndicator(config['indicators']['rsi']))
    
    # Moving Average Crossover
    if config['indicators']['ma_crossover']['enabled']:
        indicators.append(MACrossoverIndicator(config['indicators']['ma_crossover']))
    
    # MACD
    if config['indicators']['macd']['enabled']:
        indicators.append(MACDIndicator(config['indicators']['macd']))
    
    # Bollinger Bands
    if config['indicators']['bollinger_bands']['enabled']:
        indicators.append(BollingerBandsIndicator(config['indicators']['bollinger_bands']))
    
    # ADD NEW INDICATORS HERE:
    # if config['indicators']['your_indicator']['enabled']:
    #     indicators.append(YourIndicator(config['indicators']['your_indicator']))
    
    return indicators


def print_summary_table(results):
    """Print summary table with all symbols."""
    table = Table(
        title="[bold cyan]Multi-Symbol Trading Analysis[/bold cyan]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta"
    )
    
    table.add_column("Symbol", style="cyan", width=20)
    table.add_column("Price (₹)", style="white", width=10)
    table.add_column("Final Signal", style="white", width=12)
    table.add_column("Agreement", style="white", width=10)
    table.add_column("BUY", style="green", width=5)
    table.add_column("SELL", style="red", width=5)
    table.add_column("HOLD", style="yellow", width=5)
    
    for result in results:
        symbol_short = result['symbol'].split(':')[-1]
        
        # Color-code the final signal
        signal = result['final_signal']
        if signal == 'BUY':
            signal_text = f"[green bold]{signal}[/green bold]"
        elif signal == 'SELL':
            signal_text = f"[red bold]{signal}[/red bold]"
        else:
            signal_text = f"[yellow]{signal}[/yellow]"
        
        breakdown = result['signal_breakdown']
        
        table.add_row(
            symbol_short,
            f"{result['latest_price']:.2f}",
            signal_text,
            f"{result['agreement_score']:.0%}",
            str(breakdown.get('BUY', 0)),
            str(breakdown.get('SELL', 0)),
            str(breakdown.get('HOLD', 0))
        )
    
    console.print(table)


def print_indicator_details(result):
    """Print detailed indicator signals for a symbol."""
    table = Table(
        title=f"[bold]Indicator Details: {result['symbol']}[/bold]",
        box=box.SIMPLE,
        show_header=True
    )
    
    table.add_column("Indicator", style="cyan", width=25)
    table.add_column("Signal", style="white", width=10)
    
    for indicator, signal in result['indicator_signals'].items():
        if signal == 'BUY':
            signal_text = f"[green]{signal}[/green]"
        elif signal == 'SELL':
            signal_text = f"[red]{signal}[/red]"
        else:
            signal_text = f"[yellow]{signal}[/yellow]"
        
        table.add_row(indicator, signal_text)
    
    console.print(table)


def main():
    """Main function to run the trading system."""
    
    console.print("\n[bold cyan]🚀 Starting Trading System...[/bold cyan]\n")
    
    # Load configuration
    config = load_config()
    console.print("✅ Configuration loaded")
    
    # Initialize trading engine
    engine = TradingEngine(aggregation_strategy=config['aggregation_strategy'])
    console.print(f"✅ Trading engine initialized (strategy: {config['aggregation_strategy']})")
    
    # Initialize and register indicators
    indicators = initialize_indicators(config)
    engine.register_indicators(indicators)
    console.print(f"✅ Registered {len(indicators)} indicators\n")
    
    # Initialize data loader
    data_loader = DataLoader()
    
    # Analyze each symbol
    results = []
    
    for symbol in config['symbols']:
        try:
            console.print(f"\n[bold]📊 Analyzing: {symbol}[/bold]")
            console.print("─" * 70)
            
            # Load data
            df = data_loader.load_symbol_data(
                symbol,
                config['date_range']['start_date'],
                config['date_range']['end_date'],
                config['resolution']
            )
            
            console.print(f"✅ Loaded {len(df)} rows of data")
            
            # Prepare data for indicators
            df = data_loader.prepare_for_indicators(df)
            
            # Analyze symbol
            result = engine.analyze_symbol(
                df, 
                symbol, 
                verbose=config['output']['verbose']
            )
            
            results.append(result)
            
            # Print individual indicator signals
            if config['output']['verbose']:
                print_indicator_details(result)
            
            # Execute trading decision (if enabled)
            if config['trading']['enable_auto_trading']:
                order = engine.execute_trading_decision(
                    result, 
                    quantity=config['trading']['default_quantity']
                )
            
        except Exception as e:
            console.print(f"[red]❌ Error analyzing {symbol}: {str(e)}[/red]")
    
    # Print summary
    console.print("\n" + "="*70)
    console.print("[bold cyan]📊 TRADING SUMMARY[/bold cyan]")
    console.print("="*70 + "\n")
    
    print_summary_table(results)
    
    # Print trading statistics
    summary = engine.get_summary()
    console.print(f"\n[bold]Trading Statistics:[/bold]")
    console.print(f"  Total Orders: {summary['total_orders']}")
    console.print(f"  Open Positions: {summary['open_positions']}")
    console.print(f"  Closed Orders: {summary['closed_orders']}")
    console.print(f"  Total PnL: ₹{summary['total_pnl']:+.2f}")
    
    # Show open positions
    if summary['open_positions'] > 0:
        console.print("\n[bold yellow]📊 Open Positions:[/bold yellow]")
        console.print(engine.get_open_positions().to_string(index=False))
    
    # Show closed orders
    if summary['closed_orders'] > 0:
        console.print("\n[bold green]✅ Closed Orders:[/bold green]")
        console.print(engine.get_closed_orders().to_string(index=False))
    
    console.print("\n[bold green]✅ Analysis Complete![/bold green]\n")


if __name__ == "__main__":
    main()

