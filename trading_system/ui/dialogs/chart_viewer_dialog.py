"""
Chart Viewer Dialog Module

Provides a dialog to display TradingView Lightweight Charts with candlestick data
and trade markers for backtest analysis.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QMessageBox, QWidget, QComboBox
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView

from .chart_data_preparer import ChartDataPreparer


class ChartViewerDialog(QDialog):
    """
    Dialog for displaying candlestick charts with trade markers using TradingView Lightweight Charts.
    
    Features:
    - Candlestick chart visualization
    - Volume histogram
    - Buy/Sell trade markers
    - Interactive legend with OHLCV data
    - Trade statistics
    """
    
    def __init__(self, parent: QWidget = None, symbol: str = "", 
                 candle_data: pd.DataFrame = None, trades: List[Dict] = None):
        """
        Initialize the ChartViewerDialog.
        
        Args:
            parent: Parent widget
            symbol: Trading symbol name
            candle_data: DataFrame with OHLCV data (columns: datetime, open, high, low, close, volume)
            trades: List of trade dictionaries with entry/exit information
        """
        super().__init__(parent)
        self.symbol = symbol
        self.candle_data = candle_data if candle_data is not None else pd.DataFrame()
        self.trades = trades or []
        
        self.setWindowTitle(f"Chart Viewer - {symbol}")
        
        # Make dialog fullscreen and responsive
        from PySide6.QtCore import Qt
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        
        # Set to screen size
        try:
            from PySide6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            if screen:
                screen_geometry = screen.availableGeometry()
                self.setGeometry(screen_geometry)
        except:
            # Fallback if screen detection fails
            self.setMinimumSize(1400, 900)
        
        self._setup_ui()
        self._load_chart()
        
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
        
        # Symbol label
        symbol_label = QLabel(f"📊 {self.symbol}")
        symbol_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold; padding-left: 10px;")
        toolbar_layout.addWidget(symbol_label)
        
        toolbar_layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet("padding: 5px 15px; font-size: 13px;")
        refresh_btn.clicked.connect(self._load_chart)
        toolbar_layout.addWidget(refresh_btn)
        
        # Export button
        export_btn = QPushButton("💾 Export HTML")
        export_btn.setStyleSheet("padding: 5px 15px; font-size: 13px;")
        export_btn.clicked.connect(self._export_html)
        toolbar_layout.addWidget(export_btn)
        
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
        from PySide6.QtWidgets import QSizePolicy
        self.web_view = QWebEngineView()
        self.web_view.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        layout.addWidget(self.web_view)
    
    def _toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        if self.isFullScreen():
            self.showMaximized()
            self.fullscreen_btn.setText("⛶ Fullscreen")
        else:
            self.showFullScreen()
            self.fullscreen_btn.setText("⛶ Exit Fullscreen")
    
    def resizeEvent(self, event):
        """Handle resize events to update chart size."""
        super().resizeEvent(event)
        # Chart will auto-resize via JavaScript in the HTML template
    
    def _prepare_candle_data(self) -> List[Dict]:
        """
        Convert DataFrame to format required by Lightweight Charts.
        
        Returns:
            List of dictionaries with time, open, high, low, close, volume
        """
        if self.candle_data.empty:
            return []
        
        data = []
        df = self.candle_data.copy()
        
        # Ensure we have a datetime column
        time_col = None
        for col in ['datetime', 'date', 'time', 'timestamp']:
            if col in df.columns:
                time_col = col
                break
        
        if time_col is None:
            # Try to use index if it's datetime
            if isinstance(df.index, pd.DatetimeIndex):
                df['datetime'] = df.index
                time_col = 'datetime'
            else:
                print("Warning: No datetime column found in candle data")
                return []
        
        for _, row in df.iterrows():
            try:
                # Convert timestamp to Unix timestamp
                timestamp = row[time_col]
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                
                unix_time = int(timestamp.timestamp())
                
                candle = {
                    'time': unix_time,
                    'open': float(row.get('open', 0)),
                    'high': float(row.get('high', 0)),
                    'low': float(row.get('low', 0)),
                    'close': float(row.get('close', 0)),
                    'volume': float(row.get('volume', 0))
                }
                data.append(candle)
            except Exception as e:
                print(f"Error processing candle data row: {e}")
                continue
        
        # Sort by time
        data.sort(key=lambda x: x['time'])
        return data
    
    def _prepare_trade_markers(self) -> List[Dict]:
        """
        Convert trades to marker format for Lightweight Charts.
        Aligns trade timestamps to nearest candle timestamps for clean display.
        
        Returns:
            List of marker dictionaries
        """
        if not self.trades:
            return []
        
        # Get available candle timestamps
        candle_timestamps = set()
        if not self.candle_data.empty:
            time_col = None
            for col in ['datetime', 'date', 'time', 'timestamp']:
                if col in self.candle_data.columns:
                    time_col = col
                    break
            
            if time_col:
                for _, row in self.candle_data.iterrows():
                    try:
                        ts = row[time_col]
                        if isinstance(ts, str):
                            ts = pd.to_datetime(ts)
                        candle_timestamps.add(int(ts.timestamp()))
                    except:
                        continue
        
        markers = []
        
        def find_nearest_candle_time(trade_time):
            """Find the nearest available candle timestamp."""
            if not candle_timestamps:
                return trade_time
            
            if isinstance(trade_time, str):
                trade_time = pd.to_datetime(trade_time)
            
            trade_timestamp = int(trade_time.timestamp())
            
            # Find nearest candle timestamp
            nearest = min(candle_timestamps, key=lambda x: abs(x - trade_timestamp))
            return nearest
        
        for trade in self.trades:
            try:
                # Entry marker (Buy)
                entry_time = trade.get('entry_time') or trade.get('entry_datetime')
                if entry_time:
                    entry_timestamp = find_nearest_candle_time(entry_time)
                    
                    # Simplified text - just the action
                    entry_price = trade.get('entry_price', 0)
                    qty = trade.get('quantity', 0)
                    
                    entry_marker = {
                        'time': entry_timestamp,
                        'position': 'belowBar',
                        'color': '#26a69a',
                        'shape': 'arrowUp',
                        'text': f'BUY',
                        'size': 1
                    }
                    markers.append(entry_marker)
                
                # Exit marker (Sell)
                exit_time = trade.get('exit_time') or trade.get('exit_datetime')
                if exit_time:
                    exit_timestamp = find_nearest_candle_time(exit_time)
                    
                    pnl = trade.get('pnl', 0)
                    
                    # Color code by profit/loss
                    marker_color = '#26a69a' if pnl >= 0 else '#ef5350'
                    
                    exit_marker = {
                        'time': exit_timestamp,
                        'position': 'aboveBar',
                        'color': marker_color,
                        'shape': 'arrowDown',
                        'text': f'SELL',
                        'size': 1
                    }
                    markers.append(exit_marker)
                    
            except Exception as e:
                print(f"Error processing trade marker: {e}")
                continue
        
        # Sort by time and remove duplicates at same timestamp
        markers.sort(key=lambda x: x['time'])
        
        # Group markers by timestamp and position to avoid overlap
        unique_markers = []
        seen = set()
        
        for marker in markers:
            key = (marker['time'], marker['position'])
            if key not in seen:
                unique_markers.append(marker)
                seen.add(key)
        
        return unique_markers
    
    def _calculate_symbol_stats(self) -> Dict[str, Any]:
        """
        Calculate statistics for the symbol based on trades.
        
        Returns:
            Dictionary with totalTrades, winRate, totalPnL
        """
        if not self.trades:
            return {
                'totalTrades': 0,
                'winRate': 0,
                'totalPnL': 0
            }
        
        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if t.get('pnl', 0) > 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        total_pnl = sum(t.get('pnl', 0) for t in self.trades)
        
        return {
            'totalTrades': total_trades,
            'winRate': win_rate,
            'totalPnL': total_pnl
        }
    
    def _prepare_trade_data_for_js(self) -> List[Dict]:
        """
        Prepare trade data for JavaScript with aligned timestamps.
        
        Returns:
            List of trade dictionaries with Unix timestamps
        """
        if not self.trades:
            return []
        
        # Get available candle timestamps
        candle_timestamps = set()
        if not self.candle_data.empty:
            time_col = None
            for col in ['datetime', 'date', 'time', 'timestamp']:
                if col in self.candle_data.columns:
                    time_col = col
                    break
            
            if time_col:
                for _, row in self.candle_data.iterrows():
                    try:
                        ts = row[time_col]
                        if isinstance(ts, str):
                            ts = pd.to_datetime(ts)
                        candle_timestamps.add(int(ts.timestamp()))
                    except:
                        continue
        
        def find_nearest_candle_time(trade_time):
            """Find the nearest available candle timestamp."""
            if not candle_timestamps:
                if isinstance(trade_time, str):
                    trade_time = pd.to_datetime(trade_time)
                return int(trade_time.timestamp())
            
            if isinstance(trade_time, str):
                trade_time = pd.to_datetime(trade_time)
            
            trade_timestamp = int(trade_time.timestamp())
            nearest = min(candle_timestamps, key=lambda x: abs(x - trade_timestamp))
            return nearest
        
        trade_data = []
        for trade in self.trades:
            try:
                entry_time = trade.get('entry_time') or trade.get('entry_datetime')
                exit_time = trade.get('exit_time') or trade.get('exit_datetime')
                
                trade_dict = {
                    'entry_time': find_nearest_candle_time(entry_time) if entry_time else None,
                    'exit_time': find_nearest_candle_time(exit_time) if exit_time else None,
                    'entry_price': float(trade.get('entry_price', 0)),
                    'exit_price': float(trade.get('exit_price', 0)),
                    'quantity': int(trade.get('quantity', 0)),
                    'pnl': float(trade.get('pnl', 0)),
                    'exit_reason': str(trade.get('exit_reason', 'N/A')),
                    'paper_trade': bool(trade.get('paper_trade', False))
                }
                trade_data.append(trade_dict)
            except Exception as e:
                print(f"Error preparing trade data: {e}")
                continue
        
        return trade_data
    
    def _load_chart(self):
        """Load the chart with data."""
        try:
            # Prepare data using ChartDataPreparer
            candle_data_json = ChartDataPreparer.prepare_candle_data(self.candle_data)
            trade_markers_json = ChartDataPreparer.prepare_trade_markers(self.trades, self.candle_data)
            trade_data_json = ChartDataPreparer.prepare_trade_data_for_js(self.trades, self.candle_data)
            symbol_stats = ChartDataPreparer.calculate_symbol_stats(self.trades)
            
            if not candle_data_json:
                QMessageBox.warning(
                    self, 
                    "No Data", 
                    "No candlestick data available to display."
                )
                return
            
            # Load HTML template
            template_path = Path(__file__).parent.parent / "components" / "chart_viewer_template.html"
            
            if not template_path.exists():
                QMessageBox.critical(
                    self, 
                    "Template Error", 
                    f"Chart template not found at {template_path}"
                )
                return
            
            with open(template_path, 'r', encoding='utf-8') as f:
                html_template = f.read()
            
            # Replace placeholders
            html_content = html_template.replace('{{SYMBOL}}', self.symbol)
            html_content = html_content.replace('{{CANDLE_DATA}}', json.dumps(candle_data_json))
            html_content = html_content.replace('{{TRADE_MARKERS}}', json.dumps(trade_markers_json))
            html_content = html_content.replace('{{TRADE_DATA}}', json.dumps(trade_data_json))
            html_content = html_content.replace('{{SYMBOL_STATS}}', json.dumps(symbol_stats))
            
            # Load into web view
            self.web_view.setHtml(html_content)
            
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Chart Error", 
                f"Failed to load chart: {str(e)}"
            )
            print(f"Chart loading error: {e}")
    
    def _export_html(self):
        """Export the current chart as an HTML file."""
        try:
            from PySide6.QtWidgets import QFileDialog
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"chart_{self.symbol.replace(':', '_')}_{timestamp}.html"
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Chart",
                default_filename,
                "HTML Files (*.html)"
            )
            
            if file_path:
                # Get current HTML from webview using ChartDataPreparer
                candle_data_json = ChartDataPreparer.prepare_candle_data(self.candle_data)
                trade_markers_json = ChartDataPreparer.prepare_trade_markers(self.trades, self.candle_data)
                trade_data_json = ChartDataPreparer.prepare_trade_data_for_js(self.trades, self.candle_data)
                symbol_stats = ChartDataPreparer.calculate_symbol_stats(self.trades)
                
                template_path = Path(__file__).parent.parent / "components" / "chart_viewer_template.html"
                with open(template_path, 'r', encoding='utf-8') as f:
                    html_template = f.read()
                
                html_content = html_template.replace('{{SYMBOL}}', self.symbol)
                html_content = html_content.replace('{{CANDLE_DATA}}', json.dumps(candle_data_json))
                html_content = html_content.replace('{{TRADE_MARKERS}}', json.dumps(trade_markers_json))
                html_content = html_content.replace('{{TRADE_DATA}}', json.dumps(trade_data_json))
                html_content = html_content.replace('{{SYMBOL_STATS}}', json.dumps(symbol_stats))
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                QMessageBox.information(
                    self,
                    "Export Success",
                    f"Chart exported to:\n{file_path}"
                )
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export chart: {str(e)}"
            )


class MultiSymbolChartDialog(QDialog):
    """
    Dialog for viewing charts of multiple symbols with a dropdown selector.
    """
    
    def __init__(self, parent: QWidget = None, 
                 symbol_data: Dict[str, pd.DataFrame] = None,
                 symbol_trades: Dict[str, List[Dict]] = None):
        """
        Initialize the MultiSymbolChartDialog.
        
        Args:
            parent: Parent widget
            symbol_data: Dictionary mapping symbol to candle DataFrame
            symbol_trades: Dictionary mapping symbol to list of trades
        """
        super().__init__(parent)
        self.symbol_data = symbol_data or {}
        self.symbol_trades = symbol_trades or {}
        
        self.setWindowTitle("Multi-Symbol Chart Viewer")
        
        # Make dialog fullscreen and responsive
        from PySide6.QtCore import Qt
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)
        
        # Set to screen size
        try:
            from PySide6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            if screen:
                screen_geometry = screen.availableGeometry()
                self.setGeometry(screen_geometry)
        except:
            # Fallback if screen detection fails
            self.setMinimumSize(1400, 900)
        
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
        
        # Symbol selector label
        symbol_label = QLabel("📊 Symbol:")
        symbol_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold; padding-left: 10px;")
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
        
        # Export button
        export_btn = QPushButton("💾 Export HTML")
        export_btn.setStyleSheet("padding: 5px 15px; font-size: 13px;")
        export_btn.clicked.connect(self._export_current_chart)
        toolbar_layout.addWidget(export_btn)
        
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
        from PySide6.QtWidgets import QSizePolicy
        self.web_view = QWebEngineView()
        self.web_view.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        layout.addWidget(self.web_view)
        
        self.current_symbol = None
    
    def _toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        if self.isFullScreen():
            self.showMaximized()
            self.fullscreen_btn.setText("⛶ Fullscreen")
        else:
            self.showFullScreen()
            self.fullscreen_btn.setText("⛶ Exit Fullscreen")
    
    def resizeEvent(self, event):
        """Handle resize events to update chart size."""
        super().resizeEvent(event)
        # Chart will auto-resize via JavaScript in the HTML template
    
    def _on_symbol_changed(self, index: int):
        """Handle symbol selection change."""
        if index < 0 or not self.symbol_data:
            return
        
        symbol = self.symbol_selector.itemText(index)
        self.current_symbol = symbol
        
        candle_data = self.symbol_data.get(symbol, pd.DataFrame())
        trades = self.symbol_trades.get(symbol, [])
        
        self._load_chart(symbol, candle_data, trades)
    
    def _load_chart(self, symbol: str, candle_data: pd.DataFrame, trades: List[Dict]):
        """Load chart for a specific symbol."""
        try:
            # Use ChartDataPreparer for data preparation
            candle_data_json = ChartDataPreparer.prepare_candle_data(candle_data)
            trade_markers_json = ChartDataPreparer.prepare_trade_markers(trades, candle_data)
            trade_data_json = ChartDataPreparer.prepare_trade_data_for_js(trades, candle_data)
            symbol_stats = ChartDataPreparer.calculate_symbol_stats(trades)
            
            if not candle_data_json:
                self.web_view.setHtml(
                    f"<html><body style='background:#131722;color:#fff;font-family:sans-serif;text-align:center;padding-top:100px;'>"
                    f"<h2>No data available for {symbol}</h2></body></html>"
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
            
        except Exception as e:
            QMessageBox.critical(self, "Chart Error", f"Failed to load chart: {str(e)}")
            print(f"Chart loading error: {e}")
    
    def _export_current_chart(self):
        """Export the currently displayed chart."""
        if not self.current_symbol:
            return
        
        candle_data = self.symbol_data.get(self.current_symbol, pd.DataFrame())
        trades = self.symbol_trades.get(self.current_symbol, [])
        
        # Create temporary viewer and use its export method
        temp_viewer = ChartViewerDialog(
            parent=self,
            symbol=self.current_symbol,
            candle_data=candle_data,
            trades=trades
        )
        temp_viewer._export_html()
