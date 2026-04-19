# Combined Multi-Symbol Table with Trading Info

## ✅ **NEW: All Symbols in ONE Table with PnL & Orders!**

Now all symbols are shown in a single comprehensive table with trading information!

---

## 🚀 **Quick Start**

```bash
cd /home/sham/Desktop/MARKOV_MARKET
source .venv/bin/activate
python live/run_multi_symbol_live.py
```

---

## 📊 **What You'll See**

### **Single Table with ALL Symbols**

```
╭──────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│                        Multi-Symbol Trading Monitor - Complete Analysis                                          │
├────────────────────┬─────────┬────────┬────────┬────────┬────────┬────────┬────────┬────────┬────────┬────────┤
│ Symbol             │ LTP (₹) │ Final  │ Raw    │ Daily  │ Daily  │ Intra  │ Intra  │ RL     │ Regime │ Vol    │
│                    │         │ Signal │ Signal │ VOMC   │ Prob   │ VOMC   │ Prob   │ Agent  │ D/I    │ %      │
├────────────────────┼─────────┼────────┼────────┼────────┼────────┼────────┼────────┼────────┼────────┼────────┤
│ SENSEX2610185100PE │ 298.95  │ BUY    │ BUY    │ BUY    │ 47.1%  │ BUY    │ 46.9%  │ HOLD   │ 1/0    │ 1.23%  │
│ SENSEX2610185100CE │ 285.40  │ HOLD   │ BUY    │ BUY    │ 57.1%  │ BUY    │ 47.7%  │ HOLD   │ 0/1    │ 1.47%  │
│ NIFTY26DEC26050CE  │ 142.50  │ SELL   │ SELL   │ SELL   │ 35.2%  │ SELL   │ 38.4%  │ SELL   │ 2/2    │ 2.15%  │
├────────────────────┼─────────┼────────┼────────┼────────┼────────┼────────┼────────┼────────┼────────┼────────┤
│                                                                 Continued...                                     │
├────────────────────┬────────────┬────────┬────────┬──────────┐
│ Filters            │ Conf       │ Orders │ PnL (₹)│ Status   │
│ T/B/M              │ /3         │        │        │          │
├────────────────────┼────────────┼────────┼────────┼──────────┤
│ B/B/N              │ 2          │ 3      │ +4.50  │ ✓        │
│ B/b/b              │ 0          │ 1      │ -1.20  │ ✓        │
│ b/b/b              │ 3          │ 5      │ +12.80 │ ✓        │
├────────────────────┼────────────┼────────┼────────┼──────────┤
│ TOTAL              │            │ 9      │ +16.10 │          │
╰────────────────────┴────────────┴────────┴────────┴──────────╯

Legend:
  Signals: BUY | SELL | HOLD
  Filters (T/B/M): B=Bullish, b=bearish, N=neutral, -=none
  Regime D/I: Daily/Intraday regime (0,1,2)
  Conf: Confirmations out of 3 (Trend, Breakout, Momentum)
  Total Orders: 9  |  Total PnL: ₹+16.10

⏱  Next refresh in: 5s  |  Press Ctrl+C to stop
```

---

## 📋 **Table Columns**

### **Basic Info**
1. **Symbol** - Trading symbol name
2. **LTP (₹)** - Latest Traded Price in Rupees

### **Signals**
3. **Final Signal** - Signal after all filters (YOUR DECISION!)
4. **Raw Signal** - Signal before filters
5. **Daily VOMC** - Daily VOMC model signal
6. **Daily Prob** - Daily VOMC probability
7. **Intra VOMC** - Intraday VOMC signal
8. **Intra Prob** - Intraday VOMC probability
9. **RL Agent** - Reinforcement learning action

### **Analysis**
10. **Regime D/I** - Daily/Intraday regime (0,1,2)
11. **Vol %** - Volatility percentage
12. **Filters T/B/M** - Trend/Breakout/Momentum (B/b/N/-)
13. **Conf /3** - Confirmations out of 3

### **Trading** ← **NEW!**
14. **Orders** - Number of orders placed
15. **PnL (₹)** - Profit & Loss in Rupees
16. **Status** - ✓ Success or ✗ Error

---

## 💰 **Trading Tracking**

### **Automatic Order Tracking**
- Tracks when signal changes from previous value
- Counts buy/sell orders
- Calculates PnL based on entry/exit prices

### **PnL Calculation (Realized + Unrealized)**
- **BUY signal** → Opens long position at current price
- **SELL signal** → Opens short position (or closes long)
- **Signal change** → Closes previous position, calculates realized PnL
- **Open position** → Shows unrealized PnL with asterisk (*)
- **Cumulative** → Adds up all trades (realized + unrealized)

### **Example with Unrealized PnL**
```
Refresh 1: BUY @ ₹100   → Order #1, PnL = ₹0.00*   (just entered)
Refresh 2: BUY @ ₹103   → No order,  PnL = +₹3.00* (unrealized, up)
Refresh 3: BUY @ ₹98    → No order,  PnL = -₹2.00* (unrealized, down)
Refresh 4: SELL @ ₹105  → Order #2, PnL = +₹5.00  (realized, closed)
Refresh 5: SELL @ ₹103  → No order,  PnL = +₹7.00* (+₹5 realized + ₹2 unrealized)
Refresh 6: HOLD @ ₹104  → Order #3, PnL = +₹6.00  (all realized)
```

