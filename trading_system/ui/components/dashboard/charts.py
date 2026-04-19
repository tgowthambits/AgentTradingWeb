"""
Charts Module

Contains chart creation and update functionality for the dashboard.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from PySide6.QtWidgets import QLabel, QFrame, QVBoxLayout
from PySide6.QtCore import Qt
import pandas as pd


class ChartManager:
    """
    Manager for dashboard charts.
    
    This class handles:
    - PnL chart updates
    - Equity curve chart updates
    - Distribution chart updates
    - Chart styling
    
    Attributes:
        config: Configuration dictionary
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the ChartManager.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
    
    def create_chart_placeholder(self, title: str) -> QFrame:
        """
        Create a placeholder frame for a chart.
        
        Args:
            title: Chart title
        
        Returns:
            QFrame containing the placeholder
        """
        frame = QFrame()
        frame.setObjectName("chartFrame")
        frame.setStyleSheet("""
            QFrame#chartFrame {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #888888; font-size: 12px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        placeholder = QLabel("Chart will appear here")
        placeholder.setStyleSheet("color: #555555; font-size: 11px;")
        placeholder.setAlignment(Qt.AlignCenter)
        layout.addWidget(placeholder)
        
        return frame
    
    def update_pnl_chart(self, chart_label: QLabel, timestamps: List[datetime],
                         pnl_values: List[float], title: str = "PnL Over Time"):
        """
        Update PnL chart with new data.
        
        Creates a simple text-based representation when matplotlib is not available.
        
        Args:
            chart_label: QLabel to update
            timestamps: List of timestamps
            pnl_values: List of PnL values
            title: Chart title
        """
        if chart_label is None or len(timestamps) < 2:
            return
        
        try:
            # Try to use matplotlib
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
            import io
            from PySide6.QtGui import QPixmap
            
            fig, ax = plt.subplots(figsize=(6, 3), facecolor='#1e1e1e')
            ax.set_facecolor('#1e1e1e')
            
            # Plot PnL
            colors = ['#22c55e' if v >= 0 else '#ef4444' for v in pnl_values]
            ax.fill_between(range(len(timestamps)), pnl_values, alpha=0.3, 
                           color='#22c55e' if pnl_values[-1] >= 0 else '#ef4444')
            ax.plot(range(len(timestamps)), pnl_values, color='#22c55e' if pnl_values[-1] >= 0 else '#ef4444', linewidth=2)
            
            ax.set_title(title, color='white', fontsize=10)
            ax.tick_params(colors='white', labelsize=8)
            ax.spines['bottom'].set_color('#404040')
            ax.spines['top'].set_color('#404040')
            ax.spines['left'].set_color('#404040')
            ax.spines['right'].set_color('#404040')
            ax.grid(True, alpha=0.2)
            
            plt.tight_layout()
            
            # Convert to pixmap
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=100, facecolor='#1e1e1e')
            buf.seek(0)
            pixmap = QPixmap()
            pixmap.loadFromData(buf.getvalue())
            chart_label.setPixmap(pixmap.scaled(chart_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            
            plt.close(fig)
            
        except ImportError:
            # Fallback to text display
            self._update_text_chart(chart_label, pnl_values, title)
    
    def update_equity_chart(self, chart_label: QLabel, timestamps: List[datetime],
                            equity_values: List[float], title: str = "Equity Curve"):
        """
        Update equity curve chart with new data.
        
        Args:
            chart_label: QLabel to update
            timestamps: List of timestamps
            equity_values: List of equity values
            title: Chart title
        """
        if chart_label is None or len(timestamps) < 2:
            return
        
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import io
            from PySide6.QtGui import QPixmap
            
            fig, ax = plt.subplots(figsize=(6, 3), facecolor='#1e1e1e')
            ax.set_facecolor('#1e1e1e')
            
            # Plot equity
            ax.fill_between(range(len(timestamps)), equity_values, alpha=0.3, color='#3b82f6')
            ax.plot(range(len(timestamps)), equity_values, color='#3b82f6', linewidth=2)
            
            ax.set_title(title, color='white', fontsize=10)
            ax.tick_params(colors='white', labelsize=8)
            ax.spines['bottom'].set_color('#404040')
            ax.spines['top'].set_color('#404040')
            ax.spines['left'].set_color('#404040')
            ax.spines['right'].set_color('#404040')
            ax.grid(True, alpha=0.2)
            
            plt.tight_layout()
            
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=100, facecolor='#1e1e1e')
            buf.seek(0)
            pixmap = QPixmap()
            pixmap.loadFromData(buf.getvalue())
            chart_label.setPixmap(pixmap.scaled(chart_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            
            plt.close(fig)
            
        except ImportError:
            self._update_text_chart(chart_label, equity_values, title)
    
    def update_distribution_chart(self, chart_label: QLabel, trades_df: pd.DataFrame):
        """
        Update win/loss distribution chart.
        
        Args:
            chart_label: QLabel to update
            trades_df: DataFrame of completed trades
        """
        if chart_label is None or trades_df.empty:
            return
        
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import io
            from PySide6.QtGui import QPixmap
            
            fig, ax = plt.subplots(figsize=(6, 3), facecolor='#1e1e1e')
            ax.set_facecolor('#1e1e1e')
            
            # Calculate wins and losses
            wins = len(trades_df[trades_df['pnl'] > 0])
            losses = len(trades_df[trades_df['pnl'] <= 0])
            
            # Create bar chart
            bars = ax.bar(['Wins', 'Losses'], [wins, losses], color=['#22c55e', '#ef4444'])
            
            ax.set_title('Win/Loss Distribution', color='white', fontsize=10)
            ax.tick_params(colors='white', labelsize=8)
            ax.spines['bottom'].set_color('#404040')
            ax.spines['top'].set_color('#404040')
            ax.spines['left'].set_color('#404040')
            ax.spines['right'].set_color('#404040')
            
            # Add value labels
            for bar in bars:
                height = bar.get_height()
                ax.annotate(f'{int(height)}',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           ha='center', va='bottom', color='white', fontsize=9)
            
            plt.tight_layout()
            
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=100, facecolor='#1e1e1e')
            buf.seek(0)
            pixmap = QPixmap()
            pixmap.loadFromData(buf.getvalue())
            chart_label.setPixmap(pixmap.scaled(chart_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            
            plt.close(fig)
            
        except ImportError:
            if isinstance(chart_label, QLabel):
                wins = len(trades_df[trades_df['pnl'] > 0])
                losses = len(trades_df[trades_df['pnl'] <= 0])
                chart_label.setText(f"Wins: {wins} | Losses: {losses}")
    
    def _update_text_chart(self, chart_label: QLabel, values: List[float], title: str):
        """
        Update chart with text-based representation.
        
        Args:
            chart_label: QLabel to update
            values: List of values
            title: Chart title
        """
        if not values:
            return
        
        current = values[-1]
        if len(values) > 1:
            prev = values[-2]
            change = current - prev
            change_str = f"+{change:.2f}" if change >= 0 else f"{change:.2f}"
        else:
            change_str = "N/A"
        
        text = f"{title}\nCurrent: ₹{current:,.2f}\nChange: {change_str}"
        chart_label.setText(text)
        chart_label.setAlignment(Qt.AlignCenter)
