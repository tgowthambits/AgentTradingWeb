#!/usr/bin/env python3
"""
Update run_live_bot.py to have dynamic indicator columns with icons
"""

import re

file_path = "trading_system/run_live_bot.py"

# Read the file
with open(file_path, 'r') as f:
    content = f.read()

# New method implementations
new_abbreviate_method = '''    def _abbreviate_indicator_name(self, name):
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
'''

# Update the create_main_table method
new_create_main_table = '''    def create_main_table(self, results):
        """Create comprehensive main table with all indicators and positions (DYNAMIC)."""
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
        table.add_column("LTP\\n(₹)", style="white", width=8)
        table.add_column("Final\\nSignal", style="bold", width=7)
        
        # Add dynamic indicator columns with icons
        for indicator_name in active_indicators:
            display_name = self._abbreviate_indicator_name(indicator_name)
            table.add_column(display_name, style="white", width=6, justify="center")
        
        # Add aggregation and position columns
        table.add_column("Agree\\n%", style="white", width=6)
        table.add_column("Position", style="white", width=8)
        table.add_column("Entry\\n(₹)", style="white", width=8)
        table.add_column("Qty", style="white", width=4)
        table.add_column("Unrealized\\nPnL (₹)", style="white", width=12)
        
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
            # Calculate number of empty columns
            num_empty_cols = 2 + len(active_indicators) + 4  # LTP, Signal + indicators + Agree%, Pos, Entry, Qty
            empty_cols = [""] * num_empty_cols
            
            table.add_row(
                "[bold]TOTAL UNREALIZED[/bold]",
                *empty_cols,
                f"[bold {total_color}]{total_unrealized_pnl:+.2f}*[/bold {total_color}]"
            )
        
        return table
'''

# Find and replace the create_main_table method
pattern = r'    def create_main_table\(self, results\):.*?        return table\n'
match = re.search(pattern, content, re.DOTALL)

if match:
    content = content[:match.start()] + new_create_main_table + '\n' + content[match.end():]
    print("✅ Replaced create_main_table method")
else:
    print("❌ Could not find create_main_table method")

# Add new methods before _abbrev_signal if they don't exist
if '_abbreviate_indicator_name' not in content:
    # Find _abbrev_signal method
    pattern = r'    def _abbrev_signal\(self, signal\):'
    match = re.search(pattern, content)
    if match:
        content = content[:match.start()] + new_abbreviate_method + '\n' + content[match.start():]
        print("✅ Added _abbreviate_indicator_name and _format_signal_with_icon methods")
    else:
        print("❌ Could not find _abbrev_signal method")
else:
    print("ℹ️  Methods already exist")

# Write back
with open(file_path, 'w') as f:
    f.write(content)

print("\n✅ File updated successfully!")
print("\nℹ️  Run ./start_trading_bot.sh to see the dynamic table with icons")

