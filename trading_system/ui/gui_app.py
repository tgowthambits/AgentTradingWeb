"""
Trading System GUI Application - PySide6 Version
Python-based UI with tabs for Intraday and Backtesting
All configurations can be done from the UI and update in real-time

This module uses modular sub-components for better organization:
- ui/threads/: BotThread for background trading operations
- ui/components/tables/: Table managers (LTP, Positions, Trades, Summary)
- ui/components/dashboard/: Dashboard panels and charts
- ui/components/config_panels/: Configuration panel creators
- ui/services/: ConfigManager, MetricsCalculator
- ui/dialogs/: Popup dialogs for charts and results
- ui/utils/: Utility functions and helpers
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import yaml
import pandas as pd
import numpy as np
import tempfile
import webbrowser

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QLineEdit, QPushButton, QCheckBox, QRadioButton, QSpinBox, QDoubleSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea, QGroupBox,
    QMessageBox, QProgressBar, QListWidget, QListWidgetItem, QComboBox,
    QDateEdit, QTimeEdit, QTextEdit, QFrame, QSplitter, QStyledItemDelegate, QStyle,
    QDialog, QGridLayout, QFileDialog, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QDate, QTime, QUrl, QAbstractItemModel, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QFont, QTextDocument, QPainter
from PySide6.QtWebEngineWidgets import QWebEngineView

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from trading_system.run_live_bot import LiveTradingBot
from trading_system.core.indicator_loader import IndicatorLoader

# Import modular components
from trading_system.ui.utils.formatters import format_time as _format_time
from trading_system.ui.utils.helpers import get_enabled_indicators as _get_enabled_indicators
from trading_system.ui.utils.helpers import map_config_name_to_indicator_name as _map_config_name
from trading_system.ui.services.metrics_calculator import MetricsCalculator
from trading_system.ui.services.config_manager import ConfigManager

# Import table managers
from trading_system.ui.components.tables import (
    LTPTableManager,
    PositionsTableManager,
    TradesTableManager,
    SummaryTableManager
)

# Import dashboard components
from trading_system.ui.components.dashboard import (
    DashboardPanel,
    ChartManager,
    DashboardUpdater
)

# Import config panels
from trading_system.ui.components.config_panels import (
    SymbolsConfigPanel,
    TradingConfigPanel,
    IndicatorsConfigPanel,
    RiskConfigPanel,
    ExitStrategyConfigPanel,
    BacktestConfigPanel
)

# Import dialogs
from trading_system.ui.dialogs import ChartDialogs

# Import BotThread from threads module
from trading_system.ui.threads import BotThread


# HTMLDelegate class for table cell HTML rendering
class HTMLDelegate(QStyledItemDelegate):
    """Custom delegate to render HTML in table cells"""
    def paint(self, painter, option, index):
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        
        text = index.data(Qt.DisplayRole)
        if text:
            doc = QTextDocument()
            doc.setHtml(str(text))
            doc.setTextWidth(option.rect.width())
            
            painter.save()
            painter.translate(option.rect.topLeft())
            doc.drawContents(painter)
            painter.restore()


class TradingGUI(QMainWindow):
    """Main GUI application for trading system"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trading System - Intraday & Backtesting")
        self.setGeometry(100, 100, 1400, 900)
        
        # Configuration paths
        self.config_path = Path(__file__).parent.parent / "config" / "trading_config.yaml"
        self.indicators_config_path = Path(__file__).parent.parent / "config" / "indicators_config.yaml"
        agent_trading_root = Path(__file__).parent.parent.parent
        self.data_config_path = agent_trading_root / "Data" / "config" / "config.yaml"
        
        # Load initial configuration
        self.config = self.load_config()
        
        # Trading bot thread
        self.bot_thread: Optional[BotThread] = None
        
        # Store last results for position PnL calculation
        self.last_results = []
        
        # Store previous positions to detect changes
        self.previous_positions = {}
        
        # Track closed orders count for event detection
        self._last_closed_count = 0
        
        # Store previous prices for LTP change calculation
        self.previous_prices = {}
        
        # Store LTP history with timestamps for each symbol
        self.ltp_history = {}
        
        # Store historical metrics for trend visualization
        self.metrics_history = {
            'total_pnl': [], 'equity': [], 'returns_pct': [], 'win_rate': [],
            'sharpe_ratio': [], 'sortino_ratio': [], 'calmar_ratio': [],
            'max_drawdown': [], 'profit_factor': [], 'expectancy': [],
            'avg_win': [], 'avg_loss': [], 'iteration': []
        }
        
        # Map table item IDs to metric keys for trend visualization
        self.metric_key_map = {}
        
        # Map table items to symbols for click handler
        self.ltp_symbol_map = {}
        
        # Store enabled indicators list for LTP table
        self.enabled_indicators_list = []
        
        # Dashboard update throttling
        self.dashboard_update_pending = False
        self.dashboard_update_timer = QTimer()
        self.dashboard_update_timer.setSingleShot(True)
        self.dashboard_update_timer.timeout.connect(self._process_dashboard_updates)
        self.pending_dashboard_summary = None
        
        # Store backtest candlestick data for chart viewing
        self.backtest_candle_data = {}  # symbol -> DataFrame mapping
        self.backtest_live_candle_data = {}  # Progressive data during backtest
        self.live_chart_dialog = None  # Reference to live chart dialog

        # Store intraday candlestick data for live chart viewing
        self.intraday_live_candle_data = {}
        self.intraday_live_chart_dialog = None
        
        # Initialize modular components
        self._init_modular_components()
        
        # Create UI
        self.create_ui()
        
        # Initialize tables
        self.initialize_tables()
        
        # Load initial config into UI
        self.load_config_to_ui()
    
    def _init_modular_components(self):
        """Initialize modular component managers."""
        # Intraday table managers
        self._ltp_table_manager = LTPTableManager(config=self.config)
        self._positions_table_manager = PositionsTableManager(config=self.config)
        self._trades_table_manager = TradesTableManager(config=self.config)
        self._intraday_summary_manager = SummaryTableManager(config=self.config)
        
        # Backtest table managers
        self._backtest_ltp_manager = LTPTableManager(config=self.config)
        self._backtest_positions_manager = PositionsTableManager(config=self.config)
        self._backtest_trades_manager = TradesTableManager(config=self.config)
        self._backtest_summary_manager = SummaryTableManager(config=self.config)
        
        # Dashboard components
        self._dashboard_panel = DashboardPanel(config=self.config)
        self._chart_manager = ChartManager(config=self.config)
        self._dashboard_updater = DashboardUpdater(config=self.config)
        
        # Chart dialogs
        self._chart_dialogs = ChartDialogs(parent=self, config=self.config)
        
        # Metrics calculator
        self._metrics_calculator = MetricsCalculator()
        
        # Set up callbacks for intraday table managers
        self._ltp_table_manager.set_format_time_func(self.format_time)
        self._ltp_table_manager.set_get_enabled_indicators_func(self._get_enabled_indicators)
        self._ltp_table_manager.set_map_config_name_func(self._map_config_name_to_indicator_name)
        self._positions_table_manager.set_format_time_func(self.format_time)
        self._positions_table_manager.set_log_event_func(self.log_event)
        self._positions_table_manager.set_get_engine_func(self._get_engine)
        self._trades_table_manager.set_format_time_func(self.format_time)
        self._trades_table_manager.set_log_event_func(self.log_event)
        
        # Set up callbacks for backtest table managers
        self._backtest_ltp_manager.set_format_time_func(self.format_time)
        self._backtest_ltp_manager.set_get_enabled_indicators_func(self._get_enabled_indicators)
        self._backtest_ltp_manager.set_map_config_name_func(self._map_config_name_to_indicator_name)
        self._backtest_positions_manager.set_format_time_func(self.format_time)
        self._backtest_positions_manager.set_log_event_func(self.log_event)
        self._backtest_positions_manager.set_get_engine_func(self._get_engine)
        self._backtest_trades_manager.set_format_time_func(self.format_time)
        self._backtest_trades_manager.set_log_event_func(self.log_event)
    
    def _get_engine(self):
        """Get the trading engine from bot thread."""
        if self.bot_thread and hasattr(self.bot_thread, 'bot') and self.bot_thread.bot:
            return self.bot_thread.bot.engine
        return None
    
    def load_config(self) -> dict:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load config: {e}")
            return {}
    
    def save_config(self, config: dict):
        """Save configuration to YAML file"""
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save config: {e}")
            return False
    
    def create_ui(self):
        """Create the main UI with tabs"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.intraday_tab = QWidget()
        self.backtest_tab = QWidget()
        self.event_log_tab = QWidget()
        self.data_config_tab = QWidget()
        
        self.tab_widget.addTab(self.intraday_tab, "Intraday Trading")
        self.tab_widget.addTab(self.backtest_tab, "Backtesting")
        self.tab_widget.addTab(self.event_log_tab, "Event Log")
        self.tab_widget.addTab(self.data_config_tab, "Data Config")
        
        # Create content for each tab
        self.create_intraday_tab()
        self.create_backtest_tab()
        self.create_event_log_tab()
        self.create_data_config_tab()
        
        # Connect tab change signal
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
    
    def on_tab_changed(self, index):
        """Handle tab change event"""
        # Reload data config when switching to Data Config tab
        if index == 3:  # Data Config tab is the 4th tab (index 3)
            self.load_data_config_to_ui()
        elif index == 1:  # Backtest tab
            self.load_backtest_configs()
    
    def create_intraday_tab(self):
        """Create intraday trading tab with sub-tabs"""
        main_layout = QVBoxLayout(self.intraday_tab)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create sub-tab widget
        self.intraday_sub_tabs = QTabWidget()
        main_layout.addWidget(self.intraday_sub_tabs)
        
        # Trading sub-tab (existing functionality)
        trading_sub_tab = QWidget()
        trading_layout = QHBoxLayout(trading_sub_tab)
        trading_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create collapsible configuration panel
        def create_intraday_configs(parent, layout):
            self.create_symbols_config(parent, layout, prefix="intraday_")
            self.create_trading_config(parent, layout, prefix="intraday_")
            self.create_indicators_config(parent, layout, prefix="intraday_")
            self.create_risk_config(parent, layout, prefix="intraday_")
            self.create_exit_strategy_config(parent, layout, prefix="intraday_")
        
        config_widget, config_toggle_btn = self.create_collapsible_config_panel(
            "Configuration",
            create_intraday_configs,
            default_width=520,
            min_width=50
        )
        
        # Add toggle button at the top of the layout
        toggle_layout = QHBoxLayout()
        toggle_layout.addWidget(config_toggle_btn)
        toggle_layout.addStretch()
        trading_layout.insertLayout(0, toggle_layout)
        
        trading_layout.addWidget(config_widget)
        
        # Right panel: Results - should expand to fill remaining space
        results_widget = QWidget()
        results_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        results_layout = QVBoxLayout(results_widget)
        results_layout.setContentsMargins(5, 5, 5, 5)
        
        self.create_intraday_results(results_widget, results_layout)
        
        trading_layout.addWidget(results_widget, stretch=1)
        
        # Dashboard sub-tab
        dashboard_sub_tab = QWidget()
        dashboard_layout = QVBoxLayout(dashboard_sub_tab)
        dashboard_layout.setContentsMargins(5, 5, 5, 5)
        
        self.create_intraday_dashboard(dashboard_sub_tab, dashboard_layout)
        
        # Add sub-tabs
        self.intraday_sub_tabs.addTab(trading_sub_tab, "Trading")
        self.intraday_sub_tabs.addTab(dashboard_sub_tab, "Analytics Dashboard")
    
    def create_symbols_config(self, parent, layout, prefix=""):
        """Create symbols configuration panel using modular component."""
        panel = SymbolsConfigPanel(parent_widget=self, config=self.config, prefix=prefix)
        # Store panel reference for later use
        panel_attr = f"_{prefix}symbols_panel" if prefix else "_symbols_panel"
        setattr(self, panel_attr, panel)
        panel.create(parent, layout)
    
    def add_symbol(self, prefix=""):
        """Add symbol to list."""
        panel_attr = f"_{prefix}symbols_panel" if prefix else "_symbols_panel"
        panel = getattr(self, panel_attr, None)
        if panel:
            panel.add_symbol()
    
    def remove_symbol(self, prefix=""):
        """Remove selected symbol."""
        panel_attr = f"_{prefix}symbols_panel" if prefix else "_symbols_panel"
        panel = getattr(self, panel_attr, None)
        if panel:
            panel.remove_symbol()
    
    def set_lot_size(self, prefix=""):
        """Set lot size for symbol."""
        panel_attr = f"_{prefix}symbols_panel" if prefix else "_symbols_panel"
        panel = getattr(self, panel_attr, None)
        if panel:
            panel.set_lot_size()
    
    def remove_lot_size(self, prefix=""):
        """Remove lot size entry."""
        panel_attr = f"_{prefix}symbols_panel" if prefix else "_symbols_panel"
        panel = getattr(self, panel_attr, None)
        if panel:
            panel.remove_lot_size()
    
    def create_trading_config(self, parent, layout, prefix=""):
        """Create trading configuration panel using modular component."""
        panel = TradingConfigPanel(parent_widget=self, config=self.config, prefix=prefix)
        panel_attr = f"_{prefix}trading_panel" if prefix else "_trading_panel"
        setattr(self, panel_attr, panel)
        panel.create(parent, layout)
    
    def create_indicators_config(self, parent, layout, prefix=""):
        """Create indicators configuration panel using modular component."""
        panel = IndicatorsConfigPanel(parent_widget=self, config=self.config, prefix=prefix)
        panel_attr = f"_{prefix}indicators_panel" if prefix else "_indicators_panel"
        setattr(self, panel_attr, panel)
        panel.create(parent, layout)
    
    def create_risk_config(self, parent, layout, prefix=""):
        """Create risk management configuration panel using modular component."""
        panel = RiskConfigPanel(parent_widget=self, config=self.config, prefix=prefix)
        panel_attr = f"_{prefix}risk_panel" if prefix else "_risk_panel"
        setattr(self, panel_attr, panel)
        panel.create(parent, layout)
    
    def create_exit_strategy_config(self, parent, layout, prefix=""):
        """Create exit strategy configuration panel using modular component."""
        panel = ExitStrategyConfigPanel(parent_widget=self, config=self.config, prefix=prefix)
        panel_attr = f"_{prefix}exit_strategy_panel" if prefix else "_exit_strategy_panel"
        setattr(self, panel_attr, panel)
        panel.create(parent, layout)
    
    def create_intraday_results(self, parent, layout):
        """Create intraday results panel"""
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.start_intraday_btn = QPushButton("Start Intraday")
        self.start_intraday_btn.clicked.connect(self.start_intraday)
        control_layout.addWidget(self.start_intraday_btn)
        
        self.stop_intraday_btn = QPushButton("Stop Intraday")
        self.stop_intraday_btn.clicked.connect(self.stop_intraday)
        self.stop_intraday_btn.setEnabled(False)
        control_layout.addWidget(self.stop_intraday_btn)
        
        save_btn = QPushButton("Save Config")
        save_btn.clicked.connect(self.save_config_from_ui)
        control_layout.addWidget(save_btn)
        
        reload_btn = QPushButton("Reload Config")
        reload_btn.clicked.connect(self.reload_config)
        control_layout.addWidget(reload_btn)

        self.intraday_live_chart_btn = QPushButton("📈 Live Chart")
        self.intraday_live_chart_btn.setToolTip("View live chart during intraday trading")
        self.intraday_live_chart_btn.clicked.connect(self.view_intraday_live_chart)
        self.intraday_live_chart_btn.setEnabled(False)
        control_layout.addWidget(self.intraday_live_chart_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # Status
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("Ready")
        self.status_label.setFont(QFont("Arial", 10, QFont.Bold))
        status_layout.addWidget(self.status_label)
        
        layout.addWidget(status_group)
        
        # Symbol LTP table
        ltp_group = QGroupBox("Symbol Prices (LTP)")
        ltp_layout = QVBoxLayout(ltp_group)
        
        # Get enabled indicators to determine column count
        enabled_indicators = self._get_enabled_indicators()
        num_indicator_cols = len(enabled_indicators)
        num_base_cols = 6  # Symbol, LTP, Signal, Change, Confidence, DateTime
        total_cols = num_base_cols + num_indicator_cols
        
        self.ltp_table = QTableWidget(0, total_cols)
        headers = ["Symbol", "LTP", "Signal", "Change", "Confidence", "DateTime"] + [ind.replace('_', ' ').title() for ind in enabled_indicators]
        self.ltp_table.setHorizontalHeaderLabels(headers)
        self.ltp_table.horizontalHeader().setStretchLastSection(True)
        self.ltp_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.ltp_table.itemDoubleClicked.connect(self.on_symbol_click)
        
        # Store enabled indicators list for later use
        self.enabled_indicators_list = enabled_indicators
        
        ltp_layout.addWidget(self.ltp_table)
        
        hint_label = QLabel("💡 Double-click on any symbol to view its price trend chart")
        hint_label.setStyleSheet("color: gray; font-size: 9px;")
        ltp_layout.addWidget(hint_label)
        
        layout.addWidget(ltp_group)
        
        # Positions table
        positions_group = QGroupBox("Open Positions")
        positions_layout = QVBoxLayout(positions_group)
        
        self.positions_table = QTableWidget(0, 13)  # Initialize with 0 rows, 13 columns (matching backtest structure)
        self.positions_table.setHorizontalHeaderLabels([
            "Symbol", "Type", "Trade Type", "Entry", "Qty", "LTP", "PnL", "Max Profit", "Min Profit", "Avg Profit", "Avg Loss", "Capital Used", "Entry Time"
        ])
        self.positions_table.horizontalHeader().setStretchLastSection(True)
        positions_layout.addWidget(self.positions_table)
        
        layout.addWidget(positions_group)
        
        # Completed trades table
        trades_group = QGroupBox("Completed Trades")
        trades_layout = QVBoxLayout(trades_group)
        
        # Check if candle prices should be shown
        output_config = self.config.get('output', {})
        candle_config = output_config.get('show_candle_prices', {})
        show_candle_prices = candle_config.get('enabled', True)
        show_entry_high = candle_config.get('show_entry_high', True) if show_candle_prices else False
        show_exit_low = candle_config.get('show_exit_low', True) if show_candle_prices else False
        
        # Calculate column count dynamically
        base_columns = 19
        if show_entry_high:
            base_columns += 1
        if show_exit_low:
            base_columns += 1
        
        # Build header labels dynamically
        headers = ["ID", "Symbol", "Type", "Trade Type", "Entry"]
        if show_entry_high:
            headers.append("Entry High")
        headers.extend(["Exit"])
        if show_exit_low:
            headers.append("Exit Low")
        headers.extend([
            "Qty", "PnL", "Return%", "Max Profit", "Min Profit", "Avg Profit", "Avg Loss", 
            "Capital Used", "Total Charges", "Net Profit", "Entry Time", "Exit Time", "Exit Reason"
        ])
        
        self.trades_table = QTableWidget(0, base_columns)
        self.trades_table.setHorizontalHeaderLabels(headers)
        self.trades_table.horizontalHeader().setStretchLastSection(True)
        trades_layout.addWidget(self.trades_table)
        
        layout.addWidget(trades_group)
        
        # Performance summary table
        perf_group = QGroupBox("Performance Summary")
        perf_layout = QVBoxLayout(perf_group)
        
        self.intraday_summary_table = QTableWidget(0, 2)  # Initialize with 0 rows, 2 columns
        self.intraday_summary_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.intraday_summary_table.horizontalHeader().setStretchLastSection(True)
        self.intraday_summary_table.setSelectionBehavior(QTableWidget.SelectRows)
        perf_layout.addWidget(self.intraday_summary_table)
        
        layout.addWidget(perf_group)
        
        # Event Console removed - moved to Event Log tab
    
    def clear_event_console(self):
        """Clear the event console"""
        self.event_console.clear()
    
    def log_event(self, event_type: str, message: str):
        """Log an event to the console"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Color code by event type
        if event_type == "ENTRY":
            color = "#4ec9b0"  # Cyan
            icon = "📈"
        elif event_type == "EXIT" or event_type == "PARTIAL_EXIT":
            color = "#ce9178"  # Orange
            icon = "📉"
        elif event_type == "PROFIT_TARGET":
            color = "#6a9955"  # Green
            icon = "💰"
        elif event_type == "STOP_LOSS":
            color = "#f48771"  # Red
            icon = "🛑"
        elif event_type == "ERROR":
            color = "#f48771"  # Red
            icon = "❌"
        elif event_type == "INFO":
            color = "#569cd6"  # Blue
            icon = "ℹ️"
        else:
            color = "#d4d4d4"  # Default gray
            icon = "📊"
        
        formatted_message = f'<span style="color: {color};">[{timestamp}] {icon} <b>{event_type}</b>: {message}</span>'
        self.event_console.append(formatted_message)
        
        # Auto-scroll to bottom
        scrollbar = self.event_console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def create_event_log_tab(self):
        """Create Event Log tab"""
        main_layout = QVBoxLayout(self.event_log_tab)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header with title and clear button
        header_layout = QHBoxLayout()
        title_label = QLabel("Event Log Console")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        clear_btn = QPushButton("Clear Console")
        clear_btn.setMaximumWidth(150)
        clear_btn.setStyleSheet("padding: 6px 15px; font-size: 11px;")
        clear_btn.clicked.connect(self.clear_event_console)
        header_layout.addWidget(clear_btn)
        
        main_layout.addLayout(header_layout)
        
        # Event Console
        self.event_console = QTextEdit()
        self.event_console.setReadOnly(True)
        self.event_console.setFont(QFont("Consolas", 9))
        self.event_console.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #3e3e3e;")
        
        # Make it expand to fill available space
        main_layout.addWidget(self.event_console, stretch=1)
        
        # Info label at bottom
        info_label = QLabel("💡 This console shows all trading events, including entries, exits, quantity changes, and errors")
        info_label.setStyleSheet("color: gray; font-size: 9px; padding: 5px;")
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)
    
    def create_collapsible_config_panel(self, title: str, config_creators: callable, default_width: int = 520, min_width: int = 50):
        """Create a collapsible configuration panel with toggle button"""
        # Container widget for the entire panel
        container = QWidget()
        container.setMinimumWidth(min_width)
        container.setMaximumWidth(default_width)
        container.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Expanding)  # Don't expand horizontally
        
        # Main layout for container
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # Toggle button (hamburger menu style)
        toggle_btn = QPushButton("☰")
        toggle_btn.setFixedSize(40, 30)
        toggle_btn.setToolTip("Toggle Configuration Panel")
        toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3b3b3b;
            }
            QPushButton:pressed {
                background-color: #1b1b1b;
            }
        """)
        
        # Config panel widget (the actual content)
        config_widget = QWidget()
        config_widget.setMinimumWidth(default_width)
        config_widget.setMaximumWidth(default_width)
        config_layout = QVBoxLayout(config_widget)
        config_layout.setContentsMargins(5, 5, 5, 5)
        
        # Title label
        config_label = QLabel(title)
        config_label.setFont(QFont("Arial", 10, QFont.Bold))
        config_layout.addWidget(config_label)
        
        # Scrollable area for configuration
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create configuration panels using the provided creators
        config_creators(scroll_content, scroll_layout)
        
        scroll_area.setWidget(scroll_content)
        config_layout.addWidget(scroll_area)
        
        # Add config widget to container
        container_layout.addWidget(config_widget)
        
        # Animation for smooth expand/collapse
        if not hasattr(self, 'config_animations'):
            self.config_animations = {}
        animation_id = f"{title}_{id(container)}"
        
        # Create animations for both container and config_widget
        container_animation = QPropertyAnimation(container, b"maximumWidth")
        config_animation = QPropertyAnimation(config_widget, b"maximumWidth")
        
        for anim in [container_animation, config_animation]:
            anim.setDuration(300)  # 300ms animation
            anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        self.config_animations[animation_id] = {
            'container_animation': container_animation,
            'config_animation': config_animation,
            'container': container,
            'config_widget': config_widget,
            'default_width': default_width,
            'min_width': min_width,
            'is_expanded': True
        }
        
        # Toggle button click handler
        def toggle_panel():
            anim_data = self.config_animations[animation_id]
            is_expanded = anim_data['is_expanded']
            
            if is_expanded:
                # Collapse
                anim_data['container_animation'].setStartValue(default_width)
                anim_data['container_animation'].setEndValue(min_width)
                anim_data['config_animation'].setStartValue(default_width)
                anim_data['config_animation'].setEndValue(min_width)
                toggle_btn.setText("☰")
                toggle_btn.setToolTip("Expand Configuration Panel")
                # Hide content when collapsed
                scroll_area.setVisible(False)
                config_label.setVisible(False)
            else:
                # Expand
                anim_data['container_animation'].setStartValue(min_width)
                anim_data['container_animation'].setEndValue(default_width)
                anim_data['config_animation'].setStartValue(min_width)
                anim_data['config_animation'].setEndValue(default_width)
                toggle_btn.setText("☰")
                toggle_btn.setToolTip("Collapse Configuration Panel")
                # Show content when expanded
                scroll_area.setVisible(True)
                config_label.setVisible(True)
            
            anim_data['is_expanded'] = not is_expanded
            anim_data['container_animation'].start()
            anim_data['config_animation'].start()
        
        toggle_btn.clicked.connect(toggle_panel)
        
        return container, toggle_btn
    
    def create_data_config_tab(self):
        """Create Data Config tab for configuring Data/config/config.yaml"""
        main_layout = QVBoxLayout(self.data_config_tab)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Data Configuration (Fyers API)")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Save button
        save_btn = QPushButton("Save Config")
        save_btn.setMaximumWidth(150)
        save_btn.setStyleSheet("padding: 6px 15px; font-size: 11px;")
        save_btn.clicked.connect(self.save_data_config)
        header_layout.addWidget(save_btn)
        
        # Reload button
        reload_btn = QPushButton("Reload Config")
        reload_btn.setMaximumWidth(150)
        reload_btn.setStyleSheet("padding: 6px 15px; font-size: 11px;")
        reload_btn.clicked.connect(self.load_data_config_to_ui)
        header_layout.addWidget(reload_btn)
        
        main_layout.addLayout(header_layout)
        
        # Scrollable area for configuration
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        
        # Fyers Configuration Group
        fyers_group = QGroupBox("Fyers API Configuration")
        fyers_layout = QVBoxLayout(fyers_group)
        
        # Authorization Token
        auth_layout = QVBoxLayout()
        auth_label = QLabel("Authorization Token:")
        auth_label.setFont(QFont("Arial", 10, QFont.Bold))
        auth_layout.addWidget(auth_label)
        self.fyers_authorization_entry = QLineEdit()
        self.fyers_authorization_entry.setPlaceholderText("Enter Fyers authorization token (JWT)")
        self.fyers_authorization_entry.setEchoMode(QLineEdit.Password)  # Hide sensitive data
        auth_layout.addWidget(self.fyers_authorization_entry)
        
        # Show/Hide password toggle
        show_auth_btn = QPushButton("Show")
        show_auth_btn.setMaximumWidth(80)
        show_auth_btn.setCheckable(True)
        show_auth_btn.toggled.connect(lambda checked: self.fyers_authorization_entry.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password))
        show_auth_btn.toggled.connect(lambda checked: show_auth_btn.setText("Hide" if checked else "Show"))
        auth_layout.addWidget(show_auth_btn)
        fyers_layout.addLayout(auth_layout)
        
        # Token ID
        token_layout = QVBoxLayout()
        token_label = QLabel("Token ID:")
        token_label.setFont(QFont("Arial", 10, QFont.Bold))
        token_layout.addWidget(token_label)
        self.fyers_token_id_entry = QLineEdit()
        self.fyers_token_id_entry.setPlaceholderText("Enter Fyers token ID")
        self.fyers_token_id_entry.setEchoMode(QLineEdit.Password)  # Hide sensitive data
        token_layout.addWidget(self.fyers_token_id_entry)
        
        # Show/Hide token ID toggle
        show_token_btn = QPushButton("Show")
        show_token_btn.setMaximumWidth(80)
        show_token_btn.setCheckable(True)
        show_token_btn.toggled.connect(lambda checked: self.fyers_token_id_entry.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password))
        show_token_btn.toggled.connect(lambda checked: show_token_btn.setText("Hide" if checked else "Show"))
        token_layout.addWidget(show_token_btn)
        fyers_layout.addLayout(token_layout)
        
        # API URL
        api_url_layout = QVBoxLayout()
        api_url_label = QLabel("API URL:")
        api_url_label.setFont(QFont("Arial", 10, QFont.Bold))
        api_url_layout.addWidget(api_url_label)
        self.fyers_api_url_entry = QLineEdit()
        self.fyers_api_url_entry.setPlaceholderText("Enter Fyers API URL")
        api_url_layout.addWidget(self.fyers_api_url_entry)
        fyers_layout.addLayout(api_url_layout)
        
        scroll_layout.addWidget(fyers_group)
        scroll_layout.addStretch()
        
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
        # Info label
        info_label = QLabel("💡 Configure Fyers API credentials. Changes are saved to Data/config/config.yaml")
        info_label.setStyleSheet("color: gray; font-size: 9px; padding: 5px;")
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)
        
        # Load config when tab is created
        self.load_data_config_to_ui()
    
    def load_data_config(self) -> dict:
        """Load Data config from YAML file"""
        try:
            if self.data_config_path.exists():
                with open(self.data_config_path, 'r') as f:
                    return yaml.safe_load(f) or {}
            else:
                # Return default structure if file doesn't exist
                return {'Fyers': {'Authorization': '', 'token_id': '', 'api_url': 'https://api-t1.fyers.in/indus/history'}}
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to load data config: {e}")
            return {'Fyers': {'Authorization': '', 'token_id': '', 'api_url': 'https://api-t1.fyers.in/indus/history'}}
    
    def save_data_config(self):
        """Save Data config to YAML file"""
        try:
            # Get values from UI
            fyers_config = {
                'Authorization': self.fyers_authorization_entry.text().strip(),
                'token_id': self.fyers_token_id_entry.text().strip(),
                'api_url': self.fyers_api_url_entry.text().strip() or 'https://api-t1.fyers.in/indus/history'
            }
            
            config = {
                'Fyers': fyers_config
            }
            
            # Ensure directory exists
            self.data_config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save to file
            with open(self.data_config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            QMessageBox.information(self, "Success", f"Data configuration saved successfully to:\n{self.data_config_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save data config: {e}")
    
    def load_data_config_to_ui(self):
        """Load Data config into UI fields"""
        try:
            config = self.load_data_config()
            fyers_config = config.get('Fyers', {})
            
            # Load Fyers configuration
            if hasattr(self, 'fyers_authorization_entry'):
                self.fyers_authorization_entry.setText(fyers_config.get('Authorization', ''))
            if hasattr(self, 'fyers_token_id_entry'):
                self.fyers_token_id_entry.setText(fyers_config.get('token_id', ''))
            if hasattr(self, 'fyers_api_url_entry'):
                self.fyers_api_url_entry.setText(fyers_config.get('api_url', 'https://api-t1.fyers.in/indus/history'))
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to load data config into UI: {e}")
    
    def create_backtest_tab(self):
        """Create backtesting tab with sub-tabs"""
        main_layout = QVBoxLayout(self.backtest_tab)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create sub-tab widget
        self.backtest_sub_tabs = QTabWidget()
        main_layout.addWidget(self.backtest_sub_tabs)
        
        # Trading sub-tab (existing functionality)
        trading_sub_tab = QWidget()
        trading_layout = QHBoxLayout(trading_sub_tab)
        trading_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create collapsible configuration panel
        def create_backtest_configs(parent, layout):
            self.create_backtest_symbols_config(parent, layout)
            self.create_backtest_trading_config(parent, layout)
            self.create_backtest_indicators_config(parent, layout)
            self.create_backtest_risk_config(parent, layout)
            self.create_exit_strategy_config(parent, layout, prefix="backtest_")
            self.create_backtest_config(parent, layout)
        
        config_widget, config_toggle_btn = self.create_collapsible_config_panel(
            "Backtest Configuration",
            create_backtest_configs,
            default_width=520,
            min_width=50
        )
        
        # Add toggle button at the top of the layout
        toggle_layout = QHBoxLayout()
        toggle_layout.addWidget(config_toggle_btn)
        toggle_layout.addStretch()
        trading_layout.insertLayout(0, toggle_layout)
        
        trading_layout.addWidget(config_widget)
        
        # Right panel: Results - should expand to fill remaining space
        results_widget = QWidget()
        results_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        results_layout = QVBoxLayout(results_widget)
        results_layout.setContentsMargins(5, 5, 5, 5)
        
        self.create_backtest_results(results_widget, results_layout)
        
        trading_layout.addWidget(results_widget, stretch=1)
        
        # Dashboard sub-tab
        dashboard_sub_tab = QWidget()
        dashboard_layout = QVBoxLayout(dashboard_sub_tab)
        dashboard_layout.setContentsMargins(5, 5, 5, 5)
        
        self.create_backtest_dashboard(dashboard_sub_tab, dashboard_layout)
        
        # Add sub-tabs
        self.backtest_sub_tabs.addTab(trading_sub_tab, "Trading")
        self.backtest_sub_tabs.addTab(dashboard_sub_tab, "Analytics Dashboard")
        
        # Load backtest configs when tab is created
        self.load_backtest_configs()
    
    def create_intraday_dashboard(self, parent, layout):
        """Create intraday analytics dashboard"""
        # Scrollable area for dashboard
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        
        # KPI Tiles Section
        kpi_group = QGroupBox("Performance Overview")
        kpi_layout = QGridLayout(kpi_group)
        kpi_layout.setSpacing(8)
        kpi_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create KPI tiles
        self.intraday_kpi_tiles = {}
        kpi_metrics = [
            ('total_pnl', 'Total PnL', '₹0.00', '#1976d2'),
            ('win_rate', 'Win Rate', '0.00%', '#388e3c'),
            ('total_trades', 'Total Trades', '0', '#f57c00'),
            ('open_positions', 'Open Positions', '0', '#7b1fa2'),
            ('realized_pnl', 'Realized PnL', '₹0.00', '#0288d1'),
            ('avg_win', 'Avg Win', '₹0.00', '#2e7d32'),
            ('avg_loss', 'Avg Loss', '₹0.00', '#c62828'),
            ('profit_factor', 'Profit Factor', '0.00', '#f9a825')
        ]
        
        row, col = 0, 0
        for key, label, default, color in kpi_metrics:
            tile = self.create_kpi_tile(label, default, color)
            self.intraday_kpi_tiles[key] = tile
            kpi_layout.addWidget(tile, row, col)
            col += 1
            if col >= 4:
                col = 0
                row += 1
        
        scroll_layout.addWidget(kpi_group)
        
        # Charts Section - Modern styling
        charts_group = QGroupBox("Charts")
        charts_group.setStyleSheet("""
            QGroupBox {
                font-size: 12px;
                font-weight: bold;
                border: 1px solid rgba(200, 200, 200, 0.3);
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: rgba(40, 40, 40, 0.5);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        charts_layout = QVBoxLayout(charts_group)
        charts_layout.setSpacing(8)
        charts_layout.setContentsMargins(10, 15, 10, 10)
        
        # PnL Over Time Chart
        pnl_chart_label = QLabel("PnL Over Time")
        pnl_chart_label.setFont(QFont("Arial", 11, QFont.Bold))
        pnl_chart_label.setStyleSheet("color: rgba(255, 255, 255, 0.9); padding: 5px;")
        charts_layout.addWidget(pnl_chart_label)
        
        self.intraday_pnl_chart = QWebEngineView()
        self.intraday_pnl_chart.setMinimumHeight(280)
        self.intraday_pnl_chart.setStyleSheet("border-radius: 6px; background-color: rgba(30, 30, 30, 0.8);")
        charts_layout.addWidget(self.intraday_pnl_chart)
        
        # Equity Curve Chart
        equity_chart_label = QLabel("Equity Curve")
        equity_chart_label.setFont(QFont("Arial", 11, QFont.Bold))
        equity_chart_label.setStyleSheet("color: rgba(255, 255, 255, 0.9); padding: 5px;")
        charts_layout.addWidget(equity_chart_label)
        
        self.intraday_equity_chart = QWebEngineView()
        self.intraday_equity_chart.setMinimumHeight(280)
        self.intraday_equity_chart.setStyleSheet("border-radius: 6px; background-color: rgba(30, 30, 30, 0.8);")
        charts_layout.addWidget(self.intraday_equity_chart)
        
        scroll_layout.addWidget(charts_group)
        
        # Exit Reasons Breakdown
        exit_reasons_group = QGroupBox("Exit Reasons Breakdown")
        exit_reasons_layout = QVBoxLayout(exit_reasons_group)
        
        self.intraday_exit_reasons_table = QTableWidget(0, 3)
        self.intraday_exit_reasons_table.setHorizontalHeaderLabels([
            "Exit Reason", "Count", "Percentage"
        ])
        self.intraday_exit_reasons_table.horizontalHeader().setStretchLastSection(True)
        exit_reasons_layout.addWidget(self.intraday_exit_reasons_table)
        
        scroll_layout.addWidget(exit_reasons_group)
        
        # Per-Symbol Performance
        symbol_group = QGroupBox("Per-Symbol Performance")
        symbol_layout = QVBoxLayout(symbol_group)
        
        self.intraday_symbol_table = QTableWidget(0, 6)
        self.intraday_symbol_table.setHorizontalHeaderLabels([
            "Symbol", "Trades", "PnL", "Win Rate", "Avg Win", "Avg Loss"
        ])
        self.intraday_symbol_table.horizontalHeader().setStretchLastSection(True)
        symbol_layout.addWidget(self.intraday_symbol_table)
        
        scroll_layout.addWidget(symbol_group)
        
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Initialize dashboard data
        self.intraday_dashboard_data = {
            'pnl_history': [],
            'equity_history': [],
            'timestamps': []
        }
    
    def create_backtest_dashboard(self, parent, layout):
        """Create backtest analytics dashboard"""
        # Scrollable area for dashboard
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        
        # KPI Tiles Section - Modern styling
        kpi_group = QGroupBox("Performance Overview")
        kpi_group.setStyleSheet("""
            QGroupBox {
                font-size: 12px;
                font-weight: bold;
                border: 1px solid rgba(200, 200, 200, 0.3);
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: rgba(40, 40, 40, 0.5);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        kpi_layout = QGridLayout(kpi_group)
        kpi_layout.setSpacing(10)
        kpi_layout.setContentsMargins(10, 15, 10, 10)
        
        # Create KPI tiles
        self.backtest_kpi_tiles = {}
        kpi_metrics = [
            ('total_pnl', 'Total PnL', '₹0.00', '#1976d2'),
            ('win_rate', 'Win Rate', '0.00%', '#388e3c'),
            ('total_trades', 'Total Trades', '0', '#f57c00'),
            ('sharpe_ratio', 'Sharpe Ratio', '0.00', '#7b1fa2'),
            ('max_drawdown', 'Max Drawdown', '0.00%', '#c62828'),
            ('profit_factor', 'Profit Factor', '0.00', '#f9a825'),
            ('expectancy', 'Expectancy', '₹0.00', '#0288d1'),
            ('return_pct', 'Return %', '0.00%', '#2e7d32')
        ]
        
        row, col = 0, 0
        for key, label, default, color in kpi_metrics:
            tile = self.create_kpi_tile(label, default, color)
            self.backtest_kpi_tiles[key] = tile
            kpi_layout.addWidget(tile, row, col)
            col += 1
            if col >= 4:
                col = 0
                row += 1
        
        scroll_layout.addWidget(kpi_group)
        
        # Charts Section - Modern styling
        charts_group = QGroupBox("Charts")
        charts_group.setStyleSheet("""
            QGroupBox {
                font-size: 12px;
                font-weight: bold;
                border: 1px solid rgba(200, 200, 200, 0.3);
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: rgba(40, 40, 40, 0.5);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        charts_layout = QVBoxLayout(charts_group)
        charts_layout.setSpacing(8)
        charts_layout.setContentsMargins(10, 15, 10, 10)
        
        # PnL Over Time Chart
        pnl_chart_label = QLabel("PnL Over Time")
        pnl_chart_label.setFont(QFont("Arial", 11, QFont.Bold))
        pnl_chart_label.setStyleSheet("color: rgba(255, 255, 255, 0.9); padding: 5px;")
        charts_layout.addWidget(pnl_chart_label)
        
        self.backtest_pnl_chart = QWebEngineView()
        self.backtest_pnl_chart.setMinimumHeight(280)
        self.backtest_pnl_chart.setStyleSheet("border-radius: 6px; background-color: rgba(30, 30, 30, 0.8);")
        charts_layout.addWidget(self.backtest_pnl_chart)
        
        # Equity Curve Chart
        equity_chart_label = QLabel("Equity Curve")
        equity_chart_label.setFont(QFont("Arial", 11, QFont.Bold))
        equity_chart_label.setStyleSheet("color: rgba(255, 255, 255, 0.9); padding: 5px;")
        charts_layout.addWidget(equity_chart_label)
        
        self.backtest_equity_chart = QWebEngineView()
        self.backtest_equity_chart.setMinimumHeight(280)
        self.backtest_equity_chart.setStyleSheet("border-radius: 6px; background-color: rgba(30, 30, 30, 0.8);")
        charts_layout.addWidget(self.backtest_equity_chart)
        
        # Win/Loss Distribution Chart
        dist_chart_label = QLabel("Win/Loss Distribution")
        dist_chart_label.setFont(QFont("Arial", 11, QFont.Bold))
        dist_chart_label.setStyleSheet("color: rgba(255, 255, 255, 0.9); padding: 5px;")
        charts_layout.addWidget(dist_chart_label)
        
        self.backtest_dist_chart = QWebEngineView()
        self.backtest_dist_chart.setMinimumHeight(280)
        self.backtest_dist_chart.setStyleSheet("border-radius: 6px; background-color: rgba(30, 30, 30, 0.8);")
        charts_layout.addWidget(self.backtest_dist_chart)
        
        scroll_layout.addWidget(charts_group)
        
        # Exit Reasons Breakdown
        exit_reasons_group = QGroupBox("Exit Reasons Breakdown")
        exit_reasons_layout = QVBoxLayout(exit_reasons_group)
        
        self.backtest_exit_reasons_table = QTableWidget(0, 3)
        self.backtest_exit_reasons_table.setHorizontalHeaderLabels([
            "Exit Reason", "Count", "Percentage"
        ])
        self.backtest_exit_reasons_table.horizontalHeader().setStretchLastSection(True)
        exit_reasons_layout.addWidget(self.backtest_exit_reasons_table)
        
        scroll_layout.addWidget(exit_reasons_group)
        
        # Per-Symbol Performance
        symbol_group = QGroupBox("Per-Symbol Performance")
        symbol_layout = QVBoxLayout(symbol_group)
        
        self.backtest_symbol_table = QTableWidget(0, 8)
        self.backtest_symbol_table.setHorizontalHeaderLabels([
            "Symbol", "Trades", "PnL", "Win Rate", "Avg Win", "Avg Loss", "Profit Factor", "Expectancy"
        ])
        self.backtest_symbol_table.horizontalHeader().setStretchLastSection(True)
        symbol_layout.addWidget(self.backtest_symbol_table)
        
        scroll_layout.addWidget(symbol_group)
        
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Initialize dashboard data
        self.backtest_dashboard_data = {
            'pnl_history': [],
            'equity_history': [],
            'timestamps': []
        }
    
    def create_kpi_tile(self, title: str, value: str, color: str) -> QFrame:
        """Create a modern, compact KPI tile widget with gradient effect"""
        tile = QFrame()
        tile.setFrameShape(QFrame.Box)
        
        # Modern styling with subtle shadow effect and gradient-like appearance
        tile.setStyleSheet(f"""
            QFrame {{
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {color},
                    stop:1 rgba(0, 0, 0, 0.2));
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                padding: 10px;
                min-width: 130px;
                max-width: 160px;
                min-height: 75px;
                max-height: 85px;
            }}
            QFrame:hover {{
                border: 1px solid rgba(255, 255, 255, 0.3);
            }}
        """)
        
        layout = QVBoxLayout(tile)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.9);
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 0.5px;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setObjectName("kpi_value")
        value_label.setWordWrap(False)
        value_label.setStyleSheet("""
            color: white;
            font-size: 18px;
            font-weight: 700;
            background-color: transparent;
        """)
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setMinimumHeight(35)
        value_label.setMaximumHeight(40)
        # Ensure text is fully visible
        value_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout.addWidget(value_label, alignment=Qt.AlignCenter)
        
        return tile
    
    def create_backtest_symbols_config(self, parent, layout):
        """Create symbols configuration for backtest"""
        self.create_symbols_config(parent, layout, prefix="backtest_")
    
    def create_backtest_trading_config(self, parent, layout):
        """Create trading configuration for backtest"""
        self.create_trading_config(parent, layout, prefix="backtest_")
    
    def create_backtest_indicators_config(self, parent, layout):
        """Create indicators configuration for backtest"""
        self.create_indicators_config(parent, layout, prefix="backtest_")
    
    def create_backtest_risk_config(self, parent, layout):
        """Create risk configuration for backtest"""
        self.create_risk_config(parent, layout, prefix="backtest_")
    
    def create_backtest_config(self, parent, layout):
        """Create backtest-specific configuration using modular component."""
        panel = BacktestConfigPanel(parent_widget=self, config=self.config)
        setattr(self, "_backtest_config_panel", panel)
        panel.create(parent, layout)
    
    def create_backtest_results(self, parent, layout):
        """Create backtest results panel"""
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.start_backtest_btn = QPushButton("Start Backtest")
        self.start_backtest_btn.clicked.connect(self.start_backtest)
        control_layout.addWidget(self.start_backtest_btn)
        
        self.stop_backtest_btn = QPushButton("Stop Backtest")
        self.stop_backtest_btn.clicked.connect(self.stop_backtest)
        self.stop_backtest_btn.setEnabled(False)
        control_layout.addWidget(self.stop_backtest_btn)
        
        save_btn = QPushButton("Save Config")
        save_btn.clicked.connect(self.save_config_from_ui)
        control_layout.addWidget(save_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # Status
        status_group = QGroupBox("Backtest Status")
        status_layout = QVBoxLayout(status_group)
        
        self.backtest_status_label = QLabel("Ready")
        self.backtest_status_label.setFont(QFont("Arial", 10, QFont.Bold))
        status_layout.addWidget(self.backtest_status_label)
        
        # Progress bar
        self.backtest_progress = QProgressBar()
        status_layout.addWidget(self.backtest_progress)
        
        layout.addWidget(status_group)
        
        # Backtest Symbol Prices Table (similar to intraday LTP table)
        ltp_group = QGroupBox("Symbol Prices (Backtest)")
        ltp_layout = QVBoxLayout(ltp_group)
        
        # Get enabled indicators for column count
        enabled_indicators = self._get_enabled_indicators()
        num_indicator_cols = len(enabled_indicators)
        num_base_cols = 5  # Symbol, LTP, Signal, Change, Confidence
        total_cols = num_base_cols + num_indicator_cols
        
        self.backtest_ltp_table = QTableWidget(0, total_cols)
        headers = ["Symbol", "LTP", "Signal", "Change", "Confidence"] + [ind.replace('_', ' ').title() for ind in enabled_indicators]
        self.backtest_ltp_table.setHorizontalHeaderLabels(headers)
        self.backtest_ltp_table.horizontalHeader().setStretchLastSection(True)
        self.backtest_ltp_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        # Store symbol mapping for backtest LTP table
        self.backtest_ltp_symbol_map = {}  # row -> symbol
        self.backtest_previous_prices = {}  # symbol -> previous price
        
        ltp_layout.addWidget(self.backtest_ltp_table)
        layout.addWidget(ltp_group)
        
        # Backtest open positions table
        positions_group = QGroupBox("Open Positions (Backtest)")
        positions_layout = QVBoxLayout(positions_group)
        
        self.backtest_positions_table = QTableWidget(0, 13)
        self.backtest_positions_table.setHorizontalHeaderLabels([
            "Symbol", "Type", "Trade Type", "Entry", "Qty", "LTP", "PnL", "Max Profit", "Min Profit", "Avg Profit", "Avg Loss", "Capital Used", "Entry Time"
        ])
        self.backtest_positions_table.horizontalHeader().setStretchLastSection(True)
        positions_layout.addWidget(self.backtest_positions_table)
        layout.addWidget(positions_group)
        
        # Backtest results table
        results_group = QGroupBox("Backtest Results")
        results_layout = QVBoxLayout(results_group)
        
        # Button layout for table actions
        button_layout = QHBoxLayout()
        
        # Create a button to open the maximizable table dialog with filters
        self.backtest_table_btn = QPushButton("Open Full Table with Filters (Popup)")
        self.backtest_table_btn.clicked.connect(self.show_backtest_results_dialog)
        button_layout.addWidget(self.backtest_table_btn)
        
        # Export to CSV button
        self.backtest_export_btn = QPushButton("Export to CSV")
        self.backtest_export_btn.clicked.connect(self.export_backtest_results_to_csv)
        button_layout.addWidget(self.backtest_export_btn)
        
        # View Charts button
        self.backtest_view_charts_btn = QPushButton("📊 View Charts")
        self.backtest_view_charts_btn.setToolTip("View candlestick charts with trade markers")
        self.backtest_view_charts_btn.clicked.connect(self.view_backtest_charts)
        self.backtest_view_charts_btn.setEnabled(False)  # Disabled until data is available
        button_layout.addWidget(self.backtest_view_charts_btn)
        
        # Live Chart button
        self.backtest_live_chart_btn = QPushButton("📈 Live Chart")
        self.backtest_live_chart_btn.setToolTip("View live chart during backtesting")
        self.backtest_live_chart_btn.clicked.connect(self.view_live_backtest_chart)
        self.backtest_live_chart_btn.setEnabled(False)  # Disabled until backtest starts
        button_layout.addWidget(self.backtest_live_chart_btn)
        
        button_layout.addStretch()
        results_layout.addLayout(button_layout)
        
        # Keep the original table visible for inline viewing
        # Check if candle prices should be shown
        output_config = self.config.get('output', {})
        candle_config = output_config.get('show_candle_prices', {})
        show_candle_prices = candle_config.get('enabled', True)
        show_entry_high = candle_config.get('show_entry_high', True) if show_candle_prices else False
        show_exit_low = candle_config.get('show_exit_low', True) if show_candle_prices else False
        
        # Calculate column count dynamically
        base_columns = 19
        if show_entry_high:
            base_columns += 1
        if show_exit_low:
            base_columns += 1
        
        # Build header labels dynamically
        headers = ["ID", "Symbol", "Type", "Trade Type", "Entry"]
        if show_entry_high:
            headers.append("Entry High")
        headers.extend(["Exit"])
        if show_exit_low:
            headers.append("Exit Low")
        headers.extend([
            "Qty", "PnL", "Return%", "Max Profit", "Min Profit", "Avg Profit", "Avg Loss", 
            "Capital Used", "Total Charges", "Net Profit", "Entry Time", "Exit Time", "Exit Reason"
        ])
        
        self.backtest_table = QTableWidget(0, base_columns)
        self.backtest_table.setHorizontalHeaderLabels(headers)
        self.backtest_table.horizontalHeader().setStretchLastSection(True)
        results_layout.addWidget(self.backtest_table)
        
        # Store reference to dialog (will be created on first use)
        self.backtest_results_dialog = None
        
        layout.addWidget(results_group)
        
        # Backtest summary table
        summary_group = QGroupBox("Backtest Summary")
        summary_layout = QVBoxLayout(summary_group)
        
        # Create a button to open the summary popup dialog
        self.backtest_summary_btn = QPushButton("Open Summary in Full Screen (Popup)")
        self.backtest_summary_btn.clicked.connect(self.show_backtest_summary_dialog)
        summary_layout.addWidget(self.backtest_summary_btn)
        
        self.backtest_summary_table = QTableWidget(0, 2)  # Initialize with 0 rows, 2 columns
        self.backtest_summary_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.backtest_summary_table.horizontalHeader().setStretchLastSection(True)
        self.backtest_summary_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.backtest_summary_table.itemDoubleClicked.connect(self.on_metric_click)
        summary_layout.addWidget(self.backtest_summary_table)
        
        # Store reference to summary dialog (will be created on first use)
        self.backtest_summary_dialog = None
        
        layout.addWidget(summary_group)
    
    # Configuration loading and saving methods
    def load_config_to_ui(self):
        """Load configuration from file into UI"""
        try:
            # Load symbols for intraday tab
            symbols = self.config.get('symbols', [])
            if hasattr(self, 'intraday_symbols_list'):
                self.intraday_symbols_list.clear()
                for symbol in symbols:
                    self.intraday_symbols_list.addItem(str(symbol))
            
            # Load symbols for backtest tab
            if hasattr(self, 'backtest_symbols_list'):
                self.backtest_symbols_list.clear()
                for symbol in symbols:
                    self.backtest_symbols_list.addItem(str(symbol))
            
            # Load trading config for intraday
            trading = self.config.get('trading', {})
            if hasattr(self, 'intraday_auto_trade_check'):
                auto_trade = trading.get('enable_auto_trading', trading.get('auto_trade', False))
                self.intraday_auto_trade_check.setChecked(bool(auto_trade))
            
            if hasattr(self, 'intraday_allow_buy_check'):
                self.intraday_allow_buy_check.setChecked(trading.get('allow_buy', True))
            
            if hasattr(self, 'intraday_allow_sell_check'):
                self.intraday_allow_sell_check.setChecked(trading.get('allow_sell', False))
            
            if hasattr(self, 'intraday_paper_trading_check'):
                self.intraday_paper_trading_check.setChecked(trading.get('paper_trading', False))
            
            # Load refresh intervals for intraday
            if hasattr(self, 'intraday_slow_refresh_interval_entry'):
                slow_refresh_interval = trading.get('slow_refresh_interval', 30)
                self.intraday_slow_refresh_interval_entry.setText(str(slow_refresh_interval))
            
            if hasattr(self, 'intraday_fast_refresh_interval_entry'):
                fast_refresh_interval = trading.get('fast_refresh_interval', 15)
                self.intraday_fast_refresh_interval_entry.setText(str(fast_refresh_interval))
            
            # Legacy support for old refresh_interval field
            if hasattr(self, 'intraday_refresh_interval_entry'):
                refresh_interval = trading.get('refresh_interval', trading.get('slow_refresh_interval', 30))
                self.intraday_refresh_interval_entry.setText(str(refresh_interval))
            
            if hasattr(self, 'intraday_default_quantity_entry'):
                default_qty = trading.get('default_quantity', '')
                self.intraday_default_quantity_entry.setText(str(default_qty) if default_qty else '')
            
            # Load max allowed quantity for backtest
            if hasattr(self, 'backtest_default_quantity_entry'):
                backtest_default_qty = trading.get('default_quantity', '')
                self.backtest_default_quantity_entry.setText(str(backtest_default_qty) if backtest_default_qty else '')
            
            # Load aggregation strategy and min_agreement
            if hasattr(self, 'intraday_aggregation_strategy_combo'):
                agg_strategy = self.config.get('aggregation_strategy', 'weighted')
                idx = self.intraday_aggregation_strategy_combo.findText(agg_strategy)
                if idx >= 0:
                    self.intraday_aggregation_strategy_combo.setCurrentIndex(idx)
            
            if hasattr(self, 'intraday_min_agreement_entry'):
                min_agreement = self.config.get('min_agreement', 0.6)
                self.intraday_min_agreement_entry.setText(str(min_agreement))
            
            # Load risk config early (needed for max_position_size)
            risk = self.config.get('risk_management', {})
            
            # Load max position size
            if hasattr(self, 'intraday_max_position_size_entry'):
                max_pos_size = risk.get('max_position_size', 2000)
                self.intraday_max_position_size_entry.setText(str(max_pos_size))
            
            # Load backtest config
            backtest = self.config.get('backtest', {})
            initial_capital = backtest.get('initial_capital', 20000)
            
            if hasattr(self, 'backtest_initial_capital_entry'):
                self.backtest_initial_capital_entry.setText(str(initial_capital))
            
            if hasattr(self, 'intraday_initial_capital_entry'):
                self.intraday_initial_capital_entry.setText(str(initial_capital))
            
            # Load lot sizes - check both root level and trading level
            lot_sizes = {}
            if 'lot_sizes' in self.config:
                lot_sizes = self.config['lot_sizes']
            elif 'trading' in self.config and 'lot_sizes' in self.config['trading']:
                lot_sizes = self.config['trading']['lot_sizes']
            
            # Load lot sizes for intraday
            if hasattr(self, 'intraday_lot_sizes_tree'):
                self.intraday_lot_sizes_tree.setRowCount(0)
                for symbol, lot_size in lot_sizes.items():
                    if symbol != 'default':  # Skip default key
                        row = self.intraday_lot_sizes_tree.rowCount()
                        self.intraday_lot_sizes_tree.insertRow(row)
                        self.intraday_lot_sizes_tree.setItem(row, 0, QTableWidgetItem(str(symbol)))
                        self.intraday_lot_sizes_tree.setItem(row, 1, QTableWidgetItem(str(lot_size)))
            
            # Load lot sizes for backtest
            if hasattr(self, 'backtest_lot_sizes_tree'):
                self.backtest_lot_sizes_tree.setRowCount(0)
                for symbol, lot_size in lot_sizes.items():
                    if symbol != 'default':  # Skip default key
                        row = self.backtest_lot_sizes_tree.rowCount()
                        self.backtest_lot_sizes_tree.insertRow(row)
                        self.backtest_lot_sizes_tree.setItem(row, 0, QTableWidgetItem(str(symbol)))
                        self.backtest_lot_sizes_tree.setItem(row, 1, QTableWidgetItem(str(lot_size)))
            
            # Load default lot size
            default_lot = 1
            if 'lot_sizes' in self.config and 'default' in self.config['lot_sizes']:
                default_lot = self.config['lot_sizes']['default']
            elif 'trading' in self.config:
                default_lot = trading.get('default_lot_size', 1)
            
            if hasattr(self, 'intraday_default_lot_entry'):
                self.intraday_default_lot_entry.setText(str(default_lot))
            
            if hasattr(self, 'backtest_default_lot_entry'):
                self.backtest_default_lot_entry.setText(str(default_lot))
            
            # Continue loading risk config for intraday
            
            if hasattr(self, 'intraday_risk_per_trade_entry'):
                risk_pct = risk.get('risk_per_trade_pct', 2)
                self.intraday_risk_per_trade_entry.setText(str(risk_pct))
            
            # Load capital percentage per trade for intraday
            if hasattr(self, 'intraday_capital_percentage_per_trade_entry'):
                capital_pct = risk.get('capital_percentage_per_trade_intraday', 20.0)
                self.intraday_capital_percentage_per_trade_entry.setText(str(capital_pct))
            
            if hasattr(self, 'intraday_max_positions_entry'):
                max_pos = risk.get('max_positions', 5)
                self.intraday_max_positions_entry.setText(str(max_pos))
            
            if hasattr(self, 'intraday_stop_loss_entry'):
                stop_loss_pct = risk.get('stop_loss_pct', 2)
                if 'stop_loss' in risk and 'min_stop_pct' in risk['stop_loss']:
                    stop_loss_pct = risk['stop_loss']['min_stop_pct']
                self.intraday_stop_loss_entry.setText(str(stop_loss_pct))
            
            if hasattr(self, 'intraday_daily_loss_limit_entry'):
                daily_limit = risk.get('daily_loss_limit', 10000)
                self.intraday_daily_loss_limit_entry.setText(str(daily_limit))
            
            # Load daily limits for intraday
            daily_limits = risk.get('daily_limits', {})
            if hasattr(self, 'intraday_max_loss_amount_entry'):
                self.intraday_max_loss_amount_entry.setText(str(daily_limits.get('max_loss_amount', 2000)))
            if hasattr(self, 'intraday_max_trades_per_day_entry'):
                self.intraday_max_trades_per_day_entry.setText(str(daily_limits.get('max_trades_per_day', 200)))
            
            # Load paper trading mode for intraday
            paper_mode = risk.get('paper_trading_mode', {})
            if hasattr(self, 'intraday_paper_mode_enabled_check'):
                self.intraday_paper_mode_enabled_check.setChecked(paper_mode.get('enabled', False))
            if hasattr(self, 'intraday_consecutive_losses_trigger_entry'):
                self.intraday_consecutive_losses_trigger_entry.setText(str(paper_mode.get('consecutive_losses_trigger', 5)))
            if hasattr(self, 'intraday_exit_on_paper_profit_check'):
                self.intraday_exit_on_paper_profit_check.setChecked(paper_mode.get('exit_on_paper_profit', True))
            
            # Load loss recovery for intraday
            loss_recovery = risk.get('loss_recovery', {})
            if hasattr(self, 'intraday_loss_recovery_enabled_check'):
                self.intraday_loss_recovery_enabled_check.setChecked(loss_recovery.get('enabled', False))
            if hasattr(self, 'intraday_loss_recovery_max_multiplier_entry'):
                self.intraday_loss_recovery_max_multiplier_entry.setText(str(loss_recovery.get('max_multiplier', 3.0)))
            if hasattr(self, 'intraday_loss_recovery_priority_check'):
                self.intraday_loss_recovery_priority_check.setChecked(loss_recovery.get('recovery_priority', False))
            
            # Load partial exits for intraday
            partial_exits = risk.get('partial_exits', {})
            if hasattr(self, 'intraday_partial_exits_enabled_check'):
                self.intraday_partial_exits_enabled_check.setChecked(partial_exits.get('enabled', True))
            
            # Load risk config for backtest
            if hasattr(self, 'backtest_risk_per_trade_entry'):
                risk_pct = risk.get('risk_per_trade_pct', 2)
                self.backtest_risk_per_trade_entry.setText(str(risk_pct))
            
            # Load capital percentage per trade for backtest
            if hasattr(self, 'backtest_capital_percentage_per_trade_entry'):
                capital_pct = risk.get('capital_percentage_per_trade_backtest', 50.0)
                self.backtest_capital_percentage_per_trade_entry.setText(str(capital_pct))
            
            # Load max position size for backtest
            if hasattr(self, 'backtest_max_position_size_entry'):
                max_pos_size = risk.get('max_position_size', 2000)
                self.backtest_max_position_size_entry.setText(str(max_pos_size))
            
            if hasattr(self, 'backtest_max_positions_entry'):
                max_pos = risk.get('max_positions', 5)
                self.backtest_max_positions_entry.setText(str(max_pos))
            
            if hasattr(self, 'backtest_stop_loss_entry'):
                stop_loss_pct = risk.get('stop_loss_pct', 2)
                if 'stop_loss' in risk and 'min_stop_pct' in risk['stop_loss']:
                    stop_loss_pct = risk['stop_loss']['min_stop_pct']
                self.backtest_stop_loss_entry.setText(str(stop_loss_pct))
            
            if hasattr(self, 'backtest_daily_loss_limit_entry'):
                daily_limit = risk.get('daily_loss_limit', 10000)
                self.backtest_daily_loss_limit_entry.setText(str(daily_limit))
            
            # Load daily limits for backtest
            daily_limits = risk.get('daily_limits', {})
            if hasattr(self, 'backtest_max_loss_amount_entry'):
                self.backtest_max_loss_amount_entry.setText(str(daily_limits.get('max_loss_amount', 2000)))
            if hasattr(self, 'backtest_max_trades_per_day_entry'):
                self.backtest_max_trades_per_day_entry.setText(str(daily_limits.get('max_trades_per_day', 200)))
            
            # Load paper trading mode for backtest
            paper_mode = risk.get('paper_trading_mode', {})
            if hasattr(self, 'backtest_paper_mode_enabled_check'):
                self.backtest_paper_mode_enabled_check.setChecked(paper_mode.get('enabled', False))
            if hasattr(self, 'backtest_consecutive_losses_trigger_entry'):
                self.backtest_consecutive_losses_trigger_entry.setText(str(paper_mode.get('consecutive_losses_trigger', 5)))
            if hasattr(self, 'backtest_exit_on_paper_profit_check'):
                self.backtest_exit_on_paper_profit_check.setChecked(paper_mode.get('exit_on_paper_profit', True))
            
            # Load loss recovery for backtest
            loss_recovery = risk.get('loss_recovery', {})
            if hasattr(self, 'backtest_loss_recovery_enabled_check'):
                self.backtest_loss_recovery_enabled_check.setChecked(loss_recovery.get('enabled', False))
            if hasattr(self, 'backtest_loss_recovery_max_multiplier_entry'):
                self.backtest_loss_recovery_max_multiplier_entry.setText(str(loss_recovery.get('max_multiplier', 3.0)))
            if hasattr(self, 'backtest_loss_recovery_priority_check'):
                self.backtest_loss_recovery_priority_check.setChecked(loss_recovery.get('recovery_priority', False))
            
            # Load partial exits for backtest
            partial_exits = risk.get('partial_exits', {})
            if hasattr(self, 'backtest_partial_exits_enabled_check'):
                self.backtest_partial_exits_enabled_check.setChecked(partial_exits.get('enabled', True))
            
            # Load backtest dates
            if hasattr(self, 'start_date_edit'):
                if 'start_date' in backtest:
                    start_date_str = backtest['start_date']
                    # Try to parse date string
                    try:
                        if 'T' in start_date_str or ' ' in start_date_str:
                            start_date_str = start_date_str.split()[0]  # Get date part only
                        start_date = QDate.fromString(start_date_str, Qt.ISODate)
                        if not start_date.isValid():
                            # Try alternative format
                            start_date = QDate.fromString(start_date_str, "yyyy-MM-dd")
                        if start_date.isValid():
                            self.start_date_edit.setDate(start_date)
                    except:
                        pass
            
            if hasattr(self, 'end_date_edit'):
                if 'end_date' in backtest:
                    end_date_str = backtest['end_date']
                    try:
                        if 'T' in end_date_str or ' ' in end_date_str:
                            end_date_str = end_date_str.split()[0]
                        end_date = QDate.fromString(end_date_str, Qt.ISODate)
                        if not end_date.isValid():
                            end_date = QDate.fromString(end_date_str, "yyyy-MM-dd")
                        if end_date.isValid():
                            self.end_date_edit.setDate(end_date)
                    except:
                        pass
            
            # Load backtest speed and resolution
            if hasattr(self, 'speed_combo'):
                speed = backtest.get('speed', 'fast')
                speed_index = 0 if speed.lower() == 'fast' else 1
                self.speed_combo.setCurrentIndex(speed_index)
            
            if hasattr(self, 'resolution_combo'):
                resolution = backtest.get('resolution', '30S')
                # Map old format to new format if needed
                resolution_map = {
                    '1min': '1',
                    '5min': '5',
                    '15min': '15S',
                    '1hour': '1',
                    '1day': '1'
                }
                if resolution in resolution_map:
                    resolution = resolution_map[resolution]
                # Available resolutions in combo: ["5S", "15S", "30S", "1", "5"]
                resolutions = ["5S", "15S", "30S", "1", "5"]
                if resolution in resolutions:
                    self.resolution_combo.setCurrentIndex(resolutions.index(resolution))
                else:
                    # Default to 30S if not found
                    self.resolution_combo.setCurrentIndex(2)  # 30S is index 2
            
            # Load indicators for intraday tab
            indicators_config = self.config.get('indicators', {})
            intraday_indicator_controls = getattr(self, 'intraday_indicator_controls', {})
            for ind_name, ind_config in indicators_config.items():
                if ind_name in intraday_indicator_controls:
                    controls = intraday_indicator_controls[ind_name]
                    if 'enabled' in controls:
                        controls['enabled'].setChecked(ind_config.get('enabled', False))
                    if 'weight' in controls:
                        controls['weight'].setText(str(ind_config.get('weight', 1.0)))
                    # Load super_regression specific parameters
                    if ind_name == 'super_regression':
                        if 'len' in controls:
                            controls['len'].setText(str(ind_config.get('len', 20)))
                        if 'mult' in controls:
                            controls['mult'].setText(str(ind_config.get('mult', 2.0)))
                        if 'source' in controls:
                            source_val = ind_config.get('source', 'close')
                            idx = controls['source'].findText(source_val)
                            if idx >= 0:
                                controls['source'].setCurrentIndex(idx)
            
            # Load indicators for backtest tab
            backtest_indicator_controls = getattr(self, 'backtest_indicator_controls', {})
            for ind_name, ind_config in indicators_config.items():
                if ind_name in backtest_indicator_controls:
                    controls = backtest_indicator_controls[ind_name]
                    if 'enabled' in controls:
                        controls['enabled'].setChecked(ind_config.get('enabled', False))
                    if 'weight' in controls:
                        controls['weight'].setText(str(ind_config.get('weight', 1.0)))
                    # Load super_regression specific parameters
                    if ind_name == 'super_regression':
                        if 'len' in controls:
                            controls['len'].setText(str(ind_config.get('len', 20)))
                        if 'mult' in controls:
                            controls['mult'].setText(str(ind_config.get('mult', 2.0)))
                        if 'source' in controls:
                            source_val = ind_config.get('source', 'close')
                            idx = controls['source'].findText(source_val)
                            if idx >= 0:
                                controls['source'].setCurrentIndex(idx)
            
            # Load exit strategy config for intraday
            stop_loss_config = risk.get('stop_loss', {})
            if hasattr(self, 'intraday_sl_method_combo'):
                method = stop_loss_config.get('method', 'volatility')
                index = 0 if method == 'volatility' else 1
                self.intraday_sl_method_combo.setCurrentIndex(index)
            if hasattr(self, 'intraday_max_loss_per_trade_entry'):
                self.intraday_max_loss_per_trade_entry.setText(str(stop_loss_config.get('max_loss_per_trade', 300)))
            if hasattr(self, 'intraday_atr_multiplier_entry'):
                self.intraday_atr_multiplier_entry.setText(str(stop_loss_config.get('atr_multiplier', 1.5)))
            if hasattr(self, 'intraday_breakeven_enabled_check'):
                self.intraday_breakeven_enabled_check.setChecked(stop_loss_config.get('breakeven_enabled', False))
            if hasattr(self, 'intraday_breakeven_trigger_entry'):
                self.intraday_breakeven_trigger_entry.setText(str(stop_loss_config.get('breakeven_trigger_ratio', 1.05)))
            
            profit_targets_config = risk.get('profit_targets', {})
            if hasattr(self, 'intraday_profit_targets_enabled_check'):
                self.intraday_profit_targets_enabled_check.setChecked(profit_targets_config.get('enabled', False))
            if hasattr(self, 'intraday_pt1_ratio_entry'):
                pt1 = profit_targets_config.get('target_1', {})
                self.intraday_pt1_ratio_entry.setText(str(pt1.get('ratio', 1.2)))
                self.intraday_pt1_exit_entry.setText(str(pt1.get('exit_pct', 80.0)))
            if hasattr(self, 'intraday_pt2_ratio_entry'):
                pt2 = profit_targets_config.get('target_2', {})
                self.intraday_pt2_ratio_entry.setText(str(pt2.get('ratio', 2.0)))
                self.intraday_pt2_exit_entry.setText(str(pt2.get('exit_pct', 50.0)))
            if hasattr(self, 'intraday_pt3_ratio_entry'):
                pt3 = profit_targets_config.get('target_3', {})
                self.intraday_pt3_ratio_entry.setText(str(pt3.get('ratio', 3.0)))
                self.intraday_pt3_exit_entry.setText(str(pt3.get('exit_pct', 20.0)))
            
            # Load profit target reversal config for intraday
            reversal_config = profit_targets_config.get('reversal', {})
            if hasattr(self, 'intraday_profit_target_reversal_enabled_check'):
                self.intraday_profit_target_reversal_enabled_check.setChecked(reversal_config.get('enabled', True))
            if hasattr(self, 'intraday_profit_target_reversal_atr_multiplier_entry'):
                self.intraday_profit_target_reversal_atr_multiplier_entry.setText(str(reversal_config.get('atr_multiplier', 0.5)))
            if hasattr(self, 'intraday_profit_target_reversal_percent_entry'):
                self.intraday_profit_target_reversal_percent_entry.setText(str(reversal_config.get('percent_threshold', 1.0)))
            
            # Load profit reversal protection config for intraday
            profit_reversal_config = risk.get('profit_reversal_protection', {})
            if hasattr(self, 'intraday_profit_reversal_protection_enabled_check'):
                self.intraday_profit_reversal_protection_enabled_check.setChecked(profit_reversal_config.get('enabled', True))
            if hasattr(self, 'intraday_profit_reversal_min_profit_entry'):
                self.intraday_profit_reversal_min_profit_entry.setText(str(profit_reversal_config.get('min_profit', 100.0)))
            if hasattr(self, 'intraday_profit_reversal_threshold_entry'):
                self.intraday_profit_reversal_threshold_entry.setText(str(profit_reversal_config.get('reversal_threshold', 50.0)))
            if hasattr(self, 'intraday_profit_reversal_atr_multiplier_entry'):
                self.intraday_profit_reversal_atr_multiplier_entry.setText(str(profit_reversal_config.get('atr_multiplier', 1.0)))
            
            # Load profit drop protection config
            profit_drop_config = risk.get('profit_drop_protection', {})
            if hasattr(self, 'intraday_profit_drop_protection_enabled_check'):
                self.intraday_profit_drop_protection_enabled_check.setChecked(profit_drop_config.get('enabled', False))
            if hasattr(self, 'intraday_profit_drop_percentage_entry'):
                self.intraday_profit_drop_percentage_entry.setText(str(profit_drop_config.get('drop_percentage', 3.0)))
            
            # Load unrealized profit drop config
            unrealized_drop_config = risk.get('unrealized_profit_drop', {})
            if hasattr(self, 'intraday_unrealized_profit_drop_enabled_check'):
                self.intraday_unrealized_profit_drop_enabled_check.setChecked(unrealized_drop_config.get('enabled', False))
            if hasattr(self, 'intraday_unrealized_profit_drop_threshold_entry'):
                self.intraday_unrealized_profit_drop_threshold_entry.setText(str(unrealized_drop_config.get('percent_threshold', 4.0)))
            
            # Load below average profit exit config
            below_avg_config = risk.get('below_avg_profit_exit', {})
            if hasattr(self, 'intraday_below_avg_profit_exit_enabled_check'):
                self.intraday_below_avg_profit_exit_enabled_check.setChecked(below_avg_config.get('enabled', False))
            if hasattr(self, 'intraday_below_avg_profit_min_profit_entry'):
                self.intraday_below_avg_profit_min_profit_entry.setText(str(below_avg_config.get('min_profit', 50.0)))
            
            trailing_stop_config = risk.get('trailing_stop', {})
            if hasattr(self, 'intraday_trailing_stop_enabled_check'):
                self.intraday_trailing_stop_enabled_check.setChecked(trailing_stop_config.get('enabled', False))
            if hasattr(self, 'intraday_ts_activation_entry'):
                self.intraday_ts_activation_entry.setText(str(trailing_stop_config.get('activation_ratio', 1.05)))
            if hasattr(self, 'intraday_ts_multiplier_entry'):
                self.intraday_ts_multiplier_entry.setText(str(trailing_stop_config.get('trail_atr_multiplier', 1.5)))
            
            time_exit_config = risk.get('time_exit', {})
            if hasattr(self, 'intraday_time_exit_enabled_check'):
                self.intraday_time_exit_enabled_check.setChecked(time_exit_config.get('enabled', False))
            if hasattr(self, 'intraday_time_exit_max_hold_entry'):
                self.intraday_time_exit_max_hold_entry.setText(str(time_exit_config.get('max_hold_minutes', 60)))
            if hasattr(self, 'intraday_time_exit_force_eod_check'):
                self.intraday_time_exit_force_eod_check.setChecked(time_exit_config.get('force_close_eod', True))
            
            # Load candle closure exit config for intraday
            candle_closure_exit = risk.get('candle_closure_exit', {})
            if hasattr(self, 'intraday_candle_closure_exit_enabled_check'):
                self.intraday_candle_closure_exit_enabled_check.setChecked(candle_closure_exit.get('enabled', True))
            if hasattr(self, 'intraday_candle_closure_resolution_combo'):
                resolution = candle_closure_exit.get('resolution', '30S')
                index = self.intraday_candle_closure_resolution_combo.findText(resolution)
                if index >= 0:
                    self.intraday_candle_closure_resolution_combo.setCurrentIndex(index)
            if hasattr(self, 'intraday_candle_closure_loss_limit_entry'):
                self.intraday_candle_closure_loss_limit_entry.setText(str(candle_closure_exit.get('loss_limit', 0.0)))
            
            # Load exit strategy config for backtest
            if hasattr(self, 'backtest_sl_method_combo'):
                method = stop_loss_config.get('method', 'volatility')
                index = 0 if method == 'volatility' else 1
                self.backtest_sl_method_combo.setCurrentIndex(index)
            if hasattr(self, 'backtest_max_loss_per_trade_entry'):
                self.backtest_max_loss_per_trade_entry.setText(str(stop_loss_config.get('max_loss_per_trade', 300)))
            if hasattr(self, 'backtest_atr_multiplier_entry'):
                self.backtest_atr_multiplier_entry.setText(str(stop_loss_config.get('atr_multiplier', 1.5)))
            if hasattr(self, 'backtest_breakeven_enabled_check'):
                self.backtest_breakeven_enabled_check.setChecked(stop_loss_config.get('breakeven_enabled', False))
            if hasattr(self, 'backtest_breakeven_trigger_entry'):
                self.backtest_breakeven_trigger_entry.setText(str(stop_loss_config.get('breakeven_trigger_ratio', 1.05)))
            
            if hasattr(self, 'backtest_profit_targets_enabled_check'):
                self.backtest_profit_targets_enabled_check.setChecked(profit_targets_config.get('enabled', False))
            if hasattr(self, 'backtest_pt1_ratio_entry'):
                pt1 = profit_targets_config.get('target_1', {})
                self.backtest_pt1_ratio_entry.setText(str(pt1.get('ratio', 1.2)))
                self.backtest_pt1_exit_entry.setText(str(pt1.get('exit_pct', 80.0)))
            if hasattr(self, 'backtest_pt2_ratio_entry'):
                pt2 = profit_targets_config.get('target_2', {})
                self.backtest_pt2_ratio_entry.setText(str(pt2.get('ratio', 2.0)))
                self.backtest_pt2_exit_entry.setText(str(pt2.get('exit_pct', 50.0)))
            if hasattr(self, 'backtest_pt3_ratio_entry'):
                pt3 = profit_targets_config.get('target_3', {})
                self.backtest_pt3_ratio_entry.setText(str(pt3.get('ratio', 3.0)))
                self.backtest_pt3_exit_entry.setText(str(pt3.get('exit_pct', 20.0)))
            
            # Load profit target reversal config for backtest
            reversal_config = profit_targets_config.get('reversal', {})
            if hasattr(self, 'backtest_profit_target_reversal_enabled_check'):
                self.backtest_profit_target_reversal_enabled_check.setChecked(reversal_config.get('enabled', True))
            if hasattr(self, 'backtest_profit_target_reversal_atr_multiplier_entry'):
                self.backtest_profit_target_reversal_atr_multiplier_entry.setText(str(reversal_config.get('atr_multiplier', 0.5)))
            if hasattr(self, 'backtest_profit_target_reversal_percent_entry'):
                self.backtest_profit_target_reversal_percent_entry.setText(str(reversal_config.get('percent_threshold', 1.0)))
            
            # Load profit reversal protection config for backtest
            profit_reversal_config = risk.get('profit_reversal_protection', {})
            if hasattr(self, 'backtest_profit_reversal_protection_enabled_check'):
                self.backtest_profit_reversal_protection_enabled_check.setChecked(profit_reversal_config.get('enabled', True))
            if hasattr(self, 'backtest_profit_reversal_min_profit_entry'):
                self.backtest_profit_reversal_min_profit_entry.setText(str(profit_reversal_config.get('min_profit', 100.0)))
            if hasattr(self, 'backtest_profit_reversal_threshold_entry'):
                self.backtest_profit_reversal_threshold_entry.setText(str(profit_reversal_config.get('reversal_threshold', 50.0)))
            if hasattr(self, 'backtest_profit_reversal_atr_multiplier_entry'):
                self.backtest_profit_reversal_atr_multiplier_entry.setText(str(profit_reversal_config.get('atr_multiplier', 1.0)))
            
            # Load profit drop protection config
            profit_drop_config = risk.get('profit_drop_protection', {})
            if hasattr(self, 'backtest_profit_drop_protection_enabled_check'):
                self.backtest_profit_drop_protection_enabled_check.setChecked(profit_drop_config.get('enabled', False))
            if hasattr(self, 'backtest_profit_drop_percentage_entry'):
                self.backtest_profit_drop_percentage_entry.setText(str(profit_drop_config.get('drop_percentage', 3.0)))
            
            # Load unrealized profit drop config
            unrealized_drop_config = risk.get('unrealized_profit_drop', {})
            if hasattr(self, 'backtest_unrealized_profit_drop_enabled_check'):
                self.backtest_unrealized_profit_drop_enabled_check.setChecked(unrealized_drop_config.get('enabled', False))
            if hasattr(self, 'backtest_unrealized_profit_drop_threshold_entry'):
                self.backtest_unrealized_profit_drop_threshold_entry.setText(str(unrealized_drop_config.get('percent_threshold', 4.0)))
            
            # Load below average profit exit config
            below_avg_config = risk.get('below_avg_profit_exit', {})
            if hasattr(self, 'backtest_below_avg_profit_exit_enabled_check'):
                self.backtest_below_avg_profit_exit_enabled_check.setChecked(below_avg_config.get('enabled', False))
            if hasattr(self, 'backtest_below_avg_profit_min_profit_entry'):
                self.backtest_below_avg_profit_min_profit_entry.setText(str(below_avg_config.get('min_profit', 50.0)))
            
            if hasattr(self, 'backtest_trailing_stop_enabled_check'):
                self.backtest_trailing_stop_enabled_check.setChecked(trailing_stop_config.get('enabled', False))
            if hasattr(self, 'backtest_ts_activation_entry'):
                self.backtest_ts_activation_entry.setText(str(trailing_stop_config.get('activation_ratio', 1.05)))
            if hasattr(self, 'backtest_ts_multiplier_entry'):
                self.backtest_ts_multiplier_entry.setText(str(trailing_stop_config.get('trail_atr_multiplier', 1.5)))
            
            if hasattr(self, 'backtest_time_exit_enabled_check'):
                self.backtest_time_exit_enabled_check.setChecked(time_exit_config.get('enabled', False))
            if hasattr(self, 'backtest_time_exit_max_hold_entry'):
                self.backtest_time_exit_max_hold_entry.setText(str(time_exit_config.get('max_hold_minutes', 60)))
            if hasattr(self, 'backtest_time_exit_force_eod_check'):
                self.backtest_time_exit_force_eod_check.setChecked(time_exit_config.get('force_close_eod', True))
            
            # Load microstructure config for intraday
            microstructure_config = self.config.get('quant_indicators', {}).get('microstructure', {})
            if hasattr(self, 'intraday_microstructure_enabled_check'):
                self.intraday_microstructure_enabled_check.setChecked(microstructure_config.get('enabled', False))
            if hasattr(self, 'intraday_microstructure_detect_reversals_check'):
                self.intraday_microstructure_detect_reversals_check.setChecked(microstructure_config.get('detect_reversals', False))
            if hasattr(self, 'intraday_microstructure_volume_spike_entry'):
                self.intraday_microstructure_volume_spike_entry.setText(str(microstructure_config.get('volume_spike_threshold', 1.5)))
            
            # Load microstructure config for backtest
            if hasattr(self, 'backtest_microstructure_enabled_check'):
                self.backtest_microstructure_enabled_check.setChecked(microstructure_config.get('enabled', False))
            if hasattr(self, 'backtest_microstructure_detect_reversals_check'):
                self.backtest_microstructure_detect_reversals_check.setChecked(microstructure_config.get('detect_reversals', False))
            if hasattr(self, 'backtest_microstructure_volume_spike_entry'):
                self.backtest_microstructure_volume_spike_entry.setText(str(microstructure_config.get('volume_spike_threshold', 1.5)))
            
            # Initialize tables with headers if not already done
            self.initialize_tables()
            
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Error loading config: {str(e)}")
            import traceback
            print(traceback.format_exc())
    
    def initialize_tables(self):
        """Initialize all tables with proper headers"""
        # LTP table
        if hasattr(self, 'ltp_table') and self.ltp_table.columnCount() == 0:
            # Get enabled indicators to determine column count
            enabled_indicators = self._get_enabled_indicators()
            num_indicator_cols = len(enabled_indicators)
            num_base_cols = 6  # Symbol, LTP, Signal, Change, Confidence, DateTime
            total_cols = num_base_cols + num_indicator_cols
            
            self.ltp_table.setColumnCount(total_cols)
            headers = ["Symbol", "LTP", "Signal", "Change", "Confidence", "DateTime"] + [ind.replace('_', ' ').title() for ind in enabled_indicators]
            self.ltp_table.setHorizontalHeaderLabels(headers)
            self.ltp_table.horizontalHeader().setStretchLastSection(True)
            # Store enabled indicators list
            self.enabled_indicators_list = enabled_indicators
        
        # Positions table
        if hasattr(self, 'positions_table') and self.positions_table.columnCount() == 0:
            self.positions_table.setColumnCount(8)
            self.positions_table.setHorizontalHeaderLabels(["Symbol", "Type", "Trade Type", "Entry", "Qty", "LTP", "PnL", "Exit Price"])
            self.positions_table.horizontalHeader().setStretchLastSection(True)
            # Set HTML delegate for Exit Price column (column 7) to support colored text
            if not hasattr(self, '_html_delegate_set'):
                html_delegate = HTMLDelegate()
                self.positions_table.setItemDelegateForColumn(7, html_delegate)
                self._html_delegate_set = True
        
        # Trades table
        if hasattr(self, 'trades_table') and self.trades_table.columnCount() == 0:
            # Check if candle prices should be shown
            output_config = self.config.get('output', {})
            candle_config = output_config.get('show_candle_prices', {})
            show_candle_prices = candle_config.get('enabled', True)
            show_entry_high = candle_config.get('show_entry_high', True) if show_candle_prices else False
            show_exit_low = candle_config.get('show_exit_low', True) if show_candle_prices else False
            
            # Calculate column count dynamically
            base_columns = 14
            if show_entry_high:
                base_columns += 1
            if show_exit_low:
                base_columns += 1
            
            # Build header labels dynamically
            headers = ["ID", "Symbol", "Type", "Trade Type", "Entry"]
            if show_entry_high:
                headers.append("Entry High")
            headers.extend(["Exit"])
            if show_exit_low:
                headers.append("Exit Low")
            headers.extend([
                "Qty", "PnL", "Return%", "Total Charges", "Net Profit", "Entry Time", "Exit Time", "Exit Reason"
            ])
            
            self.trades_table.setColumnCount(base_columns)
            self.trades_table.setHorizontalHeaderLabels(headers)
            self.trades_table.horizontalHeader().setStretchLastSection(True)
        
        # Intraday summary table
        if hasattr(self, 'intraday_summary_table') and self.intraday_summary_table.columnCount() == 0:
            self.intraday_summary_table.setColumnCount(2)
            self.intraday_summary_table.setHorizontalHeaderLabels(["Metric", "Value"])
            self.intraday_summary_table.horizontalHeader().setStretchLastSection(True)
        
        # Backtest table
        if hasattr(self, 'backtest_table') and self.backtest_table.columnCount() == 0:
            # Check if candle prices should be shown
            output_config = self.config.get('output', {})
            candle_config = output_config.get('show_candle_prices', {})
            show_candle_prices = candle_config.get('enabled', True)
            show_entry_high = candle_config.get('show_entry_high', True) if show_candle_prices else False
            show_exit_low = candle_config.get('show_exit_low', True) if show_candle_prices else False
            
            # Calculate column count dynamically
            base_columns = 19
            if show_entry_high:
                base_columns += 1
            if show_exit_low:
                base_columns += 1
            
            # Build header labels dynamically
            headers = ["ID", "Symbol", "Type", "Trade Type", "Entry"]
            if show_entry_high:
                headers.append("Entry High")
            headers.extend(["Exit"])
            if show_exit_low:
                headers.append("Exit Low")
            headers.extend([
                "Qty", "PnL", "Return%", "Max Profit", "Min Profit", "Avg Profit", "Avg Loss", 
                "Capital Used", "Total Charges", "Net Profit", "Entry Time", "Exit Time", "Exit Reason"
            ])
            
            self.backtest_table.setColumnCount(base_columns)
            self.backtest_table.setHorizontalHeaderLabels(headers)
            self.backtest_table.horizontalHeader().setStretchLastSection(True)
        
        # Backtest LTP table
        if hasattr(self, 'backtest_ltp_table') and self.backtest_ltp_table.columnCount() == 0:
            enabled_indicators = self._get_enabled_indicators()
            num_indicator_cols = len(enabled_indicators)
            num_base_cols = 5  # Symbol, LTP, Signal, Change, Confidence
            total_cols = num_base_cols + num_indicator_cols
            
            self.backtest_ltp_table.setColumnCount(total_cols)
            headers = ["Symbol", "LTP", "Signal", "Change", "Confidence"] + [ind.replace('_', ' ').title() for ind in enabled_indicators]
            self.backtest_ltp_table.setHorizontalHeaderLabels(headers)
            self.backtest_ltp_table.horizontalHeader().setStretchLastSection(True)
        
        # Backtest summary table
        if hasattr(self, 'backtest_summary_table') and self.backtest_summary_table.columnCount() == 0:
            self.backtest_summary_table.setColumnCount(2)
            self.backtest_summary_table.setHorizontalHeaderLabels(["Metric", "Value"])
            self.backtest_summary_table.horizontalHeader().setStretchLastSection(True)
        
        # Link table managers to their widgets
        self._link_table_managers()
    
    def _link_table_managers(self):
        """Link table manager instances to their table widgets."""
        # Intraday tables
        if hasattr(self, 'ltp_table'):
            self._ltp_table_manager.set_table(self.ltp_table)
        if hasattr(self, 'positions_table'):
            self._positions_table_manager.set_table(self.positions_table)
        if hasattr(self, 'trades_table'):
            self._trades_table_manager.set_table(self.trades_table)
        if hasattr(self, 'intraday_summary_table'):
            self._intraday_summary_manager.set_table(self.intraday_summary_table)
        
        # Backtest tables
        if hasattr(self, 'backtest_ltp_table'):
            self._backtest_ltp_manager.set_table(self.backtest_ltp_table)
        if hasattr(self, 'backtest_positions_table'):
            self._backtest_positions_manager.set_table(self.backtest_positions_table)
        if hasattr(self, 'backtest_table'):
            self._backtest_trades_manager.set_table(self.backtest_table)
        if hasattr(self, 'backtest_summary_table'):
            self._backtest_summary_manager.set_table(self.backtest_summary_table)
        
        # Set up chart dialogs with history references
        self._chart_dialogs.set_ltp_history(self.ltp_history)
        self._chart_dialogs.set_metrics_history(self.metrics_history)
    
    def save_config_from_ui(self):
        """Save configuration from UI to file"""
        # Determine which tab is active
        current_tab = self.tab_widget.currentIndex()
        prefix = "backtest_" if current_tab == 1 else "intraday_"
        
        # Save symbols (use intraday tab's symbols list)
        symbols = []
        if hasattr(self, 'intraday_symbols_list'):
            for i in range(self.intraday_symbols_list.count()):
                symbols.append(self.intraday_symbols_list.item(i).text())
        self.config['symbols'] = symbols
        
        # Save trading config (use active tab's widgets)
        trading = self.config.get('trading', {})
        auto_trade_check = getattr(self, f'{prefix}auto_trade_check', None)
        if auto_trade_check:
            trading['enable_auto_trading'] = auto_trade_check.isChecked()
            trading['auto_trade'] = auto_trade_check.isChecked()
        
        allow_buy_check = getattr(self, f'{prefix}allow_buy_check', None)
        if allow_buy_check:
            trading['allow_buy'] = allow_buy_check.isChecked()
        
        allow_sell_check = getattr(self, f'{prefix}allow_sell_check', None)
        if allow_sell_check:
            trading['allow_sell'] = allow_sell_check.isChecked()
        
        paper_trading_check = getattr(self, f'{prefix}paper_trading_check', None)
        if paper_trading_check:
            trading['paper_trading'] = paper_trading_check.isChecked()
        
        # Save refresh intervals (intraday has separate fast/slow, backtest has single)
        if prefix == "intraday_":
            slow_refresh_entry = getattr(self, 'intraday_slow_refresh_interval_entry', None)
            if slow_refresh_entry and slow_refresh_entry.text():
                trading['slow_refresh_interval'] = int(slow_refresh_entry.text())
            
            fast_refresh_entry = getattr(self, 'intraday_fast_refresh_interval_entry', None)
            if fast_refresh_entry and fast_refresh_entry.text():
                trading['fast_refresh_interval'] = int(fast_refresh_entry.text())
        else:
            refresh_interval_entry = getattr(self, f'{prefix}refresh_interval_entry', None)
            if refresh_interval_entry:
                trading['refresh_interval'] = int(refresh_interval_entry.text() or 60)
        
        default_quantity_entry = getattr(self, f'{prefix}default_quantity_entry', None)
        if default_quantity_entry:
            trading['default_quantity'] = int(default_quantity_entry.text() or 0) if default_quantity_entry.text() else None
        
        # Save lot sizes (use active tab's lot sizes)
        lot_sizes = {}
        lot_sizes_tree = getattr(self, f'{prefix}lot_sizes_tree', None)
        if lot_sizes_tree:
            for row in range(lot_sizes_tree.rowCount()):
                symbol_item = lot_sizes_tree.item(row, 0)
                lot_item = lot_sizes_tree.item(row, 1)
                if symbol_item and lot_item:
                    lot_sizes[symbol_item.text()] = int(lot_item.text())
        trading['lot_sizes'] = lot_sizes
        
        default_lot_entry = getattr(self, f'{prefix}default_lot_entry', None)
        if default_lot_entry:
            default_lot = int(default_lot_entry.text() or 1)
            trading['default_lot_size'] = default_lot
        
        # Save backtest config (always save, regardless of active tab)
        backtest = self.config.get('backtest', {})
        
        # Save initial capital from backtest tab (prioritize backtest tab over intraday)
        if hasattr(self, 'backtest_initial_capital_entry') and self.backtest_initial_capital_entry.text():
            try:
                backtest['initial_capital'] = float(self.backtest_initial_capital_entry.text())
            except ValueError:
                backtest['initial_capital'] = float(backtest.get('initial_capital', 20000))
        elif hasattr(self, 'intraday_initial_capital_entry') and self.intraday_initial_capital_entry.text():
            # Fallback to intraday if backtest entry doesn't exist or is empty
            try:
                backtest['initial_capital'] = float(self.intraday_initial_capital_entry.text())
            except ValueError:
                backtest['initial_capital'] = float(backtest.get('initial_capital', 20000))
        else:
            # Keep existing value if neither entry has text
            backtest['initial_capital'] = float(backtest.get('initial_capital', 20000))
        
        # Save backtest-specific settings (only if widgets exist)
        if hasattr(self, 'start_date_edit'):
            backtest['start_date'] = self.start_date_edit.date().toString(Qt.ISODate)
        if hasattr(self, 'end_date_edit'):
            backtest['end_date'] = self.end_date_edit.date().toString(Qt.ISODate)
        
        # Save slippage settings
        if hasattr(self, 'backtest_entry_slippage_entry'):
            try:
                entry_slippage = float(self.backtest_entry_slippage_entry.text() or 0)
                backtest['entry_slippage'] = max(0.0, entry_slippage)  # Ensure non-negative
            except ValueError:
                backtest['entry_slippage'] = 0.0
        
        if hasattr(self, 'backtest_exit_slippage_entry'):
            try:
                exit_slippage = float(self.backtest_exit_slippage_entry.text() or 0)
                backtest['exit_slippage'] = max(0.0, exit_slippage)  # Ensure non-negative
            except ValueError:
                backtest['exit_slippage'] = 0.0
        if hasattr(self, 'speed_combo'):
            backtest['speed'] = self.speed_combo.currentText().lower()
        if hasattr(self, 'resolution_combo'):
            backtest['resolution'] = self.resolution_combo.currentText()
        
        # Ensure backtest config is saved
        self.config['backtest'] = backtest
        
        # Save risk config (use active tab's widgets)
        risk = self.config.get('risk_management', {})
        risk_per_trade_entry = getattr(self, f'{prefix}risk_per_trade_entry', None)
        if risk_per_trade_entry:
            risk['risk_per_trade_pct'] = float(risk_per_trade_entry.text() or 2)
        
        # Save capital percentage per trade
        capital_pct_entry = getattr(self, f'{prefix}capital_percentage_per_trade_entry', None)
        if capital_pct_entry:
            try:
                capital_pct_text = capital_pct_entry.text().strip()
                if capital_pct_text:
                    capital_pct = float(capital_pct_text)
                else:
                    # Use default based on tab
                    capital_pct = 50.0 if prefix == "backtest_" else 20.0
                # Store separately for backtest and intraday
                if prefix == "backtest_":
                    risk['capital_percentage_per_trade_backtest'] = capital_pct
                    print(f"💾 Saved capital_percentage_per_trade_backtest = {capital_pct}%")
                else:
                    risk['capital_percentage_per_trade_intraday'] = capital_pct
                    print(f"💾 Saved capital_percentage_per_trade_intraday = {capital_pct}%")
            except ValueError:
                # Use defaults if invalid
                if prefix == "backtest_":
                    risk['capital_percentage_per_trade_backtest'] = 50.0
                else:
                    risk['capital_percentage_per_trade_intraday'] = 20.0
        
        # Save max position size
        max_pos_size_entry = getattr(self, f'{prefix}max_position_size_entry', None)
        if max_pos_size_entry:
            max_pos_size_text = max_pos_size_entry.text().strip()
            if max_pos_size_text:
                try:
                    risk['max_position_size'] = int(max_pos_size_text)
                except ValueError:
                    risk['max_position_size'] = 2000  # Default if invalid
            else:
                risk['max_position_size'] = 2000  # Default if empty
        
        max_positions_entry = getattr(self, f'{prefix}max_positions_entry', None)
        if max_positions_entry:
            risk['max_positions'] = int(max_positions_entry.text() or 5)
        
        stop_loss_entry = getattr(self, f'{prefix}stop_loss_entry', None)
        if stop_loss_entry:
            risk['stop_loss_pct'] = float(stop_loss_entry.text() or 2)
        
        daily_loss_limit_entry = getattr(self, f'{prefix}daily_loss_limit_entry', None)
        if daily_loss_limit_entry:
            risk['daily_loss_limit'] = float(daily_loss_limit_entry.text() or 10000)
        
        # Save daily limits
        daily_limits = risk.get('daily_limits', {})
        max_loss_amount_entry = getattr(self, f'{prefix}max_loss_amount_entry', None)
        if max_loss_amount_entry:
            daily_limits['max_loss_amount'] = int(max_loss_amount_entry.text() or 2000)
        max_trades_entry = getattr(self, f'{prefix}max_trades_per_day_entry', None)
        if max_trades_entry:
            daily_limits['max_trades_per_day'] = int(max_trades_entry.text() or 200)
        risk['daily_limits'] = daily_limits
        
        # Save paper trading mode
        paper_mode = risk.get('paper_trading_mode', {})
        paper_mode_enabled_check = getattr(self, f'{prefix}paper_mode_enabled_check', None)
        if paper_mode_enabled_check:
            paper_mode['enabled'] = paper_mode_enabled_check.isChecked()
        consecutive_losses_entry = getattr(self, f'{prefix}consecutive_losses_trigger_entry', None)
        if consecutive_losses_entry:
            paper_mode['consecutive_losses_trigger'] = int(consecutive_losses_entry.text() or 5)
        exit_on_paper_profit_check = getattr(self, f'{prefix}exit_on_paper_profit_check', None)
        if exit_on_paper_profit_check:
            paper_mode['exit_on_paper_profit'] = exit_on_paper_profit_check.isChecked()
        risk['paper_trading_mode'] = paper_mode
        
        # Save loss recovery
        loss_recovery = risk.get('loss_recovery', {})
        loss_recovery_enabled_check = getattr(self, f'{prefix}loss_recovery_enabled_check', None)
        if loss_recovery_enabled_check:
            loss_recovery['enabled'] = loss_recovery_enabled_check.isChecked()
        max_multiplier_entry = getattr(self, f'{prefix}loss_recovery_max_multiplier_entry', None)
        if max_multiplier_entry:
            loss_recovery['max_multiplier'] = float(max_multiplier_entry.text() or 3.0)
        recovery_priority_check = getattr(self, f'{prefix}loss_recovery_priority_check', None)
        if recovery_priority_check:
            loss_recovery['recovery_priority'] = recovery_priority_check.isChecked()
        risk['loss_recovery'] = loss_recovery
        
        # Save partial exits
        partial_exits = risk.get('partial_exits', {})
        partial_exits_enabled_check = getattr(self, f'{prefix}partial_exits_enabled_check', None)
        if partial_exits_enabled_check:
            partial_exits['enabled'] = partial_exits_enabled_check.isChecked()
        risk['partial_exits'] = partial_exits
        
        # Save indicators (use active tab's indicator controls)
        indicators = self.config.get('indicators', {})
        indicator_controls_attr = f"{prefix}indicator_controls" if prefix else "indicator_controls"
        indicator_controls = getattr(self, indicator_controls_attr, {})
        
        for ind_name, controls in indicator_controls.items():
            if ind_name not in indicators:
                indicators[ind_name] = {}
            if 'enabled' in controls:
                indicators[ind_name]['enabled'] = controls['enabled'].isChecked()
            if 'weight' in controls:
                try:
                    indicators[ind_name]['weight'] = float(controls['weight'].text() or 1.0)
                except ValueError:
                    indicators[ind_name]['weight'] = 1.0
            
            # Save super_regression specific parameters
            if ind_name == 'super_regression':
                if 'len' in controls:
                    try:
                        indicators[ind_name]['len'] = int(controls['len'].text() or 20)
                    except ValueError:
                        indicators[ind_name]['len'] = 20
                if 'mult' in controls:
                    try:
                        indicators[ind_name]['mult'] = float(controls['mult'].text() or 2.0)
                    except ValueError:
                        indicators[ind_name]['mult'] = 2.0
                if 'source' in controls:
                    indicators[ind_name]['source'] = controls['source'].currentText()
        
        self.config['indicators'] = indicators
        
        # Save exit strategy config (use active tab's widgets)
        risk = self.config.get('risk_management', {})
        
        # Stop Loss
        stop_loss = risk.get('stop_loss', {})
        sl_method_combo = getattr(self, f'{prefix}sl_method_combo', None)
        if sl_method_combo:
            stop_loss['method'] = sl_method_combo.currentText()
        max_loss_entry = getattr(self, f'{prefix}max_loss_per_trade_entry', None)
        if max_loss_entry:
            stop_loss['max_loss_per_trade'] = float(max_loss_entry.text() or 300)
        atr_mult_entry = getattr(self, f'{prefix}atr_multiplier_entry', None)
        if atr_mult_entry:
            stop_loss['atr_multiplier'] = float(atr_mult_entry.text() or 1.5)
        be_enabled_check = getattr(self, f'{prefix}breakeven_enabled_check', None)
        if be_enabled_check:
            stop_loss['breakeven_enabled'] = be_enabled_check.isChecked()
        be_trigger_entry = getattr(self, f'{prefix}breakeven_trigger_entry', None)
        if be_trigger_entry:
            stop_loss['breakeven_trigger_ratio'] = float(be_trigger_entry.text() or 1.05)
        risk['stop_loss'] = stop_loss
        
        # Profit Targets
        profit_targets = risk.get('profit_targets', {})
        pt_enabled_check = getattr(self, f'{prefix}profit_targets_enabled_check', None)
        if pt_enabled_check:
            profit_targets['enabled'] = pt_enabled_check.isChecked()
        pt1_ratio_entry = getattr(self, f'{prefix}pt1_ratio_entry', None)
        pt1_exit_entry = getattr(self, f'{prefix}pt1_exit_entry', None)
        if pt1_ratio_entry and pt1_exit_entry:
            profit_targets['target_1'] = {
                'ratio': float(pt1_ratio_entry.text() or 1.2),
                'exit_pct': float(pt1_exit_entry.text() or 80.0)
            }
        pt2_ratio_entry = getattr(self, f'{prefix}pt2_ratio_entry', None)
        pt2_exit_entry = getattr(self, f'{prefix}pt2_exit_entry', None)
        if pt2_ratio_entry and pt2_exit_entry:
            profit_targets['target_2'] = {
                'ratio': float(pt2_ratio_entry.text() or 2.0),
                'exit_pct': float(pt2_exit_entry.text() or 50.0)
            }
        pt3_ratio_entry = getattr(self, f'{prefix}pt3_ratio_entry', None)
        pt3_exit_entry = getattr(self, f'{prefix}pt3_exit_entry', None)
        if pt3_ratio_entry and pt3_exit_entry:
            profit_targets['target_3'] = {
                'ratio': float(pt3_ratio_entry.text() or 3.0),
                'exit_pct': float(pt3_exit_entry.text() or 20.0)
            }
        
        # Save profit target reversal config
        reversal_enabled_check = getattr(self, f'{prefix}profit_target_reversal_enabled_check', None)
        reversal_atr_entry = getattr(self, f'{prefix}profit_target_reversal_atr_multiplier_entry', None)
        reversal_pct_entry = getattr(self, f'{prefix}profit_target_reversal_percent_entry', None)
        
        if reversal_enabled_check or reversal_atr_entry or reversal_pct_entry:
            reversal_config = profit_targets.get('reversal', {})
            if reversal_enabled_check:
                reversal_config['enabled'] = reversal_enabled_check.isChecked()
            if reversal_atr_entry:
                reversal_config['atr_multiplier'] = float(reversal_atr_entry.text() or 0.5)
            if reversal_pct_entry:
                reversal_config['percent_threshold'] = float(reversal_pct_entry.text() or 1.0)
            profit_targets['reversal'] = reversal_config
        
        risk['profit_targets'] = profit_targets
        
        # Save profit reversal protection config
        profit_reversal_enabled_check = getattr(self, f'{prefix}profit_reversal_protection_enabled_check', None)
        profit_reversal_min_profit_entry = getattr(self, f'{prefix}profit_reversal_min_profit_entry', None)
        profit_reversal_threshold_entry = getattr(self, f'{prefix}profit_reversal_threshold_entry', None)
        profit_reversal_atr_entry = getattr(self, f'{prefix}profit_reversal_atr_multiplier_entry', None)
        
        if profit_reversal_enabled_check or profit_reversal_min_profit_entry or profit_reversal_threshold_entry or profit_reversal_atr_entry:
            profit_reversal_config = risk.get('profit_reversal_protection', {})
            if profit_reversal_enabled_check:
                profit_reversal_config['enabled'] = profit_reversal_enabled_check.isChecked()
            if profit_reversal_min_profit_entry:
                profit_reversal_config['min_profit'] = float(profit_reversal_min_profit_entry.text() or 100.0)
            if profit_reversal_threshold_entry:
                profit_reversal_config['reversal_threshold'] = float(profit_reversal_threshold_entry.text() or 50.0)
            if profit_reversal_atr_entry:
                profit_reversal_config['atr_multiplier'] = float(profit_reversal_atr_entry.text() or 1.0)
            risk['profit_reversal_protection'] = profit_reversal_config
        
        # Save profit drop protection config
        profit_drop_enabled_check = getattr(self, f'{prefix}profit_drop_protection_enabled_check', None)
        profit_drop_percentage_entry = getattr(self, f'{prefix}profit_drop_percentage_entry', None)
        
        if profit_drop_enabled_check or profit_drop_percentage_entry:
            profit_drop_config = risk.get('profit_drop_protection', {})
            if profit_drop_enabled_check:
                profit_drop_config['enabled'] = profit_drop_enabled_check.isChecked()
            if profit_drop_percentage_entry:
                profit_drop_config['drop_percentage'] = float(profit_drop_percentage_entry.text() or 3.0)
            risk['profit_drop_protection'] = profit_drop_config
        
        # Save unrealized profit drop config
        unrealized_drop_enabled_check = getattr(self, f'{prefix}unrealized_profit_drop_enabled_check', None)
        unrealized_drop_threshold_entry = getattr(self, f'{prefix}unrealized_profit_drop_threshold_entry', None)
        
        if unrealized_drop_enabled_check or unrealized_drop_threshold_entry:
            unrealized_drop_config = risk.get('unrealized_profit_drop', {})
            if unrealized_drop_enabled_check:
                unrealized_drop_config['enabled'] = unrealized_drop_enabled_check.isChecked()
            if unrealized_drop_threshold_entry:
                unrealized_drop_config['percent_threshold'] = float(unrealized_drop_threshold_entry.text() or 4.0)
            risk['unrealized_profit_drop'] = unrealized_drop_config
        
        # Save below average profit exit config
        below_avg_enabled_check = getattr(self, f'{prefix}below_avg_profit_exit_enabled_check', None)
        below_avg_min_profit_entry = getattr(self, f'{prefix}below_avg_profit_min_profit_entry', None)
        
        if below_avg_enabled_check or below_avg_min_profit_entry:
            below_avg_config = risk.get('below_avg_profit_exit', {})
            if below_avg_enabled_check:
                below_avg_config['enabled'] = below_avg_enabled_check.isChecked()
            if below_avg_min_profit_entry:
                below_avg_config['min_profit'] = float(below_avg_min_profit_entry.text() or 50.0)
            risk['below_avg_profit_exit'] = below_avg_config
        
        # Candle Closure Exit (Intraday only)
        if prefix == "intraday_":
            candle_closure_exit = risk.get('candle_closure_exit', {})
            candle_closure_enabled_check = getattr(self, 'intraday_candle_closure_exit_enabled_check', None)
            if candle_closure_enabled_check:
                candle_closure_exit['enabled'] = candle_closure_enabled_check.isChecked()
            candle_closure_resolution_combo = getattr(self, 'intraday_candle_closure_resolution_combo', None)
            if candle_closure_resolution_combo:
                candle_closure_exit['resolution'] = candle_closure_resolution_combo.currentText()
            candle_closure_loss_limit_entry = getattr(self, 'intraday_candle_closure_loss_limit_entry', None)
            if candle_closure_loss_limit_entry:
                try:
                    candle_closure_exit['loss_limit'] = float(candle_closure_loss_limit_entry.text().strip() or 0)
                except ValueError:
                    candle_closure_exit['loss_limit'] = 0.0
            risk['candle_closure_exit'] = candle_closure_exit
        
        # Trailing Stop
        trailing_stop = risk.get('trailing_stop', {})
        ts_enabled_check = getattr(self, f'{prefix}trailing_stop_enabled_check', None)
        if ts_enabled_check:
            trailing_stop['enabled'] = ts_enabled_check.isChecked()
        ts_activation_entry = getattr(self, f'{prefix}ts_activation_entry', None)
        if ts_activation_entry:
            trailing_stop['activation_ratio'] = float(ts_activation_entry.text() or 1.05)
        ts_mult_entry = getattr(self, f'{prefix}ts_multiplier_entry', None)
        if ts_mult_entry:
            trailing_stop['trail_atr_multiplier'] = float(ts_mult_entry.text() or 1.5)
        risk['trailing_stop'] = trailing_stop
        
        # Time Exit
        time_exit = risk.get('time_exit', {})
        te_enabled_check = getattr(self, f'{prefix}time_exit_enabled_check', None)
        if te_enabled_check:
            time_exit['enabled'] = te_enabled_check.isChecked()
        te_max_hold_entry = getattr(self, f'{prefix}time_exit_max_hold_entry', None)
        if te_max_hold_entry:
            time_exit['max_hold_minutes'] = int(te_max_hold_entry.text() or 60)
        te_eod_check = getattr(self, f'{prefix}time_exit_force_eod_check', None)
        if te_eod_check:
            time_exit['force_close_eod'] = te_eod_check.isChecked()
        risk['time_exit'] = time_exit
        
        self.config['risk_management'] = risk
        
        # Save microstructure config (under quant_indicators)
        quant_indicators = self.config.get('quant_indicators', {})
        microstructure = quant_indicators.get('microstructure', {})
        mv_enabled_check = getattr(self, f'{prefix}microstructure_enabled_check', None)
        if mv_enabled_check:
            microstructure['enabled'] = mv_enabled_check.isChecked()
        mv_detect_check = getattr(self, f'{prefix}microstructure_detect_reversals_check', None)
        if mv_detect_check:
            microstructure['detect_reversals'] = mv_detect_check.isChecked()
        mv_threshold_entry = getattr(self, f'{prefix}microstructure_volume_spike_entry', None)
        if mv_threshold_entry:
            microstructure['volume_spike_threshold'] = float(mv_threshold_entry.text() or 1.5)
        quant_indicators['microstructure'] = microstructure
        self.config['quant_indicators'] = quant_indicators
        
        # Ensure backtest config is properly saved
        if not 'backtest' in self.config:
            self.config['backtest'] = {}
        
        # Save config to file
        self.save_config(self.config)
        QMessageBox.information(self, "Success", "Configuration saved successfully!")
    
    def reload_config(self):
        """Reload configuration from file"""
        self.config = self.load_config()
        self.load_config_to_ui()
        QMessageBox.information(self, "Success", "Configuration reloaded!")
    
    def load_backtest_configs(self):
        """Load backtest-specific configurations when switching to backtest tab"""
        # Reload config to ensure backtest tab has latest values
        self.config = self.load_config()
        
        # Load backtest-specific settings
        backtest = self.config.get('backtest', {})
        
        # Load slippage settings
        if hasattr(self, 'backtest_entry_slippage_entry'):
            entry_slippage = backtest.get('entry_slippage', 0.0)
            self.backtest_entry_slippage_entry.setText(str(entry_slippage))
        
        if hasattr(self, 'backtest_exit_slippage_entry'):
            exit_slippage = backtest.get('exit_slippage', 0.0)
            self.backtest_exit_slippage_entry.setText(str(exit_slippage))
        
        # Load initial capital
        if hasattr(self, 'backtest_initial_capital_entry'):
            initial_capital = backtest.get('initial_capital', 20000)
            self.backtest_initial_capital_entry.setText(str(initial_capital))
        
        # Load start date
        if hasattr(self, 'start_date_edit'):
            if 'start_date' in backtest:
                start_date_str = backtest['start_date']
                try:
                    if 'T' in start_date_str or ' ' in start_date_str:
                        start_date_str = start_date_str.split()[0]
                    start_date = QDate.fromString(start_date_str, Qt.ISODate)
                    if not start_date.isValid():
                        start_date = QDate.fromString(start_date_str, "yyyy-MM-dd")
                    if start_date.isValid():
                        self.start_date_edit.setDate(start_date)
                except:
                    pass
        
        # Load end date
        if hasattr(self, 'end_date_edit'):
            if 'end_date' in backtest:
                end_date_str = backtest['end_date']
                try:
                    if 'T' in end_date_str or ' ' in end_date_str:
                        end_date_str = end_date_str.split()[0]
                    end_date = QDate.fromString(end_date_str, Qt.ISODate)
                    if not end_date.isValid():
                        end_date = QDate.fromString(end_date_str, "yyyy-MM-dd")
                    if end_date.isValid():
                        self.end_date_edit.setDate(end_date)
                except:
                    pass
        
        # Load speed
        if hasattr(self, 'speed_combo'):
            speed = backtest.get('speed', 'fast')
            speed_index = 0 if speed.lower() == 'fast' else 1
            self.speed_combo.setCurrentIndex(speed_index)
        
        # Load resolution (with proper format mapping)
        if hasattr(self, 'resolution_combo'):
            resolution = backtest.get('resolution', '30S')
            # Map old format to new format if needed
            resolution_map = {
                '1min': '1',
                '5min': '5',
                '15min': '15S',
                '1hour': '1',
                '1day': '1',
                '30S': '30S',
                '15S': '15S',
                '5S': '5S'
            }
            if resolution in resolution_map:
                resolution = resolution_map[resolution]
            # Available resolutions in combo: ["5S", "15S", "30S", "1", "5"]
            resolutions = ["5S", "15S", "30S", "1", "5"]
            if resolution in resolutions:
                self.resolution_combo.setCurrentIndex(resolutions.index(resolution))
            else:
                # Default to 30S if not found
                self.resolution_combo.setCurrentIndex(2)  # 30S is index 2
                print(f"⚠️  Resolution '{resolution}' not found in combo, defaulting to 30S")
        
        # Also load all other configs (trading, risk, indicators, etc.)
        self.load_config_to_ui()
    
    # Bot control methods
    def start_intraday(self):
        """Start intraday trading"""
        if self.bot_thread and self.bot_thread.isRunning():
            QMessageBox.warning(self, "Warning", "Trading is already running!")
            return
        
        # Save config first
        self.save_config_from_ui()
        
        # Reload config to get latest enabled indicators
        self.config = self.load_config()
        
        # Update LTP table structure with current enabled indicators
        enabled_indicators = self._get_enabled_indicators()
        num_indicator_cols = len(enabled_indicators)
        num_base_cols = 6  # Symbol, LTP, Signal, Change, Confidence, DateTime
        total_cols = num_base_cols + num_indicator_cols
        
        self.ltp_table.setColumnCount(total_cols)
        headers = ["Symbol", "LTP", "Signal", "Change", "Confidence", "DateTime"] + [ind.replace('_', ' ').title() for ind in enabled_indicators]
        self.ltp_table.setHorizontalHeaderLabels(headers)
        self.enabled_indicators_list = enabled_indicators
        
        # Clear previous results
        self.ltp_table.setRowCount(0)
        self.positions_table.setRowCount(0)
        self.trades_table.setRowCount(0)
        self.intraday_summary_table.setRowCount(0)

        # Reset intraday chart data
        self.intraday_live_candle_data = {}
        if self.intraday_live_chart_dialog:
            self.intraday_live_chart_dialog.close()
            self.intraday_live_chart_dialog = None
        if hasattr(self, 'intraday_live_chart_btn'):
            self.intraday_live_chart_btn.setEnabled(False)
        
        # Start bot thread
        self.bot_thread = BotThread(
            self.config_path,
            self.indicators_config_path,
            is_backtest=False
        )
        
        # Connect signals
        self.bot_thread.status_update.connect(self.update_status)
        self.bot_thread.results_update.connect(self.update_ltp_table)
        self.bot_thread.positions_update.connect(self.update_positions_table)
        self.bot_thread.trades_update.connect(self.update_trades_table)
        self.bot_thread.summary_update.connect(self.update_performance_summary)
        self.bot_thread.summary_update.connect(self._throttled_intraday_dashboard_update)
        
        # Also connect results_update to backtest LTP table
        self.bot_thread.results_update.connect(self.update_backtest_ltp_table)
        self.bot_thread.error_occurred.connect(self.handle_error)
        self.bot_thread.finished_signal.connect(self.on_bot_finished)
        self.bot_thread.event_log.connect(self.log_event)
        
        # Log start event
        self.log_event("INFO", "Intraday trading started")
        
        # Update UI
        self.start_intraday_btn.setEnabled(False)
        self.stop_intraday_btn.setEnabled(True)
        
        # Start thread
        self.bot_thread.start()
    
    def stop_intraday(self):
        """Stop intraday trading"""
        if self.bot_thread:
            self.bot_thread.stop()
            self.start_intraday_btn.setEnabled(True)
            self.stop_intraday_btn.setEnabled(False)
    
    def start_backtest(self):
        """Start backtesting"""
        if self.bot_thread and self.bot_thread.isRunning():
            QMessageBox.warning(self, "Warning", "Backtest is already running!")
            return
        
        # Save config first to ensure all backtest settings are persisted
        self.save_config_from_ui()
        
        # Clear previous results
        self.backtest_table.setRowCount(0)
        self.backtest_summary_table.setRowCount(0)
        if hasattr(self, 'backtest_positions_table'):
            self.backtest_positions_table.setRowCount(0)
        
        # Clear dialog tables if they exist
        if hasattr(self, 'backtest_dialog_table'):
            self.backtest_dialog_table.setRowCount(0)
        if hasattr(self, 'backtest_table_data'):
            self.backtest_table_data = []
        if hasattr(self, 'backtest_summary_dialog_table'):
            self.backtest_summary_dialog_table.setRowCount(0)
        
        # Initialize trades DataFrame for export
        self.backtest_trades_df = pd.DataFrame()
        self.metrics_history = {
            'total_pnl': [],
            'equity': [],
            'returns_pct': [],
            'win_rate': [],
            'sharpe_ratio': [],
            'sortino_ratio': [],
            'calmar_ratio': [],
            'max_drawdown': [],
            'profit_factor': [],
            'expectancy': [],
            'avg_win': [],
            'avg_loss': [],
            'iteration': []
        }
        
        # Clear previous candlestick data
        self.backtest_candle_data = {}
        self.backtest_live_candle_data = {}
        
        # Enable live chart button
        if hasattr(self, 'backtest_live_chart_btn'):
            self.backtest_live_chart_btn.setEnabled(True)
        
        # Start bot thread
        self.bot_thread = BotThread(
            self.config_path,
            self.indicators_config_path,
            is_backtest=True
        )
        
        # Connect signals
        self.bot_thread.status_update.connect(self.update_backtest_status)
        self.bot_thread.results_update.connect(self.update_backtest_ltp_table)  # For LTP table
        self.bot_thread.positions_update.connect(self.update_backtest_positions)  # For open positions
        self.bot_thread.trades_update.connect(self.update_backtest_trades)
        self.bot_thread.summary_update.connect(self.update_backtest_summary)
        self.bot_thread.summary_update.connect(self._throttled_backtest_dashboard_update)
        self.bot_thread.error_occurred.connect(self.handle_error)
        self.bot_thread.finished_signal.connect(self.on_backtest_finished)
        self.bot_thread.backtest_data_ready.connect(self.on_backtest_data_ready)
        self.bot_thread.backtest_progress_update.connect(self.on_backtest_progress_update)
        
        # Update UI
        self.start_backtest_btn.setEnabled(False)
        self.stop_backtest_btn.setEnabled(True)
        
        # Start thread
        self.bot_thread.start()
    
    def stop_backtest(self):
        """Stop backtesting"""
        if self.bot_thread:
            self.bot_thread.stop()
            self.start_backtest_btn.setEnabled(True)
            self.stop_backtest_btn.setEnabled(False)
    
    def on_bot_finished(self):
        """Handle bot thread finished"""
        self.start_intraday_btn.setEnabled(True)
        self.stop_intraday_btn.setEnabled(False)

        if hasattr(self, 'intraday_live_chart_btn'):
            self.intraday_live_chart_btn.setEnabled(False)
    
    def on_backtest_finished(self):
        """Handle backtest thread finished"""
        self.start_backtest_btn.setEnabled(True)
        self.stop_backtest_btn.setEnabled(False)
        
        # Disable live chart button
        if hasattr(self, 'backtest_live_chart_btn'):
            self.backtest_live_chart_btn.setEnabled(False)
        
        # Final update to live chart if open
        if self.live_chart_dialog and hasattr(self.live_chart_dialog, 'update_chart'):
            self.live_chart_dialog.update_chart(
                self.backtest_candle_data,
                self._get_symbol_trades_dict()
            )
    
    # Update methods
    def update_status(self, message: str, color: str):
        """Update status label"""
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color};")
    
    def update_backtest_status(self, message: str, color: str):
        """Update backtest status label and progress bar"""
        self.backtest_status_label.setText(message)
        self.backtest_status_label.setStyleSheet(f"color: {color};")
        
        # Update progress if percentage in message
        if "%" in message:
            try:
                # Extract progress percentage from message like "Backtesting... 45% (450/1000 rows)"
                progress_str = message.split("%")[0].split()[-1]
                progress = int(progress_str)
                self.backtest_progress.setValue(progress)
            except:
                pass
    
    def update_ltp_table(self, results: list):
        """Update LTP table with real-time prices and indicator signals."""
        self.last_results = results

        # Update intraday live chart data (if enabled)
        self._update_intraday_live_chart_data(results)
        
        # Delegate to table manager
        self._ltp_table_manager.update(results)
        
        # Sync state from manager back to GUI
        self.ltp_symbol_map = self._ltp_table_manager.ltp_symbol_map
        self.previous_prices = self._ltp_table_manager.previous_prices
        self.ltp_history = self._ltp_table_manager.ltp_history
        self.enabled_indicators_list = self._ltp_table_manager.enabled_indicators_list

    def _update_intraday_live_chart_data(self, results: list):
        """Update intraday candlestick data and refresh live chart."""
        if not results or not isinstance(results, list):
            return

        symbol_data = {}
        for result in results:
            symbol = result.get('symbol')
            df = result.get('dataframe')
            if not symbol or not isinstance(df, pd.DataFrame) or df.empty:
                continue
            symbol_data[symbol] = df

        if not symbol_data:
            return

        self.intraday_live_candle_data = symbol_data

        if hasattr(self, 'intraday_live_chart_btn'):
            self.intraday_live_chart_btn.setEnabled(True)

        if self.intraday_live_chart_dialog and hasattr(self.intraday_live_chart_dialog, 'update_chart'):
            symbol_trades = self._get_intraday_symbol_trades_dict()
            self.intraday_live_chart_dialog.update_chart(symbol_data, symbol_trades)
    
    def update_positions_table(self, positions: dict):
        """Update positions table."""
        # Set last results for LTP lookup
        self._positions_table_manager.set_last_results(self.last_results)
        
        # Delegate to table manager
        self._positions_table_manager.update(positions)
        
        # Sync state
        self.previous_positions = self._positions_table_manager.previous_positions
    
    def _detect_position_changes(self, current_positions: dict):
        """Detect changes in positions and log events"""
        # Check for new positions
        for symbol, position in current_positions.items():
            if symbol not in self.previous_positions:
                # New position opened
                entry_price = position.get('entry_price', 0)
                quantity = position.get('quantity', 0)
                pos_type = position.get('type', 'LONG')
                order_id = position.get('order_id', 'N/A')
                
                # Get lot size and calculation details if available
                lot_info = ""
                if self.bot_thread and hasattr(self.bot_thread, 'bot') and self.bot_thread.bot:
                    engine = self.bot_thread.bot.engine
                    if hasattr(engine, 'get_lot_size'):
                        lot_size = engine.get_lot_size(symbol)
                        lots = int(quantity / lot_size) if lot_size > 0 else 0
                        available_capital = getattr(engine, 'actual_capital', 0)
                        lot_info = f" | Lots: {lots} (lot_size: {lot_size}) | Capital: ₹{available_capital:,.2f}"
                
                self.log_event("ENTRY", f"{symbol} | {pos_type} @ ₹{entry_price:.2f} x {quantity}{lot_info} | Order #{order_id}")
        
        # Check for closed positions
        for symbol, prev_position in self.previous_positions.items():
            if symbol not in current_positions:
                # Position closed
                entry_price = prev_position.get('entry_price', 0)
                quantity = prev_position.get('quantity', 0)
                pos_type = prev_position.get('type', 'LONG')
                order_id = prev_position.get('order_id', 'N/A')
                
                # Try to get exit reason and exit price from order history
                exit_reason = "Position closed"
                exit_price = prev_position.get('current_price', entry_price)
                if self.bot_thread and hasattr(self.bot_thread, 'bot') and self.bot_thread.bot:
                    engine = self.bot_thread.bot.engine
                    if hasattr(engine, 'order_history'):
                        # Find the matching closed order
                        for order in reversed(engine.order_history):
                            if order.get('symbol') == symbol and order.get('status') == 'CLOSED':
                                exit_reason = order.get('exit_reason', 'Position closed')
                                exit_price = order.get('exit_price', exit_price)
                                break
                
                # Calculate PnL
                if pos_type == 'LONG':
                    pnl = (exit_price - entry_price) * quantity
                else:
                    pnl = (entry_price - exit_price) * quantity
                
                self.log_event("EXIT", f"{symbol} | {pos_type} | Entry: ₹{entry_price:.2f} → Exit: ₹{exit_price:.2f} | Qty: {quantity} | PnL: ₹{pnl:+.2f} | Reason: {exit_reason} | Order #{order_id}")
        
        # Check for quantity changes (partial exits)
        for symbol, position in current_positions.items():
            if symbol in self.previous_positions:
                prev_position = self.previous_positions[symbol]
                prev_qty = prev_position.get('quantity', 0)
                curr_qty = position.get('quantity', 0)
                
                if curr_qty < prev_qty:
                    # Partial exit detected
                    exit_qty = prev_qty - curr_qty
                    entry_price = position.get('entry_price', 0)
                    pos_type = position.get('type', 'LONG')
                    current_price = position.get('current_price', entry_price)
                    order_id = position.get('order_id', 'N/A')
                    
                    # Calculate PnL for partial exit
                    if pos_type == 'LONG':
                        pnl = (current_price - entry_price) * exit_qty
                    else:
                        pnl = (entry_price - current_price) * exit_qty
                    
                    # Try to determine exit reason from position data
                    exit_reason = "Partial Exit"
                    if 'last_exit_reason' in position:
                        exit_reason = position.get('last_exit_reason', 'Partial Exit')
                    
                    self.log_event("PARTIAL_EXIT", 
                        f"{symbol} | {pos_type} | Exited {exit_qty}/{prev_qty} @ ₹{current_price:.2f} | "
                        f"Remaining: {curr_qty} | PnL: ₹{pnl:+.2f} | Reason: {exit_reason} | Order #{order_id}")
    
    def calculate_exit_prices(self, position: dict, current_price: float, atr: float, volatility_regime: str):
        """Calculate exit prices for all exit strategies and return as formatted string
        
        This method delegates to the risk module's display method. It does NOT evaluate
        exit conditions - it only calculates what exit prices would be for display purposes.
        """
        try:
            # Check if bot and exit_manager are available
            if not self.bot_thread or not hasattr(self.bot_thread, 'bot') or not self.bot_thread.bot:
                # Fallback: calculate from config directly
                return self._calculate_exit_prices_from_config(position, current_price, atr, volatility_regime)
            
            engine = self.bot_thread.bot.engine
            if not hasattr(engine, 'exit_manager') or not engine.exit_manager:
                # Fallback: calculate from config directly
                return self._calculate_exit_prices_from_config(position, current_price, atr, volatility_regime)
            
            exit_manager = engine.exit_manager
            
            # Get config from engine or self.config
            config = engine.config if hasattr(engine, 'config') and engine.config else self.config
            
            # Delegate to risk module's display method
            return exit_manager.calculate_exit_prices_for_display(
                position=position,
                current_price=current_price,
                atr=atr,
                volatility_regime=volatility_regime,
                config=config
            )
            
        except Exception as e:
            print(f"Error in calculate_exit_prices: {e}")
            import traceback
            traceback.print_exc()
            # Fallback calculation
            return self._calculate_exit_prices_from_config(position, current_price, atr, volatility_regime)
    
    def _calculate_exit_prices_from_config(self, position: dict, current_price: float, atr: float, volatility_regime: str):
        """Fallback method to calculate exit prices directly from config"""
        exit_price_list = []
        exit_labels = []
        
        try:
            entry_price = position.get('entry_price', 0)
            position_type = position.get('type', 'LONG')
            quantity = position.get('quantity', 0)
            
            if entry_price <= 0:
                return "N/A"
            
            risk_config = self.config.get('risk_management', {})
            stop_loss_config = risk_config.get('stop_loss', {})
            profit_targets_config = risk_config.get('profit_targets', {})
            trailing_stop_config = risk_config.get('trailing_stop', {})
            
            # Stop Loss
            stop_pct = stop_loss_config.get('min_stop_pct', 0.8) / 100.0
            if position_type == 'LONG':
                sl_price = entry_price * (1 - stop_pct)
            else:
                sl_price = entry_price * (1 + stop_pct)
            exit_price_list.append(sl_price)
            exit_labels.append('SL')
            
            # Profit Targets
            if profit_targets_config.get('enabled', False):
                stop_distance = abs(entry_price - sl_price)
                quantity = position.get('quantity', 0)
                for i in [1, 2, 3]:
                    target_key = f'target_{i}'
                    if target_key in profit_targets_config:
                        target = profit_targets_config[target_key]
                        ratio = target.get('ratio', 1.5 + (i-1) * 0.5)
                        exit_pct = target.get('exit_pct', 50.0 - (i-1) * 15.0)
                        
                        if position_type == 'LONG':
                            pt_price = entry_price + (stop_distance * ratio)
                            profit_per_unit = pt_price - entry_price
                        else:
                            pt_price = entry_price - (stop_distance * ratio)
                            profit_per_unit = entry_price - pt_price
                        
                        profit_amount = profit_per_unit * quantity * (exit_pct / 100.0)
                        
                        exit_price_list.append(pt_price)
                        exit_labels.append(f'PT{i}({exit_pct:.0f}%→₹{profit_amount:.0f})')
            
            # Trailing Stop
            if trailing_stop_config.get('enabled', False):
                exit_price_list.append(sl_price)  # Use initial stop
                exit_labels.append('TS-Init')
            
            # Microstructure/Micro Volume Exit
            microstructure_config = self.config.get('quant_indicators', {}).get('microstructure', {})
            if microstructure_config.get('enabled', False) and microstructure_config.get('detect_reversals', False):
                # Show current price as conditional exit (exits at current price when volume spike detected)
                exit_price_list.append(current_price)
                exit_labels.append('MV')
            
            # Format
            if exit_price_list:
                price_label_pairs = list(zip(exit_price_list, exit_labels))
                if position_type == 'LONG':
                    price_label_pairs.sort(key=lambda x: x[0])
                else:
                    price_label_pairs.sort(key=lambda x: x[0], reverse=True)
                
                # Return as list of tuples (formatted_string, label) for color coding
                formatted_prices = []
                for price, label in price_label_pairs:
                    formatted_prices.append((f"{label}:{price:.2f}", label))
                return formatted_prices
            else:
                return []
                
        except Exception as e:
            print(f"Error in fallback calculate_exit_prices: {e}")
            return []
    
    def update_trades_table(self, trades_df: pd.DataFrame):
        """Update completed trades table."""
        # Delegate to table manager
        self._trades_table_manager.update(trades_df)
    
    def format_time(self, time_val):
        """Format time value for display"""
        if pd.isna(time_val) or time_val is None:
            return "N/A"
        try:
            if isinstance(time_val, str):
                return time_val
            elif hasattr(time_val, 'strftime'):
                return time_val.strftime("%Y-%m-%d %H:%M:%S")
            else:
                return pd.to_datetime(time_val).strftime("%Y-%m-%d %H:%M:%S")
        except:
            return str(time_val)[:19] if time_val else "N/A"
    
    def update_performance_summary(self, summary: dict):
        """Update intraday performance summary (matching backtest summary structure)"""
        self.intraday_summary_table.setRowCount(0)
        
        # Get initial capital
        backtest_config = self.config.get('backtest', {})
        initial_capital = backtest_config.get('initial_capital', 20000)
        
        # Get closed orders for detailed metrics
        closed_orders = None
        if self.bot_thread and self.bot_thread.bot:
            closed_orders = self.bot_thread.bot.engine.get_closed_orders()
        
        # Calculate comprehensive metrics if we have closed orders
        if closed_orders is not None and not closed_orders.empty:
            metrics = self.calculate_metrics(closed_orders, initial_capital)
            
            # Add summary data from engine
            actual_capital = summary.get('actual_capital', initial_capital)
            hypothetical_capital = summary.get('hypothetical_capital', initial_capital)
            circuit_breaker_savings = summary.get('circuit_breaker_savings', 0)
            paper_trades = summary.get('paper_trades', 0)
            consecutive_losses = summary.get('consecutive_losses', 0)
            paper_trading_mode = summary.get('paper_trading_mode', False)
            
            # Count real trades (non-paper trades)
            real_trades_count = len(closed_orders) - paper_trades if 'paper_trade' in closed_orders.columns else len(closed_orders)
            if 'paper_trade' in closed_orders.columns:
                real_trades_count = len(closed_orders[~closed_orders['paper_trade']])
            else:
                real_trades_count = len(closed_orders)
            
            # Get total charges and net profit from summary
            total_charges = summary.get('total_charges', 0.0)
            total_net_profit = summary.get('total_net_profit', summary.get('total_pnl', 0))
            total_gross_pnl = summary.get('total_gross_pnl', summary.get('total_pnl', 0))
            
            # Add metrics to table with categories (matching backtest structure)
            categories = [
                ("Capital", [
                    ("Initial Capital", f"₹{initial_capital:,.2f}"),
                    ("Current Capital", f"₹{actual_capital:,.2f}"),
                    ("Hypothetical Capital", f"₹{hypothetical_capital:,.2f}"),
                    ("Circuit Breaker Savings", f"₹{circuit_breaker_savings:+,.2f}")
                ]),
                ("Performance", [
                    ("Total PnL", metrics.get("Total PnL", "₹0.00")),
                    ("Return %", metrics.get("Return %", "0.00%")),
                    ("Total Charges", f"₹{total_charges:,.2f}"),
                    ("Gross PnL", f"₹{total_gross_pnl:+,.2f}"),
                    ("Net Profit (After Charges)", f"₹{total_net_profit:+,.2f}")
                ]),
                ("Trades", [
                    ("Total Trades", metrics.get("Total Trades", 0)),
                    ("Win Rate", metrics.get("Win Rate", "0.00%")),
                    ("Paper Trades", str(paper_trades)),
                    ("Real Trades", str(real_trades_count))
                ]),
                ("Wins/Losses", [
                    ("Average Win", metrics.get("Average Win", "₹0.00")),
                    ("Average Loss", metrics.get("Average Loss", "₹0.00")),
                    ("Largest Win", metrics.get("Largest Win", "₹0.00")),
                    ("Largest Loss", metrics.get("Largest Loss", "₹0.00"))
                ]),
                ("Ratios", [
                    ("Profit Factor", metrics.get("Profit Factor", "0.00")),
                    ("Expectancy", metrics.get("Expectancy", "₹0.00")),
                    ("Sharpe Ratio", metrics.get("Sharpe Ratio", "0.00")),
                    ("Max Drawdown", metrics.get("Max Drawdown", "0.00%")),
                    ("Sortino Ratio", metrics.get("Sortino Ratio", "0.00")),
                    ("Calmar Ratio", metrics.get("Calmar Ratio", "0.00"))
                ]),
                ("Circuit Breaker", [
                    ("Consecutive Losses", str(consecutive_losses)),
                    ("Paper Trading Mode", "ACTIVE" if paper_trading_mode else "INACTIVE"),
                    ("Paper Trades Count", str(paper_trades))
                ]),
                ("System Stats", [
                    ("Open Positions", str(summary.get('open_positions', 0))),
                    ("Indicators Registered", str(summary.get('indicators_registered', 0))),
                    ("Total Signals", metrics.get("Total Signals", "N/A")),
                    ("Trades Executed", metrics.get("Trades Executed", 0)),
                    ("Trades Skipped", metrics.get("Trades Skipped", "N/A"))
                ])
            ]
            
            # Calculate and add per-symbol metrics
            symbol_metrics = self.calculate_per_symbol_metrics(closed_orders)
            if symbol_metrics:
                # Add per-symbol metrics category
                per_symbol_list = []
                for symbol, sym_metrics in symbol_metrics.items():
                    # Shorten symbol name for display
                    symbol_display = symbol.split(':')[-1] if ':' in symbol else symbol
                    per_symbol_list.append((f"📊 {symbol_display}", ""))
                    per_symbol_list.append(("  Total Orders", str(sym_metrics.get('total_orders', 0))))
                    per_symbol_list.append(("  Total PnL", f"₹{sym_metrics.get('total_pnl', 0):+,.2f}"))
                    per_symbol_list.append(("  Profit Orders", str(sym_metrics.get('profit_orders', 0))))
                    per_symbol_list.append(("  Loss Orders", str(sym_metrics.get('loss_orders', 0))))
                    per_symbol_list.append(("  Win Rate", f"{sym_metrics.get('win_rate', 0):.2f}%"))
                    per_symbol_list.append(("  Avg Win", f"₹{sym_metrics.get('avg_win', 0):,.2f}"))
                    per_symbol_list.append(("  Avg Loss", f"₹{sym_metrics.get('avg_loss', 0):,.2f}"))
                    per_symbol_list.append(("  Largest Win", f"₹{sym_metrics.get('largest_win', 0):,.2f}"))
                    per_symbol_list.append(("  Largest Loss", f"₹{sym_metrics.get('largest_loss', 0):,.2f}"))
                    per_symbol_list.append(("  Profit Factor", f"{sym_metrics.get('profit_factor', 0):.2f}"))
                    per_symbol_list.append(("  Expectancy", f"₹{sym_metrics.get('expectancy', 0):+,.2f}"))
                    per_symbol_list.append(("  Paper Trades", str(sym_metrics.get('paper_trades', 0))))
                    per_symbol_list.append(("  Real Trades", str(sym_metrics.get('real_trades', 0))))
                    per_symbol_list.append(("", ""))  # Empty row separator
                
                categories.append(("Per-Symbol Metrics", per_symbol_list))
            
            for category, metric_list in categories:
                # Add category header
                row = self.intraday_summary_table.rowCount()
                self.intraday_summary_table.insertRow(row)
                category_item = QTableWidgetItem(category)
                category_item.setFont(QFont("Arial", 9, QFont.Bold))
                category_item.setBackground(QColor(232, 232, 232))
                self.intraday_summary_table.setItem(row, 0, category_item)
                self.intraday_summary_table.setItem(row, 1, QTableWidgetItem(""))
                
                # Add metrics
                for metric_name, metric_value in metric_list:
                    row = self.intraday_summary_table.rowCount()
                    self.intraday_summary_table.insertRow(row)
                    self.intraday_summary_table.setItem(row, 0, QTableWidgetItem(metric_name))
                    
                    value_item = QTableWidgetItem(str(metric_value))
                    
                    # Color code text
                    if "PnL" in metric_name or "Return" in metric_name or "Savings" in metric_name or "Expectancy" in metric_name:
                        # Try to extract numeric value for coloring
                        try:
                            if "₹" in str(metric_value):
                                num_val = float(str(metric_value).replace("₹", "").replace(",", "").replace("+", ""))
                            elif "%" in str(metric_value):
                                num_val = float(str(metric_value).replace("%", ""))
                            else:
                                num_val = float(metric_value)
                            
                            if num_val > 0:
                                value_item.setForeground(QColor(34, 139, 34))  # Green text
                            elif num_val < 0:
                                value_item.setForeground(QColor(220, 20, 60))  # Red text
                        except:
                            pass
                    elif "📊" in metric_name or "Symbol:" in metric_name:
                        # Symbol header - make it bold and colored
                        metric_item = self.intraday_summary_table.item(row, 0)
                        if metric_item:
                            metric_item.setFont(QFont("Arial", 9, QFont.Bold))
                            metric_item.setForeground(QColor(30, 144, 255))  # Blue text
                        value_item.setForeground(QColor(30, 144, 255))  # Blue text
                    elif metric_name.startswith("  "):
                        # Indented metric - use slightly different styling
                        metric_item = self.intraday_summary_table.item(row, 0)
                        if metric_item:
                            metric_item.setForeground(QColor(180, 180, 180))  # Light gray
                        # Color code the value based on content
                        if "PnL" in metric_name or "Expectancy" in metric_name:
                            try:
                                if "₹" in str(metric_value):
                                    num_val = float(str(metric_value).replace("₹", "").replace(",", "").replace("+", ""))
                                else:
                                    num_val = float(metric_value)
                                if num_val > 0:
                                    value_item.setForeground(QColor(34, 139, 34))  # Green
                                elif num_val < 0:
                                    value_item.setForeground(QColor(220, 20, 60))  # Red
                            except:
                                pass
                        elif "Win Rate" in metric_name or "Profit Factor" in metric_name:
                            try:
                                num_val = float(str(metric_value).replace("%", ""))
                                if num_val > 0:
                                    value_item.setForeground(QColor(30, 144, 255))  # Blue
                            except:
                                pass
                    elif "Win Rate" in metric_name or "Profit Factor" in metric_name:
                        try:
                            value_str = str(metric_value).replace("%", "")
                            if value_str and value_str != "N/A":
                                num_value = float(value_str)
                                if num_value > 0:
                                    value_item.setForeground(QColor(30, 144, 255))  # Blue text
                        except:
                            pass
                    elif "ACTIVE" in str(metric_value):
                        value_item.setForeground(QColor(255, 215, 0))  # Gold/Yellow for active
                    elif "INACTIVE" in str(metric_value):
                        value_item.setForeground(QColor(128, 128, 128))  # Gray for inactive
                    
                    self.intraday_summary_table.setItem(row, 1, value_item)
        else:
            # No trades yet - show basic info
            row = self.intraday_summary_table.rowCount()
            self.intraday_summary_table.insertRow(row)
            self.intraday_summary_table.setItem(row, 0, QTableWidgetItem("Initial Capital"))
            self.intraday_summary_table.setItem(row, 1, QTableWidgetItem(f"₹{initial_capital:,.2f}"))
    
    def calculate_metrics(self, closed_orders: pd.DataFrame, initial_capital: float) -> dict:
        """Calculate comprehensive metrics from closed orders"""
        if closed_orders.empty:
            return {}
        
        total_trades = len(closed_orders)
        wins = closed_orders[closed_orders['pnl'] > 0]
        losses = closed_orders[closed_orders['pnl'] < 0]
        
        total_pnl = closed_orders['pnl'].sum()
        current_capital = initial_capital + total_pnl
        return_pct = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0
        
        win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
        avg_win = wins['pnl'].mean() if len(wins) > 0 else 0
        avg_loss = losses['pnl'].mean() if len(losses) > 0 else 0
        largest_win = wins['pnl'].max() if len(wins) > 0 else 0
        largest_loss = losses['pnl'].min() if len(losses) > 0 else 0
        
        profit_factor = abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 and losses['pnl'].sum() != 0 else 0
        expectancy = (avg_win * (len(wins) / total_trades) + avg_loss * (len(losses) / total_trades)) if total_trades > 0 else 0
        
        # Calculate Sharpe Ratio (simplified)
        returns = closed_orders['pnl'] / initial_capital if initial_capital > 0 else closed_orders['pnl']
        sharpe_ratio = (returns.mean() / returns.std() * (252 ** 0.5)) if len(returns) > 1 and returns.std() > 0 else 0
        
        # Calculate Max Drawdown
        cumulative = (initial_capital + closed_orders['pnl'].cumsum()).values
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max * 100
        max_drawdown = drawdown.min() if len(drawdown) > 0 else 0
        
        # Calculate Sortino Ratio
        downside_returns = returns[returns < 0]
        sortino_ratio = (returns.mean() / downside_returns.std() * (252 ** 0.5)) if len(downside_returns) > 1 and downside_returns.std() > 0 else 0
        
        # Calculate Calmar Ratio
        calmar_ratio = (return_pct / abs(max_drawdown)) if max_drawdown != 0 else 0
        
        return {
            "Initial Capital": f"₹{initial_capital:,.2f}",
            "Current Capital": f"₹{current_capital:,.2f}",
            "Total PnL": f"₹{total_pnl:,.2f}",
            "Return %": f"{return_pct:.2f}%",
            "Total Trades": total_trades,
            "Win Rate": f"{win_rate:.2f}%",
            "Average Win": f"₹{avg_win:,.2f}",
            "Average Loss": f"₹{avg_loss:,.2f}",
            "Largest Win": f"₹{largest_win:,.2f}",
            "Largest Loss": f"₹{largest_loss:,.2f}",
            "Profit Factor": f"{profit_factor:.2f}",
            "Expectancy": f"₹{expectancy:,.2f}",
            "Sharpe Ratio": f"{sharpe_ratio:.2f}",
            "Max Drawdown": f"{max_drawdown:.2f}%",
            "Sortino Ratio": f"{sortino_ratio:.2f}",
            "Calmar Ratio": f"{calmar_ratio:.2f}",
            "Total Signals": "N/A",  # Would need to track this
            "Trades Executed": total_trades,
            "Trades Skipped": "N/A"
        }
    
    def calculate_per_symbol_metrics(self, closed_orders: pd.DataFrame) -> dict:
        """Calculate per-symbol trading metrics"""
        if closed_orders.empty or 'symbol' not in closed_orders.columns:
            return {}
        
        symbol_metrics = {}
        
        # Group by symbol
        for symbol in closed_orders['symbol'].unique():
            symbol_orders = closed_orders[closed_orders['symbol'] == symbol]
            
            # Filter real trades (exclude paper trades if paper_trade column exists)
            if 'paper_trade' in symbol_orders.columns:
                real_trades = symbol_orders[~symbol_orders['paper_trade'].fillna(False)]
                paper_trades = symbol_orders[symbol_orders['paper_trade'].fillna(False)]
            else:
                real_trades = symbol_orders
                paper_trades = pd.DataFrame()
            
            # Calculate metrics for real trades
            total_orders = len(real_trades)
            if total_orders == 0:
                continue
            
            wins = real_trades[real_trades['pnl'] > 0]
            losses = real_trades[real_trades['pnl'] < 0]
            
            total_pnl = real_trades['pnl'].sum()
            profit_orders = len(wins)
            loss_orders = len(losses)
            win_rate = (profit_orders / total_orders * 100) if total_orders > 0 else 0
            
            avg_win = wins['pnl'].mean() if len(wins) > 0 else 0
            avg_loss = losses['pnl'].mean() if len(losses) > 0 else 0
            largest_win = wins['pnl'].max() if len(wins) > 0 else 0
            largest_loss = losses['pnl'].min() if len(losses) > 0 else 0
            
            # Calculate profit factor
            total_wins = wins['pnl'].sum() if len(wins) > 0 else 0
            total_losses = abs(losses['pnl'].sum()) if len(losses) > 0 else 0
            profit_factor = (total_wins / total_losses) if total_losses > 0 else 0
            
            # Calculate expectancy
            expectancy = (avg_win * (profit_orders / total_orders) + avg_loss * (loss_orders / total_orders)) if total_orders > 0 else 0
            
            symbol_metrics[symbol] = {
                'total_orders': total_orders,
                'total_pnl': float(total_pnl),
                'profit_orders': profit_orders,
                'loss_orders': loss_orders,
                'win_rate': float(win_rate),
                'avg_win': float(avg_win),
                'avg_loss': float(avg_loss),
                'largest_win': float(largest_win),
                'largest_loss': float(largest_loss),
                'profit_factor': float(profit_factor),
                'expectancy': float(expectancy),
                'paper_trades': len(paper_trades),
                'real_trades': total_orders
            }
        
        # Sort by total PnL (descending)
        symbol_metrics = dict(sorted(symbol_metrics.items(), key=lambda x: x[1]['total_pnl'], reverse=True))
        
        return symbol_metrics
    
    def update_backtest_trades(self, trades_df: pd.DataFrame):
        """Update backtest trades table using modular component."""
        self._backtest_trades_manager.update(trades_df)
        self.backtest_trades_df = trades_df
    
    def export_backtest_results_to_csv(self):
        """Export backtest results to CSV file"""
        try:
            # Get closed orders from engine if available
            if self.bot_thread and self.bot_thread.bot:
                trades_df = self.bot_thread.bot.engine.get_closed_orders()
            elif hasattr(self, 'backtest_trades_df') and self.backtest_trades_df is not None:
                trades_df = self.backtest_trades_df
            else:
                QMessageBox.warning(self, "No Data", "No backtest results available to export. Please run a backtest first.")
                return
            
            if trades_df.empty:
                QMessageBox.warning(self, "No Data", "No backtest results available to export. Please run a backtest first.")
                return
            
            # Get save file path
            default_filename = f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Backtest Results to CSV",
                default_filename,
                "CSV Files (*.csv);;All Files (*)"
            )
            
            if not file_path:
                return  # User cancelled
            
            # Prepare data for export with all columns
            export_data = []
            for idx, row in trades_df.iterrows():
                # Handle quantity
                trade_quantity = row.get('quantity', 0)
                if trade_quantity <= 0:
                    trade_quantity = row.get('original_quantity', 0)
                    if trade_quantity <= 0:
                        default_qty = self.config.get('trading', {}).get('default_quantity', None)
                        trade_quantity = default_qty if default_qty and default_qty > 0 else 25
                
                # Calculate return percentage
                entry_price = float(row['entry_price'])
                exit_price = float(row['exit_price'])
                
                if row['type'] == 'LONG':
                    return_pct = ((exit_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
                    calculated_pnl = (exit_price - entry_price) * trade_quantity
                else:  # SHORT
                    return_pct = ((entry_price - exit_price) / entry_price * 100) if entry_price > 0 else 0
                    calculated_pnl = (entry_price - exit_price) * trade_quantity
                
                # Use calculated PnL if stored PnL is 0
                stored_pnl = float(row.get('pnl', 0))
                if abs(stored_pnl) < 0.01 and abs(return_pct) > 0.01:
                    pnl = calculated_pnl
                else:
                    pnl = stored_pnl
                
                # Get max and min profit
                max_profit = float(row.get('max_profit', 0.0))
                min_profit = float(row.get('min_profit', 0.0))
                
                # Calculate max/min profit if not stored
                if abs(max_profit) < 0.01 and abs(min_profit) < 0.01:
                    if row['type'] == 'LONG':
                        highest = row.get('highest_price', exit_price)
                        lowest = row.get('lowest_price', exit_price)
                        max_profit = (highest - entry_price) * trade_quantity
                        min_profit = (lowest - entry_price) * trade_quantity
                    else:  # SHORT
                        highest = row.get('highest_price', exit_price)
                        lowest = row.get('lowest_price', exit_price)
                        max_profit = (entry_price - lowest) * trade_quantity
                        min_profit = (entry_price - highest) * trade_quantity
                
                # Get average profit and loss
                avg_profit = float(row.get('avg_profit', 0.0))
                avg_loss = float(row.get('avg_loss', 0.0))
                
                # Capital used
                capital_used = entry_price * trade_quantity
                
                # Format times
                entry_time = row.get('entry_time')
                if pd.notna(entry_time):
                    if isinstance(entry_time, str):
                        entry_time_str = entry_time
                    else:
                        entry_time_str = entry_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(entry_time, 'strftime') else str(entry_time)
                else:
                    entry_time_str = 'N/A'
                
                exit_time = row.get('exit_time')
                if pd.notna(exit_time):
                    if isinstance(exit_time, str):
                        exit_time_str = exit_time
                    else:
                        exit_time_str = exit_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(exit_time, 'strftime') else str(exit_time)
                else:
                    exit_time_str = 'N/A'
                
                # Get exit reason
                exit_reason = row.get('exit_reason', 'N/A')
                if pd.isna(exit_reason):
                    exit_reason = 'N/A'
                
                # Trade type
                is_paper_trade = row.get('paper_trade', False)
                if pd.isna(is_paper_trade):
                    is_paper_trade = False
                trade_type = "PAPER" if is_paper_trade else "REAL"
                
                export_data.append({
                    'Order ID': row['order_id'],
                    'Symbol': row['symbol'],
                    'Type': row['type'],
                    'Trade Type': trade_type,
                    'Entry Price': f"{entry_price:.2f}",
                    'Exit Price': f"{exit_price:.2f}",
                    'Quantity': trade_quantity,
                    'PnL': f"{pnl:+.2f}",
                    'Return %': f"{return_pct:+.2f}%",
                    'Max Profit': f"{max_profit:+.2f}",
                    'Min Profit': f"{min_profit:+.2f}",
                    'Avg Profit': f"{avg_profit:+.2f}" if avg_profit != 0 else "-",
                    'Avg Loss': f"{avg_loss:+.2f}" if avg_loss != 0 else "-",
                    'Capital Used': int(capital_used),
                    'Entry Time': entry_time_str,
                    'Exit Time': exit_time_str,
                    'Exit Reason': exit_reason
                })
            
            # Create DataFrame and export to CSV
            export_df = pd.DataFrame(export_data)
            export_df.to_csv(file_path, index=False)
            
            QMessageBox.information(self, "Success", f"Backtest results exported successfully to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export backtest results: {e}")
            import traceback
            print(traceback.format_exc())
    
    def on_backtest_data_ready(self, symbol_data: dict):
        """
        Handle backtest candlestick data being ready for chart viewing.
        
        Args:
            symbol_data: Dictionary mapping symbol to DataFrame with OHLCV data
        """
        self.backtest_candle_data = symbol_data
        
        # Enable the View Charts button
        if hasattr(self, 'backtest_view_charts_btn'):
            self.backtest_view_charts_btn.setEnabled(True)
        
        print(f"✅ Candlestick data loaded for {len(symbol_data)} symbols")
    
    def on_backtest_progress_update(self, progressive_data: dict, trades_df: pd.DataFrame):
        """
        Handle progressive backtest data updates for live chart.
        
        Args:
            progressive_data: Dictionary mapping symbol to progressive DataFrame
            trades_df: Current trades DataFrame
        """
        self.backtest_live_candle_data = progressive_data
        
        # Update live chart if open
        if self.live_chart_dialog and hasattr(self.live_chart_dialog, 'update_chart'):
            # Organize trades by symbol
            symbol_trades = {}
            if trades_df is not None and not trades_df.empty:
                for symbol in progressive_data.keys():
                    symbol_trades_df = trades_df[trades_df['symbol'] == symbol] if 'symbol' in trades_df.columns else pd.DataFrame()
                    
                    trades_list = []
                    if not symbol_trades_df.empty:
                        for _, trade in symbol_trades_df.iterrows():
                            trades_list.append(trade.to_dict())
                    
                    symbol_trades[symbol] = trades_list
            else:
                for symbol in progressive_data.keys():
                    symbol_trades[symbol] = []
            
            # Update the live chart
            self.live_chart_dialog.update_chart(progressive_data, symbol_trades)
    
    def view_backtest_charts(self):
        """Open chart viewer dialog to visualize backtest data with trade markers."""
        try:
            # Import chart dialog
            from trading_system.ui.dialogs.chart_viewer_dialog import MultiSymbolChartDialog
            
            if not self.backtest_candle_data:
                QMessageBox.warning(
                    self,
                    "No Chart Data",
                    "No candlestick data available. Please run a backtest first."
                )
                return
            
            # Get trades data
            trades_df = None
            if hasattr(self, 'backtest_trades_df') and self.backtest_trades_df is not None:
                trades_df = self.backtest_trades_df
            elif self.bot_thread and self.bot_thread.bot:
                trades_df = self.bot_thread.bot.engine.get_closed_orders()
            
            # Organize trades by symbol
            symbol_trades = {}
            if trades_df is not None and not trades_df.empty:
                for symbol in self.backtest_candle_data.keys():
                    symbol_trades_df = trades_df[trades_df['symbol'] == symbol] if 'symbol' in trades_df.columns else pd.DataFrame()
                    
                    # Convert to list of dicts
                    trades_list = []
                    if not symbol_trades_df.empty:
                        for _, trade in symbol_trades_df.iterrows():
                            trades_list.append(trade.to_dict())
                    
                    symbol_trades[symbol] = trades_list
            else:
                # No trades, create empty lists for all symbols
                for symbol in self.backtest_candle_data.keys():
                    symbol_trades[symbol] = []
            
            # Open multi-symbol chart dialog
            chart_dialog = MultiSymbolChartDialog(
                parent=self,
                symbol_data=self.backtest_candle_data,
                symbol_trades=symbol_trades
            )
            chart_dialog.exec()
            
        except ImportError as e:
            QMessageBox.warning(
                self, 
                "Charts Not Available",
                f"Chart viewing requires PySide6-WebEngine.\n\nInstall with: pip install PySide6-WebEngine\n\nError: {e}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Chart Error",
                f"Failed to open chart viewer:\n{str(e)}"
            )
            print(f"Chart viewer error: {e}")
            import traceback
            traceback.print_exc()

    def _get_intraday_symbol_trades_dict(self) -> dict:
        """Get organized trades by symbol for intraday live charts."""
        symbol_trades = {}
        trades_df = None

        if self.bot_thread and self.bot_thread.bot:
            trades_df = self.bot_thread.bot.engine.get_closed_orders()

        symbols = list(self.intraday_live_candle_data.keys())
        if not symbols:
            symbols = self.config.get('symbols', [])

        if trades_df is not None and not trades_df.empty:
            for symbol in symbols:
                symbol_trades_df = trades_df[trades_df['symbol'] == symbol] if 'symbol' in trades_df.columns else pd.DataFrame()

                trades_list = []
                if not symbol_trades_df.empty:
                    for _, trade in symbol_trades_df.iterrows():
                        trades_list.append(trade.to_dict())

                symbol_trades[symbol] = trades_list
        else:
            for symbol in symbols:
                symbol_trades[symbol] = []

        return symbol_trades
    
    def _get_symbol_trades_dict(self) -> dict:
        """Get organized trades by symbol."""
        symbol_trades = {}
        trades_df = None
        
        if hasattr(self, 'backtest_trades_df') and self.backtest_trades_df is not None:
            trades_df = self.backtest_trades_df
        elif self.bot_thread and self.bot_thread.bot:
            trades_df = self.bot_thread.bot.engine.get_closed_orders()
        
        # Get symbols from candle data
        symbols = self.backtest_live_candle_data.keys() if self.backtest_live_candle_data else self.backtest_candle_data.keys()
        
        if trades_df is not None and not trades_df.empty:
            for symbol in symbols:
                symbol_trades_df = trades_df[trades_df['symbol'] == symbol] if 'symbol' in trades_df.columns else pd.DataFrame()
                
                trades_list = []
                if not symbol_trades_df.empty:
                    for _, trade in symbol_trades_df.iterrows():
                        trades_list.append(trade.to_dict())
                
                symbol_trades[symbol] = trades_list
        else:
            for symbol in symbols:
                symbol_trades[symbol] = []
        
        return symbol_trades

    def view_intraday_live_chart(self):
        """Open live chart viewer that updates during intraday trading."""
        try:
            from trading_system.ui.dialogs.live_chart_dialog import LiveChartDialog

            if not self.intraday_live_candle_data:
                QMessageBox.warning(
                    self,
                    "No Chart Data",
                    "Please start intraday trading first to view live charts."
                )
                return

            symbol_trades = self._get_intraday_symbol_trades_dict()

            if self.intraday_live_chart_dialog is None:
                self.intraday_live_chart_dialog = LiveChartDialog(
                    parent=self,
                    symbol_data=self.intraday_live_candle_data,
                    symbol_trades=symbol_trades
                )
                self.intraday_live_chart_dialog.finished.connect(self._on_intraday_live_chart_closed)
                self.intraday_live_chart_dialog.show()
            else:
                self.intraday_live_chart_dialog.update_chart(self.intraday_live_candle_data, symbol_trades)
                self.intraday_live_chart_dialog.raise_()
                self.intraday_live_chart_dialog.activateWindow()

        except ImportError as e:
            QMessageBox.warning(
                self,
                "Charts Not Available",
                f"Chart viewing requires PySide6-WebEngine.\n\nInstall with: pip install PySide6-WebEngine\n\nError: {e}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Chart Error",
                f"Failed to open live chart viewer:\n{str(e)}"
            )
            print(f"Live chart viewer error: {e}")
            import traceback
            traceback.print_exc()
    
    def view_live_backtest_chart(self):
        """Open live chart viewer that updates during backtesting."""
        try:
            from trading_system.ui.dialogs.live_chart_dialog import LiveChartDialog
            
            if not self.backtest_live_candle_data and not self.backtest_candle_data:
                QMessageBox.warning(
                    self,
                    "No Chart Data",
                    "Please start a backtest first to view live charts."
                )
                return
            
            # Use progressive data if available, otherwise use full data
            chart_data = self.backtest_live_candle_data if self.backtest_live_candle_data else self.backtest_candle_data
            
            # Get trades
            symbol_trades = self._get_symbol_trades_dict()
            
            # Create or update live chart dialog
            if self.live_chart_dialog is None:
                self.live_chart_dialog = LiveChartDialog(
                    parent=self,
                    symbol_data=chart_data,
                    symbol_trades=symbol_trades
                )
                self.live_chart_dialog.finished.connect(self._on_live_chart_closed)
                self.live_chart_dialog.show()
            else:
                # Update existing dialog
                self.live_chart_dialog.update_chart(chart_data, symbol_trades)
                self.live_chart_dialog.raise_()
                self.live_chart_dialog.activateWindow()
            
        except ImportError as e:
            QMessageBox.warning(
                self, 
                "Charts Not Available",
                f"Chart viewing requires PySide6-WebEngine.\n\nInstall with: pip install PySide6-WebEngine\n\nError: {e}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Chart Error",
                f"Failed to open live chart viewer:\n{str(e)}"
            )
            print(f"Live chart viewer error: {e}")
            import traceback
            traceback.print_exc()

    def _on_intraday_live_chart_closed(self):
        """Handle intraday live chart dialog being closed."""
        self.intraday_live_chart_dialog = None
    
    def _on_live_chart_closed(self):
        """Handle live chart dialog being closed."""
        self.live_chart_dialog = None
    
    def update_backtest_positions(self, positions: dict):
        """Update backtest open positions table with max and min profit"""
        if not hasattr(self, 'backtest_positions_table'):
            return
        
        self.backtest_positions_table.setRowCount(0)
        
        if not positions:
            return
        
        # Calculate total capital used across ALL open positions first
        total_capital_used_all = 0
        for pos_symbol, pos_data in positions.items():
            pos_entry_price = pos_data.get('entry_price', 0)
            pos_quantity = pos_data.get('quantity', 0)
            total_capital_used_all += pos_entry_price * pos_quantity
        
        # Get initial capital (base capital, not including profits)
        initial_capital = self.config.get('backtest', {}).get('initial_capital', 20000)
        
        # Get actual capital from engine (includes profits/losses from closed trades)
        actual_capital = initial_capital
        if self.bot_thread and self.bot_thread.bot:
            actual_capital = self.bot_thread.bot.engine.actual_capital
        
        # Available capital should NOT include profits - it should not go beyond initial capital
        # If actual_capital > initial_capital (profits): use initial_capital
        # If actual_capital < initial_capital (losses): use actual_capital (losses reduce available capital)
        current_capital = min(initial_capital, actual_capital)
        
        # Available capital = current capital (capped at initial, minus losses) - total capital used in open positions
        available_capital_base = max(0, current_capital - total_capital_used_all)
        
        # Get closed orders to get max/min profit for completed trades
        closed_orders_df = None
        if self.bot_thread and self.bot_thread.bot:
            closed_orders_df = self.bot_thread.bot.engine.get_closed_orders()
        
        for symbol, position in positions.items():
            symbol_short = symbol.split(':')[-1]
            entry_price = position.get('entry_price', 0)
            quantity = position.get('quantity', 0)
            position_type = position.get('type', 'LONG')
            current_price = position.get('current_price', entry_price)
            entry_time = position.get('entry_time', None)
            is_paper_trade = position.get('paper_trade', False)

            # Adjust quantity to fit available capital per trade (backtest)
            lot_size = None
            if self.bot_thread and self.bot_thread.bot and hasattr(self.bot_thread.bot, 'engine'):
                lot_size = self.bot_thread.bot.engine.get_lot_size(symbol)
            if not lot_size or lot_size <= 0:
                lot_size = self.config.get('lot_sizes', {}).get('default', 0)
            if lot_size and lot_size > 0 and entry_price > 0:
                backtest_config = self.config.get('backtest', {})
                initial_capital = backtest_config.get('initial_capital', 20000)
                risk_config = self.config.get('risk_management', {})
                capital_pct = risk_config.get('capital_percentage_per_trade_backtest', 50.0) / 100.0
                max_capital_per_trade = initial_capital * capital_pct
                max_lots = int(max_capital_per_trade / (entry_price * lot_size))
                max_quantity = max_lots * lot_size
                if max_quantity > 0 and quantity > max_quantity:
                    quantity = max_quantity
            
            # Calculate current PnL
            if position_type == 'LONG':
                current_pnl = (current_price - entry_price) * quantity
            else:  # SHORT
                current_pnl = (entry_price - current_price) * quantity
            
            # Get max and min profit from position
            max_profit = position.get('max_profit', 0.0)
            min_profit = position.get('min_profit', 0.0)
            avg_profit = position.get('avg_profit', 0.0)
            avg_loss = position.get('avg_loss', 0.0)
            
            # If not set, calculate from highest/lowest prices
            if abs(max_profit) < 0.01 and abs(min_profit) < 0.01:
                highest_price = position.get('highest_price', current_price)
                lowest_price = position.get('lowest_price', current_price)
                if position_type == 'LONG':
                    max_profit = (highest_price - entry_price) * quantity
                    min_profit = (lowest_price - entry_price) * quantity
                else:  # SHORT
                    max_profit = (entry_price - lowest_price) * quantity
                    min_profit = (entry_price - highest_price) * quantity
            
            # Add row
            row = self.backtest_positions_table.rowCount()
            self.backtest_positions_table.insertRow(row)
            
            # Symbol
            self.backtest_positions_table.setItem(row, 0, QTableWidgetItem(symbol_short))
            
            # Type
            self.backtest_positions_table.setItem(row, 1, QTableWidgetItem(position_type))
            
            # Trade Type
            trade_type = "PAPER" if is_paper_trade else "REAL"
            trade_type_item = QTableWidgetItem(trade_type)
            if is_paper_trade:
                trade_type_item.setForeground(QColor(255, 215, 0))  # Gold/Yellow
            else:
                trade_type_item.setForeground(QColor(255, 255, 255))  # White
            self.backtest_positions_table.setItem(row, 2, trade_type_item)
            
            # Entry
            self.backtest_positions_table.setItem(row, 3, QTableWidgetItem(f"{entry_price:.2f}"))
            
            # Quantity
            self.backtest_positions_table.setItem(row, 4, QTableWidgetItem(str(quantity)))
            
            # LTP
            self.backtest_positions_table.setItem(row, 5, QTableWidgetItem(f"{current_price:.2f}"))
            
            # Current PnL
            pnl_item = QTableWidgetItem(f"{current_pnl:+.2f}")
            if current_pnl > 0:
                pnl_item.setForeground(QColor(34, 139, 34))  # Green
            elif current_pnl < 0:
                pnl_item.setForeground(QColor(220, 20, 60))  # Red
            else:
                pnl_item.setForeground(QColor(255, 255, 255))  # White
            self.backtest_positions_table.setItem(row, 6, pnl_item)
            
            # Max Profit
            max_profit_item = QTableWidgetItem(f"{max_profit:+.2f}")
            if max_profit > 0:
                max_profit_item.setForeground(QColor(34, 139, 34))  # Green
            elif max_profit < 0:
                max_profit_item.setForeground(QColor(220, 20, 60))  # Red
            else:
                max_profit_item.setForeground(QColor(255, 255, 255))  # White
            self.backtest_positions_table.setItem(row, 7, max_profit_item)
            
            # Min Profit
            min_profit_item = QTableWidgetItem(f"{min_profit:+.2f}")
            if min_profit > 0:
                min_profit_item.setForeground(QColor(34, 139, 34))  # Green
            elif min_profit < 0:
                min_profit_item.setForeground(QColor(220, 20, 60))  # Red
            else:
                min_profit_item.setForeground(QColor(255, 255, 255))  # White
            self.backtest_positions_table.setItem(row, 8, min_profit_item)
            
            # Avg Profit
            avg_profit_item = QTableWidgetItem(f"{avg_profit:+.2f}" if avg_profit != 0 else "-")
            if avg_profit > 0:
                avg_profit_item.setForeground(QColor(34, 139, 34))  # Green
            elif avg_profit < 0:
                avg_profit_item.setForeground(QColor(220, 20, 60))  # Red
            else:
                avg_profit_item.setForeground(QColor(255, 255, 255))  # White
            self.backtest_positions_table.setItem(row, 9, avg_profit_item)
            
            # Avg Loss
            avg_loss_item = QTableWidgetItem(f"{avg_loss:+.2f}" if avg_loss != 0 else "-")
            if avg_loss > 0:
                avg_loss_item.setForeground(QColor(34, 139, 34))  # Green
            elif avg_loss < 0:
                avg_loss_item.setForeground(QColor(220, 20, 60))  # Red
            else:
                avg_loss_item.setForeground(QColor(255, 255, 255))  # White
            self.backtest_positions_table.setItem(row, 10, avg_loss_item)
            
            # Capital Used (only show used capital, not available capital)
            capital_used = entry_price * quantity
            
            # Calculate what capital was available when this position was opened
            # Available capital = current capital (after profits/losses) - capital used by OTHER positions (not including this one)
            capital_used_by_others = total_capital_used_all - capital_used
            available_capital_when_opened = max(0, current_capital - capital_used_by_others)
            
            # Check if capital was insufficient when this position was opened
            if capital_used > available_capital_when_opened:
                capital_display = "Capital not available"
                capital_item = QTableWidgetItem(capital_display)
                capital_item.setForeground(QColor(255, 165, 0))  # Orange/Amber color for warning
            else:
                # Show only used capital (no available capital)
                capital_display = f"{int(capital_used)}"
                capital_item = QTableWidgetItem(capital_display)
                capital_item.setForeground(QColor(255, 255, 255))  # White
            
            self.backtest_positions_table.setItem(row, 11, capital_item)
            
            # Entry Time
            entry_time_str = self.format_time(entry_time) if entry_time else "N/A"
            self.backtest_positions_table.setItem(row, 12, QTableWidgetItem(entry_time_str))
            
            # Color code other columns based on current PnL
            color = QColor(34, 139, 34) if current_pnl > 0 else (QColor(220, 20, 60) if current_pnl < 0 else QColor(255, 255, 255))
            for col in [0, 1, 3, 4, 5, 11, 12]:  # Skip columns with their own colors (2, 6, 7, 8, 9, 10)
                item = self.backtest_positions_table.item(row, col)
                if item:
                    item.setForeground(color)
        
        # Sync to dialog if it's open
        if self.backtest_results_dialog is not None and self.backtest_results_dialog.isVisible():
            self.sync_backtest_table_to_dialog()
    
    def show_backtest_results_dialog(self):
        """Show backtest results in a maximizable dialog with filters"""
        if self.backtest_results_dialog is None:
            # Create dialog on first use
            self.backtest_results_dialog = QDialog(self)
            self.backtest_results_dialog.setWindowTitle("Backtest Results - Full Table with Filters")
            self.backtest_results_dialog.setMinimumSize(1200, 600)
            self.backtest_results_dialog.resize(1400, 800)
            
            # Create layout
            dialog_layout = QVBoxLayout(self.backtest_results_dialog)
            
            # Create filter section with scrollable area
            filter_group = QGroupBox("Filters")
            filter_group_layout = QVBoxLayout(filter_group)
            
            # Create scrollable area for filters
            filter_scroll = QScrollArea()
            filter_scroll.setWidgetResizable(True)
            filter_scroll.setMaximumHeight(200)
            filter_widget = QWidget()
            filter_widget_layout = QVBoxLayout(filter_widget)
            
            # Create filter inputs for each column in a grid
            self.backtest_filters = {}
            column_headers = [
                "ID", "Symbol", "Type", "Trade Type", "Entry", "Exit", "Qty", "PnL", "Return%",
                "Max Profit", "Min Profit", "Avg Profit", "Avg Loss", "Entry Time", "Exit Time", "Exit Reason"
            ]
            
            # Create grid layout for filters (4 columns)
            filter_grid = QGridLayout()
            row = 0
            col = 0
            for i, header in enumerate(column_headers):
                filter_input = QLineEdit()
                filter_input.setPlaceholderText(f"Filter {header}...")
                filter_input.textChanged.connect(lambda text, col_idx=i: self.filter_backtest_table(col_idx, text))
                self.backtest_filters[i] = filter_input
                filter_grid.addWidget(QLabel(f"{header}:"), row, col * 2)
                filter_grid.addWidget(filter_input, row, col * 2 + 1)
                col += 1
                if col >= 4:  # 4 columns per row
                    col = 0
                    row += 1
            
            filter_widget_layout.addLayout(filter_grid)
            filter_scroll.setWidget(filter_widget)
            filter_group_layout.addWidget(filter_scroll)
            
            # Add clear filters button
            clear_btn = QPushButton("Clear All Filters")
            clear_btn.clicked.connect(self.clear_backtest_filters)
            filter_group_layout.addWidget(clear_btn)
            
            dialog_layout.addWidget(filter_group)
            
            # Create table in dialog
            self.backtest_dialog_table = QTableWidget(0, 16)
            self.backtest_dialog_table.setHorizontalHeaderLabels(column_headers)
            self.backtest_dialog_table.horizontalHeader().setStretchLastSection(True)
            self.backtest_dialog_table.setSortingEnabled(True)
            dialog_layout.addWidget(self.backtest_dialog_table)
            
            # Store original data for filtering
            self.backtest_table_data = []
        
        # Copy data from main table to dialog table
        self.sync_backtest_table_to_dialog()
        
        # Show dialog in full screen mode
        self.backtest_results_dialog.show()
        self.backtest_results_dialog.showFullScreen()
    
    def show_backtest_summary_dialog(self):
        """Show backtest summary in a full screen dialog"""
        if self.backtest_summary_dialog is None:
            # Create dialog on first use
            self.backtest_summary_dialog = QDialog(self)
            self.backtest_summary_dialog.setWindowTitle("Backtest Summary - Full Screen")
            self.backtest_summary_dialog.setMinimumSize(800, 600)
            
            # Create layout
            dialog_layout = QVBoxLayout(self.backtest_summary_dialog)
            
            # Create table in dialog
            self.backtest_summary_dialog_table = QTableWidget(0, 2)
            self.backtest_summary_dialog_table.setHorizontalHeaderLabels(["Metric", "Value"])
            self.backtest_summary_dialog_table.horizontalHeader().setStretchLastSection(True)
            self.backtest_summary_dialog_table.setSortingEnabled(True)
            self.backtest_summary_dialog_table.setSelectionBehavior(QTableWidget.SelectRows)
            dialog_layout.addWidget(self.backtest_summary_dialog_table)
        
        # Copy data from main summary table to dialog table
        self.sync_backtest_summary_to_dialog()
        
        # Show dialog in full screen mode
        self.backtest_summary_dialog.show()
        self.backtest_summary_dialog.showFullScreen()
    
    def sync_backtest_summary_to_dialog(self):
        """Sync data from main backtest summary table to dialog table"""
        if self.backtest_summary_dialog is None or not hasattr(self, 'backtest_summary_dialog_table'):
            return
        
        # Clear dialog table
        self.backtest_summary_dialog_table.setRowCount(0)
        
        # Copy all rows from main summary table
        for row in range(self.backtest_summary_table.rowCount()):
            dialog_row = self.backtest_summary_dialog_table.rowCount()
            self.backtest_summary_dialog_table.insertRow(dialog_row)
            
            # Copy metric column
            metric_item = self.backtest_summary_table.item(row, 0)
            if metric_item:
                dialog_metric_item = QTableWidgetItem(metric_item.text())
                # Copy font and background if it's a category header
                if metric_item.font().bold():
                    dialog_metric_item.setFont(QFont("Arial", 9, QFont.Bold))
                    dialog_metric_item.setBackground(QColor(232, 232, 232))
                dialog_metric_item.setForeground(metric_item.foreground())
                self.backtest_summary_dialog_table.setItem(dialog_row, 0, dialog_metric_item)
            
            # Copy value column
            value_item = self.backtest_summary_table.item(row, 1)
            if value_item:
                dialog_value_item = QTableWidgetItem(value_item.text())
                dialog_value_item.setForeground(value_item.foreground())
                self.backtest_summary_dialog_table.setItem(dialog_row, 1, dialog_value_item)
    
    def sync_backtest_table_to_dialog(self):
        """Sync data from main backtest table to dialog table"""
        if self.backtest_results_dialog is None or not hasattr(self, 'backtest_dialog_table'):
            return
        
        # Store original data
        self.backtest_table_data = []
        
        # Copy all rows from main table
        for row in range(self.backtest_table.rowCount()):
            row_data = []
            for col in range(self.backtest_table.columnCount()):
                item = self.backtest_table.item(row, col)
                row_data.append(item.text() if item else "")
            self.backtest_table_data.append(row_data)
        
        # Apply current filters and update dialog table
        self.apply_backtest_filters()
    
    def filter_backtest_table(self, column: int, filter_text: str):
        """Filter the backtest table based on column and text"""
        if not hasattr(self, 'backtest_table_data'):
            return
        
        self.apply_backtest_filters()
    
    def apply_backtest_filters(self):
        """Apply all active filters to the dialog table"""
        if not hasattr(self, 'backtest_table_data') or not hasattr(self, 'backtest_dialog_table'):
            return
        
        # Get filter values
        filters = {}
        for col, filter_input in self.backtest_filters.items():
            filter_text = filter_input.text().strip().lower()
            if filter_text:
                filters[col] = filter_text
        
        # Filter rows
        filtered_data = []
        for row_data in self.backtest_table_data:
            match = True
            for col, filter_text in filters.items():
                if col < len(row_data):
                    cell_value = str(row_data[col]).lower()
                    if filter_text not in cell_value:
                        match = False
                        break
            if match:
                filtered_data.append(row_data)
        
        # Update dialog table
        self.backtest_dialog_table.setRowCount(len(filtered_data))
        for row_idx, row_data in enumerate(filtered_data):
            for col_idx, cell_value in enumerate(row_data):
                item = QTableWidgetItem(cell_value)
                
                # Apply color coding based on PnL column (column 7)
                if col_idx == 7:  # PnL column
                    try:
                        pnl_value = float(cell_value.replace('+', '').replace(',', ''))
                        if pnl_value > 0:
                            item.setForeground(QColor(34, 139, 34))  # Green
                        elif pnl_value < 0:
                            item.setForeground(QColor(220, 20, 60))  # Red
                    except:
                        pass
                elif col_idx == 3:  # Trade Type column
                    if "PAPER" in cell_value:
                        item.setForeground(QColor(255, 215, 0))  # Gold/Yellow
                    else:
                        item.setForeground(QColor(255, 255, 255))  # White
                
                self.backtest_dialog_table.setItem(row_idx, col_idx, item)
    
    def clear_backtest_filters(self):
        """Clear all filter inputs"""
        for filter_input in self.backtest_filters.values():
            filter_input.clear()
        self.apply_backtest_filters()
    
    def update_backtest_ltp_table(self, results: list):
        """Update backtest LTP table with prices and signals (similar to intraday)"""
        # Only update if table exists
        if not hasattr(self, 'backtest_ltp_table'):
            return
        
        # Always allow updates if table exists (don't restrict by tab)
        # The signal will only be emitted during backtesting anyway
        
        # Ensure results is a list
        if not results or not isinstance(results, list):
            return
        
        # Refresh enabled indicators list
        enabled_indicators = self._get_enabled_indicators()
        num_indicator_cols = len(enabled_indicators)
        num_base_cols = 5  # Symbol, LTP, Signal, Change, Confidence
        total_cols = num_base_cols + num_indicator_cols
        
        # Update table columns if needed
        if self.backtest_ltp_table.columnCount() != total_cols:
            self.backtest_ltp_table.setColumnCount(total_cols)
            headers = ["Symbol", "LTP", "Signal", "Change", "Confidence"] + [ind.replace('_', ' ').title() for ind in enabled_indicators]
            self.backtest_ltp_table.setHorizontalHeaderLabels(headers)
            # If columns changed, need to rebuild table
            self.backtest_ltp_table.setRowCount(0)
            self.backtest_ltp_symbol_map = {}  # Clear mapping
        
        # Build reverse mapping: symbol -> row index
        symbol_to_row = {}
        for row_idx, symbol in self.backtest_ltp_symbol_map.items():
            symbol_to_row[symbol] = row_idx
        
        # Process each result
        for result in results:
            symbol = result.get('symbol', '')
            if not symbol:
                continue
                
            symbol_short = symbol.split(':')[-1]
            ltp = result.get('latest_price', 0)
            signal = result.get('final_signal', 'HOLD')
            indicator_signals = result.get('indicator_signals', {})
            agreement_score = result.get('agreement_score', 0.0)
            
            # Check if row exists for this symbol
            if symbol in symbol_to_row:
                # Update existing row
                row = symbol_to_row[symbol]
                
                change = result.get('change', 0.0)
                change_pct = result.get('change_pct', 0.0)
                change_str = f"{change:+.2f} ({change_pct:+.2f}%)"
                
                # Update LTP (always update in real-time)
                ltp_item = self.backtest_ltp_table.item(row, 1)
                if ltp_item:
                    ltp_item.setText(f"{ltp:.2f}")
                else:
                    ltp_item = QTableWidgetItem(f"{ltp:.2f}")
                    self.backtest_ltp_table.setItem(row, 1, ltp_item)
                
                # Update Signal
                signal_item = self.backtest_ltp_table.item(row, 2)
                if signal_item:
                    signal_item.setText(signal)
                else:
                    signal_item = QTableWidgetItem(signal)
                    self.backtest_ltp_table.setItem(row, 2, signal_item)
                
                # Update Change (always update in real-time)
                change_item = self.backtest_ltp_table.item(row, 3)
                if change_item:
                    change_item.setText(change_str)
                else:
                    change_item = QTableWidgetItem(change_str)
                    self.backtest_ltp_table.setItem(row, 3, change_item)
                
                # Update Confidence
                confidence_str = f"{agreement_score:.0%}"
                confidence_item = self.backtest_ltp_table.item(row, 4)
                if confidence_item:
                    confidence_item.setText(confidence_str)
                else:
                    confidence_item = QTableWidgetItem(confidence_str)
                    self.backtest_ltp_table.setItem(row, 4, confidence_item)
                
                # Color code based on change
                if change > 0:
                    color = QColor(34, 139, 34)  # Green text
                elif change < 0:
                    color = QColor(220, 20, 60)  # Red text
                else:
                    color = QColor(255, 255, 255)  # White text
                
                for col in [0, 1, 3]:  # Symbol, LTP, Change
                    item = self.backtest_ltp_table.item(row, col)
                    if item:
                        item.setForeground(color)
                
                # Update previous price for next iteration (AFTER calculating change)
                self.backtest_previous_prices[symbol] = ltp
                
                # Signal color
                if signal == 'BUY':
                    signal_item.setForeground(QColor(34, 139, 34))
                elif signal == 'SELL':
                    signal_item.setForeground(QColor(220, 20, 60))
                else:
                    signal_item.setForeground(QColor(128, 128, 128))
                
                # Confidence color
                if agreement_score >= 0.70:
                    confidence_color = QColor(34, 139, 34)
                elif agreement_score >= 0.50:
                    confidence_color = QColor(255, 215, 0)
                else:
                    confidence_color = QColor(220, 20, 60)
                confidence_item.setForeground(confidence_color)
                
                # Update indicator columns
                for idx, ind_name in enumerate(enabled_indicators):
                    col_idx = num_base_cols + idx
                    actual_ind_name = self._map_config_name_to_indicator_name(ind_name, indicator_signals)
                    ind_signal = indicator_signals.get(actual_ind_name, 'HOLD')
                    
                    ind_item = self.backtest_ltp_table.item(row, col_idx)
                    if ind_item:
                        ind_item.setText(ind_signal)
                    else:
                        ind_item = QTableWidgetItem(ind_signal)
                        self.backtest_ltp_table.setItem(row, col_idx, ind_item)
                    
                    # Color code indicator signals
                    if ind_signal == 'BUY':
                        ind_item.setForeground(QColor(34, 139, 34))
                    elif ind_signal == 'SELL':
                        ind_item.setForeground(QColor(220, 20, 60))
                    else:
                        ind_item.setForeground(QColor(128, 128, 128))
                
                self.backtest_previous_prices[symbol] = ltp
            else:
                # New symbol - add new row
                prev_price = self.backtest_previous_prices.get(symbol, ltp)
                change = ltp - prev_price
                change_pct = (change / prev_price * 100) if prev_price > 0 else 0
                change_str = f"{change:+.2f} ({change_pct:+.2f}%)"
                confidence_str = f"{agreement_score:.0%}"
                
                row = self.backtest_ltp_table.rowCount()
                self.backtest_ltp_table.insertRow(row)
                
                # Base columns
                self.backtest_ltp_table.setItem(row, 0, QTableWidgetItem(symbol_short))
                self.backtest_ltp_table.setItem(row, 1, QTableWidgetItem(f"{ltp:.2f}"))
                self.backtest_ltp_table.setItem(row, 2, QTableWidgetItem(signal))
                self.backtest_ltp_table.setItem(row, 3, QTableWidgetItem(change_str))
                self.backtest_ltp_table.setItem(row, 4, QTableWidgetItem(confidence_str))
                
                # Color code
                if change > 0:
                    change_color = QColor(34, 139, 34)
                elif change < 0:
                    change_color = QColor(220, 20, 60)
                else:
                    change_color = QColor(255, 255, 255)
                
                for col in [0, 1, 3]:
                    item = self.backtest_ltp_table.item(row, col)
                    if item:
                        item.setForeground(change_color)
                
                # Signal color
                signal_item = self.backtest_ltp_table.item(row, 2)
                if signal == 'BUY':
                    signal_item.setForeground(QColor(34, 139, 34))
                elif signal == 'SELL':
                    signal_item.setForeground(QColor(220, 20, 60))
                else:
                    signal_item.setForeground(QColor(128, 128, 128))
                
                # Confidence color
                confidence_item = self.backtest_ltp_table.item(row, 4)
                if agreement_score >= 0.70:
                    confidence_item.setForeground(QColor(34, 139, 34))
                elif agreement_score >= 0.50:
                    confidence_item.setForeground(QColor(255, 215, 0))
                else:
                    confidence_item.setForeground(QColor(220, 20, 60))
                
                # Indicator columns
                for idx, ind_name in enumerate(enabled_indicators):
                    col_idx = num_base_cols + idx
                    actual_ind_name = self._map_config_name_to_indicator_name(ind_name, indicator_signals)
                    ind_signal = indicator_signals.get(actual_ind_name, 'HOLD')
                    
                    ind_item = QTableWidgetItem(ind_signal)
                    if ind_signal == 'BUY':
                        ind_item.setForeground(QColor(34, 139, 34))
                    elif ind_signal == 'SELL':
                        ind_item.setForeground(QColor(220, 20, 60))
                    else:
                        ind_item.setForeground(QColor(128, 128, 128))
                    self.backtest_ltp_table.setItem(row, col_idx, ind_item)
                
                # Store symbol mapping
                self.backtest_ltp_symbol_map[row] = symbol
                symbol_to_row[symbol] = row
                # Store current price as previous for next change calculation
                self.backtest_previous_prices[symbol] = ltp
    
    def update_backtest_summary(self, summary: dict):
        """Update backtest summary table with comprehensive metrics"""
        self.backtest_summary_table.setRowCount(0)
        
        # Note: Sync to dialog will happen at the end of this function
        
        # Get initial capital
        backtest_config = self.config.get('backtest', {})
        initial_capital = backtest_config.get('initial_capital', 20000)
        
        # Get closed orders for detailed metrics
        closed_orders = None
        if self.bot_thread and self.bot_thread.bot:
            closed_orders = self.bot_thread.bot.engine.get_closed_orders()
        
        # Calculate comprehensive metrics if we have closed orders
        if closed_orders is not None and not closed_orders.empty:
            metrics = self.calculate_metrics(closed_orders, initial_capital)
            
            # Add summary data from engine
            actual_capital = summary.get('actual_capital', initial_capital)
            hypothetical_capital = summary.get('hypothetical_capital', initial_capital)
            circuit_breaker_savings = summary.get('circuit_breaker_savings', 0)
            paper_trades = summary.get('paper_trades', 0)
            consecutive_losses = summary.get('consecutive_losses', 0)
            paper_trading_mode = summary.get('paper_trading_mode', False)
            
            # Get total charges and net profit from summary
            total_charges = summary.get('total_charges', 0.0)
            total_net_profit = summary.get('total_net_profit', summary.get('total_pnl', 0))
            total_gross_pnl = summary.get('total_gross_pnl', summary.get('total_pnl', 0))
            
            # Add metrics to table with categories
            categories = [
                ("Capital", [
                    ("Initial Capital", f"₹{initial_capital:,.2f}"),
                    ("Current Capital", f"₹{actual_capital:,.2f}"),
                    ("Hypothetical Capital", f"₹{hypothetical_capital:,.2f}"),
                    ("Circuit Breaker Savings", f"₹{circuit_breaker_savings:+,.2f}")
                ]),
                ("Performance", [
                    ("Total PnL", metrics.get("Total PnL", "₹0.00")),
                    ("Return %", metrics.get("Return %", "0.00%")),
                    ("Total Charges", f"₹{total_charges:,.2f}"),
                    ("Gross PnL", f"₹{total_gross_pnl:+,.2f}"),
                    ("Net Profit (After Charges)", f"₹{total_net_profit:+,.2f}")
                ]),
                ("Trades", [
                    ("Total Trades", metrics.get("Total Trades", 0)),
                    ("Win Rate", metrics.get("Win Rate", "0.00%")),
                    ("Paper Trades", str(paper_trades)),
                    ("Real Trades", str(summary.get('closed_orders', 0)))
                ]),
                ("Wins/Losses", [
                    ("Average Win", metrics.get("Average Win", "₹0.00")),
                    ("Average Loss", metrics.get("Average Loss", "₹0.00")),
                    ("Largest Win", metrics.get("Largest Win", "₹0.00")),
                    ("Largest Loss", metrics.get("Largest Loss", "₹0.00"))
                ]),
                ("Ratios", [
                    ("Profit Factor", metrics.get("Profit Factor", "0.00")),
                    ("Expectancy", metrics.get("Expectancy", "₹0.00")),
                    ("Sharpe Ratio", metrics.get("Sharpe Ratio", "0.00")),
                    ("Max Drawdown", metrics.get("Max Drawdown", "0.00%")),
                    ("Sortino Ratio", metrics.get("Sortino Ratio", "0.00")),
                    ("Calmar Ratio", metrics.get("Calmar Ratio", "0.00"))
                ]),
                ("Circuit Breaker", [
                    ("Consecutive Losses", str(consecutive_losses)),
                    ("Paper Trading Mode", "ACTIVE" if paper_trading_mode else "INACTIVE"),
                    ("Paper Trades Count", str(paper_trades))
                ]),
                ("System Stats", [
                    ("Open Positions", str(summary.get('open_positions', 0))),
                    ("Indicators Registered", str(summary.get('indicators_registered', 0))),
                    ("Total Signals", metrics.get("Total Signals", "N/A")),
                    ("Trades Executed", metrics.get("Trades Executed", 0)),
                    ("Trades Skipped", metrics.get("Trades Skipped", "N/A"))
                ])
            ]
            
            # Calculate and add per-symbol metrics
            symbol_metrics = self.calculate_per_symbol_metrics(closed_orders)
            if symbol_metrics:
                # Add per-symbol metrics category
                per_symbol_list = []
                for symbol, sym_metrics in symbol_metrics.items():
                    # Shorten symbol name for display
                    symbol_display = symbol.split(':')[-1] if ':' in symbol else symbol
                    per_symbol_list.append((f"📊 {symbol_display}", ""))
                    per_symbol_list.append(("  Total Orders", str(sym_metrics.get('total_orders', 0))))
                    per_symbol_list.append(("  Total PnL", f"₹{sym_metrics.get('total_pnl', 0):+,.2f}"))
                    per_symbol_list.append(("  Profit Orders", str(sym_metrics.get('profit_orders', 0))))
                    per_symbol_list.append(("  Loss Orders", str(sym_metrics.get('loss_orders', 0))))
                    per_symbol_list.append(("  Win Rate", f"{sym_metrics.get('win_rate', 0):.2f}%"))
                    per_symbol_list.append(("  Avg Win", f"₹{sym_metrics.get('avg_win', 0):,.2f}"))
                    per_symbol_list.append(("  Avg Loss", f"₹{sym_metrics.get('avg_loss', 0):,.2f}"))
                    per_symbol_list.append(("  Largest Win", f"₹{sym_metrics.get('largest_win', 0):,.2f}"))
                    per_symbol_list.append(("  Largest Loss", f"₹{sym_metrics.get('largest_loss', 0):,.2f}"))
                    per_symbol_list.append(("  Profit Factor", f"{sym_metrics.get('profit_factor', 0):.2f}"))
                    per_symbol_list.append(("  Expectancy", f"₹{sym_metrics.get('expectancy', 0):+,.2f}"))
                    per_symbol_list.append(("  Paper Trades", str(sym_metrics.get('paper_trades', 0))))
                    per_symbol_list.append(("  Real Trades", str(sym_metrics.get('real_trades', 0))))
                    per_symbol_list.append(("", ""))  # Empty row separator
                
                categories.append(("Per-Symbol Metrics", per_symbol_list))
            
            for category, metric_list in categories:
                # Add category header
                row = self.backtest_summary_table.rowCount()
                self.backtest_summary_table.insertRow(row)
                category_item = QTableWidgetItem(category)
                category_item.setFont(QFont("Arial", 9, QFont.Bold))
                category_item.setBackground(QColor(232, 232, 232))
                self.backtest_summary_table.setItem(row, 0, category_item)
                self.backtest_summary_table.setItem(row, 1, QTableWidgetItem(""))
                
                # Add metrics
                for metric_name, metric_value in metric_list:
                    row = self.backtest_summary_table.rowCount()
                    self.backtest_summary_table.insertRow(row)
                    self.backtest_summary_table.setItem(row, 0, QTableWidgetItem(metric_name))
                    
                    value_item = QTableWidgetItem(str(metric_value))
                    
                    # Color code text
                    if "PnL" in metric_name or "Return" in metric_name or "Savings" in metric_name or "Expectancy" in metric_name:
                        # Try to extract numeric value for coloring
                        try:
                            if "₹" in str(metric_value):
                                num_val = float(str(metric_value).replace("₹", "").replace(",", "").replace("+", ""))
                            elif "%" in str(metric_value):
                                num_val = float(str(metric_value).replace("%", ""))
                            else:
                                num_val = float(metric_value)
                            
                            if num_val > 0:
                                value_item.setForeground(QColor(34, 139, 34))  # Green text
                            elif num_val < 0:
                                value_item.setForeground(QColor(220, 20, 60))  # Red text
                        except:
                            pass
                    elif "📊" in metric_name or "Symbol:" in metric_name:
                        # Symbol header - make it bold and colored
                        metric_item = self.backtest_summary_table.item(row, 0)
                        if metric_item:
                            metric_item.setFont(QFont("Arial", 9, QFont.Bold))
                            metric_item.setForeground(QColor(30, 144, 255))  # Blue text
                        value_item.setForeground(QColor(30, 144, 255))  # Blue text
                    elif metric_name.startswith("  "):
                        # Indented metric - use slightly different styling
                        metric_item = self.backtest_summary_table.item(row, 0)
                        if metric_item:
                            metric_item.setForeground(QColor(180, 180, 180))  # Light gray
                        # Color code the value based on content
                        if "PnL" in metric_name or "Expectancy" in metric_name:
                            try:
                                if "₹" in str(metric_value):
                                    num_val = float(str(metric_value).replace("₹", "").replace(",", "").replace("+", ""))
                                    if num_val > 0:
                                        value_item.setForeground(QColor(34, 139, 34))  # Green
                                    elif num_val < 0:
                                        value_item.setForeground(QColor(220, 20, 60))  # Red
                            except:
                                pass
                        elif "Win Rate" in metric_name or "Profit Factor" in metric_name:
                            try:
                                num_val = float(str(metric_value).replace("%", ""))
                                if num_val > 50 or (num_val > 1 and "Profit Factor" in metric_name):
                                    value_item.setForeground(QColor(34, 139, 34))  # Green
                                elif num_val < 30 or (num_val < 1 and "Profit Factor" in metric_name):
                                    value_item.setForeground(QColor(220, 20, 60))  # Red
                            except:
                                pass
                    elif "Win Rate" in metric_name or "Profit Factor" in metric_name:
                        try:
                            if "%" in str(metric_value):
                                num_val = float(str(metric_value).replace("%", ""))
                            else:
                                num_val = float(metric_value)
                            if num_val > 0:
                                value_item.setForeground(QColor(30, 144, 255))  # Blue text
                        except:
                            pass
                    elif "Paper Trading Mode" in metric_name:
                        if "ACTIVE" in str(metric_value):
                            value_item.setForeground(QColor(255, 215, 0))  # Gold/Yellow
                        else:
                            value_item.setForeground(QColor(255, 255, 255))  # White
                    
                    self.backtest_summary_table.setItem(row, 1, value_item)
        else:
            # No trades yet - show basic info
                    row = self.backtest_summary_table.rowCount()
                    self.backtest_summary_table.insertRow(row)
                    self.backtest_summary_table.setItem(row, 0, QTableWidgetItem("Initial Capital"))
                    self.backtest_summary_table.setItem(row, 1, QTableWidgetItem(f"₹{initial_capital:,.2f}"))
        
        # Sync to dialog if it's open (at the end of function)
        if self.backtest_summary_dialog is not None and self.backtest_summary_dialog.isVisible():
            self.sync_backtest_summary_to_dialog()
    
    def handle_error(self, error_msg: str):
        """Handle error from bot thread"""
        self.log_event("ERROR", error_msg)
        QMessageBox.critical(self, "Error", error_msg)
    
    def _get_enabled_indicators(self):
        """Get list of enabled indicator names from config"""
        indicators_config = self.config.get('indicators', {})
        enabled = []
        for ind_name, ind_config in indicators_config.items():
            if ind_config.get('enabled', False):
                enabled.append(ind_name)
        return sorted(enabled)  # Sort for consistent column order
    
    def _map_config_name_to_indicator_name(self, config_name: str, indicator_signals: dict) -> str:
        """
        Map config indicator name to actual indicator class name.
        
        Config uses: rsi, ma_crossover, macd, bollinger_bands, mystic_pulse, super_regression
        Indicator classes use: RSI, MACrossover, MACD, BollingerBands, MysticPulse, SuperRegression
        
        Returns the actual key from indicator_signals dict, or config_name if not found.
        """
        # Direct match first
        if config_name in indicator_signals:
            return config_name
        
        # Try common mappings
        name_mappings = {
            'rsi': 'RSI',
            'ma_crossover': 'MACrossover',
            'macd': 'MACD',
            'bollinger_bands': 'BollingerBands',
            'mystic_pulse': 'MysticPulse',
            'super_regression': 'SuperRegression'
        }
        
        # Try mapped name
        mapped_name = name_mappings.get(config_name)
        if mapped_name and mapped_name in indicator_signals:
            return mapped_name
        
        # Try case-insensitive search
        config_lower = config_name.lower()
        for key in indicator_signals.keys():
            if key.lower() == config_lower or key.lower().replace('_', '') == config_lower.replace('_', ''):
                return key
        
        # Try converting config_name to class name format
        # rsi -> RSI, ma_crossover -> MACrossover
        parts = config_name.split('_')
        class_name = ''.join(word.capitalize() for word in parts)
        if class_name in indicator_signals:
            return class_name
        
        # If nothing matches, return config_name (will default to HOLD)
        return config_name
    
    # Chart display methods
    def on_symbol_click(self, item: QTableWidgetItem):
        """Handle double-click on symbol to show price trend"""
        row = item.row()
        symbol = self.ltp_symbol_map.get(row, None)
        
        if not symbol or symbol not in self.ltp_history:
            QMessageBox.information(self, "Info", "Insufficient data to show trend for this symbol.")
            return
        
        self.show_price_trend(symbol)
    
    def show_price_trend(self, symbol: str):
        """Show interactive price trend chart using Plotly."""
        # Update chart dialogs with latest data
        self._chart_dialogs.set_ltp_history(self.ltp_history)
        self._chart_dialogs.show_price_trend(symbol)
    
    def on_metric_click(self, item: QTableWidgetItem):
        """Handle double-click on metric to show trend."""
        row = item.row()
        metric_name = self.backtest_summary_table.item(row, 0).text()
        metric_map = self._chart_dialogs.get_metric_map()
        metric_key = metric_map.get(metric_name)
        if metric_key and metric_key in self.metrics_history and len(self.metrics_history[metric_key]) > 1:
            self.show_metric_trend(metric_name, metric_key)
    
    def show_metric_trend(self, metric_name: str, metric_key: str):
        """Show interactive metric trend chart."""
        self._chart_dialogs.set_metrics_history(self.metrics_history)
        self._chart_dialogs.show_metric_trend(metric_name, metric_key)
    
    def show_plotly_chart(self, fig, title: str):
        """Display Plotly chart in QWebEngineView window."""
        self._chart_dialogs._show_plotly_chart(fig, title)
    
    def _throttled_intraday_dashboard_update(self, summary: dict):
        """Throttled dashboard update for intraday - prevents UI freezing"""
        self.pending_dashboard_summary = summary
        self.pending_dashboard_type = 'intraday'
        
        # If timer is not running, start it (200ms throttle)
        if not self.dashboard_update_timer.isActive():
            self.dashboard_update_timer.start(200)
    
    def _throttled_backtest_dashboard_update(self, summary: dict):
        """Throttled dashboard update for backtest - prevents UI freezing"""
        self.pending_dashboard_summary = summary
        self.pending_dashboard_type = 'backtest'
        
        # If timer is not running, start it (500ms throttle for backtest)
        if not self.dashboard_update_timer.isActive():
            self.dashboard_update_timer.start(500)
    
    def _process_dashboard_updates(self):
        """Process pending dashboard updates"""
        if self.pending_dashboard_summary is None:
            return
        
        summary = self.pending_dashboard_summary
        dashboard_type = getattr(self, 'pending_dashboard_type', 'intraday')
        
        if dashboard_type == 'intraday':
            self.update_intraday_dashboard(summary)
        elif dashboard_type == 'backtest':
            self.update_backtest_dashboard(summary)
        
        self.pending_dashboard_summary = None
    
    def update_intraday_dashboard(self, summary: dict):
        """Update intraday analytics dashboard in real-time"""
        if not hasattr(self, 'intraday_kpi_tiles'):
            return
        
        try:
            # Update KPI tiles
            total_pnl = summary.get('total_pnl', 0)
            win_rate = summary.get('win_rate', 0) * 100
            total_trades = summary.get('closed_orders', 0)
            open_positions = summary.get('open_positions', 0)
            realized_pnl = summary.get('realized_pnl', 0)
            
            # Calculate additional metrics
            closed_orders = None
            if self.bot_thread and self.bot_thread.bot:
                closed_orders = self.bot_thread.bot.engine.get_closed_orders()
            
            avg_win = 0
            avg_loss = 0
            profit_factor = 0
            
            if closed_orders is not None and not closed_orders.empty:
                winning_trades = closed_orders[closed_orders['pnl'] > 0]
                losing_trades = closed_orders[closed_orders['pnl'] < 0]
                
                if len(winning_trades) > 0:
                    avg_win = winning_trades['pnl'].mean()
                if len(losing_trades) > 0:
                    avg_loss = abs(losing_trades['pnl'].mean())
                
                if avg_loss > 0:
                    total_profit = winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0
                    total_loss = abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else 0
                    profit_factor = total_profit / total_loss if total_loss > 0 else 0
            
            # Update tile values
            self.update_kpi_tile(self.intraday_kpi_tiles.get('total_pnl'), f'₹{total_pnl:,.2f}')
            self.update_kpi_tile(self.intraday_kpi_tiles.get('win_rate'), f'{win_rate:.2f}%')
            self.update_kpi_tile(self.intraday_kpi_tiles.get('total_trades'), str(total_trades))
            self.update_kpi_tile(self.intraday_kpi_tiles.get('open_positions'), str(open_positions))
            self.update_kpi_tile(self.intraday_kpi_tiles.get('realized_pnl'), f'₹{realized_pnl:,.2f}')
            self.update_kpi_tile(self.intraday_kpi_tiles.get('avg_win'), f'₹{avg_win:,.2f}')
            self.update_kpi_tile(self.intraday_kpi_tiles.get('avg_loss'), f'₹{avg_loss:,.2f}')
            self.update_kpi_tile(self.intraday_kpi_tiles.get('profit_factor'), f'{profit_factor:.2f}')
            
            # Initialize dashboard data if not exists
            if not hasattr(self, 'intraday_dashboard_data'):
                self.intraday_dashboard_data = {
                    'pnl_history': [],
                    'equity_history': [],
                    'timestamps': [],
                    'update_counter': 0
                }
            
            # Ensure update_counter exists
            if 'update_counter' not in self.intraday_dashboard_data:
                self.intraday_dashboard_data['update_counter'] = 0
            
            self.intraday_dashboard_data['update_counter'] += 1
            
            # Only update charts every 10th update
            if self.intraday_dashboard_data['update_counter'] % 10 == 0:
                current_time = datetime.now()
                self.intraday_dashboard_data['pnl_history'].append(total_pnl)
                self.intraday_dashboard_data['equity_history'].append(summary.get('actual_capital', 0))
                self.intraday_dashboard_data['timestamps'].append(current_time)
                
                # Keep only last 100 points for performance
                if len(self.intraday_dashboard_data['timestamps']) > 100:
                    self.intraday_dashboard_data['pnl_history'] = self.intraday_dashboard_data['pnl_history'][-100:]
                    self.intraday_dashboard_data['equity_history'] = self.intraday_dashboard_data['equity_history'][-100:]
                    self.intraday_dashboard_data['timestamps'] = self.intraday_dashboard_data['timestamps'][-100:]
                
                # Update charts (only if we have data)
                if len(self.intraday_dashboard_data['timestamps']) > 1:
                    self.update_pnl_chart(self.intraday_pnl_chart, 
                                         self.intraday_dashboard_data['timestamps'],
                                         self.intraday_dashboard_data['pnl_history'],
                                         "Intraday PnL Over Time")
                    
                    self.update_equity_chart(self.intraday_equity_chart,
                                            self.intraday_dashboard_data['timestamps'],
                                            self.intraday_dashboard_data['equity_history'],
                                            "Intraday Equity Curve")
            
            # Update per-symbol table and exit reasons only every 20 updates
            if closed_orders is not None and not closed_orders.empty:
                if self.intraday_dashboard_data['update_counter'] % 20 == 0:
                    self.update_symbol_performance_table(self.intraday_symbol_table, closed_orders)
                    self.update_exit_reasons_table(self.intraday_exit_reasons_table, closed_orders)
                
        except Exception as e:
            print(f"Error updating intraday dashboard: {e}")
            import traceback
            traceback.print_exc()
    
    def update_backtest_dashboard(self, summary: dict):
        """Update backtest analytics dashboard in real-time"""
        if not hasattr(self, 'backtest_kpi_tiles'):
            return
        
        try:
            # Get closed orders
            closed_orders = None
            if self.bot_thread and self.bot_thread.bot:
                closed_orders = self.bot_thread.bot.engine.get_closed_orders()
            
            # Get initial capital
            backtest_config = self.config.get('backtest', {})
            initial_capital = backtest_config.get('initial_capital', 20000)
            
            # Calculate metrics
            if closed_orders is not None and not closed_orders.empty:
                metrics = self.calculate_metrics(closed_orders, initial_capital)
                
                # Update KPI tiles
                total_pnl = summary.get('total_pnl', 0)
                win_rate = float(str(metrics.get('Win Rate', '0%')).replace('%', ''))
                total_trades = summary.get('closed_orders', 0)
                sharpe_ratio = float(str(metrics.get('Sharpe Ratio', '0')).replace('N/A', '0'))
                max_drawdown = float(str(metrics.get('Max Drawdown', '0%')).replace('%', ''))
                profit_factor = float(str(metrics.get('Profit Factor', '0')).replace('N/A', '0'))
                expectancy = float(str(metrics.get('Expectancy', '₹0')).replace('₹', '').replace(',', '').replace('N/A', '0'))
                return_pct = float(str(metrics.get('Return %', '0%')).replace('%', ''))
                
                self.update_kpi_tile(self.backtest_kpi_tiles.get('total_pnl'), f'₹{total_pnl:,.2f}')
                self.update_kpi_tile(self.backtest_kpi_tiles.get('win_rate'), f'{win_rate:.2f}%')
                self.update_kpi_tile(self.backtest_kpi_tiles.get('total_trades'), str(total_trades))
                self.update_kpi_tile(self.backtest_kpi_tiles.get('sharpe_ratio'), f'{sharpe_ratio:.2f}')
                self.update_kpi_tile(self.backtest_kpi_tiles.get('max_drawdown'), f'{max_drawdown:.2f}%')
                self.update_kpi_tile(self.backtest_kpi_tiles.get('profit_factor'), f'{profit_factor:.2f}')
                self.update_kpi_tile(self.backtest_kpi_tiles.get('expectancy'), f'₹{expectancy:,.2f}')
                self.update_kpi_tile(self.backtest_kpi_tiles.get('return_pct'), f'{return_pct:.2f}%')
                
                # Initialize dashboard data if not exists
                if not hasattr(self, 'backtest_dashboard_data'):
                    self.backtest_dashboard_data = {
                        'pnl_history': [],
                        'equity_history': [],
                        'timestamps': [],
                        'update_counter': 0
                    }
                
                # Ensure update_counter exists
                if 'update_counter' not in self.backtest_dashboard_data:
                    self.backtest_dashboard_data['update_counter'] = 0
                
                self.backtest_dashboard_data['update_counter'] += 1
                
                # Only update charts every 20th update
                if self.backtest_dashboard_data['update_counter'] % 20 == 0:
                    current_time = datetime.now()
                    self.backtest_dashboard_data['pnl_history'].append(total_pnl)
                    self.backtest_dashboard_data['equity_history'].append(summary.get('actual_capital', initial_capital))
                    self.backtest_dashboard_data['timestamps'].append(current_time)
                    
                    # Keep only last 500 points for backtest
                    if len(self.backtest_dashboard_data['timestamps']) > 500:
                        self.backtest_dashboard_data['pnl_history'] = self.backtest_dashboard_data['pnl_history'][-500:]
                        self.backtest_dashboard_data['equity_history'] = self.backtest_dashboard_data['equity_history'][-500:]
                        self.backtest_dashboard_data['timestamps'] = self.backtest_dashboard_data['timestamps'][-500:]
                    
                    # Update charts (only if we have data)
                    if len(self.backtest_dashboard_data['timestamps']) > 1:
                        self.update_pnl_chart(self.backtest_pnl_chart,
                                             self.backtest_dashboard_data['timestamps'],
                                             self.backtest_dashboard_data['pnl_history'],
                                             "Backtest PnL Over Time")
                        
                        self.update_equity_chart(self.backtest_equity_chart,
                                                self.backtest_dashboard_data['timestamps'],
                                                self.backtest_dashboard_data['equity_history'],
                                                "Backtest Equity Curve")
                    
                    # Update win/loss distribution chart only every 50 updates
                    if self.backtest_dashboard_data['update_counter'] % 50 == 0:
                        self.update_distribution_chart(self.backtest_dist_chart, closed_orders)
                
                # Update per-symbol table and exit reasons only every 50 updates
                if self.backtest_dashboard_data['update_counter'] % 50 == 0:
                    self.update_symbol_performance_table(self.backtest_symbol_table, closed_orders, detailed=True)
                    self.update_exit_reasons_table(self.backtest_exit_reasons_table, closed_orders)
                
        except Exception as e:
            print(f"Error updating backtest dashboard: {e}")
            import traceback
            traceback.print_exc()
    
    def update_kpi_tile(self, tile: QFrame, value: str):
        """Update KPI tile value"""
        if tile is None:
            return
        # Find the value label (second QLabel in the layout)
        layout = tile.layout()
        if layout and layout.count() >= 2:
            value_label = layout.itemAt(1).widget()
            if isinstance(value_label, QLabel):
                value_label.setText(value)
    
    def update_pnl_chart(self, chart_view: QWebEngineView, timestamps: list, pnl_values: list, title: str):
        """Update PnL over time chart"""
        try:
            import plotly.graph_objects as go
        except ImportError:
            return
        
        if len(timestamps) < 2:
            return
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=pnl_values,
            mode='lines+markers',
            name='PnL',
            line=dict(color='#1976d2', width=2),
            fill='tozeroy',
            fillcolor='rgba(25, 118, 210, 0.1)'
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Time",
            yaxis_title="PnL (₹)",
            template="plotly_white",
            height=300,
            margin=dict(l=50, r=50, t=50, b=50)
        )
        
        html_content = fig.to_html(include_plotlyjs='cdn')
        chart_view.setHtml(html_content)
    
    def update_equity_chart(self, chart_view: QWebEngineView, timestamps: list, equity_values: list, title: str):
        """Update equity curve chart"""
        try:
            import plotly.graph_objects as go
        except ImportError:
            return
        
        if len(timestamps) < 2:
            return
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=equity_values,
            mode='lines',
            name='Equity',
            line=dict(color='#388e3c', width=2)
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Time",
            yaxis_title="Capital (₹)",
            template="plotly_white",
            height=300,
            margin=dict(l=50, r=50, t=50, b=50)
        )
        
        html_content = fig.to_html(include_plotlyjs='cdn')
        chart_view.setHtml(html_content)
    
    def update_distribution_chart(self, chart_view: QWebEngineView, closed_orders: pd.DataFrame):
        """Update win/loss distribution chart"""
        try:
            import plotly.graph_objects as go
        except ImportError:
            return
        
        if closed_orders.empty:
            return
        
        winning_trades = closed_orders[closed_orders['pnl'] > 0]['pnl']
        losing_trades = closed_orders[closed_orders['pnl'] < 0]['pnl']
        
        fig = go.Figure()
        
        if len(winning_trades) > 0:
            fig.add_trace(go.Histogram(
                x=winning_trades,
                name='Wins',
                marker_color='#388e3c',
                opacity=0.7
            ))
        
        if len(losing_trades) > 0:
            fig.add_trace(go.Histogram(
                x=losing_trades,
                name='Losses',
                marker_color='#c62828',
                opacity=0.7
            ))
        
        fig.update_layout(
            title="Win/Loss Distribution",
            xaxis_title="PnL (₹)",
            yaxis_title="Frequency",
            template="plotly_white",
            height=300,
            barmode='overlay',
            margin=dict(l=50, r=50, t=50, b=50)
        )
        
        html_content = fig.to_html(include_plotlyjs='cdn')
        chart_view.setHtml(html_content)
    
    def update_exit_reasons_table(self, table: QTableWidget, closed_orders: pd.DataFrame):
        """Update exit reasons breakdown table with counts and percentages"""
        from trading_system.ui.services.metrics_calculator import categorize_drop_percentage
        
        if table is None or closed_orders is None or closed_orders.empty:
            return
        
        try:
            # Count exit reasons
            if 'exit_reason' not in closed_orders.columns:
                return
            
            # Apply categorization to group drop percentage exits into ranges
            exit_reasons = closed_orders['exit_reason'].fillna('N/A').apply(categorize_drop_percentage)
            reason_counts = exit_reasons.value_counts()
            total_trades = len(closed_orders)
            
            # Clear table
            table.setRowCount(0)
            
            # Sort by count (descending)
            sorted_reasons = reason_counts.sort_values(ascending=False)
            
            # Add rows
            for reason, count in sorted_reasons.items():
                row = table.rowCount()
                table.insertRow(row)
                
                # Exit Reason
                reason_str = str(reason) if not pd.isna(reason) else 'N/A'
                reason_item = QTableWidgetItem(reason_str)
                table.setItem(row, 0, reason_item)
                
                # Count
                count_item = QTableWidgetItem(str(int(count)))
                table.setItem(row, 1, count_item)
                
                # Percentage
                percentage = (count / total_trades * 100) if total_trades > 0 else 0
                percentage_item = QTableWidgetItem(f"{percentage:.2f}%")
                table.setItem(row, 2, percentage_item)
                
                # Color code based on exit reason type
                reason_lower = reason_str.lower()
                if 'profit' in reason_lower or 'target' in reason_lower:
                    # Green for profit-related exits
                    for col in [0, 1, 2]:
                        item = table.item(row, col)
                        if item:
                            item.setForeground(QColor(34, 139, 34))  # Green
                elif 'stop loss' in reason_lower or 'stop' in reason_lower or 'loss' in reason_lower:
                    # Red for stop loss exits
                    for col in [0, 1, 2]:
                        item = table.item(row, col)
                        if item:
                            item.setForeground(QColor(220, 20, 60))  # Red
                elif 'trailing' in reason_lower:
                    # Orange for trailing stops
                    for col in [0, 1, 2]:
                        item = table.item(row, col)
                        if item:
                            item.setForeground(QColor(255, 165, 0))  # Orange
                elif 'candle' in reason_lower or 'closure' in reason_lower:
                    # Yellow for candle closure exits
                    for col in [0, 1, 2]:
                        item = table.item(row, col)
                        if item:
                            item.setForeground(QColor(255, 215, 0))  # Gold/Yellow
                else:
                    # White for other exits
                    for col in [0, 1, 2]:
                        item = table.item(row, col)
                        if item:
                            item.setForeground(QColor(255, 255, 255))  # White
        except Exception as e:
            print(f"Error updating exit reasons table: {e}")
            import traceback
            traceback.print_exc()
    
    def update_symbol_performance_table(self, table: QTableWidget, closed_orders: pd.DataFrame, detailed: bool = False):
        """Update per-symbol performance table"""
        if closed_orders.empty:
            table.setRowCount(0)
            return
        
        # Group by symbol
        symbol_stats = {}
        for _, trade in closed_orders.iterrows():
            symbol = trade.get('symbol', 'N/A')
            if symbol not in symbol_stats:
                symbol_stats[symbol] = {
                    'trades': 0,
                    'pnl': 0,
                    'wins': 0,
                    'losses': 0,
                    'win_amounts': [],
                    'loss_amounts': []
                }
            
            symbol_stats[symbol]['trades'] += 1
            pnl = trade.get('pnl', 0)
            symbol_stats[symbol]['pnl'] += pnl
            
            if pnl > 0:
                symbol_stats[symbol]['wins'] += 1
                symbol_stats[symbol]['win_amounts'].append(pnl)
            elif pnl < 0:
                symbol_stats[symbol]['losses'] += 1
                symbol_stats[symbol]['loss_amounts'].append(abs(pnl))
        
        # Populate table
        table.setRowCount(len(symbol_stats))
        row = 0
        for symbol, stats in symbol_stats.items():
            win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            avg_win = sum(stats['win_amounts']) / len(stats['win_amounts']) if stats['win_amounts'] else 0
            avg_loss = sum(stats['loss_amounts']) / len(stats['loss_amounts']) if stats['loss_amounts'] else 0
            profit_factor = (sum(stats['win_amounts']) / sum(stats['loss_amounts'])) if stats['loss_amounts'] and sum(stats['loss_amounts']) > 0 else 0
            expectancy = ((win_rate / 100) * avg_win) - ((1 - win_rate / 100) * avg_loss)
            
            table.setItem(row, 0, QTableWidgetItem(symbol))
            table.setItem(row, 1, QTableWidgetItem(str(stats['trades'])))
            
            pnl_item = QTableWidgetItem(f'₹{stats["pnl"]:,.2f}')
            if stats['pnl'] > 0:
                pnl_item.setForeground(QColor(34, 139, 34))
            elif stats['pnl'] < 0:
                pnl_item.setForeground(QColor(220, 20, 60))
            table.setItem(row, 2, pnl_item)
            
            table.setItem(row, 3, QTableWidgetItem(f'{win_rate:.2f}%'))
            table.setItem(row, 4, QTableWidgetItem(f'₹{avg_win:,.2f}'))
            table.setItem(row, 5, QTableWidgetItem(f'₹{avg_loss:,.2f}'))
            
            if detailed:
                table.setItem(row, 6, QTableWidgetItem(f'{profit_factor:.2f}'))
                table.setItem(row, 7, QTableWidgetItem(f'₹{expectancy:,.2f}'))
            
            row += 1


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    window = TradingGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
