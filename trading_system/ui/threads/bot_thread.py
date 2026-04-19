"""
Bot Thread Module

Contains the BotThread class for running trading operations in a background thread.
"""

import time
import yaml
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal

# Import the data generator
from trading_system.ui.utils.data_generator import combined_data_generator


class BotThread(QThread):
    """
    Thread for running trading bot operations.
    
    This thread handles both intraday and backtesting modes,
    emitting signals to update the UI without blocking.
    
    Signals:
        status_update: Emitted with (message, color) for status updates
        results_update: Emitted with list of analysis results
        positions_update: Emitted with dict of current positions
        trades_update: Emitted with DataFrame of closed trades
        summary_update: Emitted with dict of summary metrics
        error_occurred: Emitted with error message string
        finished_signal: Emitted when thread completes
        event_log: Emitted with (event_type, message) for logging
    
    Attributes:
        config_path: Path to trading configuration file
        indicators_config_path: Path to indicators configuration file
        is_backtest: Whether running in backtest mode
        is_running: Whether the thread is currently running
        bot: LiveTradingBot instance
    """
    
    # Qt Signals for UI communication
    status_update = Signal(str, str)  # message, color
    results_update = Signal(list)  # results
    positions_update = Signal(dict)  # positions
    trades_update = Signal(object)  # trades DataFrame
    summary_update = Signal(dict)  # summary
    error_occurred = Signal(str)  # error message
    finished_signal = Signal()
    event_log = Signal(str, str)  # event_type, message
    backtest_data_ready = Signal(dict)  # symbol -> DataFrame mapping for chart viewing
    backtest_progress_update = Signal(dict, object)  # progressive data and trades for live chart updates
    
    def __init__(
        self,
        config_path: Path,
        indicators_config_path: Path,
        is_backtest: bool = False,
        parent=None
    ):
        """
        Initialize the BotThread.
        
        Args:
            config_path: Path to trading configuration file
            indicators_config_path: Path to indicators configuration file
            is_backtest: Whether to run in backtest mode
            parent: Parent QObject
        """
        super().__init__(parent)
        self.config_path = config_path
        self.indicators_config_path = indicators_config_path
        self.is_backtest = is_backtest
        self.is_running = False
        self.bot = None
        self._last_closed_count = 0
        self._last_results = []
    
    def run(self):
        """Run bot in thread."""
        try:
            # Import here to avoid circular imports
            from trading_system.run_live_bot import LiveTradingBot
            
            self.bot = LiveTradingBot(
                config_path=str(self.config_path),
                indicators_config_path=str(self.indicators_config_path)
            )
            
            # Update engine config with latest settings
            self._update_engine_config()
            
            if self.is_backtest:
                self.run_backtest()
            else:
                self.run_intraday()
        except Exception as e:
            self.error_occurred.emit(f"Failed to start bot: {e}")
            import traceback
            self.error_occurred.emit(traceback.format_exc())
        finally:
            self.is_running = False
            self.status_update.emit("Stopped", "red")
            self.finished_signal.emit()
    
    def _update_engine_config(self):
        """Update trading engine config with latest settings from file."""
        if not self.bot or not hasattr(self.bot, 'engine'):
            return
        
        # Reload config to get latest settings
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Update engine config
        self.bot.engine.config = config
        
        # Update paper trading mode settings
        paper_mode_config = config.get('risk_management', {}).get('paper_trading_mode', {})
        self.bot.engine.paper_mode_config = paper_mode_config
        self.bot.engine.paper_mode_enabled = paper_mode_config.get('enabled', False)
        self.bot.engine.paper_mode_trigger = paper_mode_config.get('consecutive_losses_trigger', 3)
        
        # Reload slippage configuration (backtesting only)
        if hasattr(self.bot.engine, '_load_slippage_config'):
            self.bot.engine._load_slippage_config()
        
        # Reset paper trading state (start fresh)
        self.bot.engine.consecutive_losses = 0
        self.bot.engine.paper_trading_mode = False
        
        # Log configuration status
        enabled = self.bot.engine.paper_mode_enabled
        trigger = self.bot.engine.paper_mode_trigger
        
        print(f"✅ Updated engine config - Paper Trading Mode: {'ENABLED' if enabled else 'DISABLED'}, Trigger: {trigger} consecutive losses")
        
        if not enabled:
            print(f"⚠️  WARNING: Circuit breaker is DISABLED!")
        else:
            print(f"🛡️  Circuit breaker is ENABLED and will activate after {trigger} consecutive losses")
    
    def run_intraday(self):
        """Run intraday bot with different refresh rates for symbols with/without positions."""
        self.is_running = True
        self.status_update.emit("Running...", "green")
        
        # Track last refresh time for each symbol
        last_refresh = {}
        
        # Initialize refresh intervals
        fast_refresh_interval = 15  # After order is taken
        slow_refresh_interval = 30  # Default
        
        while self.is_running:
            try:
                current_time = datetime.now()
                
                # Reload config
                self.bot.config = self.bot.load_config(str(self.config_path))
                self.bot.engine.config = self.bot.config
                
                # Get refresh intervals from config
                trading_config = self.bot.config.get('trading', {})
                fast_refresh_interval = trading_config.get('fast_refresh_interval', 15)
                slow_refresh_interval = trading_config.get('slow_refresh_interval', 30)
                
                # Get current positions
                positions_before = self.bot.engine.current_positions.copy()
                positions_set = set(positions_before.keys())
                
                all_symbols = set(self.bot.config.get('symbols', []))
                
                results = []
                symbols_to_refresh = []
                
                # Determine which symbols need refresh
                for symbol in all_symbols:
                    if symbol in positions_set:
                        # Symbols with positions: faster refresh
                        if symbol not in last_refresh or (current_time - last_refresh[symbol]).total_seconds() >= fast_refresh_interval:
                            symbols_to_refresh.append(symbol)
                            last_refresh[symbol] = current_time
                    else:
                        # Symbols without positions: slower refresh
                        if symbol not in last_refresh or (current_time - last_refresh[symbol]).total_seconds() >= slow_refresh_interval:
                            symbols_to_refresh.append(symbol)
                            last_refresh[symbol] = current_time
                
                # Refresh symbols that need updating
                if symbols_to_refresh:
                    increment = not hasattr(self, '_last_results') or len(symbols_to_refresh) == len(all_symbols)
                    symbol_results = self.bot.run_once(symbols=symbols_to_refresh, increment_count=increment)
                    
                    # Merge with existing results
                    if hasattr(self, '_last_results') and self._last_results:
                        existing_results = {r.get('symbol'): r for r in self._last_results if r.get('symbol')}
                        for r in symbol_results:
                            existing_results[r.get('symbol')] = r
                        results = list(existing_results.values())
                    else:
                        results = symbol_results
                    
                    self._last_results = results
                else:
                    results = self._last_results if hasattr(self, '_last_results') else []
                
                # Emit updates
                self.results_update.emit(results)
                self.positions_update.emit(self.bot.engine.current_positions.copy())
                
                closed_orders = self.bot.engine.get_closed_orders()
                if not closed_orders.empty:
                    self.trades_update.emit(closed_orders)
                
                self.summary_update.emit(self.bot.engine.get_summary())
                
                # Sleep between cycles
                time.sleep(1)
                
            except Exception as e:
                self.error_occurred.emit(str(e))
                import traceback
                self.error_occurred.emit(traceback.format_exc())
                break
    
    def run_backtest(self):
        """Run backtest with real-time updates."""
        self.is_running = True
        self.status_update.emit("Running backtest...", "blue")
        self.event_log.emit("INFO", "Backtest started")
        self._run_backtest_loop()
    
    def _run_backtest_loop(self):
        """The actual backtesting loop."""
        try:
            self._last_closed_count = 0
            backtest_config = self.bot.config.get('backtest', {})
            symbols = self.bot.config.get('symbols', [])
            start_date = backtest_config.get('start_date')
            end_date = backtest_config.get('end_date')
            resolution = backtest_config.get('resolution', '1min')
            speed = backtest_config.get('speed', 'fast')
            
            # Fetch all data once
            all_data = self.bot.data_loader.get_all_backtest_data(symbols, start_date, end_date, resolution)
            
            # Emit the full historical data for chart viewing
            self.backtest_data_ready.emit(all_data)
            
            # Create combined generator
            data_generator = combined_data_generator(all_data)
            
            # Progressive dataframes
            progressive_dfs = {symbol: pd.DataFrame(columns=df.columns) for symbol, df in all_data.items() if df is not None}
            
            current_step = 0
            total_steps = 0
            update_interval = 10
            last_update_step = 0
            
            # Speed control delays
            speed_delays = {
                'realtime': 0.1,
                'slow': 0.05,
                'medium': 0.01,
                'fast': 0.001
            }
            delay = speed_delays.get(speed, 0.001)
            
            for timestamp, current_data_row, all_timestamps in data_generator:
                if not self.is_running:
                    break
                if total_steps == 0:
                    total_steps = len(all_timestamps)
                
                results = []
                
                # Convert timestamp
                current_timestamp = timestamp
                if isinstance(timestamp, pd.Timestamp):
                    current_timestamp = timestamp.to_pydatetime()
                elif not isinstance(timestamp, datetime):
                    try:
                        current_timestamp = pd.to_datetime(timestamp).to_pydatetime()
                    except:
                        current_timestamp = datetime.now()
                
                for symbol, data_row in current_data_row.items():
                    if symbol not in progressive_dfs:
                        continue
                    
                    # Append new row to progressive df
                    progressive_dfs[symbol] = pd.concat([progressive_dfs[symbol], data_row.to_frame().T])
                    
                    df_slice = progressive_dfs[symbol]
                    
                    # Run analysis
                    if not df_slice.empty:
                        analysis_result = self.bot.engine.analyze_symbol(df_slice, symbol)
                        self.bot.engine.execute_trading_decision(analysis_result, df=df_slice, current_timestamp=current_timestamp)
                        results.append(analysis_result)
                
                current_step += 1
                
                # Batch UI updates
                should_update_ui = (current_step - last_update_step) >= update_interval or current_step == total_steps
                
                if should_update_ui:
                    self.results_update.emit(results)
                    self.positions_update.emit(self.bot.engine.current_positions.copy())
                    closed_orders = self.bot.engine.get_closed_orders()
                    if not closed_orders.empty:
                        self.trades_update.emit(closed_orders)
                    summary = self.bot.engine.get_summary()
                    self.summary_update.emit(summary)
                    
                    # Log total charges and net profit every iteration
                    total_charges = summary.get('total_charges', 0.0)
                    total_net_profit = summary.get('total_net_profit', summary.get('total_pnl', 0.0))
                    total_gross_pnl = summary.get('total_gross_pnl', summary.get('total_pnl', 0.0))
                    print(f"📊 Iteration {current_step}/{total_steps} | Total Charges: ₹{total_charges:.2f} | Gross PnL: ₹{total_gross_pnl:+.2f} | Net Profit: ₹{total_net_profit:+.2f} | Capital: ₹{summary.get('actual_capital', 0):,.2f}")
                    
                    # Emit progressive chart data for live updates
                    self.backtest_progress_update.emit(progressive_dfs.copy(), closed_orders)
                    
                    # Capture events
                    self._capture_engine_events()
                    
                    progress = (current_step / total_steps) * 100 if total_steps > 0 else 0
                    status_msg = f"Backtesting... {int(progress)}%"
                    self.status_update.emit(status_msg, "blue")
                    
                    last_update_step = current_step
                    time.sleep(delay)
            
            self.status_update.emit("Backtest completed", "green")
            self.event_log.emit("INFO", "Backtest completed")
        except Exception as e:
            self.error_occurred.emit(str(e))
            import traceback
            self.error_occurred.emit(traceback.format_exc())
    
    def _capture_engine_events(self):
        """Capture and emit trading events from the engine."""
        if not self.bot or not hasattr(self.bot, 'engine'):
            return
        
        # Check for new closed orders
        closed_orders = self.bot.engine.get_closed_orders()
        if closed_orders.empty:
            return
        
        current_count = len(closed_orders)
        if current_count > self._last_closed_count:
            # New trades closed - emit events
            new_orders = closed_orders.iloc[self._last_closed_count:]
            for _, order in new_orders.iterrows():
                symbol = order.get('symbol', 'Unknown')
                pnl = order.get('pnl', 0)
                reason = order.get('exit_reason', 'Unknown')
                
                if pnl >= 0:
                    event_type = "PROFIT"
                    msg = f"Trade closed: {symbol} | PnL: ₹{pnl:+,.2f} | Reason: {reason}"
                else:
                    event_type = "LOSS"
                    msg = f"Trade closed: {symbol} | PnL: ₹{pnl:,.2f} | Reason: {reason}"
                
                self.event_log.emit(event_type, msg)
            
            self._last_closed_count = current_count
    
    def stop(self):
        """Stop the running thread."""
        self.is_running = False
