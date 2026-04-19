"""
Paper Broker Implementation

Simulates broker operations for paper trading / backtesting.
No actual orders are placed - all operations are simulated locally.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from .base_broker import (
    BaseBroker, BrokerOrder, OrderStatus, OrderType, OrderSide
)
import logfire

# Configure Logfire
logfire.configure()


class PaperBroker(BaseBroker):
    """
    Paper trading broker implementation.
    
    Simulates all broker operations locally without connecting to any API.
    Useful for testing strategies and paper trading.
    
    Features:
    - Simulated order execution
    - Position tracking
    - Simulated funds management
    - Slippage simulation (configurable)
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize paper broker.
        
        Args:
            config: Configuration with options:
                - initial_capital: Starting capital (default: 500000)
                - slippage_pct: Slippage percentage (default: 0.0)
                - execution_delay_ms: Simulated delay (default: 0)
        """
        super().__init__(config)
        
        # Paper trading specific settings
        self.initial_capital = config.get('initial_capital', 500000.0) if config else 500000.0
        self.available_capital = self.initial_capital
        self.used_margin = 0.0
        self.slippage_pct = config.get('slippage_pct', 0.0) if config else 0.0
        
        # Price cache for simulation
        self._price_cache: Dict[str, float] = {}
        
        # Order counter for sequential IDs
        self._order_counter = 0
        
        self._is_connected = True  # Always "connected" for paper trading
        
        print(f"📝 Paper Broker initialized with ₹{self.initial_capital:,.2f} capital")
        
        # Log broker initialization
        logfire.info(
            'Paper Broker initialized',
            initial_capital=self.initial_capital,
            slippage_pct=self.slippage_pct,
            broker_type='paper'
        )
    
    # ==================== Connection Methods ====================
    
    def connect(self) -> bool:
        """Paper broker is always connected."""
        self._is_connected = True
        print("📝 Paper Broker: Connected (simulation mode)")
        return True
    
    def disconnect(self) -> bool:
        """Paper broker disconnection."""
        self._is_connected = False
        print("📝 Paper Broker: Disconnected")
        return True
    
    def is_connected(self) -> bool:
        """Check connection status."""
        return self._is_connected
    
    # ==================== Order Methods ====================
    
    def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        price: float = 0.0,
        order_type: OrderType = OrderType.MARKET,
        product_type: str = "INTRADAY",
        trigger_price: float = 0.0,
        tag: str = "",
        metadata: Dict[str, Any] = None
    ) -> BrokerOrder:
        """
        Place a simulated order.
        
        For market orders, executes immediately at cached price.
        For limit orders, stores as pending (would need price updates to fill).
        """
        self._order_counter += 1
        order_id = f"PAPER_{self._order_counter:06d}"
        
        # Parse symbol for exchange
        symbol_parts = self.parse_symbol(symbol)
        
            # Get execution price
        slippage_applied = False
        if order_type == OrderType.MARKET:
            # Use cached price or provided price
            exec_price = self._price_cache.get(symbol, price)
            if exec_price == 0:
                exec_price = price
            
            # Apply slippage for market orders
            if self.slippage_pct > 0:
                if side == OrderSide.BUY:
                    exec_price *= (1 + self.slippage_pct / 100)
                else:
                    exec_price *= (1 - self.slippage_pct / 100)
                slippage_applied = True
        else:
            exec_price = price
        
        # Create order
        order = BrokerOrder(
            order_id=order_id,
            broker_order_id=order_id,  # Same for paper trading
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            trigger_price=trigger_price,
            exchange=symbol_parts['exchange'],
            product_type=product_type,
            tag=tag,
            metadata=metadata or {}
        )
        
        # For market orders, execute immediately
        if order_type == OrderType.MARKET:
            order.status = OrderStatus.FILLED
            order.filled_quantity = quantity
            order.average_price = exec_price
            order.executed_at = datetime.now()
            
            # Calculate order value
            order_value = exec_price * quantity
            
            # Update position
            self._update_position(symbol, side, quantity, exec_price)
            
            # Update capital
            if side == OrderSide.BUY:
                required_margin = exec_price * quantity
                self.available_capital -= required_margin
                self.used_margin += required_margin
            
            print(f"📝 Paper Order FILLED: {side.value} {quantity} {symbol} @ ₹{exec_price:.2f} [Order: {order_id}]")
            
            # Log order execution with Logfire - Different logging for BUY vs SELL
            order_details = {
                'order_id': order_id,
                'symbol': symbol,
                'side': side.value,
                'order_type': order_type.value,
                'quantity': quantity,
                'order_value': order_value,
                'product_type': product_type,
                'tag': tag,
                'slippage_applied': slippage_applied,
                'slippage_pct': self.slippage_pct if slippage_applied else None,
                'available_capital': self.available_capital,
                'used_margin': self.used_margin,
                'timestamp': order.executed_at.isoformat() if order.executed_at else None
            }
            
            if side == OrderSide.BUY:
                # BUY orders - use warn level for visibility (same as SELL) but with green attributes
                # Log BUY order separately and prominently with all details
                # Add tag: buy_{symbol}
                buy_tag = f'buy_{symbol}'
                logfire.info(
                    f'📈 Paper Broker BUY Order Executed: {quantity} {symbol} @ ₹{exec_price:.2f}',
                    order_type='BUY',
                    order_color='green',
                    order_action='ENTRY',
                    entry_price=exec_price,  # Entry price for buy orders
                    quantity=quantity,
                    symbol=symbol,
                    order_value=order_value,
                    order_id=order_id,
                    product_type=product_type,
                    tag=tag,
                    logfire_tag=buy_tag,  # Tag for filtering: buy_{symbol}
                    slippage_applied=slippage_applied,
                    slippage_pct=self.slippage_pct if slippage_applied else None,
                    available_capital=self.available_capital,
                    used_margin=self.used_margin,
                    timestamp=order.executed_at.isoformat() if order.executed_at else None
                )
            else:
                # SELL orders - use warn level with red/negative attributes for visibility
                # Make message descriptive with quantity and price
                # Add tag: sell_{symbol}
                sell_tag = f'sell_{symbol}'
                logfire.warn(
                    f'📉 Paper Broker SELL Order Executed: {quantity} {symbol} @ ₹{exec_price:.2f}',
                    order_type='SELL',
                    order_color='red',
                    order_action='EXIT',
                    exit_price=exec_price,  # Explicitly mark as exit price for sell orders
                    quantity=quantity,
                    symbol=symbol,
                    order_value=order_value,
                    order_id=order_id,
                    product_type=product_type,
                    tag=tag,
                    logfire_tag=sell_tag,  # Tag for filtering: sell_{symbol}
                    slippage_applied=slippage_applied,
                    slippage_pct=self.slippage_pct if slippage_applied else None,
                    available_capital=self.available_capital,
                    used_margin=self.used_margin,
                    timestamp=order.executed_at.isoformat() if order.executed_at else None
                )
        else:
            # Limit/Stop orders stay pending
            order.status = OrderStatus.PENDING
            print(f"📝 Paper Order PENDING: {side.value} {quantity} {symbol} @ ₹{price:.2f} [Order: {order_id}]")
            
            # Log pending order
            logfire.info(
                'Paper Broker Order Pending',
                order_id=order_id,
                symbol=symbol,
                side=side.value,
                quantity=quantity,
                limit_price=price,
                trigger_price=trigger_price if trigger_price > 0 else None,
                order_type=order_type.value,
                product_type=product_type,
                tag=tag
            )
        
        order.updated_at = datetime.now()
        self.orders[order_id] = order
        
        # Trigger callback
        self._trigger_callback('on_order_update', order)
        
        return order
    
    def modify_order(
        self,
        order_id: str,
        quantity: int = None,
        price: float = None,
        trigger_price: float = None,
        order_type: OrderType = None
    ) -> BrokerOrder:
        """Modify a pending order."""
        if order_id not in self.orders:
            raise ValueError(f"Order {order_id} not found")
        
        order = self.orders[order_id]
        
        if order.status not in [OrderStatus.PENDING, OrderStatus.OPEN]:
            raise ValueError(f"Cannot modify order in {order.status.value} status")
        
        if quantity is not None:
            order.quantity = quantity
        if price is not None:
            order.price = price
        if trigger_price is not None:
            order.trigger_price = trigger_price
        if order_type is not None:
            order.order_type = order_type
        
        order.updated_at = datetime.now()
        
        print(f"📝 Paper Order MODIFIED: {order_id}")
        
        # Log order modification
        logfire.info(
            'Paper Broker Order Modified',
            order_id=order_id,
            symbol=order.symbol,
            new_quantity=quantity if quantity is not None else order.quantity,
            new_price=price if price is not None else order.price,
            new_trigger_price=trigger_price if trigger_price is not None else order.trigger_price,
            new_order_type=order_type.value if order_type is not None else order.order_type.value
        )
        
        self._trigger_callback('on_order_update', order)
        
        return order
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        if order_id not in self.orders:
            return False
        
        order = self.orders[order_id]
        
        if order.status not in [OrderStatus.PENDING, OrderStatus.OPEN]:
            return False
        
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now()
        
        print(f"📝 Paper Order CANCELLED: {order_id}")
        
        # Log order cancellation
        logfire.info(
            'Paper Broker Order Cancelled',
            order_id=order_id,
            symbol=order.symbol,
            side=order.side.value,
            quantity=order.quantity,
            order_type=order.order_type.value
        )
        
        self._trigger_callback('on_order_update', order)
        
        return True
    
    def get_order(self, order_id: str) -> Optional[BrokerOrder]:
        """Get order by ID."""
        return self.orders.get(order_id)
    
    def get_orders(self, status: OrderStatus = None) -> List[BrokerOrder]:
        """Get all orders, optionally filtered by status."""
        if status is None:
            return list(self.orders.values())
        return [o for o in self.orders.values() if o.status == status]
    
    # ==================== Position Methods ====================
    
    def _update_position(self, symbol: str, side: OrderSide, quantity: int, price: float):
        """Update position after order execution."""
        if symbol not in self.positions:
            self.positions[symbol] = {
                'symbol': symbol,
                'quantity': 0,
                'average_price': 0.0,
                'side': None,
                'pnl': 0.0,
                'unrealized_pnl': 0.0
            }
        
        pos = self.positions[symbol]
        
        # Store previous position state for logging
        prev_quantity = pos['quantity']
        prev_avg_price = pos['average_price']
        prev_side = pos.get('side')
        
        if side == OrderSide.BUY:
            if pos['quantity'] >= 0:
                # Adding to long or opening new long
                total_cost = (pos['quantity'] * pos['average_price']) + (quantity * price)
                pos['quantity'] += quantity
                pos['average_price'] = total_cost / pos['quantity'] if pos['quantity'] > 0 else 0
                pos['side'] = 'LONG'
            else:
                # Closing short position
                pos['quantity'] += quantity
                if pos['quantity'] == 0:
                    # Calculate PnL for closed position
                    pnl = (prev_avg_price - price) * abs(prev_quantity)  # Short position PnL
                    pnl_pct = (pnl / (prev_avg_price * abs(prev_quantity))) * 100 if prev_avg_price > 0 else 0
                    
                    # Log position close with exit price - use warn for visibility
                    logfire.warn(
                        f'📉 Paper Broker Position CLOSED (SHORT): {abs(prev_quantity)} {symbol} | Entry: ₹{prev_avg_price:.2f} | Exit: ₹{price:.2f} | PnL: ₹{pnl:.2f} ({pnl_pct:.2f}%)',
                        order_type='SELL',
                        order_color='red',
                        symbol=symbol,
                        side='SHORT',
                        entry_price=prev_avg_price,
                        exit_price=price,
                        quantity=abs(prev_quantity),
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        is_profit=pnl > 0,
                        trade_value=prev_avg_price * abs(prev_quantity)
                    )
                    del self.positions[symbol]
                    return
        else:  # SELL
            if pos['quantity'] <= 0:
                # Adding to short or opening new short
                total_cost = (abs(pos['quantity']) * pos['average_price']) + (quantity * price)
                pos['quantity'] -= quantity
                pos['average_price'] = total_cost / abs(pos['quantity']) if pos['quantity'] != 0 else 0
                pos['side'] = 'SHORT'
            else:
                # Closing long position
                pos['quantity'] -= quantity
                if pos['quantity'] == 0:
                    # Calculate PnL for closed position
                    pnl = (price - prev_avg_price) * prev_quantity  # Long position PnL
                    pnl_pct = (pnl / (prev_avg_price * prev_quantity)) * 100 if prev_avg_price > 0 else 0
                    
                    # Log position close with exit price - use warn for visibility
                    logfire.warn(
                        f'📉 Paper Broker Position CLOSED (LONG): {prev_quantity} {symbol} | Entry: ₹{prev_avg_price:.2f} | Exit: ₹{price:.2f} | PnL: ₹{pnl:.2f} ({pnl_pct:.2f}%)',
                        order_type='SELL',
                        order_color='red',
                        symbol=symbol,
                        side='LONG',
                        entry_price=prev_avg_price,
                        exit_price=price,
                        quantity=prev_quantity,
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        is_profit=pnl > 0,
                        trade_value=prev_avg_price * prev_quantity
                    )
                    del self.positions[symbol]
                    return
        
            # Log position update with detailed info
            logfire.info(
                'Paper Broker Position Updated',
                symbol=symbol,
                side=pos['side'],
                quantity=pos['quantity'],
                average_price=pos['average_price'],
                previous_quantity=prev_quantity,
                previous_avg_price=prev_avg_price,
                trade_quantity=quantity,
                trade_price=price,
                position_value=pos['quantity'] * pos['average_price'],
                order_side=side.value
            )
        
        self._trigger_callback('on_position_update', symbol, pos)
    
    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """Get all open positions."""
        return self.positions.copy()
    
    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get position for a symbol."""
        return self.positions.get(symbol)
    
    def close_position(
        self,
        symbol: str,
        quantity: int = None,
        price: float = 0.0,
        order_type: OrderType = OrderType.MARKET
    ) -> BrokerOrder:
        """Close a position."""
        if symbol not in self.positions:
            raise ValueError(f"No position for {symbol}")
        
        pos = self.positions[symbol]
        close_qty = quantity if quantity else abs(pos['quantity'])
        
        # Determine side for closing order
        if pos['quantity'] > 0:
            side = OrderSide.SELL  # Close long
        else:
            side = OrderSide.BUY   # Close short
        
        # Place closing order
        order = self.place_order(
            symbol=symbol,
            side=side,
            quantity=close_qty,
            price=price,
            order_type=order_type,
            tag="CLOSE_POSITION"
        )
        
        # Release margin
        if order.status == OrderStatus.FILLED:
            released_margin = order.average_price * close_qty
            self.available_capital += released_margin
            self.used_margin -= released_margin
            
            # Calculate PnL for closed position
            entry_price = pos['average_price']
            exit_price = order.average_price
            if pos['side'] == 'LONG':
                pnl = (exit_price - entry_price) * close_qty
            else:  # SHORT
                pnl = (entry_price - exit_price) * close_qty
            
            pnl_pct = (pnl / (entry_price * close_qty)) * 100 if entry_price > 0 else 0
            
            # Log position close with exit price - use warn for visibility
            logfire.warn(
                f'📉 Paper Broker Position CLOSED: {close_qty} {symbol} | Entry: ₹{entry_price:.2f} | Exit: ₹{exit_price:.2f} | PnL: ₹{pnl:.2f} ({pnl_pct:.2f}%)',
                order_type='SELL',
                order_color='red',
                symbol=symbol,
                side=pos['side'],
                entry_price=entry_price,
                exit_price=exit_price,
                quantity=close_qty,
                pnl=pnl,
                pnl_pct=pnl_pct,
                is_profit=pnl > 0,
                trade_value=entry_price * close_qty,
                released_margin=released_margin,
                available_capital=self.available_capital,
                used_margin=self.used_margin
            )
        
        return order
    
    # ==================== Account Methods ====================
    
    def get_funds(self) -> Dict[str, float]:
        """Get account funds."""
        return {
            'available': self.available_capital,
            'used': self.used_margin,
            'total': self.available_capital + self.used_margin
        }
    
    def get_margins(self) -> Dict[str, float]:
        """Get margin details."""
        return {
            'available_margin': self.available_capital,
            'used_margin': self.used_margin,
            'total_margin': self.initial_capital
        }
    
    # ==================== Market Data Methods ====================
    
    def set_price(self, symbol: str, price: float):
        """
        Set/update cached price for a symbol.
        
        Call this to update prices for the paper broker.
        """
        self._price_cache[symbol] = price
    
    def get_ltp(self, symbol: str) -> float:
        """Get last traded price from cache."""
        return self._price_cache.get(symbol, 0.0)
    
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Get quote data (simplified for paper trading)."""
        ltp = self._price_cache.get(symbol, 0.0)
        return {
            'symbol': symbol,
            'ltp': ltp,
            'bid': ltp * 0.9999,  # Simulated bid
            'ask': ltp * 1.0001,  # Simulated ask
            'volume': 0,
            'timestamp': datetime.now().isoformat()
        }
    
    # ==================== Paper Trading Specific ====================
    
    def reset(self):
        """Reset paper broker to initial state."""
        # Log reset event
        logfire.info(
            'Paper Broker Reset',
            orders_before_reset=len(self.orders),
            positions_before_reset=len(self.positions),
            capital_before_reset=self.available_capital + self.used_margin,
            initial_capital=self.initial_capital
        )
        
        self.orders.clear()
        self.positions.clear()
        self.available_capital = self.initial_capital
        self.used_margin = 0.0
        self._order_counter = 0
        self._price_cache.clear()
        print(f"📝 Paper Broker RESET: Capital restored to ₹{self.initial_capital:,.2f}")
    
    def get_trade_history(self) -> List[Dict[str, Any]]:
        """Get history of all trades."""
        filled_orders = [o.to_dict() for o in self.orders.values() 
                        if o.status == OrderStatus.FILLED]
        
        # Log trade history summary
        if filled_orders:
            total_trades = len(filled_orders)
            buy_orders = [o for o in filled_orders if o.get('side') == 'BUY']
            sell_orders = [o for o in filled_orders if o.get('side') == 'SELL']
            
            logfire.info(
                'Paper Broker Trade History Summary',
                total_trades=total_trades,
                buy_orders=len(buy_orders),
                sell_orders=len(sell_orders),
                trades=filled_orders
            )
        
        return filled_orders
    
    def calculate_pnl(self) -> Dict[str, float]:
        """Calculate total PnL."""
        realized_pnl = 0.0
        unrealized_pnl = 0.0
        
        # Calculate realized PnL from closed orders
        for order in self.orders.values():
            if order.status == OrderStatus.FILLED and order.side == OrderSide.SELL:
                # Find corresponding buy order or calculate from position
                # For simplicity, we'll track from positions
                pass
        
        # For positions, calculate unrealized PnL
        position_details = []
        for symbol, pos in self.positions.items():
            ltp = self._price_cache.get(symbol, pos['average_price'])
            if pos['quantity'] > 0:  # Long
                pos_pnl = (ltp - pos['average_price']) * pos['quantity']
                unrealized_pnl += pos_pnl
            else:  # Short
                pos_pnl = (pos['average_price'] - ltp) * abs(pos['quantity'])
                unrealized_pnl += pos_pnl
            
            position_details.append({
                'symbol': symbol,
                'side': pos.get('side', 'UNKNOWN'),
                'quantity': abs(pos['quantity']),
                'entry_price': pos['average_price'],
                'current_price': ltp,
                'unrealized_pnl': pos_pnl
            })
        
        total_pnl = realized_pnl + unrealized_pnl
        current_capital = self.available_capital + self.used_margin
        total_return_pct = ((current_capital - self.initial_capital) / self.initial_capital) * 100 if self.initial_capital > 0 else 0
        
        # Log PnL summary
        logfire.info(
            'Paper Broker PnL Summary',
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            total_pnl=total_pnl,
            initial_capital=self.initial_capital,
            current_capital=current_capital,
            available_capital=self.available_capital,
            used_margin=self.used_margin,
            total_return_pct=total_return_pct,
            open_positions=len(self.positions),
            position_details=position_details
        )
        
        return {
            'realized_pnl': realized_pnl,
            'unrealized_pnl': unrealized_pnl,
            'total_pnl': total_pnl,
            'capital': current_capital,
            'total_return_pct': total_return_pct
        }
