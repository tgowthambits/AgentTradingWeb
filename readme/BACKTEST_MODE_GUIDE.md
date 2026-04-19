# Backtest Mode Implementation Guide

## Overview

The trading system now supports **progressive backtesting mode** that simulates real-time data feed using historical data. This allows you to test your strategies exactly as they would run in live mode, but with historical data being fed row-by-row.

## Key Features

✅ **Progressive Data Feed**: Returns 1 row, then 2 rows, then 3 rows, etc. on each iteration  
✅ **Zero Strategy Changes**: All indicator and trading logic remains identical  
✅ **Config-Based Control**: Enable/disable with a simple flag  
✅ **Speed Control**: Run fast or simulate real-time with delays  
✅ **Progress Tracking**: Visual progress bar during backtest  
✅ **Comprehensive Summary**: Detailed performance metrics after completion  

## Architecture

### Data Flow

**Live Mode:**
```
API → Latest Data → Indicators → Strategy → Trades
```

**Backtest Mode:**
```
API (once) → Cached Full Dataset → Progressive Slices → Indicators → Strategy → Trades
```

### How Progressive Data Works

```
Iteration 1: Returns rows [0:1]       → 1 row total
Iteration 2: Returns rows [0:2]       → 2 rows total
Iteration 3: Returns rows [0:3]       → 3 rows total
...
Iteration n: Returns rows [0:n]       → n rows total
```

This simulates how indicators would see accumulating historical data in real-time trading.

## Configuration

### Enable Backtest Mode

Edit `trading_system/config/trading_config.yaml`:

```yaml
backtest:
  enabled: true                          # Enable backtest mode
  start_date: '2025-12-01 09:15:00'     # Backtest start date
  end_date: '2025-12-30 15:30:00'       # Backtest end date
  initial_capital: 100000                # Starting capital
  speed: 'fast'                          # 'fast' or 'realtime'
```

### Speed Options

- **`fast`**: Runs as quickly as possible (no delays between iterations)
- **`realtime`**: Respects `refresh_interval` setting for realistic timing

### Disable Backtest Mode (Return to Live Trading)

```yaml
backtest:
  enabled: false
```

## Usage

### Running a Backtest

1. **Configure backtest settings** in `trading_config.yaml`
2. **Run the bot**:
   ```bash
   python trading_system/run_live_bot.py
   ```

3. **Monitor progress**:
   - Progress bar shows completion percentage
   - Current iteration and total bars displayed
   - Results updated in real-time

4. **Review results**:
   - Comprehensive summary displayed at completion
   - Includes win rate, PnL, capital changes, etc.

### Running Live Trading

1. **Set `backtest.enabled: false`** in config
2. **Run the bot** (same command):
   ```bash
   python trading_system/run_live_bot.py
   ```

## Implementation Details

### New Classes

#### `BacktestDataGenerator`

Located in `trading_system/data/data_loader.py`

**Purpose**: Manages progressive data slicing for backtesting

**Key Methods**:
- `__init__()`: Fetches all historical data once
- `get_next_slice()`: Returns progressively larger data slices
- `progress()`: Returns current progress (current/total rows, percentage)
- `reset()`: Resets to beginning
- `is_complete()`: Checks if backtest is done

### Modified Classes

#### `DataLoader`

**New Parameters**:
- `backtest_mode` (bool): Enable backtest mode
- `backtest_config` (dict): Backtest configuration

**Behavior**:
- In **live mode**: Fetches latest data from API (unchanged)
- In **backtest mode**: Returns progressive slices from cached data

#### `LiveTradingBot`

**New Methods**:
- `run()`: Routes to `run_live()` or `run_backtest()` based on mode
- `run_backtest()`: Backtesting loop with progress tracking
- `show_backtest_summary()`: Displays comprehensive backtest results

**Modified**:
- `__init__()`: Detects backtest mode and configures DataLoader accordingly

## Output Examples

### Backtest Start

```
🔄 BACKTEST MODE ENABLED
Period: 2025-12-01 09:15:00 to 2025-12-30 15:30:00
Initial Capital: ₹100,000.00
Speed: fast

🔄 Starting Backtest...

Symbols: BSE:SENSEX2610185100PE, NSE:NIFTY2610626000CE
Speed: FAST
Indicators: 5 active
```

### During Backtest

```
Progress: [████████████░░░░░░░░] 62.5% (2500/4000 bars)

Backtest Iteration: 2500

┌─ Complete Trading Analysis - All Symbols ─┐
│ Symbol    Signal  Price    Position  PnL   │
│ SENSEX    ▲ BUY   18500.0  LONG     +450   │
│ NIFTY     ○ HOLD  26100.0  -        -      │
└────────────────────────────────────────────┘
```