**Key:**
- **PnL with *** = Unrealized (position still open, can change)
- **PnL without *** = Realized (all positions closed, locked in)

---

## 🎨 **Color Coding**

### **Signals**
- **BUY** = Green (bullish)
- **SELL** = Red (bearish)
- **HOLD** = Yellow (neutral)

### **PnL**
- **Positive** (+₹) = Green
- **Negative** (-₹) = Red
- **Zero** (₹0) = White
- **With asterisk (*)** = Unrealized (open position)
- **No asterisk** = Realized (closed trades)

### **Filters**
- **B** = Bullish (uppercase)
- **b** = bearish (lowercase)
- **N** = Neutral
- **-** = No filter data

---

## 📈 **Summary Row**

At the bottom of the table:

```
TOTAL  |  |  |  |  |  |  |  |  |  |  |  | 25 | +150.50 |
```

Shows:
- **Total Orders** across all symbols
- **Total PnL** (₹) - Combined profit/loss

---

## 🆚 **Before vs After**

### **Before (Separate Tables)**
```
Symbol 1 Table
  - All details for symbol 1

Symbol 2 Table  
  - All details for symbol 2

Symbol 3 Table
  - All details for symbol 3

No trading info
No totals
```

### **After (Combined Table)** ← **NOW!**
```
ONE Table with ALL Symbols
├─ Symbol 1 (row)
├─ Symbol 2 (row)
├─ Symbol 3 (row)
└─ TOTAL (summary row)

✅ All symbols visible at once
✅ Easy comparison
✅ Trading info (Orders, PnL)
✅ Total summary
```

---

## 📊 **Key Features**

### ✅ **All Symbols in One View**
- No scrolling between symbols
- Easy comparison
- See everything at once

### ✅ **Latest Price (LTP)**
- Current price for each symbol
- In Rupees (₹)
- Updates every 5 seconds

### ✅ **Complete Analysis**
- All model signals
- All filter results
- All confirmations
- Final trading decision

### ✅ **Trading Information** ← **NEW!**
- Number of orders per symbol
- PnL per symbol
- Total orders
- Total PnL

### ✅ **Auto-Refresh**
- Updates every 5 seconds
- Live tracking
- Persistent data across refreshes

---

## 💡 **Benefits**

### **1. Quick Overview**
See all symbols at a glance:
- Which are BUY signals?
- Which have positive PnL?
- Which have most orders?

### **2. Easy Comparison**
Compare symbols side-by-side:
- Best probability?
- Highest volatility?
- Most confirmations?

### **3. Trading Performance**
Track your trading:
- Total orders placed
- Cumulative PnL
- Best/worst performers

### **4. Space Efficient**
- One screen
- All information
- No scrolling needed

---

## 🔍 **Filter Legend**

### **T/B/M Column (Trend/Breakout/Momentum)**

| Code | Meaning |
|------|---------|
| **B** | Bullish (strong positive) |
| **b** | bearish (weak negative) |
| **N** | Neutral (no direction) |
| **-** | No data |

### **Examples**
- `B/B/B` = All filters bullish (strong buy)
- `b/b/b` = All filters bearish (strong sell)
- `B/N/-` = Mixed signals
- `N/N/N` = All neutral (hold)

---

## 📝 **Usage Examples**

### **Day Trading**
```
Monitor multiple symbols
Quick signal changes
Track order counts
Watch PnL accumulate
```

### **Portfolio Monitoring**
```
See all positions
Compare performance
Identify best/worst
Make informed decisions
```

### **Signal Scanning**
```
Scan for BUY signals
Check probabilities
Verify confirmations
Execute on best ones
```

---

## ⚙️ **Configuration**

### **Change Symbols**
Edit `configs/symbols_config.yaml`:
```yaml
symbols:
  - "BSE:SENSEX2610185100PE"
  - "BSE:SENSEX2610185100CE"
  - "NSE:NIFTY26DEC26050CE"
  # Add more...
```

### **Change Refresh Rate**
Edit `live/run_multi_symbol_live.py`:
```python
REFRESH_INTERVAL = 5  # seconds
```

---

## 🎯 **Summary**

**What You Get:**
- ✅ All symbols in ONE table
- ✅ Latest price (LTP) for each
- ✅ Complete analysis (signals, filters, confirmations)
- ✅ Trading info (orders, PnL)
- ✅ Total summary row
- ✅ Auto-refresh every 5 seconds
- ✅ Color-coded for easy reading

**Perfect For:**
- Multi-symbol monitoring
- Quick signal scanning
- Trading performance tracking
- Real-time analysis

---

**Updated**: December 29, 2025  
**Format**: Combined table with all symbols  
**Features**: Orders & PnL tracking  
**Status**: ✅ Production ready!

