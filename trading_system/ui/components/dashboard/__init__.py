"""
Dashboard Components Module

Contains dashboard-related classes for KPI tiles, charts, and updates:
- DashboardPanel: KPI tile creation and management
- ChartManager: Chart creation and updates
- DashboardUpdater: Throttled dashboard update handling
"""

from .dashboard_panel import DashboardPanel
from .charts import ChartManager
from .dashboard_updater import DashboardUpdater

__all__ = [
    'DashboardPanel',
    'ChartManager',
    'DashboardUpdater'
]
