# Detailed Order Tracking Guide

## 🎯 **Complete Order History with Entry/Exit Details**

The live monitor now shows **detailed order tracking** with separate tables for open and closed positions!

---

## 🚀 **Quick Start**

```bash
cd /home/sham/Desktop/MARKOV_MARKET
source .venv/bin/activate
python live/run_multi_symbol_live.py
```

---

## 📊 **What You'll See**

### **Three Tables Display**

```
╭─────────────────────────────────────────────────────────────────────────────╮
│               Multi-Symbol Trading Monitor - Complete Analysis              │
│ (Main summary table with all symbols...)                                    │
╰─────────────────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────────────────╮
│                   📊 Open Positions (Unrealized PnL)                        │
├────┬───────────────────┬────────┬─────────────┬─────────────┬──────────────┤
│ ID │ Symbol            │ Type   │ Entry Price │ Current     │ Entry Time   │
│    │                   │        │             │ Price       │              │
├────┼───────────────────┼────────┼─────────────┼─────────────┼──────────────┤
│ 1  │ SENSEX...100PE    │ LONG   │ ₹330.95     │ ₹335.50     │ 2025-12-29   │
│    │                   │        │             │             │ 10:15:30     │
│ 3  │ NIFTY...50PE      │ LONG   │ ₹69.60      │ ₹71.20      │ 2025-12-29   │
│    │                   │        │             │             │ 10:15:45     │
├────┴───────────────────┴────────┴─────────────┴─────────────┴──────────────┤
│                                                   (More columns...)         │
├────┬─────┬────────────────┤
│ Qty│ Unrealized PnL     │
├────┼────────────────────┤
│ 1  │ ₹+4.55             │
│    │                    │
│ 1  │ ₹+1.60             │
│    │                    │
├────┼────────────────────┤
│    │ ₹+6.15             │ <- Total Unrealized
╰────┴────────────────────╯

╭─────────────────────────────────────────────────────────────────────────────╮
│                   ✅ Completed Orders (Realized PnL)                        │
├────┬───────────────────┬────────┬─────────────┬─────────────┬──────────────┤
│ ID │ Symbol            │ Type   │ Entry Price │ Exit Price  │ Entry Time   │
├────┼───────────────────┼────────┼─────────────┼─────────────┼──────────────┤
│ 2  │ SENSEX...100CE    │ LONG   │ ₹209.05     │ ₹215.30     │ 2025-12-29   │
│    │                   │        │             │             │ 10:10:20     │
│ 4  │ NIFTY...50CE      │ SHORT  │ ₹35.80      │ ₹33.20      │ 2025-12-29   │
│    │                   │        │             │             │ 10:12:15     │
├────┴───────────────────┴────────┴─────────────┴─────────────┴──────────────┤
│                                                   (More columns...)         │
├──────────────┬─────┬────────────────┤
│ Exit Time    │ Qty │ Realized PnL   │
├──────────────┼─────┼────────────────┤
│ 2025-12-29   │ 1   │ ₹+6.25         │
│ 10:20:35     │     │                │
│ 2025-12-29   │ 1   │ ₹+2.60         │
│ 10:18:50     │     │                │
├──────────────┼─────┼────────────────┤
│              │     │ ₹+8.85         │ <- Total Realized
╰──────────────┴─────┴────────────────╯

Legend:
  Total Orders: 4  |  Total PnL: ₹+15.00 (₹6.15 unrealized + ₹8.85 realized)
  
⏱  Next refresh in: 5s  |  Press Ctrl+C to stop
```

---

## 📋 **Table 1: Main Summary**

### **Quick Overview**
- All symbols in one row
- Latest price, signals, filters
- Total orders and PnL per symbol

### **Columns**
- Symbol, LTP, Final Signal, Raw Signal
- Daily/Intraday VOMC, Probabilities
- RL Agent, Regimes, Volatility
- Filters, Confirmations
- **Orders** (total count)
- **PnL** (total, with * for unrealized)

---

## 📊 **Table 2: Open Positions (Unrealized)**

### **Shows Current Active Trades**

| Column | Description |
|--------|-------------|
| **ID** | Unique order ID |
| **Symbol** | Trading symbol |
| **Type** | LONG (buy) or SHORT (sell) |
| **Entry Price** | Price when position opened |
| **Current Price** | Latest price |
| **Entry Time** | When position was opened |
| **Qty** | Quantity (default: 1) |
| **Unrealized PnL** | Current profit/loss (not locked in) |

