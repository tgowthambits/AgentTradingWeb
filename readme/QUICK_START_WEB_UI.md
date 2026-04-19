# 🚀 Web UI - Quick Start Guide

## ⚡ 3-Step Setup

### Step 1: Install

```bash
./setup_web_ui.sh
```

Wait for "✅ Setup Complete!"

### Step 2: Start

```bash
./start_bot_with_ui.sh
```

You'll see:
```
🚀 Starting Trading System with Web UI
================================================

🌐 Starting Web UI Server in background...
   ✅ Web UI Server started
   📊 Dashboard: http://localhost:8000

🤖 Starting Trading Bot...
   ✅ Web UI integration enabled
```

### Step 3: Open Browser

Navigate to: **http://localhost:8000**

---

## 📊 What You'll See

```
╔════════════════════════════════════════════════════════════╗
║  🤖 Markov Market Trading System                          ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ ║
║  │ PnL      │  │ Win Rate │  │ Trades   │  │ Uptime   │ ║
║  │ ₹+1,234  │  │ 65.5%    │  │ 42       │  │ 2h 15m   │ ║
║  └──────────┘  └──────────┘  └──────────┘  └──────────┘ ║
║                                                            ║
║  ┌──────────────────────────────┐  ┌─────────────────┐   ║
║  │                              │  │ Symbols         │   ║
║  │   TradingView Chart          │  │ ┌─────────────┐ │   ║
║  │   📊 Candlesticks            │  │ │ SENSEX PE   │ │   ║
║  │   📈 Volume                   │  │ │ ₹392.95     │ │   ║
║  │   🎯 Interactive              │  │ │ [HOLD]      │ │   ║
║  │                              │  │ └─────────────┘ │   ║
║  │                              │  │                 │   ║
║  │                              │  │ Signal Details  │   ║
║  │                              │  │ - RSI: HOLD     │   ║
║  │                              │  │ - MACD: BUY     │   ║
║  └──────────────────────────────┘  └─────────────────┘   ║
║                                                            ║
║  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐ ║
║  │ Positions    │  │ Indicators   │  │ Recent Trades   │ ║
║  │ Open: 3      │  │ ✓ RSI        │  │ +137.50         │ ║
║  │ PnL: +50.00* │  │ ✓ MACD       │  │ -125.00         │ ║
║  └──────────────┘  └──────────────┘  └─────────────────┘ ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
```

---

## 🎯 Key Features

### 1. Real-Time Updates ⚡
- Live price updates
- Instant signal changes
- PnL tracking
- Position monitoring

### 2. TradingView Charts 📊
- Professional candlestick charts
- Interactive controls (pan, zoom)
- Volume overlay
- Multiple timeframes

### 3. Complete Analytics 📈
- Win rate and PnL
- Trade history
- Open positions
- Performance metrics

### 4. Symbol Selection 🎯
- Click any symbol to view
- Color-coded signals
- Live price updates
- Signal details

### 5. Event Monitoring 📝
- Real-time bot activity
- Trade execution logs
- System events
- Error tracking

---

## 🎨 Visual Guide

### Color Coding

| Color | Meaning |
|-------|---------|
| 🟢 Green | BUY signal / Profit |
| 🔴 Red | SELL signal / Loss |
| ⚪ Gray | HOLD signal / Neutral |
| 🔵 Blue | Selected / Active |

### Status Indicators

| Icon | Status |
|------|--------|
| ✅ | Connected / Running |
| ❌ | Disconnected / Stopped |
| ⏸️ | Paused / Waiting |
| ⚠️ | Warning / Error |

---

## ⚙️ Quick Controls

### Refresh Interval

Edit `trading_system/config/trading_config.yaml`:

```yaml
trading:
  refresh_interval: 5  # Seconds between updates
```

### Trade Directions

```yaml
trading:
  allow_buy: true   # Enable BUY signals
  allow_sell: true  # Enable SELL signals
```

### Auto Trading

```yaml
trading:
  enable_auto_trading: true  # Execute trades automatically
```

---

## 🔧 Common Tasks

### View Different Symbol

**Click on any symbol card** in the right panel.

Chart automatically loads with OHLCV data.

### Check Position PnL

Look at **"Open Positions"** section.

`*` indicates unrealized PnL (position still open).

### View Trade History

Scroll **"Recent Trades"** section.

Shows entry, exit, quantity, and PnL.

### Monitor Bot Events

Check **"Event Log"** at bottom right.

Real-time stream of bot activity.

---

## 📱 Access from Phone/Tablet

### Same Network

1. Find server IP:
   ```bash
   hostname -I
   ```

2. Open on device:
   ```
   http://192.168.x.x:8000
   ```

### Different Network (Advanced)

Requires:
- Port forwarding on router
- Dynamic DNS or static IP
- HTTPS and authentication (security!)

See `WEB_UI_GUIDE.md` for production setup.

---

## 🛑 Stop System

In the bot terminal:

```
Press Ctrl+C
```

This will:
1. Stop the trading bot
2. Stop the UI server (if started together)
3. Clean up processes

---

## 📖 More Information

- **Complete Guide:** `WEB_UI_GUIDE.md`
- **Technical Details:** `WEB_UI_IMPLEMENTATION_SUMMARY.md`
- **UI README:** `trading_system/ui/README.md`

---

## 🆘 Help!

### Dashboard Not Loading

```bash
# Check if server is running
curl http://localhost:8000/health

# Should return: {"status": "healthy"}
```

If not running:
```bash
./start_web_ui.sh
```

### No Data Showing

1. Ensure bot is running
2. Look for "✅ Web UI integration enabled" in bot console
3. Refresh browser (Ctrl+R)

### Chart Not Appearing

1. Click on a symbol in the list
2. Wait a few seconds for data to load
3. Check browser console (F12) for errors

---

## 🎉 You're Ready!

Your trading system now has a professional web interface!

**Start trading:** `./start_bot_with_ui.sh`  
**Access dashboard:** http://localhost:8000  
**Monitor in real-time:** ✨

---

**Questions? Check the full guide: `WEB_UI_GUIDE.md`**

