# PnL Tracking Guide - Realized & Unrealized

## 💰 **How PnL Tracking Works**

The live monitor now tracks **both realized and unrealized PnL**!

---

## 📊 **PnL Types**

### **1. Realized PnL**
- PnL from **closed** trades
- Actual profit/loss locked in
- Example: Bought at ₹100, sold at ₹105 = +₹5 realized

### **2. Unrealized PnL** ← **NEW!**
- PnL from **open** positions
- Paper profit/loss (mark-to-market)
- Changes with current price
- Example: Bought at ₹100, current ₹103 = +₹3 unrealized

### **3. Total PnL**
- **Total = Realized + Unrealized**
- What you see in the table

---

## 🔍 **PnL Display Format**

### **In the Table**

| Symbol | Orders | PnL (₹) | Meaning |
|--------|--------|---------|---------|
| ABC | 2 | **+5.50*** | +₹5.50 unrealized (open position) |
| XYZ | 4 | **+10.20** | +₹10.20 realized (closed trades) |
| DEF | 1 | **-2.30*** | -₹2.30 unrealized (open position) |

### **Legend**
- **No asterisk (*)** = Realized PnL (closed)
- **With asterisk (*)** = Unrealized PnL (open position)

---

## 📈 **Example Trade Flow**

### **Scenario: Trading SENSEX2610185100PE**

```
Refresh 1:
  Signal: BUY at ₹100
  Action: Open LONG position
  Orders: 1
  PnL: ₹0.00* (just entered, no profit yet)
  
Refresh 2:
  Signal: BUY at ₹103 (still holding)
  Action: Hold position
  Orders: 1
  PnL: +₹3.00* (unrealized, position is up)
  
Refresh 3:
  Signal: BUY at ₹98 (still holding)
  Action: Hold position
  Orders: 1
  PnL: -₹2.00* (unrealized, position is down)
  
Refresh 4:
  Signal: SELL at ₹105
  Action: Close LONG, Open SHORT
  Orders: 3 (close long + open short)
  PnL: +₹5.00 (now realized from closed long)
  
Refresh 5:
  Signal: SELL at ₹103 (still short)
  Action: Hold short position
  Orders: 3
  PnL: +₹7.00* (+₹5 realized + ₹2 unrealized from short)
  
Refresh 6:
  Signal: HOLD at ₹104
  Action: Close SHORT position
  Orders: 4 (close short)
  PnL: +₹6.00 (all realized: +₹5 from long, +₹1 from short)
```

---

## 🎯 **Understanding the Numbers**

### **When You See +₹5.00***
- You have an **open position**
- Currently showing **+₹5 paper profit**
- Not locked in yet (can change)
- Will become realized when you close

### **When You See +₹5.00** (no asterisk)
- All positions are **closed**
- **+₹5 actual profit** locked in
- Won't change unless you trade again

---

## 📊 **Position Tracking**

### **Long Position (BUY)**
```
Entry: ₹100
Current: ₹105
Unrealized PnL: +₹5 (105 - 100)
```

### **Short Position (SELL)**
```
Entry: ₹100
Current: ₹95
Unrealized PnL: +₹5 (100 - 95)
```

---

## 💡 **Key Features**

### ✅ **Real-Time Tracking**
- Updates every 5 seconds
- Shows current profit/loss
- Both open and closed positions

### ✅ **Automatic Calculation**
- Tracks entry prices
- Monitors current prices
- Calculates PnL automatically

### ✅ **Signal-Based**
- BUY signal = Long position
- SELL signal = Short position
- HOLD signal = Close position
- Signal change = New trade

### ✅ **Cumulative**
- Adds up all trades
- Tracks per symbol
- Shows totals at bottom

---

## 📋 **Complete Example**

### **Live Monitor Display**

