"""
Bot Integration Module
Adds UI data broadcasting to the trading bot without modifying core functionality
"""

import sys
from pathlib import Path
import requests
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class BotUIIntegration:
    """
    Wraps the trading bot and broadcasts data to the UI.
    Does NOT modify bot logic, only observes and shares data.
    """
    
    def __init__(self, bot_instance):
        """
        Initialize with a bot instance.
        
        Args:
            bot_instance: Instance of TradingBot (run_live_bot.py)
        """
        self.bot = bot_instance
        self.api_url = "http://localhost:8000/api"
        self.ui_available = True  # Flag to track if UI server is accessible
        self.first_error_shown = False  # Show error message only once
        
        print("✅ Bot UI Integration initialized")
    
    def _make_api_call(self, endpoint, data, method='post'):
        """
        Make an API call with graceful error handling.
        Returns True if successful, False otherwise.
        """
        if not self.ui_available:
            return False
        
        try:
            url = f"{self.api_url}/{endpoint}"
            if method == 'post':
                response = requests.post(url, json=data, timeout=1)
            else:
                response = requests.get(url, timeout=1)
            return response.status_code == 200
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if not self.first_error_shown:
                print(f"⚠️  Web UI not available (running without UI)")
                self.first_error_shown = True
            self.ui_available = False
            return False
        except Exception as e:
            if not self.first_error_shown:
                print(f"⚠️  UI communication error: {e}")
                self.first_error_shown = True
            return False
    
    def start(self):
        """Start the UI integration."""
        # Set initial bot status
        self._update_bot_status()
        
        # Set indicators info
        self._update_indicators()
        
        print("✅ Bot UI Integration started")
    
    def after_run_once(self, results):
        """
        Called after each bot run_once() cycle.
        Broadcasts latest data to UI.
        
        Args:
            results: List of analysis results from run_once()
        """
        try:
            # Update bot status
            self._update_bot_status()
            
            # Update symbols analysis
            for result in results:
                symbol = result.get('symbol')
                if symbol:
                    self._update_symbol_analysis(symbol, result)
            
            # Update performance
            self._update_performance()
            
            # Update positions
            self._update_positions()
            
        except Exception as e:
            # Silent fail - UI errors shouldn't crash the bot
            pass
    
    def _update_bot_status(self):
        """Update bot status via API."""
            status = {
                'running': True,
                'auto_trade': self.bot.auto_trade,
                'allow_buy': self.bot.allow_buy,
                'allow_sell': self.bot.allow_sell,
                'refresh_count': self.bot.refresh_count,
            'uptime_seconds': self.bot.refresh_count * self.bot.refresh_interval,
            'refresh_interval': self.bot.refresh_interval,
            'signals_generated': self.bot.total_signals_generated
            }
        self._make_api_call('update/bot-status', status)
    
    def _update_symbol_analysis(self, symbol, result):
        """Update symbol analysis via API."""
        # Check if this symbol has an open position
        position = self.bot.engine.current_positions.get(symbol)
        unrealized_pnl = 0
        
        if position:
            # Calculate unrealized PnL
            current_price = result.get('latest_price', 0)
            if position['type'] == 'LONG':
                unrealized_pnl = (current_price - position['entry_price']) * position['quantity']
            else:  # SHORT
                unrealized_pnl = (position['entry_price'] - current_price) * position['quantity']
        
            # Extract key data
            data = {
                'symbol': symbol,
                'final_signal': result.get('final_signal', 'HOLD'),
                'latest_price': result.get('latest_price', 0),
                'current_price': result.get('latest_price', 0),
                'indicator_signals': result.get('indicator_signals', {}),
                'agreement_pct': result.get('agreement_score', 0) * 100,
            'position': position['type'] if position else '-',
            'entry_price': position['entry_price'] if position else 0,
            'quantity': position['quantity'] if position else 0,
            'unrealized_pnl': unrealized_pnl
            }
            
        self._make_api_call('update/symbol', data)
    
    def _update_performance(self):
        """Update performance metrics in data bridge."""
        try:
            # Get metrics from bot's trading engine
            engine = self.bot.engine
            
            # Calculate metrics - use order_history for closed orders
            closed_orders = [order for order in engine.order_history if order.get('status') == 'closed']
            total_pnl = sum(order.get('pnl', 0) for order in closed_orders)
            
            # Calculate realized PnL (from closed orders)
            realized_pnl = total_pnl
            
            # Calculate unrealized PnL (from open positions)
            unrealized_pnl = 0
            for symbol, pos in engine.current_positions.items():
                current_price = pos.get('current_price', pos.get('entry_price', 0))
                entry_price = pos.get('entry_price', 0)
                quantity = pos.get('quantity', 0)
                pos_type = pos.get('type', 'LONG')
                
                if pos_type == 'LONG':
                    unrealized_pnl += (current_price - entry_price) * quantity
                else:  # SHORT
                    unrealized_pnl += (entry_price - current_price) * quantity
            
            # Total PnL
            total_pnl_combined = realized_pnl + unrealized_pnl
            
            # Win/Loss stats
            win_trades = sum(1 for order in closed_orders if order.get('pnl', 0) > 0)
            loss_trades = sum(1 for order in closed_orders if order.get('pnl', 0) < 0)
            total_trades = len(closed_orders)
            win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Best/Worst
            pnls = [order.get('pnl', 0) for order in closed_orders]
            best_trade = max(pnls) if pnls else 0
            worst_trade = min(pnls) if pnls else 0
            
            # Average PnL
            avg_pnl = (total_pnl / total_trades) if total_trades > 0 else 0
            
            metrics = {
                'total_pnl': total_pnl_combined,
                'realized_pnl': realized_pnl,
                'unrealized_pnl': unrealized_pnl,
                'total_trades': total_trades,
                'win_trades': win_trades,
                'loss_trades': loss_trades,
                'win_rate': win_rate,
                'best_trade': best_trade,
                'worst_trade': worst_trade,
                'avg_pnl': avg_pnl
            }
            
            self._make_api_call('update/performance', metrics)
            
        except Exception:
            pass  # Silent fail for any calculation errors
    
    def _update_positions(self):
        """Update positions in data bridge."""
        try:
            engine = self.bot.engine
            
            # Open positions - use current_positions
            open_positions = []
            for symbol, pos in engine.current_positions.items():
                
                # Calculate current unrealized PnL
                current_price = pos.get('current_price', pos.get('entry_price', 0))
                entry_price = pos.get('entry_price', 0)
                quantity = pos.get('quantity', 0)
                pos_type = pos.get('type', 'LONG')
                
                if pos_type == 'LONG':
                    unrealized_pnl = (current_price - entry_price) * quantity
                else:  # SHORT
                    unrealized_pnl = (entry_price - current_price) * quantity
                
                # Format entry_time
                entry_time_str = ''
                if 'entry_time' in pos:
                    entry_time = pos['entry_time']
                    if hasattr(entry_time, 'isoformat'):
                        entry_time_str = entry_time.isoformat()
                    else:
                        entry_time_str = str(entry_time)
                
                position_data = {
                    'symbol': pos.get('symbol', symbol),
                    'position': pos_type,
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'quantity': quantity,
                    'unrealized_pnl': unrealized_pnl,
                    'entry_time': entry_time_str
                }
                
                open_positions.append(position_data)
            
            # Closed orders - use order_history
            closed_orders = []
            for order in engine.order_history:
                if order.get('status') != 'closed':
                    continue
                closed_orders.append({
                    'symbol': order['symbol'],
                    'position': order['position'],
                    'entry_price': order['entry_price'],
                    'exit_price': order['exit_price'],
                    'quantity': order['quantity'],
                    'pnl': order.get('pnl', 0),
                    'entry_time': order.get('entry_time', ''),
                    'exit_time': order.get('exit_time', '')
                })
            
            positions_data = {
                'open': open_positions,
                'closed': closed_orders
            }
            
            self._make_api_call('update/positions', positions_data)
            
        except Exception as e:
            # Silent fail for any calculation errors
            pass
    
    def _update_indicators(self):
        """Update active indicators list in data bridge."""
        try:
            # Get indicators from bot's engine (it's already a list!)
            indicator_info = self.bot.indicator_info
            
            # indicator_info is already a list of dicts, just use it directly
            if isinstance(indicator_info, list):
                indicators = indicator_info
            else:
                # Fallback for dict format
                indicators = []
                for ind_name, info in indicator_info.items():
                    indicators.append({
                        'name': ind_name,
                        'enabled': info.get('enabled', True),
                        'weight': info.get('weight', 1.0),
                        'module': info.get('module', ''),
                        'class_name': info.get('class_name', '')
                    })
            
            self._make_api_call('update/indicators', indicators)
            
        except Exception:
            pass  # Silent fail for any calculation errors


def integrate_ui_with_bot(bot_instance):
    """
    Main function to integrate UI with bot.
    Returns the integration instance.
    
    Usage in run_live_bot.py:
        from trading_system.ui.bot_integration import integrate_ui_with_bot
        
        # After creating bot
        bot = TradingBot(config_path)
        ui_integration = integrate_ui_with_bot(bot)
        
        # In run loop, after run_once()
        results = bot.run_once()
        ui_integration.after_run_once(results)
    """
    integration = BotUIIntegration(bot_instance)
    integration.start()
    return integration

