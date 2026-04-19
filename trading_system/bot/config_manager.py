"""
Configuration management for the trading bot.
"""

import yaml
from pathlib import Path
from typing import Dict, Any


class ConfigManager:
    """Manages configuration loading and validation."""
    
    def __init__(self, config_path: str = "trading_system/config/trading_config.yaml"):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the trading configuration YAML file
        """
        self.config_path = config_path
        self.config = self.load_config(config_path)
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Dictionary containing the configuration
        """
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key (supports dot notation like 'trading.refresh_interval')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value if value is not None else default
    
    def reload(self) -> None:
        """Reload configuration from file."""
        self.config = self.load_config(self.config_path)
