"""
WebSocket consumers for real-time trading updates.
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class TradingConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for live trading updates."""

    async def connect(self):
        self.user = self.scope.get("user")

        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        self.user_id = str(self.user.id)
        self.user_group = f"user_{self.user_id}"

        # Join user-specific group
        await self.channel_layer.group_add(self.user_group, self.channel_name)

        await self.accept()

        await self.send(
            text_data=json.dumps(
                {
                    "type": "connection_established",
                    "message": "Connected to trading updates",
                }
            )
        )

    async def disconnect(self, close_code):
        if hasattr(self, "user_group"):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            if message_type == "subscribe_session":
                await self.subscribe_session(data.get("session_id"))
            elif message_type == "unsubscribe_session":
                await self.unsubscribe_session(data.get("session_id"))
            elif message_type == "ping":
                await self.send(text_data=json.dumps({"type": "pong"}))
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")

    async def subscribe_session(self, session_id):
        """Subscribe to a specific trading session's updates."""
        if session_id:
            session_group = f"session_{session_id}"
            await self.channel_layer.group_add(session_group, self.channel_name)
            await self.send(
                text_data=json.dumps({"type": "subscribed", "session_id": session_id})
            )

    async def unsubscribe_session(self, session_id):
        """Unsubscribe from a trading session's updates."""
        if session_id:
            session_group = f"session_{session_id}"
            await self.channel_layer.group_discard(session_group, self.channel_name)

    # Event handlers for group messages
    async def trade_update(self, event):
        """Send trade update to WebSocket."""
        await self.send(
            text_data=json.dumps({"type": "trade_update", "data": event["data"]})
        )

    async def position_update(self, event):
        """Send position update to WebSocket."""
        await self.send(
            text_data=json.dumps({"type": "position_update", "data": event["data"]})
        )

    async def order_update(self, event):
        """Send order update to WebSocket."""
        await self.send(
            text_data=json.dumps({"type": "order_update", "data": event["data"]})
        )

    async def price_update(self, event):
        """Send price update to WebSocket."""
        await self.send(
            text_data=json.dumps({"type": "price_update", "data": event["data"]})
        )

    async def signal_update(self, event):
        """Send signal update to WebSocket."""
        await self.send(
            text_data=json.dumps({"type": "signal_update", "data": event["data"]})
        )


class BacktestConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for backtest progress updates."""

    async def connect(self):
        self.user = self.scope.get("user")

        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        self.user_id = str(self.user.id)
        self.user_group = f"backtest_user_{self.user_id}"

        await self.channel_layer.group_add(self.user_group, self.channel_name)

        await self.accept()

        await self.send(
            text_data=json.dumps(
                {
                    "type": "connection_established",
                    "message": "Connected to backtest updates",
                }
            )
        )

    async def disconnect(self, close_code):
        if hasattr(self, "user_group"):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            if message_type == "subscribe_backtest":
                await self.subscribe_backtest(data.get("session_id"))
            elif message_type == "unsubscribe_backtest":
                await self.unsubscribe_backtest(data.get("session_id"))
            elif message_type == "ping":
                await self.send(text_data=json.dumps({"type": "pong"}))
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")

    async def subscribe_backtest(self, session_id):
        """Subscribe to a specific backtest session's updates."""
        if session_id:
            backtest_group = f"backtest_{session_id}"
            await self.channel_layer.group_add(backtest_group, self.channel_name)
            await self.send(
                text_data=json.dumps({"type": "subscribed", "session_id": session_id})
            )

    async def unsubscribe_backtest(self, session_id):
        """Unsubscribe from a backtest session's updates."""
        if session_id:
            backtest_group = f"backtest_{session_id}"
            await self.channel_layer.group_discard(backtest_group, self.channel_name)

    # Event handlers for group messages
    async def backtest_progress(self, event):
        """Send backtest progress update."""
        await self.send(
            text_data=json.dumps({"type": "backtest_progress", "data": event["data"]})
        )

    async def backtest_trade(self, event):
        """Send backtest trade update."""
        await self.send(
            text_data=json.dumps({"type": "backtest_trade", "data": event["data"]})
        )

    async def backtest_equity(self, event):
        """Send backtest equity update."""
        await self.send(
            text_data=json.dumps({"type": "backtest_equity", "data": event["data"]})
        )

    async def backtest_complete(self, event):
        """Send backtest completion notification."""
        await self.send(
            text_data=json.dumps({"type": "backtest_complete", "data": event["data"]})
        )

    async def backtest_error(self, event):
        """Send backtest error notification."""
        await self.send(
            text_data=json.dumps({"type": "backtest_error", "data": event["data"]})
        )


class MarketDataConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time market data."""

    async def connect(self):
        self.user = self.scope.get("user")

        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        self.subscribed_symbols = set()

        await self.accept()

        await self.send(
            text_data=json.dumps(
                {
                    "type": "connection_established",
                    "message": "Connected to market data",
                }
            )
        )

    async def disconnect(self, close_code):
        # Unsubscribe from all symbols
        for symbol in self.subscribed_symbols:
            await self.channel_layer.group_discard(
                f"market_{symbol}", self.channel_name
            )

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            if message_type == "subscribe":
                symbols = data.get("symbols", [])
                for symbol in symbols:
                    await self.subscribe_symbol(symbol)
            elif message_type == "unsubscribe":
                symbols = data.get("symbols", [])
                for symbol in symbols:
                    await self.unsubscribe_symbol(symbol)
            elif message_type == "ping":
                await self.send(text_data=json.dumps({"type": "pong"}))
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")

    async def subscribe_symbol(self, symbol):
        """Subscribe to a symbol's market data."""
        symbol_group = f"market_{symbol}"
        await self.channel_layer.group_add(symbol_group, self.channel_name)
        self.subscribed_symbols.add(symbol)

        await self.send(text_data=json.dumps({"type": "subscribed", "symbol": symbol}))

    async def unsubscribe_symbol(self, symbol):
        """Unsubscribe from a symbol's market data."""
        symbol_group = f"market_{symbol}"
        await self.channel_layer.group_discard(symbol_group, self.channel_name)
        self.subscribed_symbols.discard(symbol)

    # Event handlers
    async def market_tick(self, event):
        """Send market tick data."""
        await self.send(text_data=json.dumps({"type": "tick", "data": event["data"]}))

    async def market_candle(self, event):
        """Send market candle data."""
        await self.send(text_data=json.dumps({"type": "candle", "data": event["data"]}))
