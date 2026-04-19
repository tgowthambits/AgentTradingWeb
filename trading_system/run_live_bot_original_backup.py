"""
Live Trading Bot

Runs the trading system continuously, checking every 5 seconds
for real-time trading decisions.
"""

import sys
import os
import yaml
import pandas as pd
import time
import json
from datetime import datetime
from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich import box
from pathlib import Path
import numpy as np

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading_system.core.trading_engine import TradingEngine
from trading_system.data.data_loader import DataLoader
from trading_system.core.indicator_loader import IndicatorLoader

# No indicator imports needed! They're loaded dynamically from config


console = Console()


class NumpyJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles numpy types (NumPy 2.0 compatible)."""
    def default(self, obj):
        # Handle integers - np.integer is the abstract base class that covers all integer types
        if isinstance(obj, np.integer):
            return int(obj)
        # Handle floating point - np.floating is the abstract base class that covers all float types
        elif isinstance(obj, np.floating):
            return float(obj)
        # Handle booleans - check for np.bool_ (NumPy 2.0 compatible)
        elif isinstance(obj, (bool, np.bool_)) or (hasattr(np, 'bool_') and isinstance(obj, np.bool_)):
            return bool(obj)
        # Handle arrays
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


class LiveTradingBot:
    """
    Real-time trading bot that monitors symbols and executes trades.
    """
    
    def __init__(self, 
                 config_path="trading_system/config/trading_config.yaml",
                 indicators_config_path="trading_system/config/indicators_config.yaml"):
        """Initialize the live trading bot."""
        self.config = self.load_config(config_path)
        
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
        
        # Check if backtest mode is enabled
        self.backtest_mode = self.config.get('backtest', {}).get('enabled', False)
        backtest_config = self.config.get('backtest', {})
        
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
        self.auto_trade = self.config['trading'].get('enable_auto_trading', False)
        self.default_quantity = self.config['trading'].get('default_quantity', 1)
        
        # Trade direction control
        self.allow_buy = self.config['trading'].get('allow_buy', True)
        self.allow_sell = self.config['trading'].get('allow_sell', True)
        
        # Stats
        self.refresh_count = 0
        self.total_signals_generated = 0
        
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
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    # Removed: initialize_indicators() - now using dynamic IndicatorLoader!
    
    def run_once(self, symbols=None, increment_count=True):
        """Run one analysis cycle for specified symbols (or all if None)."""
        if increment_count:
            self.refresh_count += 1
        results = []
        stop_count = 0  # Track completed symbols
        
        # Use provided symbols or all symbols from config
        symbols_to_process = symbols if symbols is not None else self.config['symbols']
        
        for symbol in symbols_to_process:
            try:
                # Load latest data
                df = self.data_loader.load_symbol_data(
                    symbol,
                    self.config['date_range']['start_date'],
                    self.config['date_range']['end_date'],
                    self.config['resolution']
                )
                
                # Check if data is valid
                if df is None or df.empty:
                    console.print(f"[yellow]⚠️  No data returned for {symbol}, skipping...[/yellow]")
                    continue
                
                # Prepare data
                df = self.data_loader.prepare_for_indicators(df)
                
                # Analyze symbol
                result = self.engine.analyze_symbol(df, symbol, verbose=False)
                
                # Add dataframe for UI charting (doesn't affect core logic)
                result['dataframe'] = df
                
                results.append(result)
                
                # Execute trading decision if auto-trading enabled
                if self.auto_trade and result['final_signal'] != 'HOLD':
                    signal = result['final_signal']
                    
                    # Check if this trade direction is allowed
                    can_execute = False
                    if signal == 'BUY' and self.allow_buy:
                        can_execute = True
                    elif signal == 'SELL' and self.allow_sell:
                        can_execute = True
                    
                    if can_execute:
                        self.engine.execute_trading_decision(result, quantity=self.default_quantity, df=df)
                        self.total_signals_generated += 1
                    else:
                        # Log skipped signal
                        direction = "BUY (LONG)" if signal == 'BUY' else "SELL (SHORT)"
                        console.print(f"[yellow]⏭️  Skipped {direction} signal for {symbol} (disabled in config)[/yellow]")
            
            except StopIteration as e:
                # Symbol backtest completed - track it
                stop_count += 1
                if self.backtest_mode:
                    # Silent in backtest mode - we'll check the count
                    pass
                else:
                    console.print(f"[yellow]⚠️  {str(e)}[/yellow]")
                
            except Exception as e:
                console.print(f"[red]❌ Error analyzing {symbol}: {str(e)}[/red]")
                import traceback
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
        
        # If all symbols completed in backtest mode, raise StopIteration
        if self.backtest_mode and stop_count >= len(symbols_to_process):
            raise StopIteration("All symbols completed backtest")
        
        return results
    
    def display_results(self, results):
        """Display results with proper Rich rendering."""
        # Build trade direction info
        trade_directions = []
        if self.allow_buy:
            trade_directions.append("[green]BUY✓[/green]")
        else:
            trade_directions.append("[dim]BUY✗[/dim]")
        
        if self.allow_sell:
            trade_directions.append("[red]SELL✓[/red]")
        else:
            trade_directions.append("[dim]SELL✗[/dim]")
        
        directions_str = " ".join(trade_directions)
        
        # Header
        header = Panel(
            f"[bold cyan]🤖 Live Trading Bot[/bold cyan] | "
            f"Refresh #{self.refresh_count} | "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
            f"Auto-Trade: {'ON' if self.auto_trade else 'OFF'} | "
            f"{directions_str}",
            style="bold green"
        )
        console.print(header)
        console.print()
        
        # Single comprehensive table with all details
        comprehensive_table = self.create_comprehensive_table(results)
        console.print(comprehensive_table)
        console.print()
        
        # Closed orders table
        closed_orders = self.engine.get_closed_orders()
        if not closed_orders.empty:
            orders_table = self.create_completed_orders_table(closed_orders)
            console.print(orders_table)
            console.print()
        
        # Performance KPIs
        kpi_panel = self.create_kpi_panel(results, closed_orders)
        console.print(kpi_panel)
        console.print()
        
        # Add legend
        console.print(
            "[dim]Legend: B=BUY, S=SELL, H=HOLD | "
            "* = Unrealized PnL (open position) | "
            "RSI/MA/MACD/BB = Individual indicator signals[/dim]"
        )
    
    def create_comprehensive_table(self, results):
        """Create single comprehensive table with all trading information."""
        table = Table(
            title="[bold]📊 Complete Trading Analysis & Positions[/bold]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )
        
        # Get list of active indicators dynamically
        active_indicators = []
        if results and len(results) > 0:
            ind_signals = results[0].get('indicator_signals', {})
            active_indicators = sorted(list(ind_signals.keys()))
        
        # Add fixed columns
        table.add_column("Symbol", style="cyan", width=12)
        table.add_column("LTP\n(₹)", style="white", width=8)
        table.add_column("Final\nSignal", style="bold", width=7)
        
        # Add dynamic indicator columns with icons
        for indicator_name in active_indicators:
            display_name = self._abbreviate_indicator_name(indicator_name)
            table.add_column(display_name, style="white", width=6, justify="center")
        
        # Add aggregation and position columns
        table.add_column("Agree\n%", style="white", width=6)
        table.add_column("Position", style="white", width=8)
        table.add_column("Entry\n(₹)", style="white", width=8)
        table.add_column("Qty", style="white", width=4)
        table.add_column("Unrealized\nPnL (₹)", style="white", width=12)
        
        total_unrealized_pnl = 0
        
        for result in results:
            symbol_short = result['symbol'].split(':')[-1]
            
            # Color-code final signal
            signal = result['final_signal']
            if signal == 'BUY':
                signal_text = f"[green bold]{signal}[/green bold]"
            elif signal == 'SELL':
                signal_text = f"[red bold]{signal}[/red bold]"
            else:
                signal_text = f"[yellow]{signal}[/yellow]"
            
            # Get individual indicator signals dynamically with icons
            ind_signals = result.get('indicator_signals', {})
            indicator_signals = []
            for indicator_name in active_indicators:
                sig = ind_signals.get(indicator_name, 'HOLD')
                indicator_signals.append(self._format_signal_with_icon(sig))
            
            # Check current position
            position = self.engine.current_positions.get(result['symbol'])
            if position:
                pos_type = position['type']
                pos_str = f"[green]{pos_type}[/green]" if pos_type == 'LONG' else f"[red]{pos_type}[/red]"
                entry_price = f"{position['entry_price']:.2f}"
                qty_str = str(position['quantity'])
                
                # Calculate unrealized PnL
                current_price = result['latest_price']
                if pos_type == 'LONG':
                    unrealized_pnl = (current_price - position['entry_price']) * position['quantity']
                else:  # SHORT
                    unrealized_pnl = (position['entry_price'] - current_price) * position['quantity']
                
                total_unrealized_pnl += unrealized_pnl
                
                pnl_color = "green" if unrealized_pnl > 0 else "red" if unrealized_pnl < 0 else "white"
                pnl_str = f"[{pnl_color}]{unrealized_pnl:+.2f}*[/{pnl_color}]"
            else:
                pos_str = "[dim]-[/dim]"
                entry_price = "[dim]-[/dim]"
                qty_str = "[dim]-[/dim]"
                pnl_str = "[dim]-[/dim]"
            
            # Build row dynamically
            row = [
                symbol_short,
                f"{result['latest_price']:.2f}",
                signal_text,
            ]
            row.extend(indicator_signals)  # Add all indicator signals with icons
            row.extend([
                f"{result['agreement_score']:.0%}",
                pos_str,
                entry_price,
                qty_str,
                pnl_str
            ])
            
            table.add_row(*row)
        
        # Add total row if there are open positions
        if total_unrealized_pnl != 0:
            total_color = "green" if total_unrealized_pnl > 0 else "red"
            # Calculate number of empty columns dynamically
            num_empty_cols = 2 + len(active_indicators) + 4  # LTP, Signal + indicators + Agree%, Pos, Entry, Qty
            empty_cols = [""] * num_empty_cols
            
            table.add_row(
                "[bold]TOTAL UNREALIZED[/bold]",
                *empty_cols,
                f"[bold {total_color}]{total_unrealized_pnl:+.2f}*[/bold {total_color}]"
            )
        
        return table
    
    def _abbreviate_indicator_name(self, name):
        """Abbreviate indicator names for compact display."""
        abbreviations = {
            'RSI': 'RSI',
            'MA_Crossover': 'MA',
            'MACD': 'MACD',
            'Bollinger_Bands': 'BB',
            'MysticPulse': 'MP',
            'Mystic_Pulse': 'MP',
            'Stochastic': 'STOCH',
            'EMA': 'EMA',
            'SMA': 'SMA',
        }
        
        # Return abbreviation if exists
        if name in abbreviations:
            return abbreviations[name]
        
        # For unknown indicators, create abbreviation from capital letters or first chars
        capitals = ''.join([c for c in name if c.isupper()])
        if len(capitals) >= 2:
            return capitals[:5]
        
        # Fallback: first 5 chars uppercase
        return name[:5].upper()
    
    def _format_signal_with_icon(self, signal):
        """Format signal with visual icon."""
        if signal == 'BUY':
            return "[green bold]✓[/green bold]"  # Checkmark for BUY
        elif signal == 'SELL':
            return "[red bold]✗[/red bold]"  # X for SELL
        else:
            return "[dim]○[/dim]"  # Circle for HOLD

    def _abbrev_signal(self, signal):
        """Abbreviate signal for compact display."""
        if signal == 'BUY':
            return "[green]B[/green]"
        elif signal == 'SELL':
            return "[red]S[/red]"
        else:
            return "[dim]H[/dim]"
    
    def create_main_table_old(self, results):
        """Create main analysis table."""
        table = Table(
            title="[bold]📊 Real-Time Analysis[/bold]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )
        
        table.add_column("Symbol", style="cyan", width=20)
        table.add_column("LTP (₹)", style="white", width=10)
        table.add_column("Signal", style="white", width=10)
        table.add_column("Agree", style="white", width=8)
        table.add_column("B", style="green", width=3)
        table.add_column("S", style="red", width=3)
        table.add_column("H", style="yellow", width=3)
        table.add_column("Position", style="white", width=10)
        
        for result in results:
            symbol_short = result['symbol'].split(':')[-1]
            
            # Color-code signal
            signal = result['final_signal']
            if signal == 'BUY':
                signal_text = f"[green bold]{signal}[/green bold]"
            elif signal == 'SELL':
                signal_text = f"[red bold]{signal}[/red bold]"
            else:
                signal_text = f"[yellow]{signal}[/yellow]"
            
            # Check current position
            position = self.engine.current_positions.get(result['symbol'])
            if position:
                pos_str = f"[green]{position['type']}[/green]"
            else:
                pos_str = "[dim]-[/dim]"
            
            breakdown = result['signal_breakdown']
            
            table.add_row(
                symbol_short,
                f"{result['latest_price']:.2f}",
                signal_text,
                f"{result['agreement_score']:.0%}",
                str(breakdown.get('BUY', 0)),
                str(breakdown.get('SELL', 0)),
                str(breakdown.get('HOLD', 0)),
                pos_str
            )
        
        return table
    
    def create_indicator_table(self, result):
        """Create indicator details table for a symbol."""
        table = Table(
            title=f"Indicators: {result['symbol'].split(':')[-1]}",
            box=box.SIMPLE,
            show_header=True
        )
        
        table.add_column("Indicator", style="cyan", width=25)
        table.add_column("Signal", style="white", width=10)
        
        for indicator, signal in result['indicator_signals'].items():
            if signal == 'BUY':
                signal_text = f"[green]{signal}[/green]"
            elif signal == 'SELL':
                signal_text = f"[red]{signal}[/red]"
            else:
                signal_text = f"[yellow]{signal}[/yellow]"
            
            table.add_row(indicator, signal_text)
        
        return table
    
    def create_positions_table(self, positions_df):
        """Create open positions table."""
        table = Table(
            title="[bold yellow]📊 Open Positions[/bold yellow]",
            box=box.ROUNDED,
            show_header=True
        )
        
        table.add_column("ID", style="dim", width=5)
        table.add_column("Symbol", style="cyan", width=20)
        table.add_column("Type", style="white", width=8)
        table.add_column("Entry (₹)", style="white", width=10)
        table.add_column("Entry Time", style="dim", width=19)
        table.add_column("Qty", style="white", width=5)
        
        for _, row in positions_df.iterrows():
            symbol_short = row['symbol'].split(':')[-1]
            type_color = "green" if row['type'] == 'LONG' else "red"
            
            table.add_row(
                str(row['order_id']),
                symbol_short,
                f"[{type_color}]{row['type']}[/{type_color}]",
                f"{row['entry_price']:.2f}",
                row['entry_time'].strftime("%Y-%m-%d %H:%M:%S"),
                str(row['quantity'])
            )
        
        return table
    
    def create_completed_orders_table(self, orders_df):
        """Create completed orders table with full details."""
        table = Table(
            title="[bold green]✅ Completed Trades[/bold green]",
            box=box.ROUNDED,
            show_header=True
        )
        
        table.add_column("ID", style="dim", width=4)
        table.add_column("Symbol", style="cyan", width=18)
        table.add_column("Type", style="white", width=6)
        table.add_column("Entry\n(₹)", style="white", width=8)
        table.add_column("Exit\n(₹)", style="white", width=8)
        table.add_column("Qty", style="white", width=4)
        table.add_column("Mode", style="white", width=6)
        table.add_column("Entry Time", style="dim", width=16)
        table.add_column("Exit Time", style="dim", width=16)
        table.add_column("Duration", style="white", width=10)
        table.add_column("PnL (₹)", style="white", width=10)
        table.add_column("Return\n%", style="white", width=8)
        table.add_column("Entry Reason", style="dim", width=20)
        table.add_column("Exit Reason", style="dim", width=20)
        
        total_pnl = 0
        
        for _, row in orders_df.iterrows():
            symbol_short = row['symbol'].split(':')[-1]
            type_color = "green" if row['type'] == 'LONG' else "red"
            pnl_color = "green" if row['pnl'] > 0 else "red" if row['pnl'] < 0 else "white"
            
            # Calculate duration
            duration = row['exit_time'] - row['entry_time']
            duration_str = str(duration).split('.')[0]  # Remove microseconds
            
            # Calculate return percentage (handle division by zero)
            entry_price = row.get('entry_price', 0)
            quantity = row.get('quantity', 0)
            cost_basis = entry_price * quantity
            
            if cost_basis > 0:
                return_pct = (row['pnl'] / cost_basis) * 100
            else:
                # Handle zero quantity or zero entry price
                return_pct = 0.0
            
            return_color = "green" if return_pct > 0 else "red" if return_pct < 0 else "white"
            
            # Get entry and exit reasons
            entry_reason = row.get('entry_reason', 'N/A')
            if pd.isna(entry_reason):
                entry_reason = 'N/A'
            entry_reason_short = entry_reason[:18] if len(entry_reason) > 18 else entry_reason
            
            exit_reason = row.get('exit_reason', 'N/A')
            if pd.isna(exit_reason):
                exit_reason = 'N/A'
            exit_reason_short = exit_reason[:18] if len(exit_reason) > 18 else exit_reason
            
            # Get paper trade mode
            is_paper = row.get('paper_trade', False)
            mode_str = "[yellow]PAPER[/yellow]" if is_paper else "[white]REAL[/white]"
            
            total_pnl += row['pnl']
            
            table.add_row(
                str(row['order_id']),
                symbol_short,
                f"[{type_color}]{row['type']}[/{type_color}]",
                f"{row['entry_price']:.2f}",
                f"{row['exit_price']:.2f}",
                str(row['quantity']),
                mode_str,
                row['entry_time'].strftime("%m-%d %H:%M:%S"),
                row['exit_time'].strftime("%m-%d %H:%M:%S"),
                duration_str,
                f"[{pnl_color}]{row['pnl']:+.2f}[/{pnl_color}]",
                f"[{return_color}]{return_pct:+.2f}%[/{return_color}]",
                entry_reason_short,
                exit_reason_short
            )
        
        # Add total row
        if len(orders_df) > 0:
            total_color = "green" if total_pnl > 0 else "red"
            table.add_row(
                "",
                "[bold]TOTAL REALIZED[/bold]",
                "", "", "", "", "", "", "", "",
                f"[bold {total_color}]{total_pnl:+.2f}[/bold {total_color}]",
                "", "", ""
            )
        
        return table
    
    def create_kpi_panel(self, results, closed_orders_df):
        """Create comprehensive KPI panel with performance metrics."""
        summary = self.engine.get_summary()
        
        # Calculate performance metrics
        total_trades = len(closed_orders_df) if not closed_orders_df.empty else 0
        winning_trades = len(closed_orders_df[closed_orders_df['pnl'] > 0]) if total_trades > 0 else 0
        losing_trades = len(closed_orders_df[closed_orders_df['pnl'] < 0]) if total_trades > 0 else 0
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        total_realized_pnl = closed_orders_df['pnl'].sum() if total_trades > 0 else 0
        avg_pnl_per_trade = total_realized_pnl / total_trades if total_trades > 0 else 0
        
        # Calculate unrealized PnL
        total_unrealized_pnl = 0
        for symbol, position in self.engine.current_positions.items():
            # Find current price from results
            current_price = 0
            for result in results:
                if result['symbol'] == symbol:
                    current_price = result['latest_price']
                    break
            
            if current_price > 0:
                if position['type'] == 'LONG':
                    unrealized_pnl = (current_price - position['entry_price']) * position['quantity']
                else:
                    unrealized_pnl = (position['entry_price'] - current_price) * position['quantity']
                total_unrealized_pnl += unrealized_pnl
        
        # Total PnL
        total_pnl = total_realized_pnl + total_unrealized_pnl
        pnl_color = "green" if total_pnl > 0 else "red" if total_pnl < 0 else "white"
        
        # Indicator performance
        indicator_agreement = sum(r['agreement_score'] for r in results) / len(results) if results else 0
        
        # Signal distribution
        buy_signals = sum(1 for r in results if r['final_signal'] == 'BUY')
        sell_signals = sum(1 for r in results if r['final_signal'] == 'SELL')
        hold_signals = sum(1 for r in results if r['final_signal'] == 'HOLD')
        
        # Best/Worst trade
        best_trade = closed_orders_df['pnl'].max() if total_trades > 0 else 0
        worst_trade = closed_orders_df['pnl'].min() if total_trades > 0 else 0
        
        # Create content
        content = (
            f"[bold cyan]Trading Performance:[/bold cyan]\n"
            f"  Total PnL: [{pnl_color}]₹{total_pnl:+.2f}[/{pnl_color}] "
            f"(Realized: ₹{total_realized_pnl:+.2f} + Unrealized: ₹{total_unrealized_pnl:+.2f}*)\n"
            f"  Total Trades: {total_trades} (Win: {winning_trades} | Loss: {losing_trades})\n"
            f"  Win Rate: [{'green' if win_rate >= 50 else 'red'}]{win_rate:.1f}%[/{'green' if win_rate >= 50 else 'red'}]\n"
            f"  Avg PnL/Trade: ₹{avg_pnl_per_trade:+.2f}\n"
            f"  Best Trade: [green]₹{best_trade:+.2f}[/green] | Worst Trade: [red]₹{worst_trade:+.2f}[/red]\n"
            f"\n"
            f"[bold cyan]Current Status:[/bold cyan]\n"
            f"  Open Positions: {summary['open_positions']}\n"
            f"  Signals Generated Today: {self.total_signals_generated}\n"
            f"  Bot Uptime: {self.refresh_count} refreshes ({self.refresh_count * self.refresh_interval}s)\n"
            f"\n"
            f"[bold cyan]Signal Distribution:[/bold cyan]\n"
            f"  BUY: [green]{buy_signals}[/green] | SELL: [red]{sell_signals}[/red] | HOLD: [yellow]{hold_signals}[/yellow]\n"
            f"\n"
            f"[bold cyan]Indicator Performance:[/bold cyan]\n"
            f"  Average Agreement: {indicator_agreement:.1%}\n"
            f"  Active Indicators: {summary['indicators_registered']}\n"
            f"  Strategy: {self.config['aggregation_strategy'].title()}"
        )
        
        return Panel(content, title="[bold]📊 Performance KPIs & Metrics[/bold]", style="cyan", border_style="cyan")
    
    def run(self):
        """Run the bot in either live or backtest mode."""
        if self.backtest_mode:
            return self.run_backtest()
        else:
            return self.run_live()
    
    def run_live(self):
        """Run the live trading bot."""
        console.print("\n[bold cyan]🤖 Starting Live Trading Bot...[/bold cyan]\n")
        console.print(f"Symbols: {', '.join(self.config['symbols'])}")
        console.print(f"Refresh Interval: {self.refresh_interval}s")
        console.print(f"Auto-Trading: {'ENABLED' if self.auto_trade else 'DISABLED'}")
        
        # Show trade direction settings
        buy_status = "[green]ENABLED[/green]" if self.allow_buy else "[dim]DISABLED[/dim]"
        sell_status = "[red]ENABLED[/red]" if self.allow_sell else "[dim]DISABLED[/dim]"
        console.print(f"Trade Directions: BUY {buy_status} | SELL {sell_status}")
        
        console.print(f"Indicators: {len(self.engine.indicator_manager)} active")
        console.print("\n[dim]Press Ctrl+C to stop[/dim]\n")
        
        time.sleep(2)
        
        try:
            while True:
                # Run analysis
                results = self.run_once()
                
                # Broadcast to web UI (if available)
                if self.ui_integration:
                    try:
                        self.ui_integration.after_run_once(results)
                    except Exception:
                        pass  # Silent fail - UI errors shouldn't affect bot operation
                
                # Clear screen and display results
                console.clear()
                self.display_results(results)
                
                # Show countdown
                console.print(f"\n[dim]⏱  Next refresh in: {self.refresh_interval}s  |  Press Ctrl+C to stop[/dim]")
                
                # Wait for next refresh
                time.sleep(self.refresh_interval)
                
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
                
                # Build and print display content for this iteration
                display_content = self._build_backtest_display(results, iteration)
                
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
                                'position': self._get_symbol_position(symbol)
                            }
                    
                    # Prepare ALL trades data (not just last one)
                    all_trades_data = []
                    if not closed_orders.empty:
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
                                    duration = exit_time - entry_time
                                    duration_str = str(duration).split('.')[0]
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
        
        # Show comprehensive summary
        console.print("\n")
        self.show_backtest_summary()
    
    def _get_symbol_position(self, symbol):
        """Get current position for a symbol during backtest."""
        try:
            open_orders = self.engine.get_open_orders()
            if not open_orders.empty:
                symbol_orders = open_orders[open_orders['symbol'] == symbol]
                if not symbol_orders.empty:
                    return str(symbol_orders.iloc[0]['type'])
        except:
            pass
        return '-'
    
    def _build_backtest_display(self, results, iteration):
        """Build the display content for live backtest updates."""
        # Calculate progress
        progress_info = ""
        if results and self.data_loader.generators:
            first_gen = list(self.data_loader.generators.values())[0]
            progress = first_gen.progress()
            progress_bar = "█" * int(progress['percent'] / 5) + "░" * (20 - int(progress['percent'] / 5))
            progress_info = f"[cyan]Progress: [{progress_bar}] {progress['percent']:.1f}% ({progress['current']}/{progress['total']} bars)[/cyan]"
        
        # Build trade direction info
        trade_directions = []
        if self.allow_buy:
            trade_directions.append("[green]BUY✓[/green]")
        else:
            trade_directions.append("[dim]BUY✗[/dim]")
        
        if self.allow_sell:
            trade_directions.append("[red]SELL✓[/red]")
        else:
            trade_directions.append("[dim]SELL✗[/dim]")
        
        directions_str = " ".join(trade_directions)
        
        # Header
        header = Panel(
            f"[bold cyan]🔄 BACKTEST MODE[/bold cyan] | "
            f"Iteration #{iteration} | "
            f"{datetime.now().strftime('%H:%M:%S')} | "
            f"{directions_str}",
            style="bold yellow"
        )
        
        # Single comprehensive table with all details
        comprehensive_table = self.create_comprehensive_table(results)
        
        # Closed orders table
        closed_orders = self.engine.get_closed_orders()
        orders_content = None
        if not closed_orders.empty:
            orders_content = self.create_completed_orders_table(closed_orders)
        
        # Performance KPIs
        kpi_panel = self.create_kpi_panel(results, closed_orders)
        
        # Progress panel
        progress_panel = Panel(progress_info, style="cyan", border_style="cyan")
        
        # Legend
        legend = Panel(
            "[dim]Legend: B=BUY, S=SELL, H=HOLD | * = Unrealized PnL (open position) | Press Ctrl+C to stop[/dim]",
            style="dim"
        )
        
        # Group all elements
        elements = [header, progress_panel, comprehensive_table, kpi_panel]
        if orders_content:
            elements.insert(3, orders_content)
        elements.append(legend)
        
        return Group(*elements)
    
    def show_backtest_summary(self):
        """Display comprehensive backtest results with trades list and metrics matrix."""
        backtest_config = self.config.get('backtest', {})
        initial_capital = backtest_config.get('initial_capital', 100000)
        
        summary = self.engine.get_summary()
        closed_orders = self.engine.get_closed_orders()
        
        console.print("\n" + "=" * 100)
        console.print("[bold cyan]📋 COMPLETED TRADES LIST[/bold cyan]")
        console.print("=" * 100)
        
        # Display detailed trades table
        if not closed_orders.empty:
            trades_table = Table(
                title="All Completed Trades",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold magenta"
            )
            
            trades_table.add_column("#", style="dim", width=4)
            trades_table.add_column("Symbol", style="cyan", width=18)
            trades_table.add_column("Type", width=6)
            trades_table.add_column("Entry\n₹", style="white", width=9)
            trades_table.add_column("Exit\n₹", style="white", width=9)
            trades_table.add_column("Qty", style="white", width=4)
            trades_table.add_column("PnL\n₹", width=11)
            trades_table.add_column("Return\n%", width=7)
            trades_table.add_column("Mode", width=6)
            trades_table.add_column("Duration", style="dim", width=11)
            trades_table.add_column("Entry Reason", style="dim", width=25)
            trades_table.add_column("Exit Reason", style="dim", width=25)
            
            # Add each trade
            for idx, row in closed_orders.iterrows():
                order_id = row['order_id']
                symbol = row['symbol'].split(':')[-1]  # Show short name
                trade_type = row['type']
                entry_price = row['entry_price']
                exit_price = row['exit_price']
                quantity = row['quantity']
                pnl = row['pnl']
                
                # Calculate return %
                if trade_type == 'LONG':
                    return_pct = ((exit_price - entry_price) / entry_price) * 100
                else:
                    return_pct = ((entry_price - exit_price) / entry_price) * 100
                
                # Calculate duration
                entry_time = row['entry_time']
                exit_time = row['exit_time']
                if pd.notna(entry_time) and pd.notna(exit_time):
                    duration = exit_time - entry_time
                    duration_str = str(duration).split('.')[0]  # Remove microseconds
                else:
                    duration_str = "N/A"
                
                # Get entry reason
                entry_reason = row.get('entry_reason', 'N/A')
                if pd.isna(entry_reason):
                    entry_reason = 'N/A'
                entry_reason_short = entry_reason[:24] if len(entry_reason) > 24 else entry_reason
                
                # Get exit reason
                exit_reason = row.get('exit_reason', 'N/A')
                if pd.isna(exit_reason):
                    exit_reason = 'N/A'
                exit_reason_short = exit_reason[:24] if len(exit_reason) > 24 else exit_reason
                
                # Check if paper trade
                is_paper = row.get('paper_trade', False)
                mode_str = "[yellow]PAPER[/yellow]" if is_paper else "[white]REAL[/white]"
                
                # Color code PnL and return
                if pnl > 0:
                    pnl_str = f"[green]+{pnl:.2f}[/green]"
                    return_str = f"[green]+{return_pct:.2f}[/green]"
                    type_str = f"[green]{trade_type}[/green]" if trade_type == 'LONG' else f"[red]{trade_type}[/red]"
                else:
                    pnl_str = f"[red]{pnl:.2f}[/red]"
                    return_str = f"[red]{return_pct:.2f}[/red]"
                    type_str = f"[green]{trade_type}[/green]" if trade_type == 'LONG' else f"[red]{trade_type}[/red]"
                
                trades_table.add_row(
                    str(order_id),
                    symbol,
                    type_str,
                    f"{entry_price:.2f}",
                    f"{exit_price:.2f}",
                    str(quantity),
                    pnl_str,
                    return_str,
                    mode_str,
                    duration_str,
                    entry_reason_short,
                    exit_reason_short
                )
            
            console.print(trades_table)
            console.print()
        else:
            console.print("[yellow]No completed trades found.[/yellow]\n")
        
        # Display Loss Recovery History if enabled
        if self.engine.loss_recovery_enabled:
            self._display_loss_recovery_history()
        
        # Calculate comprehensive metrics
        total_trades = summary['total_orders']
        total_pnl = summary['total_pnl']
        final_capital = initial_capital + total_pnl
        returns_pct = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0
        
        # Separate real and paper trades
        real_trades_df = closed_orders[~closed_orders.get('paper_trade', pd.Series([False]*len(closed_orders)))]
        paper_trades_df = closed_orders[closed_orders.get('paper_trade', pd.Series([False]*len(closed_orders)))]
        
        # Metrics for WITH Circuit Breaker (real trades only)
        if not real_trades_df.empty and 'pnl' in real_trades_df.columns:
            winning_trades = len(real_trades_df[real_trades_df['pnl'] > 0])
            losing_trades = len(real_trades_df[real_trades_df['pnl'] < 0])
            avg_win = real_trades_df[real_trades_df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
            avg_loss = real_trades_df[real_trades_df['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
            max_win = real_trades_df['pnl'].max()
            max_loss = real_trades_df['pnl'].min()
            
            # Calculate profit factor
            gross_profit = real_trades_df[real_trades_df['pnl'] > 0]['pnl'].sum()
            gross_loss = abs(real_trades_df[real_trades_df['pnl'] < 0]['pnl'].sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Calculate expectancy
            real_trades_count = len(real_trades_df)
            win_rate_calc = winning_trades / real_trades_count if real_trades_count > 0 else 0
            expectancy = (win_rate_calc * avg_win) - ((1 - win_rate_calc) * abs(avg_loss))
        else:
            winning_trades = 0
            losing_trades = 0
            avg_win = 0
            avg_loss = 0
            max_win = 0
            max_loss = 0
            profit_factor = 0
            expectancy = 0
            real_trades_count = 0
            win_rate_calc = 0
        
        win_rate = summary.get('win_rate', 0)
        
        # Metrics for WITHOUT Circuit Breaker (all trades - real + paper)
        all_trades_df = closed_orders  # All trades including paper
        if not all_trades_df.empty and 'pnl' in all_trades_df.columns:
            all_trades_count = len(all_trades_df)
            winning_trades_all = len(all_trades_df[all_trades_df['pnl'] > 0])
            losing_trades_all = len(all_trades_df[all_trades_df['pnl'] < 0])
            win_rate_all = winning_trades_all / all_trades_count if all_trades_count > 0 else 0
            
            # Calculate what total PnL would be without circuit breaker
            total_pnl_all = all_trades_df['pnl'].sum()
            returns_pct_all = (total_pnl_all / initial_capital * 100) if initial_capital > 0 else 0
        else:
            all_trades_count = 0
            winning_trades_all = 0
            losing_trades_all = 0
            win_rate_all = 0
            total_pnl_all = 0
            returns_pct_all = 0
        
        # Display metrics matrix
        console.print("\n" + "=" * 100)
        console.print("[bold cyan]📊 PERFORMANCE METRICS MATRIX[/bold cyan]")
        console.print("=" * 100 + "\n")
        
        # Create metrics table
        metrics_table = Table(
            box=box.DOUBLE_EDGE,
            show_header=True,
            header_style="bold cyan",
            border_style="cyan"
        )
        
        metrics_table.add_column("Category", style="bold yellow", width=25)
        metrics_table.add_column("Metric", style="white", width=30)
        metrics_table.add_column("Value", style="bold green", width=20)
        
        # Capital & Returns
        metrics_table.add_row(
            "[bold]💰 CAPITAL & RETURNS[/bold]",
            "Initial Capital",
            f"₹{initial_capital:,.2f}"
        )
        metrics_table.add_row(
            "",
            "Final Capital",
            f"[{'green' if final_capital >= initial_capital else 'red'}]₹{final_capital:,.2f}[/]"
        )
        metrics_table.add_row(
            "",
            "Total PnL",
            f"[{'green' if total_pnl >= 0 else 'red'}]₹{total_pnl:+,.2f}[/]"
        )
        metrics_table.add_row(
            "",
            "Return %",
            f"[{'green' if returns_pct >= 0 else 'red'}]{returns_pct:+.2f}%[/]"
        )
        
        # Trading Activity
        metrics_table.add_row(
            "[bold]📈 TRADING ACTIVITY[/bold]",
            "Total Trades",
            str(total_trades)
        )
        metrics_table.add_row(
            "",
            "Winning Trades",
            f"[green]{winning_trades}[/green]"
        )
        metrics_table.add_row(
            "",
            "Losing Trades",
            f"[red]{losing_trades}[/red]"
        )
        metrics_table.add_row(
            "",
            "Win Rate",
            f"[{'green' if win_rate >= 0.5 else 'yellow'}]{win_rate:.2%}[/]"
        )
        
        # Paper Trading Statistics & Circuit Breaker Impact
        paper_trades_count = summary.get('paper_trades', 0)
        circuit_breaker_savings = summary.get('circuit_breaker_savings', 0)
        hypothetical_capital = summary.get('hypothetical_capital', initial_capital)
        actual_capital_val = summary.get('actual_capital', initial_capital)
        
        if paper_trades_count > 0 or circuit_breaker_savings != 0:
            metrics_table.add_row(
                "[bold]🛡️  CIRCUIT BREAKER IMPACT[/bold]",
                "Capital WITHOUT Circuit Breaker",
                f"[red]₹{hypothetical_capital:,.2f}[/red]"
            )
            metrics_table.add_row(
                "",
                "Capital WITH Circuit Breaker",
                f"[green]₹{actual_capital_val:,.2f}[/green]"
            )
            metrics_table.add_row(
                "",
                "Capital Saved",
                f"[{'green' if circuit_breaker_savings > 0 else 'yellow'}]₹{circuit_breaker_savings:+,.2f}[/]"
            )
            
            # Show PnL comparison
            metrics_table.add_row(
                "",
                "Total PnL WITHOUT Circuit Breaker",
                f"[{'green' if total_pnl_all >= 0 else 'red'}]₹{total_pnl_all:+,.2f} ({returns_pct_all:+.2f}%)[/]"
            )
            metrics_table.add_row(
                "",
                "Total PnL WITH Circuit Breaker",
                f"[{'green' if total_pnl >= 0 else 'red'}]₹{total_pnl:+,.2f} ({returns_pct:+.2f}%)[/]"
            )
            
            metrics_table.add_row(
                "",
                "Paper Trades (Protected)",
                f"[yellow]{paper_trades_count}[/yellow]"
            )
            
            # Add comparison metrics
            metrics_table.add_row(
                "",
                "─" * 30,
                "─" * 20
            )
            metrics_table.add_row(
                "",
                "Total Trades WITHOUT Circuit Breaker",
                f"[red]{all_trades_count}[/red]"
            )
            metrics_table.add_row(
                "",
                "Total Trades WITH Circuit Breaker",
                f"[green]{real_trades_count}[/green]"
            )
            metrics_table.add_row(
                "",
                "Trades Avoided (Paper)",
                f"[yellow]{paper_trades_count}[/yellow]"
            )
            
            metrics_table.add_row(
                "",
                "─" * 30,
                "─" * 20
            )
            metrics_table.add_row(
                "",
                "Win Rate WITHOUT Circuit Breaker",
                f"[{'green' if win_rate_all >= 0.5 else 'red'}]{win_rate_all:.2%}[/] ({winning_trades_all}W/{losing_trades_all}L)"
            )
            metrics_table.add_row(
                "",
                "Win Rate WITH Circuit Breaker",
                f"[{'green' if win_rate_calc >= 0.5 else 'red'}]{win_rate_calc:.2%}[/] ({winning_trades}W/{losing_trades}L)"
            )
            
            # Show performance improvement
            win_rate_improvement = (win_rate_calc - win_rate_all) * 100
            if abs(win_rate_improvement) > 0.01:
                metrics_table.add_row(
                    "",
                    "Win Rate Improvement",
                    f"[{'green' if win_rate_improvement > 0 else 'red'}]{win_rate_improvement:+.2f}%[/]"
                )
            
            metrics_table.add_row(
                "",
                "─" * 30,
                "─" * 20
            )
            metrics_table.add_row(
                "",
                "Paper Mode Active",
                f"[{'red' if summary.get('paper_trading_mode', False) else 'green'}]{summary.get('paper_trading_mode', False)}[/]"
            )
        
        # Profit & Loss Analysis
        metrics_table.add_row(
            "[bold]💵 PROFIT & LOSS[/bold]",
            "Average Win",
            f"[green]₹{avg_win:+,.2f}[/green]"
        )
        metrics_table.add_row(
            "",
            "Average Loss",
            f"[red]₹{avg_loss:,.2f}[/red]"
        )
        metrics_table.add_row(
            "",
            "Largest Win",
            f"[green]₹{max_win:+,.2f}[/green]"
        )
        metrics_table.add_row(
            "",
            "Largest Loss",
            f"[red]₹{max_loss:,.2f}[/red]"
        )
        metrics_table.add_row(
            "",
            "Profit Factor",
            f"[{'green' if profit_factor >= 2.0 else 'yellow'}]{profit_factor:.2f}[/]"
        )
        metrics_table.add_row(
            "",
            "Expectancy per Trade",
            f"[{'green' if expectancy >= 0 else 'red'}]₹{expectancy:+,.2f}[/]"
        )
        
        # Risk Metrics
        if self.engine.advanced_features:
            risk_status = self.engine.risk_manager.get_risk_status()
            metrics_table.add_row(
                "[bold]⚠️  RISK MANAGEMENT[/bold]",
                "Risk Per Trade",
                f"{self.config.get('risk_management', {}).get('risk_per_trade_pct', 'N/A')}%"
            )
            metrics_table.add_row(
                "",
                "Risk Multiplier",
                f"{risk_status.get('risk_multiplier', 1.0):.2f}x"
            )
            metrics_table.add_row(
                "",
                "Daily PnL",
                f"[{'green' if risk_status.get('daily_pnl', 0) >= 0 else 'red'}]₹{risk_status.get('daily_pnl', 0):+,.2f}[/]"
            )
            metrics_table.add_row(
                "",
                "Daily Trades",
                f"{risk_status.get('daily_trades', 0)}"
            )
            metrics_table.add_row(
                "",
                "Trading Halted",
                f"[{'red' if risk_status.get('trading_halted', False) else 'green'}]{risk_status.get('trading_halted', False)}[/]"
            )
        
        # System Stats
        metrics_table.add_row(
            "[bold]🔧 SYSTEM STATS[/bold]",
            "Total Iterations",
            str(self.refresh_count)
        )
        metrics_table.add_row(
            "",
            "Symbols Traded",
            str(len(self.config['symbols']))
        )
        metrics_table.add_row(
            "",
            "Indicators Active",
            str(len(self.engine.indicator_manager))
        )
        
        console.print(metrics_table)
        console.print()
        
        # Summary message
        console.print("=" * 100)
        if returns_pct > 0:
            console.print(f"[bold green]✅ BACKTEST PROFITABLE: +{returns_pct:.2f}% return on ₹{initial_capital:,.2f}[/bold green]")
        elif returns_pct < 0:
            console.print(f"[bold red]❌ BACKTEST LOSS: {returns_pct:.2f}% loss on ₹{initial_capital:,.2f}[/bold red]")
        else:
            console.print(f"[bold yellow]⚖️  BACKTEST BREAKEVEN: 0.00% on ₹{initial_capital:,.2f}[/bold yellow]")
        
        # Show circuit breaker impact if applicable
        if circuit_breaker_savings > 0:
            console.print(f"[bold green]🛡️  CIRCUIT BREAKER SAVED: ₹{circuit_breaker_savings:+,.2f} ({paper_trades_count} paper trades protected)[/bold green]")
        elif circuit_breaker_savings < 0:
            console.print(f"[yellow]🛡️  Circuit Breaker Active: {paper_trades_count} paper trades[/yellow]")
        
        console.print("=" * 100 + "\n")
        
        # Save backtest results to JSON for UI
        self._save_backtest_results_to_json(
            summary, closed_orders, initial_capital, final_capital, total_pnl, returns_pct,
            real_trades_count, winning_trades, losing_trades, win_rate_calc,
            all_trades_count, winning_trades_all, losing_trades_all, win_rate_all,
            paper_trades_count, circuit_breaker_savings, hypothetical_capital, actual_capital_val,
            avg_win, avg_loss, max_win, max_loss, profit_factor, expectancy
        )


    def _save_backtest_results_to_json(self, summary, closed_orders, initial_capital, final_capital, 
                                        total_pnl, returns_pct, real_trades_count, winning_trades, 
                                        losing_trades, win_rate_calc, all_trades_count, winning_trades_all,
                                        losing_trades_all, win_rate_all, paper_trades_count, 
                                        circuit_breaker_savings, hypothetical_capital, actual_capital_val,
                                        avg_win, avg_loss, max_win, max_loss, profit_factor, expectancy):
        """Save backtest results to JSON file for UI consumption."""
        
        console.print("\n[cyan]💾 Saving backtest results for UI...[/cyan]")
        
        try:
            # Prepare summary data
            summary_data = {
                'initial_capital': float(initial_capital),
                'final_capital': float(final_capital),
                'total_pnl': float(total_pnl),
                'returns_pct': float(returns_pct)
            }
            
            # Prepare metrics data
            metrics_data = []
            
            # Capital & Returns
            metrics_data.append({'is_category': True, 'category': '💰 CAPITAL & RETURNS'})
            metrics_data.append({'category': '', 'metric': 'Initial Capital', 'value': f"₹{initial_capital:,.2f}"})
            metrics_data.append({'category': '', 'metric': 'Final Capital', 'value': f"₹{final_capital:,.2f}", 'is_positive': bool(final_capital >= initial_capital)})
            metrics_data.append({'category': '', 'metric': 'Total PnL', 'value': f"₹{total_pnl:+,.2f}", 'is_positive': bool(total_pnl >= 0)})
            metrics_data.append({'category': '', 'metric': 'Return %', 'value': f"{returns_pct:+.2f}%", 'is_positive': bool(returns_pct >= 0)})
            
            # Trading Activity
            metrics_data.append({'is_category': True, 'category': '📈 TRADING ACTIVITY'})
            metrics_data.append({'category': '', 'metric': 'Total Trades (Real)', 'value': str(real_trades_count)})
            metrics_data.append({'category': '', 'metric': 'Winning Trades', 'value': str(winning_trades), 'is_positive': True})
            metrics_data.append({'category': '', 'metric': 'Losing Trades', 'value': str(losing_trades), 'is_positive': False})
            metrics_data.append({'category': '', 'metric': 'Win Rate', 'value': f"{win_rate_calc:.2%}", 'is_positive': bool(win_rate_calc >= 0.5)})
            
            # Circuit Breaker Impact
            if paper_trades_count > 0:
                metrics_data.append({'is_category': True, 'category': '🛡️ CIRCUIT BREAKER IMPACT'})
                metrics_data.append({'category': '', 'metric': 'Capital WITHOUT Circuit Breaker', 'value': f"₹{hypothetical_capital:,.2f}", 'is_positive': False})
                metrics_data.append({'category': '', 'metric': 'Capital WITH Circuit Breaker', 'value': f"₹{actual_capital_val:,.2f}", 'is_positive': True})
                metrics_data.append({'category': '', 'metric': 'Capital Saved', 'value': f"₹{circuit_breaker_savings:+,.2f}", 'is_positive': bool(circuit_breaker_savings > 0)})
                metrics_data.append({'category': '', 'metric': 'Paper Trades (Protected)', 'value': str(paper_trades_count)})
                
                metrics_data.append({'is_divider': True})
                metrics_data.append({'category': '', 'metric': 'Total Trades WITHOUT Circuit Breaker', 'value': str(all_trades_count), 'is_positive': False})
                metrics_data.append({'category': '', 'metric': 'Total Trades WITH Circuit Breaker', 'value': str(real_trades_count), 'is_positive': True})
                metrics_data.append({'category': '', 'metric': 'Trades Avoided (Paper)', 'value': str(paper_trades_count)})
                
                metrics_data.append({'is_divider': True})
                metrics_data.append({'category': '', 'metric': 'Win Rate WITHOUT Circuit Breaker', 'value': f"{win_rate_all:.2%} ({winning_trades_all}W/{losing_trades_all}L)", 'is_positive': bool(win_rate_all >= 0.5)})
                metrics_data.append({'category': '', 'metric': 'Win Rate WITH Circuit Breaker', 'value': f"{win_rate_calc:.2%} ({winning_trades}W/{losing_trades}L)", 'is_positive': bool(win_rate_calc >= 0.5)})
                
                win_rate_improvement = win_rate_calc - win_rate_all
                if abs(win_rate_improvement) > 0.0001:
                    metrics_data.append({'category': '', 'metric': 'Win Rate Improvement', 'value': f"{win_rate_improvement:+.2%}", 'is_positive': bool(win_rate_improvement > 0)})
            
            # Profit & Loss Analysis
            metrics_data.append({'is_category': True, 'category': '💵 PROFIT & LOSS'})
            metrics_data.append({'category': '', 'metric': 'Average Win', 'value': f"₹{avg_win:+,.2f}", 'is_positive': True})
            metrics_data.append({'category': '', 'metric': 'Average Loss', 'value': f"₹{avg_loss:,.2f}", 'is_positive': False})
            metrics_data.append({'category': '', 'metric': 'Largest Win', 'value': f"₹{max_win:+,.2f}", 'is_positive': True})
            metrics_data.append({'category': '', 'metric': 'Largest Loss', 'value': f"₹{max_loss:,.2f}", 'is_positive': False})
            metrics_data.append({'category': '', 'metric': 'Profit Factor', 'value': f"{profit_factor:.2f}", 'is_positive': bool(profit_factor >= 2.0)})
            metrics_data.append({'category': '', 'metric': 'Expectancy per Trade', 'value': f"₹{expectancy:+,.2f}", 'is_positive': bool(expectancy >= 0)})
            
            # Prepare trades data
            trades_data = []
            if not closed_orders.empty:
                for idx, row in closed_orders.iterrows():
                    trade_type = row['type']
                    entry_price = float(row['entry_price'])
                    exit_price = float(row['exit_price'])
                    
                    if trade_type == 'LONG':
                        return_pct = ((exit_price - entry_price) / entry_price) * 100
                    else:
                        return_pct = ((entry_price - exit_price) / entry_price) * 100
                    
                    # Calculate duration
                    entry_time = row['entry_time']
                    exit_time = row['exit_time']
                    if pd.notna(entry_time) and pd.notna(exit_time):
                        duration = exit_time - entry_time
                        duration_str = str(duration).split('.')[0]
                    else:
                        duration_str = "N/A"
                    
                    is_paper = bool(row.get('paper_trade', False))
                    
                    trades_data.append({
                        'order_id': int(row['order_id']),
                        'symbol': str(row['symbol']),
                        'type': str(trade_type),
                        'entry_price': float(entry_price),
                        'exit_price': float(exit_price),
                        'quantity': int(row['quantity']),
                        'pnl': float(row['pnl']),
                        'return_pct': float(return_pct),
                        'mode': 'PAPER' if is_paper else 'REAL',
                        'duration': duration_str,
                        'entry_reason': str(row.get('entry_reason', 'N/A')),
                        'exit_reason': str(row.get('exit_reason', 'N/A'))
                    })
            
            # Prepare circuit breaker data
            circuit_breaker_data = None
            if paper_trades_count > 0:
                total_pnl_all = closed_orders['pnl'].sum() if not closed_orders.empty else 0
                returns_pct_all = (total_pnl_all / initial_capital * 100) if initial_capital > 0 else 0
                
                circuit_breaker_data = {
                    'enabled': bool(True),
                    'capital_without': float(hypothetical_capital),
                    'capital_with': float(actual_capital_val),
                    'capital_saved': float(circuit_breaker_savings),
                    'pnl_without': float(total_pnl_all),
                    'pnl_with': float(total_pnl),
                    'return_pct_without': float(returns_pct_all),
                    'return_pct_with': float(returns_pct),
                    'paper_trades_count': int(paper_trades_count),
                    'total_trades_without': int(all_trades_count),
                    'total_trades_with': int(real_trades_count),
                    'trades_avoided': int(paper_trades_count),
                    'win_rate_without': float(win_rate_all),
                    'win_rate_with': float(win_rate_calc),
                    'win_rate_improvement': float(win_rate_calc - win_rate_all),
                    'wins_without': int(winning_trades_all),
                    'losses_without': int(losing_trades_all),
                    'wins_with': int(winning_trades),
                    'losses_with': int(losing_trades)
                }
            
            # Prepare config data
            backtest_config = self.config.get('backtest', {})
            risk_config = self.config.get('risk_management', {})
            paper_mode_config = risk_config.get('paper_trading_mode', {})
            stop_loss_config = risk_config.get('stop_loss', {})
            
            # Handle symbols as strings or dicts
            symbols_list = self.config.get('symbols', [])
            if symbols_list and isinstance(symbols_list[0], dict):
                symbols_str = ', '.join([s['symbol'] for s in symbols_list])
            else:
                symbols_str = ', '.join(symbols_list)
            
            config_data = {
                'symbols': symbols_str,
                'initial_capital': int(backtest_config.get('initial_capital', 0)),
                'risk_per_trade': f"{risk_config.get('risk_per_trade_pct', 'N/A')}%",
                'stop_loss_method': stop_loss_config.get('method', 'N/A'),
                'max_loss_per_trade': int(stop_loss_config.get('max_loss_per_trade', 0)),
                'circuit_breaker_enabled': bool(paper_mode_config.get('enabled', False)),
                'circuit_breaker_trigger': int(paper_mode_config.get('consecutive_losses_trigger', 0)),
                'fixed_quantity': 25  # From backtest mode
            }
            
            # Prepare timeline data
            timeline_data = {
                'start_date': backtest_config.get('start_date', 'N/A'),
                'end_date': backtest_config.get('end_date', 'N/A'),
                'duration': 'N/A',
                'total_iterations': len(trades_data),
                'backtest_started': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'backtest_completed': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'execution_time': 'N/A'
            }
            
            # Add Loss Recovery History if enabled
            loss_recovery_data = None
            if self.engine.loss_recovery_enabled:
                recovery_history = self.engine.get_recovery_history()
                loss_history = self.engine.get_loss_history()
                loss_status = self.engine.get_loss_recovery_status()
                
                loss_recovery_data = {
                    'recovery_history': recovery_history,
                    'loss_history': loss_history,
                    'current_status': loss_status
                }
            
            # Combine all data
            results = {
                'summary': summary_data,
                'metrics': metrics_data,
                'trades': trades_data,
                'circuit_breaker': circuit_breaker_data,
                'config': config_data,
                'timeline': timeline_data,
                'generated_at': datetime.now().isoformat()
            }
            
            if loss_recovery_data:
                results['loss_recovery'] = loss_recovery_data
            
            # Save to file
            results_file = Path(__file__).parent / "backtest_results.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2, cls=NumpyJSONEncoder)
            
            console.print(f"[green]✅ Backtest results saved to: {results_file}[/green]")
            console.print(f"[cyan]🌐 View in UI: http://localhost:8000/backtest[/cyan]\n")
            
        except Exception as e:
            console.print(f"[red]❌ Error saving backtest results: {e}[/red]")
    
    def _display_loss_recovery_history(self):
        """Display loss recovery history and status."""
        from rich.table import Table
        from rich.console import Console
        from datetime import datetime
        
        console = Console()
        recovery_history = self.engine.get_recovery_history()
        loss_history = self.engine.get_loss_history()
        loss_status = self.engine.get_loss_recovery_status()
        
        # Display Loss History
        if loss_history:
            console.print("\n[bold cyan]📉 LOSS HISTORY[/bold cyan]")
            loss_table = Table(show_header=True, header_style="bold magenta")
            loss_table.add_column("Trade ID", style="dim", width=8)
            loss_table.add_column("Symbol", style="cyan", width=12)
            loss_table.add_column("Loss Amount", style="red", width=12)
            loss_table.add_column("Entry ₹", style="white", width=10)
            loss_table.add_column("Exit ₹", style="white", width=10)
            loss_table.add_column("Quantity", width=8)
            loss_table.add_column("Timestamp", style="dim", width=20)
            
            for loss in loss_history:
                timestamp_str = loss['timestamp']
                if isinstance(timestamp_str, str):
                    try:
                        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        timestamp_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                loss_table.add_row(
                    str(loss['trade_id']),
                    loss['symbol'],
                    f"₹{loss['loss_amount']:.2f}",
                    f"₹{loss['entry_price']:.2f}",
                    f"₹{loss['exit_price']:.2f}",
                    str(loss['quantity']),
                    timestamp_str
                )
            
            console.print(loss_table)
            console.print()
        
        # Display Recovery History
        if recovery_history:
            console.print("[bold green]✅ RECOVERY HISTORY[/bold green]")
            recovery_table = Table(show_header=True, header_style="bold green")
            recovery_table.add_column("Trade ID", style="dim", width=8)
            recovery_table.add_column("Symbol", style="cyan", width=12)
            recovery_table.add_column("Loss Amount", style="red", width=12)
            recovery_table.add_column("Recovered", style="green", width=12)
            recovery_table.add_column("Remaining", style="yellow", width=12)
            recovery_table.add_column("Status", width=10)
            recovery_table.add_column("Entry ₹", style="white", width=10)
            recovery_table.add_column("Exit ₹", style="white", width=10)
            recovery_table.add_column("Quantity", width=8)
            recovery_table.add_column("Timestamp", style="dim", width=20)
            
            for recovery in recovery_history:
                timestamp_str = recovery['timestamp']
                if isinstance(timestamp_str, str):
                    try:
                        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        timestamp_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                status = "[green]FULL[/green]" if recovery['full_recovery'] else "[yellow]PARTIAL[/yellow]"
                recovery_table.add_row(
                    str(recovery['trade_id']),
                    recovery['symbol'],
                    f"₹{recovery['loss_amount']:.2f}",
                    f"₹{recovery['recovered_amount']:.2f}",
                    f"₹{recovery['remaining_loss']:.2f}",
                    status,
                    f"₹{recovery['entry_price']:.2f}",
                    f"₹{recovery['exit_price']:.2f}",
                    str(recovery['quantity']),
                    timestamp_str
                )
            
            console.print(recovery_table)
            console.print()
        
        # Display Current Loss Recovery Status
        if loss_status['symbols_with_loss']:
            console.print("[bold yellow]⚠️  CURRENT LOSS RECOVERY STATUS[/bold yellow]")
            status_table = Table(show_header=True, header_style="bold yellow")
            status_table.add_column("Symbol", style="cyan", width=12)
            status_table.add_column("Unrecovered Loss", style="red", width=15)
            
            for symbol in loss_status['symbols_with_loss']:
                loss_amount = loss_status['symbol_losses'][symbol]
                status_table.add_row(
                    symbol,
                    f"₹{loss_amount:.2f}"
                )
            
            status_table.add_row(
                "[bold]TOTAL[/bold]",
                f"[bold]₹{loss_status['total_unrecovered_loss']:.2f}[/bold]"
            )
            
            console.print(status_table)
            console.print()
        elif recovery_history or loss_history:
            console.print("[bold green]✅ All losses have been recovered![/bold green]\n")


def main():
    """Main function to run the live bot."""
    bot = LiveTradingBot()
    bot.run()


if __name__ == "__main__":
    main()

