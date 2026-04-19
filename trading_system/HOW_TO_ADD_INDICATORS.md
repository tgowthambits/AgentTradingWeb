# 📘 Complete Guide: Adding Custom Indicators

This guide shows you **exactly** how to add your own custom indicators to the trading system.

---

## 🎯 Overview

Adding a new indicator requires **3 simple steps**:

1. **Create** indicator class
2. **Configure** parameters  
3. **Register** in main script

**That's it!** The system automatically integrates your indicator.

---

## 📝 Step-by-Step Guide

### Step 1: Create Indicator Class

Create a new file: `trading_system/indicators/your_indicator_name.py`

```python
"""
Your Indicator Name

Brief description of what your indicator does.
"""

import pandas as pd
import numpy as np
from trading_system.core.base_indicator import BaseIndicator


class YourIndicatorName(BaseIndicator):
    """
    Detailed description of your indicator.
    
    Signals:
    - BUY: When [condition]
    - SELL: When [condition]
    - HOLD: When [condition]
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize your indicator.
        
        Config parameters:
            param1 (type): Description (default: value)
            param2 (type): Description (default: value)
            enabled (bool): Whether indicator is enabled (default: True)
            weight (float): Indicator weight for voting (default: 1.0)
        """
        super().__init__(name="Your_Indicator_Name", config=config)
        
        # Extract parameters from config
        self.param1 = self.config.get('param1', default_value)
        self.param2 = self.config.get('param2', default_value)
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate your indicator and generate signals.
        
        Args:
            df: DataFrame with OHLCV data
        
        Returns:
            DataFrame with 'signal' column ('BUY', 'SELL', 'HOLD')
        """
        # Step 1: Calculate your indicator values
        df['your_indicator'] = ...  # Your calculation here
        
        # Step 2: Generate signals based on your logic
        df['signal'] = 'HOLD'  # Default signal
        
        # BUY conditions
        df.loc[YOUR_BUY_CONDITION, 'signal'] = 'BUY'
        
        # SELL conditions
        df.loc[YOUR_SELL_CONDITION, 'signal'] = 'SELL'
        
        return df
    
    def get_required_columns(self) -> list:
        """
        List of required columns in input DataFrame.
        """
        return ['close']  # List all required columns
```

---

## 💡 Example 1: Volume Spike Indicator

```python
"""
Volume Spike Indicator

Generates signals based on unusual volume spikes.
"""

import pandas as pd
from trading_system.core.base_indicator import BaseIndicator


class VolumeSpikeIndicator(BaseIndicator):
    """
    Volume Spike Indicator
    
    Signals:
    - BUY: Volume > threshold * average volume (bullish interest)
    - SELL: Never generates SELL (volume alone isn't bearish)
    - HOLD: Normal volume
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize Volume Spike indicator.
        
        Config parameters:
            lookback (int): Periods for average volume (default: 20)
            threshold (float): Spike threshold multiplier (default: 2.0)
            enabled (bool): Whether indicator is enabled (default: True)
            weight (float): Indicator weight (default: 0.8)
        """
        super().__init__(name="Volume_Spike", config=config)
        
        self.lookback = self.config.get('lookback', 20)
        self.threshold = self.config.get('threshold', 2.0)
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate volume spike and generate signals."""
        
        # Calculate average volume
        df['avg_volume'] = df['volume'].rolling(window=self.lookback).mean()
        
        # Calculate volume ratio
        df['volume_ratio'] = df['volume'] / df['avg_volume']
        
        # Generate signals
        df['signal'] = 'HOLD'
        
        # BUY: High volume spike indicates buying interest
        df.loc[df['volume_ratio'] > self.threshold, 'signal'] = 'BUY'
        
        return df
    
    def get_required_columns(self) -> list:
        return ['volume']
```

**Configuration:**

```yaml
indicators:
  volume_spike:
    enabled: true
    weight: 0.8
    lookback: 20
    threshold: 2.0
```

---

## 💡 Example 2: Support/Resistance Indicator

