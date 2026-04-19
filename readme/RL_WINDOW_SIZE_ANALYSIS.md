# RL Agent Window Size Analysis

## Current Setting
- **Window Size**: 10 periods (configurable in `configs/params.yaml` under `rl.window`)
- **Observation**: Last 10 periods of up/down states (binary: 1=up, 0=down)

## Is 10 Periods Enough?

### ✅ Advantages of Window = 10:
1. **Good balance** between short-term and medium-term patterns
2. **Captures recent momentum** (last 10 price movements)
3. **Reasonable training complexity** - not too many patterns to learn
4. **Fast inference** - small observation space
5. **Good for intraday trading** - captures recent price action

### ⚠️ Potential Limitations:
1. **May miss longer-term trends** - only sees last 10 periods
2. **Limited context** - doesn't see broader market structure
3. **May be too reactive** - responds quickly to short-term noise

## Impact of Changing Window Size

### 📉 DECREASING Window Size (e.g., 5, 7)

#### Advantages:
- ✅ **Faster response** to recent price changes
- ✅ **Less training data needed** - fewer patterns to learn
- ✅ **Lower computational cost** - smaller observation space
- ✅ **More reactive** - catches quick momentum shifts
- ✅ **Better for scalping** - very short-term trading

#### Disadvantages:
- ❌ **Less context** - misses longer patterns
- ❌ **More noise** - reacts to short-term fluctuations
- ❌ **Higher false signals** - may trade on noise
- ❌ **Less stable** - decisions change quickly
- ❌ **May overfit** - learns noise instead of patterns

#### Example with Window = 5:
```
Observation: [1, 1, 0, 1, 1]  # Only last 5 periods
- Very recent, but limited context
- May miss that this is part of a larger downtrend
```

### 📈 INCREASING Window Size (e.g., 20, 30, 50)

#### Advantages:
- ✅ **More context** - sees longer-term patterns
- ✅ **Better trend recognition** - identifies sustained moves
- ✅ **More stable signals** - less reactive to noise
- ✅ **Better pattern matching** - recognizes complex sequences
- ✅ **Better for swing trading** - captures medium-term trends

#### Disadvantages:
- ❌ **Slower response** - takes longer to react to changes
- ❌ **More training data needed** - exponentially more patterns
- ❌ **Higher computational cost** - larger observation space
- ❌ **May miss quick opportunities** - too slow to react
- ❌ **Risk of overfitting** - too many patterns to learn properly
- ❌ **Requires more historical data** - needs enough data to train

#### Example with Window = 30:
```
Observation: [1,0,1,1,0,1,1,1,0,1,0,0,1,1,0,1,1,1,0,1,1,0,1,0,1,1,1,0,1,1]
- Much more context, but slower to react
- Can see longer trends, but may miss quick reversals
```

## Pattern Complexity Analysis

### Number of Possible Patterns:
- **Window = 5**: 2^5 = **32 possible patterns**
- **Window = 10**: 2^10 = **1,024 possible patterns**
- **Window = 20**: 2^20 = **1,048,576 possible patterns**
- **Window = 30**: 2^30 = **1,073,741,824 possible patterns**

### Training Implications:
- **Smaller window (5-10)**: Easier to train, learns faster, less data needed
- **Larger window (20+)**: Harder to train, needs more data, longer training time

## Recommendations by Trading Style

### Scalping (Very Short-Term):
- **Recommended**: Window = 5-7
- **Reason**: Need quick reactions to immediate price movements

### Intraday Trading (Current Use Case):
- **Recommended**: Window = 10-15
- **Reason**: Balance between responsiveness and context
- **Current setting (10) is reasonable** ✅

### Swing Trading (Multi-Day):
- **Recommended**: Window = 20-30
- **Reason**: Need to capture longer-term trends

### Position Trading (Weeks/Months):
- **Recommended**: Window = 50-100
- **Reason**: Focus on major trends, ignore short-term noise

## Practical Impact Examples

### Scenario: Price Suddenly Reverses

**Window = 5:**
- Sees: `[1, 1, 1, 0, 0]` → Quick reversal detected
- **Action**: Reacts immediately, may catch reversal early
- **Risk**: May be false signal, reacts to noise

**Window = 10 (Current):**
- Sees: `[1, 1, 1, 1, 1, 1, 1, 0, 0, 0]` → Reversal in context
- **Action**: Moderate reaction, considers recent uptrend
- **Risk**: Balanced - not too fast, not too slow

**Window = 20:**
- Sees: `[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0]` → Reversal in longer context
- **Action**: Slower reaction, waits for confirmation
- **Risk**: May miss quick reversals, but more stable

### Scenario: Strong Uptrend

**Window = 5:**
- Sees: `[1, 1, 1, 1, 1]` → Strong uptrend
- **Action**: BUY signal
- **Issue**: May not see if this is continuation or exhaustion

**Window = 10 (Current):**
- Sees: `[0, 0, 1, 1, 1, 1, 1, 1, 1, 1]` → Uptrend with some context
- **Action**: BUY signal with better context
- **Issue**: Still limited, but reasonable

**Window = 20:**
- Sees: `[0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]` → Strong uptrend from base
- **Action**: BUY with strong confidence
- **Issue**: May be too late, trend already established

## Testing Different Window Sizes

### How to Test:
1. **Backtest with different windows** (5, 10, 15, 20, 30)
2. **Compare metrics**:
   - Sharpe ratio
   - Win rate
   - Average profit per trade
   - Maximum drawdown
   - Number of trades
3. **Choose based on**:
   - Your trading style
   - Market conditions
   - Performance metrics

### Code to Test:
```python
# In configs/params.yaml, try different values:
rl:
  window: 5   # Test smaller
  # window: 10  # Current
  # window: 15  # Test larger
  # window: 20  # Test much larger
```

## Current Recommendation

### ✅ **Window = 10 is a GOOD starting point** because:

1. **Balanced**: Not too reactive, not too slow
2. **Manageable complexity**: 1,024 patterns is learnable
3. **Good for intraday**: Captures recent momentum
4. **Reasonable training time**: Won't take forever to train
5. **Industry standard**: Many RL trading systems use 10-15

### 🔄 **Consider Adjusting If**:

- **Too many false signals** → Try increasing to 15-20
- **Missing quick opportunities** → Try decreasing to 5-7
- **Market is very choppy** → Try increasing to 15-20 (more stable)
- **Market has strong trends** → Current 10 is fine, or try 15

## Summary Table

| Window Size | Best For | Pros | Cons | Complexity |
|-------------|----------|------|------|------------|
| **5** | Scalping | Fast, reactive | Noisy, less context | Low (32 patterns) |
| **7** | Short-term | Quick response | Limited context | Low (128 patterns) |
| **10** ✅ | **Intraday** | **Balanced** | **Moderate context** | **Medium (1K patterns)** |
| **15** | Intraday-Swing | Good context | Slower response | Medium (32K patterns) |
| **20** | Swing trading | Strong context | Slow, needs more data | High (1M patterns) |
| **30+** | Position trading | Very stable | Very slow, complex | Very High (1B+ patterns) |

## Conclusion

**Window = 10 is a solid choice** for intraday trading. It provides:
- ✅ Good balance between responsiveness and context
- ✅ Manageable training complexity
- ✅ Reasonable pattern recognition

**Consider experimenting** with 7-15 range to find what works best for your specific:
- Market conditions
- Trading style
- Data frequency (5-second bars in your case)

The optimal window size depends on your specific use case and should be validated through backtesting.

