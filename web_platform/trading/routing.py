from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/backtest/(?P<run_id>\d+)/$", consumers.BacktestConsumer.as_asgi()),
    re_path(r"ws/live/(?P<session_id>\d+)/$", consumers.LiveTradingConsumer.as_asgi()),
]
