# Backtest Mode - Quick Start Guide

## 🚀 Quick Start (30 seconds)

### Run a Backtest

1. **Edit** `trading_system/config/trading_config.yaml`:
   ```yaml
   backtest:
     enabled: true    # <-- Change this to true
   ```

2. **Run**:
   ```bash
   python trading_system/run_live_bot.py
   ```

3. **Done!** Watch your strategy trade through historical data.

### Return to Live Trading

1. **Edit** `trading_system/config/trading_config.yaml`:
   ```yaml
   backtest:
     enabled: false   # <-- Change this to false
   ```

2. **Run**:
   ```bash
   python trading_system/run_live_bot.py
   ```

3. **Done!** Back to live trading.

---

## ⚙️ Configuration Options

### Full Config Block

```yaml
backtest:
  enabled: false                      # true = backtest, false = live
  start_date: '2025-12-01 09:15:00'  # Backtest start
  end_date: '2025-12-30 15:30:00'    # Backtest end
  initial_capital: 100000             # Starting capital
  speed: 'fast'                       # 'fast' or 'realtime'
```

### Speed Options

| Speed | Description | Use Case |
|-------|-------------|----------|
| `fast` | No delays, maximum speed | Quick testing, parameter optimization |
| `realtime` | Respects `refresh_interval` | Realistic timing, final validation |

---

## 📊 What You'll See

### During Backtest

```
🔄 BACKTEST MODE ENABLED
Period: 2025-12-01 09:15:00 to 2025-12-30 15:30:00
Initial Capital: ₹100,000.00
Speed: fast

Progress: [████████████░░░░░░░░] 62.5% (2500/4000 bars)

[Live updating tables with positions and signals]
```

### After Completion

```
📊 BACKTEST SUMMARY

Capital:
  Initial: ₹100,000.00
  Final: ₹105,450.00
  Return: +5.45%

Trading Performance:
  Total Trades: 45
  Winning Trades: 28
  Losing Trades: 17
  Win Rate: 62.22%

Profit & Loss:
  Total PnL: ₹+5,450.00
  Avg Win: ₹+320.50
  Avg Loss: ₹-180.25
```

---

## 🧪 Test Installation

```bash
python test_backtest_mode.py
```

**Expected**: 4/4 tests passing

---

## 📖 Need More Details?

- **Full Guide**: See `BACKTEST_MODE_GUIDE.md`
- **Implementation Details**: See `BACKTEST_IMPLEMENTATION_COMPLETE.md`

---

## ⚡ One-Line Reference

**Backtest**: `enabled: true` → Run bot  
**Live**: `enabled: false` → Run bot  

That's it! 🎉

