"""
Live Trading Bot - Refactored Version

Runs the trading system continuously, checking every 5 seconds
for real-time trading decisions.

This version uses modular components:
- bot.display_manager: Console/display logic
- bot.trading_operations: Core trading logic
- bot.backtest_manager: Backtest-specific functionality
- bot.config_manager: Configuration management
"""

import sys
import os
import time
from rich.console import Console

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading_system.core.trading_engine import TradingEngine
from trading_system.data.data_loader import DataLoader
from trading_system.core.indicator_loader import IndicatorLoader

# Import modular components
from trading_system.bot.display_manager import DisplayManager
from trading_system.bot.trading_operations import TradingOperations
from trading_system.bot.backtest_manager import BacktestManager
from trading_system.bot.config_manager import ConfigManager

# No indicator imports needed! They're loaded dynamically from config

console = Console()


class LiveTradingBot:
    """
    Real-time trading bot that monitors symbols and executes trades.
    
    Refactored to use modular components for better organization.
    """
    
    def __init__(self, 
                 config_path="trading_system/config/trading_config.yaml",
                 indicators_config_path="trading_system/config/indicators_config.yaml"):
        """Initialize the live trading bot."""
        # Initialize config manager
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.config
        
        # Import data_bridge for real-time backtest updates
        try:
            from trading_system.ui.backend.data_bridge import data_bridge
            self.data_bridge = data_bridge
            console.print("[dim]✅ DataBridge connected for real-time updates[/dim]")
        except ImportError as e:
            console.print(f"[dim yellow]⚠️  DataBridge not available: {e}[/dim yellow]")
            self.data_bridge = None
        
        # Dynamic indicator loading
        console.print("\n[bold cyan]🔌 Initializing Plug-and-Play Indicator System...[/bold cyan]\n")
        self.indicator_loader = IndicatorLoader(
            config_path=indicators_config_path,
            trading_config_path=config_path
        )
        self.indicator_loader.validate_config()
        
        # Get aggregation config from indicator loader
        agg_config = self.indicator_loader.get_aggregation_config()
        aggregation_strategy = agg_config.get('strategy', 'weighted')
        threshold_config = agg_config.get('threshold', {})
        
        # Get min_agreement from trading config
        min_agreement = self.config.get('min_agreement', 0.5)
        
        self.engine = TradingEngine(
            aggregation_strategy=aggregation_strategy,
            threshold_config=threshold_config,
            config=self.config,
            min_agreement=min_agreement
        )
        
        # Debug: Show capital configuration after engine initialization
        backtest_config = self.config.get('backtest', {})
        initial_capital = backtest_config.get('initial_capital', 'NOT FOUND')
        console.print(f"\n[bold green]💰 CAPITAL CONFIGURATION:[/bold green]")
        console.print(f"   Config File: {config_path}")
        console.print(f"   backtest.initial_capital: {initial_capital}")
        console.print(f"   Engine initial_capital: ₹{self.engine.initial_capital:,.2f}")
        console.print(f"   Engine actual_capital: ₹{self.engine.actual_capital:,.2f}")
        risk_config = self.config.get('risk_management', {})
        intraday_pct = risk_config.get('capital_percentage_per_trade_intraday', 'NOT FOUND')
        console.print(f"   capital_percentage_per_trade_intraday: {intraday_pct}")
        console.print("")
        
        # Check if backtest mode is enabled
        self.backtest_mode = self.config.get('backtest', {}).get('enabled', False)
        
        # Initialize data loader with mode
        self.data_loader = DataLoader(
            backtest_mode=self.backtest_mode,
            backtest_config=backtest_config
        )
        
        # Load indicators dynamically (no hardcoded imports!)
        indicators = self.indicator_loader.load_indicators(verbose=True)
        self.engine.register_indicators(indicators)
        
        # Store indicator info for display
        self.indicator_info = self.indicator_loader.get_indicator_info()
        
        # Bot settings
        self.refresh_interval = self.config['trading'].get('refresh_interval', 5)
        self.slow_refresh_interval = self.config['trading'].get('slow_refresh_interval', 15)
        self.fast_refresh_interval = self.config['trading'].get('fast_refresh_interval', 3)
        self.auto_trade = self.config['trading'].get('enable_auto_trading', False)
        self.default_quantity = self.config['trading'].get('default_quantity', 1)
        
        # Trade direction control
        self.allow_buy = self.config['trading'].get('allow_buy', True)
        self.allow_sell = self.config['trading'].get('allow_sell', True)
        
        # Stats
        self.refresh_count = 0
        self.total_signals_generated = 0
        
        # Initialize modular components
        self.display_manager = DisplayManager(self.engine, self.config, console)
        self.trading_operations = TradingOperations(
            self.engine, self.data_loader, self.config,
            self.auto_trade, self.allow_buy, self.allow_sell,
            self.default_quantity, self.backtest_mode, console
        )
        self.backtest_manager = BacktestManager(
            self.engine, self.data_loader, self.config,
            self.display_manager, self.allow_buy, self.allow_sell,
            self.refresh_count, console
        )
        
        # UI Integration (optional - doesn't affect bot logic)
        self.ui_integration = None
        try:
            from trading_system.ui.bot_integration import integrate_ui_with_bot
            self.ui_integration = integrate_ui_with_bot(self)
            console.print("[green]✅ Web UI integration enabled[/green]")
        except Exception as e:
            console.print(f"[dim]ℹ️  Web UI not available: {e}[/dim]")
            console.print("[dim]   (Bot will run normally without web UI)[/dim]")
        
        # Display backtest mode if enabled
        if self.backtest_mode:
            console.print("\n[bold yellow]🔄 BACKTEST MODE ENABLED[/bold yellow]")
            console.print(f"[yellow]Period: {backtest_config.get('start_date')} to {backtest_config.get('end_date')}[/yellow]")
            console.print(f"[yellow]Initial Capital: ₹{backtest_config.get('initial_capital', 100000):,.2f}[/yellow]")
            console.print(f"[yellow]Speed: {backtest_config.get('speed', 'fast')}[/yellow]\n")
    
    def load_config(self, config_path):
        """Load configuration from YAML file (delegates to ConfigManager)."""
        return self.config_manager.load_config(config_path)
    
    def run_once(self, symbols=None, increment_count=True):
        """Run one analysis cycle for specified symbols (or all if None)."""
        if increment_count:
            self.refresh_count += 1
        
        # Delegate to trading operations
        results = self.trading_operations.run_once(symbols, increment_count=False)
        
        # Update signal count
        self.total_signals_generated = self.trading_operations.total_signals_generated
        
        return results
    
    def display_results(self, results):
        """Display results with proper Rich rendering (delegates to DisplayManager)."""
        self.display_manager.display_results(
            results, self.refresh_count, self.auto_trade,
            self.allow_buy, self.allow_sell, self.total_signals_generated,
            self.refresh_interval
        )
    
    # Delegate display methods to DisplayManager
    def create_comprehensive_table(self, results):
        """Create comprehensive table (delegates to DisplayManager)."""
        return self.display_manager.create_comprehensive_table(results)
    
    def create_completed_orders_table(self, orders_df):
        """Create completed orders table (delegates to DisplayManager)."""
        return self.display_manager.create_completed_orders_table(orders_df)
    
    def create_kpi_panel(self, results, closed_orders_df):
        """Create KPI panel (delegates to DisplayManager)."""
        return self.display_manager.create_kpi_panel(
            results, closed_orders_df, self.refresh_count,
            self.total_signals_generated, self.refresh_interval
        )
    
    def run(self):
        """Run the bot in either live or backtest mode."""
        if self.backtest_mode:
            return self.run_backtest()
        else:
            return self.run_live()
    
    def run_live(self):
        """Run the live trading bot with dynamic refresh intervals based on positions."""
        from datetime import datetime
        
        console.print("\n[bold cyan]🤖 Starting Live Trading Bot...[/bold cyan]\n")
        console.print(f"Symbols: {', '.join(self.config['symbols'])}")
        console.print(f"Slow Refresh (all symbols): {self.slow_refresh_interval}s")
        console.print(f"Fast Refresh (positions): {self.fast_refresh_interval}s")
        console.print(f"Auto-Trading: {'ENABLED' if self.auto_trade else 'DISABLED'}")
        
        # Show trade direction settings
        buy_status = "[green]ENABLED[/green]" if self.allow_buy else "[dim]DISABLED[/dim]"
        sell_status = "[red]ENABLED[/red]" if self.allow_sell else "[dim]DISABLED[/dim]"
        console.print(f"Trade Directions: BUY {buy_status} | SELL {sell_status}")
        
        console.print(f"Indicators: {len(self.engine.indicator_manager)} active")
        console.print("\n[dim]Press Ctrl+C to stop[/dim]\n")
        
        time.sleep(2)
        
        # Track last refresh time for each symbol
        last_refresh = {}
        # Cache last results for all symbols to ensure complete display
        cached_results = {}  # symbol -> result dict
        
        try:
            while True:
                current_time = datetime.now()
                
                # Get current positions to determine which symbols need fast refresh
                current_positions = set(self.engine.current_positions.keys())
                all_symbols = set(self.config['symbols'])
                
                # Determine which symbols need refresh
                symbols_to_refresh = []
                
                for symbol in all_symbols:
                    # Check if symbol has a position (needs fast refresh)
                    has_position = symbol in current_positions
                    
                    # Determine required interval for this symbol
                    required_interval = self.fast_refresh_interval if has_position else self.slow_refresh_interval
                    
                    # Check if enough time has passed since last refresh
                    if symbol not in last_refresh:
                        # First time - refresh immediately
                        symbols_to_refresh.append(symbol)
                        last_refresh[symbol] = current_time
                    else:
                        time_since_refresh = (current_time - last_refresh[symbol]).total_seconds()
                        if time_since_refresh >= required_interval:
                            symbols_to_refresh.append(symbol)
                            last_refresh[symbol] = current_time
                
                # Run analysis only for symbols that need refresh
                fresh_results = []
                if symbols_to_refresh:
                    fresh_results = self.run_once(symbols=symbols_to_refresh, increment_count=True)
                    # Update cache with fresh results
                    for result in fresh_results:
                        cached_results[result['symbol']] = result
                else:
                    # No symbols need refresh yet, just wait a bit
                    time.sleep(0.5)
                    continue
                
                # Build complete results list: fresh results + cached results for symbols not refreshed
                # Start with fresh results (most up-to-date)
                complete_results = list(fresh_results)
                
                # Add cached results for symbols that weren't refreshed this cycle
                symbols_refreshed = {r['symbol'] for r in fresh_results}
                for symbol in all_symbols:
                    if symbol not in symbols_refreshed and symbol in cached_results:
                        # Use cached result for symbols not refreshed this cycle
                        cached_result = cached_results[symbol].copy()
                        
                        # If symbol has a position, try to update price from position data
                        # This ensures PnL is calculated correctly even with cached results
                        if symbol in current_positions:
                            position = self.engine.current_positions[symbol]
                            # Use current_price from position if available (updated by exit checks)
                            if 'current_price' in position and position['current_price'] > 0:
                                cached_result['latest_price'] = position['current_price']
                        
                        complete_results.append(cached_result)
                
                # Ensure all symbols are represented (create placeholder for symbols never analyzed)
                symbols_in_results = {r['symbol'] for r in complete_results}
                for symbol in all_symbols:
                    if symbol not in symbols_in_results:
                        # Create placeholder result for symbols not yet analyzed
                        # But still show position if it exists
                        placeholder = {
                            'symbol': symbol,
                            'latest_price': 0.0,
                            'final_signal': 'HOLD',
                            'agreement_score': 0.0,
                            'indicator_signals': {}
                        }
                        # If symbol has position, try to get current price
                        if symbol in current_positions:
                            position = self.engine.current_positions[symbol]
                            if 'current_price' in position and position['current_price'] > 0:
                                placeholder['latest_price'] = position['current_price']
                        
                        complete_results.append(placeholder)
                
                # Sort results to match config symbol order for consistent display
                symbol_order = {symbol: idx for idx, symbol in enumerate(self.config['symbols'])}
                complete_results.sort(key=lambda r: symbol_order.get(r['symbol'], 999))
                
                # Broadcast to web UI (if available) - use fresh results only
                if self.ui_integration:
                    try:
                        self.ui_integration.after_run_once(fresh_results)
                    except Exception:
                        pass  # Silent fail - UI errors shouldn't affect bot operation
                
                # Clear screen and display complete results (all symbols)
                self.display_manager.clear()
                self.display_results(complete_results)
                
                # Show refresh status
                position_count = len(current_positions)
                if position_count > 0:
                    position_symbols = ', '.join(list(current_positions)[:3])
                    if len(current_positions) > 3:
                        position_symbols += f" (+{len(current_positions) - 3} more)"
                    console.print(f"\n[dim]⏱  Positions: {position_count} | Fast refresh: {self.fast_refresh_interval}s | Slow refresh: {self.slow_refresh_interval}s[/dim]")
                    console.print(f"[dim]   Active positions: {position_symbols}[/dim]")
                else:
                    console.print(f"\n[dim]⏱  No positions | Scanning all symbols every {self.slow_refresh_interval}s | Press Ctrl+C to stop[/dim]")
                
                # Sleep for a short interval before next check (allows for fast refresh of positions)
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            console.print("\n\n[yellow]🛑 Stopping bot...[/yellow]")
            
            # Show final summary
            summary = self.engine.get_summary()
            console.print("\n[bold green]📊 Final Summary:[/bold green]")
            console.print(f"  Total Refreshes: {self.refresh_count}")
            console.print(f"  Total Orders: {summary['total_orders']}")
            console.print(f"  Total PnL: ₹{summary['total_pnl']:+.2f}")
            
            console.print("\n[green]✅ Bot stopped successfully![/green]\n")
    
    def run_backtest(self):
        """Run backtesting loop with progressive data - Print new table each iteration."""
        console.print("\n[bold cyan]🔄 Starting Backtest...[/bold cyan]\n")
        
        backtest_config = self.config.get('backtest', {})
        speed = backtest_config.get('speed', 'fast')
        initial_capital = backtest_config.get('initial_capital', 20000)
        
        # Handle symbols as strings or dicts
        symbols_list = self.config.get('symbols', [])
        if symbols_list and isinstance(symbols_list[0], dict):
            symbols_str = ', '.join([s['symbol'] for s in symbols_list])
        else:
            symbols_str = ', '.join(symbols_list)
        console.print(f"Symbols: {symbols_str}")
        console.print(f"Speed: {speed.upper()}")
        console.print(f"Indicators: {len(self.engine.indicator_manager)} active")
        console.print(f"Date Range: {backtest_config.get('start_date')} to {backtest_config.get('end_date')}")
        console.print("\n[dim]Press Ctrl+C to stop[/dim]\n")
        
        # Initialize backtest in data_bridge for real-time UI updates
        if self.data_bridge:
            total_iterations = 0
            if self.data_loader.generators:
                first_gen = list(self.data_loader.generators.values())[0]
                total_iterations = first_gen.progress()['total']
            self.data_bridge.start_backtest(initial_capital, total_iterations)
            console.print(f"[dim cyan]🌐 Real-time UI updates enabled (Capital: ₹{initial_capital:,.0f}, Iterations: {total_iterations})[/dim cyan]")
        else:
            console.print("[dim yellow]⚠️  Real-time UI updates disabled (data_bridge not available)[/dim yellow]")
        
        time.sleep(2)
        
        iteration = 0
        last_results = []  # Store final results
        backtest_complete = False
        user_interrupted = False
        
        try:
            while True:
                iteration += 1
                
                # Run analysis (will get progressive data slices)
                try:
                    results = self.run_once()
                    last_results = results  # Store for final display
                except StopIteration:
                    # All symbols completed
                    backtest_complete = True
                    console.print("\n[green]✅ All symbols completed![/green]\n")
                    break
                
                # Update backtest manager refresh count
                self.backtest_manager.refresh_count = self.refresh_count
                
                # Build and print display content for this iteration
                display_content = self.backtest_manager.build_backtest_display(results, iteration)
                
                # Print the display content (new table each iteration)
                console.print(display_content)
                console.print()  # Add spacing between iterations
                
                # Update backtest state in data_bridge for real-time UI
                if self.data_bridge:
                    summary = self.engine.get_summary()
                    closed_orders = self.engine.get_closed_orders()
                    
                    # Prepare symbols LTP data from results
                    symbols_ltp = {}
                    for r in results:
                        symbol = r.get('symbol', '')
                        if symbol and 'dataframe' in r and not r['dataframe'].empty:
                            df = r['dataframe']
                            last_row = df.iloc[-1]
                            open_price = float(last_row.get('open', 0))
                            close_price = float(last_row.get('close', 0))
                            symbols_ltp[symbol] = {
                                'ltp': close_price,
                                'close': close_price,
                                'open': open_price,
                                'high': float(last_row.get('high', 0)),
                                'low': float(last_row.get('low', 0)),
                                'volume': int(last_row.get('volume', 0)) if 'volume' in last_row else 0,
                                'change': close_price - open_price,
                                'change_pct': ((close_price - open_price) / open_price * 100) if open_price > 0 else 0,
                                'signal': r.get('final_signal', '-'),
                                'position': self.backtest_manager.get_symbol_position(symbol)
                            }
                    
                    # Prepare ALL trades data (not just last one)
                    all_trades_data = []
                    if not closed_orders.empty:
                        import pandas as pd
                        for idx, row in closed_orders.iterrows():
                            trade_type = row['type']
                            entry_price = float(row['entry_price'])
                            exit_price = float(row['exit_price'])
                            
                            if trade_type == 'LONG':
                                return_pct = ((exit_price - entry_price) / entry_price) * 100
                            else:
                                return_pct = ((entry_price - exit_price) / entry_price) * 100
                            
                            # Calculate duration
                            entry_time = row.get('entry_time')
                            exit_time = row.get('exit_time')
                            duration_str = "N/A"
                            if pd.notna(entry_time) and pd.notna(exit_time):
                                try:
                                    total_secs = int((exit_time - entry_time).total_seconds())
                                    h, remainder = divmod(abs(total_secs), 3600)
                                    m, s = divmod(remainder, 60)
                                    duration_str = f"{h:02d}:{m:02d}:{s:02d}"
                                except:
                                    pass
                            
                            trade_data = {
                                'order_id': int(row['order_id']),
                                'symbol': str(row['symbol']),
                                'type': str(trade_type),
                                'entry_price': float(entry_price),
                                'exit_price': float(exit_price),
                                'quantity': int(row['quantity']),
                                'pnl': float(row['pnl']),
                                'return_pct': float(return_pct),
                                'mode': 'PAPER' if row.get('paper_trade', False) else 'REAL',
                                'duration': duration_str,
                                'entry_reason': str(row.get('entry_reason', 'N/A')),
                                'exit_reason': str(row.get('exit_reason', 'N/A'))
                            }
                            all_trades_data.append(trade_data)
                    
                    # Get last trade for quick reference
                    last_trade_data = all_trades_data[-1] if all_trades_data else None
                    
                    # Update with all trades and symbols LTP
                    self.data_bridge.update_backtest(
                        iteration=iteration,
                        trade_data=last_trade_data,
                        summary=summary,
                        all_trades=all_trades_data,
                        symbols_ltp=symbols_ltp
                    )
                
                # Broadcast to web UI (if available)
                if self.ui_integration:
                    try:
                        self.ui_integration.after_run_once(results)
                    except Exception:
                        pass  # Silent fail for UI in backtest
                
                # Speed control
                if speed == 'realtime':
                    time.sleep(self.refresh_interval)
                elif speed == 'slow':
                    time.sleep(0.5)
                elif speed == 'medium':
                    time.sleep(0.1)
                # else 'fast': run as fast as possible
                
        except KeyboardInterrupt:
            user_interrupted = True
            console.print("\n[yellow]🛑 Backtest stopped by user[/yellow]\n")
        except Exception as e:
            console.print(f"\n[red]❌ Backtest error: {e}[/red]\n")
            if self.data_bridge:
                self.data_bridge.error_backtest(str(e))
        
        # Complete backtest in data_bridge
        if self.data_bridge and not user_interrupted:
            final_summary = self.engine.get_summary()
            self.data_bridge.complete_backtest(final_summary)
        
        # Show completion message
        console.print("\n" + "=" * 100)
        if not user_interrupted and not backtest_complete:
            console.print("\n[green]✅ Backtest Complete![/green]\n")
        
        # Show final state if we have results
        if last_results:
            console.print("[bold]📊 Final Backtest State:[/bold]\n")
            self.display_results(last_results)
        
        # Show comprehensive summary with full metrics matrix
        self.backtest_manager.refresh_count = self.refresh_count  # Update refresh count
        self.backtest_manager.show_backtest_summary()


def main():
    """Main function to run the live bot."""
    bot = LiveTradingBot()
    bot.run()


if __name__ == "__main__":
    main()
