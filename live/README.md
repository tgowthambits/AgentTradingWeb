# Real-Time Trading System

Real-time trading system that runs inference every 5 seconds and executes trades based on model signals (long-only strategy).

## Features

- ✅ **5-second interval monitoring**: Continuously checks for trading signals
- ✅ **Position tracking**: Monitors active positions and PnL
- ✅ **Long-only strategy**: Only buys and sells, never shorts
- ✅ **PnL monitoring**: Real-time unrealized and realized PnL tracking
- ✅ **Order history**: Complete record of all trades

## Trading Logic

The system implements a **long-only** strategy:

- **BUY Signal (1) + No Position** → Buy
- **BUY Signal (1) + Have Position** → Hold (maintain position)
- **SELL Signal (-1) + Have Position** → Sell (close position)
- **SELL Signal (-1) + No Position** → Hold (don't short)
- **HOLD Signal (0)** → Hold (no action)

## Usage

### Start Real-Time Trading

```bash
python -m live.run_realtime
```

Or:

```bash
python live/run_realtime.py
```

### Configuration

Edit `live/run_realtime.py` to configure:

```python
QUANTITY = 1   # Number of shares/units per trade
INTERVAL = 5   # Seconds between checks
```

### Stop Trading

Press `Ctrl+C` to stop the system. It will print final status including:
- Total realized PnL
- Unrealized PnL (if position is open)
- Number of closed trades

## Output Format

The system prints formatted status updates every 5 seconds:

```
======================================================================
 2025-12-20 10:30:15 - Real-time Trading Update
======================================================================

┌─ POSITION STATUS ───────────────────────────────────────────────┐
│ Position:          LONG (1 units)                                 │
│ Entry Price:       ₹8450.00                                       │
│ Current Price:      ₹8460.00                                       │
│ Unrealized PnL:    ₹10.00                                         │
│ Duration:          45 seconds                                      │
│ Total Realized PnL: ₹50.00                                        │
│ Total PnL:          ₹60.00                                         │
│ Closed Trades:      2                                             │
└──────────────────────────────────────────────────────────────────┘

┌─ TRADING ACTION ──────────────────────────────────────────────────┐
│ ⚪ HOLD: BUY signal but already in position                        │
└──────────────────────────────────────────────────────────────────┘

┌─ MODEL SIGNAL ─────────────────────────────────────────────────────┐
│ Final Signal: BUY                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Files

- `position_tracker.py`: Tracks positions, orders, and calculates PnL
- `realtime_trader.py`: Main trading loop and decision logic
- `run_realtime.py`: Entry point script

## Integration with Broker API

To integrate with actual broker API (e.g., Fyers), modify the `decide_action` method in `realtime_trader.py` to place actual orders:

```python
def decide_action(self, signal: int, current_price: float):
    # ... existing logic ...
    
    if action == "BUY":
        # Place actual buy order via broker API
        broker_api.place_order(symbol, quantity, "BUY", current_price)
    
    elif action == "SELL":
        # Place actual sell order via broker API
        broker_api.place_order(symbol, quantity, "SELL", current_price)
```

## Notes

- The system currently tracks positions **simulated** (doesn't place real orders)
- To enable real trading, integrate with your broker's API
- All PnL calculations are based on entry/exit prices
- Order history is stored in memory (not persisted to disk)

