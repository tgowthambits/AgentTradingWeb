# ⚡ Quick Configuration Reference

## 📍 Config File Location
`trading_system/config/indicators_config.yaml`

---

## 🎚️ Aggregation Strategies

### 1. Threshold (Recommended for Control)
```yaml
aggregation:
  strategy: "threshold"
  threshold:
    min_indicators_buy: 3     # How many must say BUY
    min_indicators_sell: 3    # How many must say SELL
    min_agreement_percent: 75 # % agreement needed
```

**When to use:**
- You want precise control
- You want to set minimum indicator counts
- You want to require % agreement

**Examples:**
- **Aggressive**: `min: 2, percent: 50`
- **Balanced**: `min: 3, percent: 65`
- **Conservative**: `min: 3, percent: 75`
- **Very Safe**: `min: 4, percent: 90`

---

### 2. Weighted (Recommended for Different Importance)
```yaml
aggregation:
  strategy: "weighted"

indicators:
  rsi:
    weight: 1.0  # Normal
  ma_crossover:
    weight: 2.0  # 2x more important
  macd:
    weight: 0.5  # Half as important
```

**When to use:**
- Some indicators are more reliable
- You want to give more weight to certain signals
- Historical data shows some indicators perform better

---

### 3. Majority (Simple & Quick)
```yaml
aggregation:
  strategy: "majority"
```

**When to use:**
- Simple approach
- All indicators equally trusted
- Quick decision making

**Logic:** Whichever signal (BUY/SELL/HOLD) has most votes wins

---

### 4. Unanimous (Very Conservative)
```yaml
aggregation:
  strategy: "unanimous"
```

**When to use:**
- Very conservative trading
- Only trade when 100% agreement
- Reduce false signals

**Logic:** ALL indicators must agree, otherwise HOLD

---

### 5. Conservative (Strong Agreement)
```yaml
aggregation:
  strategy: "conservative"
  conservative:
    min_agreement: 0.75  # 75% must agree
```

**When to use:**
- Conservative but not unanimous
- Want strong agreement
- Balanced risk approach

---

## 🎛️ Enable/Disable Indicators

```yaml
indicators:
  rsi:
    enabled: true   # ✅ ACTIVE
  
  ma_crossover:
    enabled: false  # ❌ DISABLED
  
  macd:
    enabled: true   # ✅ ACTIVE
  
  bollinger_bands:
    enabled: false  # ❌ DISABLED
```

**Effect:** Only enabled indicators are loaded (saves resources)

---

## ⚖️ Adjust Weights

```yaml
indicators:
  rsi:
    weight: 1.0   # Standard
  
  ma_crossover:
    weight: 1.5   # 50% more important
  
  macd:
    weight: 2.0   # 2x more important
  
  bollinger_bands:
    weight: 0.5   # Half as important
```

**Note:** Only applies when `strategy: "weighted"`

---

## 🔧 Indicator Parameters

### RSI
```yaml
rsi:
  enabled: true
  weight: 1.0
  params:
    period: 14        # Lookback period
    oversold: 30      # Buy threshold
    overbought: 70    # Sell threshold
```

### Moving Average Crossover
```yaml
ma_crossover:
  enabled: true
  weight: 1.5
  params:
    fast_period: 50   # Fast MA period
    slow_period: 200  # Slow MA period
    ma_type: "sma"    # Type: 'sma' or 'ema'
```

### MACD
```yaml
macd:
  enabled: true
  weight: 1.2
  params:
    fast_period: 12    # Fast EMA
    slow_period: 26    # Slow EMA
    signal_period: 9   # Signal line
```

### Bollinger Bands
```yaml
bollinger_bands:
  enabled: true
  weight: 0.8
  params:
    period: 20      # Moving average period
    std_dev: 2.0    # Standard deviations
```

---

## 📊 Preset Configurations

### 🔴 AGGRESSIVE
```yaml
aggregation:
  strategy: "threshold"
  threshold:
    min_indicators_buy: 2
    min_indicators_sell: 2
    min_agreement_percent: 50

indicators:
  rsi: {enabled: true, weight: 1.0}
  ma_crossover: {enabled: true, weight: 1.0}
  # Others disabled for speed
```

**Characteristics:**
- Quick to trigger
- More trades
- Higher risk
- Good for volatile markets

---

