# Trading Entry & Exit Conditions

## 🎯 **Complete Entry and Exit Logic**

This document explains **exactly when** positions are opened and closed in your trading system.

---

## 📊 **Signal Generation Pipeline**

### **Stage 1: Generate Individual Model Signals**

#### **1. Daily VOMC Signal**
- **BUY (1)** if probability ≥ 0.5
- **SELL (-1)** if probability < 0.5
- Analyzes daily price patterns

#### **2. Intraday VOMC Signal**
- **BUY (1)** if probability ≥ 0.5
- **SELL (0)** if probability < 0.5
- Analyzes intraday price patterns

#### **3. RL Agent Action**
- **0** = BUY (mapped to 1)
- **1** = SELL (mapped to -1)
- **2** = HOLD (mapped to 0)
- Uses reinforcement learning model

---

### **Stage 2: Fuse Signals (Majority Voting)**

Combines all 3 signals using majority voting:

```python
votes = [daily_signal, intraday_signal, rl_mapped]
vote_sum = sum(votes)

if vote_sum >= 2:    # At least 2 models say BUY
    raw_signal = 1   # BUY
elif vote_sum <= -2: # At least 2 models say SELL
    raw_signal = -1  # SELL
else:
    raw_signal = 0   # HOLD
```

**Examples:**
- Daily=1, Intraday=1, RL=0 → vote_sum=2 → **BUY**
- Daily=-1, Intraday=-1, RL=1 → vote_sum=-1 → **HOLD**
- Daily=1, Intraday=1, RL=1 → vote_sum=3 → **BUY**
- Daily=-1, Intraday=-1, RL=-1 → vote_sum=-3 → **SELL**

---

### **Stage 3: Apply Precision Filters**

The raw signal must pass through precision filters to become the final signal.

---

## 🚪 **ENTRY CONDITIONS**

### **BUY Entry (LONG Position)**

To enter a **LONG** position, **ALL** of the following must be TRUE:

#### **1. Raw Signal = BUY (1)**
- At least 2 out of 3 models vote BUY

#### **2. Volatility Filter ✓**
- `volatility > 0.01` (1%)
- Ensures there's enough price movement to trade

#### **3. Confidence Filter ✓**
- `max(daily_prob, intraday_prob) ≥ 0.6` (60%)
- Models must be confident in their prediction

#### **4. Trend Filter = BULLISH (1)**
- `SMA50 > SMA200` (50-day MA above 200-day MA)
- Confirms uptrend

#### **5. Breakout Filter = BULLISH (1)**
- Higher Highs (HH) or Higher Lows (HL) detected
- Price is breaking out upward

#### **6. Momentum Filter = BUY (1)**
- `RSI > 55`
- Buying momentum present

**Summary:** For BUY, **ALL 6 conditions** must pass!

```
✅ Raw Signal = BUY (1)
✅ Volatility > 1%
✅ Confidence ≥ 60%
✅ Trend = Bullish (SMA50 > SMA200)
✅ Breakout = Bullish (HH/HL)
✅ Momentum = Buy (RSI > 55)
━━━━━━━━━━━━━━━━━━━━━
→ FINAL SIGNAL = BUY (1)
→ Open LONG position
```

---

### **SELL Entry (SHORT Position)**

To enter a **SHORT** position, these must be TRUE:

#### **1. Raw Signal = SELL (-1)**
- At least 2 out of 3 models vote SELL

#### **2. Volatility Filter ✓**
- `volatility > 0.01` (1%)

#### **3. Confidence Filter ✓**
- `max(daily_prob, intraday_prob) ≥ 0.6` (60%)

#### **4. At Least 1 Bearish Confirmation:**
- **Trend Filter = BEARISH (-1)**: `SMA50 < SMA200`
- **OR Breakout Filter = BEARISH (-1)**: Lower Lows (LL) or Lower Highs (LH)
- **OR Momentum Filter = SELL (-1)**: `RSI < 45`

**Summary:** For SELL, need volatility + confidence + **at least 1** bearish confirmation.

