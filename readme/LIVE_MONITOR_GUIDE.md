# Live Multi-Symbol Monitor - Quick Guide

## 🎨 Color-Coded Live Display

A simplified, color-coded version that updates every 5 seconds with clean, readable output!

---

## 🚀 Quick Start

```bash
cd /home/sham/Desktop/MARKOV_MARKET
source .venv/bin/activate
python live/run_multi_symbol_live.py
```

Or using uv:
```bash
cd /home/sham/Desktop/MARKOV_MARKET
uv run live/run_multi_symbol_live.py
```

---

## 📊 What You'll See

### Clean, Color-Coded Display

```
================================================================================
  LIVE MULTI-SYMBOL TRADING MONITOR  
  Updated: 2025-12-29 10:30:15  
================================================================================

┌──────────────────────────────────────────────────────────────────────────────┐
│ Symbol                    │ Signal       │ Raw        │ Daily      │ Intra      │
├──────────────────────────────────────────────────────────────────────────────┤
│ SENSEX2610185100PE        │ 🟢 BUY       │ 🟢 BUY     │ 47.1%      │ 46.9%      │
│ SENSEX2610185100CE        │ ⚪ HOLD      │ 🟢 BUY     │ 57.1%      │ 47.7%      │
└──────────────────────────────────────────────────────────────────────────────┘

▶ SENSEX2610185100PE
  Final: 🟢 BUY  Raw: 🟢 BUY  Regime: 1  Vol: 1.23%  Conf: 2/3

▶ SENSEX2610185100CE
  Final: ⚪ HOLD  Raw: 🟢 BUY  Regime: 0  Vol: 1.47%  Conf: 2/3

Legend:
  🟢 BUY = Buy Signal    🔴 SELL = Sell Signal    ⚪ HOLD = Hold/Neutral
  Daily/Intra = Probability percentages (higher = stronger signal)
  Regime = Market regime (0,1,2)  |  Vol = Volatility  |  Conf = Confirmations

Analysis: 2 successful, 0 failed  |  Time: 2.8s

────────────────────────────────────────────────────────────────────────────────
⏱  Refreshing every 5 seconds... Press Ctrl+C to stop
────────────────────────────────────────────────────────────────────────────────
```

---

## 🎨 Color Coding

### Signal Colors
- **🟢 GREEN** = BUY signal (bullish)
- **🔴 RED** = SELL signal (bearish)
- **⚪ YELLOW** = HOLD signal (neutral)

### Probability Colors
- **GREEN** = High probability (bullish)
- **RED** = Low probability (bearish)
- **CYAN** = Informational data

---

## ⚙️ Features

### ✅ Auto-Refresh
- Updates every **5 seconds** automatically
- No need to restart
- Live market monitoring

### ✅ Clean Display
- Simplified table format
- Color-coded signals
- Easy to read at a glance

### ✅ Key Information
- **Final Signal**: After all filters applied
- **Raw Signal**: Before filters
- **Daily Prob**: Daily model confidence
- **Intra Prob**: Intraday model confidence
- **Regime**: Market regime (0, 1, or 2)
- **Volatility**: Current volatility %
- **Confirmations**: Filter confirmations (out of 3)

### ✅ Auto-Save
- Results saved to CSV after each refresh
- Location: `results/multi_symbol_intraday_results.csv`

---

## 🛑 How to Stop

Press **`Ctrl+C`** to stop the monitor gracefully.

```
Monitor stopped by user.
Results saved to: results/multi_symbol_intraday_results.csv
```

---

## ⚙️ Configuration

### Change Symbols
Edit `configs/symbols_config.yaml`:
```yaml
symbols:
  - "BSE:SENSEX2610185100PE"
  - "BSE:SENSEX2610185100CE"
  - "BSE:YOUR_SYMBOL_HERE"  # Add more
```

### Change Refresh Interval
Edit `live/run_multi_symbol_live.py`:
```python
REFRESH_INTERVAL = 5  # Change to your desired seconds
```

Or change it on the fly:
```python
REFRESH_INTERVAL = 10  # 10 seconds
REFRESH_INTERVAL = 30  # 30 seconds
REFRESH_INTERVAL = 60  # 1 minute
```

