"""
Live Chart Dialog Module

Provides a live-updating chart dialog for real-time backtest visualization.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QWidget, QComboBox, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWebEngineWidgets import QWebEngineView


class LiveChartDialog(QDialog):
    """
    Live-updating chart dialog for backtesting visualization.
    
    Updates in real-time as backtest progresses.
    """
    
    def __init__(self, parent: QWidget = None, 
                 symbol_data: Dict[str, pd.DataFrame] = None,
                 symbol_trades: Dict[str, List[Dict]] = None):
        """
        Initialize the LiveChartDialog.
        
        Args:
            parent: Parent widget
            symbol_data: Dictionary mapping symbol to candle DataFrame
            symbol_trades: Dictionary mapping symbol to list of trades
        """
        super().__init__(parent)
        self.symbol_data = symbol_data or {}
        self.symbol_trades = symbol_trades or {}
        
        self.setWindowTitle("Live Chart - Backtest in Progress")
        
        # Make dialog fullscreen and responsive
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        
        # Set to screen size
        try:
            from PySide6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            if screen:
                screen_geometry = screen.availableGeometry()
                self.setGeometry(screen_geometry)
        except:
            self.setMinimumSize(1400, 900)
        
        self.current_symbol = None
        self.pending_update = False
        self.chart_loaded = False
        
        # Update throttling timer
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self._process_pending_update)
        
        self._setup_ui()
        
        # Load first symbol if available
        if self.symbol_data:
            self.symbol_selector.setCurrentIndex(0)
            self._on_symbol_changed(0)
        
        # Show maximized
        self.showMaximized()
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Toolbar
        toolbar = QWidget()
        toolbar.setStyleSheet("background-color: #2a2e39; padding: 8px;")
        toolbar.setFixedHeight(50)
        toolbar_layout = QHBoxLayout(toolbar)
        
        # Live indicator
        live_indicator = QLabel("🔴 LIVE")
        live_indicator.setStyleSheet("""
            color: #ef5350;
            font-size: 16px;
            font-weight: bold;
            padding-left: 10px;
            animation: blink 1s infinite;
        """)
        toolbar_layout.addWidget(live_indicator)
        
        # Symbol selector label
        symbol_label = QLabel("📊 Symbol:")
        symbol_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold; padding-left: 20px;")
        toolbar_layout.addWidget(symbol_label)
        
        # Symbol selector dropdown
        self.symbol_selector = QComboBox()
        self.symbol_selector.addItems(list(self.symbol_data.keys()))
        self.symbol_selector.currentIndexChanged.connect(self._on_symbol_changed)
        self.symbol_selector.setMinimumWidth(300)
        self.symbol_selector.setStyleSheet("""
            QComboBox {
                padding: 5px 10px;
                font-size: 13px;
                border: 1px solid #444;
                background: #1e222d;
                color: white;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white;
                margin-right: 5px;
            }
        """)
        toolbar_layout.addWidget(self.symbol_selector)
        
        toolbar_layout.addStretch()
        
        # Auto-scroll toggle
        self.auto_scroll_btn = QPushButton("📍 Auto-Scroll: ON")
        self.auto_scroll_btn.setCheckable(True)
        self.auto_scroll_btn.setChecked(True)
        self.auto_scroll_btn.setStyleSheet("padding: 5px 15px; font-size: 13px;")
        self.auto_scroll_btn.clicked.connect(self._toggle_auto_scroll)
        toolbar_layout.addWidget(self.auto_scroll_btn)
        
        # Fullscreen toggle button
        self.fullscreen_btn = QPushButton("⛶ Fullscreen")
        self.fullscreen_btn.setStyleSheet("padding: 5px 15px; font-size: 13px;")
        self.fullscreen_btn.clicked.connect(self._toggle_fullscreen)
        toolbar_layout.addWidget(self.fullscreen_btn)
        
        # Close button
        close_btn = QPushButton("✖ Close")
        close_btn.setStyleSheet("padding: 5px 15px; font-size: 13px;")
        close_btn.clicked.connect(self.accept)
        toolbar_layout.addWidget(close_btn)
        
        layout.addWidget(toolbar)
        
        # Web view for chart - takes remaining space
        self.web_view = QWebEngineView()
        self.web_view.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        layout.addWidget(self.web_view)
        
        self.auto_scroll_enabled = True
    
    def _toggle_auto_scroll(self):
        """Toggle auto-scroll to latest data."""
        self.auto_scroll_enabled = self.auto_scroll_btn.isChecked()
        self.auto_scroll_btn.setText(
            "📍 Auto-Scroll: ON" if self.auto_scroll_enabled else "📍 Auto-Scroll: OFF"
        )
    
    def _toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        if self.isFullScreen():
            self.showMaximized()
            self.fullscreen_btn.setText("⛶ Fullscreen")
        else:
            self.showFullScreen()
            self.fullscreen_btn.setText("⛶ Exit Fullscreen")
    
    def _on_symbol_changed(self, index: int):
        """Handle symbol selection change."""
        if index < 0 or not self.symbol_data:
            return
        
        symbol = self.symbol_selector.itemText(index)
        self.current_symbol = symbol
        
        candle_data = self.symbol_data.get(symbol, pd.DataFrame())
        trades = self.symbol_trades.get(symbol, [])
        
        # Full reload when changing symbols
        self.chart_loaded = False
        self._load_chart(symbol, candle_data, trades)
    
    def update_chart(self, symbol_data: Dict[str, pd.DataFrame], symbol_trades: Dict[str, List[Dict]]):
        """
        Update chart with new data (called from backtest thread).
        
        Args:
            symbol_data: Updated symbol data
            symbol_trades: Updated trades data
        """
        self.symbol_data = symbol_data
        self.symbol_trades = symbol_trades
        
        # Throttle updates to avoid overwhelming the UI
        if not self.pending_update:
            self.pending_update = True
            self.update_timer.start(500)  # Update every 500ms at most
    
    def _process_pending_update(self):
        """Process pending chart update."""
        self.pending_update = False
        
        if self.current_symbol and self.current_symbol in self.symbol_data:
            candle_data = self.symbol_data.get(self.current_symbol, pd.DataFrame())
            trades = self.symbol_trades.get(self.current_symbol, [])
            
            # If chart is already loaded, update data via JavaScript
            if self.chart_loaded:
                self._update_chart_data(self.current_symbol, candle_data, trades)
            else:
                self._load_chart(self.current_symbol, candle_data, trades)
    
    def _load_chart(self, symbol: str, candle_data: pd.DataFrame, trades: List[Dict]):
        """Load chart for a specific symbol (initial load only)."""
        try:
            # Use data preparer instead of instantiating dialog
            from .chart_data_preparer import ChartDataPreparer
            
            candle_data_json = ChartDataPreparer.prepare_candle_data(candle_data)
            trade_markers_json = ChartDataPreparer.prepare_trade_markers(trades, candle_data)
            trade_data_json = ChartDataPreparer.prepare_trade_data_for_js(trades, candle_data)
            symbol_stats = ChartDataPreparer.calculate_symbol_stats(trades)
            
            if not candle_data_json:
                self.chart_loaded = False
                self.web_view.setHtml(
                    f"<html><body style='background:#131722;color:#fff;font-family:sans-serif;text-align:center;padding-top:100px;'>"
                    f"<h2>Waiting for data for {symbol}...</h2>"
                    f"<p>Backtest in progress</p></body></html>"
                )
                return
            
            # Load HTML template
            template_path = Path(__file__).parent.parent / "components" / "chart_viewer_template.html"
            
            with open(template_path, 'r', encoding='utf-8') as f:
                html_template = f.read()
            
            html_content = html_template.replace('{{SYMBOL}}', symbol)
            html_content = html_content.replace('{{CANDLE_DATA}}', json.dumps(candle_data_json))
            html_content = html_content.replace('{{TRADE_MARKERS}}', json.dumps(trade_markers_json))
            html_content = html_content.replace('{{TRADE_DATA}}', json.dumps(trade_data_json))
            html_content = html_content.replace('{{SYMBOL_STATS}}', json.dumps(symbol_stats))
            
            self.web_view.setHtml(html_content)
            self.chart_loaded = True
            
        except Exception as e:
            print(f"Live chart loading error: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_chart_data(self, symbol: str, candle_data: pd.DataFrame, trades: List[Dict]):
        """Update chart data via JavaScript without reloading the page."""
        try:
            # Use data preparer instead of instantiating dialog
            from .chart_data_preparer import ChartDataPreparer
            
            candle_data_json = ChartDataPreparer.prepare_candle_data(candle_data)
            trade_markers_json = ChartDataPreparer.prepare_trade_markers(trades, candle_data)
            trade_data_json = ChartDataPreparer.prepare_trade_data_for_js(trades, candle_data)
            symbol_stats = ChartDataPreparer.calculate_symbol_stats(trades)
            
            if not candle_data_json:
                return
            
            # Update chart via JavaScript
            js_code = f"""
                (function() {{
                    try {{
                        // Update candle data
                        if (typeof candleSeries !== 'undefined') {{
                            candleSeries.setData({json.dumps(candle_data_json)});
                        }}
                        
                        // Update volume data
                        if (typeof volumeSeries !== 'undefined') {{
                            const newCandleData = {json.dumps(candle_data_json)};
                            const newVolumeData = newCandleData.map(candle => ({{
                                time: candle.time,
                                value: candle.volume || 0,
                                color: candle.close >= candle.open ? 'rgba(38, 166, 154, 0.5)' : 'rgba(239, 83, 80, 0.5)'
                            }}));
                            volumeSeries.setData(newVolumeData);
                        }}
                        
                        // Update trade markers
                        if (typeof candleSeries !== 'undefined') {{
                            candleSeries.setMarkers({json.dumps(trade_markers_json)});
                        }}
                        
                        // Update trade data for hover
                        if (typeof tradeData !== 'undefined') {{
                            const newTradeData = {json.dumps(trade_data_json)};
                            
                            // Rebuild trades by time map
                            const newTradesByTime = {{}};
                            newTradeData.forEach(trade => {{
                                if (trade.entry_time) {{
                                    if (!newTradesByTime[trade.entry_time]) {{
                                        newTradesByTime[trade.entry_time] = [];
                                    }}
                                    newTradesByTime[trade.entry_time].push({{type: 'entry', trade: trade}});
                                }}
                                if (trade.exit_time) {{
                                    if (!newTradesByTime[trade.exit_time]) {{
                                        newTradesByTime[trade.exit_time] = [];
                                    }}
                                    newTradesByTime[trade.exit_time].push({{type: 'exit', trade: trade}});
                                }}
                            }});
                            
                            // Update global variable
                            window.tradesByTime = newTradesByTime;
                        }}
                        
                        // Update stats
                        const stats = {json.dumps(symbol_stats)};
                        if (document.getElementById('total-trades')) {{
                            document.getElementById('total-trades').textContent = stats.totalTrades || 0;
                        }}
                        if (document.getElementById('win-rate')) {{
                            document.getElementById('win-rate').textContent = 
                                stats.winRate ? stats.winRate.toFixed(1) + '%' : '0%';
                        }}
                        if (document.getElementById('total-pnl')) {{
                            const pnlElement = document.getElementById('total-pnl');
                            const pnl = stats.totalPnL || 0;
                            pnlElement.textContent = '₹' + pnl.toFixed(2);
                            pnlElement.className = pnl >= 0 ? 'stat-value positive' : 'stat-value negative';
                        }}
                        
                        // Auto-scroll if enabled
                        if ({str(self.auto_scroll_enabled).lower()}) {{
                            chart.timeScale().scrollToRealTime();
                        }}
                    }} catch (e) {{
                        console.error('Error updating chart:', e);
                    }}
                }})();
            """
            
            self.web_view.page().runJavaScript(js_code)
            
        except Exception as e:
            print(f"Error updating chart data: {e}")
            import traceback
            traceback.print_exc()
    
    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)
