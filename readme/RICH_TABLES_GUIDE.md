# Rich Tables Live Monitor - Beautiful UI

## 🎨 **Updated with Beautiful Rich Tables!**

The live monitor now uses the same beautiful table format as your real-time trading script!

---

## 🚀 **Quick Start**

```bash
cd /home/sham/Desktop/MARKOV_MARKET
./start_live_monitor.sh
```

Or:

```bash
source .venv/bin/activate
python live/run_multi_symbol_live.py
```

---

## 📊 **What You'll See**

### **Beautiful Formatted Tables (Like Your Trading Script!)**

```
╭──────────────────────────╮
│ Real-time Multi-Symbol   │
│ Monitor                  │
│ 2025-12-29 10:35:09      │
╰──────────────────────────╯

                              Market Data                               
╭───────────────────────────┬──────────────────────────────────────────╮
│ Metric                    │ Value                                    │
├───────────────────────────┼──────────────────────────────────────────┤
│ Symbol                    │ SENSEX2610185100PE                       │
│ Volatility                │ 1.23%                                    │
│ Regime                    │ Regime 1                                 │
╰───────────────────────────┴──────────────────────────────────────────╯

                                  Daily Models                                  
╭───────────────────────────┬──────────────────────┬───────────────────────────╮
│ Model                     │ Signal/Value         │ Details                   │
├───────────────────────────┼──────────────────────┼───────────────────────────┤
│ VOMC Daily                │ BUY                  │ Prob: 47.06%              │
│ HMM Regime                │ Regime 1             │                           │
╰───────────────────────────┴──────────────────────┴───────────────────────────╯

                                Intraday Models                                 
╭───────────────────────────┬──────────────────────┬───────────────────────────╮
│ Model                     │ Signal/Value         │ Details                   │
├───────────────────────────┼──────────────────────┼───────────────────────────┤
│ VOMC Intraday             │ BUY                  │ Prob: 46.88%              │
│ RL Agent                  │ HOLD                 │ Action: 2                 │
╰───────────────────────────┴──────────────────────┴───────────────────────────╯

                               Precision Filters                                
╭───────────────────────────┬──────────────────────┬───────────────────────────╮
│ Filter                    │ Status               │ Confirmation              │
├───────────────────────────┼──────────────────────┼───────────────────────────┤
│ Volatility                │ ✓ PASS               │ Vol: 1.23%                │
│ Confirmations             │ 2/3                  │ Trend, Breakout, Momentum │
╰───────────────────────────┴──────────────────────┴───────────────────────────╯

                                 Signal Summary                                 
╭───────────────────────────┬──────────────────────┬───────────────────────────╮
│ Signal Type               │ Value                │ Status                    │
├───────────────────────────┼──────────────────────┼───────────────────────────┤
│ Raw Signal                │ BUY                  │ Before Filters            │
│ Final Signal              │ BUY                  │ After Filters             │
╰───────────────────────────┴──────────────────────┴───────────────────────────╯

                              Analysis Summary                              
╭───────────────────────────┬──────────────────────────────────────────╮
│ Metric                    │ Value                                    │
├───────────────────────────┼──────────────────────────────────────────┤
│ ✓ Successful              │ 2                                        │
│ ✗ Failed                  │ 0                                        │
│ ⏱  Time                   │ 2.8s                                     │
│ 📊 Total Symbols          │ 2                                        │
╰───────────────────────────┴──────────────────────────────────────────╯

⠙ Next refresh in...  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3s  Press Ctrl+C to stop
```

---

## ✨ **Features**

### ✅ **Beautiful Rich Tables**
- Rounded borders (`╭─╮` style)
- Clean, professional look
- Same format as your trading script
- Color-coded signals (GREEN/RED/YELLOW)

### ✅ **Organized Layout**
- **Market Data**: Symbol, volatility, regime
- **Daily Models**: VOMC signals, HMM, regime
- **Intraday Models**: VOMC signals, RL agent
- **Precision Filters**: All filter status
- **Signal Summary**: Raw vs Final signal
- **Analysis Summary**: Stats and timing

### ✅ **Progress Bar**
- Visual countdown between refreshes
- Shows remaining time
- Smooth animation
- Clear "Press Ctrl+C" reminder

### ✅ **Multi-Symbol**
- Shows each symbol separately
- Clear separation between symbols
- All details for each symbol
- Summary at the end

---

## 🎨 **Color Coding**

### **Signals**
- **BUY** = Green (bullish)
- **SELL** = Red (bearish)
- **HOLD** = Yellow (neutral)

### **Status**
- **✓ PASS** = Green (filter passed)
- **✗ FAIL** = Red (filter failed)
- **Metrics** = Cyan (informational)

---

## 🔄 **Auto-Refresh**

### **Countdown Progress Bar**
```
⠙ Next refresh in...  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 5s  Press Ctrl+C to stop
⠹ Next refresh in...  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4s  Press Ctrl+C to stop
⠸ Next refresh in...  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3s  Press Ctrl+C to stop
```

- Animated spinner
- Progress bar visualization
- Clear countdown
- Press Ctrl+C to stop

---

## 📋 **Per-Symbol Display**

For each symbol, you get:

1. **Market Data Table**
   - Symbol name
   - Current volatility
   - Market regime

2. **Daily Models Table**
   - VOMC signal + probability
   - HMM regime

3. **Intraday Models Table**
   - VOMC signal + probability
   - RL agent action

4. **Precision Filters Table**
   - Filter pass/fail status
   - Confirmation count

5. **Signal Summary Table**
   - Raw signal (before filters)
   - Final signal (after filters)

---

## 🛑 **How to Stop**

Press **`Ctrl+C`**:

```
🛑 Monitor stopped by user.
💾 Results saved to: results/multi_symbol_intraday_results.csv
```

---

## ⚙️ **Configuration**

### Change Refresh Interval
Edit `live/run_multi_symbol_live.py`:
```python
REFRESH_INTERVAL = 5   # seconds
```

### Add Symbols
Edit `configs/symbols_config.yaml`:
```yaml
symbols:
  - "BSE:SENSEX2610185100PE"
  - "BSE:SENSEX2610185100CE"
  - "YOUR:SYMBOL_HERE"
```

---

## 🆚 **Comparison**

| Feature | Old (Colorama) | New (Rich) |
|---------|----------------|------------|
| **Tables** | Simple text boxes | Beautiful rounded boxes |
| **Layout** | Basic columns | Professional multi-tables |
| **Progress** | Text countdown | Animated progress bar |
| **Colors** | Basic | Rich styling |
| **Readability** | Good | Excellent ✅ |
| **Professional** | Basic | Production-ready ✅ |

---

## 💡 **Tips**

### 1. Full Screen
Run in full-screen terminal for best experience

### 2. Font
Use a monospace font for perfect alignment

### 3. Colors
Ensure your terminal supports colors (most do)

### 4. Screen Size
Tables auto-fit, but larger screen = better view

---

## 🎯 **Summary**

**Now using Rich library for:**
- ✅ Beautiful rounded table borders
- ✅ Professional color-coding
- ✅ Animated progress bars
- ✅ Clean organized layout
- ✅ Same style as trading script
- ✅ Production-ready UI

**Just run:**
```bash
./start_live_monitor.sh
```

**And enjoy beautiful live monitoring!** 🎨

---

**Updated**: December 29, 2025  
**UI Library**: Rich (Python)  
**Style**: Professional rounded tables  
**Status**: ✅ Production ready!

