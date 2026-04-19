from django.urls import path
from .api import api
from . import views

urlpatterns = [
    path("api/", api.urls),
    path("", views.dashboard, name="dashboard"),
    path("backtest/", views.backtest_page, name="backtest"),
    path("backtest/results/", views.backtest_results_page, name="backtest_results"),
    path("backtest/results/<int:run_id>/", views.backtest_detail_page, name="backtest_detail"),
    path("live/", views.live_trading_page, name="live_trading"),
    path("live/sessions/", views.live_sessions_page, name="live_sessions"),
    path("live/sessions/<int:session_id>/", views.live_session_detail_page, name="live_session_detail"),
    path("config/", views.config_page, name="config"),
]
