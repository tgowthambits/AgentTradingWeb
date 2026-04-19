# Trading System GUI Application

A Python-based GUI application for the trading system with separate tabs for Intraday Trading and Backtesting.

## Features

- ✅ **Separate Tabs**: Intraday Trading and Backtesting tabs
- ✅ **Full Configuration**: All trading settings can be configured from the UI
- ✅ **Real-time Updates**: Configurations update in real-time during trading/backtesting
- ✅ **Live Result Tables**: Result tables update during backtesting and intraday trading
- ✅ **Position Tracking**: Real-time position and PnL tracking
- ✅ **Trade History**: Complete trade history with detailed metrics

## Running the GUI

### Option 1: Direct Python execution

```bash
cd agent_trading/trading_system/ui
python gui_app.py
```

### Option 2: Using the launcher script

```bash
cd agent_trading/trading_system/ui
python run_gui.py
```

### Option 3: From project root

```bash
python -m agent_trading.trading_system.ui.gui_app
```

## UI Components

### Intraday Trading Tab

**Left Panel - Configuration:**
- **Symbols**: Add/remove trading symbols, configure lot sizes
- **Trading Settings**: Auto-trading, trade directions (BUY/SELL), paper trading, refresh interval, default quantity
- **Indicators**: Enable/disable indicators, adjust weights
- **Risk Management**: Risk per trade, position limits, stop loss, daily limits

**Right Panel - Results:**
- **Control Buttons**: Start/Stop intraday trading, Save/Reload config
- **Status**: Current trading status
- **Open Positions Table**: Real-time position tracking with entry price, quantity, LTP, and PnL
- **Completed Trades Table**: All closed trades with entry/exit prices, PnL, and return %
- **Performance Summary**: Total PnL, win rate, trade statistics

### Backtesting Tab

**Left Panel - Configuration:**
- **Backtest Settings**: Start/end dates, initial capital, speed (fast/realtime), resolution
- **Control Buttons**: Start/Stop backtest, Save config

**Right Panel - Results:**
- **Backtest Status**: Current backtest status
- **Progress Bar**: Visual progress indicator
- **Backtest Results Table**: All trades executed during backtest
- **Backtest Summary**: Final capital, total PnL, returns, win rate, and other metrics

## Configuration Management

### Real-time Configuration Updates

1. **During Trading/Backtesting**: 
   - Click "Save Config" to update the configuration file
   - The running bot will automatically reload the configuration
   - Changes take effect on the next refresh cycle

2. **Before Starting**:
   - Configure all settings in the UI
   - Click "Save Config" to persist changes
   - Start trading/backtesting

### Configuration Sections

1. **Symbols**: List of symbols to trade (e.g., "BSE:SENSEX2610885000PE")
2. **Trading Settings**: 
   - Enable Auto Trading: Automatically execute trades based on signals
   - Allow BUY/SELL: Control which trade directions are allowed
   - Paper Trading: Run in paper trading mode (no real orders)
   - Refresh Interval: Seconds between analysis cycles
   - Default Quantity: Default number of units per trade

3. **Indicators**: 
   - Enable/disable each indicator
   - Adjust indicator weights for signal aggregation

4. **Risk Management**:
   - Risk Per Trade: Percentage of capital to risk per trade
   - Max Position Size: Maximum quantity per position
   - Stop Loss: Maximum loss per trade in ₹
   - Daily Limits: Maximum daily loss and trades per day

5. **Backtest Settings**:
   - Start/End Date: Date range for backtesting
   - Initial Capital: Starting capital for backtest
   - Speed: "fast" (no delays) or "realtime" (respects refresh interval)
   - Resolution: Data resolution (e.g., "30S" for 30 seconds)

## Real-time Updates

### During Intraday Trading

- **Positions Table**: Updates every refresh interval with:
  - Current positions
  - Latest price (LTP)
  - Unrealized PnL
  
- **Trades Table**: Updates when trades are closed with:
  - Trade ID, Symbol, Type
  - Entry/Exit prices
  - Quantity, PnL, Return %

- **Performance Summary**: Updates with:
  - Total PnL (realized + unrealized)
  - Total trades, win rate
  - Open positions count

### During Backtesting

- **Progress Bar**: Shows backtest progress percentage
- **Results Table**: Updates as trades are executed
- **Summary**: Updates with cumulative metrics

## Thread Safety

The GUI uses a message queue system for thread-safe updates:
- Trading bot runs in a separate thread
- UI updates are sent via queue
- Main thread processes queue every 100ms

## Error Handling

- Configuration errors are shown in message boxes
- Trading errors are displayed in status and error dialogs
- Bot continues running even if individual symbol analysis fails

## Integration with Trading System

The GUI integrates with:
- `LiveTradingBot` from `run_live_bot.py`
- `TradingEngine` for analysis and execution
- `DataLoader` for data fetching
- `IndicatorLoader` for dynamic indicator loading

All configurations are saved to `trading_config.yaml` and loaded by the trading system.

## Notes

- The GUI requires tkinter (usually included with Python)
- Configuration changes are saved to YAML files
- Real-time updates may have slight delays due to refresh intervals
- Backtesting can be stopped at any time using the Stop button
