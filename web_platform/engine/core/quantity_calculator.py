"""
Quantity Calculator Module

Handles dynamic quantity calculation based on available capital,
lot sizes, and risk management parameters.
"""

from typing import Dict, Any, Optional


class QuantityCalculator:
    """
    Calculates trading quantities based on capital and risk parameters.
    
    This class handles:
    - Lot size management for different symbols
    - Dynamic quantity calculation based on available capital
    - Capital percentage allocation per trade
    - Margin requirements for LONG vs SHORT positions
    
    Attributes:
        config: Trading configuration dictionary
        lot_sizes: Dictionary mapping symbols to their lot sizes
        default_lot_size: Default lot size when symbol-specific size is unavailable
        initial_capital: Starting capital for the trading session
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the QuantityCalculator.
        
        Args:
            config: Trading configuration dictionary
        """
        self.config = config or {}
        self._load_lot_sizes()
        self._load_capital_settings()
    
    def _load_lot_sizes(self):
        """Load lot size configuration from config."""
        trading_config = self.config.get('trading', {})
        self.lot_sizes = trading_config.get('lot_sizes', {})
        
        # Get default lot size from lot_sizes config or use fallback
        lot_sizes_config = self.config.get('lot_sizes', {})
        self.default_lot_size = lot_sizes_config.get('default', 50)
        
        # Also check trading config for lot_sizes
        if not self.lot_sizes and 'lot_sizes' in trading_config:
            self.lot_sizes = trading_config.get('lot_sizes', {})
    
    def _load_capital_settings(self):
        """Load capital-related settings from config."""
        backtest_config = self.config.get('backtest', {})
        self.initial_capital = backtest_config.get('initial_capital', 20000)
    
    def reload_config(self, config: Dict[str, Any]):
        """
        Reload configuration with new config.
        
        Args:
            config: New trading configuration dictionary
        """
        self.config = config
        self._load_lot_sizes()
        self._load_capital_settings()
    
    def get_lot_size(self, symbol: str) -> int:
        """
        Get lot size for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'NSE:NIFTY2612025700CE')
        
        Returns:
            Lot size as integer, or 0 if invalid
        """
        lot_size = self.lot_sizes.get(symbol, self.default_lot_size)
        
        # Ensure lot_size is valid (positive integer)
        if lot_size is None or lot_size <= 0:
            return 0  # Return 0 to indicate invalid lot size
        return int(lot_size)
    
    def set_lot_size(self, symbol: str, lot_size: int):
        """
        Set lot size for a specific symbol.
        
        Args:
            symbol: Trading symbol
            lot_size: Lot size value
        """
        self.lot_sizes[symbol] = lot_size
    
    def calculate_dynamic_quantity(
        self,
        symbol: str,
        price: float,
        available_capital: float = None,
        position_type: str = "LONG",
        actual_capital: float = None
    ) -> int:
        """
        Calculate dynamic quantity based on available capital, lot size, and risk per trade.
        
        The calculation follows this formula:
        1. Get lot size for symbol
        2. Calculate max capital per trade based on percentage
        3. Calculate margin per lot (different for LONG vs SHORT)
        4. Calculate max lots = floor(max_capital_per_trade / margin_per_lot)
        5. Final quantity = max_lots * lot_size
        
        Args:
            symbol: Trading symbol
            price: Entry price per unit
            available_capital: Available capital for trading (if None, uses initial_capital)
            position_type: 'LONG' or 'SHORT' (affects margin calculation)
            actual_capital: Current actual capital (for reference in calculations)
        
        Returns:
            Quantity as integer (multiple of lot size)
        """
        if available_capital is None:
            available_capital = self.initial_capital
        
        # Ensure available capital is positive
        if available_capital <= 0:
            print(f"⚠️  Warning: Available capital is ₹{available_capital:.2f}, cannot calculate quantity")
            return 0
        
        # Get lot size for symbol
        lot_size = self.get_lot_size(symbol)
        
        # If lot size is 0 or invalid, use default lot size
        if lot_size <= 0:
            lot_size = self.default_lot_size
            if not lot_size or lot_size <= 0:
                print(f"⚠️  Invalid lot size and no default lot size for {symbol}. Cannot calculate quantity.")
                return 0
            print(f"⚠️  Invalid lot size for {symbol}. Using default lot size: {lot_size}")
        
        # Get capital percentage based on trading mode
        backtest_mode = self.config.get('backtest', {}).get('enabled', False)
        risk_config = self.config.get('risk_management', {})
        
        if backtest_mode:
            capital_pct_raw = risk_config.get('capital_percentage_per_trade_backtest', 50.0)
            capital_percentage = float(capital_pct_raw) / 100.0
            print(f"📊 Backtest mode: Using {capital_pct_raw}% of capital per trade")
        else:
            capital_pct_raw = risk_config.get('capital_percentage_per_trade_intraday', 20.0)
            capital_percentage = float(capital_pct_raw) / 100.0
            print(f"📊 Intraday mode: Using {capital_pct_raw}% of capital per trade")
        
        # Calculate max capital per trade
        max_capital_per_trade = available_capital * capital_percentage
        print(f"💰 Capital allocation: {capital_percentage*100:.0f}% of ₹{available_capital:,.2f} = ₹{max_capital_per_trade:,.2f} per trade")
        
        # Calculate cost per lot
        cost_per_lot = price * lot_size
        
        if cost_per_lot <= 0:
            print(f"⚠️  Invalid price or lot size: price={price}, lot_size={lot_size}")
            default_qty = self.config.get('trading', {}).get('default_quantity', None)
            if default_qty and default_qty > 0:
                return int(default_qty)
            return 25  # Last resort fallback
        
        # Calculate margin per lot (depends on position type)
        if position_type == 'SHORT':
            short_margin_per_lot = risk_config.get('short_margin_per_lot', None)
            if short_margin_per_lot is not None:
                margin_per_lot = float(short_margin_per_lot)
            else:
                margin_per_lot = cost_per_lot
        else:
            # LONG (option buying): margin is premium cost per lot
            margin_per_lot = cost_per_lot
        
        if margin_per_lot <= 0:
            print(f"⚠️  Invalid margin per lot: {margin_per_lot}")
            return 0
        
        # Calculate number of lots we can afford
        max_lots = int(max_capital_per_trade / margin_per_lot)
        
        # Ensure at least 1 lot if capital permits
        if max_lots < 1:
            if max_capital_per_trade >= cost_per_lot:
                max_lots = 1
                print(f"📊 Using 1 lot within capital percentage limit: ₹{max_capital_per_trade:.2f}")
            else:
                print(f"⚠️  Insufficient capital for 1 lot. Max per trade: ₹{max_capital_per_trade:.2f}, Required: ₹{cost_per_lot:.2f}")
                return 0
        
        # Calculate final quantity
        if max_lots < 1:
            print(f"⚠️  Insufficient capital for 1 lot. Max per trade: ₹{max_capital_per_trade:.2f}, Required: ₹{margin_per_lot:.2f}")
            return 0
        
        quantity = max_lots * lot_size
        
        # Verify we don't exceed available capital
        total_cost = quantity * price
        if total_cost > available_capital:
            affordable_lots = int(available_capital / cost_per_lot)
            if affordable_lots >= 1:
                quantity = affordable_lots * lot_size
                print(f"📊 Quantity adjusted to fit available capital: {quantity} (from {max_lots} lots)")
            else:
                print(f"⚠️  Cannot afford calculated quantity. Available: ₹{available_capital:.2f}, Required: ₹{total_cost:.2f}")
                return 0
            if quantity == 0:
                print(f"⚠️  Cannot afford any lots. Available: ₹{available_capital:.2f}, Cost per lot: ₹{cost_per_lot:.2f}")
                return 0
        
        return quantity
    
    def calculate_recovery_quantity(
        self,
        symbol: str,
        price: float,
        base_quantity: int,
        loss_to_recover: float,
        max_multiplier: float = 3.0
    ) -> int:
        """
        Calculate additional quantity needed to recover a loss.
        
        Args:
            symbol: Trading symbol
            price: Entry price
            base_quantity: Base quantity before recovery adjustment
            loss_to_recover: Amount to recover
            max_multiplier: Maximum multiplier for recovery (default 3x)
        
        Returns:
            Additional recovery quantity
        """
        if loss_to_recover <= 0:
            return 0
        
        lot_size = self.get_lot_size(symbol)
        if lot_size <= 0:
            lot_size = self.default_lot_size
            if lot_size <= 0:
                return 0
        
        # Calculate additional quantity needed to recover loss
        # Estimate profit per lot (5% profit estimate)
        estimated_profit_pct = 0.05
        estimated_profit_per_lot = price * lot_size * estimated_profit_pct
        
        if estimated_profit_per_lot <= 0:
            return 0
        
        # Calculate lots needed for recovery
        lots_needed = int((loss_to_recover / estimated_profit_per_lot) + 0.5)
        base_lots = int(base_quantity / lot_size) if lot_size > 0 else 0
        max_recovery_lots = int(base_lots * (max_multiplier - 1.0))
        
        # Cap recovery lots
        recovery_lots = min(lots_needed, max_recovery_lots)
        recovery_quantity = recovery_lots * lot_size
        
        if recovery_quantity > 0:
            print(f"🔄 Loss Recovery: ₹{loss_to_recover:.2f} to recover")
            print(f"   Lot size: {lot_size}, Base lots: {base_lots}, Recovery lots: {recovery_lots}")
            print(f"   Recovery quantity: {recovery_quantity}")
        
        return recovery_quantity
    
    def get_capital_percentage(self, backtest_mode: bool = False) -> float:
        """
        Get the capital percentage per trade for the given mode.
        
        Args:
            backtest_mode: Whether backtesting mode is active
        
        Returns:
            Capital percentage as decimal (e.g., 0.5 for 50%)
        """
        risk_config = self.config.get('risk_management', {})
        
        if backtest_mode:
            pct = risk_config.get('capital_percentage_per_trade_backtest', 50.0)
        else:
            pct = risk_config.get('capital_percentage_per_trade_intraday', 20.0)
        
        return float(pct) / 100.0
    
    def get_lot_sizes_info(self) -> Dict[str, int]:
        """
        Get all configured lot sizes.
        
        Returns:
            Dictionary of symbol to lot size mappings
        """
        return {
            'lot_sizes': self.lot_sizes.copy(),
            'default_lot_size': self.default_lot_size
        }
