"""
Exit Strategy Configuration Panel Module

Creates and manages the exit strategy configuration panel with
stop loss, profit targets, and profit protection settings.
"""

from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QLineEdit, QCheckBox, QComboBox
)


class ExitStrategyConfigPanel:
    """
    Manager for exit strategy configuration panel.
    
    This class handles:
    - Stop loss configuration (volatility/fixed)
    - Breakeven settings
    - Profit target levels (3 targets)
    - Profit reversal protection
    - Profit drop protection
    
    Attributes:
        parent_widget: Parent widget reference
        config: Configuration dictionary
        prefix: Attribute prefix for distinguishing intraday/backtest
    """
    
    def __init__(self, parent_widget: QWidget = None, config: Dict[str, Any] = None, prefix: str = ""):
        """
        Initialize the ExitStrategyConfigPanel.
        
        Args:
            parent_widget: Parent widget to store attribute references
            config: Configuration dictionary
            prefix: Prefix for widget attribute names
        """
        self.parent_widget = parent_widget
        self.config = config or {}
        self.prefix = prefix
        
        # Stop loss widgets
        self.sl_method_combo: Optional[QComboBox] = None
        self.max_loss_per_trade_entry: Optional[QLineEdit] = None
        self.atr_multiplier_entry: Optional[QLineEdit] = None
        self.breakeven_enabled_check: Optional[QCheckBox] = None
        self.breakeven_trigger_entry: Optional[QLineEdit] = None
        
        # Profit target widgets
        self.profit_targets_enabled_check: Optional[QCheckBox] = None
        self.pt1_ratio_entry: Optional[QLineEdit] = None
        self.pt1_exit_entry: Optional[QLineEdit] = None
        self.pt2_ratio_entry: Optional[QLineEdit] = None
        self.pt2_exit_entry: Optional[QLineEdit] = None
        self.pt3_ratio_entry: Optional[QLineEdit] = None
        self.pt3_exit_entry: Optional[QLineEdit] = None
        
        # Profit target reversal widgets
        self.profit_target_reversal_enabled_check: Optional[QCheckBox] = None
        self.profit_target_reversal_atr_multiplier_entry: Optional[QLineEdit] = None
        self.profit_target_reversal_percent_entry: Optional[QLineEdit] = None
        
        # Profit reversal protection widgets
        self.profit_reversal_protection_enabled_check: Optional[QCheckBox] = None
        self.profit_reversal_min_profit_entry: Optional[QLineEdit] = None
        self.profit_reversal_threshold_entry: Optional[QLineEdit] = None
        self.profit_reversal_atr_multiplier_entry: Optional[QLineEdit] = None
        
        # Profit drop protection widgets
        self.profit_drop_protection_enabled_check: Optional[QCheckBox] = None
        self.profit_drop_percentage_entry: Optional[QLineEdit] = None
        
        # Below average profit exit widgets
        self.below_avg_profit_exit_enabled_check: Optional[QCheckBox] = None
        self.below_avg_profit_min_profit_entry: Optional[QLineEdit] = None
    
    def create(self, parent: QWidget, layout: QVBoxLayout) -> QGroupBox:
        """
        Create the exit strategy configuration panel.
        
        Args:
            parent: Parent widget
            layout: Layout to add the panel to
        
        Returns:
            The created QGroupBox
        """
        group = QGroupBox("Exit Strategy")
        group_layout = QVBoxLayout(group)
        
        # Stop Loss Configuration
        sl_group = self._create_stop_loss_group()
        group_layout.addWidget(sl_group)
        
        # Profit Targets Configuration
        pt_group = self._create_profit_targets_group()
        group_layout.addWidget(pt_group)
        
        # Profit Reversal Protection
        reversal_group = self._create_profit_reversal_group()
        group_layout.addWidget(reversal_group)
        
        # Profit Drop Protection
        drop_group = self._create_profit_drop_group()
        group_layout.addWidget(drop_group)
        
        # Below Average Profit Exit
        below_avg_group = self._create_below_avg_profit_group()
        group_layout.addWidget(below_avg_group)
        
        layout.addWidget(group)
        return group
    
    def _create_stop_loss_group(self) -> QGroupBox:
        """Create stop loss configuration group."""
        sl_group = QGroupBox("Stop Loss")
        sl_group_layout = QVBoxLayout(sl_group)
        
        # Method
        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("Method:"))
        self.sl_method_combo = QComboBox()
        self.sl_method_combo.addItems(["volatility", "fixed_amount"])
        self._set_parent_attr('sl_method_combo', self.sl_method_combo)
        method_layout.addWidget(self.sl_method_combo)
        method_layout.addStretch()
        sl_group_layout.addLayout(method_layout)
        
        # Max Loss Per Trade
        max_loss_layout = QHBoxLayout()
        max_loss_layout.addWidget(QLabel("Max Loss/Trade:"))
        self.max_loss_per_trade_entry = QLineEdit()
        self.max_loss_per_trade_entry.setMaximumWidth(100)
        self._set_parent_attr('max_loss_per_trade_entry', self.max_loss_per_trade_entry)
        max_loss_layout.addWidget(self.max_loss_per_trade_entry)
        max_loss_layout.addStretch()
        sl_group_layout.addLayout(max_loss_layout)
        
        # ATR Multiplier
        atr_mult_layout = QHBoxLayout()
        atr_mult_layout.addWidget(QLabel("ATR Multiplier:"))
        self.atr_multiplier_entry = QLineEdit()
        self.atr_multiplier_entry.setMaximumWidth(100)
        self._set_parent_attr('atr_multiplier_entry', self.atr_multiplier_entry)
        atr_mult_layout.addWidget(self.atr_multiplier_entry)
        atr_mult_layout.addStretch()
        sl_group_layout.addLayout(atr_mult_layout)
        
        # Breakeven
        self.breakeven_enabled_check = QCheckBox("Enable Breakeven")
        self._set_parent_attr('breakeven_enabled_check', self.breakeven_enabled_check)
        sl_group_layout.addWidget(self.breakeven_enabled_check)
        
        be_trigger_layout = QHBoxLayout()
        be_trigger_layout.addWidget(QLabel("Breakeven Trigger Ratio:"))
        self.breakeven_trigger_entry = QLineEdit()
        self.breakeven_trigger_entry.setMaximumWidth(100)
        self._set_parent_attr('breakeven_trigger_entry', self.breakeven_trigger_entry)
        be_trigger_layout.addWidget(self.breakeven_trigger_entry)
        be_trigger_layout.addStretch()
        sl_group_layout.addLayout(be_trigger_layout)
        
        return sl_group
    
    def _create_profit_targets_group(self) -> QGroupBox:
        """Create profit targets configuration group."""
        pt_group = QGroupBox("Profit Targets")
        pt_group_layout = QVBoxLayout(pt_group)
        
        self.profit_targets_enabled_check = QCheckBox("Enable Profit Targets")
        self._set_parent_attr('profit_targets_enabled_check', self.profit_targets_enabled_check)
        pt_group_layout.addWidget(self.profit_targets_enabled_check)
        
        # Target 1
        pt1_group = QGroupBox("Target 1")
        pt1_layout = QVBoxLayout(pt1_group)
        
        pt1_ratio_layout = QHBoxLayout()
        pt1_ratio_layout.addWidget(QLabel("Risk:Reward Ratio:"))
        self.pt1_ratio_entry = QLineEdit()
        self.pt1_ratio_entry.setMaximumWidth(100)
        self._set_parent_attr('pt1_ratio_entry', self.pt1_ratio_entry)
        pt1_ratio_layout.addWidget(self.pt1_ratio_entry)
        pt1_ratio_layout.addStretch()
        pt1_layout.addLayout(pt1_ratio_layout)
        
        pt1_exit_layout = QHBoxLayout()
        pt1_exit_layout.addWidget(QLabel("Exit %:"))
        self.pt1_exit_entry = QLineEdit()
        self.pt1_exit_entry.setMaximumWidth(100)
        self._set_parent_attr('pt1_exit_entry', self.pt1_exit_entry)
        pt1_exit_layout.addWidget(self.pt1_exit_entry)
        pt1_exit_layout.addStretch()
        pt1_layout.addLayout(pt1_exit_layout)
        
        pt_group_layout.addWidget(pt1_group)
        
        # Target 2
        pt2_group = QGroupBox("Target 2")
        pt2_layout = QVBoxLayout(pt2_group)
        
        pt2_ratio_layout = QHBoxLayout()
        pt2_ratio_layout.addWidget(QLabel("Risk:Reward Ratio:"))
        self.pt2_ratio_entry = QLineEdit()
        self.pt2_ratio_entry.setMaximumWidth(100)
        self._set_parent_attr('pt2_ratio_entry', self.pt2_ratio_entry)
        pt2_ratio_layout.addWidget(self.pt2_ratio_entry)
        pt2_ratio_layout.addStretch()
        pt2_layout.addLayout(pt2_ratio_layout)
        
        pt2_exit_layout = QHBoxLayout()
        pt2_exit_layout.addWidget(QLabel("Exit %:"))
        self.pt2_exit_entry = QLineEdit()
        self.pt2_exit_entry.setMaximumWidth(100)
        self._set_parent_attr('pt2_exit_entry', self.pt2_exit_entry)
        pt2_exit_layout.addWidget(self.pt2_exit_entry)
        pt2_exit_layout.addStretch()
        pt2_layout.addLayout(pt2_exit_layout)
        
        pt_group_layout.addWidget(pt2_group)
        
        # Target 3
        pt3_group = QGroupBox("Target 3")
        pt3_layout = QVBoxLayout(pt3_group)
        
        pt3_ratio_layout = QHBoxLayout()
        pt3_ratio_layout.addWidget(QLabel("Risk:Reward Ratio:"))
        self.pt3_ratio_entry = QLineEdit()
        self.pt3_ratio_entry.setMaximumWidth(100)
        self._set_parent_attr('pt3_ratio_entry', self.pt3_ratio_entry)
        pt3_ratio_layout.addWidget(self.pt3_ratio_entry)
        pt3_ratio_layout.addStretch()
        pt3_layout.addLayout(pt3_ratio_layout)
        
        pt3_exit_layout = QHBoxLayout()
        pt3_exit_layout.addWidget(QLabel("Exit %:"))
        self.pt3_exit_entry = QLineEdit()
        self.pt3_exit_entry.setMaximumWidth(100)
        self._set_parent_attr('pt3_exit_entry', self.pt3_exit_entry)
        pt3_exit_layout.addWidget(self.pt3_exit_entry)
        pt3_exit_layout.addStretch()
        pt3_layout.addLayout(pt3_exit_layout)
        
        pt_group_layout.addWidget(pt3_group)
        
        # Profit Target Reversal
        reversal_group = QGroupBox("Profit Target Reversal")
        reversal_layout = QVBoxLayout(reversal_group)
        
        self.profit_target_reversal_enabled_check = QCheckBox("Enable Reversal Detection")
        self.profit_target_reversal_enabled_check.setChecked(True)
        self._set_parent_attr('profit_target_reversal_enabled_check', self.profit_target_reversal_enabled_check)
        reversal_layout.addWidget(self.profit_target_reversal_enabled_check)
        
        reversal_atr_layout = QHBoxLayout()
        reversal_atr_layout.addWidget(QLabel("ATR Multiplier:"))
        self.profit_target_reversal_atr_multiplier_entry = QLineEdit()
        self.profit_target_reversal_atr_multiplier_entry.setMaximumWidth(100)
        self.profit_target_reversal_atr_multiplier_entry.setPlaceholderText("0.5")
        self._set_parent_attr('profit_target_reversal_atr_multiplier_entry', self.profit_target_reversal_atr_multiplier_entry)
        reversal_atr_layout.addWidget(self.profit_target_reversal_atr_multiplier_entry)
        reversal_atr_layout.addStretch()
        reversal_layout.addLayout(reversal_atr_layout)
        
        reversal_pct_layout = QHBoxLayout()
        reversal_pct_layout.addWidget(QLabel("Percent Threshold (%):"))
        self.profit_target_reversal_percent_entry = QLineEdit()
        self.profit_target_reversal_percent_entry.setMaximumWidth(100)
        self.profit_target_reversal_percent_entry.setPlaceholderText("1.0")
        self._set_parent_attr('profit_target_reversal_percent_entry', self.profit_target_reversal_percent_entry)
        reversal_pct_layout.addWidget(self.profit_target_reversal_percent_entry)
        reversal_pct_layout.addStretch()
        reversal_layout.addLayout(reversal_pct_layout)
        
        reversal_hint = QLabel("Exits fully when price reverses from hit profit target")
        reversal_hint.setWordWrap(True)
        reversal_hint.setStyleSheet("color: gray; font-size: 9px;")
        reversal_layout.addWidget(reversal_hint)
        
        pt_group_layout.addWidget(reversal_group)
        
        return pt_group
    
    def _create_profit_reversal_group(self) -> QGroupBox:
        """Create profit reversal protection group."""
        group = QGroupBox("Profit Reversal Protection")
        layout = QVBoxLayout(group)
        
        self.profit_reversal_protection_enabled_check = QCheckBox("Enable Profit Reversal Protection")
        self.profit_reversal_protection_enabled_check.setChecked(True)
        self._set_parent_attr('profit_reversal_protection_enabled_check', self.profit_reversal_protection_enabled_check)
        layout.addWidget(self.profit_reversal_protection_enabled_check)
        
        min_profit_layout = QHBoxLayout()
        min_profit_layout.addWidget(QLabel("Min Profit to Activate:"))
        self.profit_reversal_min_profit_entry = QLineEdit()
        self.profit_reversal_min_profit_entry.setMaximumWidth(100)
        self.profit_reversal_min_profit_entry.setPlaceholderText("100")
        self._set_parent_attr('profit_reversal_min_profit_entry', self.profit_reversal_min_profit_entry)
        min_profit_layout.addWidget(self.profit_reversal_min_profit_entry)
        min_profit_layout.addStretch()
        layout.addLayout(min_profit_layout)
        
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Reversal Threshold (%):"))
        self.profit_reversal_threshold_entry = QLineEdit()
        self.profit_reversal_threshold_entry.setMaximumWidth(100)
        self.profit_reversal_threshold_entry.setPlaceholderText("50")
        self._set_parent_attr('profit_reversal_threshold_entry', self.profit_reversal_threshold_entry)
        threshold_layout.addWidget(self.profit_reversal_threshold_entry)
        threshold_layout.addStretch()
        layout.addLayout(threshold_layout)
        
        atr_layout = QHBoxLayout()
        atr_layout.addWidget(QLabel("ATR Multiplier (optional):"))
        self.profit_reversal_atr_multiplier_entry = QLineEdit()
        self.profit_reversal_atr_multiplier_entry.setMaximumWidth(100)
        self.profit_reversal_atr_multiplier_entry.setPlaceholderText("1.0")
        self._set_parent_attr('profit_reversal_atr_multiplier_entry', self.profit_reversal_atr_multiplier_entry)
        atr_layout.addWidget(self.profit_reversal_atr_multiplier_entry)
        atr_layout.addStretch()
        layout.addLayout(atr_layout)
        
        hint = QLabel("Exits when profitable trade reverses to protect gains")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray; font-size: 9px;")
        layout.addWidget(hint)
        
        return group
    
    def _create_profit_drop_group(self) -> QGroupBox:
        """Create profit drop protection group."""
        group = QGroupBox("Profit Drop Protection")
        layout = QVBoxLayout(group)
        
        self.profit_drop_protection_enabled_check = QCheckBox("Enable Profit Drop Protection")
        self.profit_drop_protection_enabled_check.setChecked(False)
        self._set_parent_attr('profit_drop_protection_enabled_check', self.profit_drop_protection_enabled_check)
        layout.addWidget(self.profit_drop_protection_enabled_check)
        
        drop_pct_layout = QHBoxLayout()
        drop_pct_layout.addWidget(QLabel("Drop Percentage (%):"))
        self.profit_drop_percentage_entry = QLineEdit()
        self.profit_drop_percentage_entry.setMaximumWidth(100)
        self.profit_drop_percentage_entry.setPlaceholderText("3.0")
        self._set_parent_attr('profit_drop_percentage_entry', self.profit_drop_percentage_entry)
        drop_pct_layout.addWidget(self.profit_drop_percentage_entry)
        drop_pct_layout.addStretch()
        layout.addLayout(drop_pct_layout)
        
        hint = QLabel("Exits if profit drops by X% from max profit reached")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray; font-size: 9px;")
        layout.addWidget(hint)
        
        return group
    
    def _create_below_avg_profit_group(self) -> QGroupBox:
        """Create below average profit exit group."""
        group = QGroupBox("Below Average Profit Exit")
        layout = QVBoxLayout(group)
        
        self.below_avg_profit_exit_enabled_check = QCheckBox("Enable Below Avg Profit Exit")
        self.below_avg_profit_exit_enabled_check.setChecked(False)
        self._set_parent_attr('below_avg_profit_exit_enabled_check', self.below_avg_profit_exit_enabled_check)
        layout.addWidget(self.below_avg_profit_exit_enabled_check)
        
        min_profit_layout = QHBoxLayout()
        min_profit_layout.addWidget(QLabel("Min Profit to Activate (₹):"))
        self.below_avg_profit_min_profit_entry = QLineEdit()
        self.below_avg_profit_min_profit_entry.setMaximumWidth(100)
        self.below_avg_profit_min_profit_entry.setPlaceholderText("50.0")
        self._set_parent_attr('below_avg_profit_min_profit_entry', self.below_avg_profit_min_profit_entry)
        min_profit_layout.addWidget(self.below_avg_profit_min_profit_entry)
        min_profit_layout.addStretch()
        layout.addLayout(min_profit_layout)
        
        hint = QLabel("Exits if unrealized profit drops below the average profit recorded during the trade")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray; font-size: 9px;")
        layout.addWidget(hint)
        
        return group
    
    def _set_parent_attr(self, name: str, widget):
        """Set attribute on parent widget with prefix."""
        if self.parent_widget:
            attr_name = f"{self.prefix}{name}" if self.prefix else name
            setattr(self.parent_widget, attr_name, widget)
    
    def load_from_config(self, config: Dict[str, Any]):
        """Load values from configuration."""
        self.config = config
        exit_config = config.get('exit_strategy', {})
        sl_config = exit_config.get('stop_loss', {})
        pt_config = exit_config.get('profit_targets', {})
        reversal_config = exit_config.get('profit_reversal_protection', {})
        drop_config = exit_config.get('profit_drop_protection', {})
        
        # Stop loss
        if self.sl_method_combo:
            method = sl_config.get('method', 'volatility')
            idx = self.sl_method_combo.findText(method)
            if idx >= 0:
                self.sl_method_combo.setCurrentIndex(idx)
        
        if self.max_loss_per_trade_entry:
            self.max_loss_per_trade_entry.setText(str(sl_config.get('max_loss_per_trade', 500)))
        
        if self.atr_multiplier_entry:
            self.atr_multiplier_entry.setText(str(sl_config.get('atr_multiplier', 2.0)))
        
        if self.breakeven_enabled_check:
            be_config = sl_config.get('breakeven', {})
            self.breakeven_enabled_check.setChecked(be_config.get('enabled', False))
        
        if self.breakeven_trigger_entry:
            be_config = sl_config.get('breakeven', {})
            self.breakeven_trigger_entry.setText(str(be_config.get('trigger_ratio', 1.0)))
        
        # Profit targets
        if self.profit_targets_enabled_check:
            self.profit_targets_enabled_check.setChecked(pt_config.get('enabled', True))
        
        targets = pt_config.get('targets', [])
        if len(targets) > 0:
            if self.pt1_ratio_entry:
                self.pt1_ratio_entry.setText(str(targets[0].get('risk_reward_ratio', 1.0)))
            if self.pt1_exit_entry:
                self.pt1_exit_entry.setText(str(targets[0].get('exit_percentage', 40)))
        
        if len(targets) > 1:
            if self.pt2_ratio_entry:
                self.pt2_ratio_entry.setText(str(targets[1].get('risk_reward_ratio', 1.5)))
            if self.pt2_exit_entry:
                self.pt2_exit_entry.setText(str(targets[1].get('exit_percentage', 30)))
        
        if len(targets) > 2:
            if self.pt3_ratio_entry:
                self.pt3_ratio_entry.setText(str(targets[2].get('risk_reward_ratio', 2.0)))
            if self.pt3_exit_entry:
                self.pt3_exit_entry.setText(str(targets[2].get('exit_percentage', 30)))
        
        # Profit reversal protection
        if self.profit_reversal_protection_enabled_check:
            self.profit_reversal_protection_enabled_check.setChecked(reversal_config.get('enabled', True))
        
        if self.profit_reversal_min_profit_entry:
            self.profit_reversal_min_profit_entry.setText(str(reversal_config.get('min_profit_to_activate', 100)))
        
        if self.profit_reversal_threshold_entry:
            self.profit_reversal_threshold_entry.setText(str(reversal_config.get('reversal_threshold_percent', 50)))
        
        # Profit drop protection
        if self.profit_drop_protection_enabled_check:
            self.profit_drop_protection_enabled_check.setChecked(drop_config.get('enabled', False))
        
        if self.profit_drop_percentage_entry:
            self.profit_drop_percentage_entry.setText(str(drop_config.get('drop_percentage', 3.0)))
        
        # Below average profit exit (from risk_management section)
        below_avg_config = config.get('risk_management', {}).get('below_avg_profit_exit', {})
        if self.below_avg_profit_exit_enabled_check:
            self.below_avg_profit_exit_enabled_check.setChecked(below_avg_config.get('enabled', False))
        
        if self.below_avg_profit_min_profit_entry:
            self.below_avg_profit_min_profit_entry.setText(str(below_avg_config.get('min_profit', 50.0)))
