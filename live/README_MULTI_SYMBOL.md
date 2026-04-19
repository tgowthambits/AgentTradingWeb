# 🚀 Multi-Symbol Intraday Trading System

## Overview

This system allows you to run intraday trading analysis on multiple symbols **sequentially** (one at a time) to prevent console hanging. Results are saved incrementally to a CSV file after each symbol is processed.

## 📁 Files Created

### Core Files
1. **`run_multi_symbol_intraday.py`** - Main script for multi-symbol analysis
2. **`configs/symbols_config.yaml`** - Configuration file for symbols and settings
3. **`example_multi_symbol.py`** - Simple example script
4. **`test_multi_symbol_setup.py`** - Setup verification script

### Documentation
5. **`QUICK_START_MULTI_SYMBOL.md`** - Quick start guide (3 steps)
6. **`MULTI_SYMBOL_USAGE.md`** - Complete documentation
7. **`IMPLEMENTATION_SUMMARY.md`** - Technical implementation details
8. **`README_MULTI_SYMBOL.md`** - This file

## 🎯 Key Features

✅ **Sequential Processing** - No more console hanging  
✅ **Incremental Saving** - Results saved after each symbol  
✅ **Error Resilience** - Continues even if some symbols fail  
✅ **Detailed Tables** - Both summary and per-symbol analysis  
✅ **Easy Configuration** - YAML-based symbol management  
✅ **Progress Tracking** - Real-time logging  
✅ **40+ Data Fields** - Comprehensive analysis per symbol  

## 🚀 Quick Start (3 Steps)

### Step 1: Verify Setup

```bash
python test_multi_symbol_setup.py
```

This will check:
- All required files exist
- Python dependencies are installed
- Configuration is valid
- Results directory exists

### Step 2: Configure Symbols

Edit `configs/symbols_config.yaml`:

```yaml
symbols:
  - "BSE:SENSEX2610185100CE"
  - "BSE:SENSEX2610185100PE"
  # Add more symbols here

date_range:
  start_date: "2025-12-27 16:15:00"
  end_date: "2025-12-29 16:15:00"

output:
  results_csv: "results/multi_symbol_intraday_results.csv"
```

### Step 3: Run Analysis

```bash
python run_multi_symbol_intraday.py
```

## 📊 What You Get

### 1. Console Output

#### Summary Table
```
┌─────────────────────────┬──────────────┬────────────┬─────────────┬────────────┐
│ Symbol                  │ Final Signal │ Raw Signal │ Daily VOMC  │ Status     │
├─────────────────────────┼──────────────┼────────────┼─────────────┼────────────┤
│ BSE:SENSEX2610185100CE  │ BUY          │ BUY        │ BUY         │ SUCCESS    │
│ BSE:SENSEX2610185100PE  │ HOLD         │ HOLD       │ HOLD        │ SUCCESS    │
└─────────────────────────┴──────────────┴────────────┴─────────────┴────────────┘
```

#### Detailed Analysis (Per Symbol)
```
📊 SYMBOL: BSE:SENSEX2610185100CE
────────────────────────────────────────

┌─ MODEL SIGNALS ─────────────────────┐
│ Daily VOMC Signal:     BUY          │
│ Daily Regime:          2            │
│ Intraday VOMC Signal:  BUY          │
│ RL Agent Action:       BUY          │
└─────────────────────────────────────┘

┌─ PRECISION FILTERS ─────────────────┐
│ Volatility Filter:      PASS        │
│ Trend Filter:          BULLISH      │
│ Breakout Filter:       BULLISH      │
│ Momentum Filter:       BUY          │
│ Confidence Filter:     PASS         │
└─────────────────────────────────────┘

┌─ FINAL DECISION ────────────────────┐
│           🟢 BUY SIGNAL             │
└─────────────────────────────────────┘
```

### 2. CSV File

Location: `results/multi_symbol_intraday_results.csv`

Contains 40+ columns including:
- Symbol identification
- Timestamps
- Daily signals (VOMC, HMM, XGBoost)
- Intraday signals (VOMC, HMM, XGBoost, RL)
- Signal fusion (raw + final)
- All filter results
- Confirmations
- Status and errors

## 📖 Documentation

| Document | Purpose |
|----------|---------|
| `QUICK_START_MULTI_SYMBOL.md` | 3-step quick start guide |
| `MULTI_SYMBOL_USAGE.md` | Complete usage documentation |
| `IMPLEMENTATION_SUMMARY.md` | Technical implementation details |
| `README_MULTI_SYMBOL.md` | This overview document |

## 🔧 Configuration Options

### Symbols
Add as many symbols as needed:
```yaml
symbols:
  - "BSE:SENSEX2610185100CE"
  - "BSE:SENSEX2610185100PE"
  - "BSE:SENSEX25DEC85400PE"
  - "NSE:NIFTY50-INDEX"
```

### Date Range
Customize analysis period:
```yaml
date_range:
  start_date: "2025-12-20 16:15:00"
  end_date: "2025-12-29 16:15:00"
```

### Output File
Change result file location:
```yaml
output:
  results_csv: "results/my_custom_results.csv"
```

### Position Tracking
Track if you have open positions:
```yaml
has_position: false  # Set to true if you have positions
```

## 🛠️ Installation

### Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- pandas
- numpy
- pyyaml
- loguru
- tabulate
- hmmlearn
- xgboost
- stable-baselines3
- scikit-learn

### Verify Installation

```bash
python test_multi_symbol_setup.py
```

## 📈 Usage Examples

### Example 1: Basic Usage

