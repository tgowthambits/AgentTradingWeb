#!/usr/bin/env python3
"""
Test Dynamic Indicator Loading

Validates that the plug-and-play architecture works correctly.
"""

import sys
import os

# Add to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trading_system.core.indicator_loader import IndicatorLoader
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def test_config_validation():
    """Test configuration validation."""
    console.print("\n[bold cyan]Test 1: Configuration Validation[/bold cyan]")
    
    try:
        loader = IndicatorLoader("trading_system/config/indicators_config.yaml")
        loader.validate_config()
        console.print("✅ Configuration is valid\n")
        return True
    except Exception as e:
        console.print(f"❌ Configuration validation failed: {e}\n")
        return False


def test_indicator_loading():
    """Test dynamic indicator loading."""
    console.print("[bold cyan]Test 2: Dynamic Indicator Loading[/bold cyan]\n")
    
    try:
        loader = IndicatorLoader("trading_system/config/indicators_config.yaml")
        indicators = loader.load_indicators(verbose=True)
        
        if len(indicators) > 0:
            console.print(f"\n✅ Successfully loaded {len(indicators)} indicators\n")
            return True, indicators
        else:
            console.print("\n❌ No indicators were loaded\n")
            return False, []
            
    except Exception as e:
        console.print(f"\n❌ Indicator loading failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False, []


def test_indicator_info():
    """Test getting indicator information."""
    console.print("[bold cyan]Test 3: Indicator Information[/bold cyan]\n")
    
    try:
        loader = IndicatorLoader("trading_system/config/indicators_config.yaml")
        info = loader.get_indicator_info()
        
        # Create table
        table = Table(title="Configured Indicators", show_header=True)
        table.add_column("Indicator", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Module", style="yellow")
        table.add_column("Weight", style="magenta")
        
        for ind in info:
            status = "✅ Enabled" if ind['enabled'] else "❌ Disabled"
            table.add_row(
                ind['name'],
                status,
                ind['module'],
                str(ind['weight'])
            )
        
        console.print(table)
        console.print()
        return True
        
    except Exception as e:
        console.print(f"❌ Failed to get indicator info: {e}\n")
        return False


def test_aggregation_config():
    """Test aggregation configuration."""
    console.print("[bold cyan]Test 4: Aggregation Configuration[/bold cyan]\n")
    
    try:
        loader = IndicatorLoader("trading_system/config/indicators_config.yaml")
        agg_config = loader.get_aggregation_config()
        
        console.print(f"Strategy: [green]{agg_config.get('strategy', 'N/A')}[/green]")
        
        if 'threshold' in agg_config:
            console.print("\nThreshold Settings:")
            threshold = agg_config['threshold']
            console.print(f"  Min Indicators (BUY): [yellow]{threshold.get('min_indicators_buy')}[/yellow]")
            console.print(f"  Min Indicators (SELL): [yellow]{threshold.get('min_indicators_sell')}[/yellow]")
            console.print(f"  Min Agreement %: [yellow]{threshold.get('min_agreement_percent')}%[/yellow]")
        
        console.print("\n✅ Aggregation config loaded successfully\n")
        return True
        
    except Exception as e:
        console.print(f"❌ Failed to get aggregation config: {e}\n")
        return False


def test_indicator_calculation(indicators):
    """Test that indicators can calculate."""
    console.print("[bold cyan]Test 5: Indicator Calculation Test[/bold cyan]\n")
    
    if not indicators:
        console.print("⏭️  Skipping (no indicators loaded)\n")
        return True
    
    try:
        # Create dummy data
        import pandas as pd
        import numpy as np
        
        dates = pd.date_range(start='2024-01-01', periods=300, freq='5min')
        df = pd.DataFrame({
            'datetime': dates,
            'open': np.random.uniform(100, 110, 300),
            'high': np.random.uniform(110, 120, 300),
            'low': np.random.uniform(90, 100, 300),
            'close': np.random.uniform(100, 110, 300),
            'volume': np.random.uniform(1000, 5000, 300)
        })
        
        results = []
        for indicator in indicators:
            try:
                result_df = indicator.calculate(df.copy())
                
                if 'signal' in result_df.columns:
                    last_signal = result_df['signal'].iloc[-1]
                    results.append((indicator.name, last_signal, "✅"))
                else:
                    results.append((indicator.name, "N/A", "❌ No signal"))
                    
            except Exception as e:
                results.append((indicator.name, "ERROR", f"❌ {str(e)[:30]}"))
        
        # Display results
        table = Table(title="Indicator Calculation Results")
        table.add_column("Indicator", style="cyan")
        table.add_column("Signal", style="green")
        table.add_column("Status", style="yellow")
        
        for name, signal, status in results:
            table.add_row(name, str(signal), status)
        
        console.print(table)
        console.print()
        
        success_count = sum(1 for _, _, status in results if "✅" in status)
        console.print(f"✅ {success_count}/{len(indicators)} indicators calculated successfully\n")
        
        return success_count == len(indicators)
        
    except Exception as e:
        console.print(f"❌ Calculation test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    console.clear()
    
    panel = Panel(
        "[bold cyan]🔌 Dynamic Indicator Loader Test Suite[/bold cyan]\n\n"
        "Testing plug-and-play indicator architecture...",
        style="bold green"
    )
    console.print(panel)
    console.print()
    
    results = []
    
    # Run tests
    results.append(("Configuration Validation", test_config_validation()))
    
    success, indicators = test_indicator_loading()
    results.append(("Indicator Loading", success))
    
    results.append(("Indicator Information", test_indicator_info()))
    results.append(("Aggregation Config", test_aggregation_config()))
    results.append(("Indicator Calculation", test_indicator_calculation(indicators)))
    
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
        console.print("[bold green]🎉 All tests passed! Plug-and-play architecture is working![/bold green]\n")
        return 0
    else:
        console.print("[bold red]⚠️  Some tests failed. Please check the configuration.[/bold red]\n")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

