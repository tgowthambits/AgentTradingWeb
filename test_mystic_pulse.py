#!/usr/bin/env python3
"""
Test Mystic Pulse Indicator

Tests the newly created Mystic Pulse indicator.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trading_system.indicators.mystic_pulse_indicator import MysticPulseIndicator
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def create_sample_data(num_bars=200):
    """Create sample OHLC data for testing."""
    dates = pd.date_range(start='2024-01-01', periods=num_bars, freq='5min')
    
    # Generate realistic price data with trend
    base_price = 100
    trend = np.linspace(0, 10, num_bars)
    noise = np.random.randn(num_bars) * 2
    
    close_prices = base_price + trend + noise
    
    # Generate OHLC from close
    data = {
        'datetime': dates,
        'open': close_prices + np.random.randn(num_bars) * 0.5,
        'high': close_prices + np.abs(np.random.randn(num_bars) * 1.5),
        'low': close_prices - np.abs(np.random.randn(num_bars) * 1.5),
        'close': close_prices,
        'volume': np.random.randint(1000, 5000, num_bars)
    }
    
    return pd.DataFrame(data)


def test_indicator_creation():
    """Test creating the indicator."""
    console.print("\n[bold cyan]Test 1: Indicator Creation[/bold cyan]\n")
    
    try:
        indicator = MysticPulseIndicator()
        console.print(f"✅ Created: {indicator}\n")
        
        # Test with custom config
        indicator_custom = MysticPulseIndicator(config={
            'adx_length': 14,
            'smoothing_factor': 2,
            'buy_threshold': 3,
            'sell_threshold': 3
        })
        console.print(f"✅ Created with config: {indicator_custom}\n")
        
        return True
        
    except Exception as e:
        console.print(f"❌ Failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_indicator_calculation():
    """Test indicator calculations."""
    console.print("[bold cyan]Test 2: Indicator Calculation[/bold cyan]\n")
    
    try:
        # Create indicator
        indicator = MysticPulseIndicator(config={
            'adx_length': 9,
            'smoothing_factor': 1,
            'buy_threshold': 2,
            'sell_threshold': 2,
            'min_trend_score': 3
        })
        
        # Create sample data
        df = create_sample_data(200)
        console.print(f"📊 Created sample data: {len(df)} bars\n")
        
        # Calculate indicator
        result_df = indicator.calculate(df)
        
        # Check required columns exist
        required_cols = ['di_plus', 'di_minus', 'positive_count', 
                        'negative_count', 'trend_score', 'signal']
        
        missing_cols = [col for col in required_cols if col not in result_df.columns]
        
        if missing_cols:
            console.print(f"❌ Missing columns: {missing_cols}\n")
            return False
        
        console.print("✅ All required columns present\n")
        
        # Display statistics
        console.print("[bold]Calculation Statistics:[/bold]")
        console.print(f"  DI+ range: {result_df['di_plus'].min():.2f} to {result_df['di_plus'].max():.2f}")
        console.print(f"  DI- range: {result_df['di_minus'].min():.2f} to {result_df['di_minus'].max():.2f}")
        console.print(f"  Max positive count: {result_df['positive_count'].max()}")
        console.print(f"  Max negative count: {result_df['negative_count'].max()}")
        console.print(f"  Trend score range: {result_df['trend_score'].min()} to {result_df['trend_score'].max()}")
        console.print()
        
        # Signal distribution
        signal_counts = result_df['signal'].value_counts()
        console.print("[bold]Signal Distribution:[/bold]")
        for signal, count in signal_counts.items():
            pct = (count / len(result_df)) * 100
            console.print(f"  {signal}: {count} ({pct:.1f}%)")
        console.print()
        
        return True
        
    except Exception as e:
        console.print(f"❌ Calculation failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_signal_generation():
    """Test signal generation logic."""
    console.print("[bold cyan]Test 3: Signal Generation[/bold cyan]\n")
    
    try:
        indicator = MysticPulseIndicator(config={
            'adx_length': 9,
            'buy_threshold': 2,
            'sell_threshold': 2,
            'min_trend_score': 3
        })
        
        df = create_sample_data(200)
        result_df = indicator.calculate(df)
        
        # Get last 10 bars
        last_bars = result_df.tail(10)
        
        # Create display table
        table = Table(title="Last 10 Bars - Signals")
        table.add_column("Index", style="cyan")
        table.add_column("DI+", style="green")
        table.add_column("DI-", style="red")
        table.add_column("Pos Cnt", style="green")
        table.add_column("Neg Cnt", style="red")
        table.add_column("Score", style="yellow")
        table.add_column("Signal", style="bold magenta")
        
        for idx, row in last_bars.iterrows():
            signal_color = "green" if row['signal'] == 'BUY' else ("red" if row['signal'] == 'SELL' else "white")
            
            table.add_row(
                str(idx),
                f"{row['di_plus']:.2f}",
                f"{row['di_minus']:.2f}",
                str(int(row['positive_count'])),
                str(int(row['negative_count'])),
                str(int(row['trend_score'])),
                f"[{signal_color}]{row['signal']}[/{signal_color}]"
            )
        
        console.print(table)
        console.print()
        
        console.print("✅ Signal generation working\n")
        return True
        
    except Exception as e:
        console.print(f"❌ Signal generation failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_auto_discovery():
    """Test that auto-discovery finds the new indicator."""
    console.print("[bold cyan]Test 4: Auto-Discovery Integration[/bold cyan]\n")
    
    try:
        from trading_system.core.indicator_loader import IndicatorLoader
        
        # Discover indicators
        loader = IndicatorLoader(auto_sync=False)
        discovered = loader.discover_indicators()
        
        if 'mystic_pulse' in discovered:
            info = discovered['mystic_pulse']
            console.print("✅ Mystic Pulse discovered!\n")
            console.print(f"  Name: {info['name']}")
            console.print(f"  Module: {info['module']}")
            console.print(f"  Class: {info['class_name']}")
            console.print(f"  Parameters: {list(info['default_params'].keys())}")
            console.print()
            return True
        else:
            console.print("❌ Mystic Pulse not discovered\n")
            console.print(f"Discovered indicators: {list(discovered.keys())}\n")
            return False
            
    except Exception as e:
        console.print(f"❌ Auto-discovery test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    console.clear()
    
    panel = Panel(
        "[bold cyan]🔮 Mystic Pulse V2.0 Indicator Test Suite[/bold cyan]\n\n"
        "Testing the refactored Pine Script indicator...",
        style="bold green"
    )
    console.print(panel)
    console.print()
    
    results = []
    
    # Run tests
    results.append(("Indicator Creation", test_indicator_creation()))
    results.append(("Indicator Calculation", test_indicator_calculation()))
    results.append(("Signal Generation", test_signal_generation()))
    results.append(("Auto-Discovery", test_auto_discovery()))
    
    # Summary
    console.print("\n" + "="*60)
    console.print("[bold cyan]Test Summary[/bold cyan]")
    console.print("="*60 + "\n")
    
    passed = 0
    failed = 0
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        color = "green" if success else "red"
        console.print(f"{test_name}: [{color}]{status}[/{color}]")
        
        if success:
            passed += 1
        else:
            failed += 1
    
    console.print("\n" + "="*60)
    console.print(f"Total: [green]{passed} passed[/green], [red]{failed} failed[/red]")
    console.print("="*60 + "\n")
    
    if failed == 0:
        console.print("[bold green]🎉 All tests passed! Mystic Pulse is ready to use![/bold green]\n")
        console.print("[bold yellow]Next step: Run ./start_trading_bot.sh to auto-add to config![/bold yellow]\n")
        return 0
    else:
        console.print("[bold yellow]⚠️  Some tests failed. Please check the results above.[/bold yellow]\n")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

