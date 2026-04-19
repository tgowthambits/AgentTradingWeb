# Volume Profile - Density of Density [DAFE] Indicator

## Overview

The Volume Profile indicator has been successfully integrated into the trading system. This advanced indicator provides institutional-level analysis including:

- **Volume Profile** with POC (Point of Control) and Value Area
- **Delta Analysis** (buying vs selling pressure using microstructure hybrid method)
- **HVN/LVN Detection** (High/Low Volume Nodes)
- **Market Regime Classification** (Quiet, Trending, Ranging, Volatile)
- **Entropy Calculations** (market disorder/coiling detection)
- **Bayesian Confidence Scores** (probabilistic directional bias)
- **Multiple Trading Signals** (POC cross, VA breakout, delta extremes, absorption/distribution, coiling)

## Features

### Core Components

1. **Volume Profile Building**
   - Divides price range into configurable rows
   - Distributes volume across price levels
   - Calculates POC (highest volume price level)
   - Calculates Value Area (price range containing specified % of volume)

2. **Delta Engine**
   - Microstructure Hybrid method (recommended)
   - Analyzes wicks, body, and close position
   - Splits volume into buy vs sell components
   - Detects absorption and distribution patterns

3. **Node Detection**
   - HVN (High Volume Nodes): Areas of acceptance/liquidity
   - LVN (Low Volume Nodes): Areas of rejection/fast moves

4. **Market Regime**
   - Quiet: Low volatility, low trend
   - Trending: Strong trend, moderate volatility
   - Ranging: Low trend, moderate volatility
   - Volatile: High volatility

5. **Signal Generation**
   - POC Cross: Price crossing Point of Control
   - VA Breakout: Price breaking out of Value Area
   - Delta Extreme: Extreme buying/selling pressure
   - Absorption/Distribution: High volume with low price movement
   - Coiling: Contracting Value Area (breakout setup)

## Configuration

The indicator is configured in `trading_system/config/indicators_config.yaml`:

```yaml
volume_profile:
  enabled: true
  module: trading_system.indicators.volume_profile_indicator
  class_name: VolumeProfileIndicator
  weight: 2.0
  params:
    profile_length: 100        # Lookback period for profile
    num_rows: 70               # Number of price rows
    value_area_pct: 70.0       # Value area percentage
    delta_method: microstructure_hybrid  # Delta calculation method
    hvn_threshold: 1.3         # HVN threshold (standard deviations)
    lvn_threshold: 0.4         # LVN threshold (standard deviations)
    use_htf: false            # Use higher timeframe data
    htf_resolution: '240'      # Higher timeframe resolution
    volume_filter: 3.0         # Min volume filter %
    price_buffer: 2.0          # Price buffer %
    poc_cross_signal: true     # Enable POC cross signals
    va_breakout_signal: true   # Enable VA breakout signals
    delta_extreme_signal: true # Enable delta extreme signals
    absorption_signal: true    # Enable absorption/distribution signals
    coiling_signal: true       # Enable coiling setup signals
```

## Usage

### In Backtesting

The indicator automatically participates in backtesting when enabled. It will:
- Calculate volume profile for each bar
- Generate signals based on configured conditions
- Contribute to the final signal aggregation (weight: 2.0)

### In Live Trading

The indicator runs in real-time and:
- Updates volume profile as new bars arrive
- Generates signals based on current market conditions
- Provides metrics for decision making

## Output Columns

The indicator adds the following columns to the DataFrame:

- `vp_poc`: Point of Control price
- `vp_va_high`: Value Area high price
- `vp_va_low`: Value Area low price
- `vp_delta_imbalance`: Delta imbalance percentage
- `vp_entropy`: Normalized entropy (0-100)
- `vp_regime`: Market regime name
- `vp_bullish_conf`: Bayesian bullish confidence (0-100)
- `vp_bearish_conf`: Bayesian bearish confidence (0-100)
- `signal`: Trading signal (BUY/SELL/HOLD)

## Signal Logic

### BUY Signals

1. **POC Cross Up**: Price crosses above POC with volume confirmation
2. **VA Breakout Up**: Price breaks above Value Area high
3. **Delta Extreme Bull**: Extreme buying pressure (>15%) with price above POC and VA
4. **Absorption**: High volume (>2x avg) with low price movement and positive delta
5. **Coiling Bull**: Contracting VA with bullish confidence >60%
6. **Bayesian High Confidence**: Bullish confidence >70% with price above POC

### SELL Signals

1. **POC Cross Down**: Price crosses below POC with volume confirmation
2. **VA Breakout Down**: Price breaks below Value Area low
3. **Delta Extreme Bear**: Extreme selling pressure (<-15%) with price below POC and VA
4. **Distribution**: High volume (>2x avg) with low price movement and negative delta
5. **Coiling Bear**: Contracting VA with bearish confidence >60%
6. **Bayesian High Confidence**: Bearish confidence >70% with price below POC

## Performance Considerations

- The indicator requires at least `profile_length` bars to start generating signals
- Higher `num_rows` provides more precision but uses more memory
- `microstructure_hybrid` delta method is recommended for accuracy
- The indicator maintains history of up to 500 POC values for velocity calculations

## Integration Status

✅ Indicator class created  
✅ Configuration files updated  
✅ Auto-discovery compatible  
✅ Ready for backtesting  
✅ Ready for live trading  
✅ UI will display signals automatically  

## Notes

- The indicator uses a rolling window approach, recalculating the profile for each bar
- Volume profile metrics are stored in the DataFrame for analysis
- The indicator weight (2.0) gives it higher influence in signal aggregation
- All signals require volume confirmation (current volume > 1.2x average)

## Future Enhancements

Potential improvements:
- Higher timeframe composite profiles
- Visual volume profile rendering in charts
- Advanced node zone detection
- Real-time dashboard for VP metrics
- Alert system integration

