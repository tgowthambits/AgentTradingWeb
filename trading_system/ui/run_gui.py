"""
Launcher script for Trading System GUI
Run this to start the GUI application
"""

import sys
import os
from pathlib import Path

# Add parent directories to path
current_dir = Path(__file__).parent
parent_dir = current_dir.parent.parent
sys.path.insert(0, str(parent_dir))

from trading_system.ui.gui_app import main

if __name__ == "__main__":
    main()