### Backtest Summary

```
================================================================================
┌───────────────────────────────────────────────────────────────────────────┐
│                         📊 BACKTEST SUMMARY                                │
│                                                                            │
│ Period:                                                                    │
│   Start: 2025-12-01 09:15:00                                              │
│   End: 2025-12-30 15:30:00                                                │
│                                                                            │
│ Capital:                                                                   │
│   Initial: ₹100,000.00                                                    │
│   Final: ₹105,450.00                                                      │
│   Return: +5.45%                                                          │
│                                                                            │
│ Trading Performance:                                                       │
│   Total Trades: 45                                                         │
│   Winning Trades: 28                                                       │
│   Losing Trades: 17                                                        │
│   Win Rate: 62.22%                                                        │
│                                                                            │
│ Profit & Loss:                                                            │
│   Total PnL: ₹+5,450.00                                                   │
│   Avg Win: ₹+320.50                                                       │
│   Avg Loss: ₹-180.25                                                      │
│   Realized PnL: ₹+5,450.00                                                │
│                                                                            │
│ Statistics:                                                                │
│   Total Refreshes: 4000                                                    │
│   Symbols Traded: 2                                                        │
└───────────────────────────────────────────────────────────────────────────┘
================================================================================
```

## Testing

Run the test suite to verify implementation:

```bash
python test_backtest_mode.py
```

**Expected Output**: All 4 tests should pass
- Config Loading
- DataLoader Live Mode
- DataLoader Backtest Mode
- Progressive Data Concept

## Key Benefits

1. **Realistic Testing**: Simulates real-time data accumulation exactly as in live trading
2. **No Code Changes**: Strategy logic remains completely unchanged
3. **Fast Iteration**: Test months of data in minutes with `speed: 'fast'`
4. **Detailed Metrics**: Comprehensive performance analysis
5. **Easy Switching**: Toggle between live and backtest with one config change

## Important Notes

### Data Requirements

- Backtest requires historical data from the Fyers API
- Date range must be valid and have available data
- Resolution setting applies to backtest data fetch

### Memory Considerations

- Full dataset is loaded into memory at start
- For very long date ranges, consider splitting into multiple backtests

### Indicator Behavior

- Indicators receive progressively more data on each iteration
- This accurately simulates real-time indicator calculations
- Early iterations may not have enough data for some indicators (e.g., 200-period MA needs 200+ bars)

### Position Tracking

- All position tracking works identically in both modes
- PnL calculations are accurate and tracked per iteration
- Web UI integration works in backtest mode (optional)

## Troubleshooting

### "FyersDataScanner not available"

**Solution**: Ensure `Data/fyers_data_final.py` exists and API is configured

### "Backtest complete" appears immediately

**Possible causes**:
- Invalid symbol format
- Date range has no data
- API authentication issues

**Solution**: Check symbol names and date range, verify API access

### Indicators showing incorrect signals

**Expected behavior**: Early iterations may not have enough historical data for some indicators. This is realistic - in live trading, indicators also need time to accumulate data.

## Examples

### Quick Backtest (1 Day)

```yaml
backtest:
  enabled: true
  start_date: '2025-12-28 09:15:00'
  end_date: '2025-12-28 15:30:00'
  initial_capital: 100000
  speed: 'fast'
```

### Extended Backtest (1 Month)

```yaml
backtest:
  enabled: true
  start_date: '2025-12-01 09:15:00'
  end_date: '2025-12-31 15:30:00'
  initial_capital: 100000
  speed: 'fast'
```

### Realistic Timing Backtest

```yaml
backtest:
  enabled: true
  start_date: '2025-12-20 09:15:00'
  end_date: '2025-12-27 15:30:00'
  initial_capital: 100000
  speed: 'realtime'  # Respects refresh_interval
```

## File Changes Summary

### New Files
- `test_backtest_mode.py`: Test suite for backtest implementation
- `BACKTEST_MODE_GUIDE.md`: This documentation

### Modified Files
- `trading_system/config/trading_config.yaml`: Added `backtest` section
- `trading_system/data/data_loader.py`: Added `BacktestDataGenerator` class, updated `DataLoader`
- `trading_system/run_live_bot.py`: Added `run_backtest()`, `show_backtest_summary()`, split `run()` method

### Lines of Code Added
- ~200 lines of new functionality
- Zero changes to existing strategy logic

## Support

For issues or questions:
1. Run `python test_backtest_mode.py` to verify setup
2. Check console output for error messages
3. Verify `trading_config.yaml` backtest section is properly formatted
4. Ensure date ranges and symbols are valid

---

**Version**: 1.0  
**Last Updated**: January 1, 2026  
**Status**: ✅ Implementation Complete & Tested