```bash
# Edit config
nano configs/symbols_config.yaml

# Run analysis
python run_multi_symbol_intraday.py

# Check results
cat results/multi_symbol_intraday_results.csv
```

### Example 2: Programmatic Usage

```python
from run_multi_symbol_intraday import run_symbol_analysis, save_results

symbols = ["BSE:SENSEX2610185100CE", "BSE:SENSEX2610185100PE"]
results = []

for symbol in symbols:
    result = run_symbol_analysis(
        symbol=symbol,
        start_date='2025-12-27 16:15:00',
        end_date='2025-12-29 16:15:00',
        has_position=False
    )
    results.append(result)
    save_results(results, 'my_results.csv')
```

### Example 3: Using the Example Script

```bash
python example_multi_symbol.py
```

## 🔍 Understanding Results

### Signal Values
- **1** / **BUY**: Buy signal
- **-1** / **SELL**: Sell signal  
- **0** / **HOLD**: Hold/no action

### Filter Status
- **PASS** / **✓**: Filter passed
- **FAIL** / **✗**: Filter failed

### Trend Values
- **BULLISH**: Upward trend
- **BEARISH**: Downward trend
- **NEUTRAL**: No clear trend

### Status Values
- **SUCCESS**: Analysis completed successfully
- **ERROR**: Analysis failed (see error column)

## ⚠️ Troubleshooting

### Problem: Console Hanging
**Solution**: The new script processes symbols sequentially to prevent this.

### Problem: Missing Dependencies
**Solution**: 
```bash
pip install -r requirements.txt
```

### Problem: Symbol Error
**Solution**: 
- Check symbol format (needs BSE: or NSE: prefix)
- Verify date range has trading data
- Check Fyers API connection

### Problem: Config Error
**Solution**:
```bash
python test_multi_symbol_setup.py
```

## 🔄 Workflow

```
1. Configure
   ↓
2. Verify Setup (test_multi_symbol_setup.py)
   ↓
3. Run Analysis (run_multi_symbol_intraday.py)
   ↓
4. Monitor Progress (console logs)
   ↓
5. Review Results (CSV + console tables)
   ↓
6. Take Trading Action
```

## 📊 Data Flow

```
Config File (symbols_config.yaml)
  ↓
Load Symbol Data (Daily + Intraday)
  ↓
Add Technical Indicators
  ↓
Run Models (VOMC, HMM, XGBoost, RL)
  ↓
Fuse Signals (Majority Voting)
  ↓
Apply Filters (Volatility, Trend, etc.)
  ↓
Generate Final Signal
  ↓
Save to CSV (Incremental)
  ↓
Display Results (Console Tables)
```

## 🎯 Key Advantages Over Previous Approach

| Feature | Old Approach | New Approach |
|---------|-------------|--------------|
| Processing | Simultaneous (hangs) | Sequential (stable) |
| Saving | All at once | Incremental |
| Error Handling | Stops on error | Continues |
| Progress | Hidden | Real-time logs |
| Configuration | Hardcoded | YAML file |
| Output | Single format | CSV + Tables |

## 💡 Pro Tips

1. **Start Small**: Test with 2 symbols first
2. **Monitor Logs**: Watch console for real-time status
3. **Check CSV**: Results saved after each symbol
4. **Review Errors**: Failed symbols marked with details
5. **Use Config**: Easy to manage symbol lists
6. **Incremental**: Safe to interrupt and resume

## 🔗 Integration

### With Existing Scripts
Uses same pipeline as `main.py`:
- `pipeline/live_inference.py`
- `pipeline/run_daily_models.py`
- `pipeline/run_intraday_models.py`
- `utils/filters.py`

### With Live Trading
Compatible with:
- `live/run_live.py`
- `live/realtime_trader.py`
- `live/position_tracker.py`

## 📝 Output Fields Reference

### Identification
- symbol, timestamp, start_date, end_date, status, error

### Daily Models
- daily_vomc_signal, daily_vomc_prob
- daily_regime, daily_return_prediction

### Intraday Models
- intraday_vomc_signal, intraday_vomc_prob
- intraday_regime, intraday_return_prediction
- rl_action

### Signals
- raw_signal, final_signal

### Filters
- volatility_filter, trend_filter
- breakout_filter, momentum_filter
- confidence_filter

### Confirmations
- trend_confirmation
- breakout_confirmation
- momentum_confirmation

## ✅ Testing Checklist

- [ ] Run `python test_multi_symbol_setup.py`
- [ ] Edit `configs/symbols_config.yaml`
- [ ] Add 2 test symbols
- [ ] Run `python run_multi_symbol_intraday.py`
- [ ] Check console output
- [ ] Verify CSV file created
- [ ] Review detailed tables
- [ ] Add more symbols
- [ ] Run full analysis

## 🎓 Learning Resources

1. **Quick Start**: Read `QUICK_START_MULTI_SYMBOL.md`
2. **Full Docs**: Read `MULTI_SYMBOL_USAGE.md`
3. **Technical**: Read `IMPLEMENTATION_SUMMARY.md`
4. **Example**: Run `example_multi_symbol.py`
5. **Test**: Run `test_multi_symbol_setup.py`

## 🚦 Status

✅ **Ready for Production Use**

- All files created
- Documentation complete
- Error handling implemented
- Testing script provided
- Examples included

## 📞 Support

For issues or questions:
1. Check documentation files
2. Run test script: `python test_multi_symbol_setup.py`
3. Review error messages in console
4. Check CSV file for error details

---

**Version**: 1.0  
**Created**: December 29, 2025  
**Purpose**: Multi-symbol intraday trading analysis without console hanging  
**Status**: Production Ready ✅