```
✅ Raw Signal = SELL (-1)
✅ Volatility > 1%
✅ Confidence ≥ 60%
✅ At least 1 of:
   - Trend = Bearish (SMA50 < SMA200)
   - Breakout = Bearish (LL/LH)
   - Momentum = Sell (RSI < 45)
━━━━━━━━━━━━━━━━━━━━━
→ FINAL SIGNAL = SELL (-1)
→ Open SHORT position
```

---

## 🚪 **EXIT CONDITIONS**

### **Exit LONG Position**

A LONG position is closed when:

#### **1. Signal Changes from BUY to anything else**
- New signal = **SELL (-1)** → Close LONG, Open SHORT
- New signal = **HOLD (0)** → Close LONG, No new position

**Example:**
```
Refresh 1: Final Signal = BUY (1)
  → Opens LONG @ ₹100

Refresh 2: Final Signal = BUY (1)
  → Hold LONG (no change)

Refresh 3: Final Signal = HOLD (0)
  → Close LONG @ ₹105
  → Realized PnL = +₹5
```

---

### **Exit SHORT Position**

A SHORT position is closed when:

#### **1. Signal Changes from SELL to anything else**
- New signal = **BUY (1)** → Close SHORT, Open LONG
- New signal = **HOLD (0)** → Close SHORT, No new position

**Example:**
```
Refresh 1: Final Signal = SELL (-1)
  → Opens SHORT @ ₹100

Refresh 2: Final Signal = SELL (-1)
  → Hold SHORT (no change)

Refresh 3: Final Signal = HOLD (0)
  → Close SHORT @ ₹95
  → Realized PnL = +₹5 (profit from price drop)
```

---

## 🔄 **Signal Change Logic**

The system tracks the **last signal** and compares it to the **current signal**:

```python
# PREVENT DUPLICATE ORDERS - Check if already in same position
same_direction = (signal == 1 and position == 1) or \
                (signal == -1 and position == -1)

if same_direction:
    # Already in this position, just hold and update PnL
    # NO new order created (prevents duplicates)
    pass
elif signal_changed:
    if position is OPEN:
        # Close existing position
        # Record exit price and time
        # Calculate realized PnL
    
    if signal == 1 and position != 1:
        # Open LONG (only if not already LONG)
    elif signal == -1 and position != -1:
        # Open SHORT (only if not already SHORT)
```

**Key Change:** System now prevents duplicate orders by checking if a position already exists in the same direction before opening a new one.

---

## 📊 **Complete Entry/Exit Flow**

### **Scenario 1: BUY Entry → Hold → HOLD Exit**

```
Time 10:00 - Analysis:
  Daily VOMC = 1, Intraday VOMC = 1, RL = 1
  → Raw Signal = 1 (BUY)
  Volatility = 1.5% ✓
  Confidence = 65% ✓
  Trend = Bullish ✓
  Breakout = Bullish ✓
  Momentum = Buy (RSI=58) ✓
  → FINAL SIGNAL = BUY (1)
  
Action: Open LONG @ ₹330.95
Order #1: LONG, Entry: ₹330.95, Status: OPEN

---

Time 10:05 - Analysis:
  Daily VOMC = 1, Intraday VOMC = 1, RL = 1
  → Raw Signal = 1 (BUY)
  All filters pass
  → FINAL SIGNAL = BUY (1)
  
Action: HOLD LONG (signal unchanged)
Current Price: ₹335.50
Unrealized PnL: +₹4.55

---

Time 10:10 - Analysis:
  Daily VOMC = 1, Intraday VOMC = 0, RL = 0
  → Raw Signal = 0 (HOLD)
  → FINAL SIGNAL = HOLD (0)
  
Action: Close LONG @ ₹340.00
Order #1: CLOSED, Exit: ₹340.00
Realized PnL: +₹9.05
```

---

### **Scenario 2: BUY Entry → SELL Signal → Reversal**

```
Time 10:00 - FINAL SIGNAL = BUY (1)
Action: Open LONG @ ₹100

Time 10:05 - FINAL SIGNAL = SELL (-1)
Action: Close LONG @ ₹105 (PnL: +₹5)
        Open SHORT @ ₹105

Time 10:10 - FINAL SIGNAL = SELL (-1)
Action: HOLD SHORT
Current Price: ₹103
Unrealized PnL: +₹2

Time 10:15 - FINAL SIGNAL = BUY (1)
Action: Close SHORT @ ₹102 (PnL: +₹3)
        Open LONG @ ₹102

Total Realized PnL: +₹5 + ₹3 = +₹8
```

