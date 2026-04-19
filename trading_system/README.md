# 🚀 Plugin-Based Trading System

A clean, modular, and extensible trading system with **plug-and-play** indicator architecture.

## ✨ Key Features

- **🔌 Plug-and-Play Indicators** - Add new indicators without touching core code
- **📊 Multiple Aggregation Strategies** - Majority, Weighted, Unanimous, Conservative
- **🎯 Simple Class-Based Architecture** - Easy to understand and extend
- **📈 Real-Time Analysis** - Analyze multiple symbols simultaneously
- **💰 Order Management** - Track open positions and P&L
- **⚙️ YAML Configuration** - Easy configuration without code changes

---

## 📁 Project Structure

```
trading_system/
├── core/
│   ├── base_indicator.py       # Abstract base class for all indicators
│   ├── indicator_manager.py    # Manages and executes indicators
│   ├── signal_aggregator.py    # Combines signals from multiple indicators
│   └── trading_engine.py       # Main trading engine
├── indicators/
│   ├── rsi_indicator.py        # RSI indicator
│   ├── ma_crossover_indicator.py  # Moving Average crossover
│   ├── macd_indicator.py       # MACD indicator
│   ├── bollinger_indicator.py  # Bollinger Bands
│   └── [your_custom_indicator.py]  # ← Add your indicators here!
├── data/
│   └── data_loader.py          # Data loading and preprocessing
├── config/
│   └── trading_config.yaml     # Configuration file
├── run_trading_system.py       # Main script to run
└── README.md                   # This file
```

---

## 🚀 Quick Start

### Option 1: One-Time Analysis

```bash
cd /home/sham/Desktop/MARKOV_MARKET
python trading_system/run_trading_system.py
```

Analyzes symbols once and displays results.

### Option 2: Live Trading Bot 🤖

```bash
cd /home/sham/Desktop/MARKOV_MARKET
./start_trading_bot.sh
```

Runs continuously, checking every 5 seconds for real-time trading!

**See [LIVE_BOT_GUIDE.md](LIVE_BOT_GUIDE.md) for details.**

---

### Configure Symbols and Parameters

Edit `trading_system/config/trading_config.yaml`:

```yaml
symbols:
  - "BSE:SENSEX2610185100PE"
  - "NSE:NIFTY25DEC26050PE"

indicators:
  rsi:
    enabled: true
    weight: 1.0
    period: 14
```

### 3. View Results

The system will:
- Load data for all symbols
- Run all enabled indicators
- Aggregate signals
- Display results in a beautiful table

---

## 🎯 How It Works

### 1. Data Flow

```
Data Loader
    ↓
[Symbol OHLCV Data]
    ↓
Indicator Manager → Executes All Indicators
    ↓
[Individual Signals: BUY/SELL/HOLD]
    ↓
Signal Aggregator → Combines Signals
    ↓
[Final Signal]
    ↓
Trading Engine → Execute Orders
```

### 2. Signal Generation

Each indicator returns a DataFrame with a `signal` column:
- **BUY** - Bullish signal
- **SELL** - Bearish signal  
- **HOLD** - Neutral signal

### 3. Signal Aggregation

Multiple strategies available:
- **Majority** - Most common signal wins
- **Weighted** - Weighted by indicator importance
- **Unanimous** - All indicators must agree
- **Conservative** - Requires strong consensus

---

## 🔌 Adding Custom Indicators

### Step 1: Create Your Indicator Class

Create a new file in `trading_system/indicators/`:

```python
# my_custom_indicator.py

from trading_system.core.base_indicator import BaseIndicator
import pandas as pd

class MyCustomIndicator(BaseIndicator):
    """
    Your custom indicator description.
    """
    
    def __init__(self, config: dict = None):
        super().__init__(name="My_Custom_Indicator", config=config)
        
        # Your parameters
        self.threshold = self.config.get('threshold', 0.5)
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate your indicator and generate signals.
        """
        # 1. Calculate your indicator
        df['my_indicator'] = ... # Your calculation
        
        # 2. Generate signals
        df['signal'] = 'HOLD'  # Default
        df.loc[df['my_indicator'] > self.threshold, 'signal'] = 'BUY'
        df.loc[df['my_indicator'] < -self.threshold, 'signal'] = 'SELL'
        
        return df
    
    def get_required_columns(self) -> list:
        """Required columns in input DataFrame."""
        return ['close']  # List required columns
```

### Step 2: Add to Configuration

Edit `trading_system/config/trading_config.yaml`:

```yaml
indicators:
  my_custom_indicator:
    enabled: true
    weight: 1.0
    threshold: 0.5
```

### Step 3: Register in Main Script

Edit `trading_system/run_trading_system.py`:

```python
from trading_system.indicators.my_custom_indicator import MyCustomIndicator

def initialize_indicators(config):
    indicators = []
    
    # ... existing indicators ...
    
    # Add your indicator
    if config['indicators']['my_custom_indicator']['enabled']:
        indicators.append(MyCustomIndicator(config['indicators']['my_custom_indicator']))
    
    return indicators
```

### Step 4: Run!

```bash
python trading_system/run_trading_system.py
```

**That's it!** Your indicator is now part of the system!

---

## 📊 Available Indicators

### 1. RSI (Relative Strength Index)
- **BUY**: RSI < 30 (oversold)
- **SELL**: RSI > 70 (overbought)
- **Parameters**: `period`, `oversold`, `overbought`

### 2. Moving Average Crossover
- **BUY**: Fast MA > Slow MA (bullish trend)
- **SELL**: Fast MA < Slow MA (bearish trend)
- **Parameters**: `fast_period`, `slow_period`, `ma_type`

