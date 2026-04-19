# Summary Table Enhancements - Beautification & Trend Visualization

## ✅ Enhancements Implemented

### 1. **Beautiful Color-Coded Table**
The summary table now features professional color coding:

- **Category Headers**: Gray background (`#e8e8e8`) with bold text
- **Profit Values**: Green background (`#d4edda`) with dark green text (`#155724`)
- **Loss Values**: Red background (`#f8d7da`) with dark red text (`#721c24`)
- **Neutral Values**: White background

**Color Logic:**
- Positive metrics (PnL, returns, win rate ≥50%, ratios): Green
- Negative metrics (losses, drawdown, win rate <50%): Red
- Zero/neutral values: White

### 2. **Improved Table Structure**
- Better column alignment (left for metrics, right for values)
- Wider columns for better readability
- Category headers with visual separation
- Professional font styling

### 3. **Clickable Trend Visualization**
- **Double-click any metric value** to view its trend chart
- Interactive matplotlib charts with:
  - Line plot with markers
  - Filled area under curve
  - Current value indicator (red dashed line)
  - Min/Max markers
  - Interactive toolbar (zoom, pan, save)
  - Professional styling

### 4. **Historical Data Tracking**
Metrics are tracked during backtesting:
- Total PnL
- Equity (Final Capital)
- Return %
- Win Rate
- Sharpe Ratio
- Sortino Ratio
- Calmar Ratio
- Max Drawdown
- Profit Factor
- Expectancy
- Average Win/Loss

## Visual Improvements

### Color Scheme
```
Category Headers:  #e8e8e8 (Light Gray)
Profit Values:     #d4edda (Light Green) / #155724 (Dark Green Text)
Loss Values:       #f8d7da (Light Red) / #721c24 (Dark Red Text)
Neutral Values:    #ffffff (White)
```

### Table Structure
- **Metric Column**: 320px width, left-aligned
- **Value Column**: 220px width, right-aligned
- **Category Headers**: Bold, gray background
- **Hint Label**: "💡 Double-click on any metric value to view its trend chart"

## Trend Chart Features

### Chart Elements
1. **Main Line**: Colored line with markers showing metric progression
2. **Filled Area**: Semi-transparent fill under the curve
3. **Current Value**: Red dashed horizontal line
4. **Min/Max Markers**: Green triangle (max) and red triangle (min)
5. **Grid**: Light gray grid for easy reading
6. **Legend**: Shows current, max, and min values

### Chart Colors
- **Positive Metrics** (PnL, Equity, Win Rate, Ratios): Green (`#2e7d32`)
- **Negative Metrics** (Drawdown, Losses): Red (`#c62828`)
- **Neutral Metrics**: Blue (`#1976d2`)

### Interactive Features
- **Zoom**: Click and drag to zoom
- **Pan**: Click and drag to pan
- **Reset**: Reset view to original
- **Save**: Save chart as image
- **Navigation**: Full matplotlib toolbar

## Usage

### Viewing Trends
1. Run a backtest
2. Wait for metrics to accumulate (need at least 2 data points)
3. Double-click on any metric value in the summary table
4. A new window opens showing the trend chart
5. Use the toolbar to interact with the chart

### Supported Metrics for Trends
- Total PnL
- Return %
- Win Rate
- Sharpe Ratio
- Sortino Ratio
- Calmar Ratio
- Max Drawdown
- Profit Factor
- Final Capital (Equity)
- Average Win
- Average Loss
- Expectancy per Trade

## Technical Details

### Data Storage
- Metrics history stored in `self.metrics_history` dictionary
- Updated every backtest iteration
- Reset when starting new backtest

### Chart Library
- Uses `matplotlib` with TkAgg backend
- Embedded in tkinter Toplevel window
- Full navigation toolbar included

### Click Handler
- Double-click event bound to summary tree
- Extracts metric key from tree item
- Validates data availability
- Opens trend window if sufficient data

## Dependencies

To use trend visualization, install matplotlib:
```bash
pip install matplotlib
```

If matplotlib is not installed, a helpful error message will be shown.

## Benefits

1. **Visual Clarity**: Color coding makes profits/losses instantly recognizable
2. **Professional Appearance**: Clean, organized table structure
3. **Trend Analysis**: Understand how metrics evolve during backtesting
4. **Interactive Exploration**: Zoom, pan, and analyze trends in detail
5. **Better Decision Making**: Visual trends help identify patterns and issues

## Example Use Cases

- **Monitor PnL**: Watch how total profit/loss changes over iterations
- **Track Win Rate**: See if win rate improves or degrades over time
- **Analyze Risk**: Monitor Sharpe ratio and drawdown trends
- **Performance Analysis**: Compare different metrics side-by-side
- **Strategy Optimization**: Identify when metrics peak or decline
