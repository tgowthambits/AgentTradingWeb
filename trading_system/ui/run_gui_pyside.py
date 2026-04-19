"""
Launcher script for PySide6 GUI
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from trading_system.ui.gui_app_pyside import main

if __name__ == "__main__":
    main()
