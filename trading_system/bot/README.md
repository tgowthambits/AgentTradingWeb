# Bot Module - Refactored Architecture

This directory contains the refactored modular components of the Live Trading Bot.

## Structure

### `display_manager.py`
**Purpose**: Handles all console output and Rich table/panel rendering.

**Key Features**:
- Console display management
- Table creation (comprehensive table, completed orders table)
- KPI panel generation
- Signal formatting and visualization

**Usage**:
```python
display_manager = DisplayManager(engine, config, console)
display_manager.display_results(results, refresh_count, auto_trade, ...)
```

### `trading_operations.py`
**Purpose**: Core trading logic and symbol analysis.

**Key Features**:
- `run_once()`: Execute one analysis cycle for symbols
- Trading decision execution
- Signal generation tracking
- Error handling for symbol analysis

**Usage**:
```python
trading_ops = TradingOperations(engine, data_loader, config, ...)
results = trading_ops.run_once(symbols)
```

### `backtest_manager.py`
**Purpose**: Backtest-specific functionality.

**Key Features**:
- Backtest display building
- Progress tracking
- Backtest results JSON export
- Symbol position tracking during backtest

**Usage**:
```python
backtest_mgr = BacktestManager(engine, data_loader, config, display_manager, ...)
display_content = backtest_mgr.build_backtest_display(results, iteration)
```

### `config_manager.py`
**Purpose**: Configuration loading and management.

**Key Features**:
- YAML configuration loading
- Configuration value access with dot notation
- Configuration reloading

**Usage**:
```python
config_mgr = ConfigManager(config_path)
value = config_mgr.get('trading.refresh_interval')
```

### `utils.py`
**Purpose**: Utility classes and functions.

**Key Features**:
- `NumpyJSONEncoder`: Custom JSON encoder for NumPy types (NumPy 2.0 compatible)

## Benefits of Refactoring

1. **Separation of Concerns**: Each module has a single, well-defined responsibility
2. **Maintainability**: Easier to locate and fix bugs
3. **Testability**: Each module can be tested independently
4. **Reusability**: Modules can be reused in other parts of the system
5. **Readability**: Smaller, focused files are easier to understand

## Migration Notes

The refactored `LiveTradingBot` class maintains the same public interface, so existing code using it should continue to work without changes. The internal implementation now delegates to the modular components.

## Original File Backup

The original `run_live_bot.py` has been backed up as `run_live_bot_original_backup.py` in case you need to reference the original implementation.