---

## 🎯 **Filter Thresholds (Default)**

| Filter | Threshold | Description |
|--------|-----------|-------------|
| **Volatility** | > 1% | Minimum price movement |
| **Confidence** | ≥ 60% | Model probability |
| **RSI Buy** | > 55 | Buying momentum |
| **RSI Sell** | < 45 | Selling momentum |
| **SMA Trend** | 50 vs 200 | Long-term trend |
| **Breakout** | 20 periods | Recent price patterns |

These can be adjusted in `configs/params_fast.yaml`:

```yaml
filters:
  volatility_threshold: 0.01  # 1%
  confidence_threshold: 0.6   # 60%
  rsi_buy: 55
  rsi_sell: 45
  use_sma50_200: true
  breakout_lookback: 20
```

---

## ⚠️ **Important Notes**

### **1. BUY Requires ALL Filters**
- For safety, BUY signals need **all 3 filters** to be bullish
- This reduces false positives
- More conservative entry

### **2. SELL Requires At Least 1 Filter**
- For flexibility, SELL signals need **at least 1** bearish filter
- Allows quicker exits
- More aggressive exit

### **3. HOLD Signal**
- Closes any open position
- Does not open new position
- Occurs when filters don't agree or confidence is low

### **4. Auto-Close on Signal Change**
- Positions automatically close when signal changes
- No manual exit required
- Ensures you're never stuck in a position

### **5. Duplicate Order Prevention** ⭐ **NEW!**
- System checks if position already exists in same direction
- BUY signal when already LONG → **Holds position** (no new order)
- SELL signal when already SHORT → **Holds position** (no new order)
- Prevents unnecessary close/reopen cycles
- Cleaner order history and accurate PnL tracking

---

## 🔍 **Example: Why Signal Might be HOLD**

```
Raw Signal = BUY (1) from models

But...
❌ Trend = Neutral (SMA50 ≈ SMA200)
✓ Breakout = Bullish
✓ Momentum = Buy

Result: Not ALL filters passed (only 2/3)
→ FINAL SIGNAL = HOLD (0)
→ Do not enter position
```

---

## 📈 **PnL Calculation**

### **LONG Position PnL**
```
PnL = (Exit Price - Entry Price) × Quantity
Example: (₹340 - ₹330) × 1 = +₹10
```

### **SHORT Position PnL**
```
PnL = (Entry Price - Exit Price) × Quantity
Example: (₹100 - ₹95) × 1 = +₹5
```

### **Unrealized PnL (Open Position)**
```
LONG: (Current Price - Entry Price) × Quantity
SHORT: (Entry Price - Current Price) × Quantity

Updates every 5 seconds with latest price
```

---

## ✅ **Entry/Exit Checklist**

### **To Enter LONG:**
- [ ] At least 2 models vote BUY
- [ ] Volatility > 1%
- [ ] Confidence ≥ 60%
- [ ] SMA50 > SMA200 (Bullish)
- [ ] HH or HL detected (Breakout)
- [ ] RSI > 55 (Momentum)

### **To Enter SHORT:**
- [ ] At least 2 models vote SELL
- [ ] Volatility > 1%
- [ ] Confidence ≥ 60%
- [ ] At least 1 of:
  - [ ] SMA50 < SMA200 (Bearish)
  - [ ] LL or LH detected (Breakdown)
  - [ ] RSI < 45 (Sell momentum)

### **To Exit Position:**
- [ ] Signal changes from last signal
- [ ] New signal ≠ current position direction

---

## 🎯 **Summary**

**Entry Conditions:**
- **LONG**: All 6 conditions (Raw BUY + 5 filters)
- **SHORT**: 4 conditions (Raw SELL + volatility + confidence + 1 bearish filter)

**Exit Conditions:**
- **Any signal change** from current position
- Automatic exit when new signal appears
- Records entry/exit time, price, and PnL

**Refresh Rate:**
- Analysis runs every **5 seconds**
- Signals can change every refresh
- Positions auto-managed based on signals

---

**Updated**: December 29, 2025  
**Feature**: Complete entry/exit conditions documented  
**Status**: ✅ Fully explained!

