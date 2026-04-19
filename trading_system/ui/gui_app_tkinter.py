"""
Trading System GUI Application
Python-based UI with tabs for Intraday and Backtesting
All configurations can be done from the UI and update in real-time
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import queue
import yaml
from pathlib import Path
from datetime import datetime
import sys
import os
from typing import Dict, Any, List
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from trading_system.run_live_bot import LiveTradingBot
from trading_system.core.indicator_loader import IndicatorLoader


class TradingGUI:
    """Main GUI application for trading system"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Trading System - Intraday & Backtesting")
        self.root.geometry("1400x900")
        
        # Configuration paths
        self.config_path = Path(__file__).parent.parent / "config" / "trading_config.yaml"
        self.indicators_config_path = Path(__file__).parent.parent / "config" / "indicators_config.yaml"
        
        # Load initial configuration
        self.config = self.load_config()
        
        # Trading bot instance (will be created when needed)
        self.bot = None
        self.bot_thread = None
        self.is_running = False
        
        # Message queue for thread-safe UI updates
        self.message_queue = queue.Queue()
        
        # Store last results for position PnL calculation
        self.last_results = []
        
        # Store previous prices for LTP change calculation
        self.previous_prices = {}
        
        # Store LTP history with timestamps for each symbol
        self.ltp_history = {}  # {symbol: [(timestamp, price), ...]}
        
        # Store historical metrics for trend visualization
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
        
        # Map Treeview item IDs to metric keys for trend visualization
        self.metric_key_map = {}
        
        # Create UI
        self.create_ui()
        
        # Start message queue processor
        self.root.after(100, self.process_queue)
        
        # Load initial config into UI
        self.load_config_to_ui()
        
        # Bind tab change event to load configs
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
    
    def on_tab_changed(self, event):
        """Handle tab change event"""
        # Reload configs when switching tabs to ensure consistency
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 1:  # Backtest tab
            # Ensure backtest configs are loaded
            self.load_backtest_configs()
    
    def load_config(self) -> dict:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config: {e}")
            return {}
    
    def save_config(self, config: dict):
        """Save configuration to YAML file"""
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {e}")
            return False
    
    def create_ui(self):
        """Create the main UI with tabs"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create tabs
        self.intraday_tab = ttk.Frame(self.notebook)
        self.backtest_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.intraday_tab, text="Intraday Trading")
        self.notebook.add(self.backtest_tab, text="Backtesting")
        
        # Create content for each tab
        self.create_intraday_tab()
        self.create_backtest_tab()
    
    def create_intraday_tab(self):
        """Create intraday trading tab"""
        # Left panel: Configuration with fixed width
        config_container = ttk.Frame(self.intraday_tab)
        config_container.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        config_container.config(width=520)
        config_container.pack_propagate(False)  # Prevent shrinking
        
        config_label = ttk.Label(config_container, text="Configuration", font=("Arial", 10, "bold"))
        config_label.pack(fill=tk.X, pady=(0, 5))
        
        # Create scrollable frame
        canvas = tk.Canvas(config_container, width=520)
        scrollbar = ttk.Scrollbar(config_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Create configuration panels inside scrollable frame
        self.create_symbols_config(scrollable_frame)
        self.create_trading_config(scrollable_frame)
        self.create_indicators_config(scrollable_frame)
        self.create_risk_config(scrollable_frame)
        
        # Update canvas scroll region when frame size changes
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        scrollable_frame.bind("<Configure>", on_frame_configure)
        
        # Mouse wheel scrolling (Windows)
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        # Bind mouse wheel to canvas
        def bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        def unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
        
        canvas.bind("<Enter>", bind_mousewheel)
        canvas.bind("<Leave>", unbind_mousewheel)
        
        # Right panel: Results and Status
        results_frame = ttk.Frame(self.intraday_tab)
        results_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create results panel
        self.create_intraday_results(results_frame)
    
    def create_backtest_tab(self):
        """Create backtesting tab"""
        # Left panel: Configuration with fixed width
        config_container = ttk.Frame(self.backtest_tab)
        config_container.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        config_container.config(width=520)
        config_container.pack_propagate(False)  # Prevent shrinking
        
        config_label = ttk.Label(config_container, text="Backtest Configuration", font=("Arial", 10, "bold"))
        config_label.pack(fill=tk.X, pady=(0, 5))
        
        # Create scrollable frame
        canvas = tk.Canvas(config_container, width=520)
        scrollbar = ttk.Scrollbar(config_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Create complete configuration panels (same as intraday) inside scrollable frame
        self.create_backtest_symbols_config(scrollable_frame)
        self.create_backtest_trading_config(scrollable_frame)
        self.create_backtest_indicators_config(scrollable_frame)
        self.create_backtest_risk_config(scrollable_frame)
        self.create_backtest_config(scrollable_frame)
        
        # Update canvas scroll region when frame size changes
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        scrollable_frame.bind("<Configure>", on_frame_configure)
        
        # Mouse wheel scrolling (Windows)
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        # Bind mouse wheel to canvas
        def bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        def unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
        
        canvas.bind("<Enter>", bind_mousewheel)
        canvas.bind("<Leave>", unbind_mousewheel)
        
        # Right panel: Results
        results_frame = ttk.Frame(self.backtest_tab)
        results_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create backtest results
        self.create_backtest_results(results_frame)
    
    def create_symbols_config(self, parent):
        """Create symbols configuration panel"""
        frame = ttk.LabelFrame(parent, text="Symbols", padding=5)
        frame.pack(fill=tk.X, pady=5)
        
        # Symbols listbox with scrollbar
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.symbols_listbox = tk.Listbox(list_frame, height=6, yscrollcommand=scrollbar.set)
        self.symbols_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.symbols_listbox.yview)
        
        # Add/Remove symbols
        symbol_controls = ttk.Frame(frame)
        symbol_controls.pack(fill=tk.X, pady=5)
        
        self.symbol_entry = ttk.Entry(symbol_controls, width=30)
        self.symbol_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(symbol_controls, text="Add", command=self.add_symbol).pack(side=tk.LEFT, padx=2)
        ttk.Button(symbol_controls, text="Remove", command=self.remove_symbol).pack(side=tk.LEFT, padx=2)
        
        # Lot sizes
        lot_frame = ttk.LabelFrame(frame, text="Lot Sizes", padding=5)
        lot_frame.pack(fill=tk.X, pady=5)
        
        self.lot_size_entry = ttk.Entry(lot_frame, width=15)
        self.lot_size_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(lot_frame, text="Default:").pack(side=tk.LEFT, padx=2)
        self.default_lot_entry = ttk.Entry(lot_frame, width=10)
        self.default_lot_entry.pack(side=tk.LEFT, padx=2)
    
    def create_trading_config(self, parent):
        """Create trading configuration panel"""
        frame = ttk.LabelFrame(parent, text="Trading Settings", padding=5)
        frame.pack(fill=tk.X, pady=5)
        
        # Auto trading
        self.auto_trade_var = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Enable Auto Trading", variable=self.auto_trade_var).pack(anchor=tk.W)
        
        # Trade directions
        direction_frame = ttk.Frame(frame)
        direction_frame.pack(fill=tk.X, pady=5)
        
        self.allow_buy_var = tk.BooleanVar(value=True)
        self.allow_sell_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(direction_frame, text="Allow BUY", variable=self.allow_buy_var).pack(anchor=tk.W)
        ttk.Checkbutton(direction_frame, text="Allow SELL", variable=self.allow_sell_var).pack(anchor=tk.W)
        
        # Paper trading
        self.paper_trading_var = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Paper Trading Mode", variable=self.paper_trading_var).pack(anchor=tk.W)
        
        # Refresh interval
        interval_frame = ttk.Frame(frame)
        interval_frame.pack(fill=tk.X, pady=2)
        ttk.Label(interval_frame, text="Refresh Interval (s):", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.refresh_interval_entry = ttk.Entry(interval_frame, width=12)
        self.refresh_interval_entry.pack(side=tk.LEFT, padx=2)
        
        # Initial capital (for intraday - used for quantity calculation)
        capital_frame = ttk.Frame(frame)
        capital_frame.pack(fill=tk.X, pady=2)
        ttk.Label(capital_frame, text="Initial Capital (₹):", width=22, anchor=tk.W).pack(side=tk.LEFT)
        self.intraday_initial_capital_entry = ttk.Entry(capital_frame, width=12)
        backtest_config = self.config.get('backtest', {})
        self.intraday_initial_capital_entry.insert(0, str(backtest_config.get('initial_capital', 20000)))
        self.intraday_initial_capital_entry.pack(side=tk.LEFT, padx=2)
        
        # Max allowed quantity
        qty_frame = ttk.Frame(frame)
        qty_frame.pack(fill=tk.X, pady=2)
        ttk.Label(qty_frame, text="Max Allowed Quantity:", width=22, anchor=tk.W).pack(side=tk.LEFT)
        self.default_quantity_entry = ttk.Entry(qty_frame, width=12)
        self.default_quantity_entry.pack(side=tk.LEFT, padx=2)
        
        # Show calculated max quantity hint
        hint_text = "💡 Quantity is calculated dynamically based on capital and lot size, capped at max allowed"
        self.default_quantity_hint = ttk.Label(frame, text=hint_text, font=("Arial", 7), foreground="gray")
        self.default_quantity_hint.pack(anchor=tk.W, pady=(0, 2))
    
    def create_indicators_config(self, parent):
        """Create indicators configuration panel"""
        frame = ttk.LabelFrame(parent, text="Indicators", padding=5)
        frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Scrollable frame for indicators
        canvas = tk.Canvas(frame, height=200)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.indicator_vars = {}
        self.indicator_widgets = {}
        
        # Load indicators from config
        indicators_config = self.config.get('indicators', {})
        for ind_name, ind_config in indicators_config.items():
            self.create_indicator_control(scrollable_frame, ind_name, ind_config)
    
    def create_indicator_control(self, parent, name: str, config: dict):
        """Create control for a single indicator"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        
        # Enable checkbox
        var = tk.BooleanVar(value=config.get('enabled', False))
        self.indicator_vars[name] = {'enabled': var}
        ttk.Checkbutton(frame, text=name, variable=var).pack(side=tk.LEFT)
        
        # Weight
        ttk.Label(frame, text="Weight:").pack(side=tk.LEFT, padx=5)
        weight_entry = ttk.Entry(frame, width=8)
        weight_entry.insert(0, str(config.get('weight', 1.0)))
        weight_entry.pack(side=tk.LEFT, padx=2)
        self.indicator_vars[name]['weight'] = weight_entry
        
        # Store widget references
        self.indicator_widgets[name] = frame
    
    def create_risk_config(self, parent):
        """Create risk management configuration panel"""
        frame = ttk.LabelFrame(parent, text="Risk Management", padding=5)
        frame.pack(fill=tk.X, pady=5)
        
        risk_config = self.config.get('risk_management', {})
        
        # Risk per trade
        risk_frame = ttk.Frame(frame)
        risk_frame.pack(fill=tk.X, pady=2)
        ttk.Label(risk_frame, text="Risk Per Trade (%):", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.risk_per_trade_entry = ttk.Entry(risk_frame, width=12)
        self.risk_per_trade_entry.insert(0, str(risk_config.get('risk_per_trade_pct', 0.8)))
        self.risk_per_trade_entry.pack(side=tk.LEFT, padx=2)
        
        # Max position size
        pos_frame = ttk.Frame(frame)
        pos_frame.pack(fill=tk.X, pady=2)
        ttk.Label(pos_frame, text="Max Position Size:", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.max_position_entry = ttk.Entry(pos_frame, width=12)
        self.max_position_entry.insert(0, str(risk_config.get('max_position_size', 100)))
        self.max_position_entry.pack(side=tk.LEFT, padx=2)
        
        # Stop loss
        sl_frame = ttk.LabelFrame(frame, text="Stop Loss", padding=5)
        sl_frame.pack(fill=tk.X, pady=2)
        
        sl_config = risk_config.get('stop_loss', {})
        max_loss_frame = ttk.Frame(sl_frame)
        max_loss_frame.pack(fill=tk.X, pady=2)
        ttk.Label(max_loss_frame, text="Max Loss/Trade (₹):", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.max_loss_entry = ttk.Entry(max_loss_frame, width=12)
        self.max_loss_entry.insert(0, str(sl_config.get('max_loss_per_trade', 300)))
        self.max_loss_entry.pack(side=tk.LEFT, padx=2)
        
        atr_frame = ttk.Frame(sl_frame)
        atr_frame.pack(fill=tk.X, pady=2)
        ttk.Label(atr_frame, text="ATR Multiplier:", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.sl_atr_multiplier_entry = ttk.Entry(atr_frame, width=12)
        self.sl_atr_multiplier_entry.insert(0, str(sl_config.get('atr_multiplier', 1.5)))
        self.sl_atr_multiplier_entry.pack(side=tk.LEFT, padx=2)
        
        min_stop_frame = ttk.Frame(sl_frame)
        min_stop_frame.pack(fill=tk.X, pady=2)
        ttk.Label(min_stop_frame, text="Min Stop %:", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.sl_min_pct_entry = ttk.Entry(min_stop_frame, width=12)
        self.sl_min_pct_entry.insert(0, str(sl_config.get('min_stop_pct', 0.5)))
        self.sl_min_pct_entry.pack(side=tk.LEFT, padx=2)
        
        max_stop_frame = ttk.Frame(sl_frame)
        max_stop_frame.pack(fill=tk.X, pady=2)
        ttk.Label(max_stop_frame, text="Max Stop %:", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.sl_max_pct_entry = ttk.Entry(max_stop_frame, width=12)
        self.sl_max_pct_entry.insert(0, str(sl_config.get('max_stop_pct', 3.0)))
        self.sl_max_pct_entry.pack(side=tk.LEFT, padx=2)
        
        # Breakeven stop
        be_frame = ttk.Frame(sl_frame)
        be_frame.pack(fill=tk.X, pady=2)
        self.sl_breakeven_var = tk.BooleanVar(value=sl_config.get('breakeven_enabled', True))
        ttk.Checkbutton(be_frame, text="Breakeven Enabled", variable=self.sl_breakeven_var).pack(side=tk.LEFT)
        be_ratio_frame = ttk.Frame(sl_frame)
        be_ratio_frame.pack(fill=tk.X, pady=2)
        ttk.Label(be_ratio_frame, text="Breakeven Trigger Ratio:", width=22, anchor=tk.W).pack(side=tk.LEFT)
        self.sl_breakeven_ratio_entry = ttk.Entry(be_ratio_frame, width=10)
        self.sl_breakeven_ratio_entry.insert(0, str(sl_config.get('breakeven_trigger_ratio', 1.0)))
        self.sl_breakeven_ratio_entry.pack(side=tk.LEFT, padx=2)
        
        # Profit Targets
        pt_frame = ttk.LabelFrame(frame, text="Profit Targets", padding=5)
        pt_frame.pack(fill=tk.X, pady=2)
        
        pt_config = risk_config.get('profit_targets', {})
        self.profit_targets_enabled_var = tk.BooleanVar(value=pt_config.get('enabled', True))
        ttk.Checkbutton(pt_frame, text="Enable Profit Targets", variable=self.profit_targets_enabled_var).pack(side=tk.LEFT)
        
        # Target 1
        t1_frame = ttk.Frame(pt_frame)
        t1_frame.pack(fill=tk.X, pady=2)
        ttk.Label(t1_frame, text="Target 1 - Ratio:", width=16, anchor=tk.W).pack(side=tk.LEFT)
        self.pt_target1_ratio_entry = ttk.Entry(t1_frame, width=8)
        self.pt_target1_ratio_entry.insert(0, str(pt_config.get('target_1', {}).get('ratio', 1.5)))
        self.pt_target1_ratio_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(t1_frame, text="Exit %:", width=8, anchor=tk.W).pack(side=tk.LEFT, padx=2)
        self.pt_target1_exit_entry = ttk.Entry(t1_frame, width=8)
        self.pt_target1_exit_entry.insert(0, str(pt_config.get('target_1', {}).get('exit_pct', 80)))
        self.pt_target1_exit_entry.pack(side=tk.LEFT, padx=2)
        
        # Target 2
        t2_frame = ttk.Frame(pt_frame)
        t2_frame.pack(fill=tk.X, pady=2)
        ttk.Label(t2_frame, text="Target 2 - Ratio:", width=16, anchor=tk.W).pack(side=tk.LEFT)
        self.pt_target2_ratio_entry = ttk.Entry(t2_frame, width=8)
        self.pt_target2_ratio_entry.insert(0, str(pt_config.get('target_2', {}).get('ratio', 2.0)))
        self.pt_target2_ratio_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(t2_frame, text="Exit %:", width=8, anchor=tk.W).pack(side=tk.LEFT, padx=2)
        self.pt_target2_exit_entry = ttk.Entry(t2_frame, width=8)
        self.pt_target2_exit_entry.insert(0, str(pt_config.get('target_2', {}).get('exit_pct', 50)))
        self.pt_target2_exit_entry.pack(side=tk.LEFT, padx=2)
        
        # Target 3
        t3_frame = ttk.Frame(pt_frame)
        t3_frame.pack(fill=tk.X, pady=2)
        ttk.Label(t3_frame, text="Target 3 - Ratio:", width=16, anchor=tk.W).pack(side=tk.LEFT)
        self.pt_target3_ratio_entry = ttk.Entry(t3_frame, width=8)
        self.pt_target3_ratio_entry.insert(0, str(pt_config.get('target_3', {}).get('ratio', 3.0)))
        self.pt_target3_ratio_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(t3_frame, text="Exit %:", width=8, anchor=tk.W).pack(side=tk.LEFT, padx=2)
        self.pt_target3_exit_entry = ttk.Entry(t3_frame, width=8)
        self.pt_target3_exit_entry.insert(0, str(pt_config.get('target_3', {}).get('exit_pct', 20)))
        self.pt_target3_exit_entry.pack(side=tk.LEFT, padx=2)
        
        # Trailing Stop
        ts_frame = ttk.LabelFrame(frame, text="Trailing Stop", padding=5)
        ts_frame.pack(fill=tk.X, pady=2)
        
        ts_config = risk_config.get('trailing_stop', {})
        self.trailing_stop_enabled_var = tk.BooleanVar(value=ts_config.get('enabled', True))
        ttk.Checkbutton(ts_frame, text="Enable Trailing Stop", variable=self.trailing_stop_enabled_var).pack(anchor=tk.W, pady=2)
        ts_act_frame = ttk.Frame(ts_frame)
        ts_act_frame.pack(fill=tk.X, pady=2)
        ttk.Label(ts_act_frame, text="Activation Ratio:", width=22, anchor=tk.W).pack(side=tk.LEFT)
        self.ts_activation_ratio_entry = ttk.Entry(ts_act_frame, width=10)
        self.ts_activation_ratio_entry.insert(0, str(ts_config.get('activation_ratio', 1.0)))
        self.ts_activation_ratio_entry.pack(side=tk.LEFT, padx=2)
        ts_atr_frame = ttk.Frame(ts_frame)
        ts_atr_frame.pack(fill=tk.X, pady=2)
        ttk.Label(ts_atr_frame, text="Trail ATR Multiplier:", width=22, anchor=tk.W).pack(side=tk.LEFT)
        self.ts_atr_multiplier_entry = ttk.Entry(ts_atr_frame, width=10)
        self.ts_atr_multiplier_entry.insert(0, str(ts_config.get('trail_atr_multiplier', 1.0)))
        self.ts_atr_multiplier_entry.pack(side=tk.LEFT, padx=2)
        
        # Time Exit
        te_frame = ttk.LabelFrame(frame, text="Time-Based Exit", padding=5)
        te_frame.pack(fill=tk.X, pady=2)
        
        te_config = risk_config.get('time_exit', {})
        self.time_exit_enabled_var = tk.BooleanVar(value=te_config.get('enabled', True))
        ttk.Checkbutton(te_frame, text="Enable Time Exit", variable=self.time_exit_enabled_var).pack(anchor=tk.W, pady=2)
        te_hold_frame = ttk.Frame(te_frame)
        te_hold_frame.pack(fill=tk.X, pady=2)
        ttk.Label(te_hold_frame, text="Max Hold (minutes):", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.te_max_hold_entry = ttk.Entry(te_hold_frame, width=12)
        self.te_max_hold_entry.insert(0, str(te_config.get('max_hold_minutes', 60)))
        self.te_max_hold_entry.pack(side=tk.LEFT, padx=2)
        self.te_force_close_eod_var = tk.BooleanVar(value=te_config.get('force_close_eod', True))
        ttk.Checkbutton(te_frame, text="Force Close EOD", variable=self.te_force_close_eod_var).pack(anchor=tk.W, pady=2)
        
        # Daily limits
        daily_frame = ttk.LabelFrame(frame, text="Daily Limits", padding=5)
        daily_frame.pack(fill=tk.X, pady=2)
        
        daily_config = risk_config.get('daily_limits', {})
        daily_loss_frame = ttk.Frame(daily_frame)
        daily_loss_frame.pack(fill=tk.X, pady=2)
        ttk.Label(daily_loss_frame, text="Max Daily Loss (₹):", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.max_daily_loss_entry = ttk.Entry(daily_loss_frame, width=12)
        self.max_daily_loss_entry.insert(0, str(daily_config.get('max_loss_amount', 2000)))
        self.max_daily_loss_entry.pack(side=tk.LEFT, padx=2)
        
        daily_trades_frame = ttk.Frame(daily_frame)
        daily_trades_frame.pack(fill=tk.X, pady=2)
        ttk.Label(daily_trades_frame, text="Max Trades/Day:", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.max_trades_entry = ttk.Entry(daily_trades_frame, width=12)
        self.max_trades_entry.insert(0, str(daily_config.get('max_trades_per_day', 200)))
        self.max_trades_entry.pack(side=tk.LEFT, padx=2)
    
    def create_intraday_results(self, parent):
        """Create intraday results panel"""
        # Control buttons
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, pady=5)
        
        self.start_intraday_btn = ttk.Button(control_frame, text="Start Intraday", command=self.start_intraday)
        self.start_intraday_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_intraday_btn = ttk.Button(control_frame, text="Stop Intraday", command=self.stop_intraday, state=tk.DISABLED)
        self.stop_intraday_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="Save Config", command=self.save_config_from_ui).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Reload Config", command=self.reload_config).pack(side=tk.LEFT, padx=5)
        
        # Status
        status_frame = ttk.LabelFrame(parent, text="Status", padding=5)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="Ready", font=("Arial", 10, "bold"))
        self.status_label.pack(anchor=tk.W)
        
        # Symbol LTP table (real-time prices)
        ltp_frame = ttk.LabelFrame(parent, text="Symbol Prices (LTP)", padding=5)
        ltp_frame.pack(fill=tk.X, pady=5)
        
        self.ltp_tree = ttk.Treeview(ltp_frame, columns=("Symbol", "LTP", "Signal", "Change"), show="headings", height=4)
        for col in ("Symbol", "LTP", "Signal", "Change"):
            self.ltp_tree.heading(col, text=col)
            self.ltp_tree.column(col, width=100)
        
        # Configure tags for LTP table
        self.ltp_tree.tag_configure("profit", background="#d4edda", foreground="#155724")
        self.ltp_tree.tag_configure("loss", background="#f8d7da", foreground="#721c24")
        self.ltp_tree.tag_configure("neutral", background="#ffffff")
        
        ltp_scroll = ttk.Scrollbar(ltp_frame, orient=tk.VERTICAL, command=self.ltp_tree.yview)
        self.ltp_tree.configure(yscrollcommand=ltp_scroll.set)
        self.ltp_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ltp_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind double-click event to show price trend
        self.ltp_tree.bind("<Double-1>", self.on_symbol_click)
        
        # Add hint label
        hint_label = ttk.Label(ltp_frame, text="💡 Double-click on any symbol to view its price trend chart", 
                              font=("Arial", 8), foreground="gray")
        hint_label.pack(pady=2)
        
        # Positions table
        positions_frame = ttk.LabelFrame(parent, text="Open Positions", padding=5)
        positions_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.positions_tree = ttk.Treeview(positions_frame, columns=("Symbol", "Type", "Entry", "Qty", "LTP", "PnL"), show="headings", height=8)
        for col in ("Symbol", "Type", "Entry", "Qty", "LTP", "PnL"):
            self.positions_tree.heading(col, text=col)
            self.positions_tree.column(col, width=100)
        
        # Configure tags for positions table
        self.positions_tree.tag_configure("profit", background="#d4edda", foreground="#155724")
        self.positions_tree.tag_configure("loss", background="#f8d7da", foreground="#721c24")
        self.positions_tree.tag_configure("neutral", background="#ffffff")
        
        positions_scroll = ttk.Scrollbar(positions_frame, orient=tk.VERTICAL, command=self.positions_tree.yview)
        self.positions_tree.configure(yscrollcommand=positions_scroll.set)
        self.positions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        positions_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Completed trades table
        trades_frame = ttk.LabelFrame(parent, text="Completed Trades", padding=5)
        trades_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.trades_tree = ttk.Treeview(trades_frame, columns=("ID", "Symbol", "Type", "Entry", "Exit", "Qty", "PnL", "Return%", "Entry Time", "Exit Time", "Exit Reason"), show="headings", height=8)
        for col in ("ID", "Symbol", "Type", "Entry", "Exit", "Qty", "PnL", "Return%", "Entry Time", "Exit Time", "Exit Reason"):
            self.trades_tree.heading(col, text=col)
            if col == "Exit Reason":
                self.trades_tree.column(col, width=200)
            elif col in ("Entry Time", "Exit Time"):
                self.trades_tree.column(col, width=140)
            else:
                self.trades_tree.column(col, width=80)
        
        # Configure tags for trades table
        self.trades_tree.tag_configure("profit", background="#d4edda", foreground="#155724")
        self.trades_tree.tag_configure("loss", background="#f8d7da", foreground="#721c24")
        self.trades_tree.tag_configure("neutral", background="#ffffff")
        
        trades_scroll = ttk.Scrollbar(trades_frame, orient=tk.VERTICAL, command=self.trades_tree.yview)
        self.trades_tree.configure(yscrollcommand=trades_scroll.set)
        self.trades_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        trades_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Performance summary (detailed table)
        perf_frame = ttk.LabelFrame(parent, text="Performance Summary", padding=5)
        perf_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        summary_table_frame = ttk.Frame(perf_frame)
        summary_table_frame.pack(fill=tk.BOTH, expand=True)
        
        self.intraday_summary_tree = ttk.Treeview(summary_table_frame, columns=("Metric", "Value"), show="headings", height=15)
        self.intraday_summary_tree.heading("Metric", text="Metric", anchor=tk.W)
        self.intraday_summary_tree.heading("Value", text="Value", anchor=tk.E)
        self.intraday_summary_tree.column("Metric", width=320, anchor=tk.W)
        self.intraday_summary_tree.column("Value", width=220, anchor=tk.E)
        
        # Configure tags for color coding
        self.intraday_summary_tree.tag_configure("category", background="#e8e8e8", foreground="#000000", font=("Arial", 9, "bold"))
        self.intraday_summary_tree.tag_configure("profit", background="#d4edda", foreground="#155724", font=("Arial", 9))
        self.intraday_summary_tree.tag_configure("loss", background="#f8d7da", foreground="#721c24", font=("Arial", 9))
        self.intraday_summary_tree.tag_configure("neutral", background="#ffffff", foreground="#000000", font=("Arial", 9))
        self.intraday_summary_tree.tag_configure("positive", background="#d1ecf1", foreground="#0c5460", font=("Arial", 9))
        self.intraday_summary_tree.tag_configure("negative", background="#f8d7da", foreground="#721c24", font=("Arial", 9))
        
        summary_scroll = ttk.Scrollbar(summary_table_frame, orient=tk.VERTICAL, command=self.intraday_summary_tree.yview)
        self.intraday_summary_tree.configure(yscrollcommand=summary_scroll.set)
        self.intraday_summary_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        summary_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_backtest_symbols_config(self, parent):
        """Create symbols configuration panel for backtest"""
        frame = ttk.LabelFrame(parent, text="Symbols", padding=5)
        frame.pack(fill=tk.X, pady=5)
        
        # Symbols listbox with scrollbar
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.backtest_symbols_listbox = tk.Listbox(list_frame, height=4, yscrollcommand=scrollbar.set)
        self.backtest_symbols_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.backtest_symbols_listbox.yview)
        
        # Add/Remove symbols
        symbol_controls = ttk.Frame(frame)
        symbol_controls.pack(fill=tk.X, pady=5)
        
        self.backtest_symbol_entry = ttk.Entry(symbol_controls, width=30)
        self.backtest_symbol_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(symbol_controls, text="Add", command=self.add_backtest_symbol).pack(side=tk.LEFT, padx=2)
        ttk.Button(symbol_controls, text="Remove", command=self.remove_backtest_symbol).pack(side=tk.LEFT, padx=2)
    
    def create_backtest_trading_config(self, parent):
        """Create trading configuration panel for backtest"""
        frame = ttk.LabelFrame(parent, text="Trading Settings", padding=5)
        frame.pack(fill=tk.X, pady=5)
        
        # Auto trading
        self.backtest_auto_trade_var = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Enable Auto Trading", variable=self.backtest_auto_trade_var).pack(anchor=tk.W)
        
        # Trade directions
        direction_frame = ttk.Frame(frame)
        direction_frame.pack(fill=tk.X, pady=5)
        
        self.backtest_allow_buy_var = tk.BooleanVar(value=True)
        self.backtest_allow_sell_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(direction_frame, text="Allow BUY", variable=self.backtest_allow_buy_var).pack(anchor=tk.W)
        ttk.Checkbutton(direction_frame, text="Allow SELL", variable=self.backtest_allow_sell_var).pack(anchor=tk.W)
        
        # Max allowed quantity
        qty_frame = ttk.Frame(frame)
        qty_frame.pack(fill=tk.X, pady=2)
        ttk.Label(qty_frame, text="Max Allowed Quantity:", width=22, anchor=tk.W).pack(side=tk.LEFT)
        self.backtest_default_quantity_entry = ttk.Entry(qty_frame, width=12)
        trading = self.config.get('trading', {})
        self.backtest_default_quantity_entry.insert(0, str(trading.get('default_quantity', 300)))
        self.backtest_default_quantity_entry.pack(side=tk.LEFT, padx=2)
        
        # Show calculated max quantity hint
        hint_text = "💡 Quantity is calculated dynamically based on capital and lot size, capped at max allowed"
        self.backtest_default_quantity_hint = ttk.Label(frame, text=hint_text, font=("Arial", 7), foreground="gray")
        self.backtest_default_quantity_hint.pack(anchor=tk.W, pady=(0, 2))
    
    def create_backtest_indicators_config(self, parent):
        """Create indicators configuration panel for backtest"""
        frame = ttk.LabelFrame(parent, text="Indicators", padding=5)
        frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Scrollable frame for indicators
        canvas = tk.Canvas(frame, height=150)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.backtest_indicator_vars = {}
        self.backtest_indicator_widgets = {}
        
        # Load indicators from config
        indicators_config = self.config.get('indicators', {})
        for ind_name, ind_config in indicators_config.items():
            self.create_backtest_indicator_control(scrollable_frame, ind_name, ind_config)
    
    def create_backtest_indicator_control(self, parent, name: str, config: dict):
        """Create control for a single indicator in backtest"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        
        # Enable checkbox
        var = tk.BooleanVar(value=config.get('enabled', False))
        self.backtest_indicator_vars[name] = {'enabled': var}
        ttk.Checkbutton(frame, text=name, variable=var).pack(side=tk.LEFT)
        
        # Weight
        ttk.Label(frame, text="Weight:").pack(side=tk.LEFT, padx=5)
        weight_entry = ttk.Entry(frame, width=8)
        weight_entry.insert(0, str(config.get('weight', 1.0)))
        weight_entry.pack(side=tk.LEFT, padx=2)
        self.backtest_indicator_vars[name]['weight'] = weight_entry
        
        # Store widget references
        self.backtest_indicator_widgets[name] = frame
    
    def create_backtest_risk_config(self, parent):
        """Create risk management configuration panel for backtest"""
        frame = ttk.LabelFrame(parent, text="Risk Management", padding=5)
        frame.pack(fill=tk.X, pady=5)
        
        risk_config = self.config.get('risk_management', {})
        
        # Risk per trade
        risk_frame = ttk.Frame(frame)
        risk_frame.pack(fill=tk.X, pady=2)
        ttk.Label(risk_frame, text="Risk Per Trade (%):", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.backtest_risk_per_trade_entry = ttk.Entry(risk_frame, width=12)
        self.backtest_risk_per_trade_entry.insert(0, str(risk_config.get('risk_per_trade_pct', 0.8)))
        self.backtest_risk_per_trade_entry.pack(side=tk.LEFT, padx=2)
        
        # Max position size
        pos_frame = ttk.Frame(frame)
        pos_frame.pack(fill=tk.X, pady=2)
        ttk.Label(pos_frame, text="Max Position Size:", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.backtest_max_position_entry = ttk.Entry(pos_frame, width=12)
        self.backtest_max_position_entry.insert(0, str(risk_config.get('max_position_size', 100)))
        self.backtest_max_position_entry.pack(side=tk.LEFT, padx=2)
        
        # Stop loss
        sl_frame = ttk.LabelFrame(frame, text="Stop Loss", padding=5)
        sl_frame.pack(fill=tk.X, pady=2)
        
        sl_config = risk_config.get('stop_loss', {})
        max_loss_frame = ttk.Frame(sl_frame)
        max_loss_frame.pack(fill=tk.X, pady=2)
        ttk.Label(max_loss_frame, text="Max Loss/Trade (₹):", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.backtest_max_loss_entry = ttk.Entry(max_loss_frame, width=12)
        self.backtest_max_loss_entry.insert(0, str(sl_config.get('max_loss_per_trade', 300)))
        self.backtest_max_loss_entry.pack(side=tk.LEFT, padx=2)
        
        atr_frame = ttk.Frame(sl_frame)
        atr_frame.pack(fill=tk.X, pady=2)
        ttk.Label(atr_frame, text="ATR Multiplier:", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.backtest_sl_atr_multiplier_entry = ttk.Entry(atr_frame, width=12)
        self.backtest_sl_atr_multiplier_entry.insert(0, str(sl_config.get('atr_multiplier', 1.5)))
        self.backtest_sl_atr_multiplier_entry.pack(side=tk.LEFT, padx=2)
        
        min_stop_frame = ttk.Frame(sl_frame)
        min_stop_frame.pack(fill=tk.X, pady=2)
        ttk.Label(min_stop_frame, text="Min Stop %:", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.backtest_sl_min_pct_entry = ttk.Entry(min_stop_frame, width=12)
        self.backtest_sl_min_pct_entry.insert(0, str(sl_config.get('min_stop_pct', 0.5)))
        self.backtest_sl_min_pct_entry.pack(side=tk.LEFT, padx=2)
        
        max_stop_frame = ttk.Frame(sl_frame)
        max_stop_frame.pack(fill=tk.X, pady=2)
        ttk.Label(max_stop_frame, text="Max Stop %:", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.backtest_sl_max_pct_entry = ttk.Entry(max_stop_frame, width=12)
        self.backtest_sl_max_pct_entry.insert(0, str(sl_config.get('max_stop_pct', 3.0)))
        self.backtest_sl_max_pct_entry.pack(side=tk.LEFT, padx=2)
        
        # Breakeven stop
        be_frame = ttk.Frame(sl_frame)
        be_frame.pack(fill=tk.X, pady=2)
        self.backtest_sl_breakeven_var = tk.BooleanVar(value=sl_config.get('breakeven_enabled', True))
        ttk.Checkbutton(be_frame, text="Breakeven Enabled", variable=self.backtest_sl_breakeven_var).pack(side=tk.LEFT)
        be_ratio_frame = ttk.Frame(sl_frame)
        be_ratio_frame.pack(fill=tk.X, pady=2)
        ttk.Label(be_ratio_frame, text="Breakeven Trigger Ratio:", width=22, anchor=tk.W).pack(side=tk.LEFT)
        self.backtest_sl_breakeven_ratio_entry = ttk.Entry(be_ratio_frame, width=10)
        self.backtest_sl_breakeven_ratio_entry.insert(0, str(sl_config.get('breakeven_trigger_ratio', 1.0)))
        self.backtest_sl_breakeven_ratio_entry.pack(side=tk.LEFT, padx=2)
        
        # Profit Targets
        pt_frame = ttk.LabelFrame(frame, text="Profit Targets", padding=5)
        pt_frame.pack(fill=tk.X, pady=2)
        
        pt_config = risk_config.get('profit_targets', {})
        self.backtest_profit_targets_enabled_var = tk.BooleanVar(value=pt_config.get('enabled', True))
        ttk.Checkbutton(pt_frame, text="Enable Profit Targets", variable=self.backtest_profit_targets_enabled_var).pack(side=tk.LEFT)
        
        # Target 1
        t1_frame = ttk.Frame(pt_frame)
        t1_frame.pack(fill=tk.X, pady=2)
        ttk.Label(t1_frame, text="Target 1 - Ratio:", width=16, anchor=tk.W).pack(side=tk.LEFT)
        self.backtest_pt_target1_ratio_entry = ttk.Entry(t1_frame, width=8)
        self.backtest_pt_target1_ratio_entry.insert(0, str(pt_config.get('target_1', {}).get('ratio', 1.5)))
        self.backtest_pt_target1_ratio_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(t1_frame, text="Exit %:", width=8, anchor=tk.W).pack(side=tk.LEFT, padx=2)
        self.backtest_pt_target1_exit_entry = ttk.Entry(t1_frame, width=8)
        self.backtest_pt_target1_exit_entry.insert(0, str(pt_config.get('target_1', {}).get('exit_pct', 80)))
        self.backtest_pt_target1_exit_entry.pack(side=tk.LEFT, padx=2)
        
        # Target 2
        t2_frame = ttk.Frame(pt_frame)
        t2_frame.pack(fill=tk.X, pady=2)
        ttk.Label(t2_frame, text="Target 2 - Ratio:", width=16, anchor=tk.W).pack(side=tk.LEFT)
        self.backtest_pt_target2_ratio_entry = ttk.Entry(t2_frame, width=8)
        self.backtest_pt_target2_ratio_entry.insert(0, str(pt_config.get('target_2', {}).get('ratio', 2.0)))
        self.backtest_pt_target2_ratio_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(t2_frame, text="Exit %:", width=8, anchor=tk.W).pack(side=tk.LEFT, padx=2)
        self.backtest_pt_target2_exit_entry = ttk.Entry(t2_frame, width=8)
        self.backtest_pt_target2_exit_entry.insert(0, str(pt_config.get('target_2', {}).get('exit_pct', 50)))
        self.backtest_pt_target2_exit_entry.pack(side=tk.LEFT, padx=2)
        
        # Target 3
        t3_frame = ttk.Frame(pt_frame)
        t3_frame.pack(fill=tk.X, pady=2)
        ttk.Label(t3_frame, text="Target 3 - Ratio:", width=16, anchor=tk.W).pack(side=tk.LEFT)
        self.backtest_pt_target3_ratio_entry = ttk.Entry(t3_frame, width=8)
        self.backtest_pt_target3_ratio_entry.insert(0, str(pt_config.get('target_3', {}).get('ratio', 3.0)))
        self.backtest_pt_target3_ratio_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(t3_frame, text="Exit %:", width=8, anchor=tk.W).pack(side=tk.LEFT, padx=2)
        self.backtest_pt_target3_exit_entry = ttk.Entry(t3_frame, width=8)
        self.backtest_pt_target3_exit_entry.insert(0, str(pt_config.get('target_3', {}).get('exit_pct', 20)))
        self.backtest_pt_target3_exit_entry.pack(side=tk.LEFT, padx=2)
        
        # Trailing Stop
        ts_frame = ttk.LabelFrame(frame, text="Trailing Stop", padding=5)
        ts_frame.pack(fill=tk.X, pady=2)
        
        ts_config = risk_config.get('trailing_stop', {})
        self.backtest_trailing_stop_enabled_var = tk.BooleanVar(value=ts_config.get('enabled', True))
        ttk.Checkbutton(ts_frame, text="Enable Trailing Stop", variable=self.backtest_trailing_stop_enabled_var).pack(anchor=tk.W, pady=2)
        ts_act_frame = ttk.Frame(ts_frame)
        ts_act_frame.pack(fill=tk.X, pady=2)
        ttk.Label(ts_act_frame, text="Activation Ratio:", width=22, anchor=tk.W).pack(side=tk.LEFT)
        self.backtest_ts_activation_ratio_entry = ttk.Entry(ts_act_frame, width=10)
        self.backtest_ts_activation_ratio_entry.insert(0, str(ts_config.get('activation_ratio', 1.0)))
        self.backtest_ts_activation_ratio_entry.pack(side=tk.LEFT, padx=2)
        ts_atr_frame = ttk.Frame(ts_frame)
        ts_atr_frame.pack(fill=tk.X, pady=2)
        ttk.Label(ts_atr_frame, text="Trail ATR Multiplier:", width=22, anchor=tk.W).pack(side=tk.LEFT)
        self.backtest_ts_atr_multiplier_entry = ttk.Entry(ts_atr_frame, width=10)
        self.backtest_ts_atr_multiplier_entry.insert(0, str(ts_config.get('trail_atr_multiplier', 1.0)))
        self.backtest_ts_atr_multiplier_entry.pack(side=tk.LEFT, padx=2)
        
        # Time Exit
        te_frame = ttk.LabelFrame(frame, text="Time-Based Exit", padding=5)
        te_frame.pack(fill=tk.X, pady=2)
        
        te_config = risk_config.get('time_exit', {})
        self.backtest_time_exit_enabled_var = tk.BooleanVar(value=te_config.get('enabled', True))
        ttk.Checkbutton(te_frame, text="Enable Time Exit", variable=self.backtest_time_exit_enabled_var).pack(anchor=tk.W, pady=2)
        te_hold_frame = ttk.Frame(te_frame)
        te_hold_frame.pack(fill=tk.X, pady=2)
        ttk.Label(te_hold_frame, text="Max Hold (minutes):", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.backtest_te_max_hold_entry = ttk.Entry(te_hold_frame, width=12)
        self.backtest_te_max_hold_entry.insert(0, str(te_config.get('max_hold_minutes', 60)))
        self.backtest_te_max_hold_entry.pack(side=tk.LEFT, padx=2)
        self.backtest_te_force_close_eod_var = tk.BooleanVar(value=te_config.get('force_close_eod', True))
        ttk.Checkbutton(te_frame, text="Force Close EOD", variable=self.backtest_te_force_close_eod_var).pack(anchor=tk.W, pady=2)
    
    def create_backtest_config(self, parent):
        """Create backtest configuration panel"""
        frame = ttk.LabelFrame(parent, text="Backtest Settings", padding=5)
        frame.pack(fill=tk.X, pady=5)
        
        # Date range
        date_frame = ttk.Frame(frame)
        date_frame.pack(fill=tk.X, pady=2)
        ttk.Label(date_frame, text="Start Date:", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.backtest_start_entry = ttk.Entry(date_frame, width=20)
        self.backtest_start_entry.pack(side=tk.LEFT, padx=2)
        
        date_frame2 = ttk.Frame(frame)
        date_frame2.pack(fill=tk.X, pady=2)
        ttk.Label(date_frame2, text="End Date:", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.backtest_end_entry = ttk.Entry(date_frame2, width=20)
        self.backtest_end_entry.pack(side=tk.LEFT, padx=2)
        
        # Initial capital
        capital_frame = ttk.Frame(frame)
        capital_frame.pack(fill=tk.X, pady=2)
        ttk.Label(capital_frame, text="Initial Capital (₹):", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.initial_capital_entry = ttk.Entry(capital_frame, width=20)
        self.initial_capital_entry.pack(side=tk.LEFT, padx=2)
        
        # Speed
        speed_frame = ttk.Frame(frame)
        speed_frame.pack(fill=tk.X, pady=2)
        ttk.Label(speed_frame, text="Speed:", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.speed_var = tk.StringVar(value="fast")
        ttk.Radiobutton(speed_frame, text="Fast", variable=self.speed_var, value="fast").pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(speed_frame, text="Real-time", variable=self.speed_var, value="realtime").pack(side=tk.LEFT, padx=2)
        
        # Resolution
        res_frame = ttk.Frame(frame)
        res_frame.pack(fill=tk.X, pady=2)
        ttk.Label(res_frame, text="Resolution:", width=20, anchor=tk.W).pack(side=tk.LEFT)
        self.resolution_entry = ttk.Entry(res_frame, width=20)
        self.resolution_entry.pack(side=tk.LEFT, padx=2)
        
        # Control buttons
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, pady=10)
        
        self.start_backtest_btn = ttk.Button(control_frame, text="Start Backtest", command=self.start_backtest)
        self.start_backtest_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_backtest_btn = ttk.Button(control_frame, text="Stop Backtest", command=self.stop_backtest, state=tk.DISABLED)
        self.stop_backtest_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="Save Config", command=self.save_config_from_ui).pack(side=tk.LEFT, padx=5)
    
    def create_backtest_results(self, parent):
        """Create backtest results panel"""
        # Status
        status_frame = ttk.LabelFrame(parent, text="Backtest Status", padding=5)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.backtest_status_label = ttk.Label(status_frame, text="Ready", font=("Arial", 10, "bold"))
        self.backtest_status_label.pack(anchor=tk.W)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        # Results table
        results_frame = ttk.LabelFrame(parent, text="Backtest Results", padding=5)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.backtest_tree = ttk.Treeview(results_frame, columns=("ID", "Symbol", "Type", "Entry", "Exit", "Qty", "PnL", "Return%", "Entry Time", "Exit Time", "Exit Reason"), show="headings", height=15)
        for col in ("ID", "Symbol", "Type", "Entry", "Exit", "Qty", "PnL", "Return%", "Entry Time", "Exit Time", "Exit Reason"):
            self.backtest_tree.heading(col, text=col)
            if col == "Exit Reason":
                self.backtest_tree.column(col, width=150)
            elif col in ("Entry Time", "Exit Time"):
                self.backtest_tree.column(col, width=140)
            else:
                self.backtest_tree.column(col, width=80)
        
        # Configure tags for backtest table
        self.backtest_tree.tag_configure("profit", background="#d4edda", foreground="#155724")
        self.backtest_tree.tag_configure("loss", background="#f8d7da", foreground="#721c24")
        self.backtest_tree.tag_configure("neutral", background="#ffffff")
        
        results_scroll = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.backtest_tree.yview)
        self.backtest_tree.configure(yscrollcommand=results_scroll.set)
        self.backtest_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        results_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Summary Table
        summary_frame = ttk.LabelFrame(parent, text="Backtest Summary Metrics", padding=5)
        summary_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create summary table with scrollbar
        summary_table_frame = ttk.Frame(summary_frame)
        summary_table_frame.pack(fill=tk.BOTH, expand=True)
        
        self.backtest_summary_tree = ttk.Treeview(summary_table_frame, columns=("Metric", "Value"), show="headings", height=20)
        self.backtest_summary_tree.heading("Metric", text="Metric", anchor=tk.W)
        self.backtest_summary_tree.heading("Value", text="Value", anchor=tk.E)
        self.backtest_summary_tree.column("Metric", width=320, anchor=tk.W)
        self.backtest_summary_tree.column("Value", width=220, anchor=tk.E)
        
        # Configure tags for color coding
        self.backtest_summary_tree.tag_configure("category", background="#e8e8e8", foreground="#000000", font=("Arial", 9, "bold"))
        self.backtest_summary_tree.tag_configure("profit", background="#d4edda", foreground="#155724", font=("Arial", 9))
        self.backtest_summary_tree.tag_configure("loss", background="#f8d7da", foreground="#721c24", font=("Arial", 9))
        self.backtest_summary_tree.tag_configure("neutral", background="#ffffff", foreground="#000000", font=("Arial", 9))
        self.backtest_summary_tree.tag_configure("positive", background="#d1ecf1", foreground="#0c5460", font=("Arial", 9))
        self.backtest_summary_tree.tag_configure("negative", background="#f8d7da", foreground="#721c24", font=("Arial", 9))
        
        # Bind double-click event for trend viewing
        self.backtest_summary_tree.bind("<Double-1>", self.on_metric_click)
        
        # Add hint label
        hint_label = ttk.Label(summary_frame, text="💡 Double-click on any metric value to view its trend chart", 
                              font=("Arial", 8), foreground="gray")
        hint_label.pack(pady=2)
        
        summary_scroll = ttk.Scrollbar(summary_table_frame, orient=tk.VERTICAL, command=self.backtest_summary_tree.yview)
        self.backtest_summary_tree.configure(yscrollcommand=summary_scroll.set)
        self.backtest_summary_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        summary_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    def load_config_to_ui(self):
        """Load configuration values into UI widgets"""
        # Symbols
        symbols = self.config.get('symbols', [])
        self.symbols_listbox.delete(0, tk.END)
        for symbol in symbols:
            self.symbols_listbox.insert(tk.END, symbol)
        
        # Backtest symbols (use same symbols by default)
        if hasattr(self, 'backtest_symbols_listbox'):
            self.backtest_symbols_listbox.delete(0, tk.END)
            for symbol in symbols:
                self.backtest_symbols_listbox.insert(tk.END, symbol)
        
        # Lot sizes
        lot_sizes = self.config.get('lot_sizes', {})
        self.default_lot_entry.delete(0, tk.END)
        self.default_lot_entry.insert(0, str(lot_sizes.get('default', 20)))
        
        # Trading settings
        trading = self.config.get('trading', {})
        self.auto_trade_var.set(trading.get('enable_auto_trading', False))
        self.allow_buy_var.set(trading.get('allow_buy', True))
        self.allow_sell_var.set(trading.get('allow_sell', False))
        self.paper_trading_var.set(trading.get('paper_trading', True))
        self.refresh_interval_entry.delete(0, tk.END)
        self.refresh_interval_entry.insert(0, str(trading.get('refresh_interval', 5)))
        self.default_quantity_entry.delete(0, tk.END)
        self.default_quantity_entry.insert(0, str(trading.get('default_quantity', 300)))
        
        # Load initial capital for intraday
        if hasattr(self, 'intraday_initial_capital_entry'):
            backtest_config = self.config.get('backtest', {})
            self.intraday_initial_capital_entry.delete(0, tk.END)
            self.intraday_initial_capital_entry.insert(0, str(backtest_config.get('initial_capital', 20000)))
        
        # Backtest trading settings
        if hasattr(self, 'backtest_auto_trade_var'):
            self.backtest_auto_trade_var.set(trading.get('enable_auto_trading', False))
            self.backtest_allow_buy_var.set(trading.get('allow_buy', True))
            self.backtest_allow_sell_var.set(trading.get('allow_sell', False))
            if hasattr(self, 'backtest_default_quantity_entry'):
                self.backtest_default_quantity_entry.delete(0, tk.END)
                self.backtest_default_quantity_entry.insert(0, str(trading.get('default_quantity', 300)))
        
        # Backtest settings
        backtest = self.config.get('backtest', {})
        self.backtest_start_entry.delete(0, tk.END)
        self.backtest_start_entry.insert(0, backtest.get('start_date', '2026-01-06 16:15:00'))
        self.backtest_end_entry.delete(0, tk.END)
        self.backtest_end_entry.insert(0, backtest.get('end_date', '2026-01-08 16:15:00'))
        self.initial_capital_entry.delete(0, tk.END)
        self.initial_capital_entry.insert(0, str(backtest.get('initial_capital', 50000)))
        self.speed_var.set(backtest.get('speed', 'fast'))
        
        # Resolution and date range
        date_range = self.config.get('date_range', {})
        self.resolution_entry.delete(0, tk.END)
        # Resolution can be in date_range or at root level
        resolution = date_range.get('resolution') or self.config.get('resolution', '30S')
        self.resolution_entry.insert(0, resolution)
    
    def save_config_from_ui(self):
        """Save configuration from UI to YAML file"""
        # Update config from UI
        config = self.config.copy()
        
        # Symbols (use active tab's symbols)
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:  # Intraday tab
            symbols = list(self.symbols_listbox.get(0, tk.END))
        else:  # Backtest tab
            symbols = list(self.backtest_symbols_listbox.get(0, tk.END)) if hasattr(self, 'backtest_symbols_listbox') else list(self.symbols_listbox.get(0, tk.END))
        config['symbols'] = symbols
        
        # Lot sizes
        lot_sizes = config.get('lot_sizes', {})
        try:
            default_lot = int(self.default_lot_entry.get())
            lot_sizes['default'] = default_lot
        except:
            pass
        config['lot_sizes'] = lot_sizes
        
        # Trading settings
        trading = config.get('trading', {})
        trading['enable_auto_trading'] = self.auto_trade_var.get()
        trading['allow_buy'] = self.allow_buy_var.get()
        trading['allow_sell'] = self.allow_sell_var.get()
        trading['paper_trading'] = self.paper_trading_var.get()
        try:
            trading['refresh_interval'] = int(self.refresh_interval_entry.get())
            trading['default_quantity'] = int(self.default_quantity_entry.get())
        except:
            pass
        config['trading'] = trading
        
        # Update initial capital (used for both intraday and backtest)
        backtest = config.get('backtest', {})
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:  # Intraday tab
            try:
                backtest['initial_capital'] = int(self.intraday_initial_capital_entry.get())
            except:
                pass
        else:  # Backtest tab
            try:
                backtest['initial_capital'] = int(self.initial_capital_entry.get())
            except:
                pass
        config['backtest'] = backtest
        
        # Indicators (use active tab's indicators)
        indicators = config.get('indicators', {})
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:  # Intraday tab
            indicator_vars = self.indicator_vars
        else:  # Backtest tab
            indicator_vars = self.backtest_indicator_vars if hasattr(self, 'backtest_indicator_vars') else self.indicator_vars
        
        for name, vars_dict in indicator_vars.items():
            if name in indicators:
                indicators[name]['enabled'] = vars_dict['enabled'].get()
                try:
                    indicators[name]['weight'] = float(vars_dict['weight'].get())
                except:
                    pass
        config['indicators'] = indicators
        
        # Risk management (use active tab's risk settings)
        risk_config = config.get('risk_management', {})
        current_tab = self.notebook.index(self.notebook.select())
        try:
            if current_tab == 0:  # Intraday tab
                risk_config['risk_per_trade_pct'] = float(self.risk_per_trade_entry.get())
                risk_config['max_position_size'] = int(self.max_position_entry.get())
                
                stop_loss = risk_config.get('stop_loss', {})
                stop_loss['max_loss_per_trade'] = int(self.max_loss_entry.get())
                stop_loss['atr_multiplier'] = float(self.sl_atr_multiplier_entry.get())
                stop_loss['min_stop_pct'] = float(self.sl_min_pct_entry.get())
                stop_loss['max_stop_pct'] = float(self.sl_max_pct_entry.get())
                stop_loss['breakeven_enabled'] = self.sl_breakeven_var.get()
                stop_loss['breakeven_trigger_ratio'] = float(self.sl_breakeven_ratio_entry.get())
                risk_config['stop_loss'] = stop_loss
                
                profit_targets = risk_config.get('profit_targets', {})
                profit_targets['enabled'] = self.profit_targets_enabled_var.get()
                profit_targets['target_1'] = {
                    'ratio': float(self.pt_target1_ratio_entry.get()),
                    'exit_pct': float(self.pt_target1_exit_entry.get())
                }
                profit_targets['target_2'] = {
                    'ratio': float(self.pt_target2_ratio_entry.get()),
                    'exit_pct': float(self.pt_target2_exit_entry.get())
                }
                profit_targets['target_3'] = {
                    'ratio': float(self.pt_target3_ratio_entry.get()),
                    'exit_pct': float(self.pt_target3_exit_entry.get())
                }
                risk_config['profit_targets'] = profit_targets
                
                trailing_stop = risk_config.get('trailing_stop', {})
                trailing_stop['enabled'] = self.trailing_stop_enabled_var.get()
                trailing_stop['activation_ratio'] = float(self.ts_activation_ratio_entry.get())
                trailing_stop['trail_atr_multiplier'] = float(self.ts_atr_multiplier_entry.get())
                risk_config['trailing_stop'] = trailing_stop
                
                time_exit = risk_config.get('time_exit', {})
                time_exit['enabled'] = self.time_exit_enabled_var.get()
                time_exit['max_hold_minutes'] = int(self.te_max_hold_entry.get())
                time_exit['force_close_eod'] = self.te_force_close_eod_var.get()
                risk_config['time_exit'] = time_exit
                
                daily_limits = risk_config.get('daily_limits', {})
                daily_limits['max_loss_amount'] = int(self.max_daily_loss_entry.get())
                daily_limits['max_trades_per_day'] = int(self.max_trades_entry.get())
                risk_config['daily_limits'] = daily_limits
            else:  # Backtest tab
                if hasattr(self, 'backtest_risk_per_trade_entry'):
                    risk_config['risk_per_trade_pct'] = float(self.backtest_risk_per_trade_entry.get())
                    risk_config['max_position_size'] = int(self.backtest_max_position_entry.get())
                    
                    stop_loss = risk_config.get('stop_loss', {})
                    stop_loss['max_loss_per_trade'] = int(self.backtest_max_loss_entry.get())
                    stop_loss['atr_multiplier'] = float(self.backtest_sl_atr_multiplier_entry.get())
                    stop_loss['min_stop_pct'] = float(self.backtest_sl_min_pct_entry.get())
                    stop_loss['max_stop_pct'] = float(self.backtest_sl_max_pct_entry.get())
                    stop_loss['breakeven_enabled'] = self.backtest_sl_breakeven_var.get()
                    stop_loss['breakeven_trigger_ratio'] = float(self.backtest_sl_breakeven_ratio_entry.get())
                    risk_config['stop_loss'] = stop_loss
                    
                    profit_targets = risk_config.get('profit_targets', {})
                    profit_targets['enabled'] = self.backtest_profit_targets_enabled_var.get()
                    profit_targets['target_1'] = {
                        'ratio': float(self.backtest_pt_target1_ratio_entry.get()),
                        'exit_pct': float(self.backtest_pt_target1_exit_entry.get())
                    }
                    profit_targets['target_2'] = {
                        'ratio': float(self.backtest_pt_target2_ratio_entry.get()),
                        'exit_pct': float(self.backtest_pt_target2_exit_entry.get())
                    }
                    profit_targets['target_3'] = {
                        'ratio': float(self.backtest_pt_target3_ratio_entry.get()),
                        'exit_pct': float(self.backtest_pt_target3_exit_entry.get())
                    }
                    risk_config['profit_targets'] = profit_targets
                    
                    trailing_stop = risk_config.get('trailing_stop', {})
                    trailing_stop['enabled'] = self.backtest_trailing_stop_enabled_var.get()
                    trailing_stop['activation_ratio'] = float(self.backtest_ts_activation_ratio_entry.get())
                    trailing_stop['trail_atr_multiplier'] = float(self.backtest_ts_atr_multiplier_entry.get())
                    risk_config['trailing_stop'] = trailing_stop
                    
                    time_exit = risk_config.get('time_exit', {})
                    time_exit['enabled'] = self.backtest_time_exit_enabled_var.get()
                    time_exit['max_hold_minutes'] = int(self.backtest_te_max_hold_entry.get())
                    time_exit['force_close_eod'] = self.backtest_te_force_close_eod_var.get()
                    risk_config['time_exit'] = time_exit
        except:
            pass
        config['risk_management'] = risk_config
        
        # Backtest settings
        backtest = config.get('backtest', {})
        backtest['start_date'] = self.backtest_start_entry.get()
        backtest['end_date'] = self.backtest_end_entry.get()
        try:
            backtest['initial_capital'] = int(self.initial_capital_entry.get())
        except:
            pass
        backtest['speed'] = self.speed_var.get()
        config['backtest'] = backtest
        
        # Resolution and date range
        date_range = config.get('date_range', {})
        resolution = self.resolution_entry.get()
        date_range['resolution'] = resolution
        config['resolution'] = resolution  # Also set at root level for compatibility
        # Use current date range start/end for intraday, or backtest dates for backtest
        if not date_range.get('start_date'):
            date_range['start_date'] = '2026-01-08 16:15:00'
        if not date_range.get('end_date'):
            date_range['end_date'] = '2026-01-09 16:15:00'
        config['date_range'] = date_range
        
        # Save to file
        if self.save_config(config):
            self.config = config
            messagebox.showinfo("Success", "Configuration saved successfully!")
            
            # Update bot if running
            if self.bot and self.is_running:
                self.update_bot_config()
    
    def update_bot_config(self):
        """Update running bot with new configuration"""
        if not self.bot:
            return
        
        # Reload config
        self.bot.config = self.load_config()
        
        # Update bot settings
        self.bot.auto_trade = self.bot.config['trading'].get('enable_auto_trading', False)
        self.bot.allow_buy = self.bot.config['trading'].get('allow_buy', True)
        self.bot.allow_sell = self.bot.config['trading'].get('allow_sell', True)
        self.bot.refresh_interval = self.bot.config['trading'].get('refresh_interval', 5)
        # Note: default_quantity is now used as max allowed, not a fixed quantity
        self.bot.default_quantity = self.bot.config['trading'].get('default_quantity', 300)
        print(f"📊 Updated max allowed quantity to: {self.bot.default_quantity}")
        
        # Update engine config and reinitialize advanced features
        if hasattr(self.bot, 'engine'):
            # Update config first
            self.bot.engine.config = self.bot.config
            
            # Reinitialize advanced features with new config (this recreates risk_manager and exit_manager)
            if hasattr(self.bot.engine, '_init_advanced_features'):
                self.bot.engine._init_advanced_features()
            
            # Update paper trading mode config
            paper_mode_config = self.bot.config.get('risk_management', {}).get('paper_trading_mode', {})
            self.bot.engine.paper_mode_config = paper_mode_config
            self.bot.engine.paper_mode_enabled = paper_mode_config.get('enabled', False)
            self.bot.engine.paper_mode_trigger = paper_mode_config.get('consecutive_losses_trigger', 3)
            
            # Update initial capital (for both backtest and intraday)
            backtest_config = self.bot.config.get('backtest', {})
            new_initial_capital = backtest_config.get('initial_capital', 20000)
            
            # Always update initial capital (used for quantity calculation)
            if hasattr(self.bot.engine, 'initial_capital'):
                old_capital = self.bot.engine.initial_capital
                self.bot.engine.initial_capital = new_initial_capital
                self.bot.engine.actual_capital = new_initial_capital
                self.bot.engine.hypothetical_capital = new_initial_capital
                print(f"💰 Updated initial capital: ₹{old_capital:,.2f} → ₹{new_initial_capital:,.2f}")
                
                # Update risk manager capital if it exists
                if hasattr(self.bot.engine, 'risk_manager') and self.bot.engine.risk_manager:
                    self.bot.engine.risk_manager.initial_capital = new_initial_capital
                    self.bot.engine.risk_manager.current_capital = new_initial_capital
                    print(f"📊 Updated risk manager capital to: ₹{new_initial_capital:,.2f}")
            
            # Store profit targets config in engine for use when calculating targets
            risk_config = self.bot.config.get('risk_management', {})
            profit_targets_config = risk_config.get('profit_targets', {})
            if profit_targets_config.get('enabled', True):
                # Store profit targets config for use in calculate_profit_targets
                self.bot.engine.profit_targets_config = profit_targets_config
            else:
                self.bot.engine.profit_targets_config = None
            
            # Store trailing stop config
            trailing_config = risk_config.get('trailing_stop', {})
            self.bot.engine.trailing_stop_config = trailing_config
            
            # Store stop loss config
            stop_loss_config = risk_config.get('stop_loss', {})
            self.bot.engine.stop_loss_config = stop_loss_config
            
            # Store time exit config
            time_exit_config = risk_config.get('time_exit', {})
            self.bot.engine.time_exit_config = time_exit_config
            
            # Update initial capital in engine (important for quantity calculation)
            # Always update initial capital (used for both backtest and intraday quantity calculation)
            backtest_config = self.bot.config.get('backtest', {})
            new_initial_capital = backtest_config.get('initial_capital', 20000)
            if hasattr(self.bot.engine, 'initial_capital'):
                old_capital = self.bot.engine.initial_capital
                self.bot.engine.initial_capital = new_initial_capital
                self.bot.engine.actual_capital = new_initial_capital
                self.bot.engine.hypothetical_capital = new_initial_capital
                print(f"💰 Updated initial capital: ₹{old_capital:,.2f} → ₹{new_initial_capital:,.2f}")
                
                # Update risk manager capital if it exists
                if hasattr(self.bot.engine, 'risk_manager') and self.bot.engine.risk_manager:
                    self.bot.engine.risk_manager.initial_capital = new_initial_capital
                    self.bot.engine.risk_manager.current_capital = new_initial_capital
                    print(f"📊 Updated risk manager capital to: ₹{new_initial_capital:,.2f}")
        
        # Update data loader config if backtest mode changed
        if hasattr(self.bot, 'data_loader'):
            backtest_config = self.bot.config.get('backtest', {})
            self.bot.data_loader.backtest_config = backtest_config
        
        print("✅ Bot configuration updated successfully")
    
    def add_symbol(self):
        """Add symbol to list"""
        symbol = self.symbol_entry.get().strip()
        if symbol:
            self.symbols_listbox.insert(tk.END, symbol)
            self.symbol_entry.delete(0, tk.END)
    
    def remove_symbol(self):
        """Remove selected symbol"""
        selection = self.symbols_listbox.curselection()
        if selection:
            self.symbols_listbox.delete(selection[0])
    
    def add_backtest_symbol(self):
        """Add symbol to backtest list"""
        symbol = self.backtest_symbol_entry.get().strip()
        if symbol:
            self.backtest_symbols_listbox.insert(tk.END, symbol)
            self.backtest_symbol_entry.delete(0, tk.END)
    
    def remove_backtest_symbol(self):
        """Remove selected symbol from backtest list"""
        selection = self.backtest_symbols_listbox.curselection()
        if selection:
            self.backtest_symbols_listbox.delete(selection[0])
    
    def reload_config(self):
        """Reload configuration from file"""
        self.config = self.load_config()
        self.load_config_to_ui()
        self.load_backtest_configs()
        messagebox.showinfo("Success", "Configuration reloaded!")
    
    def load_backtest_configs(self):
        """Load backtest-specific configurations"""
        if not hasattr(self, 'backtest_symbols_listbox'):
            return
        
        # Load symbols
        symbols = self.config.get('symbols', [])
        self.backtest_symbols_listbox.delete(0, tk.END)
        for symbol in symbols:
            self.backtest_symbols_listbox.insert(tk.END, symbol)
        
        # Load trading settings
        trading = self.config.get('trading', {})
        if hasattr(self, 'backtest_auto_trade_var'):
            self.backtest_auto_trade_var.set(trading.get('enable_auto_trading', False))
            self.backtest_allow_buy_var.set(trading.get('allow_buy', True))
            self.backtest_allow_sell_var.set(trading.get('allow_sell', False))
            if hasattr(self, 'backtest_default_quantity_entry'):
                self.backtest_default_quantity_entry.delete(0, tk.END)
                self.backtest_default_quantity_entry.insert(0, str(trading.get('default_quantity', 300)))
        
        # Load risk management
        risk_config = self.config.get('risk_management', {})
        if hasattr(self, 'backtest_risk_per_trade_entry'):
            self.backtest_risk_per_trade_entry.delete(0, tk.END)
            self.backtest_risk_per_trade_entry.insert(0, str(risk_config.get('risk_per_trade_pct', 0.8)))
        if hasattr(self, 'backtest_max_position_entry'):
            self.backtest_max_position_entry.delete(0, tk.END)
            self.backtest_max_position_entry.insert(0, str(risk_config.get('max_position_size', 100)))
        if hasattr(self, 'backtest_max_loss_entry'):
            sl_config = risk_config.get('stop_loss', {})
            self.backtest_max_loss_entry.delete(0, tk.END)
            self.backtest_max_loss_entry.insert(0, str(sl_config.get('max_loss_per_trade', 300)))
            if hasattr(self, 'backtest_sl_atr_multiplier_entry'):
                self.backtest_sl_atr_multiplier_entry.delete(0, tk.END)
                self.backtest_sl_atr_multiplier_entry.insert(0, str(sl_config.get('atr_multiplier', 1.5)))
                self.backtest_sl_min_pct_entry.delete(0, tk.END)
                self.backtest_sl_min_pct_entry.insert(0, str(sl_config.get('min_stop_pct', 0.5)))
                self.backtest_sl_max_pct_entry.delete(0, tk.END)
                self.backtest_sl_max_pct_entry.insert(0, str(sl_config.get('max_stop_pct', 3.0)))
                self.backtest_sl_breakeven_var.set(sl_config.get('breakeven_enabled', True))
                self.backtest_sl_breakeven_ratio_entry.delete(0, tk.END)
                self.backtest_sl_breakeven_ratio_entry.insert(0, str(sl_config.get('breakeven_trigger_ratio', 1.0)))
            
            # Load profit targets
            if hasattr(self, 'backtest_profit_targets_enabled_var'):
                pt_config = risk_config.get('profit_targets', {})
                self.backtest_profit_targets_enabled_var.set(pt_config.get('enabled', True))
                self.backtest_pt_target1_ratio_entry.delete(0, tk.END)
                self.backtest_pt_target1_ratio_entry.insert(0, str(pt_config.get('target_1', {}).get('ratio', 1.5)))
                self.backtest_pt_target1_exit_entry.delete(0, tk.END)
                self.backtest_pt_target1_exit_entry.insert(0, str(pt_config.get('target_1', {}).get('exit_pct', 80)))
                self.backtest_pt_target2_ratio_entry.delete(0, tk.END)
                self.backtest_pt_target2_ratio_entry.insert(0, str(pt_config.get('target_2', {}).get('ratio', 2.0)))
                self.backtest_pt_target2_exit_entry.delete(0, tk.END)
                self.backtest_pt_target2_exit_entry.insert(0, str(pt_config.get('target_2', {}).get('exit_pct', 50)))
                self.backtest_pt_target3_ratio_entry.delete(0, tk.END)
                self.backtest_pt_target3_ratio_entry.insert(0, str(pt_config.get('target_3', {}).get('ratio', 3.0)))
                self.backtest_pt_target3_exit_entry.delete(0, tk.END)
                self.backtest_pt_target3_exit_entry.insert(0, str(pt_config.get('target_3', {}).get('exit_pct', 20)))
            
            # Load trailing stop
            if hasattr(self, 'backtest_trailing_stop_enabled_var'):
                ts_config = risk_config.get('trailing_stop', {})
                self.backtest_trailing_stop_enabled_var.set(ts_config.get('enabled', True))
                self.backtest_ts_activation_ratio_entry.delete(0, tk.END)
                self.backtest_ts_activation_ratio_entry.insert(0, str(ts_config.get('activation_ratio', 1.0)))
                self.backtest_ts_atr_multiplier_entry.delete(0, tk.END)
                self.backtest_ts_atr_multiplier_entry.insert(0, str(ts_config.get('trail_atr_multiplier', 1.0)))
            
            # Load time exit
            if hasattr(self, 'backtest_time_exit_enabled_var'):
                te_config = risk_config.get('time_exit', {})
                self.backtest_time_exit_enabled_var.set(te_config.get('enabled', True))
                self.backtest_te_max_hold_entry.delete(0, tk.END)
                self.backtest_te_max_hold_entry.insert(0, str(te_config.get('max_hold_minutes', 60)))
                self.backtest_te_force_close_eod_var.set(te_config.get('force_close_eod', True))
        
        # Load indicators
        indicators_config = self.config.get('indicators', {})
        if hasattr(self, 'backtest_indicator_vars'):
            for name, vars_dict in self.backtest_indicator_vars.items():
                if name in indicators_config:
                    vars_dict['enabled'].set(indicators_config[name].get('enabled', False))
                    vars_dict['weight'].delete(0, tk.END)
                    vars_dict['weight'].insert(0, str(indicators_config[name].get('weight', 1.0)))
    
    def start_intraday(self):
        """Start intraday trading"""
        if self.is_running:
            messagebox.showwarning("Warning", "Trading is already running!")
            return
        
        # Save config first
        self.save_config_from_ui()
        
        # Disable backtest mode
        self.config['backtest'] = self.config.get('backtest', {})
        self.config['backtest']['enabled'] = False
        self.save_config(self.config)  # Save to file
        
        # Start bot in separate thread
        self.is_running = True
        self.start_intraday_btn.config(state=tk.DISABLED)
        self.stop_intraday_btn.config(state=tk.NORMAL)
        self.status_label.config(text="Starting...", foreground="blue")
        
        self.bot_thread = threading.Thread(target=self.run_intraday_bot, daemon=True)
        self.bot_thread.start()
    
    def stop_intraday(self):
        """Stop intraday trading"""
        self.is_running = False
        self.start_intraday_btn.config(state=tk.NORMAL)
        self.stop_intraday_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Stopped", foreground="red")
    
    def run_intraday_bot(self):
        """Run intraday bot in background thread"""
        try:
            # Create bot instance
            self.bot = LiveTradingBot(
                config_path=str(self.config_path),
                indicators_config_path=str(self.indicators_config_path)
            )
            
            # Ensure engine has latest initial capital from config
            backtest_config = self.bot.config.get('backtest', {})
            initial_capital = backtest_config.get('initial_capital', 20000)
            if hasattr(self.bot.engine, 'initial_capital'):
                self.bot.engine.initial_capital = initial_capital
                self.bot.engine.actual_capital = initial_capital
                self.bot.engine.hypothetical_capital = initial_capital
                print(f"💰 Initial capital set to: ₹{initial_capital:,.2f}")
            
            # Update status
            self.message_queue.put(("status", "Running...", "green"))
            
            # Run bot with periodic updates
            while self.is_running:
                try:
                    # Reload config before each cycle to get latest values
                    self.bot.config = self.bot.load_config(str(self.config_path))
                    self.bot.engine.config = self.bot.config
                    
                    # Update initial capital if changed
                    backtest_config = self.bot.config.get('backtest', {})
                    new_initial_capital = backtest_config.get('initial_capital', 20000)
                    if hasattr(self.bot.engine, 'initial_capital') and self.bot.engine.initial_capital != new_initial_capital:
                        self.bot.engine.initial_capital = new_initial_capital
                        self.bot.engine.actual_capital = new_initial_capital
                        self.bot.engine.hypothetical_capital = new_initial_capital
                    
                    results = self.bot.run_once()
                    
                    # Update UI with results (including LTP)
                    self.message_queue.put(("results", results))
                    self.message_queue.put(("positions", self.bot.engine.current_positions.copy()))
                    
                    # Get closed orders (only send if there are new ones)
                    closed_orders = self.bot.engine.get_closed_orders()
                    if not closed_orders.empty:
                        # Convert to dict for JSON serialization
                        trades_data = closed_orders.to_dict('records')
                        self.message_queue.put(("trades", closed_orders))
                    
                    # Get summary
                    summary = self.bot.engine.get_summary()
                    self.message_queue.put(("summary", summary))
                    
                    # Update status with refresh count
                    self.message_queue.put(("status", f"Running... (Refresh #{self.bot.refresh_count})", "green"))
                    
                    # Sleep for refresh interval
                    import time
                    time.sleep(self.bot.refresh_interval)
                    
                except Exception as e:
                    self.message_queue.put(("error", str(e)))
                    import traceback
                    self.message_queue.put(("error", traceback.format_exc()))
                    break
                    
        except Exception as e:
            self.message_queue.put(("error", f"Failed to start bot: {e}"))
            import traceback
            self.message_queue.put(("error", traceback.format_exc()))
        finally:
            self.is_running = False
            self.message_queue.put(("status", "Stopped", "red"))
            self.message_queue.put(("button_state", "intraday_stop"))
    
    def start_backtest(self):
        """Start backtesting"""
        if self.is_running:
            messagebox.showwarning("Warning", "Trading is already running!")
            return
        
        # Save config first
        self.save_config_from_ui()
        
        # Enable backtest mode
        self.config['backtest'] = self.config.get('backtest', {})
        self.config['backtest']['enabled'] = True
        self.save_config(self.config)
        
        # Clear previous results
        for item in self.backtest_tree.get_children():
            self.backtest_tree.delete(item)
        for item in self.backtest_summary_tree.get_children():
            self.backtest_summary_tree.delete(item)
        
        # Reset metrics history
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
        
        # Reset metric key map
        self.metric_key_map = {}
        
        # Start backtest in separate thread
        self.is_running = True
        self.start_backtest_btn.config(state=tk.DISABLED)
        self.stop_backtest_btn.config(state=tk.NORMAL)
        self.backtest_status_label.config(text="Starting backtest...", foreground="blue")
        
        self.bot_thread = threading.Thread(target=self.run_backtest_bot, daemon=True)
        self.bot_thread.start()
    
    def stop_backtest(self):
        """Stop backtesting"""
        self.is_running = False
        self.start_backtest_btn.config(state=tk.NORMAL)
        self.stop_backtest_btn.config(state=tk.DISABLED)
        self.backtest_status_label.config(text="Stopped", foreground="red")
    
    def run_backtest_bot(self):
        """Run backtest bot in background thread"""
        import time
        
        try:
            # Create bot instance
            self.bot = LiveTradingBot(
                config_path=str(self.config_path),
                indicators_config_path=str(self.indicators_config_path)
            )
            
            # Ensure engine has latest initial capital from config
            backtest_config = self.bot.config.get('backtest', {})
            initial_capital = backtest_config.get('initial_capital', 20000)
            if hasattr(self.bot.engine, 'initial_capital'):
                self.bot.engine.initial_capital = initial_capital
                self.bot.engine.actual_capital = initial_capital
                self.bot.engine.hypothetical_capital = initial_capital
                print(f"💰 Initial capital set to: ₹{initial_capital:,.2f}")
            
            # Update status
            self.message_queue.put(("backtest_status", "Running backtest...", "green"))
            
            # Get speed setting
            speed = self.config.get('backtest', {}).get('speed', 'fast')
            
            # Run backtest
            iteration = 0
            last_update_time = time.time()
            update_interval = 0.1  # Update UI every 100ms even in fast mode
            
            while self.is_running:
                try:
                    results = self.bot.run_once()
                    iteration += 1
                    
                    current_time = time.time()
                    
                    # Update progress (throttle to avoid queue overflow)
                    if self.message_queue.qsize() < 50:
                        if self.bot.data_loader.generators:
                            first_gen = list(self.bot.data_loader.generators.values())[0]
                            progress = first_gen.progress()
                            self.message_queue.put(("progress", progress['percent']))
                    
                    # Reload config before each iteration to get latest values
                    self.bot.config = self.bot.load_config(str(self.config_path))
                    self.bot.engine.config = self.bot.config
                    
                    # Update initial capital if changed
                    backtest_config = self.bot.config.get('backtest', {})
                    new_initial_capital = backtest_config.get('initial_capital', 20000)
                    if hasattr(self.bot.engine, 'initial_capital') and self.bot.engine.initial_capital != new_initial_capital:
                        self.bot.engine.initial_capital = new_initial_capital
                        self.bot.engine.actual_capital = new_initial_capital
                        self.bot.engine.hypothetical_capital = new_initial_capital
                    
                    # Update results periodically to avoid overwhelming UI
                    if current_time - last_update_time >= update_interval:
                        # Check queue size to prevent overflow
                        if self.message_queue.qsize() < 50:  # Prevent queue overflow
                            # Update results
                            closed_orders = self.bot.engine.get_closed_orders()
                            if not closed_orders.empty:
                                self.message_queue.put(("backtest_trades", closed_orders))
                            
                            # Update summary (include trades for metrics calculation)
                            summary = self.bot.engine.get_summary()
                            summary['closed_orders'] = closed_orders  # Include trades for metrics
                            summary['iteration'] = iteration  # Include iteration for trend tracking
                            self.message_queue.put(("backtest_summary", summary))
                            
                            # Update status (less frequently to reduce queue load)
                            if iteration % 10 == 0:
                                self.message_queue.put(("backtest_status", f"Running... Iteration #{iteration}", "green"))
                            
                            last_update_time = current_time
                        else:
                            # Queue is getting full, skip this update cycle
                            pass
                    
                    # Speed control - always yield some time to UI thread
                    if speed == 'realtime':
                        time.sleep(self.bot.refresh_interval)
                    elif speed == 'slow':
                        time.sleep(0.5)
                    elif speed == 'medium':
                        time.sleep(0.1)
                    else:  # fast mode - still yield to UI
                        time.sleep(0.05)  # Small delay to allow UI updates (increased from 0.01)
                    
                except StopIteration:
                    # Backtest complete
                    self.message_queue.put(("backtest_status", "Backtest completed!", "green"))
                    break
                except Exception as e:
                    self.message_queue.put(("error", str(e)))
                    import traceback
                    self.message_queue.put(("error", traceback.format_exc()))
                    break
                    
        except Exception as e:
            self.message_queue.put(("error", f"Failed to start backtest: {e}"))
            import traceback
            self.message_queue.put(("error", traceback.format_exc()))
        finally:
            self.is_running = False
            self.message_queue.put(("backtest_status", "Stopped", "red"))
            self.message_queue.put(("button_state", "backtest_stop"))
    
    def process_queue(self):
        """Process messages from queue (thread-safe UI updates)"""
        # Process multiple messages per cycle to avoid backlog
        messages_processed = 0
        max_messages_per_cycle = 10  # Limit to prevent UI blocking
        
        try:
            while messages_processed < max_messages_per_cycle:
                msg = self.message_queue.get_nowait()
                msg_type = msg[0]
                
                if msg_type == "status":
                    self.status_label.config(text=msg[1], foreground=msg[2])
                elif msg_type == "backtest_status":
                    self.backtest_status_label.config(text=msg[1], foreground=msg[2])
                elif msg_type == "progress":
                    self.progress_var.set(msg[1])
                elif msg_type == "results":
                    self.last_results = msg[1]  # Store for position PnL calculation
                    # Update LTP table with real-time prices
                    self.update_ltp_table(msg[1])
                elif msg_type == "positions":
                    self.update_positions_table(msg[1])
                elif msg_type == "trades":
                    self.update_trades_table(msg[1])
                elif msg_type == "summary":
                    self.update_performance_summary(msg[1])
                elif msg_type == "backtest_trades":
                    self.update_backtest_trades(msg[1])
                    # Update summary when trades update
                    if hasattr(self, 'bot') and self.bot:
                        summary = self.bot.engine.get_summary()
                        summary['closed_orders'] = msg[1]  # Use the trades from message
                        self.update_backtest_summary(summary)
                elif msg_type == "backtest_summary":
                    self.update_backtest_summary(msg[1])
                elif msg_type == "error":
                    # Use after() to show error dialog in main thread (avoid blocking)
                    error_msg = msg[1]  # Capture in local variable
                    self.root.after_idle(lambda e=error_msg: messagebox.showerror("Error", e))
                elif msg_type == "button_state":
                    if msg[1] == "intraday_stop":
                        self.start_intraday_btn.config(state=tk.NORMAL)
                        self.stop_intraday_btn.config(state=tk.DISABLED)
                    elif msg[1] == "backtest_stop":
                        self.start_backtest_btn.config(state=tk.NORMAL)
                        self.stop_backtest_btn.config(state=tk.DISABLED)
                
                messages_processed += 1
                        
        except queue.Empty:
            pass
        
        # Schedule next check - use shorter interval during backtesting
        if self.is_running:
            # Check more frequently when running
            self.root.after(50, self.process_queue)
        else:
            # Normal interval when idle
            self.root.after(100, self.process_queue)
    
    def update_ltp_table(self, results: list):
        """Update LTP table with real-time prices and store history"""
        # Clear existing
        for item in self.ltp_tree.get_children():
            self.ltp_tree.delete(item)
        
        # Store previous prices for change calculation
        if not hasattr(self, 'previous_prices'):
            self.previous_prices = {}
        
        # Initialize LTP history if not exists
        if not hasattr(self, 'ltp_history'):
            self.ltp_history = {}
        
        # Get current timestamp
        current_time = datetime.now()
        
        # Add symbols with LTP
        for result in results:
            symbol = result.get('symbol', '')
            symbol_short = symbol.split(':')[-1]
            ltp = result.get('latest_price', 0)
            signal = result.get('final_signal', 'HOLD')
            
            # Store LTP history with timestamp
            if symbol not in self.ltp_history:
                self.ltp_history[symbol] = []
            
            # Add new data point (limit to last 1000 points to prevent memory issues)
            self.ltp_history[symbol].append((current_time, ltp))
            if len(self.ltp_history[symbol]) > 1000:
                self.ltp_history[symbol] = self.ltp_history[symbol][-1000:]
            
            # Calculate change
            prev_price = self.previous_prices.get(symbol, ltp)
            change = ltp - prev_price
            change_pct = (change / prev_price * 100) if prev_price > 0 else 0
            change_str = f"{change:+.2f} ({change_pct:+.2f}%)"
            
            # Determine tag based on change
            if change > 0:
                tag = "profit"
            elif change < 0:
                tag = "loss"
            else:
                tag = "neutral"
            
            # Update previous price
            self.previous_prices[symbol] = ltp
            
            item_id = self.ltp_tree.insert("", tk.END, values=(
                symbol_short,
                f"{ltp:.2f}",
                signal,
                change_str
            ), tags=(tag,))
            
            # Store symbol mapping for click handler
            if not hasattr(self, 'ltp_symbol_map'):
                self.ltp_symbol_map = {}
            self.ltp_symbol_map[item_id] = symbol
    
    def update_positions_table(self, positions: dict):
        """Update positions table with color coding"""
        # Clear existing
        for item in self.positions_tree.get_children():
            self.positions_tree.delete(item)
        
        # Add positions
        for symbol, position in positions.items():
            symbol_short = symbol.split(':')[-1]
            
            # Try to get current price from results if available
            ltp = 0.0
            pnl_val = 0.0
            if hasattr(self, 'last_results'):
                for result in self.last_results:
                    if result.get('symbol') == symbol:
                        ltp = result.get('latest_price', 0)
                        # Calculate PnL
                        current_price = result.get('latest_price', 0)
                        if position['type'] == 'LONG':
                            pnl_val = (current_price - position['entry_price']) * position['quantity']
                        else:
                            pnl_val = (position['entry_price'] - current_price) * position['quantity']
                        break
            
            # Determine tag based on PnL
            if pnl_val > 0:
                tag = "profit"
            elif pnl_val < 0:
                tag = "loss"
            else:
                tag = "neutral"
            
            self.positions_tree.insert("", tk.END, values=(
                symbol_short,
                position['type'],
                f"{position['entry_price']:.2f}",
                position['quantity'],
                f"{ltp:.2f}" if ltp > 0 else "N/A",
                f"{pnl_val:+.2f}" if pnl_val != 0 else "N/A"
            ), tags=(tag,))
    
    def update_trades_table(self, trades_df: pd.DataFrame):
        """Update completed trades table with color coding"""
        # Clear existing
        for item in self.trades_tree.get_children():
            self.trades_tree.delete(item)
        
        # Add trades
        if not trades_df.empty:
            for idx, row in trades_df.iterrows():
                symbol_short = row['symbol'].split(':')[-1]
                return_pct = ((row['exit_price'] - row['entry_price']) / row['entry_price'] * 100) if row['type'] == 'LONG' else ((row['entry_price'] - row['exit_price']) / row['entry_price'] * 100)
                pnl = row['pnl']
                
                # Determine tag based on PnL
                if pnl > 0:
                    tag = "profit"
                elif pnl < 0:
                    tag = "loss"
                else:
                    tag = "neutral"
                
                # Get exit reason
                exit_reason = row.get('exit_reason', 'N/A')
                if pd.isna(exit_reason):
                    exit_reason = 'N/A'
                exit_reason_short = exit_reason[:40] if len(exit_reason) > 40 else exit_reason
                
                # Format entry and exit times
                entry_time = row.get('entry_time', None)
                exit_time = row.get('exit_time', None)
                
                # Format entry time
                if pd.notna(entry_time) and entry_time is not None:
                    try:
                        if isinstance(entry_time, str):
                            # Try to parse if it's a string
                            entry_time_str = entry_time
                        elif hasattr(entry_time, 'strftime'):
                            # It's a datetime object
                            entry_time_str = entry_time.strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            # Try to convert to datetime
                            entry_time_str = pd.to_datetime(entry_time).strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        entry_time_str = str(entry_time)[:19] if entry_time else "N/A"
                else:
                    entry_time_str = "N/A"
                
                # Format exit time
                if pd.notna(exit_time) and exit_time is not None:
                    try:
                        if isinstance(exit_time, str):
                            # Try to parse if it's a string
                            exit_time_str = exit_time
                        elif hasattr(exit_time, 'strftime'):
                            # It's a datetime object
                            exit_time_str = exit_time.strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            # Try to convert to datetime
                            exit_time_str = pd.to_datetime(exit_time).strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        exit_time_str = str(exit_time)[:19] if exit_time else "N/A"
                else:
                    exit_time_str = "N/A"
                
                self.trades_tree.insert("", tk.END, values=(
                    row['order_id'],
                    symbol_short,
                    row['type'],
                    f"{row['entry_price']:.2f}",
                    f"{row['exit_price']:.2f}",
                    row['quantity'],
                    f"{pnl:+.2f}",
                    f"{return_pct:+.2f}%",
                    entry_time_str,
                    exit_time_str,
                    exit_reason_short
                ), tags=(tag,))
    
    def update_performance_summary(self, summary: dict):
        """Update intraday performance summary table with comprehensive metrics"""
        # Clear existing
        for item in self.intraday_summary_tree.get_children():
            self.intraday_summary_tree.delete(item)
        
        # Get initial capital from config (for intraday, use backtest config or default)
        backtest_config = self.config.get('backtest', {})
        initial_capital = backtest_config.get('initial_capital', 20000)
        
        # Get closed orders for detailed metrics
        closed_orders = None
        if hasattr(self, 'bot') and self.bot:
            closed_orders = self.bot.engine.get_closed_orders()
        
        if closed_orders is not None and not closed_orders.empty:
            metrics = self.calculate_metrics(closed_orders, initial_capital)
        else:
            metrics = {}
        
        # Calculate basic values
        total_pnl = summary.get('total_pnl', 0)
        final_capital = initial_capital + total_pnl
        returns_pct = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0
        
        # Add metrics to table with color coding
        def add_metric(metric, value, is_category=False, metric_key=None):
            if is_category:
                self.intraday_summary_tree.insert("", tk.END, values=(metric, ""), tags=("category",))
            else:
                # Determine tag based on value
                tag = "neutral"
                if metric_key and metric_key in ['total_pnl', 'avg_win', 'max_win', 'expectancy', 'profit_factor', 'sharpe_ratio', 'sortino_ratio', 'calmar_ratio', 'returns_pct', 'circuit_breaker_savings']:
                    # Check if value is positive or negative
                    try:
                        # Extract numeric value
                        if isinstance(value, str):
                            # Remove currency symbols and extract number
                            num_str = value.replace('₹', '').replace(',', '').replace('+', '').replace('%', '').strip()
                            num_val = float(num_str)
                        else:
                            num_val = float(value)
                        
                        if num_val > 0:
                            tag = "profit"
                        elif num_val < 0:
                            tag = "loss"
                        else:
                            tag = "neutral"
                    except:
                        tag = "neutral"
                elif metric_key and metric_key in ['avg_loss', 'max_loss', 'max_drawdown']:
                    try:
                        if isinstance(value, str):
                            num_str = value.replace('₹', '').replace(',', '').replace('-', '').replace('%', '').strip()
                            num_val = float(num_str)
                        else:
                            num_val = float(value)
                        
                        if num_val < 0:
                            tag = "loss"
                        elif num_val > 0:
                            tag = "profit"
                        else:
                            tag = "neutral"
                    except:
                        tag = "neutral"
                elif metric_key and metric_key in ['win_rate']:
                    try:
                        if isinstance(value, str):
                            num_str = value.replace('%', '').strip()
                            num_val = float(num_str)
                        else:
                            num_val = float(value)
                        
                        if num_val >= 50:
                            tag = "profit"
                        elif num_val < 50:
                            tag = "loss"
                        else:
                            tag = "neutral"
                    except:
                        tag = "neutral"
                
                self.intraday_summary_tree.insert("", tk.END, values=(metric, value), tags=(tag,))
        
        # Capital & Returns
        add_metric("💰 CAPITAL & RETURNS", "", True)
        add_metric("Initial Capital", f"₹{initial_capital:,.2f}")
        add_metric("Current Capital", f"₹{final_capital:,.2f}")
        add_metric("Total PnL", f"₹{total_pnl:+,.2f}", metric_key="total_pnl")
        add_metric("Return %", f"{returns_pct:+.2f}%", metric_key="returns_pct")
        
        # Trading Activity
        add_metric("📈 TRADING ACTIVITY", "", True)
        total_orders = summary.get('total_orders', 0)
        add_metric("Total Trades (Real)", str(total_orders))
        if metrics:
            add_metric("Winning Trades", str(metrics.get('winning_trades', 0)))
            add_metric("Losing Trades", str(metrics.get('losing_trades', 0)))
            add_metric("Win Rate", f"{metrics.get('win_rate', 0):.2%}", metric_key="win_rate")
        
        # Circuit Breaker Impact
        if metrics and metrics.get('paper_trades_count', 0) > 0:
            add_metric("🛡️ CIRCUIT BREAKER", "", True)
            add_metric("Paper Trades (Protected)", str(metrics.get('paper_trades_count', 0)))
            add_metric("Capital Saved", f"₹{metrics.get('circuit_breaker_savings', 0):+,.2f}", metric_key="circuit_breaker_savings")
            add_metric("PnL WITHOUT Circuit Breaker", f"₹{metrics.get('all_trades_pnl', 0):+,.2f}")
            add_metric("PnL WITH Circuit Breaker", f"₹{metrics.get('total_pnl', 0):+,.2f}", metric_key="total_pnl")
        
        # Performance Metrics
        if metrics:
            add_metric("💵 PROFIT & LOSS", "", True)
            add_metric("Average Win", f"₹{metrics.get('avg_win', 0):+,.2f}", metric_key="avg_win")
            add_metric("Average Loss", f"₹{metrics.get('avg_loss', 0):,.2f}", metric_key="avg_loss")
            add_metric("Largest Win", f"₹{metrics.get('max_win', 0):+,.2f}", metric_key="max_win")
            add_metric("Largest Loss", f"₹{metrics.get('max_loss', 0):,.2f}", metric_key="max_loss")
            add_metric("Profit Factor", f"{metrics.get('profit_factor', 0):.2f}", metric_key="profit_factor")
            add_metric("Expectancy per Trade", f"₹{metrics.get('expectancy', 0):+,.2f}", metric_key="expectancy")
            
            # Risk Metrics
            add_metric("⚠️ RISK METRICS", "", True)
            add_metric("Sharpe Ratio", f"{metrics.get('sharpe_ratio', 0):.2f}", metric_key="sharpe_ratio")
            add_metric("Max Drawdown", f"{metrics.get('max_drawdown', 0):.2%}", metric_key="max_drawdown")
            
            # Calculate Sortino Ratio if we have trades
            if hasattr(self, 'bot') and self.bot:
                closed_orders = self.bot.engine.get_closed_orders()
                if not closed_orders.empty:
                    real_trades = closed_orders[~closed_orders.get('paper_trade', pd.Series([False]*len(closed_orders)))]
                    if not real_trades.empty and len(real_trades) > 1:
                        returns = []
                        equity = initial_capital
                        for _, trade in real_trades.iterrows():
                            trade_return = trade['pnl'] / equity
                            returns.append(trade_return)
                            equity += trade['pnl']
                        
                        if len(returns) > 1:
                            returns_array = np.array(returns)
                            downside_returns = returns_array[returns_array < 0]
                            if len(downside_returns) > 0:
                                downside_std = np.std(downside_returns, ddof=1)
                                mean_return = np.mean(returns_array)
                                if downside_std > 0:
                                    sortino = (mean_return * 252 - 0.05) / (downside_std * np.sqrt(252))
                                    add_metric("Sortino Ratio", f"{sortino:.2f}", metric_key="sortino_ratio")
                        
                        # Calmar Ratio
                        if metrics.get('max_drawdown', 0) != 0:
                            annual_return = (total_pnl / initial_capital) * (252 / len(real_trades)) if len(real_trades) > 0 else 0
                            calmar = annual_return / abs(metrics.get('max_drawdown', 0)) if metrics.get('max_drawdown', 0) != 0 else 0
                            add_metric("Calmar Ratio", f"{calmar:.2f}", metric_key="calmar_ratio")
        
        # System Stats
        add_metric("🔧 SYSTEM STATS", "", True)
        add_metric("Open Positions", str(summary.get('open_positions', 0)))
        if hasattr(self, 'bot') and self.bot:
            add_metric("Indicators Active", str(len(self.bot.engine.indicator_manager)))
    
    def update_backtest_trades(self, trades_df: pd.DataFrame):
        """Update backtest trades table with color coding"""
        # Clear existing
        for item in self.backtest_tree.get_children():
            self.backtest_tree.delete(item)
        
        # Add trades
        if not trades_df.empty:
            for idx, row in trades_df.iterrows():
                symbol_short = row['symbol'].split(':')[-1]
                return_pct = ((row['exit_price'] - row['entry_price']) / row['entry_price'] * 100) if row['type'] == 'LONG' else ((row['entry_price'] - row['exit_price']) / row['entry_price'] * 100)
                pnl = row['pnl']
                
                # Determine tag based on PnL
                if pnl > 0:
                    tag = "profit"
                elif pnl < 0:
                    tag = "loss"
                else:
                    tag = "neutral"
                
                # Get exit reason
                exit_reason = row.get('exit_reason', 'N/A')
                if pd.isna(exit_reason):
                    exit_reason = 'N/A'
                exit_reason_short = exit_reason[:30] if len(exit_reason) > 30 else exit_reason
                
                # Format entry and exit times
                entry_time = row.get('entry_time', None)
                exit_time = row.get('exit_time', None)
                
                # Format entry time
                if pd.notna(entry_time) and entry_time is not None:
                    try:
                        if isinstance(entry_time, str):
                            # Try to parse if it's a string
                            entry_time_str = entry_time
                        elif hasattr(entry_time, 'strftime'):
                            # It's a datetime object
                            entry_time_str = entry_time.strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            # Try to convert to datetime
                            entry_time_str = pd.to_datetime(entry_time).strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        entry_time_str = str(entry_time)[:19] if entry_time else "N/A"
                else:
                    entry_time_str = "N/A"
                
                # Format exit time
                if pd.notna(exit_time) and exit_time is not None:
                    try:
                        if isinstance(exit_time, str):
                            # Try to parse if it's a string
                            exit_time_str = exit_time
                        elif hasattr(exit_time, 'strftime'):
                            # It's a datetime object
                            exit_time_str = exit_time.strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            # Try to convert to datetime
                            exit_time_str = pd.to_datetime(exit_time).strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        exit_time_str = str(exit_time)[:19] if exit_time else "N/A"
                else:
                    exit_time_str = "N/A"
                
                self.backtest_tree.insert("", tk.END, values=(
                    row['order_id'],
                    symbol_short,
                    row['type'],
                    f"{row['entry_price']:.2f}",
                    f"{row['exit_price']:.2f}",
                    row['quantity'],
                    f"{pnl:+.2f}",
                    f"{return_pct:+.2f}%",
                    entry_time_str,
                    exit_time_str,
                    exit_reason_short
                ), tags=(tag,))
    
    def calculate_sharpe_ratio(self, returns: list, periods_per_year: int = 252) -> float:
        """Calculate Sharpe Ratio"""
        if len(returns) < 2:
            return 0.0
        
        returns_array = np.array(returns)
        mean_return = np.mean(returns_array)
        std_return = np.std(returns_array, ddof=1)
        
        if std_return == 0:
            return 0.0
        
        # Annualize
        annual_return = mean_return * periods_per_year
        annual_std = std_return * np.sqrt(periods_per_year)
        risk_free_rate = 0.05  # 5% risk-free rate
        
        sharpe = (annual_return - risk_free_rate) / annual_std
        return float(sharpe)
    
    def calculate_metrics(self, trades_df: pd.DataFrame, initial_capital: float) -> dict:
        """Calculate comprehensive trading metrics"""
        if trades_df.empty or len(trades_df) == 0:
            return {}
        
        # Separate real and paper trades
        real_trades = trades_df[~trades_df.get('paper_trade', pd.Series([False]*len(trades_df)))]
        paper_trades = trades_df[trades_df.get('paper_trade', pd.Series([False]*len(trades_df)))]
        
        # Basic metrics for real trades
        total_trades = len(real_trades) if not real_trades.empty else 0
        winning_trades = len(real_trades[real_trades['pnl'] > 0]) if total_trades > 0 else 0
        losing_trades = len(real_trades[real_trades['pnl'] < 0]) if total_trades > 0 else 0
        win_rate = (winning_trades / total_trades) if total_trades > 0 else 0
        
        # PnL metrics
        total_pnl = real_trades['pnl'].sum() if not real_trades.empty else 0
        avg_win = real_trades[real_trades['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = real_trades[real_trades['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
        max_win = real_trades['pnl'].max() if not real_trades.empty else 0
        max_loss = real_trades['pnl'].min() if not real_trades.empty else 0
        
        # Profit factor
        gross_profit = real_trades[real_trades['pnl'] > 0]['pnl'].sum() if winning_trades > 0 else 0
        gross_loss = abs(real_trades[real_trades['pnl'] < 0]['pnl'].sum()) if losing_trades > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0
        
        # Expectancy
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * abs(avg_loss)) if total_trades > 0 else 0
        
        # Returns for Sharpe calculation
        returns = []
        equity = initial_capital
        for _, trade in real_trades.iterrows():
            trade_return = trade['pnl'] / equity
            returns.append(trade_return)
            equity += trade['pnl']
        
        # Sharpe ratio
        sharpe = self.calculate_sharpe_ratio(returns) if len(returns) > 1 else 0
        
        # Max drawdown calculation
        equity_curve = [initial_capital]
        for _, trade in real_trades.iterrows():
            equity_curve.append(equity_curve[-1] + trade['pnl'])
        
        if len(equity_curve) > 1:
            equity_array = np.array(equity_curve)
            running_max = np.maximum.accumulate(equity_array)
            drawdown = (equity_array - running_max) / running_max
            max_drawdown = float(drawdown.min()) if len(drawdown) > 0 else 0
        else:
            max_drawdown = 0
        
        # Circuit breaker metrics
        paper_trades_count = len(paper_trades) if not paper_trades.empty else 0
        all_trades_pnl = trades_df['pnl'].sum() if not trades_df.empty else 0
        circuit_breaker_savings = all_trades_pnl - total_pnl
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'max_win': max_win,
            'max_loss': max_loss,
            'profit_factor': profit_factor,
            'expectancy': expectancy,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'paper_trades_count': paper_trades_count,
            'circuit_breaker_savings': circuit_breaker_savings,
            'all_trades_pnl': all_trades_pnl
        }
    
    def update_backtest_summary(self, summary: dict):
        """Update backtest summary table with comprehensive metrics"""
        # Clear existing
        for item in self.backtest_summary_tree.get_children():
            self.backtest_summary_tree.delete(item)
        
        backtest_config = self.config.get('backtest', {})
        initial_capital = backtest_config.get('initial_capital', 50000)
        
        # Get closed orders for detailed metrics
        closed_orders = None
        if 'closed_orders' in summary:
            closed_orders = summary['closed_orders']
        elif hasattr(self, 'bot') and self.bot:
            closed_orders = self.bot.engine.get_closed_orders()
        
        if closed_orders is not None and not closed_orders.empty:
            metrics = self.calculate_metrics(closed_orders, initial_capital)
        else:
            metrics = {}
        
        # Calculate basic values
        total_pnl = summary.get('total_pnl', 0)
        final_capital = initial_capital + total_pnl
        returns_pct = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0
        
        # Add metrics to table with color coding
        def add_metric(metric, value, is_category=False, metric_key=None):
            if is_category:
                self.backtest_summary_tree.insert("", tk.END, values=(metric, ""), tags=("category",))
            else:
                # Determine tag based on value
                tag = "neutral"
                if metric_key and metric_key in ['total_pnl', 'avg_win', 'max_win', 'expectancy', 'profit_factor', 'sharpe_ratio', 'sortino_ratio', 'calmar_ratio', 'returns_pct', 'circuit_breaker_savings']:
                    # Check if value is positive or negative
                    try:
                        # Extract numeric value
                        if isinstance(value, str):
                            # Remove currency symbols and extract number
                            num_str = value.replace('₹', '').replace(',', '').replace('+', '').replace('%', '').strip()
                            num_val = float(num_str)
                        else:
                            num_val = float(value)
                        
                        if num_val > 0:
                            tag = "profit"
                        elif num_val < 0:
                            tag = "loss"
                        else:
                            tag = "neutral"
                    except:
                        tag = "neutral"
                elif metric_key and metric_key in ['avg_loss', 'max_loss', 'max_drawdown']:
                    try:
                        if isinstance(value, str):
                            num_str = value.replace('₹', '').replace(',', '').replace('-', '').replace('%', '').strip()
                            num_val = float(num_str)
                        else:
                            num_val = float(value)
                        
                        if num_val < 0:
                            tag = "loss"
                        elif num_val > 0:
                            tag = "profit"
                        else:
                            tag = "neutral"
                    except:
                        tag = "neutral"
                elif metric_key and metric_key in ['win_rate']:
                    try:
                        if isinstance(value, str):
                            num_str = value.replace('%', '').strip()
                            num_val = float(num_str)
                        else:
                            num_val = float(value)
                        
                        if num_val >= 50:
                            tag = "profit"
                        elif num_val < 50:
                            tag = "loss"
                        else:
                            tag = "neutral"
                    except:
                        tag = "neutral"
                
                # Store metric key for trend viewing
                item_id = self.backtest_summary_tree.insert("", tk.END, values=(metric, value), tags=(tag,))
                if metric_key:
                    self.metric_key_map[item_id] = metric_key
        
        # Capital & Returns
        add_metric("💰 CAPITAL & RETURNS", "", True)
        add_metric("Initial Capital", f"₹{initial_capital:,.2f}", metric_key="initial_capital")
        add_metric("Final Capital", f"₹{final_capital:,.2f}", metric_key="final_capital")
        add_metric("Total PnL", f"₹{total_pnl:+,.2f}", metric_key="total_pnl")
        add_metric("Return %", f"{returns_pct:+.2f}%", metric_key="returns_pct")
        
        # Trading Activity
        add_metric("📈 TRADING ACTIVITY", "", True)
        total_orders = summary.get('total_orders', 0)
        add_metric("Total Trades (Real)", str(total_orders), metric_key="total_trades")
        if metrics:
            add_metric("Winning Trades", str(metrics.get('winning_trades', 0)), metric_key="winning_trades")
            add_metric("Losing Trades", str(metrics.get('losing_trades', 0)), metric_key="losing_trades")
            add_metric("Win Rate", f"{metrics.get('win_rate', 0):.2%}", metric_key="win_rate")
        
        # Circuit Breaker Impact
        if metrics and metrics.get('paper_trades_count', 0) > 0:
            add_metric("🛡️ CIRCUIT BREAKER", "", True)
            add_metric("Paper Trades (Protected)", str(metrics.get('paper_trades_count', 0)), metric_key="paper_trades")
            add_metric("Capital Saved", f"₹{metrics.get('circuit_breaker_savings', 0):+,.2f}", metric_key="circuit_breaker_savings")
            add_metric("PnL WITHOUT Circuit Breaker", f"₹{metrics.get('all_trades_pnl', 0):+,.2f}", metric_key="all_trades_pnl")
            add_metric("PnL WITH Circuit Breaker", f"₹{metrics.get('total_pnl', 0):+,.2f}", metric_key="total_pnl")
        
        # Performance Metrics
        if metrics:
            add_metric("💵 PROFIT & LOSS", "", True)
            add_metric("Average Win", f"₹{metrics.get('avg_win', 0):+,.2f}", metric_key="avg_win")
            add_metric("Average Loss", f"₹{metrics.get('avg_loss', 0):,.2f}", metric_key="avg_loss")
            add_metric("Largest Win", f"₹{metrics.get('max_win', 0):+,.2f}", metric_key="max_win")
            add_metric("Largest Loss", f"₹{metrics.get('max_loss', 0):,.2f}", metric_key="max_loss")
            add_metric("Profit Factor", f"{metrics.get('profit_factor', 0):.2f}", metric_key="profit_factor")
            add_metric("Expectancy per Trade", f"₹{metrics.get('expectancy', 0):+,.2f}", metric_key="expectancy")
            
            # Risk Metrics
            add_metric("⚠️ RISK METRICS", "", True)
            add_metric("Sharpe Ratio", f"{metrics.get('sharpe_ratio', 0):.2f}", metric_key="sharpe_ratio")
            add_metric("Max Drawdown", f"{metrics.get('max_drawdown', 0):.2%}", metric_key="max_drawdown")
            
            # Calculate Sortino Ratio (downside deviation)
            if hasattr(self, 'bot') and self.bot:
                closed_orders = self.bot.engine.get_closed_orders()
                if not closed_orders.empty:
                    real_trades = closed_orders[~closed_orders.get('paper_trade', pd.Series([False]*len(closed_orders)))]
                    if not real_trades.empty:
                        returns = []
                        equity = initial_capital
                        for _, trade in real_trades.iterrows():
                            trade_return = trade['pnl'] / equity
                            returns.append(trade_return)
                            equity += trade['pnl']
                        
                        if len(returns) > 1:
                            returns_array = np.array(returns)
                            downside_returns = returns_array[returns_array < 0]
                            if len(downside_returns) > 0:
                                downside_std = np.std(downside_returns, ddof=1)
                                mean_return = np.mean(returns_array)
                                if downside_std > 0:
                                    sortino = (mean_return * 252 - 0.05) / (downside_std * np.sqrt(252))
                                    add_metric("Sortino Ratio", f"{sortino:.2f}", metric_key="sortino_ratio")
                                    # Store in metrics for history
                                    metrics['sortino_ratio'] = sortino
                        
                        # Calmar Ratio
                        if metrics.get('max_drawdown', 0) != 0:
                            annual_return = (total_pnl / initial_capital) * (252 / len(real_trades)) if len(real_trades) > 0 else 0
                            calmar = annual_return / abs(metrics.get('max_drawdown', 0)) if metrics.get('max_drawdown', 0) != 0 else 0
                            add_metric("Calmar Ratio", f"{calmar:.2f}", metric_key="calmar_ratio")
                            # Store in metrics for history
                            metrics['calmar_ratio'] = calmar
        
        # System Stats
        add_metric("🔧 SYSTEM STATS", "", True)
        add_metric("Open Positions", str(summary.get('open_positions', 0)), metric_key="open_positions")
        if hasattr(self, 'bot') and self.bot:
            add_metric("Indicators Active", str(len(self.bot.engine.indicator_manager)), metric_key="indicators_active")
        
        # Store current metrics for trend tracking
        self._store_metrics_for_trend(metrics, total_pnl, final_capital, returns_pct, summary)
    
    def _store_metrics_for_trend(self, metrics: dict, total_pnl: float, final_capital: float, returns_pct: float, summary: dict):
        """Store metrics history for trend visualization"""
        if not hasattr(self, 'metrics_history'):
            return
        
        iteration = len(self.metrics_history['iteration'])
        self.metrics_history['iteration'].append(iteration)
        self.metrics_history['total_pnl'].append(total_pnl)
        self.metrics_history['equity'].append(final_capital)
        self.metrics_history['returns_pct'].append(returns_pct)
        
        if metrics:
            self.metrics_history['win_rate'].append(metrics.get('win_rate', 0) * 100)  # Convert to percentage
            self.metrics_history['sharpe_ratio'].append(metrics.get('sharpe_ratio', 0))
            self.metrics_history['max_drawdown'].append(metrics.get('max_drawdown', 0) * 100)  # Convert to percentage
            self.metrics_history['profit_factor'].append(metrics.get('profit_factor', 0))
            self.metrics_history['expectancy'].append(metrics.get('expectancy', 0))
            self.metrics_history['avg_win'].append(metrics.get('avg_win', 0))
            self.metrics_history['avg_loss'].append(metrics.get('avg_loss', 0))
            # Sortino and Calmar will be added when calculated
            self.metrics_history['sortino_ratio'].append(metrics.get('sortino_ratio', 0))
            self.metrics_history['calmar_ratio'].append(metrics.get('calmar_ratio', 0))
        else:
            self.metrics_history['win_rate'].append(0)
            self.metrics_history['sharpe_ratio'].append(0)
            self.metrics_history['max_drawdown'].append(0)
            self.metrics_history['profit_factor'].append(0)
            self.metrics_history['expectancy'].append(0)
            self.metrics_history['avg_win'].append(0)
            self.metrics_history['avg_loss'].append(0)
            self.metrics_history['sortino_ratio'].append(0)
            self.metrics_history['calmar_ratio'].append(0)
    
    def on_metric_click(self, event):
        """Handle double-click on metric value to show trend"""
        selection = self.backtest_summary_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.backtest_summary_tree.item(item, 'values')
        metric_name = values[0] if values else ""
        
        # Get metric key from map if available
        metric_key = self.metric_key_map.get(item, None)
        
        # Map metric names to keys
        metric_map = {
            "Total PnL": "total_pnl",
            "Return %": "returns_pct",
            "Win Rate": "win_rate",
            "Sharpe Ratio": "sharpe_ratio",
            "Max Drawdown": "max_drawdown",
            "Profit Factor": "profit_factor",
            "Sortino Ratio": "sortino_ratio",
            "Calmar Ratio": "calmar_ratio",
            "Final Capital": "equity",
            "Average Win": "avg_win",
            "Average Loss": "avg_loss",
            "Expectancy per Trade": "expectancy",
            "Initial Capital": "initial_capital",
            "Capital Saved": "circuit_breaker_savings"
        }
        
        if not metric_key:
            metric_key = metric_map.get(metric_name, None)
        
        if metric_key and metric_key in self.metrics_history and len(self.metrics_history[metric_key]) > 1:
            self.show_metric_trend(metric_name, metric_key)
    
    def show_metric_trend(self, metric_name: str, metric_key: str):
        """Show interactive trend chart for a metric using Plotly"""
        try:
            import plotly.graph_objects as go
            from plotly.offline import plot
            import tempfile
        except ImportError:
            messagebox.showerror("Error", "plotly is required for interactive charts.\nInstall it with: pip install plotly")
            return
        
        if metric_key not in self.metrics_history or len(self.metrics_history[metric_key]) < 2:
            messagebox.showinfo("Info", f"Insufficient data to show trend for {metric_name}.\nNeed at least 2 data points.")
            return
        
        # Get data
        iterations = self.metrics_history['iteration']
        values = self.metrics_history[metric_key]
        
        # Determine color based on metric type
        if metric_key in ['total_pnl', 'equity', 'win_rate', 'sharpe_ratio', 'profit_factor', 'sortino_ratio', 'calmar_ratio', 'returns_pct']:
            line_color = '#2e7d32'  # Green for positive metrics
            fill_color = 'rgba(46, 125, 50, 0.2)'
        elif metric_key in ['max_drawdown', 'avg_loss', 'max_loss']:
            line_color = '#c62828'  # Red for negative metrics
            fill_color = 'rgba(198, 40, 40, 0.2)'
        else:
            line_color = '#1976d2'  # Blue for neutral
            fill_color = 'rgba(25, 118, 210, 0.2)'
        
        # Create interactive plotly figure
        fig = go.Figure()
        
        # Add main trend line
        fig.add_trace(go.Scatter(
            x=iterations,
            y=values,
            mode='lines+markers',
            name=metric_name,
            line=dict(color=line_color, width=2.5),
            marker=dict(size=6, color=line_color),
            fill='tonexty',
            fillcolor=fill_color,
            hovertemplate=f'<b>Iteration:</b> %{{x}}<br><b>{metric_name}:</b> %{{y:.2f}}<extra></extra>'
        ))
        
        # Add current value line
        if len(values) > 0:
            current_val = values[-1]
            fig.add_hline(
                y=current_val,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Current: {current_val:.2f}",
                annotation_position="right"
            )
            
            # Add min/max markers
            if len(values) > 1:
                max_idx = np.argmax(values)
                min_idx = np.argmin(values)
                if max_idx != min_idx:
                    fig.add_trace(go.Scatter(
                        x=[iterations[max_idx]],
                        y=[values[max_idx]],
                        mode='markers',
                        name='Max',
                        marker=dict(size=12, color='green', symbol='triangle-up'),
                        hovertemplate=f'<b>Max:</b> {values[max_idx]:.2f}<br><b>Iteration:</b> {iterations[max_idx]}<extra></extra>'
                    ))
                    
                    fig.add_trace(go.Scatter(
                        x=[iterations[min_idx]],
                        y=[values[min_idx]],
                        mode='markers',
                        name='Min',
                        marker=dict(size=12, color='red', symbol='triangle-down'),
                        hovertemplate=f'<b>Min:</b> {values[min_idx]:.2f}<br><b>Iteration:</b> {iterations[min_idx]}<extra></extra>'
                    ))
        
        # Update layout
        fig.update_layout(
            title=dict(
                text=f'{metric_name} Trend Over Time',
                font=dict(size=18, color='#2c3e50'),
                x=0.5
            ),
            xaxis=dict(
                title=dict(text='Iteration', font=dict(size=14, color='#2c3e50')),
                tickfont=dict(size=11),
                showgrid=True,
                gridcolor='rgba(128, 128, 128, 0.2)'
            ),
            yaxis=dict(
                title=dict(text=metric_name, font=dict(size=14, color='#2c3e50')),
                tickfont=dict(size=11),
                showgrid=True,
                gridcolor='rgba(128, 128, 128, 0.2)'
            ),
            hovermode='x unified',
            template='plotly_white',
            height=600,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # Generate HTML content using plotly's to_html method
        try:
            html_content = fig.to_html(
                include_plotlyjs='cdn',  # Use CDN for better compatibility
                config={
                    'displayModeBar': True,
                    'displaylogo': False,
                    'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'drawclosedpath', 'drawcircle', 'drawrect', 'eraseshape']
                }
            )
            
            # Save to temporary file
            html_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
            html_path = html_file.name
            html_file.write(html_content)
            html_file.close()
            
            # Try to display chart in popup window
            chart_displayed = False
            
            # Method 1: Try tkinterweb with JavaScript enabled
            try:
                import tkinterweb
                
                # Create popup window
                chart_window = tk.Toplevel(self.root)
                chart_window.title(f"Trend: {metric_name}")
                chart_window.geometry("900x700")
                
                # Create frame for webview with JavaScript enabled (required for Plotly)
                # Note: enable_javascript may not be available in all tkinterweb versions
                try:
                    html_frame = tkinterweb.HtmlFrame(chart_window, messages_enabled=False, enable_javascript=True)
                except TypeError:
                    # If enable_javascript parameter doesn't exist, try without it
                    html_frame = tkinterweb.HtmlFrame(chart_window, messages_enabled=False)
                
                # Load HTML content directly (better for JavaScript)
                try:
                    html_frame.load_html(html_content)
                except AttributeError:
                    # If load_html doesn't exist, use load_file with absolute path
                    import os
                    abs_html_path = os.path.abspath(html_path)
                    html_frame.load_file(abs_html_path)
                
                html_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
                
                # Add close button
                close_btn = ttk.Button(chart_window, text="Close", command=chart_window.destroy)
                close_btn.pack(pady=5)
                chart_displayed = True
                
            except (ImportError, Exception) as e:
                print(f"Warning: tkinterweb failed: {e}")
                import traceback
                traceback.print_exc()
            
            # Method 2: Fallback to browser
            if not chart_displayed:
                import webbrowser
                import os
                webbrowser.open(f'file://{os.path.abspath(html_path)}')
                messagebox.showinfo("Info", f"Chart opened in browser.\nTo display in popup window, install:\npip install tkinterweb[javascript]")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create chart: {str(e)}")
    
    def on_symbol_click(self, event):
        """Handle double-click on symbol in LTP table to show price trend"""
        selection = self.ltp_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        
        # Get symbol from mapping
        if not hasattr(self, 'ltp_symbol_map'):
            return
        
        symbol = self.ltp_symbol_map.get(item, None)
        if not symbol:
            # Try to get from values
            values = self.ltp_tree.item(item, 'values')
            if values:
                symbol_short = values[0]
                # Find full symbol from config
                symbols = self.config.get('symbols', [])
                for s in symbols:
                    if s.split(':')[-1] == symbol_short:
                        symbol = s
                        break
        
        if not symbol or symbol not in self.ltp_history:
            messagebox.showinfo("Info", f"No price history available for this symbol yet.\nStart trading to collect price data.")
            return
        
        history = self.ltp_history[symbol]
        if len(history) < 2:
            messagebox.showinfo("Info", f"Insufficient data to show trend.\nNeed at least 2 data points.")
            return
        
        # Create interactive price trend chart using Plotly
        try:
            import plotly.graph_objects as go
            from plotly.offline import plot
            import webbrowser
            import tempfile
        except ImportError:
            messagebox.showerror("Error", "plotly is required for interactive charts.\nInstall it with: pip install plotly")
            return
        
        # Extract timestamps and prices
        timestamps = [h[0] for h in history]
        prices = [h[1] for h in history]
        
        symbol_short = symbol.split(':')[-1]
        
        # Calculate statistics
        if len(prices) > 0:
            min_price = min(prices)
            max_price = max(prices)
            current_price = prices[-1]
            price_change = current_price - prices[0] if len(prices) > 1 else 0
            price_change_pct = (price_change / prices[0] * 100) if len(prices) > 1 and prices[0] > 0 else 0
        else:
            min_price = max_price = current_price = price_change = price_change_pct = 0
        
        # Create interactive plotly figure
        fig = go.Figure()
        
        # Add price line with fill to zero
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=prices,
            mode='lines+markers',
            name='Price',
            line=dict(color='#2c3e50', width=2),
            marker=dict(size=4, color='#3498db'),
            fill='tozeroy',
            fillcolor='rgba(52, 152, 219, 0.2)',
            hovertemplate='<b>Time:</b> %{x}<br><b>Price:</b> ₹%{y:.2f}<extra></extra>'
        ))
        
        # Add min/max markers
        if len(prices) > 1:
            min_idx = prices.index(min_price)
            max_idx = prices.index(max_price)
            
            fig.add_trace(go.Scatter(
                x=[timestamps[min_idx]],
                y=[min_price],
                mode='markers',
                name='Min Price',
                marker=dict(size=12, color='red', symbol='triangle-down'),
                hovertemplate=f'<b>Min Price:</b> ₹{min_price:.2f}<br><b>Time:</b> {timestamps[min_idx]}<extra></extra>'
            ))
            
            fig.add_trace(go.Scatter(
                x=[timestamps[max_idx]],
                y=[max_price],
                mode='markers',
                name='Max Price',
                marker=dict(size=12, color='green', symbol='triangle-up'),
                hovertemplate=f'<b>Max Price:</b> ₹{max_price:.2f}<br><b>Time:</b> {timestamps[max_idx]}<extra></extra>'
            ))
        
        # Add current price line
        fig.add_hline(
            y=current_price,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Current: ₹{current_price:.2f}",
            annotation_position="right"
        )
        
        # Update layout
        fig.update_layout(
            title=dict(
                text=f'Price Trend: {symbol_short}',
                font=dict(size=18, color='#2c3e50'),
                x=0.5
            ),
            xaxis=dict(
                title=dict(text='Time', font=dict(size=14, color='#2c3e50')),
                tickfont=dict(size=11),
                showgrid=True,
                gridcolor='rgba(128, 128, 128, 0.2)'
            ),
            yaxis=dict(
                title=dict(text='Price (₹)', font=dict(size=14, color='#2c3e50')),
                tickfont=dict(size=11),
                showgrid=True,
                gridcolor='rgba(128, 128, 128, 0.2)'
            ),
            hovermode='x unified',
            template='plotly_white',
            height=600,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            annotations=[
                dict(
                    text=f"Current: ₹{current_price:.2f} | Min: ₹{min_price:.2f} | Max: ₹{max_price:.2f}<br>"
                         f"Change: ₹{price_change:+.2f} ({price_change_pct:+.2f}%) | Points: {len(prices)}",
                    xref="paper", yref="paper",
                    x=0.5, y=-0.15,
                    xanchor='center', yanchor='top',
                    showarrow=False,
                    font=dict(size=11, color='#555')
                )
            ],
            margin=dict(b=80)
        )
        
        # Generate HTML content using plotly's to_html method
        try:
            html_content = fig.to_html(
                include_plotlyjs='cdn',  # Use CDN for better compatibility
                config={
                    'displayModeBar': True,
                    'displaylogo': False,
                    'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'drawclosedpath', 'drawcircle', 'drawrect', 'eraseshape']
                }
            )
            
            # Save to temporary file
            html_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
            html_path = html_file.name
            html_file.write(html_content)
            html_file.close()
            
            # Try to display chart in popup window
            chart_displayed = False
            
            # Method 1: Try tkinterweb with JavaScript enabled
            try:
                import tkinterweb
                
                # Create popup window
                chart_window = tk.Toplevel(self.root)
                chart_window.title(f"Price Trend: {symbol_short}")
                chart_window.geometry("1000x700")
                
                # Create frame for webview with JavaScript enabled (required for Plotly)
                # Note: enable_javascript may not be available in all tkinterweb versions
                try:
                    html_frame = tkinterweb.HtmlFrame(chart_window, messages_enabled=False, enable_javascript=True)
                except TypeError:
                    # If enable_javascript parameter doesn't exist, try without it
                    html_frame = tkinterweb.HtmlFrame(chart_window, messages_enabled=False)
                
                # Load HTML content directly (better for JavaScript)
                try:
                    html_frame.load_html(html_content)
                except AttributeError:
                    # If load_html doesn't exist, use load_file with absolute path
                    import os
                    abs_html_path = os.path.abspath(html_path)
                    html_frame.load_file(abs_html_path)
                
                html_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
                
                # Add close button
                close_btn = ttk.Button(chart_window, text="Close", command=chart_window.destroy)
                close_btn.pack(pady=5)
                chart_displayed = True
                
            except (ImportError, Exception) as e:
                print(f"Warning: tkinterweb failed: {e}")
                import traceback
                traceback.print_exc()
            
            # Method 2: Fallback to browser
            if not chart_displayed:
                import webbrowser
                import os
                webbrowser.open(f'file://{os.path.abspath(html_path)}')
                messagebox.showinfo("Info", f"Chart opened in browser.\nTo display in popup window, install:\npip install tkinterweb[javascript]")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create chart: {str(e)}")


def main():
    """Main entry point"""
    root = tk.Tk()
    app = TradingGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
