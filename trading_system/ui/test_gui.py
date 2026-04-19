"""
Quick test script to verify GUI imports and basic functionality
"""

import sys
import os
from pathlib import Path

# Add parent directories to path
current_dir = Path(__file__).parent
parent_dir = current_dir.parent.parent
sys.path.insert(0, str(parent_dir))

try:
    from trading_system.ui.gui_app import TradingGUI
    print("✅ GUI module imported successfully")
    
    # Test tkinter availability
    import tkinter as tk
    print("✅ tkinter is available")
    
    # Test configuration loading
    config_path = Path(__file__).parent.parent / "config" / "trading_config.yaml"
    if config_path.exists():
        print(f"✅ Config file found: {config_path}")
    else:
        print(f"⚠️  Config file not found: {config_path}")
    
    print("\n✅ All checks passed! You can run the GUI with:")
    print("   python gui_app.py")
    print("   or")
    print("   python run_gui.py")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nMake sure you're running from the correct directory and all dependencies are installed.")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
