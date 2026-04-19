# 🤖 Live Trading Bot Guide

## ✨ Real-Time Trading Bot

A **continuous monitoring bot** that:
- ✅ Checks signals every 5 seconds
- ✅ Analyzes all symbols automatically
- ✅ Executes trades based on indicators
- ✅ Tracks positions and PnL in real-time
- ✅ Beautiful live-updating display

---

## 🚀 Quick Start

### Method 1: Using Launcher Script (Easiest)

```bash
cd /home/sham/Desktop/MARKOV_MARKET
./start_trading_bot.sh
```

### Method 2: Direct Python

```bash
cd /home/sham/Desktop/MARKOV_MARKET
python trading_system/run_live_bot.py
```

---

## 📊 What You'll See

### Real-Time Display

```
╭────────────────────────────────────────────────────────────────────────╮
│ 🤖 Live Trading Bot | Refresh #42 | 2025-12-29 14:23:15 | Auto-Trade: ON │
╰────────────────────────────────────────────────────────────────────────╯

╭──────────────────────────────────────────────────────────────────────────╮
│                      📊 Real-Time Analysis                                │
├──────────────┬─────────┬────────┬───────┬───┬───┬───┬──────────┤
│ Symbol       │ LTP (₹) │ Signal │ Agree │ B │ S │ H │ Position │
├──────────────┼─────────┼────────┼───────┼───┼───┼───┼──────────┤
│ SENSEX...PE  │ 330.95  │ BUY    │ 75%   │ 3 │ 0 │ 1 │ LONG     │
│ SENSEX...CE  │ 209.05  │ HOLD   │ 50%   │ 2 │ 1 │ 1 │ -        │
│ NIFTY...PE   │ 69.60   │ BUY    │ 100%  │ 4 │ 0 │ 0 │ LONG     │
│ NIFTY...CE   │ 35.80   │ SELL   │ 75%   │ 0 │ 3 │ 1 │ -        │
╰──────────────┴─────────┴────────┴───────┴───┴───┴───┴──────────╯

╭────────────────────────────────────────────────────────────────────────╮
│                      📊 Open Positions                                  │
├────┬──────────────────┬──────┬───────────┬─────────────────────┬─────┤
│ ID │ Symbol           │ Type │ Entry (₹) │ Entry Time          │ Qty │
├────┼──────────────────┼──────┼───────────┼─────────────────────┼─────┤
│ 1  │ SENSEX...100PE   │ LONG │ 330.95    │ 2025-12-29 14:15:30 │ 1   │
│ 3  │ NIFTY...050PE    │ LONG │ 69.60     │ 2025-12-29 14:18:45 │ 1   │
╰────┴──────────────────┴──────┴───────────┴─────────────────────┴─────╯

╭────────────────────────────────────────────────────────────────────────╮
│                      ✅ Recent Closed Orders                            │
├────┬──────────────────┬──────┬───────────┬─────────────────────┤
│ ID │ Symbol           │ Type │ PnL (₹)   │ Exit Time           │
├────┼──────────────────┼──────┼───────────┼─────────────────────┤
│ 2  │ SENSEX...100CE   │ LONG │ +6.25     │ 2025-12-29 14:17:20 │
│ 4  │ NIFTY...050CE    │ SHORT│ +2.50     │ 2025-12-29 14:20:15 │
╰────┴──────────────────┴──────┴───────────┴─────────────────────╯

╭────────────────────────────────────────────────────────────────────────╮
│                      📈 Trading Summary                                 │
├────────────────────────────────────────────────────────────────────────┤
│ Statistics:                                                             │
│   Total Orders: 4                                                       │
│   Open Positions: 2                                                     │
│   Closed Orders: 2                                                      │
│   Total PnL: ₹+8.75                                                     │
│   Signals Generated: 12                                                 │
│   Indicators Active: 4                                                  │
╰────────────────────────────────────────────────────────────────────────╯

⏱  Next refresh in: 5s  |  Press Ctrl+C to stop
```

---

## ⚙️ Configuration

Edit `trading_system/config/trading_config.yaml`:

### Basic Settings

```yaml
# Symbols to monitor
symbols:
  - "BSE:SENSEX2610185100PE"
  - "NSE:NIFTY25DEC26050PE"

# How often to check (seconds)
trading:
  refresh_interval: 5  # Check every 5 seconds
```

### Auto-Trading

