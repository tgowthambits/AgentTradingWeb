# Symbol Loading Issue - Bank Nifty Options Not Showing

## Problem
User configured 6 symbols but only 4 are appearing in console and UI:

### Configured (6 symbols):
1. ✅ BSE:SENSEX2610184700PE
2. ✅ BSE:SENSEX2610184700CE
3. ✅ NSE:NIFTY25DEC25950PE
4. ✅ NSE:NIFTY25DEC25950CE
5. ❌ NSE:NBANKNIFTY25DEC58900PE
6. ❌ NSE:NBANKNIFTY25DEC58900CE

### Shown (4 symbols):
Only the first 4 symbols appear in the table.

## Root Causes Found

### 1. Data Fetch Failures
From terminal logs:
```
Line 81: Getting data for NSE:NBANKNIFTY25DEC58900PE
Line 83: Cache name: fyers_cache_NSE:NBANKNIFTY25DEC58900PE...
```

But **NO** "Data: XXX rows" message appears for NBANKNIFTY (unlike other symbols).

### 2. Silent Error Handling
The bot's `run_once()` method catches exceptions but doesn't show detailed error information:

```python
except Exception as e:
    console.print(f"[red]Error analyzing {symbol}: {str(e)}[/red]")
    # No traceback shown!
```

### 3. Possible Causes for Data Fetch Failure

#### A. Symbol Format Issue
- Bank Nifty options use **NBANKNIFTY** prefix
- Format: `NSE:NBANKNIFTY25DEC58900PE`
- This format might not be recognized by Fyers API

#### B. Contract Expiry
- 25DEC expiry might be expired or invalid
- Options contracts have specific strike prices
- 58900 strike might not exist for Bank Nifty

#### C. API Data Availability
- Bank Nifty options might not be available in test mode
- Paper trading might not support these contracts
- API might not have data for these symbols

#### D. DataFrame Column Mismatch
From logs:
```
ERROR | Data.DATA_SOURCE:get_data:101 - Error in fetching data: 6 columns passed, passed data had 7 columns
```

This error appears for ALL symbols, but only Bank Nifty fails completely.

## Solutions Applied

### 1. Enhanced Error Reporting
**File**: `trading_system/run_live_bot.py`

Added detailed error tracking:

```python
except Exception as e:
    console.print(f"[red]❌ Error analyzing {symbol}: {str(e)}[/red]")
    import traceback
    console.print(f"[dim]{traceback.format_exc()}[/dim]")
```

Now shows full stack trace when symbol processing fails.

### 2. Empty Data Checking
**File**: `trading_system/run_live_bot.py`

Added data validation before processing:

```python
# Check if data is valid
if df is None or df.empty:
    console.print(f"[yellow]⚠️  No data returned for {symbol}, skipping...[/yellow]")
    continue

# Prepare data
df = self.data_loader.prepare_for_indicators(df)
```

This will show a clear warning when data fetch returns empty results.

## How to Diagnose

### Step 1: Restart Bot with Enhanced Logging

```bash
python trading_system/run_live_bot.py
```

Watch for:
- `❌ Error analyzing NSE:NBANKNIFTY...` messages
- `⚠️ No data returned for NSE:NBANKNIFTY...` warnings
- Full stack traces showing exact error

### Step 2: Check Terminal Output

Look for patterns:
- Does it show "Data: XXX rows" for Bank Nifty?
- Are there specific error messages?
- Does data fetch timeout?

### Step 3: Verify Symbol Format

Bank Nifty option symbol format should be:
```
NSE:BANKNIFTY[EXPIRY][STRIKE][CE/PE]
```

Example valid formats:
- `NSE:BANKNIFTY30DEC2458900CE`  
- `NSE:BANKNIFTY30DEC2458900PE`

**NOT:**
- `NSE:NBANKNIFTY25DEC58900PE` ❌ (Invalid format)

## Likely Issue: Symbol Format

### Problem
The symbols use `NBANKNIFTY` but should use `BANKNIFTY`

### Incorrect Format:
```yaml
- NSE:NBANKNIFTY25DEC58900PE  ❌
- NSE:NBANKNIFTY25DEC58900CE  ❌
```

### Correct Format:
```yaml
- NSE:BANKNIFTY30DEC2458900PE  ✅
- NSE:BANKNIFTY30DEC2458900CE  ✅
```

### Format Components:
1. Exchange: `NSE:`
2. Instrument: `BANKNIFTY` (not NBANKNIFTY)
3. Expiry: `30DEC24` (date format: DDMMMYY)
4. Strike: `58900`
5. Type: `PE` or `CE`

## Recommended Fixes

