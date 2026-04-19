"""
Backtest Configuration Panel Module

Creates and manages the backtest-specific configuration panel with
date range, initial capital, and other backtest settings.
"""

from typing import Dict, Any, Optional
from datetime import datetime, date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QLineEdit, QCheckBox, QDateEdit, QTimeEdit
)
from PySide6.QtCore import QDate, QTime


class BacktestConfigPanel:
    """
    Manager for backtest configuration panel.
    
    This class handles:
    - Date range selection (start/end dates)
    - Time range selection (start/end times)
    - Initial capital setting
    - Backtest-specific settings
    
    Attributes:
        parent_widget: Parent widget reference
        config: Configuration dictionary
    """
    
    def __init__(self, parent_widget: QWidget = None, config: Dict[str, Any] = None):
        """
        Initialize the BacktestConfigPanel.
        
        Args:
            parent_widget: Parent widget to store attribute references
            config: Configuration dictionary
        """
        self.parent_widget = parent_widget
        self.config = config or {}
        
        # Widget references
        self.start_date_edit: Optional[QDateEdit] = None
        self.end_date_edit: Optional[QDateEdit] = None
        self.start_time_edit: Optional[QTimeEdit] = None
        self.end_time_edit: Optional[QTimeEdit] = None
        self.initial_capital_entry: Optional[QLineEdit] = None
        self.enable_slippage_check: Optional[QCheckBox] = None
        self.entry_slippage_entry: Optional[QLineEdit] = None
        self.exit_slippage_entry: Optional[QLineEdit] = None
    
    def create(self, parent: QWidget, layout: QVBoxLayout) -> QGroupBox:
        """
        Create the backtest configuration panel.
        
        Args:
            parent: Parent widget
            layout: Layout to add the panel to
        
        Returns:
            The created QGroupBox
        """
        group = QGroupBox("Backtest Settings")
        group_layout = QVBoxLayout(group)
        
        # Date range
        date_group = QGroupBox("Date Range")
        date_layout = QVBoxLayout(date_group)
        
        # Start date
        start_date_layout = QHBoxLayout()
        start_date_layout.addWidget(QLabel("Start Date:"))
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addDays(-30))
        self._set_parent_attr('backtest_start_date', self.start_date_edit)
        start_date_layout.addWidget(self.start_date_edit)
        start_date_layout.addStretch()
        date_layout.addLayout(start_date_layout)
        
        # End date
        end_date_layout = QHBoxLayout()
        end_date_layout.addWidget(QLabel("End Date:"))
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        self._set_parent_attr('backtest_end_date', self.end_date_edit)
        end_date_layout.addWidget(self.end_date_edit)
        end_date_layout.addStretch()
        date_layout.addLayout(end_date_layout)
        
        group_layout.addWidget(date_group)
        
        # Time range
        time_group = QGroupBox("Time Range")
        time_layout = QVBoxLayout(time_group)
        
        # Start time
        start_time_layout = QHBoxLayout()
        start_time_layout.addWidget(QLabel("Start Time:"))
        self.start_time_edit = QTimeEdit()
        self.start_time_edit.setTime(QTime(9, 15))
        self._set_parent_attr('backtest_start_time', self.start_time_edit)
        start_time_layout.addWidget(self.start_time_edit)
        start_time_layout.addStretch()
        time_layout.addLayout(start_time_layout)
        
        # End time
        end_time_layout = QHBoxLayout()
        end_time_layout.addWidget(QLabel("End Time:"))
        self.end_time_edit = QTimeEdit()
        self.end_time_edit.setTime(QTime(15, 30))
        self._set_parent_attr('backtest_end_time', self.end_time_edit)
        end_time_layout.addWidget(self.end_time_edit)
        end_time_layout.addStretch()
        time_layout.addLayout(end_time_layout)
        
        group_layout.addWidget(time_group)
        
        # Initial capital
        capital_layout = QHBoxLayout()
        capital_layout.addWidget(QLabel("Initial Capital:"))
        self.initial_capital_entry = QLineEdit()
        self.initial_capital_entry.setMaximumWidth(100)
        self._set_parent_attr('backtest_initial_capital', self.initial_capital_entry)
        capital_layout.addWidget(self.initial_capital_entry)
        capital_layout.addStretch()
        group_layout.addLayout(capital_layout)
        
        # Slippage settings
        slippage_group = QGroupBox("Slippage")
        slippage_layout = QVBoxLayout(slippage_group)
        
        self.enable_slippage_check = QCheckBox("Enable Slippage Simulation")
        self._set_parent_attr('backtest_enable_slippage', self.enable_slippage_check)
        slippage_layout.addWidget(self.enable_slippage_check)
        
        entry_slippage_layout = QHBoxLayout()
        entry_slippage_layout.addWidget(QLabel("Entry Slippage (%):"))
        self.entry_slippage_entry = QLineEdit()
        self.entry_slippage_entry.setMaximumWidth(100)
        self.entry_slippage_entry.setPlaceholderText("0.1")
        self._set_parent_attr('backtest_entry_slippage', self.entry_slippage_entry)
        entry_slippage_layout.addWidget(self.entry_slippage_entry)
        entry_slippage_layout.addStretch()
        slippage_layout.addLayout(entry_slippage_layout)
        
        exit_slippage_layout = QHBoxLayout()
        exit_slippage_layout.addWidget(QLabel("Exit Slippage (%):"))
        self.exit_slippage_entry = QLineEdit()
        self.exit_slippage_entry.setMaximumWidth(100)
        self.exit_slippage_entry.setPlaceholderText("0.1")
        self._set_parent_attr('backtest_exit_slippage', self.exit_slippage_entry)
        exit_slippage_layout.addWidget(self.exit_slippage_entry)
        exit_slippage_layout.addStretch()
        slippage_layout.addLayout(exit_slippage_layout)
        
        slippage_hint = QLabel("Slippage simulates real-world price differences")
        slippage_hint.setWordWrap(True)
        slippage_hint.setStyleSheet("color: gray; font-size: 9px;")
        slippage_layout.addWidget(slippage_hint)
        
        group_layout.addWidget(slippage_group)
        
        layout.addWidget(group)
        return group
    
    def _set_parent_attr(self, name: str, widget):
        """Set attribute on parent widget."""
        if self.parent_widget:
            setattr(self.parent_widget, name, widget)
    
    def load_from_config(self, config: Dict[str, Any]):
        """Load values from configuration."""
        self.config = config
        backtest_config = config.get('backtest', {})
        slippage_config = backtest_config.get('slippage', {})
        
        # Date range
        if self.start_date_edit:
            start_date_str = backtest_config.get('start_date')
            if start_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                    self.start_date_edit.setDate(QDate(start_date.year, start_date.month, start_date.day))
                except:
                    pass
        
        if self.end_date_edit:
            end_date_str = backtest_config.get('end_date')
            if end_date_str:
                try:
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                    self.end_date_edit.setDate(QDate(end_date.year, end_date.month, end_date.day))
                except:
                    pass
        
        # Time range
        if self.start_time_edit:
            start_time_str = backtest_config.get('start_time', '09:15')
            try:
                parts = start_time_str.split(':')
                self.start_time_edit.setTime(QTime(int(parts[0]), int(parts[1])))
            except:
                pass
        
        if self.end_time_edit:
            end_time_str = backtest_config.get('end_time', '15:30')
            try:
                parts = end_time_str.split(':')
                self.end_time_edit.setTime(QTime(int(parts[0]), int(parts[1])))
            except:
                pass
        
        # Initial capital
        if self.initial_capital_entry:
            self.initial_capital_entry.setText(str(backtest_config.get('initial_capital', 20000)))
        
        # Slippage
        if self.enable_slippage_check:
            self.enable_slippage_check.setChecked(slippage_config.get('enabled', False))
        
        if self.entry_slippage_entry:
            self.entry_slippage_entry.setText(str(slippage_config.get('entry_slippage_pct', 0.1)))
        
        if self.exit_slippage_entry:
            self.exit_slippage_entry.setText(str(slippage_config.get('exit_slippage_pct', 0.1)))
    
    def get_values(self) -> Dict[str, Any]:
        """Get current configuration values."""
        values = {}
        
        if self.start_date_edit:
            qdate = self.start_date_edit.date()
            values['start_date'] = f"{qdate.year():04d}-{qdate.month():02d}-{qdate.day():02d}"
        
        if self.end_date_edit:
            qdate = self.end_date_edit.date()
            values['end_date'] = f"{qdate.year():04d}-{qdate.month():02d}-{qdate.day():02d}"
        
        if self.start_time_edit:
            qtime = self.start_time_edit.time()
            values['start_time'] = f"{qtime.hour():02d}:{qtime.minute():02d}"
        
        if self.end_time_edit:
            qtime = self.end_time_edit.time()
            values['end_time'] = f"{qtime.hour():02d}:{qtime.minute():02d}"
        
        if self.initial_capital_entry:
            try:
                values['initial_capital'] = float(self.initial_capital_entry.text())
            except ValueError:
                values['initial_capital'] = 20000
        
        values['slippage'] = {}
        if self.enable_slippage_check:
            values['slippage']['enabled'] = self.enable_slippage_check.isChecked()
        
        if self.entry_slippage_entry:
            try:
                values['slippage']['entry_slippage_pct'] = float(self.entry_slippage_entry.text())
            except ValueError:
                values['slippage']['entry_slippage_pct'] = 0.1
        
        if self.exit_slippage_entry:
            try:
                values['slippage']['exit_slippage_pct'] = float(self.exit_slippage_entry.text())
            except ValueError:
                values['slippage']['exit_slippage_pct'] = 0.1
        
        return values
