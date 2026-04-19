# Buy Signal Generation Flow

## Signal Generation Pipeline

The **BUY signal (1)** is generated through a multi-stage pipeline:

### Stage 1: Individual Model Signals

#### 1. **Daily VOMC Signal** (`models/vomc_daily.py`)
- **Module**: `pipeline/run_daily_models.py` → `VOMCDaily.predict()`
- **Logic**: 
  - Analyzes historical price patterns (Up/Down states)
  - Calculates probability of next day being "Up"
  - **Signal**: `1` if `prob >= 0.5`, else `-1`
- **Location**: ```26:26:pipeline/run_daily_models.py
vomc_signal = 1 if vomc_prob >= 0.5 else -1
```

#### 2. **Intraday VOMC Signal** (`models/vomc_intraday.py`)
- **Module**: `pipeline/run_intraday_models.py` → `VOMCIntraday.predict()`
- **Logic**:
  - Analyzes intraday price patterns
  - Predicts next state (Up=1, Down=0)
  - **Signal**: `1` if `p_up >= 0.5`, else `0`
- **Location**: ```24:24:pipeline/run_intraday_models.py
vomc_micro_signal = vomc.predict(history)
```

#### 3. **RL Agent Action** (`models/rl_agent.py`)
- **Module**: `pipeline/run_intraday_models.py` → `RLAgent.predict()`
- **Logic**:
  - Uses trained PPO model (or default hold if no model)
  - **Action**: `0`=buy, `1`=sell, `2`=hold
  - **Mapped to signal**: `0→1`, `1→-1`, `2→0`
- **Location**: ```31:31:pipeline/run_intraday_models.py
rl_action = agent.predict(obs)
```

### Stage 2: Signal Fusion

#### 4. **Fuse Signals** (`pipeline/live_inference.py`)
- **Module**: `pipeline/live_inference.py` → `fuse_signals()`
- **Logic**: Majority voting
  - Combines: `daily_sig`, `intra_sig`, `rl_mapped`
  - **BUY (1)** if `vote_sum >= 2`
  - **SELL (-1)** if `vote_sum <= -2`
  - **HOLD (0)** otherwise
- **Location**: ```27:61:pipeline/live_inference.py
def fuse_signals(daily, intraday, rl, strict=False):
    rl_mapped = {0: 1, 1: -1, 2: 0}.get(rl, 0)
    votes = [daily, intraday, rl_mapped]
    vote_sum = sum(votes)
    if vote_sum >= 2:
        return 1      # BUY
    elif vote_sum <= -2:
        return -1     # SELL
    return 0           # HOLD
```

### Stage 3: Precision Filters

#### 5. **Apply Filters** (`utils/filters.py`)
- **Module**: `pipeline/live_inference.py` → `apply_all_filters()`
- **Filters Applied**:
  - **Volatility Filter**: Only trade if volatility > threshold
  - **Trend Confirmation**: MA50 > MA200 (bullish)
  - **Breakout Detection**: HH/HL patterns (bullish)
  - **Momentum Filter**: RSI > 55 (buy momentum)
  - **Confidence Threshold**: Daily prob > 0.6
- **Location**: ```90:95:pipeline/live_inference.py
filter_results = apply_all_filters(
    df=daily_df,
    signal=raw_signal,
    daily_prob=daily_prob,
    config=filter_config
)
```

### Stage 4: Final Signal

#### 6. **Final Signal** (`pipeline/live_inference.py`)
- **Module**: `pipeline/live_inference.py`
- **Logic**: 
  - Raw signal from fusion is filtered
  - Signal is only valid if:
    1. Volatility filter passes
    2. Confidence threshold met
    3. At least one confirmation (trend/breakout/momentum)
- **Location**: ```98:98:pipeline/live_inference.py
final_sig = filter_results["filtered_signal"]
```

## Summary

**BUY Signal (1) is generated when:**

1. **Raw Signal = 1** (from majority voting of 3 models)
2. **Volatility filter passes** (volatility > threshold)
3. **Confidence filter passes** (daily_prob > 0.6)
4. **At least 1 confirmation** from:
   - Trend confirmation (MA50 > MA200)
   - Breakout detection (HH/HL pattern)
   - Momentum filter (RSI > 55)

## Code Flow

```
live_inference()
  ├─> run_daily_models()
  │   └─> VOMCDaily.predict() → daily_sig (1 or -1)
  │
  ├─> run_intraday()
  │   ├─> VOMCIntraday.predict() → intra_sig (1 or 0)
  │   └─> RLAgent.predict() → rl_action (0, 1, or 2)
  │
  ├─> fuse_signals() → raw_signal (1, -1, or 0)
  │
  └─> apply_all_filters() → final_signal (1, -1, or 0)
```

## Key Modules

1. **`models/vomc_daily.py`** - Daily pattern-based prediction
2. **`models/vomc_intraday.py`** - Intraday pattern-based prediction  
3. **`models/rl_agent.py`** - Reinforcement learning agent
4. **`pipeline/live_inference.py`** - Main fusion and filtering logic
5. **`utils/filters.py`** - Precision filters for signal validation