### Option 1: Fix Symbol Names (Recommended)
**File**: `trading_system/config/trading_config.yaml`

```yaml
symbols:
  - BSE:SENSEX2610184700PE
  - BSE:SENSEX2610184700CE
  - NSE:NIFTY25DEC25950PE
  - NSE:NIFTY25DEC25950CE
  - NSE:BANKNIFTY30DEC2458900PE    # Changed from NBANKNIFTY
  - NSE:BANKNIFTY30DEC2458900CE    # Changed from NBANKNIFTY
```

### Option 2: Verify Expiry and Strike

Check if:
- 25DEC expiry is valid (might be expired)
- 58900 strike exists for Bank Nifty
- Use current/upcoming expiry dates

### Option 3: Check Available Strikes

Bank Nifty typical strikes (100-point intervals):
- 58700, 58800, 58900, 59000, etc.

Verify 58900 is a valid strike for the expiry date.

### Option 4: Use Paper Trading Symbols

If in paper trading mode, use symbols that are definitely available:
```yaml
- NSE:BANKNIFTY  # Index itself
- NSE:BANKNIFTY-EQ  # Equity format
```

## Testing Steps

### 1. Update Symbol Format
Edit `trading_system/config/trading_config.yaml`:

```yaml
symbols:
  - NSE:BANKNIFTY30DEC2459000CE  # Use current expiry
  - NSE:BANKNIFTY30DEC2459000PE
```

### 2. Restart Bot

```bash
# Stop current bot (Ctrl+C)
python trading_system/run_live_bot.py
```

### 3. Watch for Errors

Terminal should now show:
- Either: `⚠️ No data returned for...` (symbol still invalid)
- Or: Data loads successfully and all 6 symbols appear

### 4. Check Fyers Symbol Search

Use Fyers API to search for valid symbols:
```python
# In test.py or Python console
from Data.fyers_data_final import fyers_data

# Search for Bank Nifty options
results = fyers_data.search("BANKNIFTY")
print(results)
```

## Expected Behavior After Fix

### With Correct Symbols:
```
Symbols: BSE:SENSEX..., NSE:NIFTY..., NSE:BANKNIFTY...
                    📊 Complete Trading Analysis & Positions
╭──────────┬────────┬───────┬──────┬──────┬──────┬──────╮
│ Symbol   │ LTP    │ Signal│  BB  │ MACD │ ...  │  ... │
├──────────┼────────┼───────┼──────┼──────┼──────┼──────┤
│ SENSEX.. │ 211.70 │ HOLD  │  ○   │  ✓   │  ✗   │  ... │
│ SENSEX.. │ 288.00 │ HOLD  │  ○   │  ✗   │  ✓   │  ... │
│ NIFTY..  │ 36.95  │ HOLD  │  ○   │  ✓   │  ✗   │  ... │
│ NIFTY..  │ 28.50  │ SELL  │  ○   │  ✗   │  ✗   │  ... │
│ BANKNIF..│ 45.50  │ BUY   │  ✓   │  ✓   │  ✓   │  ... │  ✅
│ BANKNIF..│ 52.30  │ HOLD  │  ○   │  ✓   │  ○   │  ... │  ✅
╰──────────┴────────┴───────┴──────┴──────┴──────┴──────╯
```

All 6 symbols showing!

### With Invalid Symbols:
```
⚠️ No data returned for NSE:NBANKNIFTY25DEC58900PE, skipping...
⚠️ No data returned for NSE:NBANKNIFTY25DEC58900CE, skipping...
```

Clear error messages.

## Files Modified

1. **`trading_system/run_live_bot.py`**
   - Added full error traceback
   - Added empty data checking
   - Better error messages

## Next Steps

1. **Update symbol format** in `trading_config.yaml`
2. **Restart the bot** to see detailed errors
3. **Verify symbols** using Fyers symbol search
4. **Check expiry dates** - use current/upcoming expiries
5. **Confirm strikes** - ensure they exist for Bank Nifty

## Common Bank Nifty Symbol Formats

### Current Week Expiry:
```yaml
NSE:BANKNIFTY30DEC2459000CE
NSE:BANKNIFTY30DEC2459000PE
```

### Monthly Expiry:
```yaml
NSE:BANKNIFTY30JAN2559000CE
NSE:BANKNIFTY30JAN2559000PE
```

### Futures:
```yaml
NSE:BANKNIFTY25JANFUT
NSE:BANKNIFTY25FEBFUT
```

---

**Status**: ⚠️ Awaiting symbol format correction
**Action Required**: Update `trading_config.yaml` with correct Bank Nifty symbol format
**Testing**: Restart bot after updating symbols

