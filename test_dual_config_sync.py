#!/usr/bin/env python3
"""
Test Dual Config Synchronization

Tests that both indicators_config.yaml and trading_config.yaml
are automatically synced with available indicators.
"""

import sys
import os
import yaml
import shutil

# Add to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trading_system.core.indicator_loader import IndicatorLoader
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def backup_configs():
    """Create backups of config files."""
    configs = [
        "trading_system/config/indicators_config.yaml",
        "trading_system/config/trading_config.yaml"
    ]
    
    for config in configs:
        if os.path.exists(config):
            shutil.copy(config, f"{config}.backup")
            console.print(f"💾 Backed up: {config}")


def restore_configs():
    """Restore config files from backups."""
    configs = [
        "trading_system/config/indicators_config.yaml",
        "trading_system/config/trading_config.yaml"
    ]
    
    for config in configs:
        backup = f"{config}.backup"
        if os.path.exists(backup):
            shutil.move(backup, config)
            console.print(f"↩️  Restored: {config}")


def read_config(path):
    """Read a YAML config file."""
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def test_dual_sync():
    """Test that both configs are synced."""
    console.print("\n[bold cyan]Test: Dual Config Synchronization[/bold cyan]\n")
    
    try:
        # Backup configs first
        backup_configs()
        console.print()
        
        # Run auto-sync
        console.print("[bold]Running auto-sync...[/bold]\n")
        loader = IndicatorLoader(
            config_path="trading_system/config/indicators_config.yaml",
            trading_config_path="trading_system/config/trading_config.yaml",
            auto_sync=True
        )
        
        # Read both configs
        indicators_config = read_config("trading_system/config/indicators_config.yaml")
        trading_config = read_config("trading_system/config/trading_config.yaml")
        
        # Get indicator lists
        indicators_list = set(indicators_config.get('indicators', {}).keys())
        trading_list = set(trading_config.get('indicators', {}).keys())
        
        # Compare
        console.print("\n[bold]Comparison Results:[/bold]\n")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Config File", style="cyan")
        table.add_column("Indicators Count", style="white")
        table.add_column("Indicators List", style="yellow")
        
        table.add_row(
            "indicators_config.yaml",
            str(len(indicators_list)),
            ", ".join(sorted(indicators_list))
        )
        
        table.add_row(
            "trading_config.yaml",
            str(len(trading_list)),
            ", ".join(sorted(trading_list))
        )
        
        console.print(table)
        console.print()
        
        # Check if they match
        if indicators_list == trading_list:
            console.print("✅ [bold green]Both configs are in sync![/bold green]\n")
            
            # Show details of a sample indicator in both configs
            sample_indicator = list(indicators_list)[0] if indicators_list else None
            
            if sample_indicator:
                console.print(f"[bold]Sample Indicator: {sample_indicator}[/bold]\n")
                
                ind_conf = indicators_config['indicators'][sample_indicator]
                trad_conf = trading_config['indicators'][sample_indicator]
                
                detail_table = Table(show_header=True)
                detail_table.add_column("Property", style="cyan")
                detail_table.add_column("indicators_config.yaml", style="green")
                detail_table.add_column("trading_config.yaml", style="yellow")
                
                detail_table.add_row("enabled", str(ind_conf.get('enabled')), str(trad_conf.get('enabled')))
                detail_table.add_row("weight", str(ind_conf.get('weight')), str(trad_conf.get('weight')))
                detail_table.add_row("module", str(ind_conf.get('module', 'N/A')), "N/A (not in trading config)")
                detail_table.add_row("class_name", str(ind_conf.get('class_name', 'N/A')), "N/A (not in trading config)")
                
                console.print(detail_table)
                console.print()
            
            return True
        else:
            console.print("❌ [bold red]Configs are NOT in sync![/bold red]\n")
            
            only_in_indicators = indicators_list - trading_list
            only_in_trading = trading_list - indicators_list
            
            if only_in_indicators:
                console.print(f"Only in indicators_config: {only_in_indicators}")
            if only_in_trading:
                console.print(f"Only in trading_config: {only_in_trading}")
            
            console.print()
            return False
            
    except Exception as e:
        console.print(f"❌ Test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Restore configs
        console.print("\n[bold]Restoring original configs...[/bold]\n")
        restore_configs()


def main():
    """Run the test."""
    console.clear()
    
    panel = Panel(
        "[bold cyan]🔄 Dual Config Synchronization Test[/bold cyan]\n\n"
        "Testing that both indicators_config.yaml and trading_config.yaml\n"
        "are automatically synced with available indicators...",
        style="bold green"
    )
    console.print(panel)
    console.print()
    
    # Run test
    success = test_dual_sync()
    
    # Summary
    console.print("\n" + "="*60)
    console.print("[bold cyan]Test Result[/bold cyan]")
    console.print("="*60 + "\n")
    
    if success:
        console.print("✅ [bold green]PASS[/bold green] - Both configs synced successfully\n")
        console.print("[bold yellow]What this means:[/bold yellow]")
        console.print("• indicators_config.yaml - Detailed indicator configurations")
        console.print("• trading_config.yaml - Trading-specific settings")
        console.print("• Both stay in sync automatically with available indicators\n")
        return 0
    else:
        console.print("❌ [bold red]FAIL[/bold red] - Configs not in sync\n")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

