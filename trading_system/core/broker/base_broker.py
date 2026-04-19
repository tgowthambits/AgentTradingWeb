"""
Base Broker Interface

Defines the contract that all broker implementations must follow.
This allows seamless switching between paper trading and live trading.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import uuid


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "PENDING"           # Order submitted, awaiting confirmation
    OPEN = "OPEN"                 # Order confirmed, position is open
    PARTIALLY_FILLED = "PARTIALLY_FILLED"  # Partially executed
    FILLED = "FILLED"             # Fully executed
    CANCELLED = "CANCELLED"       # Order cancelled
    REJECTED = "REJECTED"         # Order rejected by broker
    CLOSED = "CLOSED"             # Position closed


class OrderType(Enum):
    """Order type enumeration."""
    MARKET = "MARKET"             # Market order - execute at current price
    LIMIT = "LIMIT"               # Limit order - execute at specified price or better
    STOP_LOSS = "STOP_LOSS"       # Stop loss order
    STOP_LIMIT = "STOP_LIMIT"     # Stop limit order
    BRACKET = "BRACKET"           # Bracket order with target and stop loss


class OrderSide(Enum):
    """Order side enumeration."""
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class BrokerOrder:
    """
    Represents an order in the broker system.
    
    This is the standardized order format used across all broker implementations.
    """
    order_id: str                           # Unique order ID (internal)
    broker_order_id: Optional[str] = None   # Broker's order ID (from API)
    symbol: str = ""                        # Trading symbol
    side: OrderSide = OrderSide.BUY         # BUY or SELL
    order_type: OrderType = OrderType.MARKET
    quantity: int = 0                       # Order quantity
    price: float = 0.0                      # Limit price (for limit orders)
    trigger_price: float = 0.0              # Trigger price (for stop orders)
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0                # Quantity filled so far
    average_price: float = 0.0              # Average fill price
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    executed_at: Optional[datetime] = None  # When order was executed
    exchange: str = ""                      # Exchange (NSE, BSE, etc.)
    product_type: str = "INTRADAY"          # INTRADAY, DELIVERY, etc.
    validity: str = "DAY"                   # DAY, IOC, GTC
    tag: str = ""                           # Custom tag for tracking
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional data
    error_message: str = ""                 # Error message if rejected
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert order to dictionary."""
        return {
            'order_id': self.order_id,
            'broker_order_id': self.broker_order_id,
            'symbol': self.symbol,
            'side': self.side.value,
            'order_type': self.order_type.value,
            'quantity': self.quantity,
            'price': self.price,
            'trigger_price': self.trigger_price,
            'status': self.status.value,
            'filled_quantity': self.filled_quantity,
            'average_price': self.average_price,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'exchange': self.exchange,
            'product_type': self.product_type,
            'validity': self.validity,
            'tag': self.tag,
            'metadata': self.metadata,
            'error_message': self.error_message
        }


