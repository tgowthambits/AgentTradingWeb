"""
Display manager for console output and Rich table/panel rendering.
"""

import pandas as pd
from datetime import datetime
from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich import box
from typing import List, Dict, Any, Optional


class DisplayManager:
    """Manages all console display and Rich table/panel rendering."""
    
    def __init__(self, engine, config: Dict[str, Any], console: Optional[Console] = None):
        """
        Initialize the display manager.
        
        Args:
            engine: TradingEngine instance
            config: Configuration dictionary
            console: Optional Rich Console instance (creates new one if not provided)
        """
        self.engine = engine
        self.config = config
        self.console = console or Console()
    
    def display_results(self, results: List[Dict], refresh_count: int, 
                       auto_trade: bool, allow_buy: bool, allow_sell: bool,
                       total_signals_generated: int, refresh_interval: int):
        """Display results with proper Rich rendering."""
        # Build trade direction info
        trade_directions = []
        if allow_buy:
            trade_directions.append("[green]BUY✓[/green]")
        else:
            trade_directions.append("[dim]BUY✗[/dim]")
        
        if allow_sell:
            trade_directions.append("[red]SELL✓[/red]")
        else:
            trade_directions.append("[dim]SELL✗[/dim]")
        
        directions_str = " ".join(trade_directions)
        
        # Header
        header = Panel(
            f"[bold cyan]🤖 Live Trading Bot[/bold cyan] | "
            f"Refresh #{refresh_count} | "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
            f"Auto-Trade: {'ON' if auto_trade else 'OFF'} | "
            f"{directions_str}",
            style="bold green"
        )
        self.console.print(header)
        self.console.print()
        
        # Single comprehensive table with all details
        comprehensive_table = self.create_comprehensive_table(results)
        self.console.print(comprehensive_table)
        self.console.print()
        
        # Closed orders table
        closed_orders = self.engine.get_closed_orders()
        if not closed_orders.empty:
            orders_table = self.create_completed_orders_table(closed_orders)
            self.console.print(orders_table)
            self.console.print()
        
        # Performance KPIs
        kpi_panel = self.create_kpi_panel(
            results, closed_orders, refresh_count, 
            total_signals_generated, refresh_interval
        )
        self.console.print(kpi_panel)
        self.console.print()
        
        # Add legend
        self.console.print(
            "[dim]Legend: B=BUY, S=SELL, H=HOLD | "
            "* = Unrealized PnL (open position) | "
            "RSI/MA/MACD/BB = Individual indicator signals[/dim]"
        )
    
    def create_comprehensive_table(self, results: List[Dict]) -> Table:
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
    
    def _abbreviate_indicator_name(self, name: str) -> str:
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
    
    def _format_signal_with_icon(self, signal: str) -> str:
        """Format signal with visual icon."""
        if signal == 'BUY':
            return "[green bold]✓[/green bold]"  # Checkmark for BUY
        elif signal == 'SELL':
            return "[red bold]✗[/red bold]"  # X for SELL
        else:
            return "[dim]○[/dim]"  # Circle for HOLD
    
    def create_completed_orders_table(self, orders_df: pd.DataFrame) -> Table:
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
        table.add_column("Max U.PnL\n(₹)", style="green", width=11)
        table.add_column("Min U.PnL\n(₹)", style="red", width=11)
        table.add_column("Return\n%", style="white", width=8)
        table.add_column("Total\nCharges\n(₹)", style="yellow", width=12)
        table.add_column("Net\nProfit\n(₹)", style="white", width=11)
        table.add_column("Entry Reason", style="dim", width=20)
        table.add_column("Exit Reason", style="dim", width=20)
        
        total_pnl = 0
        
        for _, row in orders_df.iterrows():
            symbol_short = row['symbol'].split(':')[-1]
            type_color = "green" if row['type'] == 'LONG' else "red"
            pnl_color = "green" if row['pnl'] > 0 else "red" if row['pnl'] < 0 else "white"
            max_unrealized = float(row.get('max_profit', 0.0) or 0.0)
            min_unrealized = float(row.get('min_profit', 0.0) or 0.0)
            
            # Calculate duration
            total_secs = int((row['exit_time'] - row['entry_time']).total_seconds())
            h, remainder = divmod(abs(total_secs), 3600)
            m, s = divmod(remainder, 60)
            duration_str = f"{h:02d}:{m:02d}:{s:02d}"
            
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
            
            # Get total charges and net profit (with fallbacks)
            total_charges = float(row.get('total_charges', 0.0))
            net_profit = float(row.get('net_profit', row['pnl']))  # Fallback to pnl if not available
            if pd.isna(total_charges) or total_charges is None:
                total_charges = 0.0
            if pd.isna(net_profit) or net_profit is None:
                net_profit = row['pnl']
            
            # Color code net profit
            net_profit_color = "green" if net_profit > 0 else "red" if net_profit < 0 else "white"
            
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
                f"[green]{max_unrealized:+.2f}[/green]",
                f"[red]{min_unrealized:+.2f}[/red]",
                f"[{return_color}]{return_pct:+.2f}%[/{return_color}]",
                f"[yellow]{total_charges:.2f}[/yellow]",
                f"[{net_profit_color}]{net_profit:+.2f}[/{net_profit_color}]",
                entry_reason_short,
                exit_reason_short
            )
        
        # Add total row
        if len(orders_df) > 0:
            total_color = "green" if total_pnl > 0 else "red"
            total_row = [""] * len(table.columns)
            total_row[1] = "[bold]TOTAL REALIZED[/bold]"
            total_row[10] = f"[bold {total_color}]{total_pnl:+.2f}[/bold {total_color}]"
            table.add_row(*total_row)
        
        return table
    
    def create_kpi_panel(self, results: List[Dict], closed_orders_df: pd.DataFrame,
                        refresh_count: int, total_signals_generated: int, 
                        refresh_interval: int) -> Panel:
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
            f"  Signals Generated Today: {total_signals_generated}\n"
            f"  Bot Uptime: {refresh_count} refreshes ({refresh_count * refresh_interval}s)\n"
            f"\n"
            f"[bold cyan]Signal Distribution:[/bold cyan]\n"
            f"  BUY: [green]{buy_signals}[/green] | SELL: [red]{sell_signals}[/red] | HOLD: [yellow]{hold_signals}[/yellow]\n"
            f"\n"
            f"[bold cyan]Indicator Performance:[/bold cyan]\n"
            f"  Average Agreement: {indicator_agreement:.1%}\n"
            f"  Active Indicators: {summary['indicators_registered']}\n"
            f"  Strategy: {self.config.get('aggregation_strategy', 'weighted').title()}"
        )
        
        return Panel(content, title="[bold]📊 Performance KPIs & Metrics[/bold]", style="cyan", border_style="cyan")
    
    def clear(self):
        """Clear the console."""
        self.console.clear()
    
    def print(self, *args, **kwargs):
        """Print to console."""
        self.console.print(*args, **kwargs)
