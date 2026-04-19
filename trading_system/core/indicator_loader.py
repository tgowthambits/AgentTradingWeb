"""
Dynamic Indicator Loader with Auto-Discovery

Loads indicators dynamically from configuration without hardcoded imports.
Implements true plug-and-play architecture with automatic indicator discovery
and config file synchronization.
"""

import importlib
import yaml
import os
import inspect
from pathlib import Path
from typing import List, Dict, Any, Set
from trading_system.core.base_indicator import BaseIndicator


class IndicatorLoader:
    """
    Dynamically loads indicators from configuration.
    
    No hardcoded imports - all indicators loaded at runtime!
    """
    
    def __init__(self, 
                 config_path: str = "trading_system/config/indicators_config.yaml",
                 indicators_dir: str = "trading_system/indicators",
                 auto_sync: bool = True,
                 trading_config_path: str = "trading_system/config/trading_config.yaml"):
        """
        Initialize the indicator loader.
        
        Args:
            config_path: Path to indicators configuration file
            indicators_dir: Directory containing indicator modules
            auto_sync: Automatically sync config with available indicators
            trading_config_path: Path to trading configuration file (also synced)
        """
        self.config_path = config_path
        self.indicators_dir = indicators_dir
        self.auto_sync = auto_sync
        self.trading_config_path = trading_config_path
        self.config = self._load_config()
        self.loaded_indicators = []
        
        # Auto-sync config with available indicators
        if self.auto_sync:
            self._sync_config_with_indicators()
            self._sync_trading_config_with_indicators()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Indicators config not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in indicators config: {e}")
    
    def load_indicators(self, verbose: bool = True) -> List[BaseIndicator]:
        """
        Load all enabled indicators from configuration.
        
        Args:
            verbose: Print loading information
        
        Returns:
            List of loaded indicator instances
        """
        indicators = []
        indicator_configs = self.config.get('indicators', {})
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"🔌 Dynamic Indicator Loading")
            print(f"{'='*60}\n")
        
        for indicator_name, indicator_config in indicator_configs.items():
            # Skip disabled indicators
            if not indicator_config.get('enabled', False):
                if verbose:
                    print(f"⏭️  Skipping disabled: {indicator_name}")
                continue
            
            try:
                # Load indicator dynamically
                indicator = self._load_single_indicator(
                    indicator_name, 
                    indicator_config, 
                    verbose
                )
                
                if indicator:
                    indicators.append(indicator)
                    self.loaded_indicators.append(indicator_name)
                    
            except Exception as e:
                print(f"❌ Failed to load {indicator_name}: {str(e)}")
                if verbose:
                    import traceback
                    traceback.print_exc()
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"✅ Loaded {len(indicators)} indicators successfully")
            print(f"{'='*60}\n")
        
        return indicators
    
    def _load_single_indicator(
        self, 
        indicator_name: str, 
        config: Dict[str, Any],
        verbose: bool
    ) -> BaseIndicator:
        """
        Load a single indicator dynamically.
        
        Args:
            indicator_name: Name of the indicator
            config: Indicator configuration dict
            verbose: Print loading info
        
        Returns:
            Loaded indicator instance
        """
        # Extract module and class information
        module_path = config.get('module')
        class_name = config.get('class_name')
        
        if not module_path or not class_name:
            raise ValueError(
                f"Missing 'module' or 'class_name' for {indicator_name}"
            )
        
        if verbose:
            print(f"⚙️  Loading: {indicator_name}")
            print(f"   Module: {module_path}")
            print(f"   Class: {class_name}")
        
        # Dynamically import the module
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            raise ImportError(
                f"Cannot import module '{module_path}' for {indicator_name}: {e}"
            )
        
        # Get the class from the module
        try:
            indicator_class = getattr(module, class_name)
        except AttributeError:
            raise AttributeError(
                f"Class '{class_name}' not found in module '{module_path}'"
            )
        
        # Verify it's a valid indicator class
        if not issubclass(indicator_class, BaseIndicator):
            raise TypeError(
                f"{class_name} must inherit from BaseIndicator"
            )
        
        # Prepare indicator configuration
        indicator_config = {
            'enabled': True,
            'weight': config.get('weight', 1.0),
            **config.get('params', {})
        }
        
        # Instantiate the indicator
        indicator_instance = indicator_class(config=indicator_config)
        
        if verbose:
            print(f"   ✅ Loaded successfully (weight: {indicator_config['weight']})")
        
        return indicator_instance
    
    def get_aggregation_config(self) -> Dict[str, Any]:
        """Get signal aggregation configuration."""
        return self.config.get('aggregation', {})
    
    def get_signal_filtering_config(self) -> Dict[str, Any]:
        """Get signal filtering configuration."""
        return self.config.get('signal_filtering', {})
    
    def get_advanced_config(self) -> Dict[str, Any]:
        """Get advanced configuration."""
        return self.config.get('advanced', {})
    
    def reload_config(self):
        """Reload configuration from file (for hot reload)."""
        self.config = self._load_config()
        print("🔄 Configuration reloaded")
    
    def validate_config(self) -> bool:
        """
        Validate the configuration file.
        
        Returns:
            True if valid, raises exception otherwise
        """
        # Check required sections
        required_sections = ['aggregation', 'indicators']
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required section: {section}")
        
        # Check at least one indicator is enabled
        indicators = self.config.get('indicators', {})
        enabled_count = sum(
            1 for ind in indicators.values() 
            if ind.get('enabled', False)
        )
        
        if enabled_count == 0:
            raise ValueError("No indicators are enabled in configuration")
        
        # Validate each indicator configuration
        for name, ind_config in indicators.items():
            if not ind_config.get('enabled', False):
                continue
            
            # Check required fields
            if 'module' not in ind_config:
                raise ValueError(f"Indicator '{name}' missing 'module' field")
            
            if 'class_name' not in ind_config:
                raise ValueError(f"Indicator '{name}' missing 'class_name' field")
        
        print("✅ Configuration is valid")
        return True
    
    def get_indicator_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all configured indicators.
        
        Returns:
            List of dicts with indicator information
        """
        info = []
        
        for name, config in self.config.get('indicators', {}).items():
            info.append({
                'name': name,
                'enabled': config.get('enabled', False),
                'module': config.get('module', 'N/A'),
                'class': config.get('class_name', 'N/A'),
                'weight': config.get('weight', 1.0),
                'signals': config.get('signals', {})
            })
        
        return info
    
    def __str__(self):
        enabled = len(self.loaded_indicators)
        total = len(self.config.get('indicators', {}))
        return f"IndicatorLoader ({enabled}/{total} loaded)"
    
    def __repr__(self):
        return f"<IndicatorLoader: {self.loaded_indicators}>"
    
    # ========== AUTO-DISCOVERY & SYNC METHODS ==========
    
    def discover_indicators(self) -> Dict[str, Dict[str, Any]]:
        """
        Automatically discover all available indicators in the indicators directory.
        
        Returns:
            Dict mapping indicator names to their metadata
        """
        discovered = {}
        
        if not os.path.exists(self.indicators_dir):
            print(f"⚠️  Indicators directory not found: {self.indicators_dir}")
            return discovered
        
        # Scan all Python files in indicators directory
        for file_path in Path(self.indicators_dir).glob("*.py"):
            if file_path.name.startswith("_"):
                continue  # Skip __init__.py and private files
            
            try:
                # Extract indicator info from file
                indicator_info = self._extract_indicator_info(file_path)
                
                if indicator_info:
                    indicator_name = indicator_info['name']
                    discovered[indicator_name] = indicator_info
                    
            except Exception as e:
                print(f"⚠️  Failed to process {file_path.name}: {e}")
        
        return discovered
    
    def _extract_indicator_info(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract indicator information from a Python file.
        
        Args:
            file_path: Path to the indicator file
        
        Returns:
            Dict with indicator metadata
        """
        # Convert file path to module path
        # Use absolute path resolution
        abs_path = file_path.resolve()
        
        # Get the module path relative to project root
        # trading_system/indicators/rsi_indicator.py -> trading_system.indicators.rsi_indicator
        path_parts = abs_path.parts
        
        # Find 'trading_system' in path
        try:
            idx = path_parts.index('trading_system')
            module_parts = path_parts[idx:]
            module_path = '.'.join(module_parts).replace('.py', '')
        except ValueError:
            # Fallback: use the filename
            module_path = f"trading_system.indicators.{file_path.stem}"
        
        try:
            # Import the module
            module = importlib.import_module(module_path)
            
            # Find BaseIndicator subclasses
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # Check if it's a BaseIndicator subclass (but not BaseIndicator itself)
                if (issubclass(obj, BaseIndicator) and 
                    obj != BaseIndicator and 
                    obj.__module__ == module.__name__):
                    
                    # Extract default config from __init__ signature
                    default_params = self._extract_default_params(obj)
                    
                    # Create indicator name from class name
                    indicator_name = self._class_name_to_indicator_name(name)
                    
                    return {
                        'name': indicator_name,
                        'module': module_path,
                        'class_name': name,
                        'default_params': default_params,
                        'file_path': str(file_path)
                    }
        
        except Exception as e:
            raise Exception(f"Failed to extract info from {file_path}: {e}")
        
        return None
    
    def _extract_default_params(self, indicator_class) -> Dict[str, Any]:
        """
        Extract default parameters from indicator class __init__ method.
        
        Args:
            indicator_class: The indicator class
        
        Returns:
            Dict of parameter names to default values
        """
        params = {}
        
        try:
            # Get __init__ signature
            init_signature = inspect.signature(indicator_class.__init__)
            
            # Create a temporary instance to get defaults
            temp_instance = indicator_class(config={})
            
            # Extract common parameters
            common_params = ['period', 'fast_period', 'slow_period', 'signal_period',
                           'oversold', 'overbought', 'std_dev', 'ma_type']
            
            for param in common_params:
                if hasattr(temp_instance, param):
                    params[param] = getattr(temp_instance, param)
            
        except Exception as e:
            # If we can't extract, use empty dict
            pass
        
        return params
    
    def _class_name_to_indicator_name(self, class_name: str) -> str:
        """
        Convert class name to indicator name.
        
        Example: RSIIndicator -> rsi
                 MACrossoverIndicator -> ma_crossover
                 MACDIndicator -> macd
        
        Args:
            class_name: Class name
        
        Returns:
            Indicator name for config file
        """
        # Remove 'Indicator' suffix
        name = class_name.replace('Indicator', '')
        
        # Handle acronyms smartly
        # If it's all uppercase (like RSI, MACD), keep it as one word
        if name.isupper():
            return name.lower()
        
        # Convert CamelCase to snake_case, handling acronyms
        result = []
        for i, char in enumerate(name):
            if char.isupper():
                # Add underscore before uppercase letter if:
                # - Not first character
                # - Previous char is lowercase (CamelCase boundary)
                # - OR previous char is uppercase but next char is lowercase (end of acronym)
                if i > 0:
                    prev_lower = name[i-1].islower()
                    next_lower = i < len(name) - 1 and name[i+1].islower()
                    
                    if prev_lower or (name[i-1].isupper() and next_lower):
                        result.append('_')
                
                result.append(char.lower())
            else:
                result.append(char)
        
        return ''.join(result)
    
    def _sync_config_with_indicators(self):
        """
        Synchronize config file with available indicators.
        
        - Adds newly discovered indicators
        - Removes indicators that no longer exist
        - Updates config file
        """
        print(f"\n{'='*60}")
        print(f"🔄 Auto-Syncing Indicator Configuration")
        print(f"{'='*60}\n")
        
        # Discover available indicators
        discovered = self.discover_indicators()
        
        if not discovered:
            print("⚠️  No indicators discovered\n")
            return
        
        print(f"📂 Discovered {len(discovered)} indicators in {self.indicators_dir}")
        
        # Get current config indicators
        current_indicators = set(self.config.get('indicators', {}).keys())
        discovered_indicators = set(discovered.keys())
        
        # Find differences
        new_indicators = discovered_indicators - current_indicators
        removed_indicators = current_indicators - discovered_indicators
        
        if not new_indicators and not removed_indicators:
            print("✅ Config is already in sync\n")
            return
        
        # Report changes
        if new_indicators:
            print(f"\n➕ New indicators found: {len(new_indicators)}")
            for name in new_indicators:
                print(f"   • {name}")
        
        if removed_indicators:
            print(f"\n➖ Removed indicators (files deleted): {len(removed_indicators)}")
            for name in removed_indicators:
                print(f"   • {name}")
        
        # Update config
        self._update_config(discovered, new_indicators, removed_indicators)
        
        print(f"\n✅ Configuration updated and saved to: {self.config_path}\n")
    
    def _update_config(self, 
                      discovered: Dict[str, Dict[str, Any]], 
                      new_indicators: Set[str],
                      removed_indicators: Set[str]):
        """
        Update the config file with discovered indicators.
        
        Args:
            discovered: Discovered indicators metadata
            new_indicators: Set of new indicator names
            removed_indicators: Set of removed indicator names
        """
        # Remove deleted indicators
        for name in removed_indicators:
            if name in self.config['indicators']:
                del self.config['indicators'][name]
        
        # Add new indicators with defaults
        for name in new_indicators:
            indicator_info = discovered[name]
            
            default_config = {
                'enabled': False,  # Disabled by default for safety
                'module': indicator_info['module'],
                'class_name': indicator_info['class_name'],
                'weight': 1.0,
                'params': indicator_info['default_params'],
                'signals': {
                    'buy': True,
                    'sell': True,
                    'hold': True
                }
            }
            
            self.config['indicators'][name] = default_config
        
        # Save updated config
        self._save_config()
    
    def _save_config(self):
        """Save the current configuration to YAML file."""
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(
                    self.config, 
                    f, 
                    default_flow_style=False,
                    sort_keys=False,
                    indent=2
                )
        except Exception as e:
            print(f"❌ Failed to save config: {e}")
            raise
    
    def add_indicator_to_config(self, 
                               indicator_name: str,
                               module_path: str,
                               class_name: str,
                               params: Dict[str, Any] = None,
                               weight: float = 1.0,
                               enabled: bool = False):
        """
        Manually add an indicator to the configuration.
        
        Args:
            indicator_name: Name for the indicator in config
            module_path: Python module path
            class_name: Class name in the module
            params: Indicator parameters
            weight: Voting weight
            enabled: Whether to enable by default
        """
        if 'indicators' not in self.config:
            self.config['indicators'] = {}
        
        self.config['indicators'][indicator_name] = {
            'enabled': enabled,
            'module': module_path,
            'class_name': class_name,
            'weight': weight,
            'params': params or {},
            'signals': {
                'buy': True,
                'sell': True,
                'hold': True
            }
        }
        
        self._save_config()
        print(f"✅ Added {indicator_name} to configuration")
    
    def remove_indicator_from_config(self, indicator_name: str):
        """
        Remove an indicator from the configuration.
        
        Args:
            indicator_name: Name of the indicator to remove
        """
        if indicator_name in self.config.get('indicators', {}):
            del self.config['indicators'][indicator_name]
            self._save_config()
            print(f"✅ Removed {indicator_name} from configuration")
        else:
            print(f"⚠️  Indicator {indicator_name} not found in configuration")
    
    def _sync_trading_config_with_indicators(self):
        """
        Synchronize trading_config.yaml with available indicators.
        
        Updates the indicators section in trading_config.yaml to match
        discovered indicators from the indicators folder.
        """
        print(f"\n{'='*60}")
        print(f"🔄 Auto-Syncing Trading Configuration")
        print(f"{'='*60}\n")
        
        # Load trading config
        try:
            with open(self.trading_config_path, 'r') as f:
                trading_config = yaml.safe_load(f)
        except FileNotFoundError:
            print(f"⚠️  Trading config not found: {self.trading_config_path}")
            return
        
        # Discover available indicators
        discovered = self.discover_indicators()
        
        if not discovered:
            print("⚠️  No indicators discovered\n")
            return
        
        print(f"📂 Discovered {len(discovered)} indicators")
        
        # Get current trading config indicators
        current_indicators = set(trading_config.get('indicators', {}).keys())
        discovered_indicators = set(discovered.keys())
        
        # Find differences
        new_indicators = discovered_indicators - current_indicators
        removed_indicators = current_indicators - discovered_indicators
        
        if not new_indicators and not removed_indicators:
            print("✅ Trading config is already in sync\n")
            return
        
        # Report changes
        if new_indicators:
            print(f"\n➕ New indicators to add to trading config: {len(new_indicators)}")
            for name in new_indicators:
                print(f"   • {name}")
        
        if removed_indicators:
            print(f"\n➖ Removed indicators from trading config: {len(removed_indicators)}")
            for name in removed_indicators:
                print(f"   • {name}")
        
        # Update trading config
        self._update_trading_config(trading_config, discovered, new_indicators, removed_indicators)
        
        print(f"\n✅ Trading configuration updated and saved to: {self.trading_config_path}\n")
    
    def _update_trading_config(self,
                              trading_config: dict,
                              discovered: Dict[str, Dict[str, Any]],
                              new_indicators: Set[str],
                              removed_indicators: Set[str]):
        """
        Update the trading config with discovered indicators.
        
        Args:
            trading_config: Current trading configuration dict
            discovered: Discovered indicators metadata
            new_indicators: Set of new indicator names
            removed_indicators: Set of removed indicator names
        """
        # Ensure indicators section exists
        if 'indicators' not in trading_config:
            trading_config['indicators'] = {}
        
        # Remove deleted indicators
        for name in removed_indicators:
            if name in trading_config['indicators']:
                del trading_config['indicators'][name]
        
        # Add new indicators with defaults
        for name in new_indicators:
            indicator_info = discovered[name]
            
            # Get default parameters from indicators_config if available
            indicators_config_params = self.config.get('indicators', {}).get(name, {}).get('params', {})
            default_params = indicator_info['default_params'] if indicator_info['default_params'] else indicators_config_params
            
            # Get weight from indicators_config if available
            default_weight = self.config.get('indicators', {}).get(name, {}).get('weight', 1.0)
            
            # Get enabled status from indicators_config if available
            default_enabled = self.config.get('indicators', {}).get(name, {}).get('enabled', True)
            
            default_config = {
                'enabled': default_enabled,
                'weight': default_weight,
            }
            
            # Add parameters as top-level keys (trading_config style)
            default_config.update(default_params)
            
            trading_config['indicators'][name] = default_config
        
        # Save updated trading config
        self._save_trading_config(trading_config)
    
    def _save_trading_config(self, trading_config: dict):
        """Save the trading configuration to YAML file."""
        try:
            with open(self.trading_config_path, 'w') as f:
                yaml.dump(
                    trading_config,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    indent=2
                )
        except Exception as e:
            print(f"❌ Failed to save trading config: {e}")
            raise