class BaseBroker(ABC):
    """
    Abstract base class for all broker implementations.
    
    This defines the interface that all brokers must implement.
    Allows seamless switching between paper and live trading.
    
    Usage:
        broker = PaperBroker(config)  # or LiveBroker(config)
        order = broker.place_order(symbol, OrderSide.BUY, quantity, price)
        broker.modify_order(order.order_id, new_quantity=100)
        broker.cancel_order(order.order_id)
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the broker.
        
        Args:
            config: Broker configuration dictionary
        """
        self.config = config or {}
        self.orders: Dict[str, BrokerOrder] = {}  # order_id -> BrokerOrder
        self.positions: Dict[str, Dict[str, Any]] = {}  # symbol -> position data
        self._callbacks: Dict[str, List[Callable]] = {
            'on_order_update': [],
            'on_position_update': [],
            'on_error': []
        }
        self._is_connected = False
    
    # ==================== Connection Methods ====================
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Connect to the broker API.
        
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        Disconnect from the broker API.
        
        Returns:
            True if disconnection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if connected to the broker.
        
        Returns:
            True if connected, False otherwise
        """
        pass
    
    # ==================== Order Methods ====================
    
    @abstractmethod
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
        Place a new order.
        
        Args:
            symbol: Trading symbol (e.g., "NSE:NIFTY26JAN25150CE")
            side: BUY or SELL
            quantity: Order quantity
            price: Limit price (0 for market orders)
            order_type: MARKET, LIMIT, STOP_LOSS, etc.
            product_type: INTRADAY, DELIVERY, etc.
            trigger_price: Trigger price for stop orders
            tag: Custom tag for tracking
            metadata: Additional metadata
            
        Returns:
            BrokerOrder object with order details
        """
        pass
    
    @abstractmethod
    def modify_order(
        self,
        order_id: str,
        quantity: int = None,
        price: float = None,
        trigger_price: float = None,
        order_type: OrderType = None
    ) -> BrokerOrder:
        """
        Modify an existing order.
        
        Args:
            order_id: Order ID to modify
            quantity: New quantity (optional)
            price: New price (optional)
            trigger_price: New trigger price (optional)
            order_type: New order type (optional)
            
        Returns:
            Updated BrokerOrder object
        """
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if cancellation successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_order(self, order_id: str) -> Optional[BrokerOrder]:
        """
        Get order details.
        
        Args:
            order_id: Order ID
            
        Returns:
            BrokerOrder object or None if not found
        """
        pass
    
    @abstractmethod
    def get_orders(self, status: OrderStatus = None) -> List[BrokerOrder]:
        """
        Get all orders, optionally filtered by status.
        
        Args:
            status: Filter by order status (optional)
            
        Returns:
            List of BrokerOrder objects
        """
        pass
    
    # ==================== Position Methods ====================
    
    @abstractmethod
    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all open positions.
        
        Returns:
            Dictionary of symbol -> position data
        """
        pass
    
    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get position for a specific symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Position data dictionary or None if no position
        """
        pass
    
    @abstractmethod
    def close_position(
        self,
        symbol: str,
        quantity: int = None,
        price: float = 0.0,
        order_type: OrderType = OrderType.MARKET
    ) -> BrokerOrder:
        """
        Close a position (fully or partially).
        
        Args:
            symbol: Symbol to close
            quantity: Quantity to close (None = full position)
            price: Exit price (0 for market)
            order_type: MARKET or LIMIT
            
        Returns:
            BrokerOrder object for the closing order
        """
        pass
    
    # ==================== Account Methods ====================
    
    @abstractmethod
    def get_funds(self) -> Dict[str, float]:
        """
        Get account funds/margins.
        
        Returns:
            Dictionary with fund details (available, used, total)
        """
        pass
    
    @abstractmethod
    def get_margins(self) -> Dict[str, float]:
        """
        Get margin details.
        
        Returns:
            Dictionary with margin details
        """
        pass
    
    # ==================== Market Data Methods ====================
    
    @abstractmethod
    def get_ltp(self, symbol: str) -> float:
        """
        Get Last Traded Price for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Last traded price
        """
        pass
    
    @abstractmethod
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get full quote data for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Quote data dictionary
        """
        pass
    
    # ==================== Callback Methods ====================
    
    def register_callback(self, event: str, callback: Callable):
        """
        Register a callback for broker events.
        
        Args:
            event: Event type ('on_order_update', 'on_position_update', 'on_error')
            callback: Callback function
        """
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def _trigger_callback(self, event: str, *args, **kwargs):
        """Trigger callbacks for an event."""
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    print(f"Callback error: {e}")
    
    # ==================== Utility Methods ====================
    
    def generate_order_id(self) -> str:
        """Generate a unique order ID."""
        return str(uuid.uuid4())[:8].upper()
    
    def parse_symbol(self, symbol: str) -> Dict[str, str]:
        """
        Parse symbol into components.
        
        Args:
            symbol: Full symbol (e.g., "NSE:NIFTY26JAN25150CE")
            
        Returns:
            Dictionary with exchange, tradingsymbol, etc.
        """
        if ':' in symbol:
            exchange, tradingsymbol = symbol.split(':', 1)
        else:
            exchange = "NSE"
            tradingsymbol = symbol
        
        return {
            'exchange': exchange,
            'tradingsymbol': tradingsymbol,
            'full_symbol': symbol
        }
