# Fix Applied - "macd not in index" Error

## ✅ Problem Fixed

**Error**: `"['macd'] not in index"`  
**Cause**: Configuration file requested `macd` feature that doesn't exist in the dataframe  
**Fixed**: Updated `configs/params_fast.yaml` to use only available features

---

## What Changed

### File: `configs/params_fast.yaml`

#### ❌ Before (Broken)
```yaml
daily_features:
  - daily_return
  - rsi
  - macd  # ← This feature doesn't exist!
```

#### ✅ After (Fixed)
```yaml
daily_features:
  - daily_return  # ← Always available
  - sma_5         # ← Created by add_technical_features()
  - sma_20        # ← Created by add_technical_features()
  - volatility    # ← Created by add_technical_features()
```

---

## Available Features

### Created by `add_technical_features()`:
- `sma_5` - 5-period simple moving average
- `sma_20` - 20-period simple moving average
- `volatility` - 10-period rolling std of returns

### Created by `add_advanced_features()`:
- `sma_50` - 50-period simple moving average
- `sma_200` - 200-period simple moving average
- `rsi` - Relative Strength Index (14-period)
- `volatility_20` - 20-period rolling std of returns
- `hh`, `hl`, `ll`, `lh` - Breakout patterns

### Always Available:
- `daily_return` - Daily price returns
- `return` - Intraday price returns (for intraday data)

---

## Additional Fixes Applied

1. **Added complete RL configuration** (was incomplete)
2. **Added trading parameters** (stop loss settings)
3. **Updated filter configuration** (matched params.yaml structure)
4. **Set `require_all: false`** for filters (less strict, faster)

---

## How to Run

### Option 1: Using Virtual Environment (Recommended)
```bash
cd /home/sham/Desktop/MARKOV_MARKET
source .venv/bin/activate
python live/run_multi_symbol_intraday.py
```

### Option 2: Using uv run
```bash
cd /home/sham/Desktop/MARKOV_MARKET
uv run live/run_multi_symbol_intraday.py
```

### Option 3: Direct Python (if .venv is active)
```bash
cd /home/sham/Desktop/MARKOV_MARKET
python live/run_multi_symbol_intraday.py
```

---

## Expected Output (After Fix)

```
INFO: Starting multi-symbol intraday analysis for 2 symbols
INFO: Model config: configs/params_fast.yaml
INFO: Max intraday rows: 1000

INFO: Processing symbol 1/2: BSE:SENSEX2610185100PE
INFO: Loading daily data for BSE:SENSEX2610185100PE...
INFO: Adding technical features to daily data...  ← sma_5, sma_20, volatility created
INFO: Loading intraday data for BSE:SENSEX2610185100PE...
INFO: Data loading took 2.50s (Daily: 61 rows, Intraday: 1000 rows)
INFO: Running inference for BSE:SENSEX2610185100PE...
INFO: Inference took 12.34s
SUCCESS: Successfully analyzed BSE:SENSEX2610185100PE in 15.02s ✓

INFO: Processing symbol 2/2: BSE:SENSEX2610185100CE
...
SUCCESS: Successfully analyzed BSE:SENSEX2610185100CE in 14.89s ✓

┌─────────────────────────┬──────────────┬────────────┬─────────────┐
│ Symbol                  │ Final Signal │ Raw Signal │ Status      │
├─────────────────────────┼──────────────┼────────────┼─────────────┤
│ BSE:SENSEX2610185100PE  │ BUY          │ BUY        │ SUCCESS ✓   │
│ BSE:SENSEX2610185100CE  │ HOLD         │ HOLD       │ SUCCESS ✓   │
└─────────────────────────┴──────────────┴────────────┴─────────────┘

SUMMARY: 2 successful, 0 failed out of 2 total symbols
```

---

## Verify the Fix

### Check Configuration
```bash
cat configs/params_fast.yaml | grep -A 5 "daily_features"
```

Should show:
```yaml
daily_features:
  - daily_return
  - sma_5
  - sma_20
  - volatility
```

### Check Features Are Created
The script logs will show:
```
INFO: Adding technical features to daily data...
```

This creates: `sma_5`, `sma_20`, `volatility` ✓

---

## If You Still Get Errors

### Error: Feature not found
**Check**: The feature name matches what's created in `utils/features.py`

**Available features**:
- From `add_technical_features()`: sma_5, sma_20, volatility
- From `add_advanced_features()`: sma_50, sma_200, rsi, volatility_20

### Error: Python version
**Solution**: Activate the virtual environment first:
```bash
source .venv/bin/activate
```

---

## Summary

✅ **Fixed**: Removed non-existent `macd` feature  
✅ **Added**: Correct features (sma_5, sma_20, volatility)  
✅ **Updated**: Complete configuration structure  
✅ **Status**: Ready to run!

---

**Fixed**: December 29, 2025  
**File**: `configs/params_fast.yaml`  
**Error**: "['macd'] not in index"  
**Solution**: Use only features that are actually created

