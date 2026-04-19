"""
Backtest manager for backtest-specific functionality.
"""

import pandas as pd
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich import box

from .utils import NumpyJSONEncoder


class BacktestManager:
    """Manages backtest-specific operations and display."""
    
    def __init__(self, engine, data_loader, config: Dict[str, Any], 
                 display_manager, allow_buy: bool, allow_sell: bool,
                 refresh_count: int, console: Optional[Console] = None):
        """
        Initialize backtest manager.
        
        Args:
            engine: TradingEngine instance
            data_loader: DataLoader instance
            config: Configuration dictionary
            display_manager: DisplayManager instance
            allow_buy: Whether BUY signals are allowed
            allow_sell: Whether SELL signals are allowed
            refresh_count: Current refresh count
            console: Optional Rich Console instance
        """
        self.engine = engine
        self.data_loader = data_loader
        self.config = config
        self.display_manager = display_manager
        self.allow_buy = allow_buy
        self.allow_sell = allow_sell
        self.refresh_count = refresh_count
        self.console = console or Console()
    
    def build_backtest_display(self, results: List[Dict], iteration: int) -> Group:
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
        comprehensive_table = self.display_manager.create_comprehensive_table(results)
        
        # Closed orders table
        closed_orders = self.engine.get_closed_orders()
        orders_content = None
        if not closed_orders.empty:
            orders_content = self.display_manager.create_completed_orders_table(closed_orders)
        
        # Performance KPIs
        kpi_panel = self.display_manager.create_kpi_panel(
            results, closed_orders, self.refresh_count, 0, 0
        )
        
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
    
    def get_symbol_position(self, symbol: str) -> str:
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
    
    def save_backtest_results_to_json(self, summary: Dict, closed_orders: pd.DataFrame,
                                     initial_capital: float, final_capital: float,
                                     total_pnl: float, returns_pct: float,
                                     real_trades_count: int, winning_trades: int,
                                     losing_trades: int, win_rate_calc: float,
                                     all_trades_count: int, winning_trades_all: int,
                                     losing_trades_all: int, win_rate_all: float,
                                     paper_trades_count: int, circuit_breaker_savings: float,
                                     hypothetical_capital: float, actual_capital_val: float,
                                     avg_win: float, avg_loss: float, max_win: float,
                                     max_loss: float, profit_factor: float, expectancy: float):
        """Save backtest results to JSON file for UI consumption."""
        
        self.console.print("\n[cyan]💾 Saving backtest results for UI...[/cyan]")
        
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
            # Get total charges and net profit from summary
            total_charges = summary.get('total_charges', 0.0)
            total_net_profit = summary.get('total_net_profit', total_pnl)  # Fallback to total_pnl if not available
            total_gross_pnl = summary.get('total_gross_pnl', total_pnl)  # Fallback to total_pnl if not available
            
            metrics_data.append({'category': '', 'metric': 'Total PnL', 'value': f"₹{total_pnl:+,.2f}", 'is_positive': bool(total_pnl >= 0)})
            metrics_data.append({'category': '', 'metric': 'Return %', 'value': f"{returns_pct:+.2f}%", 'is_positive': bool(returns_pct >= 0)})
            metrics_data.append({'category': '', 'metric': 'Total Charges', 'value': f"₹{total_charges:,.2f}", 'is_positive': None})
            metrics_data.append({'category': '', 'metric': 'Gross PnL', 'value': f"₹{total_gross_pnl:+,.2f}", 'is_positive': bool(total_gross_pnl >= 0)})
            metrics_data.append({'category': '', 'metric': 'Net Profit (After Charges)', 'value': f"₹{total_net_profit:+,.2f}", 'is_positive': bool(total_net_profit >= 0)})
            
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
                        total_secs = int((exit_time - entry_time).total_seconds())
                        h, remainder = divmod(abs(total_secs), 3600)
                        m, s = divmod(remainder, 60)
                        duration_str = f"{h:02d}:{m:02d}:{s:02d}"
                    else:
                        duration_str = "N/A"
                    
                    is_paper = bool(row.get('paper_trade', False))
                    
                    # Get charges and net profit (with fallbacks)
                    total_charges = float(row.get('total_charges', 0.0))
                    net_profit = float(row.get('net_profit', row['pnl']))  # Fallback to pnl if not available
                    
                    trades_data.append({
                        'order_id': int(row['order_id']),
                        'symbol': str(row['symbol']),
                        'type': str(trade_type),
                        'entry_price': float(entry_price),
                        'exit_price': float(exit_price),
                        'quantity': int(row['quantity']),
                        'pnl': float(row['pnl']),
                        'max_unrealized_profit': float(row.get('max_profit', 0.0) or 0.0),
                        'min_unrealized_profit': float(row.get('min_profit', 0.0) or 0.0),
                        'return_pct': float(return_pct),
                        'mode': 'PAPER' if is_paper else 'REAL',
                        'duration': duration_str,
                        'total_charges': total_charges,
                        'net_profit': net_profit,
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
            results_file = Path(__file__).parent.parent / "backtest_results.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2, cls=NumpyJSONEncoder)
            
            self.console.print(f"[green]✅ Backtest results saved to: {results_file}[/green]")
            self.console.print(f"[cyan]🌐 View in UI: http://localhost:8000/backtest[/cyan]\n")
            
        except Exception as e:
            self.console.print(f"[red]❌ Error saving backtest results: {e}[/red]")
    
    def show_backtest_summary(self):
        """Display comprehensive backtest results with trades list and metrics matrix."""
        backtest_config = self.config.get('backtest', {})
        initial_capital = backtest_config.get('initial_capital', 100000)
        
        summary = self.engine.get_summary()
        closed_orders = self.engine.get_closed_orders()
        
        self.console.print("\n" + "=" * 100)
        self.console.print("[bold cyan]📋 COMPLETED TRADES LIST[/bold cyan]")
        self.console.print("=" * 100)
        
        # Display detailed trades table
        if not closed_orders.empty:
            trades_table = Table(
                title="All Completed Trades",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold magenta"
            )
            
            # Check if candle prices should be shown
            output_config = self.config.get('output', {})
            candle_config = output_config.get('show_candle_prices', {})
            show_candle_prices = candle_config.get('enabled', True)
            show_entry_high = candle_config.get('show_entry_high', True) if show_candle_prices else False
            show_exit_low = candle_config.get('show_exit_low', True) if show_candle_prices else False
            
            trades_table.add_column("#", style="dim", width=4)
            trades_table.add_column("Symbol", style="cyan", width=18)
            trades_table.add_column("Type", style="white", width=6)
            trades_table.add_column("Entry\n₹", style="white", width=9)
            if show_entry_high:
                trades_table.add_column("Entry\nHigh\n₹", style="dim", width=10)
            trades_table.add_column("Exit\n₹", style="white", width=9)
            if show_exit_low:
                trades_table.add_column("Exit\nLow\n₹", style="dim", width=10)
            trades_table.add_column("Qty", style="white", width=4)
            trades_table.add_column("PnL\n₹", style="white", width=11)
            trades_table.add_column("Max U.PnL\n₹", style="green", width=11)
            trades_table.add_column("Min U.PnL\n₹", style="red", width=11)
            trades_table.add_column("Return\n%", style="white", width=7)
            trades_table.add_column("Total\nCharges\n₹", style="yellow", width=12)
            trades_table.add_column("Net\nProfit\n₹", style="white", width=11)
            trades_table.add_column("Mode", style="white", width=6)
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
                max_unrealized = float(row.get('max_profit', 0.0) or 0.0)
                min_unrealized = float(row.get('min_profit', 0.0) or 0.0)
                
                # Calculate return %
                if entry_price is not None and not pd.isna(entry_price) and entry_price != 0:
                    if trade_type == 'LONG':
                        return_pct = ((exit_price - entry_price) / entry_price) * 100
                    else:
                        return_pct = ((entry_price - exit_price) / entry_price) * 100
                else:
                    return_pct = 0.0
                
                # Calculate duration
                entry_time = row['entry_time']
                exit_time = row['exit_time']
                if pd.notna(entry_time) and pd.notna(exit_time):
                    total_secs = int((exit_time - entry_time).total_seconds())
                    h, remainder = divmod(abs(total_secs), 3600)
                    m, s = divmod(remainder, 60)
                    duration_str = f"{h:02d}:{m:02d}:{s:02d}"
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
                
                # Ensure return_pct and pnl are valid
                if pd.isna(return_pct) or return_pct is None:
                    return_pct = 0.0
                if pd.isna(pnl) or pnl is None:
                    pnl = 0.0
                
                # Get total charges and net profit (with fallbacks)
                total_charges = float(row.get('total_charges', 0.0))
                net_profit = float(row.get('net_profit', pnl))  # Fallback to pnl if not available
                if pd.isna(total_charges) or total_charges is None:
                    total_charges = 0.0
                if pd.isna(net_profit) or net_profit is None:
                    net_profit = pnl
                
                # Color code PnL and return
                if pnl > 0:
                    pnl_str = f"[green]+{pnl:.2f}[/green]"
                    return_str = f"[green]+{return_pct:.2f}[/green]"
                    type_str = f"[green]{trade_type}[/green]" if trade_type == 'LONG' else f"[red]{trade_type}[/red]"
                else:
                    pnl_str = f"[red]{pnl:.2f}[/red]"
                    return_str = f"[red]{return_pct:.2f}[/red]"
                    type_str = f"[green]{trade_type}[/green]" if trade_type == 'LONG' else f"[red]{trade_type}[/red]"
                
                # Color code net profit
                if net_profit > 0:
                    net_profit_str = f"[green]+{net_profit:.2f}[/green]"
                else:
                    net_profit_str = f"[red]{net_profit:.2f}[/red]"
                
                # Format total charges (always yellow/orange)
                charges_str = f"[yellow]{total_charges:.2f}[/yellow]"
                
                # Get entry candle high and exit candle low
                entry_candle_high = row.get('entry_candle_high', None)
                exit_candle_low = row.get('exit_candle_low', None)
                
                # Build row with indicator signals - ensure all values are strings
                row_data = [
                    str(order_id) if order_id is not None and not pd.isna(order_id) else "N/A",
                    str(symbol) if symbol is not None and not pd.isna(symbol) else "N/A",
                    type_str,
                    f"{entry_price:.2f}" if entry_price is not None and not pd.isna(entry_price) else "N/A",
                ]
                
                # Add entry candle high if enabled
                if show_entry_high:
                    if entry_candle_high is not None and not pd.isna(entry_candle_high):
                        row_data.append(f"[dim]{entry_candle_high:.2f}[/dim]")
                    else:
                        row_data.append("[dim]N/A[/dim]")
                
                row_data.append(f"{exit_price:.2f}" if exit_price is not None and not pd.isna(exit_price) else "N/A")
                
                # Add exit candle low if enabled
                if show_exit_low:
                    if exit_candle_low is not None and not pd.isna(exit_candle_low):
                        row_data.append(f"[dim]{exit_candle_low:.2f}[/dim]")
                    else:
                        row_data.append("[dim]N/A[/dim]")
                
                row_data.extend([
                    str(quantity) if quantity is not None and not pd.isna(quantity) else "N/A",
                    pnl_str,
                    f"[green]{max_unrealized:+.2f}[/green]",
                    f"[red]{min_unrealized:+.2f}[/red]",
                    return_str,
                    charges_str,
                    net_profit_str,
                    mode_str,
                    str(duration_str) if duration_str is not None else "N/A",
                    str(entry_reason_short) if entry_reason_short is not None else "N/A",
                    str(exit_reason_short) if exit_reason_short is not None else "N/A"
                ])
                
                trades_table.add_row(*row_data)
            
            self.console.print(trades_table)
            self.console.print()
            
            # Display Indicator Combination Summary
            self._display_indicator_combination_summary(closed_orders)
        else:
            self.console.print("[yellow]No completed trades found.[/yellow]\n")
        
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
        self.console.print("\n" + "=" * 100)
        self.console.print("[bold cyan]📊 PERFORMANCE METRICS MATRIX[/bold cyan]")
        self.console.print("=" * 100 + "\n")
        
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
        
        # Get total charges and net profit from summary
        total_charges = summary.get('total_charges', 0.0)
        total_net_profit = summary.get('total_net_profit', total_pnl)  # Fallback to total_pnl if not available
        total_gross_pnl = summary.get('total_gross_pnl', total_pnl)  # Fallback to total_pnl if not available
        
        metrics_table.add_row(
            "",
            "Total Charges",
            f"[yellow]₹{total_charges:,.2f}[/yellow]"
        )
        metrics_table.add_row(
            "",
            "Gross PnL",
            f"[{'green' if total_gross_pnl >= 0 else 'red'}]₹{total_gross_pnl:+,.2f}[/]"
        )
        metrics_table.add_row(
            "",
            "Net Profit (After Charges)",
            f"[{'green' if total_net_profit >= 0 else 'red'}]₹{total_net_profit:+,.2f}[/]"
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
        
        self.console.print(metrics_table)
        self.console.print()
        
        # Get total charges and net profit from summary
        total_charges = summary.get('total_charges', 0.0)
        total_net_profit = summary.get('total_net_profit', total_pnl)  # Fallback to total_pnl if not available
        total_gross_pnl = summary.get('total_gross_pnl', total_pnl)  # Fallback to total_pnl if not available
        
        # Summary message
        self.console.print("=" * 100)
        if returns_pct > 0:
            self.console.print(f"[bold green]✅ BACKTEST PROFITABLE: +{returns_pct:.2f}% return on ₹{initial_capital:,.2f}[/bold green]")
        elif returns_pct < 0:
            self.console.print(f"[bold red]❌ BACKTEST LOSS: {returns_pct:.2f}% loss on ₹{initial_capital:,.2f}[/bold red]")
        else:
            self.console.print(f"[bold yellow]⚖️  BACKTEST BREAKEVEN: 0.00% on ₹{initial_capital:,.2f}[/bold yellow]")
        
        # Display charges and net profit summary
        self.console.print(f"[bold cyan]💰 TRADING CHARGES & NET PROFIT SUMMARY[/bold cyan]")
        self.console.print(f"   Gross PnL (Before Charges): [{'green' if total_gross_pnl >= 0 else 'red'}]₹{total_gross_pnl:+,.2f}[/]")
        self.console.print(f"   Total Charges: [yellow]₹{total_charges:,.2f}[/yellow]")
        self.console.print(f"   Net Profit (After Charges): [{'green' if total_net_profit >= 0 else 'red'}]₹{total_net_profit:+,.2f}[/]")
        if total_charges > 0:
            charges_pct = (total_charges / abs(total_gross_pnl) * 100) if total_gross_pnl != 0 else 0
            self.console.print(f"   Charges Impact: [yellow]{charges_pct:.2f}% of gross PnL[/yellow]")
        
        # Show circuit breaker impact if applicable
        if circuit_breaker_savings > 0:
            self.console.print(f"[bold green]🛡️  CIRCUIT BREAKER SAVED: ₹{circuit_breaker_savings:+,.2f} ({paper_trades_count} paper trades protected)[/bold green]")
        elif circuit_breaker_savings < 0:
            self.console.print(f"[yellow]🛡️  Circuit Breaker Active: {paper_trades_count} paper trades[/yellow]")
        
        self.console.print("=" * 100 + "\n")
        
        # Save backtest results to JSON for UI
        self.save_backtest_results_to_json(
            summary, closed_orders, initial_capital, final_capital, total_pnl, returns_pct,
            real_trades_count, winning_trades, losing_trades, win_rate_calc,
            all_trades_count, winning_trades_all, losing_trades_all, win_rate_all,
            paper_trades_count, circuit_breaker_savings, hypothetical_capital, actual_capital_val,
            avg_win, avg_loss, max_win, max_loss, profit_factor, expectancy
        )
    
    def _display_indicator_combination_summary(self, closed_orders: pd.DataFrame):
        """Display indicator combination success ratio summary."""
        if closed_orders.empty:
            return
        
        # Analyze indicator combinations
        combination_stats = {}
        indicator_stats = {}
        
        for idx, row in closed_orders.iterrows():
            indicator_signals = row.get('indicator_signals', {})
            if not isinstance(indicator_signals, dict) or not indicator_signals:
                continue
            
            pnl = row.get('pnl', 0)
            is_win = pnl > 0
            
            # Create combination key with only BUY signals (to avoid duplicates)
            buy_signals = [f"{ind}:{sig}" for ind, sig in indicator_signals.items() if sig == 'BUY']
            if not buy_signals:  # Skip if no BUY signals
                continue
            combo_key = tuple(sorted(buy_signals))
            
            # Track combination stats
            if combo_key not in combination_stats:
                combination_stats[combo_key] = {'wins': 0, 'losses': 0, 'total_pnl': 0.0}
            
            if is_win:
                combination_stats[combo_key]['wins'] += 1
            else:
                combination_stats[combo_key]['losses'] += 1
            combination_stats[combo_key]['total_pnl'] += pnl
            
            # Track individual indicator stats
            for ind, sig in indicator_signals.items():
                if ind not in indicator_stats:
                    indicator_stats[ind] = {'BUY': {'wins': 0, 'losses': 0, 'total_pnl': 0.0},
                                           'SELL': {'wins': 0, 'losses': 0, 'total_pnl': 0.0},
                                           'HOLD': {'wins': 0, 'losses': 0, 'total_pnl': 0.0}}
                
                if is_win:
                    indicator_stats[ind][sig]['wins'] += 1
                else:
                    indicator_stats[ind][sig]['losses'] += 1
                indicator_stats[ind][sig]['total_pnl'] += pnl
        
        # Display Indicator Combination Summary
        self.console.print("\n" + "=" * 100)
        self.console.print("[bold cyan]📊 INDICATOR COMBINATION SUCCESS SUMMARY[/bold cyan]")
        self.console.print("=" * 100 + "\n")
        
        # Individual Indicator Performance Table
        if indicator_stats:
            ind_table = Table(
                title="Individual Indicator Performance",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold yellow"
            )
            
            ind_table.add_column("Indicator", style="cyan", width=20)
            ind_table.add_column("Signal", style="white", width=8)
            ind_table.add_column("Wins", style="green", width=6)
            ind_table.add_column("Losses", style="red", width=6)
            ind_table.add_column("Total", style="white", width=6)
            ind_table.add_column("Win Rate", style="bold", width=10)
            ind_table.add_column("Total PnL", style="bold", width=12)
            ind_table.add_column("Avg PnL", style="dim", width=10)
            
            # Sort indicators by total PnL
            sorted_indicators = []
            for ind, stats in indicator_stats.items():
                for sig in ['BUY', 'SELL', 'HOLD']:
                    wins = stats[sig]['wins']
                    losses = stats[sig]['losses']
                    total = wins + losses
                    if total > 0:
                        sorted_indicators.append((ind, sig, wins, losses, total, stats[sig]['total_pnl']))
            
            sorted_indicators.sort(key=lambda x: x[5], reverse=True)  # Sort by total PnL
            
            for ind, sig, wins, losses, total, total_pnl in sorted_indicators:
                win_rate = (wins / total * 100) if total > 0 else 0
                avg_pnl = total_pnl / total if total > 0 else 0
                
                # Color code win rate
                if win_rate >= 60:
                    win_rate_str = f"[green]{win_rate:.1f}%[/green]"
                elif win_rate >= 40:
                    win_rate_str = f"[yellow]{win_rate:.1f}%[/yellow]"
                else:
                    win_rate_str = f"[red]{win_rate:.1f}%[/red]"
                
                # Color code PnL
                if total_pnl > 0:
                    pnl_str = f"[green]₹{total_pnl:+,.2f}[/green]"
                    avg_pnl_str = f"[green]₹{avg_pnl:+,.2f}[/green]"
                else:
                    pnl_str = f"[red]₹{total_pnl:,.2f}[/red]"
                    avg_pnl_str = f"[red]₹{avg_pnl:,.2f}[/red]"
                
                # Color code signal
                if sig == 'BUY':
                    sig_str = "[green]BUY[/green]"
                elif sig == 'SELL':
                    sig_str = "[red]SELL[/red]"
                else:
                    sig_str = "[dim]HOLD[/dim]"
                
                ind_table.add_row(
                    ind,
                    sig_str,
                    str(wins),
                    str(losses),
                    str(total),
                    win_rate_str,
                    pnl_str,
                    avg_pnl_str
                )
            
            self.console.print(ind_table)
            self.console.print()
        
        # Top Indicator Combinations Table
        if combination_stats:
            combo_table = Table(
                title="Top Indicator Combinations (by Total PnL)",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold magenta"
            )
            
            combo_table.add_column("Rank", style="dim", width=5)
            combo_table.add_column("Combination", style="cyan", width=80)
            combo_table.add_column("Wins", style="green", width=6)
            combo_table.add_column("Losses", style="red", width=6)
            combo_table.add_column("Total", style="white", width=6)
            combo_table.add_column("Win Rate", style="bold", width=10)
            combo_table.add_column("Total PnL", style="bold", width=12)
            combo_table.add_column("Avg PnL", style="dim", width=10)
            
            # Sort combinations by total PnL (combo_key already contains only BUY signals)
            sorted_combos = []
            for combo_key, stats in combination_stats.items():
                wins = stats['wins']
                losses = stats['losses']
                total = wins + losses
                total_pnl = stats['total_pnl']
                sorted_combos.append((combo_key, wins, losses, total, total_pnl))
            
            sorted_combos.sort(key=lambda x: x[4], reverse=True)  # Sort by total PnL
            sorted_combos = sorted_combos[:20]  # Show top 20
            
            for rank, (combo_key, wins, losses, total, total_pnl) in enumerate(sorted_combos, 1):
                win_rate = (wins / total * 100) if total > 0 else 0
                avg_pnl = total_pnl / total if total > 0 else 0
                
                # Format combination string (combo_key already contains only BUY signals)
                combo_str = ", ".join([f"{ind.split(':')[0]}:{ind.split(':')[1]}" for ind in combo_key])
                if len(combo_str) > 78:
                    combo_str = combo_str[:75] + "..."
                
                # Color code win rate
                if win_rate >= 60:
                    win_rate_str = f"[green]{win_rate:.1f}%[/green]"
                elif win_rate >= 40:
                    win_rate_str = f"[yellow]{win_rate:.1f}%[/yellow]"
                else:
                    win_rate_str = f"[red]{win_rate:.1f}%[/red]"
                
                # Color code PnL
                if total_pnl > 0:
                    pnl_str = f"[green]₹{total_pnl:+,.2f}[/green]"
                    avg_pnl_str = f"[green]₹{avg_pnl:+,.2f}[/green]"
                else:
                    pnl_str = f"[red]₹{total_pnl:,.2f}[/red]"
                    avg_pnl_str = f"[red]₹{avg_pnl:,.2f}[/red]"
                
                combo_table.add_row(
                    str(rank),
                    combo_str,
                    str(wins),
                    str(losses),
                    str(total),
                    win_rate_str,
                    pnl_str,
                    avg_pnl_str
                )
            
            self.console.print(combo_table)
            self.console.print()
        
        # Display Symbol-wise Indicator Performance
        self._display_symbol_wise_indicator_performance(closed_orders)
    
    def _display_symbol_wise_indicator_performance(self, closed_orders: pd.DataFrame):
        """Display indicator performance broken down by symbol."""
        if closed_orders.empty:
            return
        
        # Group by symbol
        symbols = closed_orders['symbol'].unique()
        
        self.console.print("\n" + "=" * 100)
        self.console.print("[bold cyan]📈 SYMBOL-WISE INDICATOR PERFORMANCE[/bold cyan]")
        self.console.print("=" * 100 + "\n")
        
        for symbol in sorted(symbols):
            symbol_short = symbol.split(':')[-1]
            symbol_orders = closed_orders[closed_orders['symbol'] == symbol]
            
            if symbol_orders.empty:
                continue
            
            # Analyze indicator combinations for this symbol
            combination_stats = {}
            indicator_stats = {}
            
            for idx, row in symbol_orders.iterrows():
                indicator_signals = row.get('indicator_signals', {})
                if not isinstance(indicator_signals, dict) or not indicator_signals:
                    continue
                
                pnl = row.get('pnl', 0)
                is_win = pnl > 0
                
                # Create combination key with only BUY signals
                buy_signals = [f"{ind}:{sig}" for ind, sig in indicator_signals.items() if sig == 'BUY']
                if not buy_signals:
                    continue
                combo_key = tuple(sorted(buy_signals))
                
                # Track combination stats
                if combo_key not in combination_stats:
                    combination_stats[combo_key] = {'wins': 0, 'losses': 0, 'total_pnl': 0.0}
                
                if is_win:
                    combination_stats[combo_key]['wins'] += 1
                else:
                    combination_stats[combo_key]['losses'] += 1
                combination_stats[combo_key]['total_pnl'] += pnl
                
                # Track individual indicator stats
                for ind, sig in indicator_signals.items():
                    if ind not in indicator_stats:
                        indicator_stats[ind] = {'BUY': {'wins': 0, 'losses': 0, 'total_pnl': 0.0},
                                               'SELL': {'wins': 0, 'losses': 0, 'total_pnl': 0.0},
                                               'HOLD': {'wins': 0, 'losses': 0, 'total_pnl': 0.0}}
                    
                    if is_win:
                        indicator_stats[ind][sig]['wins'] += 1
                    else:
                        indicator_stats[ind][sig]['losses'] += 1
                    indicator_stats[ind][sig]['total_pnl'] += pnl
            
            # Display symbol header
            self.console.print(f"\n[bold yellow]Symbol: {symbol_short}[/bold yellow]")
            self.console.print(f"Total Trades: {len(symbol_orders)}")
            total_pnl_symbol = symbol_orders['pnl'].sum()
            pnl_color = "green" if total_pnl_symbol > 0 else "red"
            self.console.print(f"Total PnL: [{pnl_color}]₹{total_pnl_symbol:+,.2f}[/{pnl_color}]\n")
            
            # Individual Indicator Performance for this symbol
            if indicator_stats:
                ind_table = Table(
                    title=f"Individual Indicator Performance - {symbol_short}",
                    box=box.ROUNDED,
                    show_header=True,
                    header_style="bold yellow"
                )
                
                ind_table.add_column("Indicator", style="cyan", width=20)
                ind_table.add_column("Signal", style="white", width=8)
                ind_table.add_column("Wins", style="green", width=6)
                ind_table.add_column("Losses", style="red", width=6)
                ind_table.add_column("Total", style="white", width=6)
                ind_table.add_column("Win Rate", style="bold", width=10)
                ind_table.add_column("Total PnL", style="bold", width=12)
                ind_table.add_column("Avg PnL", style="dim", width=10)
                
                # Sort indicators by total PnL
                sorted_indicators = []
                for ind, stats in indicator_stats.items():
                    for sig in ['BUY', 'SELL', 'HOLD']:
                        wins = stats[sig]['wins']
                        losses = stats[sig]['losses']
                        total = wins + losses
                        if total > 0:
                            sorted_indicators.append((ind, sig, wins, losses, total, stats[sig]['total_pnl']))
                
                sorted_indicators.sort(key=lambda x: x[5], reverse=True)
                
                for ind, sig, wins, losses, total, total_pnl in sorted_indicators:
                    win_rate = (wins / total * 100) if total > 0 else 0
                    avg_pnl = total_pnl / total if total > 0 else 0
                    
                    # Color code win rate
                    if win_rate >= 60:
                        win_rate_str = f"[green]{win_rate:.1f}%[/green]"
                    elif win_rate >= 40:
                        win_rate_str = f"[yellow]{win_rate:.1f}%[/yellow]"
                    else:
                        win_rate_str = f"[red]{win_rate:.1f}%[/red]"
                    
                    # Color code PnL
                    if total_pnl > 0:
                        pnl_str = f"[green]₹{total_pnl:+,.2f}[/green]"
                        avg_pnl_str = f"[green]₹{avg_pnl:+,.2f}[/green]"
                    else:
                        pnl_str = f"[red]₹{total_pnl:,.2f}[/red]"
                        avg_pnl_str = f"[red]₹{avg_pnl:,.2f}[/red]"
                    
                    # Color code signal
                    if sig == 'BUY':
                        sig_str = "[green]BUY[/green]"
                    elif sig == 'SELL':
                        sig_str = "[red]SELL[/red]"
                    else:
                        sig_str = "[dim]HOLD[/dim]"
                    
                    ind_table.add_row(
                        ind,
                        sig_str,
                        str(wins),
                        str(losses),
                        str(total),
                        win_rate_str,
                        pnl_str,
                        avg_pnl_str
                    )
                
                self.console.print(ind_table)
                self.console.print()
            
            # Indicator Combinations for this symbol
            if combination_stats:
                combo_table = Table(
                    title=f"Indicator Combinations - {symbol_short}",
                    box=box.ROUNDED,
                    show_header=True,
                    header_style="bold magenta"
                )
                
                combo_table.add_column("Rank", style="dim", width=5)
                combo_table.add_column("Combination", style="cyan", width=80)
                combo_table.add_column("Wins", style="green", width=6)
                combo_table.add_column("Losses", style="red", width=6)
                combo_table.add_column("Total", style="white", width=6)
                combo_table.add_column("Win Rate", style="bold", width=10)
                combo_table.add_column("Total PnL", style="bold", width=12)
                combo_table.add_column("Avg PnL", style="dim", width=10)
                
                # Sort combinations by total PnL
                sorted_combos = []
                for combo_key, stats in combination_stats.items():
                    wins = stats['wins']
                    losses = stats['losses']
                    total = wins + losses
                    total_pnl = stats['total_pnl']
                    sorted_combos.append((combo_key, wins, losses, total, total_pnl))
                
                sorted_combos.sort(key=lambda x: x[4], reverse=True)
                
                for rank, (combo_key, wins, losses, total, total_pnl) in enumerate(sorted_combos, 1):
                    win_rate = (wins / total * 100) if total > 0 else 0
                    avg_pnl = total_pnl / total if total > 0 else 0
                    
                    # Format combination string
                    combo_str = ", ".join([f"{ind.split(':')[0]}:{ind.split(':')[1]}" for ind in combo_key])
                    if len(combo_str) > 78:
                        combo_str = combo_str[:75] + "..."
                    
                    # Color code win rate
                    if win_rate >= 60:
                        win_rate_str = f"[green]{win_rate:.1f}%[/green]"
                    elif win_rate >= 40:
                        win_rate_str = f"[yellow]{win_rate:.1f}%[/yellow]"
                    else:
                        win_rate_str = f"[red]{win_rate:.1f}%[/red]"
                    
                    # Color code PnL
                    if total_pnl > 0:
                        pnl_str = f"[green]₹{total_pnl:+,.2f}[/green]"
                        avg_pnl_str = f"[green]₹{avg_pnl:+,.2f}[/green]"
                    else:
                        pnl_str = f"[red]₹{total_pnl:,.2f}[/red]"
                        avg_pnl_str = f"[red]₹{avg_pnl:,.2f}[/red]"
                    
                    combo_table.add_row(
                        str(rank),
                        combo_str,
                        str(wins),
                        str(losses),
                        str(total),
                        win_rate_str,
                        pnl_str,
                        avg_pnl_str
                    )
                
                self.console.print(combo_table)
                self.console.print()
    
    def _display_loss_recovery_history(self):
        """Display loss recovery history and status."""
        recovery_history = self.engine.get_recovery_history()
        loss_history = self.engine.get_loss_history()
        loss_status = self.engine.get_loss_recovery_status()
        
        # Display Loss History
        if loss_history:
            self.console.print("\n[bold cyan]📉 LOSS HISTORY[/bold cyan]")
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
            
            self.console.print(loss_table)
            self.console.print()
        
        # Display Recovery History
        if recovery_history:
            self.console.print("[bold green]✅ RECOVERY HISTORY[/bold green]")
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
            
            self.console.print(recovery_table)
            self.console.print()
        
        # Display Current Loss Recovery Status
        if loss_status['symbols_with_loss']:
            self.console.print("[bold yellow]⚠️  CURRENT LOSS RECOVERY STATUS[/bold yellow]")
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
            
            self.console.print(status_table)
            self.console.print()
        elif recovery_history or loss_history:
            self.console.print("[bold green]✅ All losses have been recovered![/bold green]\n")