### **Features**
- ✅ Real-time PnL updates
- ✅ Shows time in position
- ✅ Color-coded: Green (profit), Red (loss)
- ✅ Total unrealized PnL at bottom

---

## ✅ **Table 3: Completed Orders (Realized)**

### **Shows Closed Trade History**

| Column | Description |
|--------|-------------|
| **ID** | Unique order ID |
| **Symbol** | Trading symbol |
| **Type** | LONG or SHORT |
| **Entry Price** | Entry price |
| **Exit Price** | Exit price |
| **Entry Time** | When opened |
| **Exit Time** | When closed |
| **Qty** | Quantity traded |
| **Realized PnL** | Locked-in profit/loss |

### **Features**
- ✅ Complete trade history
- ✅ Shows trade duration
- ✅ Final PnL for each trade
- ✅ Total realized PnL at bottom

---

## 💰 **Understanding PnL**

### **Unrealized PnL (Open Positions)**
- Position is still **OPEN**
- PnL changes with price
- Not locked in yet
- **Can go up or down**

### **Realized PnL (Completed Orders)**
- Position is **CLOSED**
- PnL is **final**
- Locked in
- **Won't change**

### **Example**

```
Order #1: Buy @ ₹100
Current: ₹105
Unrealized PnL: +₹5 (can change)

Order #2: Buy @ ₹200, Sell @ ₹210
Realized PnL: +₹10 (locked in)

Total PnL: +₹15 (₹5 unrealized + ₹10 realized)
```

---

## 🔍 **Order Lifecycle**

### **1. Position Opens**
```
Signal: BUY at ₹330.95
Creates Order #1:
  - ID: 1
  - Symbol: SENSEX2610185100PE
  - Type: LONG
  - Entry Price: ₹330.95
  - Entry Time: 2025-12-29 10:15:30
  - Status: OPEN
  - Unrealized PnL: ₹0.00

Shows in "Open Positions" table
```

### **2. Price Moves (Position Held)**
```
Price: ₹335.50
Updates Order #1:
  - Current Price: ₹335.50
  - Unrealized PnL: +₹4.55

Still in "Open Positions" table
PnL updates every 5 seconds
```

### **3. Position Closes**
```
Signal: SELL at ₹340.00
Closes Order #1:
  - Exit Price: ₹340.00
  - Exit Time: 2025-12-29 10:25:15
  - Realized PnL: +₹9.05
  - Status: CLOSED

Moves to "Completed Orders" table
PnL is now final
```

---

## 📊 **Order ID System**

### **Sequential IDs**
- Order #1, #2, #3, etc.
- Never repeats
- Easy to track
- Unique per order

### **Tracking Orders**
- Open position has current ID
- Can reference specific orders
- History persists across refreshes
- No order lost

---

## 🎨 **Color Coding**

### **Order Types**
- **LONG** = Green (buy position)
- **SHORT** = Red (sell position)

### **PnL Colors**
- **Green** = Profit (positive)
- **Red** = Loss (negative)
- **White** = Breakeven (zero)

### **Table Titles**
- **Yellow** = Open Positions (watch these!)
- **Green** = Completed Orders (history)

---

## ⏰ **Time Tracking**

### **Format**
```
2025-12-29 10:15:30
YYYY-MM-DD HH:MM:SS
```

### **What It Shows**
- Exact entry time
- Exact exit time (for closed)
- Trade duration
- Intraday timing

### **Use Cases**
- Verify execution time
- Analyze hold duration
- Compare entry/exit timing
- Track intraday patterns

---

## 📈 **Example Scenarios**

### **Scenario 1: Multiple Open Positions**

```
Open Positions:
  #1: SENSEX...PE  LONG  ₹330 → ₹335  +₹5.00
  #3: SENSEX...CE  LONG  ₹209 → ₹211  +₹2.00
  #5: NIFTY...PE   LONG  ₹69  → ₹71   +₹2.00
  TOTAL: +₹9.00 (unrealized)

Completed Orders:
  (empty)
```

### **Scenario 2: Mixed Positions**