### 🟡 BALANCED
```yaml
aggregation:
  strategy: "weighted"

indicators:
  rsi: {enabled: true, weight: 1.0}
  ma_crossover: {enabled: true, weight: 1.5}
  macd: {enabled: true, weight: 1.2}
  bollinger_bands: {enabled: true, weight: 0.8}
```

**Characteristics:**
- Moderate frequency
- Balanced risk/reward
- Uses all indicators
- Good for most markets

---

### 🟢 CONSERVATIVE
```yaml
aggregation:
  strategy: "threshold"
  threshold:
    min_indicators_buy: 3
    min_indicators_sell: 3
    min_agreement_percent: 75

indicators:
  rsi: {enabled: true, weight: 1.0}
  ma_crossover: {enabled: true, weight: 1.5}
  macd: {enabled: true, weight: 1.2}
  bollinger_bands: {enabled: true, weight: 1.0}
```

**Characteristics:**
- Fewer trades
- Lower risk
- High confidence signals
- Good for trending markets

---

### 🔵 VERY CONSERVATIVE
```yaml
aggregation:
  strategy: "unanimous"

indicators:
  rsi: {enabled: true, weight: 1.0}
  ma_crossover: {enabled: true, weight: 1.0}
  macd: {enabled: true, weight: 1.0}
  bollinger_bands: {enabled: true, weight: 1.0}
```

**Characteristics:**
- Very few trades
- Minimal risk
- All must agree
- Good for uncertain markets

---

## 🎯 Common Adjustments

### Make More Aggressive
1. Lower `min_indicators_buy` (e.g., 2 instead of 3)
2. Lower `min_agreement_percent` (e.g., 50% instead of 75%)
3. Use `majority` strategy
4. Enable fewer indicators (faster decisions)

### Make More Conservative
1. Increase `min_indicators_buy` (e.g., 3 or 4)
2. Increase `min_agreement_percent` (e.g., 80% or 90%)
3. Use `unanimous` strategy
4. Enable more indicators (more checks)

### Trust Specific Indicators More
1. Use `weighted` strategy
2. Increase their `weight` (e.g., 2.0)
3. Decrease others' weights (e.g., 0.5)

### Speed Up Bot (Less CPU)
1. Disable some indicators
2. Use `majority` strategy (faster)
3. Reduce indicator parameters (e.g., shorter periods)

---

## 🚀 Quick Commands

### Edit Config
```bash
nano trading_system/config/indicators_config.yaml
```

### Restart Bot
```bash
./start_trading_bot.sh
```

### View Current Config
```bash
cat trading_system/config/indicators_config.yaml
```

---

## 💡 Tips

1. **Start Conservative**: Better safe than sorry
2. **Test Changes**: Try in paper trading first
3. **Track Performance**: Note which configs work best
4. **Market Dependent**: Different markets need different configs
5. **Review Regularly**: What works today may not work tomorrow

---

## ⚠️ Common Mistakes

❌ **Setting min_indicators higher than enabled indicators**
```yaml
threshold:
  min_indicators_buy: 4  # But only 3 indicators enabled!
```
**Result:** Never triggers BUY

---

❌ **Using weights with wrong strategy**
```yaml
aggregation:
  strategy: "majority"  # Doesn't use weights

indicators:
  rsi:
    weight: 2.0  # ❌ Ignored!
```
**Fix:** Use `strategy: "weighted"` to use weights

---

❌ **Disabling all indicators**
```yaml
indicators:
  rsi: {enabled: false}
  ma_crossover: {enabled: false}
  macd: {enabled: false}
  bollinger_bands: {enabled: false}
```
**Result:** Bot won't work!

---

## 📈 Recommended Settings by Market

### Volatile Market (High Movement)
```yaml
strategy: "threshold"
min_indicators_buy: 2
min_agreement_percent: 60
```

### Trending Market (Clear Direction)
```yaml
strategy: "weighted"
# Give MA higher weight (trend following)
ma_crossover: {weight: 2.0}
```

### Sideways Market (Range-Bound)
```yaml
strategy: "conservative"
min_agreement: 0.75
# Trust RSI and Bollinger (oscillators)
```

### Uncertain Market
```yaml
strategy: "unanimous"
# Only trade on 100% agreement
```

---

## ✅ Apply Changes

After editing config:
1. Save file
2. Restart bot: `./start_trading_bot.sh`
3. Watch indicator loading messages
4. Verify correct indicators are active

---

**That's it! Simple YAML config, powerful control.** 🎉

