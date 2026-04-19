"""
Dashboard Panel Module

Contains the KPI tile creation and dashboard layout components.
"""

from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
    QWidget, QGroupBox
)
from PySide6.QtCore import Qt


class DashboardPanel:
    """
    Manager for dashboard panels with KPI tiles.
    
    This class handles:
    - Creation of KPI tile grids
    - Styling and layout of dashboard components
    - KPI tile updates
    
    Attributes:
        config: Configuration dictionary
        kpi_tiles: Dictionary of KPI tile widgets
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the DashboardPanel.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.kpi_tiles: Dict[str, QFrame] = {}
    
    def create_kpi_grid(self, parent: QWidget, kpi_definitions: list) -> Dict[str, QFrame]:
        """
        Create a grid of KPI tiles.
        
        Args:
            parent: Parent widget
            kpi_definitions: List of tuples (key, title, initial_value)
        
        Returns:
            Dictionary mapping KPI keys to tile widgets
        """
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)
        
        tiles = {}
        cols = 4  # 4 tiles per row
        
        for idx, (key, title, initial_value) in enumerate(kpi_definitions):
            row = idx // cols
            col = idx % cols
            
            tile = self.create_kpi_tile(title, initial_value)
            grid_layout.addWidget(tile, row, col)
            tiles[key] = tile
        
        parent.setLayout(grid_layout)
        self.kpi_tiles = tiles
        return tiles
    
    def create_kpi_tile(self, title: str, value: str = "0") -> QFrame:
        """
        Create a single KPI tile.
        
        Args:
            title: Title text for the tile
            value: Initial value to display
        
        Returns:
            QFrame containing the KPI tile
        """
        tile = QFrame()
        tile.setObjectName("kpiTile")
        tile.setStyleSheet("""
            QFrame#kpiTile {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 8px;
                padding: 10px;
            }
            QFrame#kpiTile:hover {
                border: 1px solid #505050;
                background-color: #353535;
            }
        """)
        
        layout = QVBoxLayout(tile)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Title label
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            color: #888888;
            font-size: 11px;
            font-weight: normal;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Value label
        value_label = QLabel(value)
        value_label.setStyleSheet("""
            color: #ffffff;
            font-size: 18px;
            font-weight: bold;
        """)
        value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_label)
        
        return tile
    
    def update_kpi_tile(self, tile: QFrame, value: str):
        """
        Update a KPI tile value.
        
        Args:
            tile: The tile widget to update
            value: New value to display
        """
        if tile is None:
            return
        
        layout = tile.layout()
        if layout and layout.count() >= 2:
            value_label = layout.itemAt(1).widget()
            if isinstance(value_label, QLabel):
                value_label.setText(value)
                
                # Color code based on value
                if value.startswith('₹'):
                    try:
                        amount = float(value.replace('₹', '').replace(',', ''))
                        if amount > 0:
                            value_label.setStyleSheet("color: #22c55e; font-size: 18px; font-weight: bold;")
                        elif amount < 0:
                            value_label.setStyleSheet("color: #ef4444; font-size: 18px; font-weight: bold;")
                        else:
                            value_label.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: bold;")
                    except:
                        pass
    
    def create_intraday_kpi_definitions(self) -> list:
        """Get KPI definitions for intraday dashboard."""
        return [
            ('total_pnl', 'Total PnL', '₹0.00'),
            ('win_rate', 'Win Rate', '0.00%'),
            ('total_trades', 'Total Trades', '0'),
            ('open_positions', 'Open Positions', '0'),
            ('realized_pnl', 'Realized PnL', '₹0.00'),
            ('avg_win', 'Avg Win', '₹0.00'),
            ('avg_loss', 'Avg Loss', '₹0.00'),
            ('profit_factor', 'Profit Factor', '0.00'),
        ]
    
    def create_backtest_kpi_definitions(self) -> list:
        """Get KPI definitions for backtest dashboard."""
        return [
            ('total_pnl', 'Total PnL', '₹0.00'),
            ('win_rate', 'Win Rate', '0.00%'),
            ('total_trades', 'Total Trades', '0'),
            ('sharpe_ratio', 'Sharpe Ratio', '0.00'),
            ('max_drawdown', 'Max Drawdown', '0.00%'),
            ('profit_factor', 'Profit Factor', '0.00'),
            ('expectancy', 'Expectancy', '₹0.00'),
            ('return_pct', 'Return %', '0.00%'),
        ]
    
    def get_kpi_tiles(self) -> Dict[str, QFrame]:
        """Get the dictionary of KPI tiles."""
        return self.kpi_tiles
