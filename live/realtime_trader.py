"""
Real-time Trading System
Runs inference every 5 seconds and executes trades based on signals (long-only)
"""

import time
from datetime import datetime
from typing import Optional, Dict
import pandas as pd
import yaml
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from pipeline.live_inference import live_inference
from data.loaders import load_daily, load_intraday,load_intraday_generator
from live.position_tracker import PositionTracker

console = Console()
# Initialize generator once (outside loop)
intraday_stream = load_intraday()


class RealTimeTrader:
    """Real-time trading system with position tracking"""
    
    def __init__(self, quantity: int = 1, interval: int = 5, rl_sell_threshold: int = None, config_path: str = "configs/params.yaml"):
        """
        Initialize real-time trader
        
        Args:
            quantity: Number of shares/units to trade per order
            interval: Time interval in seconds between checks (default: 5)
            rl_sell_threshold: Number of consecutive RL SELL signals to trigger immediate sell (default: from config or 2)
            config_path: Path to configuration file
        """
        self.quantity = quantity
        self.interval = interval
        
        # Load stop loss from config
        try:
            with open(config_path, "r") as f:
                cfg = yaml.safe_load(f)
            stop_loss_amount = cfg.get("trading", {}).get("stop_loss_amount", 2.0)
        except Exception as e:
            logger.warning(f"Could not load stop loss from config: {e}. Using default: ₹2.0")
            stop_loss_amount = 2.0
        
        self.position_tracker = PositionTracker(stop_loss_amount=stop_loss_amount)
        self.running = False
        self.last_signal = 0
        
        # Load RL sell threshold from config if not provided
        if rl_sell_threshold is None:
            try:
                with open(config_path, "r") as f:
                    cfg = yaml.safe_load(f)
                rl_sell_threshold = cfg.get("rl", {}).get("sell_threshold", 2)
            except Exception as e:
                logger.warning(f"Could not load RL sell threshold from config: {e}. Using default: 2")
                rl_sell_threshold = 2
        
        self.rl_sell_threshold = rl_sell_threshold
        self.rl_consecutive_sells = 0  # Track consecutive RL SELL signals
        
    def get_current_price(self, intraday_df: pd.DataFrame) -> float:
        """Get current price from intraday data"""
        if len(intraday_df) > 0:
            return float(intraday_df["close"].iloc[-1])
        return 0.0
    
    def decide_action(self, signal: int, current_price: float, rl_action: int = None) -> Dict:
        """
        Decide trading action based on signal and current position
        
        Long-only strategy:
        - BUY (signal=1, no position) -> Buy
        - HOLD (signal=1, have position) -> Hold
        - SELL (signal=-1, have position) -> Sell
        - HOLD (signal=0) -> Hold (no action)
        
        RL Agent Immediate Sell:
        - If RL agent gives SELL signal N consecutive times (default: 2), sell immediately
        
        Args:
            signal: Model signal (-1, 0, 1)
            current_price: Current market price
            rl_action: RL agent action (0=BUY, 1=SELL, 2=HOLD)
            
        Returns:
            Action dictionary
        """
        has_position = self.position_tracker.has_position()
        
        # Check stop loss first (if in position) - highest priority
        if has_position:
            self.position_tracker.update_pnl(current_price)
            stop_loss_triggered = self.position_tracker.check_stop_loss(current_price)
            if stop_loss_triggered:
                result = self.position_tracker.sell(current_price, reason="Stop Loss")
                return {
                    "action": "SELL",
                    "signal": signal,
                    "result": result,
                    "reason": f"Stop Loss triggered at ₹{current_price:.2f} (SL: ₹{result.get('stop_loss_price', 0):.2f})"
                }
        
        # Track consecutive RL SELL signals
        if rl_action is not None:
            if rl_action == 1:  # RL SELL signal
                self.rl_consecutive_sells += 1
            else:  # RL BUY or HOLD
                self.rl_consecutive_sells = 0  # Reset counter
        
        # Check if RL agent triggered immediate sell
        if has_position and rl_action == 1 and self.rl_consecutive_sells >= self.rl_sell_threshold:
            result = self.position_tracker.sell(current_price, reason="RL Agent")
            self.rl_consecutive_sells = 0  # Reset after selling
            return {
                "action": "SELL",
                "signal": signal,
                "result": result,
                "reason": f"RL Agent SELL signal {self.rl_sell_threshold} consecutive times (immediate sell)"
            }
        
        if signal == 1:  # BUY signal
            if not has_position:
                # Buy when we have no position
                result = self.position_tracker.buy(current_price, self.quantity)
                return {
                    "action": "BUY",
                    "signal": signal,
                    "result": result,
                    "reason": "BUY signal received, no existing position"
                }
            else:
                # Hold when we already have position
                self.position_tracker.update_pnl(current_price)
                return {
                    "action": "HOLD",
                    "signal": signal,
                    "reason": "BUY signal but already in position",
                    "unrealized_pnl": self.position_tracker.unrealized_pnl
                }
        
        elif signal == -1:  # SELL signal
            if has_position:
                # Sell when we have position
                result = self.position_tracker.sell(current_price)
                return {
                    "action": "SELL",
                    "signal": signal,
                    "result": result,
                    "reason": "SELL signal received, closing position"
                }
            else:
                # Hold when no position (long-only, don't short)
                return {
                    "action": "HOLD",
                    "signal": signal,
                    "reason": "SELL signal but no position (long-only strategy)"
                }
        
        else:  # signal == 0 (HOLD)
            if has_position:
                # Update PnL but hold
                self.position_tracker.update_pnl(current_price)
                return {
                    "action": "HOLD",
                    "signal": signal,
                    "reason": "HOLD signal, maintaining position",
                    "unrealized_pnl": self.position_tracker.unrealized_pnl
                }
            else:
                return {
                    "action": "HOLD",
                    "signal": signal,
                    "reason": "HOLD signal, no position"
                }
    
    def _build_conditions_string(self, output: Dict) -> str:
        """
        Build a conditions string showing why a trade was executed
        
        Args:
            output: Output dictionary from live_inference
            
        Returns:
            String describing the conditions that led to the trade
        """
        conditions = []
        
        # Get filter statuses
        filters = output.get('filters_applied', {})
        confirmations = output.get('confirmations', {})
        
        # Model signals
        daily_models = output.get('daily_models', {})
        intraday_models = output.get('intraday_models', {})
        
        daily_signal = daily_models.get('vomc_daily_signal', 0)
        intraday_signal = intraday_models.get('vomc_intraday_signal', 0)
        rl_action = intraday_models.get('rl_intraday_action', 2)
        
        # Map RL action to signal: 0=BUY, 1=SELL, 2=HOLD
        rl_signal_map = {0: "BUY", 1: "SELL", 2: "HOLD"}
        rl_signal_str = rl_signal_map.get(rl_action, "UNKNOWN")
        
        # Add RL consecutive sell count if applicable
        if rl_action == 1 and self.position_tracker.has_position():
            rl_signal_str += f" ({self.rl_consecutive_sells}/{self.rl_sell_threshold})"
        
        # Add model signals - always show RL agent signal prominently
        signal_parts = []
        # Always include RL agent signal
        signal_parts.append(f"RL Agent: {rl_signal_str}")
        
        # Add other model signals if they're not HOLD
        if daily_signal != 0:
            signal_parts.append(f"Daily: {'BUY' if daily_signal == 1 else 'SELL'}")
        if intraday_signal != 0:
            signal_parts.append(f"Intraday: {'BUY' if intraday_signal == 1 else 'SELL'}")
        
        if signal_parts:
            conditions.append(" | ".join(signal_parts))
        
        # Add filter confirmations
        conf_parts = []
        if confirmations.get('trend', False):
            conf_parts.append("Trend ✓")
        if confirmations.get('breakout', False):
            conf_parts.append("Breakout ✓")
        if confirmations.get('momentum', False):
            conf_parts.append("Momentum ✓")
        
        if conf_parts:
            conditions.append("Confirmations: " + ", ".join(conf_parts))
        
        # Add filter statuses
        filter_parts = []
        if filters.get('volatility', False):
            vol_value = output.get('volatility_value', 0.0)
            filter_parts.append(f"Vol: {vol_value:.2%} ✓")
        if filters.get('confidence', False):
            daily_prob = daily_models.get('vomc_daily_prob', 0)
            intraday_prob = intraday_models.get('vomc_intraday_prob', 0)
            max_prob = max(daily_prob, intraday_prob)
            filter_parts.append(f"Conf: {max_prob:.2%} ✓")
        
        if filter_parts:
            conditions.append(" | ".join(filter_parts))
        
        return " | ".join(conditions) if conditions else "No conditions met"
    
    def print_status(self, output: Dict, action_result: Dict, current_price: float, intraday_df: pd.DataFrame = None):
        """Print formatted status update with all model results"""
        status = self.position_tracker.get_status(current_price)
        
        # Extract LTP and time from intraday_df
        ltp = current_price
        ltp_time = "N/A"
        if intraday_df is not None and len(intraday_df) > 0:
            last_row = intraday_df.iloc[-1]
            ltp = float(last_row.get('close', current_price))
            # Try to get timestamp from various possible column names
            for time_col in ['datetime', 'time', 'timestamp', 'Time', 'DateTime']:
                if time_col in last_row:
                    time_val = last_row[time_col]
                    if pd.notna(time_val):
                        if isinstance(time_val, datetime):
                            ltp_time = time_val.strftime('%Y-%m-%d %H:%M:%S')
                        elif isinstance(time_val, pd.Timestamp):
                            ltp_time = time_val.strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            ltp_time = str(time_val)
                        break
        
        # Clear screen and print header
        console.print()
        console.print(Panel.fit(
            f"[bold cyan]Real-time Trading Update[/bold cyan]\n"
            f"[dim]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]",
            border_style="cyan"
        ))
        
        # Market Data Table
        market_table = Table(title="Market Data", box=box.ROUNDED, show_header=True, header_style="bold magenta")
        market_table.add_column("Metric", style="cyan", width=25)
        market_table.add_column("Value", style="green", width=40)
        market_table.add_row("LTP (Last Traded Price)", f"₹{ltp:.2f}")
        market_table.add_row("Last Update Time", ltp_time)
        console.print(market_table)
        
        # Position Status Table
        position_table = Table(title="Position Status", box=box.ROUNDED, show_header=True, header_style="bold blue")
        position_table.add_column("Metric", style="cyan", width=25)
        position_table.add_column("Value", style="yellow", width=40)
        
        if status["has_position"]:
            position_table.add_row("Position", f"[green]LONG ({status['quantity']} units)[/green]")
            position_table.add_row("Entry Price", f"₹{status['entry_price']:.2f}")
            position_table.add_row("Current Price", f"₹{current_price:.2f}")
            position_table.add_row("Unrealized PnL", f"₹{status['unrealized_pnl']:.2f}")
            if status['entry_time']:
                duration = (datetime.now() - status['entry_time']).total_seconds()
                position_table.add_row("Duration", f"{duration:.0f} seconds")
        else:
            position_table.add_row("Position", "[dim]NO POSITION[/dim]")
        
        position_table.add_row("Total Realized PnL", f"₹{status['total_realized_pnl']:.2f}")
        position_table.add_row("Total PnL", f"₹{status['total_pnl']:.2f}")
        position_table.add_row("Closed Trades", str(status['closed_trades']))
        
        # Stop Loss Information
        stop_loss_amount = status.get('stop_loss_amount', 2.0)
        stop_loss_hits = status.get('stop_loss_hits', 0)
        stop_loss_orders = status.get('stop_loss_orders', 0)
        
        position_table.add_row("Stop Loss Amount", f"₹{stop_loss_amount:.2f} per order")
        position_table.add_row("Stop Loss Hits", f"{stop_loss_hits} times")
        position_table.add_row("Stop Loss Orders", f"{stop_loss_orders} orders")
        
        if status.get('stop_loss_price') is not None:
            position_table.add_row("Current Stop Loss", f"₹{status['stop_loss_price']:.2f}")
        
        console.print(position_table)
        
        # Daily Models Table
        daily_models = output.get('daily_models', {})
        daily_table = Table(title="Daily Models", box=box.ROUNDED, show_header=True, header_style="bold green")
        daily_table.add_column("Model", style="cyan", width=25)
        daily_table.add_column("Signal/Value", style="yellow", width=20)
        daily_table.add_column("Details", style="white", width=25)
        
        vomc_signal = daily_models.get('vomc_daily_signal', 0)
        vomc_signal_str = {1: "[green]BUY[/green]", -1: "[red]SELL[/red]", 0: "[dim]HOLD[/dim]"}.get(vomc_signal, "UNKNOWN")
        vomc_prob = daily_models.get('vomc_daily_prob', 0)
        daily_table.add_row("VOMC Daily", vomc_signal_str, f"Prob: {vomc_prob:.2%}")
        
        regime = daily_models.get('daily_regime', 0)
        daily_table.add_row("HMM Regime", f"Regime {regime}", "")
        
        xgb_pred = daily_models.get('daily_return_prediction', 0)
        daily_table.add_row("XGBoost Prediction", f"{xgb_pred:.4f}", "Expected Return")
        console.print(daily_table)
        
        # Intraday Models Table
        intraday_models = output.get('intraday_models', {})
        intraday_table = Table(title="Intraday Models", box=box.ROUNDED, show_header=True, header_style="bold yellow")
        intraday_table.add_column("Model", style="cyan", width=25)
        intraday_table.add_column("Signal/Value", style="yellow", width=20)
        intraday_table.add_column("Details", style="white", width=25)
        
        vomc_intra_signal = intraday_models.get('vomc_intraday_signal', 0)
        vomc_intra_str = {1: "[green]BUY[/green]", -1: "[red]SELL[/red]", 0: "[dim]HOLD[/dim]"}.get(vomc_intra_signal, "UNKNOWN")
        vomc_intra_prob = intraday_models.get('vomc_intraday_prob', 0)
        intraday_table.add_row("VOMC Intraday", vomc_intra_str, f"Prob: {vomc_intra_prob:.2%}")
        
        regime_intra = intraday_models.get('intraday_regime', 0)
        intraday_table.add_row("HMM Regime", f"Regime {regime_intra}", "")
        
        xgb_pred_intra = intraday_models.get('intraday_return_prediction', 0)
        intraday_table.add_row("XGBoost Prediction", f"{xgb_pred_intra:.4f}", "Expected Return")
        
        rl_action = intraday_models.get('rl_intraday_action', 1)
        rl_mapped = {0: "[green]BUY[/green]", 1: "[red]SELL[/red]", 2: "[dim]HOLD[/dim]"}.get(rl_action, "UNKNOWN")
        intraday_table.add_row("RL Agent", rl_mapped, f"Action: {rl_action}")
        console.print(intraday_table)
        
        # Filters Table
        filters = output.get('filters_applied', {})
        confirmations = output.get('confirmations', {})
        filters_table = Table(title="Precision Filters", box=box.ROUNDED, show_header=True, header_style="bold red")
        filters_table.add_column("Filter", style="cyan", width=25)
        filters_table.add_column("Status", style="yellow", width=20)
        filters_table.add_column("Confirmation", style="white", width=25)
        
        # Show volatility filter with positive, negative, and overall volatility
        vol_status = "[green]✓ PASS[/green]" if filters.get('volatility', False) else "[red]✗ FAIL[/red]"
        overall_vol = output.get('volatility_value', 0.0)
        positive_vol = output.get('volatility_positive', 0.0)
        negative_vol = output.get('volatility_negative', 0.0)
        vol_threshold = 0.01  # Default threshold, could be read from config if needed
        vol_details = f"Overall: {overall_vol:.4%} | +{positive_vol:.4%} | -{negative_vol:.4%} (Thresh: {vol_threshold:.2%})"
        filters_table.add_row("Volatility", vol_status, vol_details)
        
        trend_val = filters.get('trend', 0)
        trend_str = {1: "[green]BULLISH[/green]", -1: "[red]BEARISH[/red]", 0: "[dim]NEUTRAL[/dim]"}.get(trend_val, "UNKNOWN")
        trend_conf = "[green]✓[/green]" if confirmations.get('trend', False) else "[dim]✗[/dim]"
        filters_table.add_row("Trend (MA50/200)", trend_str, f"Confirms: {trend_conf}")
        
        breakout_val = filters.get('breakout', 0)
        breakout_str = {1: "[green]BULLISH[/green]", -1: "[red]BEARISH[/red]", 0: "[dim]NONE[/dim]"}.get(breakout_val, "UNKNOWN")
        breakout_conf = "[green]✓[/green]" if confirmations.get('breakout', False) else "[dim]✗[/dim]"
        filters_table.add_row("Breakout", breakout_str, f"Confirms: {breakout_conf}")
        
        momentum_val = filters.get('momentum', 0)
        momentum_str = {1: "[green]BUY[/green]", -1: "[red]SELL[/red]", 0: "[dim]NEUTRAL[/dim]"}.get(momentum_val, "UNKNOWN")
        momentum_conf = "[green]✓[/green]" if confirmations.get('momentum', False) else "[dim]✗[/dim]"
        filters_table.add_row("Momentum (RSI)", momentum_str, f"Confirms: {momentum_conf}")
        
        # Show confidence filter with actual probability values
        conf_status = "[green]✓ PASS[/green]" if filters.get('confidence', False) else "[red]✗ FAIL[/red]"
        # Get probability values from models
        daily_prob = daily_models.get('vomc_daily_prob', 0)
        intraday_prob = intraday_models.get('vomc_intraday_prob', 0)
        max_prob = max(daily_prob, intraday_prob)
        conf_details = f"Max: {max_prob:.2%} (Daily: {daily_prob:.2%}, Intra: {intraday_prob:.2%})"
        filters_table.add_row("Confidence", conf_status, conf_details)
        console.print(filters_table)
        
        # Signal Summary Table
        signal_table = Table(title="Signal Summary", box=box.ROUNDED, show_header=True, header_style="bold white")
        signal_table.add_column("Signal Type", style="cyan", width=25)
        signal_table.add_column("Value", style="yellow", width=20)
        signal_table.add_column("Status", style="white", width=25)
        
        raw_signal = output.get('raw_signal', 0)
        raw_signal_str = {1: "[green]BUY[/green]", -1: "[red]SELL[/red]", 0: "[dim]HOLD[/dim]"}.get(raw_signal, "UNKNOWN")
        signal_table.add_row("Raw Signal", raw_signal_str, "Before Filters")
        
        final_signal = output.get('final_signal', 0)
        final_signal_str = {1: "[bold green]BUY[/bold green]", -1: "[bold red]SELL[/bold red]", 0: "[bold dim]HOLD[/bold dim]"}.get(final_signal, "UNKNOWN")
        signal_table.add_row("Final Signal", final_signal_str, "[bold]After Filters[/bold]")
        console.print(signal_table)
        
        # Trading Action Table
        action_table = Table(title="Trading Action", box=box.ROUNDED, show_header=True, header_style="bold magenta")
        action_table.add_column("Action", style="cyan", width=25)
        action_table.add_column("Details", style="yellow", width=43)
        
        action = action_result["action"]
        if action == "BUY":
            conditions = self._build_conditions_string(output)
            action_table.add_row("[bold green]🟢 BUY[/bold green]", 
                               f"{action_result['result'].get('quantity', 0)} units @ ₹{current_price:.2f}")
            action_table.add_row("", f"[dim]Conditions: {conditions}[/dim]")
        elif action == "SELL":
            pnl = action_result['result'].get('pnl', 0)
            pnl_color = "[green]" if pnl > 0 else "[red]"
            is_stop_loss = action_result['result'].get('is_stop_loss', False)
            reason = action_result.get('reason', 'Manual')
            
            # Show stop loss indicator if triggered
            sell_label = "[bold red]🔴 SELL[/bold red]"
            if is_stop_loss:
                sell_label = "[bold yellow]🛑 SELL (STOP LOSS)[/bold yellow]"
            
            action_table.add_row(sell_label, 
                               f"{action_result['result'].get('quantity', 0)} units @ ₹{current_price:.2f} | PnL: {pnl_color}₹{pnl:.2f}[/{pnl_color}]")
            
            # Show stop loss details if applicable
            if is_stop_loss:
                stop_loss_price = action_result['result'].get('stop_loss_price', 0)
                entry_price = action_result['result'].get('entry_price', 0)
                action_table.add_row("", f"[yellow]Stop Loss: ₹{stop_loss_price:.2f} | Entry: ₹{entry_price:.2f} | Loss: ₹{abs(pnl):.2f}[/yellow]")
            
            conditions = self._build_conditions_string(output)
            action_table.add_row("", f"[dim]Reason: {reason}[/dim]")
            action_table.add_row("", f"[dim]Conditions: {conditions}[/dim]")
        else:
            # Show conditions even for HOLD actions
            conditions = self._build_conditions_string(output)
            action_table.add_row("[dim]⚪ HOLD[/dim]", action_result['reason'])
            if conditions and conditions != "No conditions met":
                action_table.add_row("", f"[dim]Conditions: {conditions}[/dim]")
        console.print(action_table)
        console.print()
    
    def run_once(self):
        """Run one iteration of the trading loop"""
        try:
            # Load data
            daily_df = load_daily()
            intraday_df, prices = load_intraday()
            # intraday_df, prices = next(intraday_stream)
            
            # Get current price
            current_price = self.get_current_price(intraday_df)
            
            if current_price == 0:
                logger.warning("Could not get current price, skipping iteration")
                return
            
            # Run inference (pass position status for RL agent)
            has_position = self.position_tracker.has_position()
            output = live_inference(daily_df, intraday_df, prices, has_position=has_position)
            signal = output["final_signal"]
            
            # Get RL agent action for immediate sell check
            intraday_models = output.get('intraday_models', {})
            rl_action = intraday_models.get('rl_intraday_action', 2)
            
            # Decide action (pass RL action for immediate sell logic)
            action_result = self.decide_action(signal, current_price, rl_action=rl_action)
            
            # Print status
            self.print_status(output, action_result, current_price, intraday_df)
            
            # Store last signal
            self.last_signal = signal
            
        except Exception as e:
            logger.error(f"Error in trading loop: {e}")
            import traceback
            traceback.print_exc()
    
    def run(self):
        """Start the real-time trading loop"""
        self.running = True
        logger.info(f"Starting real-time trading system (interval: {self.interval}s)")
        logger.info("Long-only strategy: BUY on signal=1, SELL on signal=-1, HOLD otherwise")
        logger.info("Press Ctrl+C to stop")
        
        try:
            while self.running:
                self.run_once()
                time.sleep(self.interval)
        except KeyboardInterrupt:
            logger.info("Stopping real-time trading system...")
            self.running = False
            
            # Print final status
            status = self.position_tracker.get_status()
            print("\n" + "="*70)
            print(" FINAL STATUS")
            print("="*70)
            print(f"Total Realized PnL: ₹{status['total_realized_pnl']:.2f}")
            print(f"Unrealized PnL: ₹{status['unrealized_pnl']:.2f}")
            print(f"Total PnL: ₹{status['total_pnl']:.2f}")
            print(f"Closed Trades: {status['closed_trades']}")
            if status['has_position']:
                print(f"⚠️  Active position: {status['quantity']} units @ ₹{status['entry_price']:.2f}")
            print("="*70 + "\n")
    
    def stop(self):
        """Stop the trading loop"""
        self.running = False


if __name__ == "__main__":
    # Initialize trader
    trader = RealTimeTrader(quantity=1, interval=5)
    
    # Start trading
    trader.run()

