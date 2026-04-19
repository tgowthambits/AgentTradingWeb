# Backtest Chart Viewer

## Overview

The Chart Viewer feature allows you to visualize backtest results using interactive TradingView Lightweight Charts. It displays candlestick data with trade entry/exit markers, making it easy to analyze trading strategies.

## Features

### Live Chart Features
- **🔴 Real-Time Updates**: Chart updates live as backtest progresses
- **Smooth Updates**: Data updates via JavaScript without page reload (no blinking!)
- **Auto-Scroll**: Automatically scrolls to show latest data (toggleable)
- **Trade Visualization**: See trades appear on chart as they execute
- **Multi-Symbol Switching**: View different symbols while backtest runs
- **Throttled Updates**: Optimized to update every 500ms for smooth performance
- **Live Indicator**: Red "LIVE" badge shows chart is actively updating

### Standard Chart Features
- **Fullscreen Charts**: Opens maximized to full screen resolution by default
- **Responsive Design**: Charts automatically resize when you resize the window
- **Candlestick Charts**: View OHLCV data in a professional candlestick format
- **Trade Markers**: Buy/Sell markers showing entry and exit points
- **Trade Details**: Hover over markers to see trade information (price, quantity, PnL, exit reason)
- **Multi-Symbol Support**: Switch between different symbols using a dropdown
- **Volume Histogram**: Visualize trading volume alongside price action
- **Interactive Legend**: Real-time OHLCV data as you move your cursor
- **Export Capability**: Save charts as standalone HTML files
- **Fullscreen Toggle**: Press the fullscreen button to toggle true fullscreen mode

## Installation

The chart viewer requires `PySide6-WebEngine` to render the charts:

```bash
pip install PySide6-WebEngine
```

## Usage

### From the GUI

#### Live Chart (During Backtest)
1. Start a backtest in the Backtest tab
2. Click the **"📈 Live Chart"** button (becomes available when backtest starts)
3. Watch the chart update in real-time as the backtest progresses
4. See trades appear as they are executed
5. Auto-scroll keeps you viewing the latest data
6. Switch between symbols using the dropdown

#### Historical Chart (After Backtest)
1. Wait for the backtest to complete
2. Click the **"📊 View Charts"** button in the Backtest Results section
3. Select a symbol from the dropdown to view its complete chart
4. Analyze all trades and patterns
5. Export charts as HTML files for later review

### Programmatic Usage

```python
from trading_system.ui.dialogs.chart_viewer_dialog import MultiSymbolChartDialog
import pandas as pd

# Prepare candlestick data (DataFrame with columns: datetime, open, high, low, close, volume)
symbol_data = {
    'NSE:NIFTY2612025450PE': candle_df1,
    'NSE:NIFTY2612025450CE': candle_df2
}

# Prepare trades data (list of dictionaries)
trades = [
    {
        'symbol': 'NSE:NIFTY2612025450PE',
        'entry_time': '2026-01-15 09:30:00',
        'entry_price': 100.50,
        'exit_time': '2026-01-15 10:15:00',
        'exit_price': 105.25,
        'quantity': 10,
        'pnl': 47.50,
        'exit_reason': 'Target Hit'
    }
]

symbol_trades = {
    'NSE:NIFTY2612025450PE': trades
}

# Open chart dialog
dialog = MultiSymbolChartDialog(
    parent=None,
    symbol_data=symbol_data,
    symbol_trades=symbol_trades
)
dialog.exec()
```

## Chart Components

### HTML Template
- **Location**: `agent_trading/trading_system/ui/components/chart_viewer_template.html`
- **Purpose**: TradingView Lightweight Charts integration
- **Technology**: HTML5, JavaScript, Lightweight Charts library (CDN)

### Dialog Classes
- **ChartViewerDialog**: Single symbol chart viewer
- **MultiSymbolChartDialog**: Multi-symbol chart viewer with dropdown selector

### Data Format

#### Candlestick Data
DataFrame with columns:
- `datetime` or `date` or `time`: Timestamp column
- `open`: Opening price
- `high`: Highest price
- `low`: Lowest price
- `close`: Closing price
- `volume`: Trading volume (optional)

#### Trade Data
List of dictionaries with keys:
- `entry_time` or `entry_datetime`: Trade entry timestamp
- `entry_price`: Entry price
- `exit_time` or `exit_datetime`: Trade exit timestamp
- `exit_price`: Exit price
- `quantity`: Trade quantity
- `pnl`: Profit/Loss
- `exit_reason`: Reason for exit (e.g., "Target Hit", "Stop Loss")
- `paper_trade`: Boolean indicating if it's a paper trade (optional)

## Visual Features

### Trade Markers
- **Buy (Entry)**: Green arrow pointing up below the candle with "BUY" label
- **Sell (Exit)**: Color-coded arrow pointing down above the candle with "SELL" label
  - Green for profitable trades
  - Red for losing trades
- **Hover Interaction**: When you hover over a candle with a trade, a detailed panel appears showing:
  - Entry: Price, Quantity, Time
  - Exit: Price, PnL, Exit Reason, Time

### Color Coding
- **Bullish Candles**: Green (#26a69a)
- **Bearish Candles**: Red (#ef5350)
- **Volume Bars**: Semi-transparent matching candle color

### Statistics Display
- Total Trades count
- Win Rate percentage
- Total PnL in ₹

## Controls

### Window Controls
- **⛶ Fullscreen Button**: Toggle between maximized and fullscreen mode
- **Maximize/Minimize**: Standard window controls available
- **Resize**: Drag window edges to resize - chart automatically adjusts
- **ESC Key**: Exit fullscreen mode (when in fullscreen)

### Live Chart Controls
- **📍 Auto-Scroll Toggle**: Enable/disable automatic scrolling to latest data
- **Symbol Selector**: Switch between symbols during backtest
- **🔴 LIVE Indicator**: Shows when chart is receiving live updates

### Chart Interactions
- **Mouse Wheel**: Zoom in/out
- **Click and Drag**: Pan the chart
- **Double Click**: Reset zoom
- **Hover**: View OHLCV data and trade details

## Troubleshooting

### Charts Not Displaying
1. Ensure `PySide6-WebEngine` is installed
2. Check browser console for JavaScript errors (if using exported HTML)
3. Verify candlestick data has valid datetime column

### No Trade Markers
1. Ensure trades have valid `entry_time` and `exit_time` fields
2. Check that trade timestamps fall within the candlestick data range
3. Verify symbol names match between candlestick data and trades

### Trade Markers Overlapping
- The system automatically aligns trade timestamps to the nearest candle timestamp
- If multiple trades occur at the same candle, only one marker per type (entry/exit) is shown
- Hover over the candle to see all trade details in the info panel

### Performance Issues
- Large datasets (>10,000 candles) may slow down rendering
- Consider filtering data to a specific date range
- Use faster chart speed settings in backtest config

## Technical Details

### Dependencies
- PySide6-WebEngine: For rendering HTML/JavaScript charts
- TradingView Lightweight Charts: v4.1.3 (loaded from CDN)
- pandas: For data manipulation

### Browser Compatibility (Exported HTML)
- Chrome/Chromium: ✅ Fully supported
- Firefox: ✅ Fully supported  
- Safari: ✅ Fully supported
- Edge: ✅ Fully supported

## Future Enhancements

Potential improvements:
- [ ] Multiple timeframe support
- [ ] Technical indicator overlays
- [ ] Drawing tools (trendlines, support/resistance)
- [ ] Chart comparison (multiple symbols)
- [ ] Performance metrics overlay
- [ ] Dark/Light theme toggle
