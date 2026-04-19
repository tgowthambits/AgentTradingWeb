"""
Symbols Configuration Panel Module

Creates and manages the symbols configuration panel with symbol list,
lot sizes, and related controls.
"""

from typing import Dict, Any, Optional, Callable
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QLineEdit, QPushButton, QListWidget, QTableWidget, QTableWidgetItem,
    QMessageBox
)


class SymbolsConfigPanel:
    """
    Manager for symbols configuration panel.
    
    This class handles:
    - Symbols list creation and management
    - Lot size configuration
    - Add/remove symbol controls
    
    Attributes:
        parent_widget: Parent widget reference
        config: Configuration dictionary
        prefix: Attribute prefix for distinguishing intraday/backtest
    """
    
    def __init__(self, parent_widget: QWidget = None, config: Dict[str, Any] = None, prefix: str = ""):
        """
        Initialize the SymbolsConfigPanel.
        
        Args:
            parent_widget: Parent widget to store attribute references
            config: Configuration dictionary
            prefix: Prefix for widget attribute names
        """
        self.parent_widget = parent_widget
        self.config = config or {}
        self.prefix = prefix
        
        # Widget references
        self.symbols_list: Optional[QListWidget] = None
        self.symbol_entry: Optional[QLineEdit] = None
        self.lot_size_entry: Optional[QLineEdit] = None
        self.lot_size_value_entry: Optional[QLineEdit] = None
        self.default_lot_entry: Optional[QLineEdit] = None
        self.lot_sizes_tree: Optional[QTableWidget] = None
    
    def create(self, parent: QWidget, layout: QVBoxLayout) -> QGroupBox:
        """
        Create the symbols configuration panel.
        
        Args:
            parent: Parent widget
            layout: Layout to add the panel to
        
        Returns:
            The created QGroupBox
        """
        group = QGroupBox("Symbols")
        group_layout = QVBoxLayout(group)
        
        # Symbols list
        self.symbols_list = QListWidget()
        self.symbols_list.setMaximumHeight(150)
        self._set_parent_attr('symbols_list', self.symbols_list)
        group_layout.addWidget(self.symbols_list)
        
        # Add/Remove controls
        controls_layout = QHBoxLayout()
        
        self.symbol_entry = QLineEdit()
        self.symbol_entry.setPlaceholderText("Enter symbol (e.g., NSE:RELIANCE)")
        self._set_parent_attr('symbol_entry', self.symbol_entry)
        controls_layout.addWidget(self.symbol_entry)
        
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self.add_symbol)
        controls_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self.remove_symbol)
        controls_layout.addWidget(remove_btn)
        
        group_layout.addLayout(controls_layout)
        
        # Lot sizes section
        lot_group = QGroupBox("Lot Sizes")
        lot_layout = QHBoxLayout(lot_group)
        
        lot_layout.addWidget(QLabel("Symbol:"))
        self.lot_size_entry = QLineEdit()
        self.lot_size_entry.setPlaceholderText("Symbol")
        self._set_parent_attr('lot_size_entry', self.lot_size_entry)
        lot_layout.addWidget(self.lot_size_entry)
        
        lot_layout.addWidget(QLabel("Lot Size:"))
        self.lot_size_value_entry = QLineEdit()
        self._set_parent_attr('lot_size_value_entry', self.lot_size_value_entry)
        lot_layout.addWidget(self.lot_size_value_entry)
        
        set_lot_btn = QPushButton("Set")
        set_lot_btn.clicked.connect(self.set_lot_size)
        lot_layout.addWidget(set_lot_btn)
        
        remove_lot_btn = QPushButton("Remove")
        remove_lot_btn.clicked.connect(self.remove_lot_size)
        lot_layout.addWidget(remove_lot_btn)
        
        group_layout.addWidget(lot_group)
        
        # Default lot size
        default_lot_layout = QHBoxLayout()
        default_lot_layout.addWidget(QLabel("Default Lot Size:"))
        self.default_lot_entry = QLineEdit()
        self._set_parent_attr('default_lot_entry', self.default_lot_entry)
        default_lot_layout.addWidget(self.default_lot_entry)
        group_layout.addLayout(default_lot_layout)
        
        # Lot sizes table
        self.lot_sizes_tree = QTableWidget(0, 2)
        self.lot_sizes_tree.setHorizontalHeaderLabels(["Symbol", "Lot Size"])
        self.lot_sizes_tree.horizontalHeader().setStretchLastSection(True)
        self.lot_sizes_tree.setMaximumHeight(100)
        self._set_parent_attr('lot_sizes_tree', self.lot_sizes_tree)
        group_layout.addWidget(self.lot_sizes_tree)
        
        layout.addWidget(group)
        return group
    
    def _set_parent_attr(self, name: str, widget):
        """Set attribute on parent widget with prefix."""
        if self.parent_widget:
            attr_name = f"{self.prefix}{name}" if self.prefix else name
            setattr(self.parent_widget, attr_name, widget)
    
    def _get_parent_attr(self, name: str, default=None):
        """Get attribute from parent widget with prefix."""
        if self.parent_widget:
            attr_name = f"{self.prefix}{name}" if self.prefix else name
            return getattr(self.parent_widget, attr_name, default)
        return default
    
    def add_symbol(self):
        """Add symbol to the list."""
        if not self.symbol_entry or not self.symbols_list:
            return
        
        symbol = self.symbol_entry.text().strip()
        if symbol:
            self.symbols_list.addItem(symbol)
            self.symbol_entry.clear()
    
    def remove_symbol(self):
        """Remove selected symbol from the list."""
        if not self.symbols_list:
            return
        
        current_item = self.symbols_list.currentItem()
        if current_item:
            self.symbols_list.takeItem(self.symbols_list.row(current_item))
    
    def set_lot_size(self):
        """Set lot size for a symbol."""
        if not self.lot_size_entry or not self.lot_size_value_entry or not self.lot_sizes_tree:
            return
        
        symbol = self.lot_size_entry.text().strip()
        lot_size = self.lot_size_value_entry.text().strip()
        
        if symbol and lot_size:
            try:
                lot_size_val = int(lot_size)
                row = self.lot_sizes_tree.rowCount()
                self.lot_sizes_tree.insertRow(row)
                self.lot_sizes_tree.setItem(row, 0, QTableWidgetItem(symbol))
                self.lot_sizes_tree.setItem(row, 1, QTableWidgetItem(str(lot_size_val)))
                
                self.lot_size_entry.clear()
                self.lot_size_value_entry.clear()
            except ValueError:
                if self.parent_widget:
                    QMessageBox.warning(self.parent_widget, "Error", "Lot size must be a number")
    
    def remove_lot_size(self):
        """Remove selected lot size entry."""
        if not self.lot_sizes_tree:
            return
        
        current_row = self.lot_sizes_tree.currentRow()
        if current_row >= 0:
            self.lot_sizes_tree.removeRow(current_row)
    
    def get_symbols(self) -> list:
        """Get list of symbols."""
        if not self.symbols_list:
            return []
        return [self.symbols_list.item(i).text() for i in range(self.symbols_list.count())]
    
    def get_lot_sizes(self) -> Dict[str, int]:
        """Get lot sizes dictionary."""
        if not self.lot_sizes_tree:
            return {}
        
        lot_sizes = {}
        for row in range(self.lot_sizes_tree.rowCount()):
            symbol_item = self.lot_sizes_tree.item(row, 0)
            lot_size_item = self.lot_sizes_tree.item(row, 1)
            if symbol_item and lot_size_item:
                try:
                    lot_sizes[symbol_item.text()] = int(lot_size_item.text())
                except ValueError:
                    pass
        return lot_sizes
    
    def get_default_lot_size(self) -> int:
        """Get default lot size."""
        if not self.default_lot_entry:
            return 50
        try:
            return int(self.default_lot_entry.text())
        except ValueError:
            return 50
    
    def load_from_config(self, config: Dict[str, Any]):
        """Load values from configuration."""
        self.config = config
        
        # Load symbols
        symbols = config.get('trading', {}).get('symbols', [])
        if self.symbols_list:
            self.symbols_list.clear()
            for symbol in symbols:
                self.symbols_list.addItem(symbol)
        
        # Load lot sizes
        lot_sizes = config.get('trading', {}).get('lot_sizes', {})
        if self.lot_sizes_tree:
            self.lot_sizes_tree.setRowCount(0)
            for symbol, lot_size in lot_sizes.items():
                row = self.lot_sizes_tree.rowCount()
                self.lot_sizes_tree.insertRow(row)
                self.lot_sizes_tree.setItem(row, 0, QTableWidgetItem(symbol))
                self.lot_sizes_tree.setItem(row, 1, QTableWidgetItem(str(lot_size)))
        
        # Load default lot size
        default_lot = config.get('lot_sizes', {}).get('default', 50)
        if self.default_lot_entry:
            self.default_lot_entry.setText(str(default_lot))
