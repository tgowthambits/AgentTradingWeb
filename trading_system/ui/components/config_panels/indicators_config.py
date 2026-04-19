"""
Indicators Configuration Panel Module

Creates and manages the indicators configuration panel with
enable/disable toggles and weight settings for each indicator.
"""

from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QLineEdit, QCheckBox, QComboBox, QScrollArea, QFrame
)


class IndicatorsConfigPanel:
    """
    Manager for indicators configuration panel.
    
    This class handles:
    - Dynamic indicator control creation
    - Enable/disable toggles for each indicator
    - Weight configuration for signal aggregation
    - Indicator-specific parameters (e.g., super_regression)
    
    Attributes:
        parent_widget: Parent widget reference
        config: Configuration dictionary
        prefix: Attribute prefix for distinguishing intraday/backtest
        indicator_controls: Dictionary of indicator control widgets
    """
    
    def __init__(self, parent_widget: QWidget = None, config: Dict[str, Any] = None, prefix: str = ""):
        """
        Initialize the IndicatorsConfigPanel.
        
        Args:
            parent_widget: Parent widget to store attribute references
            config: Configuration dictionary
            prefix: Prefix for widget attribute names
        """
        self.parent_widget = parent_widget
        self.config = config or {}
        self.prefix = prefix
        self.indicator_controls: Dict[str, Dict] = {}
    
    def create(self, parent: QWidget, layout: QVBoxLayout) -> QGroupBox:
        """
        Create the indicators configuration panel.
        
        Args:
            parent: Parent widget
            layout: Layout to add the panel to
        
        Returns:
            The created QGroupBox
        """
        group = QGroupBox("Indicators")
        group_layout = QVBoxLayout(group)
        
        # Scrollable area for indicators
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(200)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(5, 5, 5, 5)
        
        # Store indicator controls
        self.indicator_controls = {}
        self._set_parent_attr('indicator_controls', self.indicator_controls)
        
        # Load indicators from config and create controls
        indicators_config = self.config.get('indicators', {})
        for ind_name, ind_config in indicators_config.items():
            self._create_indicator_control(scroll_content, scroll_layout, ind_name, ind_config)
        
        scroll_area.setWidget(scroll_content)
        group_layout.addWidget(scroll_area)
        
        layout.addWidget(group)
        return group
    
    def _create_indicator_control(self, parent: QWidget, layout: QVBoxLayout, 
                                   name: str, config: Dict[str, Any]):
        """Create control for a single indicator."""
        frame = QFrame()
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(5, 2, 5, 2)
        
        # First row: Enable checkbox and Weight
        row1_layout = QHBoxLayout()
        
        # Enable checkbox
        enabled_check = QCheckBox(name.replace('_', ' ').title())
        enabled_check.setChecked(config.get('enabled', False))
        self._set_parent_attr(f'indicator_{name}_enabled', enabled_check)
        row1_layout.addWidget(enabled_check)
        
        # Weight
        row1_layout.addWidget(QLabel("Weight:"))
        weight_entry = QLineEdit()
        weight_entry.setMaximumWidth(60)
        weight_entry.setText(str(config.get('weight', 1.0)))
        self._set_parent_attr(f'indicator_{name}_weight', weight_entry)
        row1_layout.addWidget(weight_entry)
        
        row1_layout.addStretch()
        frame_layout.addLayout(row1_layout)
        
        # Store controls
        controls_dict = {
            'enabled': enabled_check,
            'weight': weight_entry
        }
        
        # Indicator-specific parameters (for super_regression)
        if name == 'super_regression':
            params_row = QHBoxLayout()
            
            params_row.addWidget(QLabel("Length:"))
            len_entry = QLineEdit()
            len_entry.setMaximumWidth(60)
            len_entry.setText(str(config.get('len', 20)))
            self._set_parent_attr(f'indicator_{name}_len', len_entry)
            controls_dict['len'] = len_entry
            params_row.addWidget(len_entry)
            
            params_row.addWidget(QLabel("Multiplier:"))
            mult_entry = QLineEdit()
            mult_entry.setMaximumWidth(60)
            mult_entry.setText(str(config.get('mult', 2.0)))
            self._set_parent_attr(f'indicator_{name}_mult', mult_entry)
            controls_dict['mult'] = mult_entry
            params_row.addWidget(mult_entry)
            
            params_row.addWidget(QLabel("Source:"))
            source_combo = QComboBox()
            source_combo.addItems(['close', 'open', 'high', 'low'])
            source_val = config.get('source', 'close')
            idx = source_combo.findText(source_val)
            if idx >= 0:
                source_combo.setCurrentIndex(idx)
            self._set_parent_attr(f'indicator_{name}_source', source_combo)
            controls_dict['source'] = source_combo
            params_row.addWidget(source_combo)
            
            params_row.addStretch()
            frame_layout.addLayout(params_row)
        
        self.indicator_controls[name] = controls_dict
        layout.addWidget(frame)
    
    def _set_parent_attr(self, name: str, widget):
        """Set attribute on parent widget with prefix."""
        if self.parent_widget:
            attr_name = f"{self.prefix}{name}" if self.prefix else name
            setattr(self.parent_widget, attr_name, widget)
    
    def get_enabled_indicators(self) -> list:
        """Get list of enabled indicator names."""
        enabled = []
        for name, controls in self.indicator_controls.items():
            if controls.get('enabled') and controls['enabled'].isChecked():
                enabled.append(name)
        return enabled
    
    def get_indicator_config(self, name: str) -> Dict[str, Any]:
        """Get configuration for a specific indicator."""
        controls = self.indicator_controls.get(name, {})
        config = {}
        
        if 'enabled' in controls:
            config['enabled'] = controls['enabled'].isChecked()
        
        if 'weight' in controls:
            try:
                config['weight'] = float(controls['weight'].text())
            except ValueError:
                config['weight'] = 1.0
        
        # Indicator-specific parameters
        if 'len' in controls:
            try:
                config['len'] = int(controls['len'].text())
            except ValueError:
                config['len'] = 20
        
        if 'mult' in controls:
            try:
                config['mult'] = float(controls['mult'].text())
            except ValueError:
                config['mult'] = 2.0
        
        if 'source' in controls:
            config['source'] = controls['source'].currentText()
        
        return config
    
    def get_all_indicators_config(self) -> Dict[str, Dict]:
        """Get configuration for all indicators."""
        all_config = {}
        for name in self.indicator_controls:
            all_config[name] = self.get_indicator_config(name)
        return all_config
    
    def load_from_config(self, config: Dict[str, Any]):
        """Load values from configuration."""
        self.config = config
        indicators_config = config.get('indicators', {})
        
        for name, ind_config in indicators_config.items():
            controls = self.indicator_controls.get(name, {})
            
            if 'enabled' in controls:
                controls['enabled'].setChecked(ind_config.get('enabled', False))
            
            if 'weight' in controls:
                controls['weight'].setText(str(ind_config.get('weight', 1.0)))
            
            if 'len' in controls:
                controls['len'].setText(str(ind_config.get('len', 20)))
            
            if 'mult' in controls:
                controls['mult'].setText(str(ind_config.get('mult', 2.0)))
            
            if 'source' in controls:
                source_val = ind_config.get('source', 'close')
                idx = controls['source'].findText(source_val)
                if idx >= 0:
                    controls['source'].setCurrentIndex(idx)