### 3. MACD
- **BUY**: MACD > Signal Line (bullish momentum)
- **SELL**: MACD < Signal Line (bearish momentum)
- **Parameters**: `fast_period`, `slow_period`, `signal_period`

### 4. Bollinger Bands
- **BUY**: Price ≤ Lower Band (oversold)
- **SELL**: Price ≥ Upper Band (overbought)
- **Parameters**: `period`, `std_dev`

---

## ⚙️ Configuration Guide

### Aggregation Strategies

```yaml
# Simple majority voting
aggregation_strategy: "majority"

# Weighted voting (uses indicator weights)
aggregation_strategy: "weighted"

# All indicators must agree
aggregation_strategy: "unanimous"

# Requires strong consensus (min_agreement)
aggregation_strategy: "conservative"
min_agreement: 0.6  # 60% agreement required
```

### Indicator Weights

Higher weight = more important in decision:

```yaml
indicators:
  rsi:
    weight: 1.0  # Standard importance
  
  ma_crossover:
    weight: 1.5  # Higher importance
  
  bollinger_bands:
    weight: 0.8  # Lower importance
```

---

## 📈 Example Output

```
╭────────────────────────────────────────────────────────────────╮
│           Multi-Symbol Trading Analysis                         │
├──────────────────┬──────────┬──────────────┬───────────┬──────┤
│ Symbol           │ Price(₹) │ Final Signal │ Agreement │ B/S/H│
├──────────────────┼──────────┼──────────────┼───────────┼──────┤
│ SENSEX...100PE   │ 330.95   │ BUY          │ 75%       │ 3/0/1│
│ SENSEX...100CE   │ 209.05   │ HOLD         │ 50%       │ 2/0/2│
│ NIFTY...050PE    │ 69.60    │ BUY          │ 100%      │ 4/0/0│
│ NIFTY...050CE    │ 35.80    │ SELL         │ 75%       │ 0/3/1│
╰──────────────────┴──────────┴──────────────┴───────────┴──────╯

Indicator Details: SENSEX2610185100PE
┌─────────────────────────┬────────┐
│ Indicator               │ Signal │
├─────────────────────────┼────────┤
│ RSI                     │ BUY    │
│ MA_Crossover            │ BUY    │
│ MACD                    │ BUY    │
│ Bollinger_Bands         │ HOLD   │
└─────────────────────────┴────────┘
```

---

## 🎓 Code Architecture

### BaseIndicator (Abstract Class)

All indicators inherit from this:

```python
class MyIndicator(BaseIndicator):
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        # Must return DataFrame with 'signal' column
        pass
    
    def get_required_columns(self) -> list:
        # List required columns
        pass
```

### IndicatorManager

Manages all indicators:

```python
manager = IndicatorManager()
manager.register_indicator(MyIndicator())
signals = manager.execute_all(df)  # Returns dict of signals
```

### SignalAggregator

Combines signals:

```python
aggregator = SignalAggregator(strategy='weighted')
final_signal = aggregator.aggregate(signals, weights)
```

### TradingEngine

Coordinates everything:

```python
engine = TradingEngine()
engine.register_indicators([RSIIndicator(), MACDIndicator()])
result = engine.analyze_symbol(df, 'SYMBOL')
engine.execute_trading_decision(result)
```

---

## 💡 Best Practices

### 1. Indicator Design
- Keep indicators simple and focused
- Return clean DataFrames with 'signal' column
- Use configuration for parameters
- Validate input data

### 2. Signal Generation
- **BUY** for bullish conditions
- **SELL** for bearish conditions
- **HOLD** when uncertain
- Be conservative with signals

### 3. Weights
- Important indicators: 1.5 - 2.0
- Standard indicators: 1.0
- Experimental indicators: 0.5 - 0.8

### 4. Testing
- Test with historical data
- Verify signals make sense
- Check edge cases
- Monitor performance

---

## 🔧 Troubleshooting

### Issue: Indicator not executing
- Check `enabled: true` in config
- Verify indicator is registered in `initialize_indicators()`
- Check for import errors

### Issue: Wrong signals
- Verify indicator logic in `calculate()`
- Check threshold values
- Print intermediate values for debugging

### Issue: Data errors
- Ensure required columns exist
- Check data quality (NaN values)
- Verify data format (OHLCV)

---

## 📚 API Reference

### BaseIndicator

```python
class BaseIndicator(ABC):
    def __init__(self, name: str, config: dict)
    @abstractmethod
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame
    @abstractmethod
    def get_required_columns(self) -> list
    def validate_data(self, df: pd.DataFrame) -> bool
    def get_latest_signal(self, df: pd.DataFrame) -> str
```

### TradingEngine

```python
class TradingEngine:
    def __init__(self, aggregation_strategy: str)
    def register_indicators(self, indicators: list)
    def analyze_symbol(self, df: pd.DataFrame, symbol: str) -> dict
    def execute_trading_decision(self, analysis: dict) -> dict
    def get_open_positions() -> pd.DataFrame
    def get_closed_orders() -> pd.DataFrame
    def get_total_pnl() -> float
```

---

## 🎯 Next Steps

1. ✅ Run the system with default indicators
2. ✅ Adjust parameters in `trading_config.yaml`
3. ✅ Add your custom indicators
4. ✅ Backtest with historical data
5. ✅ Deploy for live monitoring

---

## 📝 License

This is a custom trading system. Use at your own risk.

---

## 🤝 Contributing

To add a new indicator:
1. Create indicator class in `indicators/`
2. Add configuration to `trading_config.yaml`
3. Register in `run_trading_system.py`
4. Test and enjoy!

---

**Happy Trading!** 🚀📈💰

