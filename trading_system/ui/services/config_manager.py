"""
Config Manager Module

Handles loading, saving, and managing configuration files.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """
    Manages trading configuration files.
    
    This class handles:
    - Loading configuration from YAML files
    - Saving configuration to YAML files
    - Configuration validation
    - Default value management
    
    Attributes:
        config_path: Path to the trading configuration file
        indicators_config_path: Path to the indicators configuration file
    """
    
    def __init__(
        self,
        config_path: Optional[Path] = None,
        indicators_config_path: Optional[Path] = None
    ):
        """
        Initialize the ConfigManager.
        
        Args:
            config_path: Path to trading config file
            indicators_config_path: Path to indicators config file
        """
        # Set default paths
        base_path = Path(__file__).parent.parent.parent / "config"
        
        self.config_path = config_path or base_path / "trading_config.yaml"
        self.indicators_config_path = indicators_config_path or base_path / "indicators_config.yaml"
        
        # Cache loaded config
        self._config = None
        self._indicators_config = None
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file.
        
        Returns:
            Configuration dictionary
        
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid YAML
        """
        try:
            with open(self.config_path, 'r') as f:
                self._config = yaml.safe_load(f) or {}
            return self._config
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML in config file: {e}")
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        Save configuration to YAML file.
        
        Args:
            config: Configuration dictionary to save
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            self._config = config
            return True
        except Exception as e:
            print(f"Failed to save config: {e}")
            return False
    
    def load_indicators_config(self) -> Dict[str, Any]:
        """
        Load indicators configuration.
        
        Returns:
            Indicators configuration dictionary
        """
        try:
            with open(self.indicators_config_path, 'r') as f:
                self._indicators_config = yaml.safe_load(f) or {}
            return self._indicators_config
        except FileNotFoundError:
            return {}
        except yaml.YAMLError:
            return {}
    
    def save_indicators_config(self, config: Dict[str, Any]) -> bool:
        """
        Save indicators configuration.
        
        Args:
            config: Indicators configuration dictionary
        
        Returns:
            True if successful
        """
        try:
            with open(self.indicators_config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            self._indicators_config = config
            return True
        except Exception as e:
            print(f"Failed to save indicators config: {e}")
            return False
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get current configuration (loads if not cached).
        
        Returns:
            Configuration dictionary
        """
        if self._config is None:
            self.load_config()
        return self._config or {}
    
    def get_nested_value(self, *keys, default=None) -> Any:
        """
        Get a nested configuration value.
        
        Args:
            *keys: Keys to traverse
            default: Default value if not found
        
        Returns:
            Configuration value or default
        
        Example:
            >>> manager.get_nested_value('risk_management', 'stop_loss', 'enabled', default=True)
        """
        config = self.get_config()
        for key in keys:
            if isinstance(config, dict) and key in config:
                config = config[key]
            else:
                return default
        return config
    
    def set_nested_value(self, value: Any, *keys):
        """
        Set a nested configuration value.
        
        Args:
            value: Value to set
            *keys: Keys to traverse
        
        Example:
            >>> manager.set_nested_value(True, 'risk_management', 'stop_loss', 'enabled')
        """
        config = self.get_config()
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
        self._config = config
    
    def reload(self):
        """Force reload configuration from file."""
        self._config = None
        self._indicators_config = None
        self.load_config()
    
    def get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration values.
        
        Returns:
            Dictionary of default configuration values
        """
        return {
            'symbols': [],
            'trading': {
                'default_quantity': 350,
                'enable_auto_trading': False,
                'refresh_interval': 60,
                'slow_refresh_interval': 30,
                'fast_refresh_interval': 15,
                'allow_buy': True,
                'allow_sell': False,
                'paper_trading': True,
                'auto_trade': False,
            },
            'backtest': {
                'enabled': False,
                'start_date': '',
                'end_date': '',
                'initial_capital': 20000.0,
                'speed': 'fast',
                'resolution': '30S',
            },
            'risk_management': {
                'stop_loss': {
                    'enabled': True,
                    'method': 'volatility_adjusted',
                },
                'trailing_stop': {
                    'enabled': True,
                },
                'profit_targets': {
                    'enabled': True,
                },
                'paper_trading_mode': {
                    'enabled': True,
                    'consecutive_losses_trigger': 3,
                },
                'capital_percentage_per_trade_intraday': 20.0,
                'capital_percentage_per_trade_backtest': 50.0,
            },
            'indicators': {},
        }
    
    def validate_config(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Validate configuration and fill in missing defaults.
        
        Args:
            config: Configuration to validate (uses loaded config if None)
        
        Returns:
            Dictionary with validation results and corrected config
        """
        if config is None:
            config = self.get_config()
        
        defaults = self.get_default_config()
        errors = []
        warnings = []
        
        # Check required sections
        for section in ['symbols', 'trading', 'risk_management']:
            if section not in config:
                warnings.append(f"Missing section: {section}")
                config[section] = defaults.get(section, {})
        
        # Validate initial capital
        initial_capital = config.get('backtest', {}).get('initial_capital', 0)
        if initial_capital <= 0:
            errors.append("Initial capital must be greater than 0")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'config': config
        }