```yaml
trading:
  enable_auto_trading: false  # ⚠️ Set to true for automatic orders
  default_quantity: 1
```

**⚠️ Important:**
- `false` = **Monitor only** (no orders placed)
- `true` = **Auto-trade** (orders executed automatically)

### Indicators

```yaml
indicators:
  rsi:
    enabled: true   # Include in analysis
    weight: 1.0     # Standard importance
  
  macd:
    enabled: false  # Exclude from analysis
```

---

## 🎯 How It Works

### 1. Continuous Loop

```
Load Data → Execute Indicators → Aggregate Signals → Make Decision
    ↓            ↓                    ↓                   ↓
  Every       All Active         Combined          BUY/SELL/HOLD
  5 secs      Indicators         Signal               ↓
                                                  Execute Order
                                                  (if auto-trade ON)
    ↑                                                   ↓
    └───────────────── Wait 5s ─────────────────────────┘
```

### 2. Signal Generation

```
Refresh 1:
  RSI: BUY
  MACD: BUY
  MA: BUY
  Bollinger: HOLD
  → Final: BUY (75% agreement)
  → Action: Open LONG @ ₹330.95

Refresh 2 (5s later):
  RSI: BUY
  MACD: HOLD
  MA: BUY
  Bollinger: HOLD
  → Final: BUY (still)
  → Action: Hold LONG (no duplicate)

Refresh 3 (5s later):
  RSI: HOLD
  MACD: HOLD
  MA: HOLD
  Bollinger: SELL
  → Final: HOLD (mixed signals)
  → Action: Close LONG @ ₹335.50 (PnL: +₹4.55)
```

---

## 📊 Display Sections

### 1. Header
- Refresh count
- Current time
- Auto-trade status

### 2. Real-Time Analysis
- Latest price for each symbol
- Final signal (BUY/SELL/HOLD)
- Agreement score (consensus strength)
- Signal breakdown (B/S/H counts)
- Current position

### 3. Open Positions
- All active trades
- Entry price and time
- Quantity

### 4. Recent Closed Orders
- Last 5 closed trades
- PnL for each
- Exit time

### 5. Trading Summary
- Total orders
- Open/closed counts
- Total PnL
- Active indicators

---

## ⚠️ Safety Features

### 1. Duplicate Order Prevention

```python
# Won't create duplicate orders
if signal == 'BUY' and position == 'LONG':
    # Hold existing position (no new order)
    pass
```

### 2. Auto-Trade Toggle

```yaml
enable_auto_trading: false  # Safe default (monitor only)
```

### 3. Paper Trading Mode

```yaml
paper_trading: true  # Simulate without real money
```

### 4. Keyboard Interrupt

Press `Ctrl+C` to stop anytime:
```
🛑 Stopping bot...

📊 Final Summary:
  Total Refreshes: 42
  Total Orders: 8
  Total PnL: ₹+125.50

✅ Bot stopped successfully!
```

---

## 🎛️ Operating Modes

### Mode 1: Monitor Only (Safest)

```yaml
trading:
  enable_auto_trading: false
```

**What happens:**
- ✅ Displays signals
- ✅ Shows recommendations
- ❌ **No orders executed**
- ✅ Perfect for testing

### Mode 2: Paper Trading

```yaml
trading:
  enable_auto_trading: true
  paper_trading: true
```

**What happens:**
- ✅ Simulates order execution
- ✅ Tracks PnL
- ✅ No real money
- ✅ Perfect for strategy testing

### Mode 3: Live Trading (⚠️ Real Money!)

```yaml
trading:
  enable_auto_trading: true
  paper_trading: false
  live_mode: true
```

**What happens:**
- ⚠️ **REAL ORDERS EXECUTED**
- ⚠️ **REAL MONEY AT RISK**
- ✅ Live trading
- ⚠️ Use with caution!

---

## 🔧 Customization

### Change Refresh Rate

```yaml
trading:
  refresh_interval: 10  # Check every 10 seconds (slower)
  refresh_interval: 3   # Check every 3 seconds (faster)
```

### Show/Hide Indicator Details

```yaml
output:
  verbose: true   # Show individual indicator signals
  verbose: false  # Show only final signals
```

### Adjust Quantity

```yaml
trading:
  default_quantity: 1   # Standard
  default_quantity: 5   # Trade 5 lots per signal
```

---

## 📈 Performance Monitoring

