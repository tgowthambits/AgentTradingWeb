"""
Backtest Dialogs Module

Provides dialogs for backtest results, export, and analysis.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QMessageBox, QWidget, QGroupBox, QTextEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

try:
    from .chart_viewer_dialog import ChartViewerDialog, MultiSymbolChartDialog
    CHARTS_AVAILABLE = True
except ImportError:
    print("Warning: Chart viewer not available. Install PySide6-WebEngine: pip install PySide6-WebEngine")
    CHARTS_AVAILABLE = False


class BacktestResultsDialog(QDialog):
    """
    Dialog for displaying detailed backtest results.
    
    Shows comprehensive metrics, trade breakdown, and analysis.
    """
    
    def __init__(self, parent: QWidget = None, results: Dict[str, Any] = None, 
                 symbol_data: Dict[str, pd.DataFrame] = None):
        """
        Initialize the BacktestResultsDialog.
        
        Args:
            parent: Parent widget
            results: Dictionary containing backtest results
            symbol_data: Dictionary mapping symbol to OHLCV DataFrame for charting
        """
        super().__init__(parent)
        self.results = results or {}
        self.symbol_data = symbol_data or {}
        self.setWindowTitle("Backtest Results")
        self.setMinimumSize(800, 600)
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Summary section
        summary_group = QGroupBox("Summary")
        summary_layout = QVBoxLayout(summary_group)
        
        metrics = self.results.get('metrics', {})
        summary_text = f"""
        Total PnL: {metrics.get('Total PnL', 'N/A')}
        Return %: {metrics.get('Return %', 'N/A')}
        Win Rate: {metrics.get('Win Rate', 'N/A')}
        Total Trades: {metrics.get('Total Trades', 'N/A')}
        Profit Factor: {metrics.get('Profit Factor', 'N/A')}
        Sharpe Ratio: {metrics.get('Sharpe Ratio', 'N/A')}
        Max Drawdown: {metrics.get('Max Drawdown', 'N/A')}
        """
        
        summary_label = QLabel(summary_text)
        summary_label.setStyleSheet("font-family: monospace; font-size: 12px;")
        summary_layout.addWidget(summary_label)
        layout.addWidget(summary_group)
        
        # Trades table
        trades_group = QGroupBox("Trades")
        trades_layout = QVBoxLayout(trades_group)
        
        trades_df = self.results.get('trades', pd.DataFrame())
        if not trades_df.empty:
            self.trades_table = QTableWidget()
            self._populate_trades_table(trades_df)
            trades_layout.addWidget(self.trades_table)
        else:
            trades_layout.addWidget(QLabel("No trades available"))
        
        layout.addWidget(trades_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # View Charts button
        if CHARTS_AVAILABLE and self.symbol_data:
            view_charts_btn = QPushButton("📊 View Charts")
            view_charts_btn.setToolTip("View candlestick charts with trade markers")
            view_charts_btn.clicked.connect(self._view_charts)
            button_layout.addWidget(view_charts_btn)
        
        export_btn = QPushButton("💾 Export to CSV")
        export_btn.clicked.connect(self._export_to_csv)
        button_layout.addWidget(export_btn)
        
        close_btn = QPushButton("✖ Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _populate_trades_table(self, trades_df: pd.DataFrame):
        """Populate the trades table."""
        columns = ['order_id', 'symbol', 'type', 'entry_price', 'exit_price', 'quantity', 'pnl', 'exit_reason']
        available_cols = [c for c in columns if c in trades_df.columns]
        
        self.trades_table.setColumnCount(len(available_cols))
        self.trades_table.setHorizontalHeaderLabels(available_cols)
        self.trades_table.setRowCount(len(trades_df))
        
        for row_idx, (_, row) in enumerate(trades_df.iterrows()):
            for col_idx, col in enumerate(available_cols):
                value = row.get(col, '')
                if col in ['entry_price', 'exit_price', 'pnl']:
                    try:
                        item = QTableWidgetItem(f"{float(value):.2f}")
                    except:
                        item = QTableWidgetItem(str(value))
                else:
                    item = QTableWidgetItem(str(value))
                
                # Color code PnL
                if col == 'pnl':
                    try:
                        pnl = float(value)
                        if pnl > 0:
                            item.setForeground(QColor(34, 139, 34))
                        elif pnl < 0:
                            item.setForeground(QColor(220, 20, 60))
                    except:
                        pass
                
                self.trades_table.setItem(row_idx, col_idx, item)
        
        self.trades_table.horizontalHeader().setStretchLastSection(True)
    
    def _export_to_csv(self):
        """Export results to CSV file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Results", "", "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                trades_df = self.results.get('trades', pd.DataFrame())
                if not trades_df.empty:
                    trades_df.to_csv(file_path, index=False)
                    QMessageBox.information(self, "Success", f"Results exported to {file_path}")
                else:
                    QMessageBox.warning(self, "Warning", "No trades to export")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export: {str(e)}")
    
    def _view_charts(self):
        """Open chart viewer dialog to visualize trades on candlestick charts."""
        if not CHARTS_AVAILABLE:
            QMessageBox.warning(
                self, 
                "Charts Not Available",
                "Chart viewing requires PySide6-WebEngine.\n\nInstall with: pip install PySide6-WebEngine"
            )
            return
        
        if not self.symbol_data:
            QMessageBox.warning(
                self,
                "No Chart Data",
                "No candlestick data available for charting."
            )
            return
        
        try:
            # Organize trades by symbol
            trades_df = self.results.get('trades', pd.DataFrame())
            symbol_trades = {}
            
            if not trades_df.empty:
                # Group trades by symbol
                for symbol in self.symbol_data.keys():
                    symbol_trades_df = trades_df[trades_df['symbol'] == symbol] if 'symbol' in trades_df.columns else pd.DataFrame()
                    
                    # Convert to list of dicts
                    trades_list = []
                    if not symbol_trades_df.empty:
                        for _, trade in symbol_trades_df.iterrows():
                            trades_list.append(trade.to_dict())
                    
                    symbol_trades[symbol] = trades_list
            
            # Open multi-symbol chart dialog
            chart_dialog = MultiSymbolChartDialog(
                parent=self,
                symbol_data=self.symbol_data,
                symbol_trades=symbol_trades
            )
            chart_dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Chart Error",
                f"Failed to open chart viewer: {str(e)}"
            )
            print(f"Chart viewer error: {e}")