```python
"""
Support/Resistance Indicator

Generates signals based on price levels.
"""

import pandas as pd
import numpy as np
from trading_system.core.base_indicator import BaseIndicator


class SupportResistanceIndicator(BaseIndicator):
    """
    Support/Resistance Indicator
    
    Signals:
    - BUY: Price near support level (bounce opportunity)
    - SELL: Price near resistance level (rejection opportunity)
    - HOLD: Price between levels
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize S/R indicator.
        
        Config parameters:
            lookback (int): Periods to find levels (default: 50)
            tolerance (float): Distance tolerance % (default: 0.02 = 2%)
            enabled (bool): Whether indicator is enabled (default: True)
            weight (float): Indicator weight (default: 1.2)
        """
        super().__init__(name="Support_Resistance", config=config)
        
        self.lookback = self.config.get('lookback', 50)
        self.tolerance = self.config.get('tolerance', 0.02)
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate S/R levels and generate signals."""
        
        # Find recent support (lowest low)
        df['support'] = df['low'].rolling(window=self.lookback).min()
        
        # Find recent resistance (highest high)
        df['resistance'] = df['high'].rolling(window=self.lookback).max()
        
        # Calculate distance from levels
        df['dist_to_support'] = (df['close'] - df['support']) / df['support']
        df['dist_to_resistance'] = (df['resistance'] - df['close']) / df['close']
        
        # Generate signals
        df['signal'] = 'HOLD'
        
        # BUY: Price near support (within tolerance)
        df.loc[df['dist_to_support'] <= self.tolerance, 'signal'] = 'BUY'
        
        # SELL: Price near resistance (within tolerance)
        df.loc[df['dist_to_resistance'] <= self.tolerance, 'signal'] = 'SELL'
        
        return df
    
    def get_required_columns(self) -> list:
        return ['high', 'low', 'close']
```

---

## 💡 Example 3: Price Pattern Indicator

```python
"""
Price Pattern Indicator

Detects candlestick patterns.
"""

import pandas as pd
from trading_system.core.base_indicator import BaseIndicator


class PricePatternIndicator(BaseIndicator):
    """
    Price Pattern Indicator
    
    Signals:
    - BUY: Bullish patterns (hammer, morning star, etc.)
    - SELL: Bearish patterns (shooting star, evening star, etc.)
    - HOLD: No clear pattern
    """
    
    def __init__(self, config: dict = None):
        super().__init__(name="Price_Pattern", config=config)
        
        self.min_body_ratio = self.config.get('min_body_ratio', 0.3)
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect patterns and generate signals."""
        
        # Calculate candle properties
        df['body'] = abs(df['close'] - df['open'])
        df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
        df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
        df['range'] = df['high'] - df['low']
        
        # Avoid division by zero
        df['range'] = df['range'].replace(0, 0.0001)
        
        # Calculate ratios
        df['body_ratio'] = df['body'] / df['range']
        df['upper_wick_ratio'] = df['upper_wick'] / df['range']
        df['lower_wick_ratio'] = df['lower_wick'] / df['range']
        
        # Detect patterns
        df['signal'] = 'HOLD'
        
        # Hammer pattern (BUY): Small body, long lower wick, small upper wick
        hammer = (
            (df['lower_wick_ratio'] > 0.5) & 
            (df['upper_wick_ratio'] < 0.1) & 
            (df['body_ratio'] < 0.3)
        )
        df.loc[hammer, 'signal'] = 'BUY'
        
        # Shooting Star pattern (SELL): Small body, long upper wick, small lower wick
        shooting_star = (
            (df['upper_wick_ratio'] > 0.5) & 
            (df['lower_wick_ratio'] < 0.1) & 
            (df['body_ratio'] < 0.3)
        )
        df.loc[shooting_star, 'signal'] = 'SELL'
        
        return df
    
    def get_required_columns(self) -> list:
        return ['open', 'high', 'low', 'close']
```

---

## 📋 Template Checklist

When creating a new indicator, make sure you:

- [ ] Inherit from `BaseIndicator`
- [ ] Call `super().__init__(name, config)`
- [ ] Implement `calculate()` method
- [ ] Implement `get_required_columns()` method
- [ ] Return DataFrame with 'signal' column
- [ ] Use 'BUY', 'SELL', 'HOLD' as signal values
- [ ] Extract parameters from `self.config`
- [ ] Add docstrings explaining your logic
- [ ] Handle edge cases (NaN, zero division, etc.)

---

## ⚙️ Step 2: Configure Your Indicator

Add to `trading_system/config/trading_config.yaml`:

```yaml
indicators:
  your_indicator_name:
    enabled: true
    weight: 1.0
    param1: value1
    param2: value2
```

---

## 🔧 Step 3: Register Your Indicator

Edit `trading_system/run_trading_system.py`:

```python
# Add import at top
from trading_system.indicators.your_indicator import YourIndicatorName

def initialize_indicators(config):
    indicators = []
    
    # ... existing indicators ...
    
    # Add your indicator
    if config['indicators']['your_indicator_name']['enabled']:
        indicators.append(
            YourIndicatorName(config['indicators']['your_indicator_name'])
        )
    
    return indicators
```