### Real-Time Metrics

The bot tracks:
- **Refresh Count** - How many analysis cycles completed
- **Total Orders** - Orders placed since start
- **Open Positions** - Currently active trades
- **Closed Orders** - Completed trades
- **Total PnL** - Cumulative profit/loss
- **Signals Generated** - Trading signals created
- **Agreement Score** - Indicator consensus strength

### Example Stats

```
Statistics:
  Total Orders: 24
  Open Positions: 3
  Closed Orders: 21
  Total PnL: ₹+450.25
  Signals Generated: 48
  Indicators Active: 4
  
Win Rate: 85% (18 wins, 3 losses)
Average PnL per Trade: ₹+21.44
```

---

## 🐛 Troubleshooting

### Bot Not Starting

```bash
# Check Python path
which python

# Try with python3
python3 trading_system/run_live_bot.py

# Check dependencies
pip install -r requirements.txt
```

### Data Loading Errors

```python
# Error: "Could not import FyersDataScanner"
# Solution: Ensure Data/ folder exists
```

### No Signals Generated

```yaml
# Check indicator configuration
indicators:
  rsi:
    enabled: true  # Make sure at least one is enabled
```

### Orders Not Executing

```yaml
# Check auto-trade setting
trading:
  enable_auto_trading: true  # Must be true
```

---

## 💡 Tips & Best Practices

### 1. Start with Monitor Mode
- Run bot with `enable_auto_trading: false`
- Observe signals for a day
- Verify logic before auto-trading

### 2. Test with Paper Trading
- Enable paper trading first
- Verify PnL calculations
- Test different indicators

### 3. Adjust Refresh Rate
- **5 seconds**: Good for most cases
- **10+ seconds**: For slower strategies
- **< 5 seconds**: For high-frequency trading

### 4. Monitor Closely
- Watch first few hours actively
- Check PnL regularly
- Stop if unexpected behavior

### 5. Use Stop Loss
- Consider adding stop-loss indicators
- Monitor max drawdown
- Set daily loss limits

---

## 🎯 Example Session

### Starting the Bot

```bash
$ ./start_trading_bot.sh

🤖 Starting Live Trading Bot...

Symbols: BSE:SENSEX2610185100PE, NSE:NIFTY25DEC26050PE
Refresh Interval: 5s
Auto-Trading: DISABLED
Indicators: 4 active

Press Ctrl+C to stop
```

### After 1 Hour

```
Refresh #720 (1 hour of 5s intervals)

Statistics:
  Total Orders: 12
  Open Positions: 2
  Closed Orders: 10
  Total PnL: ₹+85.50
  Signals Generated: 28
```

### Stopping

```
^C
🛑 Stopping bot...

📊 Final Summary:
  Total Refreshes: 720
  Total Orders: 12
  Total PnL: ₹+85.50

✅ Bot stopped successfully!
```

---

## 🔐 Safety Checklist

Before enabling auto-trading:

- [ ] Tested in monitor mode
- [ ] Verified indicators working correctly
- [ ] Checked signal logic
- [ ] Tested with paper trading
- [ ] Set appropriate position sizes
- [ ] Understood risk
- [ ] Have stop-loss strategy
- [ ] Monitoring actively
- [ ] Know how to stop (Ctrl+C)
- [ ] Comfortable with potential losses

---

## 📚 Related Documentation

- **README.md** - System overview
- **HOW_TO_ADD_INDICATORS.md** - Custom indicators
- **SYSTEM_OVERVIEW.md** - Architecture details
- **trading_config.yaml** - Configuration reference

---

## 🎉 Summary

**You now have a:**
- ✅ **Real-time trading bot**
- ✅ **Auto-refresh every 5 seconds**
- ✅ **Live signal monitoring**
- ✅ **Automatic order execution** (optional)
- ✅ **Beautiful display**
- ✅ **Safe defaults**

**Perfect for:**
- Live trading
- Strategy testing
- Signal monitoring
- Performance tracking

---

## 🚀 Start Trading!

```bash
cd /home/sham/Desktop/MARKOV_MARKET
./start_trading_bot.sh
```

**The bot will:**
1. Load indicators
2. Start monitoring
3. Check every 5 seconds
4. Display results live
5. Execute trades (if enabled)

**Press Ctrl+C to stop anytime!**

---

**Happy Bot Trading!** 🤖📈💰

