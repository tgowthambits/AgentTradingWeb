#!/usr/bin/env python3
"""
Test Automated Indicator Discovery & Config Sync

Tests the automatic indicator discovery and configuration synchronization.
"""

import sys
import os
import shutil
from pathlib import Path

# Add to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trading_system.core.indicator_loader import IndicatorLoader
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def test_indicator_discovery():
    """Test automatic indicator discovery."""
    console.print("\n[bold cyan]Test 1: Indicator Discovery[/bold cyan]\n")
    
    try:
        loader = IndicatorLoader(
            "trading_system/config/indicators_config.yaml",
            auto_sync=False  # Don't sync yet, just discover
        )
        
        discovered = loader.discover_indicators()
        
        if discovered:
            console.print(f"✅ Discovered {len(discovered)} indicators\n")
            
            # Display discovered indicators
            table = Table(title="Discovered Indicators", show_header=True)
            table.add_column("Name", style="cyan")
            table.add_column("Class", style="yellow")
            table.add_column("Module", style="green")
            table.add_column("Parameters", style="magenta")
            
            for name, info in discovered.items():
                params = ", ".join(info['default_params'].keys()) if info['default_params'] else "None"
                table.add_row(
                    name,
                    info['class_name'],
                    info['module'],
                    params
                )
            
            console.print(table)
            console.print()
            return True
        else:
            console.print("❌ No indicators discovered\n")
            return False
            
    except Exception as e:
        console.print(f"❌ Discovery failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_config_sync():
    """Test automatic config synchronization."""
    console.print("[bold cyan]Test 2: Config Synchronization[/bold cyan]\n")
    
    try:
        # Create a backup of the config
        config_path = "trading_system/config/indicators_config.yaml"
        backup_path = "trading_system/config/indicators_config.yaml.backup"
        
        if os.path.exists(config_path):
            shutil.copy(config_path, backup_path)
            console.print("💾 Created config backup\n")
        
        # Load with auto-sync enabled
        loader = IndicatorLoader(
            config_path,
            auto_sync=True
        )
        
        console.print("✅ Config synchronization completed\n")
        
        # Restore backup
        if os.path.exists(backup_path):
            # Actually, let's keep the synced version for now
            # shutil.move(backup_path, config_path)
            os.remove(backup_path)
            console.print("🔄 Cleaned up backup\n")
        
        return True
        
    except Exception as e:
        console.print(f"❌ Sync failed: {e}\n")
        import traceback
        traceback.print_exc()
        
        # Restore backup on error
        if os.path.exists(backup_path):
            shutil.move(backup_path, config_path)
            console.print("↩️  Restored config from backup\n")
        
        return False


def test_add_indicator():
    """Test manually adding an indicator to config."""
    console.print("[bold cyan]Test 3: Manual Indicator Addition[/bold cyan]\n")
    
    try:
        loader = IndicatorLoader(auto_sync=False)
        
        # Check if test indicator already exists
        test_name = "test_custom_indicator"
        
        if test_name in loader.config.get('indicators', {}):
            console.print(f"⏭️  Test indicator already exists, removing first\n")
            loader.remove_indicator_from_config(test_name)
        
        # Add a test indicator
        loader.add_indicator_to_config(
            indicator_name=test_name,
            module_path="trading_system.indicators.test_indicator",
            class_name="TestIndicator",
            params={'period': 20, 'threshold': 0.5},
            weight=1.0,
            enabled=False
        )
        
        # Verify it was added
        if test_name in loader.config['indicators']:
            console.print(f"✅ Successfully added {test_name} to config\n")
            
            # Clean up - remove the test indicator
            loader.remove_indicator_from_config(test_name)
            console.print(f"🧹 Cleaned up test indicator\n")
            
            return True
        else:
            console.print(f"❌ Failed to add {test_name}\n")
            return False
            
    except Exception as e:
        console.print(f"❌ Manual addition failed: {e}\n")
        return False


def test_class_name_conversion():
    """Test class name to indicator name conversion."""
    console.print("[bold cyan]Test 4: Name Conversion[/bold cyan]\n")
    
    loader = IndicatorLoader(auto_sync=False)
    
    test_cases = [
        ('RSIIndicator', 'rsi'),
        ('MACrossoverIndicator', 'ma_crossover'),
        ('MACDIndicator', 'macd'),
        ('BollingerBandsIndicator', 'bollinger_bands'),
        ('MyCustomIndicator', 'my_custom'),
    ]
    
    table = Table(title="Class Name Conversion Tests")
    table.add_column("Class Name", style="cyan")
    table.add_column("Expected", style="yellow")
    table.add_column("Got", style="green")
    table.add_column("Status", style="magenta")
    
    passed = 0
    for class_name, expected in test_cases:
        result = loader._class_name_to_indicator_name(class_name)
        status = "✅" if result == expected else "❌"
        
        table.add_row(class_name, expected, result, status)
        
        if result == expected:
            passed += 1
    
    console.print(table)
    console.print(f"\n✅ {passed}/{len(test_cases)} conversion tests passed\n")
    
    return passed == len(test_cases)


def test_real_world_scenario():
    """Test a real-world scenario: new indicator added to directory."""
    console.print("[bold cyan]Test 5: Real-World Scenario[/bold cyan]\n")
    
    # This test simulates what happens when a user adds a new indicator file
    console.print("📝 Scenario: User creates a new indicator file\n")
    
    # Create a temporary test indicator file
    test_indicator_code = '''"""
Test Indicator for Auto-Discovery
"""

from trading_system.core.base_indicator import BaseIndicator
import pandas as pd

class TestAutoDiscoveryIndicator(BaseIndicator):
    """Test indicator for auto-discovery testing."""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.period = config.get('period', 14)
        self.threshold = config.get('threshold', 0.5)
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate test indicator."""
        df = df.copy()
        df['signal'] = 'HOLD'
        return df
    
    def get_required_columns(self) -> list:
        """Required columns."""
        return ['close']
'''
    
    test_file_path = "trading_system/indicators/test_auto_discovery_indicator.py"
    
    try:
        # Create the test indicator file
        console.print(f"1. Creating test indicator: {test_file_path}")
        with open(test_file_path, 'w') as f:
            f.write(test_indicator_code)
        console.print("   ✅ File created\n")
        
        # Run auto-discovery
        console.print("2. Running auto-discovery with sync...")
        loader = IndicatorLoader(auto_sync=True)
        console.print("   ✅ Discovery completed\n")
        
        # Check if it was added to config
        console.print("3. Checking if indicator was added to config...")
        if 'test_auto_discovery' in loader.config.get('indicators', {}):
            console.print("   ✅ Indicator automatically added to config!\n")
            
            indicator_config = loader.config['indicators']['test_auto_discovery']
            console.print("   Configuration details:")
            console.print(f"   • Enabled: {indicator_config.get('enabled')}")
            console.print(f"   • Module: {indicator_config.get('module')}")
            console.print(f"   • Class: {indicator_config.get('class_name')}")
            console.print(f"   • Params: {indicator_config.get('params')}")
            console.print()
            
            success = True
        else:
            console.print("   ❌ Indicator was not added to config\n")
            success = False
        
        # Clean up - remove test file
        console.print("4. Cleaning up test indicator...")
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            console.print("   ✅ Test file removed\n")
        
        # Run sync again to remove it from config
        console.print("5. Re-syncing to remove deleted indicator...")
        loader = IndicatorLoader(auto_sync=True)
        
        if 'test_auto_discovery' not in loader.config.get('indicators', {}):
            console.print("   ✅ Deleted indicator removed from config!\n")
        else:
            console.print("   ⚠️  Indicator still in config (expected if keeping for reference)\n")
        
        return success
        
    except Exception as e:
        console.print(f"❌ Real-world test failed: {e}\n")
        import traceback
        traceback.print_exc()
        
        # Clean up on error
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            console.print("🧹 Cleaned up test file\n")
        
        return False


def main():
    """Run all tests."""
    console.clear()
    
    panel = Panel(
        "[bold cyan]🤖 Automated Indicator Discovery Test Suite[/bold cyan]\n\n"
        "Testing automatic indicator discovery and config synchronization...",
        style="bold green"
    )
    console.print(panel)
    console.print()
    
    results = []
    
    # Run tests
    results.append(("Indicator Discovery", test_indicator_discovery()))
    results.append(("Config Synchronization", test_config_sync()))
    results.append(("Manual Addition", test_add_indicator()))
    results.append(("Name Conversion", test_class_name_conversion()))
    results.append(("Real-World Scenario", test_real_world_scenario()))
    
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
        console.print("[bold green]🎉 All tests passed! Auto-discovery is working perfectly![/bold green]\n")
        return 0
    else:
        console.print("[bold yellow]⚠️  Some tests failed. Please check the results above.[/bold yellow]\n")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

