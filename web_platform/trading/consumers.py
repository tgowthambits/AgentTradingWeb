import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger("trading.consumers")


class BacktestConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time backtest progress updates."""

    async def connect(self):
        self.run_id = self.scope["url_route"]["kwargs"]["run_id"]
        self.group_name = f"backtest_{self.run_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self.send(text_data=json.dumps({
            "type": "connected",
            "run_id": int(self.run_id),
            "message": "Connected to backtest stream",
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        pass

    async def broadcast_message(self, event):
        await self.send(text_data=json.dumps(event["data"]))


class LiveTradingConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time live trading updates."""

    async def connect(self):
        self.session_id = self.scope["url_route"]["kwargs"]["session_id"]
        self.group_name = f"live_{self.session_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self.send(text_data=json.dumps({
            "type": "connected",
            "session_id": int(self.session_id),
            "message": "Connected to live trading stream",
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        pass

    async def broadcast_message(self, event):
        await self.send(text_data=json.dumps(event["data"]))