### Change Performance Settings
Edit `configs/symbols_config.yaml`:
```yaml
performance:
  params_config: "configs/params_fast.yaml"  # Fast mode
  max_intraday_rows: 1000  # Data limit
```

---

## 📈 Understanding the Output

### Final Signal
The signal **after all filters** are applied:
- 🟢 **BUY**: Strong buy signal, all filters passed
- 🔴 **SELL**: Strong sell signal, all filters passed
- ⚪ **HOLD**: Neutral or filters didn't confirm

### Raw Signal
The signal **before filters** (from model fusion):
- Shows what the models are saying
- May differ from final signal if filters block it

### Probabilities
- **Daily Prob**: Daily VOMC model confidence (0-100%)
- **Intra Prob**: Intraday VOMC model confidence (0-100%)
- Higher = Stronger signal

### Regime
Market regime detected by HMM:
- **0**: Low volatility / stable
- **1**: Normal / trending
- **2**: High volatility / crash

### Confirmations
Number of filter confirmations (out of 3):
- **3/3**: All filters confirm (strongest)
- **2/3**: Two filters confirm (moderate)
- **1/3**: One filter confirms (weak)
- **0/3**: No filters confirm (ignore)

---

## 🔧 Troubleshooting

### Monitor Not Starting
**Check Python environment**:
```bash
source .venv/bin/activate
```

### Colors Not Showing
**Install colorama**:
```bash
pip install colorama
```

### Too Slow
**Reduce symbols** or **increase max_intraday_rows limit**:
```yaml
# configs/symbols_config.yaml
performance:
  max_intraday_rows: 500  # Lower = faster
```

### Too Fast (Missing Updates)
**Increase refresh interval**:
```python
# live/run_multi_symbol_live.py
REFRESH_INTERVAL = 10  # seconds
```

---

## 📊 Comparison: One-Time vs Live

### One-Time Analysis
```bash
python live/run_multi_symbol_intraday.py
```
- Runs once and exits
- Shows detailed tables
- Good for analysis

### Live Monitor
```bash
python live/run_multi_symbol_live.py
```
- Runs continuously (every 5s)
- Color-coded display
- Good for live trading

---

## 💡 Pro Tips

### 1. Split Screen
Run monitor in split terminal:
```bash
# Terminal 1: Monitor
python live/run_multi_symbol_live.py

# Terminal 2: Your trading commands
python live/your_trading_script.py
```

### 2. Background Logging
Results are auto-saved to CSV:
```bash
# View results while monitor runs
tail -f results/multi_symbol_intraday_results.csv
```

### 3. Quick Check
For quick status without running monitor:
```bash
python live/run_multi_symbol_intraday.py | tail -50
```

---

## 📝 Example Use Cases

### Day Trading
```bash
# Set to 5-second updates
REFRESH_INTERVAL = 5
python live/run_multi_symbol_live.py
```

### Swing Trading
```bash
# Set to 1-minute updates
REFRESH_INTERVAL = 60
python live/run_multi_symbol_live.py
```

### Portfolio Monitoring
```bash
# Add all your positions to symbols_config.yaml
# Run monitor in background terminal
python live/run_multi_symbol_live.py
```

---

## 🎯 Quick Commands

### Start Monitor
```bash
python live/run_multi_symbol_live.py
```

### Stop Monitor
Press `Ctrl+C`

### Change Symbols
```bash
nano configs/symbols_config.yaml
```

### Change Speed
```bash
nano live/run_multi_symbol_live.py
# Edit: REFRESH_INTERVAL = 5
```

### View Saved Results
```bash
cat results/multi_symbol_intraday_results.csv
```

---

## ✅ Summary

**Live Monitor Features**:
- ✅ Auto-refresh every 5 seconds
- ✅ Color-coded signals (🟢🔴⚪)
- ✅ Simplified, clean display
- ✅ Key metrics at a glance
- ✅ Auto-save to CSV
- ✅ Press Ctrl+C to stop

**Perfect for**:
- Live trading monitoring
- Multi-symbol tracking
- Quick signal checks
- Real-time market analysis

---

**Created**: December 29, 2025  
**Purpose**: Live color-coded multi-symbol monitoring  
**Refresh**: Every 5 seconds  
**Status**: ✅ Ready to use!