---

## 🚀 Step 4: Run and Test

```bash
python trading_system/run_trading_system.py
```

Your indicator will now:
- ✅ Load automatically
- ✅ Calculate signals
- ✅ Participate in voting
- ✅ Appear in output tables

---

## 💡 Tips & Best Practices

### 1. Signal Logic
- **Be specific**: Clear conditions for BUY/SELL
- **Be conservative**: When in doubt, return HOLD
- **Be consistent**: Same logic throughout

### 2. Parameter Defaults
- Choose sensible defaults
- Document each parameter
- Test with different values

### 3. Error Handling
```python
def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
    # Handle missing data
    if 'close' not in df.columns:
        raise ValueError("Missing 'close' column")
    
    # Handle insufficient data
    if len(df) < self.period:
        df['signal'] = 'HOLD'
        return df
    
    # Your calculation...
```

### 4. Performance
- Vectorize operations (use pandas, not loops)
- Avoid redundant calculations
- Use `.rolling()` for moving calculations

### 5. Testing
```python
# Quick test in Python
from your_indicator import YourIndicator
import pandas as pd

# Create test data
df = pd.DataFrame({
    'close': [100, 102, 101, 103, 105],
    'volume': [1000, 1200, 900, 1500, 1100]
})

# Test indicator
indicator = YourIndicator()
result = indicator.calculate(df)
print(result[['close', 'signal']])
```

---

## 🎓 Advanced: Complex Indicators

### Combining Multiple Conditions

```python
def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
    # Calculate multiple indicators
    df['ma_20'] = df['close'].rolling(20).mean()
    df['rsi'] = self._calculate_rsi(df)
    df['volume_avg'] = df['volume'].rolling(20).mean()
    
    # Combine conditions for strong signals
    strong_buy = (
        (df['close'] > df['ma_20']) &  # Above MA
        (df['rsi'] < 40) &              # Oversold RSI
        (df['volume'] > df['volume_avg'] * 1.5)  # High volume
    )
    
    strong_sell = (
        (df['close'] < df['ma_20']) &  # Below MA
        (df['rsi'] > 60) &              # Overbought RSI
        (df['volume'] > df['volume_avg'] * 1.5)  # High volume
    )
    
    df['signal'] = 'HOLD'
    df.loc[strong_buy, 'signal'] = 'BUY'
    df.loc[strong_sell, 'signal'] = 'SELL'
    
    return df
```

### Using Helper Methods

```python
class MyIndicator(BaseIndicator):
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        # Use helper methods for clarity
        df = self._calculate_indicators(df)
        df = self._generate_signals(df)
        return df
    
    def _calculate_indicators(self, df):
        """Helper: Calculate all indicator values"""
        df['indicator1'] = ...
        df['indicator2'] = ...
        return df
    
    def _generate_signals(self, df):
        """Helper: Generate signals from indicators"""
        df['signal'] = 'HOLD'
        # Signal logic...
        return df
```

---

## 🔍 Debugging Tips

### Print Indicator Values

```python
def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
    df['my_indicator'] = ...
    
    # Debug: Print latest values
    print(f"Latest indicator value: {df['my_indicator'].iloc[-1]}")
    print(f"Signal: {df['signal'].iloc[-1]}")
    
    return df
```

### Visualize Signals

```python
# After running system, visualize your indicator
import matplotlib.pyplot as plt

result_df = engine.indicator_manager.results['Your_Indicator_Name']

plt.figure(figsize=(12, 6))
plt.plot(result_df['close'], label='Price')
plt.scatter(result_df[result_df['signal'] == 'BUY'].index, 
           result_df[result_df['signal'] == 'BUY']['close'], 
           color='green', marker='^', label='BUY')
plt.scatter(result_df[result_df['signal'] == 'SELL'].index, 
           result_df[result_df['signal'] == 'SELL']['close'], 
           color='red', marker='v', label='SELL')
plt.legend()
plt.show()
```

---

## 📚 More Examples

Check the `indicators/` folder for more examples:
- `rsi_indicator.py` - Simple single-value indicator
- `ma_crossover_indicator.py` - Crossover strategy
- `macd_indicator.py` - Multi-component indicator
- `bollinger_indicator.py` - Band-based indicator

---

## 🎯 Summary

**Adding an indicator is as simple as:**

1. Create class in `indicators/`
2. Add config in `trading_config.yaml`
3. Register in `run_trading_system.py`
4. Run!

**That's the power of plug-and-play architecture!** 🚀

---

**Now go create amazing indicators!** 💡📈

