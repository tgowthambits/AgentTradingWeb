# RL Agent Buy/Sell/Hold Conditions

## Overview
The RL Agent uses a PPO (Proximal Policy Optimization) model to make trading decisions based on historical price patterns.

## Action Space
- **Action 0** = BUY
- **Action 1** = SELL  
- **Action 2** = HOLD

## Input/Observation
The RL agent receives:
- **Observation**: Array of up/down states from the last N periods (default: 10 periods)
  - States are binary: `1` = price went up, `0` = price went down
  - Example: `[1, 0, 1, 1, 0, 1, 1, 1, 0, 1]` (last 10 periods)
- **Window size**: Configurable in `configs/params.yaml` under `rl.window` (default: 10)

## Decision Making Process

### 1. Model Prediction
```python
obs = states[-window:]  # Last N periods of up/down states
action = model.predict(obs, deterministic=True)
```

The trained PPO model analyzes the pattern of recent up/down states and predicts the best action based on:
- **Learned patterns**: The model was trained to maximize profit by recognizing patterns that lead to profitable trades
- **Historical performance**: The model learned which state sequences typically lead to price increases (BUY) or decreases (SELL)

### 2. Position-Aware Logic
After the model prediction, position-aware constraints are applied:

#### BUY (Action 0) Conditions:
- ✅ Model predicts BUY (action 0)
- ✅ **AND** `has_position == False` (no existing position)
- ❌ If `has_position == True` → Converted to HOLD (can't buy when already in position)

#### SELL (Action 1) Conditions:
- ✅ Model predicts SELL (action 1)
- ✅ **AND** `has_position == True` (must have a position to sell)
- ❌ If `has_position == False` → Converted to HOLD (can't sell without position)

#### HOLD (Action 2) Conditions:
- ✅ Model predicts HOLD (action 2)
- ✅ **OR** Model predicts BUY but `has_position == True`
- ✅ **OR** Model predicts SELL but `has_position == False`
- ✅ **OR** No model loaded (default fallback)

## Training Conditions (How Model Learns)

The model learns optimal actions by:
1. **Reward Signal**: PnL (Profit and Loss)
   ```python
   reward = (next_price - current_price) * position
   ```
   - Positive reward when price moves in favor of position
   - Negative reward when price moves against position

2. **Training Process**:
   - Model explores different actions in different state sequences
   - Learns which patterns lead to profitable trades
   - Optimizes policy to maximize cumulative reward

3. **State Patterns**:
   - Sequences like `[1,1,1,1,1]` (multiple ups) might signal continuation → BUY
   - Sequences like `[0,0,0,0,0]` (multiple downs) might signal continuation → SELL
   - Mixed patterns might signal reversal or uncertainty → HOLD

## Current Implementation

### When Model is Loaded:
```python
if model_path exists and loads successfully:
    obs = states[-window:]  # Last 10 periods
    action = model.predict(obs)
    
    # Apply position-aware constraints
    if not has_position and action == 1:  # SELL without position
        return 2  # HOLD
    elif has_position and action == 0:  # BUY with position
        return 2  # HOLD
    else:
        return action  # Return model's prediction
```

### When No Model is Loaded:
```python
if model_path is None or model doesn't exist:
    return 2  # Always HOLD (safe default)
```

## Example Scenarios

### Scenario 1: BUY Signal
- **Observation**: `[1, 1, 0, 1, 1, 1, 0, 1, 1, 1]` (mostly ups, recent uptrend)
- **Model Prediction**: Action 0 (BUY)
- **Position Status**: No position
- **Final Action**: **BUY (0)** ✅

### Scenario 2: BUY Blocked (Already in Position)
- **Observation**: `[1, 1, 0, 1, 1, 1, 0, 1, 1, 1]` (mostly ups)
- **Model Prediction**: Action 0 (BUY)
- **Position Status**: Has position
- **Final Action**: **HOLD (2)** (can't buy again)

### Scenario 3: SELL Signal
- **Observation**: `[0, 0, 1, 0, 0, 0, 1, 0, 0, 0]` (mostly downs, recent downtrend)
- **Model Prediction**: Action 1 (SELL)
- **Position Status**: Has position
- **Final Action**: **SELL (1)** ✅

### Scenario 4: SELL Blocked (No Position)
- **Observation**: `[0, 0, 1, 0, 0, 0, 1, 0, 0, 0]` (mostly downs)
- **Model Prediction**: Action 1 (SELL)
- **Position Status**: No position
- **Final Action**: **HOLD (2)** (can't sell without position)

### Scenario 5: HOLD Signal
- **Observation**: `[1, 0, 1, 0, 1, 0, 1, 0, 1, 0]` (mixed, choppy)
- **Model Prediction**: Action 2 (HOLD)
- **Position Status**: Any
- **Final Action**: **HOLD (2)** ✅

## Configuration

In `configs/params.yaml`:
```yaml
rl:
  window: 10  # Number of periods to look back for observation
  model_path: null  # Path to trained PPO model (if null, always returns HOLD)
```

## Summary Table

| Model Prediction | Position Status | Final Action | Reason |
|----------------|-----------------|--------------|--------|
| BUY (0) | No position | **BUY (0)** | ✅ Valid buy signal |
| BUY (0) | Has position | **HOLD (2)** | ❌ Already in position |
| SELL (1) | Has position | **SELL (1)** | ✅ Valid sell signal |
| SELL (1) | No position | **HOLD (2)** | ❌ Can't sell without position |
| HOLD (2) | Any | **HOLD (2)** | ✅ Valid hold signal |
| No model | Any | **HOLD (2)** | ✅ Safe default |

## Notes

1. **The actual decision logic is learned by the PPO model during training** - it's not hardcoded rules
2. **The model learns patterns** that historically led to profitable trades
3. **Position-aware logic** ensures we don't make invalid trades (buying when already long, selling when flat)
4. **Without a trained model**, the agent always returns HOLD as a safe default

