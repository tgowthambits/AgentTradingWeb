# ⚡ Quick Start: Live Trading Bot

## 🚀 Run Live Bot (5 Second Refresh)

```bash
cd /home/sham/Desktop/MARKOV_MARKET
./start_trading_bot.sh
```

**OR**

```bash
python trading_system/run_live_bot.py
```

---

## ⚙️ Quick Configuration

Edit `trading_system/config/trading_config.yaml`:

### Monitor Only (Safe)
```yaml
trading:
  enable_auto_trading: false  # Just watch, no orders
  refresh_interval: 5
```

### Auto-Trade Enabled
```yaml
trading:
  enable_auto_trading: true   # Execute orders automatically
  refresh_interval: 5
```

---

## 📊 What You'll See

```
🤖 Live Trading Bot | Refresh #42 | Auto-Trade: ON

Symbol         LTP      Signal   Position
SENSEX...PE    330.95   BUY      LONG
NIFTY...PE     69.60    BUY      LONG

Open Positions: 2
Total PnL: ₹+125.50

⏱  Next refresh in: 5s
```

---

## 🎯 Quick Commands

### Start Bot
```bash
./start_trading_bot.sh
```

### Stop Bot
Press `Ctrl+C`

### One-Time Analysis (No Loop)
```bash
python trading_system/run_trading_system.py
```

---

## ⚠️ Safety

- **Default**: Monitor only (no auto-trade)
- **Test first**: Run with `enable_auto_trading: false`
- **Stop anytime**: Press `Ctrl+C`

---

## 📖 Full Documentation

- **LIVE_BOT_GUIDE.md** - Complete bot guide
- **README.md** - System overview
- **HOW_TO_ADD_INDICATORS.md** - Add indicators

---

## 🎉 That's It!

**Bot checks every 5 seconds automatically!** 🤖📈

