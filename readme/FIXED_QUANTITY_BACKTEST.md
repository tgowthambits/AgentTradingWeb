# ✅ Fixed Quantity for Backtesting

## 🎯 Change Made

The backtesting now uses a **fixed quantity of 25** for all trades, instead of dynamic position sizing based on risk management.

---

## 📝 What Changed

### Modified: `trading_system/core/trading_engine.py`

In the `_open_position()` method:

**Before:**
```python
# Dynamic position sizing
final_quantity = quantity

if self.advanced_features:
    optimal_size = self.risk_manager.calculate_position_size(...)
    final_quantity = min(optimal_size, quantity)
```

**After:**
```python
# Check if backtest mode
backtest_mode = self.config.get('backtest', {}).get('enabled', False)

# Fixed quantity for backtest, dynamic for live
final_quantity = 25 if backtest_mode else quantity

if self.advanced_features:
    if not backtest_mode:  # Skip dynamic sizing in backtest
        optimal_size = self.risk_manager.calculate_position_size(...)
        final_quantity = min(optimal_size, quantity)
```

---

## 🔄 Behavior

### In Backtest Mode (`backtest.enabled: true`):
- ✅ **Fixed quantity: 25** for all trades
- ✅ Stop loss still calculated (volatility-adjusted)
- ✅ Profit targets still calculated
- ✅ Exit strategies still active
- ✅ Position limits NOT enforced
- ✅ Display shows: "Position Size: 25 (fixed for backtest)"

### In Live Mode (`backtest.enabled: false`):
- ✅ **Dynamic position sizing** based on risk
- ✅ Risk per trade: 1.5% of capital
- ✅ Adjusts for volatility
- ✅ Position limits enforced
- ✅ Display shows: "Position Size: X (optimal)"

---

## 📊 What You'll See in Backtest

### When Opening Position:

```
📊 Risk Analysis:
   Volatility Regime: NORMAL
   ATR: ₹3.45
   Stop Loss: ₹94.10
   Position Size: 25 (fixed for backtest)
   Profit Targets: ₹105.18 / ₹108.63 / ₹113.80

📈 OPENED LONG position: NSE:NIFTY2610626000PE @ ₹100.00 x 25 (Order #1)
```

**Notice:**
- Position Size: **Always 25**
- Label says: **(fixed for backtest)**
- Not: ~~(optimal)~~

---

## 💡 Why This Change?

### Consistency:
- All trades use same quantity
- Easier to compare performance across symbols
- Simpler PnL calculations

### Comparability:
- Can compare backtests directly
- Not affected by capital changes
- Pure strategy performance

### Simplicity:
- No position sizing complexity in backtest
- Focus on entry/exit logic
- Clearer trade analysis

---

## 🎨 Impact on Results

### Position Sizing:
| Mode | Before | After |
|------|--------|-------|
| **Backtest** | Variable (15-50) | **Fixed: 25** |
| **Live** | Variable (optimal) | Variable (optimal) |

### Exit Strategies:
| Strategy | Backtest | Live |
|----------|----------|------|
| Volatility Stop Loss | ✅ Active | ✅ Active |
| Trailing Stop | ✅ Active | ✅ Active |
| Profit Targets | ✅ Active | ✅ Active |
| Time Exit | ✅ Active | ✅ Active |
| Microstructure | ✅ Active | ✅ Active |

### Risk Management:
| Feature | Backtest | Live |
|---------|----------|------|
| Position Size | Fixed: 25 | Dynamic |
| Stop Loss | Calculated | Calculated |
| Profit Targets | Calculated | Calculated |
| Position Limits | Disabled | Enabled |
| Daily Loss Limit | Disabled | Enabled |

---

## 🚀 Testing

Run your backtest:

```bash
cd /home/sham/Desktop/MARKOV_MARKET
python trading_system/run_live_bot.py
```

**Expected Output:**
```
📊 Risk Analysis:
   Volatility Regime: NORMAL
   ATR: ₹3.45
   Stop Loss: ₹94.10
   Position Size: 25 (fixed for backtest)  ← Always 25!
   Profit Targets: ₹105.18 / ₹108.63 / ₹113.80

📈 OPENED LONG position: ... @ ₹100.00 x 25
```

---

## 📈 Example Trades

### Trade 1:
```
Symbol: NIFTY2610626000PE
Entry: ₹100.00
Quantity: 25 (fixed)
Exit: ₹105.18
PnL: ₹+129.50  (25 × 5.18)
```

### Trade 2:
```
Symbol: BANKNIFTY26JAN59300PE
Entry: ₹665.95
Quantity: 25 (fixed)
Exit: ₹716.80
PnL: ₹+1,271.25  (25 × 50.85)
```

### Trade 3:
```
Symbol: SENSEX26JAN84800PE
Entry: ₹290.30
Quantity: 25 (fixed)
Exit: ₹287.20
PnL: ₹-77.50  (25 × -3.10)
```

**All trades: Exactly 25 quantity!**

---

## ✅ Verification

Check your backtest output:

- [ ] All positions show "Quantity: 25"
- [ ] Risk analysis shows "Position Size: 25 (fixed for backtest)"
- [ ] No positions with varying quantities
- [ ] PnL calculations are consistent
- [ ] Stop losses still trigger
- [ ] Profit targets still trigger

---

## 🔧 Configuration

Your `trading_config.yaml`:

```yaml
backtest:
  enabled: true           # This enables fixed quantity
  start_date: '2025-12-29 09:15:00'
  end_date: '2025-12-30 15:30:00'
  initial_capital: 20000
  speed: 'fast'
```

**When `enabled: true`:**
- Quantity = 25 (fixed)
- Dynamic sizing disabled
- Position limits disabled

**When `enabled: false`:**
- Quantity = calculated (optimal)
- Dynamic sizing enabled
- Position limits enabled

---

## 💻 Code Reference

Location: `trading_system/core/trading_engine.py`

Method: `_open_position()`

Lines: ~280-330

Key Logic:
```python
# Check mode
backtest_mode = self.config.get('backtest', {}).get('enabled', False)

# Set quantity
final_quantity = 25 if backtest_mode else quantity

# Skip dynamic sizing in backtest
if not backtest_mode and self.risk_manager.can_open_position(...):
    optimal_size = self.risk_manager.calculate_position_size(...)
    final_quantity = min(optimal_size, quantity)
```

---

## 🎯 Summary

| Aspect | Value |
|--------|-------|
| **Fixed Quantity** | 25 |
| **Mode** | Backtest only |
| **Live Trading** | Still uses dynamic sizing |
| **Stop Loss** | Still calculated |
| **Profit Targets** | Still calculated |
| **Exit Strategies** | Fully active |

---

## ✅ Result

Your backtest now:
- ✅ Uses consistent quantity of 25 for all trades
- ✅ Maintains all exit strategies
- ✅ Calculates stop loss and profit targets
- ✅ Simpler and more consistent results
- ✅ Easier to analyze performance

**All trades will now use exactly 25 quantity! 🎯**