```
╭──────────────────────────────────────────────────────────────────────────────╮
│               Multi-Symbol Trading Monitor - Complete Analysis               │
├────────────────────┬─────────┬────────┬─────────────┬────────┬──────────────┤
│ Symbol             │ LTP (₹) │ Final  │ ... (cols)  │ Orders │ PnL (₹)      │
├────────────────────┼─────────┼────────┼─────────────┼────────┼──────────────┤
│ SENSEX...100PE     │ 330.95  │ BUY    │ ...         │ 1      │ +0.00*       │ <- Just opened
│ SENSEX...100CE     │ 209.05  │ HOLD   │ ...         │ 0      │ 0.00         │ <- No position
│ NIFTY...50PE       │ 69.60   │ BUY    │ ...         │ 3      │ +5.50*       │ <- Open +₹5.50
│ NIFTY...50CE       │ 35.80   │ HOLD   │ ...         │ 4      │ +12.30       │ <- Closed +₹12.30
├────────────────────┼─────────┼────────┼─────────────┼────────┼──────────────┤
│ TOTAL              │         │        │             │ 8      │ +17.80       │ <- Total PnL
╰────────────────────┴─────────┴────────┴─────────────┴────────┴──────────────╯

Legend:
  PnL with * = Unrealized (open position)
  Total Orders: 8  |  Total PnL: ₹+17.80
```

---

## 🔄 **How Orders Are Counted**

### **New Position**
- Signal changes from HOLD/0 to BUY/SELL
- Opens new position
- **+1 order**

### **Close Position**
- Signal changes from BUY/SELL to HOLD
- OR signal reverses (BUY→SELL or SELL→BUY)
- Closes existing position
- **+1 order** for close
- **+1 order** for new position (if not HOLD)

### **Hold Position**
- Signal stays the same
- No new orders
- PnL updates with current price

---

## 🎨 **Color Coding**

### **PnL Colors**
- **Green** = Positive (profit) 💚
- **Red** = Negative (loss) 💔
- **White** = Zero (breakeven) ⚪

### **Signal Colors**
- **Green** = BUY (bullish) 🟢
- **Red** = SELL (bearish) 🔴
- **Yellow** = HOLD (neutral) 🟡

---

## 📊 **Reading the Summary**

### **Bottom of Table**
```
│ TOTAL  │  │  │  │  │ 25 │ +150.50 │
                      ↑        ↑
                   Orders   Total PnL
```

- **25** = Total orders across all symbols
- **+150.50** = Total PnL (realized + unrealized)

### **Legend Section**
```
Total Orders: 25  |  Total PnL: ₹+150.50
```
- Quick summary
- Same info as table
- Easy to spot

---

## 💡 **Pro Tips**

### **1. Watch for Asterisks**
- **With *** = Position is open, PnL can change
- **Without *** = Position closed, PnL locked in

### **2. Monitor Unrealized**
- Unrealized PnL changes every refresh
- Shows if position is profitable
- Helps decide when to close

### **3. Track Total PnL**
- Total at bottom = overall performance
- Green = profitable
- Red = losing

### **4. Order Count**
- High orders = active trading
- Low orders = holding positions
- 0 orders = no trades yet

---

## ⚠️ **Important Notes**

### **1. Entry Price**
- Recorded when position opens
- Used for PnL calculation
- Doesn't change until new position

### **2. Position Types**
- **Long (BUY)**: Profit when price goes UP
- **Short (SELL)**: Profit when price goes DOWN
- **No position (HOLD)**: No PnL

### **3. Signal Changes**
- Only changes trigger orders
- Same signal = hold position
- HOLD closes any open position

### **4. PnL Persistence**
- Tracked across refreshes
- Doesn't reset
- Cumulative since start

---

## 🎯 **Summary**

### **What the PnL Shows**
✅ **Real-time** profit/loss  
✅ **Open positions** (unrealized with *)  
✅ **Closed trades** (realized, no *)  
✅ **Total performance** (sum of all)  

### **How to Use It**
1. Check PnL with * = Open position, watch it
2. Green PnL = Winning trade
3. Red PnL = Losing trade
4. Total at bottom = Overall performance

### **Perfect For**
- Live trading monitoring
- Performance tracking
- Position management
- Quick profit/loss check

---

**Updated**: December 29, 2025  
**Feature**: Realized + Unrealized PnL Tracking  
**Status**: ✅ Working with asterisk indicator!

