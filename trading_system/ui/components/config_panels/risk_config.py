"""
Risk Configuration Panel Module

Creates and manages the risk management configuration panel with
risk limits, paper trading mode, and loss recovery settings.
"""

from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QLineEdit, QCheckBox
)


class RiskConfigPanel:
    """
    Manager for risk configuration panel.
    
    This class handles:
    - Risk per trade settings
    - Capital percentage per trade
    - Position and loss limits
    - Paper trading mode configuration
    - Loss recovery settings
    
    Attributes:
        parent_widget: Parent widget reference
        config: Configuration dictionary
        prefix: Attribute prefix for distinguishing intraday/backtest
    """
    
    def __init__(self, parent_widget: QWidget = None, config: Dict[str, Any] = None, prefix: str = ""):
        """
        Initialize the RiskConfigPanel.
        
        Args:
            parent_widget: Parent widget to store attribute references
            config: Configuration dictionary
            prefix: Prefix for widget attribute names
        """
        self.parent_widget = parent_widget
        self.config = config or {}
        self.prefix = prefix
        
        # Widget references
        self.risk_per_trade_entry: Optional[QLineEdit] = None
        self.capital_percentage_per_trade_entry: Optional[QLineEdit] = None
        self.max_positions_entry: Optional[QLineEdit] = None
        self.stop_loss_entry: Optional[QLineEdit] = None
        self.daily_loss_limit_entry: Optional[QLineEdit] = None
        self.max_loss_amount_entry: Optional[QLineEdit] = None
        self.max_trades_per_day_entry: Optional[QLineEdit] = None
        self.paper_mode_enabled_check: Optional[QCheckBox] = None
        self.consecutive_losses_trigger_entry: Optional[QLineEdit] = None
        self.exit_on_paper_profit_check: Optional[QCheckBox] = None
        self.loss_recovery_enabled_check: Optional[QCheckBox] = None
        self.loss_recovery_max_multiplier_entry: Optional[QLineEdit] = None
        self.loss_recovery_priority_check: Optional[QCheckBox] = None
        self.partial_exits_enabled_check: Optional[QCheckBox] = None
    
    def create(self, parent: QWidget, layout: QVBoxLayout) -> QGroupBox:
        """
        Create the risk configuration panel.
        
        Args:
            parent: Parent widget
            layout: Layout to add the panel to
        
        Returns:
            The created QGroupBox
        """
        group = QGroupBox("Risk Management")
        group_layout = QVBoxLayout(group)
        
        # Risk per trade
        risk_layout = QHBoxLayout()
        risk_layout.addWidget(QLabel("Risk per Trade (%):"))
        self.risk_per_trade_entry = QLineEdit()
        self.risk_per_trade_entry.setMaximumWidth(100)
        self._set_parent_attr('risk_per_trade_entry', self.risk_per_trade_entry)
        risk_layout.addWidget(self.risk_per_trade_entry)
        risk_layout.addStretch()
        group_layout.addLayout(risk_layout)
        
        # Capital percentage per trade
        capital_pct_layout = QHBoxLayout()
        capital_pct_layout.addWidget(QLabel("Capital % Per Trade (%):"))
        self.capital_percentage_per_trade_entry = QLineEdit()
        self.capital_percentage_per_trade_entry.setMaximumWidth(100)
        placeholder = "20" if self.prefix != "backtest_" else "50"
        self.capital_percentage_per_trade_entry.setPlaceholderText(placeholder)
        self._set_parent_attr('capital_percentage_per_trade_entry', self.capital_percentage_per_trade_entry)
        capital_pct_layout.addWidget(self.capital_percentage_per_trade_entry)
        capital_pct_layout.addStretch()
        group_layout.addLayout(capital_pct_layout)
        
        hint = QLabel("Percentage of available capital used per trade")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray; font-size: 9px;")
        group_layout.addWidget(hint)
        
        # Position limits
        pos_limit_layout = QHBoxLayout()
        pos_limit_layout.addWidget(QLabel("Max Positions:"))
        self.max_positions_entry = QLineEdit()
        self.max_positions_entry.setMaximumWidth(100)
        self._set_parent_attr('max_positions_entry', self.max_positions_entry)
        pos_limit_layout.addWidget(self.max_positions_entry)
        pos_limit_layout.addStretch()
        group_layout.addLayout(pos_limit_layout)
        
        # Stop loss
        sl_layout = QHBoxLayout()
        sl_layout.addWidget(QLabel("Stop Loss (%):"))
        self.stop_loss_entry = QLineEdit()
        self.stop_loss_entry.setMaximumWidth(100)
        self._set_parent_attr('stop_loss_entry', self.stop_loss_entry)
        sl_layout.addWidget(self.stop_loss_entry)
        sl_layout.addStretch()
        group_layout.addLayout(sl_layout)
        
        # Daily loss limit
        daily_limit_layout = QHBoxLayout()
        daily_limit_layout.addWidget(QLabel("Daily Loss Limit:"))
        self.daily_loss_limit_entry = QLineEdit()
        self.daily_loss_limit_entry.setMaximumWidth(100)
        self._set_parent_attr('daily_loss_limit_entry', self.daily_loss_limit_entry)
        daily_limit_layout.addWidget(self.daily_loss_limit_entry)
        daily_limit_layout.addStretch()
        group_layout.addLayout(daily_limit_layout)
        
        # Daily Limits Section
        daily_limits_group = QGroupBox("Daily Limits")
        daily_limits_layout = QVBoxLayout(daily_limits_group)
        
        max_loss_layout = QHBoxLayout()
        max_loss_layout.addWidget(QLabel("Max Loss Amount:"))
        self.max_loss_amount_entry = QLineEdit()
        self.max_loss_amount_entry.setMaximumWidth(100)
        self._set_parent_attr('max_loss_amount_entry', self.max_loss_amount_entry)
        max_loss_layout.addWidget(self.max_loss_amount_entry)
        max_loss_layout.addStretch()
        daily_limits_layout.addLayout(max_loss_layout)
        
        max_trades_layout = QHBoxLayout()
        max_trades_layout.addWidget(QLabel("Max Trades Per Day:"))
        self.max_trades_per_day_entry = QLineEdit()
        self.max_trades_per_day_entry.setMaximumWidth(100)
        self._set_parent_attr('max_trades_per_day_entry', self.max_trades_per_day_entry)
        max_trades_layout.addWidget(self.max_trades_per_day_entry)
        max_trades_layout.addStretch()
        daily_limits_layout.addLayout(max_trades_layout)
        
        group_layout.addWidget(daily_limits_group)
        
        # Paper Trading Mode Section
        paper_mode_group = QGroupBox("Paper Trading Mode")
        paper_mode_layout = QVBoxLayout(paper_mode_group)
        
        self.paper_mode_enabled_check = QCheckBox("Enable Paper Trading Mode")
        self._set_parent_attr('paper_mode_enabled_check', self.paper_mode_enabled_check)
        paper_mode_layout.addWidget(self.paper_mode_enabled_check)
        
        consecutive_losses_layout = QHBoxLayout()
        consecutive_losses_layout.addWidget(QLabel("Consecutive Losses Trigger:"))
        self.consecutive_losses_trigger_entry = QLineEdit()
        self.consecutive_losses_trigger_entry.setMaximumWidth(100)
        self._set_parent_attr('consecutive_losses_trigger_entry', self.consecutive_losses_trigger_entry)
        consecutive_losses_layout.addWidget(self.consecutive_losses_trigger_entry)
        consecutive_losses_layout.addStretch()
        paper_mode_layout.addLayout(consecutive_losses_layout)
        
        self.exit_on_paper_profit_check = QCheckBox("Exit on Paper Profit")
        self._set_parent_attr('exit_on_paper_profit_check', self.exit_on_paper_profit_check)
        paper_mode_layout.addWidget(self.exit_on_paper_profit_check)
        
        group_layout.addWidget(paper_mode_group)
        
        # Loss Recovery Section
        loss_recovery_group = QGroupBox("Loss Recovery")
        loss_recovery_layout = QVBoxLayout(loss_recovery_group)
        
        self.loss_recovery_enabled_check = QCheckBox("Enable Loss Recovery")
        self._set_parent_attr('loss_recovery_enabled_check', self.loss_recovery_enabled_check)
        loss_recovery_layout.addWidget(self.loss_recovery_enabled_check)
        
        max_multiplier_layout = QHBoxLayout()
        max_multiplier_layout.addWidget(QLabel("Max Multiplier:"))
        self.loss_recovery_max_multiplier_entry = QLineEdit()
        self.loss_recovery_max_multiplier_entry.setMaximumWidth(100)
        self._set_parent_attr('loss_recovery_max_multiplier_entry', self.loss_recovery_max_multiplier_entry)
        max_multiplier_layout.addWidget(self.loss_recovery_max_multiplier_entry)
        max_multiplier_layout.addStretch()
        loss_recovery_layout.addLayout(max_multiplier_layout)
        
        self.loss_recovery_priority_check = QCheckBox("Recovery Priority")
        self._set_parent_attr('loss_recovery_priority_check', self.loss_recovery_priority_check)
        loss_recovery_layout.addWidget(self.loss_recovery_priority_check)
        
        group_layout.addWidget(loss_recovery_group)
        
        # Partial Exits Section
        partial_exits_group = QGroupBox("Partial Exits")
        partial_exits_layout = QVBoxLayout(partial_exits_group)
        
        self.partial_exits_enabled_check = QCheckBox("Enable Partial Exits (loss recovery, profit targets)")
        self._set_parent_attr('partial_exits_enabled_check', self.partial_exits_enabled_check)
        partial_exits_layout.addWidget(self.partial_exits_enabled_check)
        
        group_layout.addWidget(partial_exits_group)
        
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
        risk_config = config.get('risk_management', {})
        paper_mode_config = risk_config.get('paper_trading_mode', {})
        loss_recovery_config = risk_config.get('loss_recovery', {})
        partial_exits_config = risk_config.get('partial_exits', {})
        daily_limits = risk_config.get('daily_limits', {})
        
        if self.risk_per_trade_entry:
            self.risk_per_trade_entry.setText(str(risk_config.get('risk_per_trade', 2.0)))
        
        if self.capital_percentage_per_trade_entry:
            key = 'capital_percentage_per_trade_backtest' if self.prefix == 'backtest_' else 'capital_percentage_per_trade_intraday'
            default = 50 if self.prefix == 'backtest_' else 20
            self.capital_percentage_per_trade_entry.setText(str(risk_config.get(key, default)))
        
        if self.max_positions_entry:
            self.max_positions_entry.setText(str(risk_config.get('max_positions', 5)))
        
        if self.stop_loss_entry:
            self.stop_loss_entry.setText(str(risk_config.get('stop_loss_percentage', 5.0)))
        
        if self.daily_loss_limit_entry:
            self.daily_loss_limit_entry.setText(str(daily_limits.get('max_loss_amount', 5000)))
        
        if self.max_loss_amount_entry:
            self.max_loss_amount_entry.setText(str(daily_limits.get('max_loss_amount', 5000)))
        
        if self.max_trades_per_day_entry:
            self.max_trades_per_day_entry.setText(str(daily_limits.get('max_trades_per_day', 20)))
        
        if self.paper_mode_enabled_check:
            self.paper_mode_enabled_check.setChecked(paper_mode_config.get('enabled', False))
        
        if self.consecutive_losses_trigger_entry:
            self.consecutive_losses_trigger_entry.setText(str(paper_mode_config.get('consecutive_losses_trigger', 3)))
        
        if self.exit_on_paper_profit_check:
            self.exit_on_paper_profit_check.setChecked(paper_mode_config.get('exit_on_paper_profit', True))
        
        if self.loss_recovery_enabled_check:
            self.loss_recovery_enabled_check.setChecked(loss_recovery_config.get('enabled', False))
        
        if self.loss_recovery_max_multiplier_entry:
            self.loss_recovery_max_multiplier_entry.setText(str(loss_recovery_config.get('max_multiplier', 3.0)))
        
        if self.loss_recovery_priority_check:
            self.loss_recovery_priority_check.setChecked(loss_recovery_config.get('recovery_priority', False))
        
        if self.partial_exits_enabled_check:
            self.partial_exits_enabled_check.setChecked(partial_exits_config.get('enabled', True))
    
    def get_values(self) -> Dict[str, Any]:
        """Get current configuration values."""
        values = {
            'risk_management': {},
            'paper_trading_mode': {},
            'loss_recovery': {},
            'partial_exits': {},
            'daily_limits': {}
        }
        
        if self.risk_per_trade_entry:
            try:
                values['risk_management']['risk_per_trade'] = float(self.risk_per_trade_entry.text())
            except ValueError:
                values['risk_management']['risk_per_trade'] = 2.0
        
        if self.capital_percentage_per_trade_entry:
            try:
                key = 'capital_percentage_per_trade_backtest' if self.prefix == 'backtest_' else 'capital_percentage_per_trade_intraday'
                values['risk_management'][key] = float(self.capital_percentage_per_trade_entry.text())
            except ValueError:
                pass
        
        if self.max_positions_entry:
            try:
                values['risk_management']['max_positions'] = int(self.max_positions_entry.text())
            except ValueError:
                values['risk_management']['max_positions'] = 5
        
        if self.paper_mode_enabled_check:
            values['paper_trading_mode']['enabled'] = self.paper_mode_enabled_check.isChecked()
        
        if self.consecutive_losses_trigger_entry:
            try:
                values['paper_trading_mode']['consecutive_losses_trigger'] = int(self.consecutive_losses_trigger_entry.text())
            except ValueError:
                values['paper_trading_mode']['consecutive_losses_trigger'] = 3
        
        if self.loss_recovery_enabled_check:
            values['loss_recovery']['enabled'] = self.loss_recovery_enabled_check.isChecked()
        
        if self.loss_recovery_max_multiplier_entry:
            try:
                values['loss_recovery']['max_multiplier'] = float(self.loss_recovery_max_multiplier_entry.text())
            except ValueError:
                values['loss_recovery']['max_multiplier'] = 3.0
        
        if self.partial_exits_enabled_check:
            values['partial_exits']['enabled'] = self.partial_exits_enabled_check.isChecked()
        
        return values
