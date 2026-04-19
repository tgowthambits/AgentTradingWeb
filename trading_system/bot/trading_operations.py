"""
Trading operations module for core trading logic.
"""

from typing import List, Dict, Any, Optional
from rich.console import Console


class TradingOperations:
    """Handles core trading operations and symbol analysis."""
    
    def __init__(self, engine, data_loader, config: Dict[str, Any], 
                 auto_trade: bool, allow_buy: bool, allow_sell: bool,
                 default_quantity: int, backtest_mode: bool, console: Optional[Console] = None):
        """
        Initialize trading operations.
        
        Args:
            engine: TradingEngine instance
            data_loader: DataLoader instance
            config: Configuration dictionary
            auto_trade: Whether auto-trading is enabled
            allow_buy: Whether BUY signals are allowed
            allow_sell: Whether SELL signals are allowed
            default_quantity: Default quantity for trades
            backtest_mode: Whether running in backtest mode
            console: Optional Rich Console instance
        """
        self.engine = engine
        self.data_loader = data_loader
        self.config = config
        self.auto_trade = auto_trade
        self.allow_buy = allow_buy
        self.allow_sell = allow_sell
        self.default_quantity = default_quantity
        self.backtest_mode = backtest_mode
        self.console = console or Console()
        self.total_signals_generated = 0
    
    def run_once(self, symbols: Optional[List[str]] = None, increment_count: bool = True) -> List[Dict]:
        """
        Run one analysis cycle for specified symbols (or all if None).
        
        Args:
            symbols: List of symbols to process (None for all)
            increment_count: Whether to increment refresh count
            
        Returns:
            List of analysis results
        """
        results = []
        stop_count = 0  # Track completed symbols
        
        # Use provided symbols or all symbols from config
        symbols_to_process = symbols if symbols is not None else self.config['symbols']
        
        for symbol in symbols_to_process:
            try:
                # Load latest data
                df = self.data_loader.load_symbol_data(
                    symbol,
                    self.config['date_range']['start_date'],
                    self.config['date_range']['end_date'],
                    self.config['resolution']
                )
                
                # Check if data is valid
                if df is None or df.empty:
                    self.console.print(f"[yellow]⚠️  No data returned for {symbol}, skipping...[/yellow]")
                    continue
                
                # Prepare data
                df = self.data_loader.prepare_for_indicators(df)
                
                # Analyze symbol
                result = self.engine.analyze_symbol(df, symbol, verbose=False)
                
                # Add dataframe for UI charting (doesn't affect core logic)
                result['dataframe'] = df
                
                results.append(result)
                
                # Execute trading decision if auto-trading enabled
                if self.auto_trade and result['final_signal'] != 'HOLD':
                    signal = result['final_signal']
                    
                    # Check if this trade direction is allowed
                    can_execute = False
                    if signal == 'BUY' and self.allow_buy:
                        can_execute = True
                    elif signal == 'SELL' and self.allow_sell:
                        can_execute = True
                    
                    if can_execute:
                        self.engine.execute_trading_decision(
                            result, quantity=self.default_quantity, df=df,
                            current_timestamp=result.get('timestamp')
                        )
                        self.total_signals_generated += 1
                    else:
                        # Log skipped signal
                        direction = "BUY (LONG)" if signal == 'BUY' else "SELL (SHORT)"
                        self.console.print(f"[yellow]⏭️  Skipped {direction} signal for {symbol} (disabled in config)[/yellow]")
            
            except StopIteration as e:
                # Symbol backtest completed - track it
                stop_count += 1
                if self.backtest_mode:
                    # Silent in backtest mode - we'll check the count
                    pass
                else:
                    self.console.print(f"[yellow]⚠️  {str(e)}[/yellow]")
                
            except Exception as e:
                self.console.print(f"[red]❌ Error analyzing {symbol}: {str(e)}[/red]")
                import traceback
                self.console.print(f"[dim]{traceback.format_exc()}[/dim]")
        
        # If all symbols completed in backtest mode, raise StopIteration
        if self.backtest_mode and stop_count >= len(symbols_to_process):
            raise StopIteration("All symbols completed backtest")
        
        return results
