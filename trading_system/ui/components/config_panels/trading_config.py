"""
Trading Configuration Panel Module

Creates and manages the trading configuration panel with
auto-trading, refresh intervals, and quantity settings.
"""

from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QLineEdit, QCheckBox, QComboBox
)


class TradingConfigPanel:
    """
    Manager for trading configuration panel.
    
    This class handles:
    - Auto trading toggle
    - Trade direction controls (BUY/SELL)
    - Refresh interval settings
    - Signal aggregation strategy
    - Quantity and position size settings
    
    Attributes:
        parent_widget: Parent widget reference
        config: Configuration dictionary
        prefix: Attribute prefix for distinguishing intraday/backtest
    """
    
    def __init__(self, parent_widget: QWidget = None, config: Dict[str, Any] = None, prefix: str = ""):
        """
        Initialize the TradingConfigPanel.
        
        Args:
            parent_widget: Parent widget to store attribute references
            config: Configuration dictionary
            prefix: Prefix for widget attribute names
        """
        self.parent_widget = parent_widget
        self.config = config or {}
        self.prefix = prefix
        
        # Widget references
        self.auto_trade_check: Optional[QCheckBox] = None
        self.allow_buy_check: Optional[QCheckBox] = None
        self.allow_sell_check: Optional[QCheckBox] = None
        self.paper_trading_check: Optional[QCheckBox] = None
        self.refresh_interval_entry: Optional[QLineEdit] = None
        self.slow_refresh_interval_entry: Optional[QLineEdit] = None
        self.fast_refresh_interval_entry: Optional[QLineEdit] = None
        self.aggregation_strategy_combo: Optional[QComboBox] = None
        self.min_agreement_entry: Optional[QLineEdit] = None
        self.initial_capital_entry: Optional[QLineEdit] = None
        self.default_quantity_entry: Optional[QLineEdit] = None
        self.max_position_size_entry: Optional[QLineEdit] = None
    
    def create(self, parent: QWidget, layout: QVBoxLayout) -> QGroupBox:
        """
        Create the trading configuration panel.
        
        Args:
            parent: Parent widget
            layout: Layout to add the panel to
        
        Returns:
            The created QGroupBox
        """
        group = QGroupBox("Trading Settings")
        group_layout = QVBoxLayout(group)
        
        # Auto trading
        self.auto_trade_check = QCheckBox("Enable Auto Trading")
        self._set_parent_attr('auto_trade_check', self.auto_trade_check)
        group_layout.addWidget(self.auto_trade_check)
        
        # Trade directions
        self.allow_buy_check = QCheckBox("Allow BUY")
        self.allow_buy_check.setChecked(True)
        self._set_parent_attr('allow_buy_check', self.allow_buy_check)
        group_layout.addWidget(self.allow_buy_check)
        
        self.allow_sell_check = QCheckBox("Allow SELL")
        self._set_parent_attr('allow_sell_check', self.allow_sell_check)
        group_layout.addWidget(self.allow_sell_check)
        
        # Paper trading
        self.paper_trading_check = QCheckBox("Paper Trading Mode")
        self._set_parent_attr('paper_trading_check', self.paper_trading_check)
        group_layout.addWidget(self.paper_trading_check)
        
        # Refresh intervals
        if self.prefix == "intraday_":
            # Slow refresh interval
            slow_interval_layout = QHBoxLayout()
            slow_interval_layout.addWidget(QLabel("Default Refresh Interval (s):"))
            self.slow_refresh_interval_entry = QLineEdit()
            self.slow_refresh_interval_entry.setMaximumWidth(100)
            self.slow_refresh_interval_entry.setPlaceholderText("30")
            self.slow_refresh_interval_entry.setToolTip("Refresh interval when no positions are open")
            self._set_parent_attr('slow_refresh_interval_entry', self.slow_refresh_interval_entry)
            slow_interval_layout.addWidget(self.slow_refresh_interval_entry)
            slow_interval_layout.addStretch()
            group_layout.addLayout(slow_interval_layout)
            
            # Fast refresh interval
            fast_interval_layout = QHBoxLayout()
            fast_interval_layout.addWidget(QLabel("Active Refresh Interval (s):"))
            self.fast_refresh_interval_entry = QLineEdit()
            self.fast_refresh_interval_entry.setMaximumWidth(100)
            self.fast_refresh_interval_entry.setPlaceholderText("15")
            self.fast_refresh_interval_entry.setToolTip("Refresh interval when positions are open")
            self._set_parent_attr('fast_refresh_interval_entry', self.fast_refresh_interval_entry)
            fast_interval_layout.addWidget(self.fast_refresh_interval_entry)
            fast_interval_layout.addStretch()
            group_layout.addLayout(fast_interval_layout)
        else:
            # Legacy refresh interval for backtest
            interval_layout = QHBoxLayout()
            interval_layout.addWidget(QLabel("Refresh Interval (s):"))
            self.refresh_interval_entry = QLineEdit()
            self.refresh_interval_entry.setMaximumWidth(100)
            self._set_parent_attr('refresh_interval_entry', self.refresh_interval_entry)
            interval_layout.addWidget(self.refresh_interval_entry)
            interval_layout.addStretch()
            group_layout.addLayout(interval_layout)
        
        # Signal Aggregation Strategy
        agg_strategy_layout = QHBoxLayout()
        agg_strategy_layout.addWidget(QLabel("Aggregation Strategy:"))
        self.aggregation_strategy_combo = QComboBox()
        self.aggregation_strategy_combo.addItems(["weighted", "majority", "unanimous", "conservative", "threshold"])
        self._set_parent_attr('aggregation_strategy_combo', self.aggregation_strategy_combo)
        agg_strategy_layout.addWidget(self.aggregation_strategy_combo)
        agg_strategy_layout.addStretch()
        group_layout.addLayout(agg_strategy_layout)
        
        # Min Agreement
        min_agreement_layout = QHBoxLayout()
        min_agreement_layout.addWidget(QLabel("Min Agreement:"))
        self.min_agreement_entry = QLineEdit()
        self.min_agreement_entry.setMaximumWidth(100)
        self.min_agreement_entry.setPlaceholderText("0.6")
        self._set_parent_attr('min_agreement_entry', self.min_agreement_entry)
        min_agreement_layout.addWidget(self.min_agreement_entry)
        min_agreement_layout.addStretch()
        group_layout.addLayout(min_agreement_layout)
        
        # Initial capital (only for intraday)
        if self.prefix == "intraday_":
            capital_layout = QHBoxLayout()
            capital_layout.addWidget(QLabel("Initial Capital:"))
            self.initial_capital_entry = QLineEdit()
            self.initial_capital_entry.setMaximumWidth(100)
            self._set_parent_attr('initial_capital_entry', self.initial_capital_entry)
            capital_layout.addWidget(self.initial_capital_entry)
            capital_layout.addStretch()
            group_layout.addLayout(capital_layout)
        
        # Max allowed quantity
        qty_layout = QHBoxLayout()
        qty_layout.addWidget(QLabel("Max Allowed Quantity:"))
        self.default_quantity_entry = QLineEdit()
        self.default_quantity_entry.setMaximumWidth(100)
        self._set_parent_attr('default_quantity_entry', self.default_quantity_entry)
        qty_layout.addWidget(self.default_quantity_entry)
        qty_layout.addStretch()
        group_layout.addLayout(qty_layout)
        
        # Max Position Size
        max_pos_size_layout = QHBoxLayout()
        max_pos_size_layout.addWidget(QLabel("Max Position Size:"))
        self.max_position_size_entry = QLineEdit()
        self.max_position_size_entry.setMaximumWidth(100)
        self._set_parent_attr('max_position_size_entry', self.max_position_size_entry)
        max_pos_size_layout.addWidget(self.max_position_size_entry)
        max_pos_size_layout.addStretch()
        group_layout.addLayout(max_pos_size_layout)
        
        # Hint label
        hint_label = QLabel("Quantity is calculated dynamically based on capital and lot size")
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("color: gray; font-size: 9px;")
        group_layout.addWidget(hint_label)
        
        layout.addWidget(group)
        return group
    
    def _set_parent_attr(self, name: str, widget):
        """Set attribute on parent widget with prefix."""
        if self.parent_widget:
            attr_name = f"{self.prefix}{name}" if self.prefix else name
            setattr(self.parent_widget, attr_name, widget)
    
    def load_from_config(self, config: Dict[str, Any]):
        """Load values from configuration."""
        self.config = config
        trading_config = config.get('trading', {})
        signal_agg = config.get('signal_aggregation', {})
        
        if self.auto_trade_check:
            self.auto_trade_check.setChecked(trading_config.get('auto_trade', False))
        
        if self.allow_buy_check:
            self.allow_buy_check.setChecked(trading_config.get('allow_buy', True))
        
        if self.allow_sell_check:
            self.allow_sell_check.setChecked(trading_config.get('allow_sell', False))
        
        if self.paper_trading_check:
            self.paper_trading_check.setChecked(trading_config.get('paper_trading', False))
        
        if self.refresh_interval_entry:
            self.refresh_interval_entry.setText(str(trading_config.get('refresh_interval', 30)))
        
        if self.slow_refresh_interval_entry:
            self.slow_refresh_interval_entry.setText(str(trading_config.get('slow_refresh_interval', 30)))
        
        if self.fast_refresh_interval_entry:
            self.fast_refresh_interval_entry.setText(str(trading_config.get('fast_refresh_interval', 15)))
        
        if self.aggregation_strategy_combo:
            strategy = signal_agg.get('strategy', 'weighted')
            idx = self.aggregation_strategy_combo.findText(strategy)
            if idx >= 0:
                self.aggregation_strategy_combo.setCurrentIndex(idx)
        
        if self.min_agreement_entry:
            self.min_agreement_entry.setText(str(signal_agg.get('min_agreement', 0.6)))
        
        if self.default_quantity_entry:
            self.default_quantity_entry.setText(str(trading_config.get('default_quantity', 25)))
        
        if self.max_position_size_entry:
            self.max_position_size_entry.setText(str(trading_config.get('max_position_size', 100)))
        
        if self.initial_capital_entry:
            backtest_config = config.get('backtest', {})
            self.initial_capital_entry.setText(str(backtest_config.get('initial_capital', 20000)))
    
    def get_values(self) -> Dict[str, Any]:
        """Get current configuration values."""
        values = {}
        
        if self.auto_trade_check:
            values['auto_trade'] = self.auto_trade_check.isChecked()
        
        if self.allow_buy_check:
            values['allow_buy'] = self.allow_buy_check.isChecked()
        
        if self.allow_sell_check:
            values['allow_sell'] = self.allow_sell_check.isChecked()
        
        if self.paper_trading_check:
            values['paper_trading'] = self.paper_trading_check.isChecked()
        
        if self.refresh_interval_entry:
            try:
                values['refresh_interval'] = int(self.refresh_interval_entry.text())
            except ValueError:
                values['refresh_interval'] = 30
        
        if self.aggregation_strategy_combo:
            values['aggregation_strategy'] = self.aggregation_strategy_combo.currentText()
        
        if self.min_agreement_entry:
            try:
                values['min_agreement'] = float(self.min_agreement_entry.text())
            except ValueError:
                values['min_agreement'] = 0.6
        
        if self.default_quantity_entry:
            try:
                values['default_quantity'] = int(self.default_quantity_entry.text())
            except ValueError:
                values['default_quantity'] = 25
        
        if self.max_position_size_entry:
            try:
                values['max_position_size'] = int(self.max_position_size_entry.text())
            except ValueError:
                values['max_position_size'] = 100
        
        return values