class BacktestComparisonDialog(QDialog):
    """
    Dialog for comparing multiple backtest results.
    """
    
    def __init__(self, parent: QWidget = None, results_list: List[Dict] = None):
        """
        Initialize the BacktestComparisonDialog.
        
        Args:
            parent: Parent widget
            results_list: List of result dictionaries to compare
        """
        super().__init__(parent)
        self.results_list = results_list or []
        self.setWindowTitle("Backtest Comparison")
        self.setMinimumSize(900, 500)
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        if not self.results_list:
            layout.addWidget(QLabel("No results to compare"))
            return
        
        # Comparison table
        self.comparison_table = QTableWidget()
        
        # Define metrics to compare
        metrics = [
            'Total PnL', 'Return %', 'Win Rate', 'Total Trades',
            'Profit Factor', 'Sharpe Ratio', 'Max Drawdown'
        ]
        
        self.comparison_table.setRowCount(len(metrics))
        self.comparison_table.setColumnCount(len(self.results_list) + 1)
        
        # Set headers
        headers = ['Metric'] + [f"Run {i+1}" for i in range(len(self.results_list))]
        self.comparison_table.setHorizontalHeaderLabels(headers)
        
        # Populate data
        for row_idx, metric in enumerate(metrics):
            self.comparison_table.setItem(row_idx, 0, QTableWidgetItem(metric))
            
            for col_idx, results in enumerate(self.results_list):
                value = results.get('metrics', {}).get(metric, 'N/A')
                item = QTableWidgetItem(str(value))
                self.comparison_table.setItem(row_idx, col_idx + 1, item)
        
        self.comparison_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.comparison_table)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class BacktestExportDialog(QDialog):
    """
    Dialog for exporting backtest data with options.
    """
    
    def __init__(self, parent: QWidget = None, trades_df: pd.DataFrame = None,
                 metrics: Dict[str, Any] = None):
        """
        Initialize the BacktestExportDialog.
        
        Args:
            parent: Parent widget
            trades_df: DataFrame of trades
            metrics: Dictionary of calculated metrics
        """
        super().__init__(parent)
        self.trades_df = trades_df if trades_df is not None else pd.DataFrame()
        self.metrics = metrics or {}
        self.setWindowTitle("Export Backtest Results")
        self.setMinimumSize(400, 300)
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Export options
        layout.addWidget(QLabel("Select export options:"))
        
        from PySide6.QtWidgets import QCheckBox
        
        self.export_trades_check = QCheckBox("Export Trades (CSV)")
        self.export_trades_check.setChecked(True)
        layout.addWidget(self.export_trades_check)
        
        self.export_metrics_check = QCheckBox("Export Metrics (JSON)")
        self.export_metrics_check.setChecked(True)
        layout.addWidget(self.export_metrics_check)
        
        self.export_summary_check = QCheckBox("Export Summary (TXT)")
        self.export_summary_check.setChecked(False)
        layout.addWidget(self.export_summary_check)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self._export)
        button_layout.addWidget(export_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _export(self):
        """Perform the export."""
        folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        
        if not folder:
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if self.export_trades_check.isChecked() and not self.trades_df.empty:
                trades_path = f"{folder}/backtest_trades_{timestamp}.csv"
                self.trades_df.to_csv(trades_path, index=False)
            
            if self.export_metrics_check.isChecked() and self.metrics:
                import json
                metrics_path = f"{folder}/backtest_metrics_{timestamp}.json"
                with open(metrics_path, 'w') as f:
                    json.dump(self.metrics, f, indent=2, default=str)
            
            if self.export_summary_check.isChecked():
                summary_path = f"{folder}/backtest_summary_{timestamp}.txt"
                with open(summary_path, 'w') as f:
                    f.write("Backtest Summary\n")
                    f.write("=" * 40 + "\n\n")
                    for key, value in self.metrics.items():
                        f.write(f"{key}: {value}\n")
            
            QMessageBox.information(self, "Success", f"Results exported to {folder}")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")
