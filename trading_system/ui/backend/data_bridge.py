"""
Data Bridge - Connects Trading Bot to Web UI
Handles real-time data broadcasting without modifying bot logic
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from collections import deque
import threading
import pandas as pd


class DataBridge:
    """
    Central hub for bot-to-UI data communication.
    Thread-safe singleton that stores latest data and broadcasts updates.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        
        # Current state
        self.bot_status = {
            'running': False,
            'auto_trade': False,
            'allow_buy': True,
            'allow_sell': True,
            'refresh_count': 0,
            'last_update': None,
            'uptime_seconds': 0
        }
        
        # Latest analysis results for all symbols
        self.symbol_data = {}
        
        # OHLCV data for charts (keep last 500 candles per symbol)
        self.chart_data = {}
        self.max_candles = 500
        
        # Performance metrics
        self.performance = {
            'total_pnl': 0.0,
            'realized_pnl': 0.0,
            'unrealized_pnl': 0.0,
            'total_trades': 0,
            'win_trades': 0,
            'loss_trades': 0,
            'win_rate': 0.0,
            'best_trade': 0.0,
            'worst_trade': 0.0
        }
        
        # Open positions and closed orders
        self.open_positions = []
        self.closed_orders = []
        
        # Active indicators
        self.indicators = []
        
        # WebSocket connections
        self.connections: List[Any] = []
        
        # Event history (last 100 events)
        self.events = deque(maxlen=100)
        
        # Backtest state
        self.backtest_active = False
        self.backtest_data = {
            'status': 'idle',  # idle, running, completed, error
            'progress': 0,
            'total_iterations': 0,
            'current_iteration': 0,
            'initial_capital': 0,
            'current_capital': 0,
            'total_pnl': 0,
            'returns_pct': 0,
            'total_trades': 0,
            'real_trades': 0,
            'paper_trades': 0,
            'win_rate': 0,
            'circuit_breaker_active': False,
            'consecutive_losses': 0,
            'last_trade': None,
            'trades_list': [],
            'metrics': {},
            'start_time': None,
            'end_time': None,
            'symbols_ltp': {}
        }
        
        print("✅ DataBridge initialized")
    
    # ========== Bot Update Methods ==========
    
    def update_bot_status(self, status: Dict[str, Any]):
        """Update bot status information."""
        self.bot_status.update(status)
        self.bot_status['last_update'] = datetime.now().isoformat()
        self._log_event('bot_status', 'Bot status updated')
    
    def update_symbol_analysis(self, symbol: str, data: Dict[str, Any]):
        """Update analysis results for a symbol."""
        self.symbol_data[symbol] = {
            **data,
            'timestamp': datetime.now().isoformat()
        }
        self._log_event('analysis', f'Analysis updated for {symbol}')
    
    def update_chart_data(self, symbol: str, df):
        """Update OHLCV data for charting."""
        try:
            # Keep only last N candles for performance
            if len(df) > self.max_candles:
                df = df.tail(self.max_candles)
            
            # Convert to JSON-serializable format
            chart_json = []
            for idx, row in df.iterrows():
                # Handle both datetime and integer indices
                if hasattr(idx, 'timestamp'):
                    time_val = int(idx.timestamp())
                elif isinstance(idx, (int, float)):
                    time_val = int(idx)
                else:
                    # Try to convert to timestamp
                    try:
                        time_val = int(pd.to_datetime(idx).timestamp())
                    except:
                        time_val = int(datetime.now().timestamp())
                
                chart_json.append({
                    'time': time_val,
                    'open': float(row.get('open', 0)),
                    'high': float(row.get('high', 0)),
                    'low': float(row.get('low', 0)),
                    'close': float(row.get('close', 0)),
                    'volume': float(row.get('volume', 0))
                })
            
            self.chart_data[symbol] = chart_json
            self._log_event('chart', f'Chart data updated for {symbol} ({len(chart_json)} candles)')
        except Exception as e:
            print(f"Error updating chart data: {e}")
    
    def update_performance(self, metrics: Dict[str, Any]):
        """Update performance metrics."""
        self.performance.update(metrics)
        self._log_event('performance', 'Performance metrics updated')
    
    def update_positions(self, open_positions: List[Dict], closed_orders: List[Dict]):
        """Update open positions and closed orders."""
        self.open_positions = open_positions
        self.closed_orders = closed_orders[-50:]  # Keep last 50 closed orders
        self._log_event('positions', f'{len(open_positions)} open, {len(closed_orders)} closed')
    
    def set_indicators(self, indicators: List[Dict[str, Any]]):
        """Set active indicators list."""
        self.indicators = indicators
        self._log_event('indicators', f'{len(indicators)} indicators configured')
    
    def add_trade_event(self, event_type: str, symbol: str, details: Dict[str, Any]):
        """Log a trade event."""
        self._log_event(event_type, f"{symbol}: {details.get('action', 'N/A')}")
    
    # ========== WebSocket Management ==========
    
    def register_connection(self, websocket):
        """Register a new WebSocket connection."""
        self.connections.append(websocket)
        print(f"✅ WebSocket connected. Total: {len(self.connections)}")
    
    def unregister_connection(self, websocket):
        """Unregister a WebSocket connection."""
        if websocket in self.connections:
            self.connections.remove(websocket)
        print(f"❌ WebSocket disconnected. Total: {len(self.connections)}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected WebSocket clients."""
        if not self.connections:
            return
        
        message_json = json.dumps(message, default=str)
        disconnected = []
        
        for connection in self.connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                print(f"Error broadcasting to client: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.unregister_connection(conn)
    
    def broadcast_sync(self, message: Dict[str, Any]):
        """
        Synchronous broadcast - for use in non-async bot code.
        Creates a new event loop if needed.
        """
        if not self.connections:
            return
        
        try:
            # Try to get the running loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Schedule the coroutine
                asyncio.create_task(self.broadcast(message))
            else:
                # Run in new loop
                loop.run_until_complete(self.broadcast(message))
        except RuntimeError:
            # No event loop, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.broadcast(message))
            loop.close()
    
    # ========== Data Retrieval Methods ==========
    
    def get_full_state(self) -> Dict[str, Any]:
        """Get complete current state for new connections."""
        return {
            'type': 'full_state',
            'data': {
                'bot_status': self.bot_status,
                'symbols': self.symbol_data,
                'performance': self.performance,
                'open_positions': self.open_positions,
                'closed_orders': self.closed_orders,
                'indicators': self.indicators,
                'events': list(self.events)[-20:]  # Last 20 events
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def get_chart_data(self, symbol: str) -> List[Dict]:
        """Get chart data for a specific symbol."""
        return self.chart_data.get(symbol, [])
    
    def get_symbols(self) -> List[str]:
        """Get list of active symbols."""
        return list(self.symbol_data.keys())
    
    # ========== Backtest Methods ==========
    
    def start_backtest(self, initial_capital: float, total_iterations: int = 0):
        """Initialize backtest state."""
        self.backtest_active = True
        self.backtest_data = {
            'status': 'running',
            'progress': 0,
            'total_iterations': total_iterations,
            'current_iteration': 0,
            'initial_capital': initial_capital,
            'current_capital': initial_capital,
            'total_pnl': 0,
            'returns_pct': 0,
            'total_trades': 0,
            'real_trades': 0,
            'paper_trades': 0,
            'win_rate': 0,
            'circuit_breaker_active': False,
            'consecutive_losses': 0,
            'last_trade': None,
            'trades_list': [],
            'metrics': {},
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'symbols_ltp': {}
        }
        self._log_event('backtest', 'Backtest started')
    
    def update_backtest(self, iteration: int = None, trade_data: Dict = None, summary: Dict = None, all_trades: List[Dict] = None, symbols_ltp: Dict = None):
        """Update backtest progress and data."""
        if not self.backtest_active:
            return
        
        # Debug logging
        import sys
        print(f"[DataBridge] Updating backtest - iteration: {iteration}, trades: {len(all_trades) if all_trades else 0}", file=sys.stderr, flush=True)
        
        if iteration is not None:
            self.backtest_data['current_iteration'] = iteration
            if self.backtest_data['total_iterations'] > 0:
                self.backtest_data['progress'] = (iteration / self.backtest_data['total_iterations']) * 100
        
        # Update all trades list if provided
        if all_trades is not None:
            self.backtest_data['trades_list'] = all_trades
            self.backtest_data['total_trades'] = len(all_trades)
            # Count real vs paper trades
            self.backtest_data['real_trades'] = len([t for t in all_trades if t.get('mode') == 'REAL'])
            self.backtest_data['paper_trades'] = len([t for t in all_trades if t.get('mode') == 'PAPER'])
        
        if trade_data:
            self.backtest_data['last_trade'] = trade_data
        
        # Update symbols LTP data
        if symbols_ltp:
            self.backtest_data['symbols_ltp'] = symbols_ltp
        
        if summary:
            self.backtest_data['current_capital'] = summary.get('actual_capital', self.backtest_data['initial_capital'])
            self.backtest_data['total_pnl'] = summary.get('total_pnl', 0)
            initial = self.backtest_data['initial_capital']
            if initial > 0:
                self.backtest_data['returns_pct'] = (self.backtest_data['total_pnl'] / initial) * 100
            self.backtest_data['win_rate'] = summary.get('win_rate', 0)
            self.backtest_data['circuit_breaker_active'] = summary.get('paper_trading_mode', False)
            self.backtest_data['consecutive_losses'] = summary.get('consecutive_losses', 0)
            self.backtest_data['metrics'] = summary
    
    def complete_backtest(self, final_summary: Dict = None):
        """Mark backtest as completed."""
        self.backtest_data['status'] = 'completed'
        self.backtest_data['progress'] = 100
        self.backtest_data['end_time'] = datetime.now().isoformat()
        if final_summary:
            self.update_backtest(summary=final_summary)
        self._log_event('backtest', 'Backtest completed')
    
    def error_backtest(self, error_message: str):
        """Mark backtest as errored."""
        self.backtest_data['status'] = 'error'
        self.backtest_data['error'] = error_message
        self.backtest_data['end_time'] = datetime.now().isoformat()
        self._log_event('backtest_error', error_message)
    
    def get_backtest_state(self) -> Dict:
        """Get current backtest state."""
        return {
            'active': self.backtest_active,
            'data': self.backtest_data.copy()
        }
    
    # ========== Internal Methods ==========
    
    def _log_event(self, event_type: str, message: str):
        """Log an event to the history."""
        event = {
            'type': event_type,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        self.events.append(event)


# Global singleton instance
data_bridge = DataBridge()