```
Open Positions:
  #4: NIFTY...CE   LONG  ₹35 → ₹36   +₹1.00
  TOTAL: +₹1.00 (unrealized)

Completed Orders:
  #1: SENSEX...PE  LONG  ₹330→₹340  +₹10.00
  #2: SENSEX...CE  LONG  ₹209→₹215  +₹6.00
  #3: NIFTY...PE   SHORT ₹70→₹68    +₹2.00
  TOTAL: +₹18.00 (realized)

Grand Total PnL: +₹19.00
```

### **Scenario 3: All Closed**

```
Open Positions:
  (no open positions)

Completed Orders:
  #1: SENSEX...PE  LONG  ₹330→₹340  +₹10.00
  #2: SENSEX...CE  LONG  ₹209→₹205  -₹4.00
  #3: NIFTY...PE   LONG  ₹69→₹75    +₹6.00
  #4: NIFTY...CE   SHORT ₹36→₹35    +₹1.00
  TOTAL: +₹13.00 (all realized)
```

---

## 💡 **Pro Tips**

### **1. Monitor Open Positions**
- Check unrealized PnL frequently
- Green = winning trade, hold or close
- Red = losing trade, consider stop-loss

### **2. Review Completed Orders**
- Analyze win/loss ratio
- Check average hold time
- Identify best performers

### **3. Track Total PnL**
- Main table shows combined total
- Open table shows unrealized
- Closed table shows realized
- All three should match

### **4. Use Order IDs**
- Track specific trades
- Reference in analysis
- Cross-check with broker

---

## 🔄 **Auto-Refresh**

### **Updates Every 5 Seconds**
- Open positions PnL updates
- New orders added automatically
- Closed orders moved to history
- Real-time monitoring

### **Persistent Data**
- Order history never resets
- IDs keep incrementing
- All trades tracked
- Until script stops

---

## 📊 **Summary Statistics**

### **In Main Table**
```
Total Orders: 8  |  Total PnL: ₹+25.50
```

### **In Open Positions**
```
TOTAL: ₹+5.50 (unrealized)
```

### **In Completed Orders**
```
TOTAL: ₹+20.00 (realized)
```

### **Verification**
```
Total PnL = Unrealized + Realized
₹+25.50 = ₹+5.50 + ₹+20.00 ✓
```

---

## ⚙️ **Customization**

### **Change Quantity**
Edit the quantity in `update_trading_tracker`:
```python
'quantity': 1,  # Change to desired lot size
```

### **Change Refresh Rate**
Edit `REFRESH_INTERVAL`:
```python
REFRESH_INTERVAL = 5  # seconds
```

---

## 🎯 **What You Asked For**

✅ **Unrealized profit separately**
- Open Positions table with live unrealized PnL

✅ **Relevant orders with entry/exit time**
- Complete timestamps for all orders

✅ **Quantity**
- Qty column in both tables

✅ **PnL for each order**
- Individual PnL per order

✅ **All completed orders separately**
- Dedicated Completed Orders table

---

## 🌟 **Key Benefits**

### **1. Complete Transparency**
- See every order
- Track every rupee
- No hidden information

### **2. Real-Time Updates**
- Live unrealized PnL
- Instant order tracking
- Auto-refresh

### **3. Historical Record**
- All completed trades
- Entry/exit details
- Performance analysis

### **4. Easy Analysis**
- Separate open vs closed
- Clear PnL breakdown
- Color-coded results

---

## 📱 **Screen Layout**

```
┌─────────────────────────────────────────┐
│  Main Summary Table                     │
│  (All symbols overview)                 │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│  📊 Open Positions                      │
│  (Unrealized PnL - Watch these!)       │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│  ✅ Completed Orders                    │
│  (Realized PnL - History)              │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│  Legend & Stats                         │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│  ⏱  Next refresh in: 5s                │
└─────────────────────────────────────────┘
```

---

## 🎉 **Summary**

**You now have:**
- ✅ Main summary table (all symbols)
- ✅ Open positions table (unrealized PnL)
- ✅ Completed orders table (realized PnL)
- ✅ Entry/exit times for all orders
- ✅ Quantity tracking
- ✅ Individual order PnL
- ✅ Total PnL breakdown
- ✅ Auto-refresh every 5 seconds

**Perfect for:**
- Active day trading
- Position monitoring
- Performance tracking
- Trade analysis
- Real-time decisions

---

**Updated**: December 29, 2025  
**Feature**: Complete order tracking with detailed history  
**Status**: ✅ Fully implemented!

