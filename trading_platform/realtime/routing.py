"""
WebSocket URL routing for realtime app.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/trading/$", consumers.TradingConsumer.as_asgi()),
    re_path(r"ws/backtest/$", consumers.BacktestConsumer.as_asgi()),
    re_path(r"ws/market/$", consumers.MarketDataConsumer.as_asgi()),
]
