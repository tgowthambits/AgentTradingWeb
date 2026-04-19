"""
Metrics Calculator Module

Calculates trading performance metrics from order data.
"""

import pandas as pd
import numpy as np
import re
from typing import Dict, Any, List, Optional


def categorize_drop_percentage(exit_reason: str) -> str:
    """
    Categorize 'Drop in percentage' exit reasons into meaningful ranges.
    
    Instead of showing exact values like "Drop in percentage: 2.51% drop from peak profit (4.90% → 2.39%)",
    this function groups them into 1% increment categories:
    - 0-1%: Very small drop
    - 1-2%: Small drop
    - 2-3%: Medium drop
    - 3-4%: Large drop
    - 4-5%: Very large drop
    - 5%+: Extreme drop
    
    Args:
        exit_reason: The original exit reason string
    
    Returns:
        Categorized exit reason string, or original if not a drop percentage reason
    """
    if not exit_reason or pd.isna(exit_reason):
        return "Unknown"
    
    # Check if this is a "Drop in percentage" exit reason
    # Pattern: "Drop in percentage: X.XX% drop from peak profit (Y.YY% → Z.ZZ%)"
    drop_pattern = r'Drop in percentage:\s*([\d.]+)%\s*drop from peak profit'
    match = re.search(drop_pattern, str(exit_reason))
    
    if match:
        try:
            drop_value = float(match.group(1))
            
            # Categorize based on 1% increment ranges
            if drop_value < 1.0:
                return "Drop: 0-1%"
            elif drop_value < 2.0:
                return "Drop: 1-2%"
            elif drop_value < 3.0:
                return "Drop: 2-3%"
            elif drop_value < 4.0:
                return "Drop: 3-4%"
            elif drop_value < 5.0:
                return "Drop: 4-5%"
            else:
                return "Drop: 5%+"
        except (ValueError, TypeError):
            return exit_reason
    
    # Check for "Profit drop protection" similar pattern
    profit_drop_pattern = r'Profit drop protection:\s*([\d.]+)%\s*drop from max profit'
    match = re.search(profit_drop_pattern, str(exit_reason))
    
    if match:
        try:
            drop_value = float(match.group(1))
            
            # Categorize based on 1% increment ranges
            if drop_value < 1.0:
                return "Profit Drop: 0-1%"
            elif drop_value < 2.0:
                return "Profit Drop: 1-2%"
            elif drop_value < 3.0:
                return "Profit Drop: 2-3%"
            elif drop_value < 4.0:
                return "Profit Drop: 3-4%"
            elif drop_value < 5.0:
                return "Profit Drop: 4-5%"
            else:
                return "Profit Drop: 5%+"
        except (ValueError, TypeError):
            return exit_reason
    
    # Return original reason for non-drop exits
    return exit_reason


class MetricsCalculator:
    """
    Calculates comprehensive trading performance metrics.
    
    This class provides methods to calculate:
    - Overall performance metrics (PnL, return %, win rate)
    - Risk-adjusted returns (Sharpe, Sortino, Calmar ratios)
    - Drawdown analysis
    - Per-symbol performance breakdown
    
    Attributes:
        initial_capital: Starting capital for calculations
    """
    
    def __init__(self, initial_capital: float = 20000.0):
        """
        Initialize the MetricsCalculator.
        
        Args:
            initial_capital: Starting capital for performance calculations
        """
        self.initial_capital = initial_capital
    
    def set_initial_capital(self, capital: float):
        """
        Set the initial capital.
        
        Args:
            capital: Initial capital value
        """
        self.initial_capital = capital
    
    def calculate_metrics(
        self,
        closed_orders: pd.DataFrame,
        initial_capital: float = None
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive metrics from closed orders.
        
        Args:
            closed_orders: DataFrame with closed order data (must have 'pnl' column)
            initial_capital: Override initial capital (uses instance value if None)
        
        Returns:
            Dictionary with formatted metric strings
        """
        if initial_capital is None:
            initial_capital = self.initial_capital
        
        if closed_orders.empty:
            return {}
        
        total_trades = len(closed_orders)
        wins = closed_orders[closed_orders['pnl'] > 0]
        losses = closed_orders[closed_orders['pnl'] < 0]
        
        total_pnl = closed_orders['pnl'].sum()
        current_capital = initial_capital + total_pnl
        return_pct = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0
        
        win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
        avg_win = wins['pnl'].mean() if len(wins) > 0 else 0
        avg_loss = losses['pnl'].mean() if len(losses) > 0 else 0
        largest_win = wins['pnl'].max() if len(wins) > 0 else 0
        largest_loss = losses['pnl'].min() if len(losses) > 0 else 0
        
        # Profit factor
        profit_factor = abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 and losses['pnl'].sum() != 0 else 0
        
        # Expectancy
        expectancy = (avg_win * (len(wins) / total_trades) + avg_loss * (len(losses) / total_trades)) if total_trades > 0 else 0
        
        # Sharpe Ratio (simplified, annualized)
        returns = closed_orders['pnl'] / initial_capital if initial_capital > 0 else closed_orders['pnl']
        sharpe_ratio = (returns.mean() / returns.std() * (252 ** 0.5)) if len(returns) > 1 and returns.std() > 0 else 0
        
        # Max Drawdown
        cumulative = (initial_capital + closed_orders['pnl'].cumsum()).values
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max * 100
        max_drawdown = drawdown.min() if len(drawdown) > 0 else 0
        
        # Sortino Ratio (downside deviation)
        downside_returns = returns[returns < 0]
        sortino_ratio = (returns.mean() / downside_returns.std() * (252 ** 0.5)) if len(downside_returns) > 1 and downside_returns.std() > 0 else 0
        
        # Calmar Ratio
        calmar_ratio = (return_pct / abs(max_drawdown)) if max_drawdown != 0 else 0
        
        return {
            "Initial Capital": f"₹{initial_capital:,.2f}",
            "Current Capital": f"₹{current_capital:,.2f}",
            "Total PnL": f"₹{total_pnl:,.2f}",
            "Return %": f"{return_pct:.2f}%",
            "Total Trades": total_trades,
            "Win Rate": f"{win_rate:.2f}%",
            "Average Win": f"₹{avg_win:,.2f}",
            "Average Loss": f"₹{avg_loss:,.2f}",
            "Largest Win": f"₹{largest_win:,.2f}",
            "Largest Loss": f"₹{largest_loss:,.2f}",
            "Profit Factor": f"{profit_factor:.2f}",
            "Expectancy": f"₹{expectancy:,.2f}",
            "Sharpe Ratio": f"{sharpe_ratio:.2f}",
            "Max Drawdown": f"{max_drawdown:.2f}%",
            "Sortino Ratio": f"{sortino_ratio:.2f}",
            "Calmar Ratio": f"{calmar_ratio:.2f}",
            "Total Signals": "N/A",
            "Trades Executed": total_trades,
            "Trades Skipped": "N/A"
        }
    
    def calculate_raw_metrics(
        self,
        closed_orders: pd.DataFrame,
        initial_capital: float = None
    ) -> Dict[str, Any]:
        """
        Calculate metrics as raw numeric values (not formatted strings).
        
        Args:
            closed_orders: DataFrame with closed order data
            initial_capital: Override initial capital
        
        Returns:
            Dictionary with raw metric values
        """
        if initial_capital is None:
            initial_capital = self.initial_capital
        
        if closed_orders.empty:
            return {
                'total_trades': 0,
                'total_pnl': 0.0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0
            }
        
        total_trades = len(closed_orders)
        wins = closed_orders[closed_orders['pnl'] > 0]
        losses = closed_orders[closed_orders['pnl'] < 0]
        
        total_pnl = closed_orders['pnl'].sum()
        current_capital = initial_capital + total_pnl
        return_pct = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0
        
        win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
        avg_win = wins['pnl'].mean() if len(wins) > 0 else 0
        avg_loss = losses['pnl'].mean() if len(losses) > 0 else 0
        largest_win = wins['pnl'].max() if len(wins) > 0 else 0
        largest_loss = losses['pnl'].min() if len(losses) > 0 else 0
        
        profit_factor = abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 and losses['pnl'].sum() != 0 else 0
        expectancy = (avg_win * (len(wins) / total_trades) + avg_loss * (len(losses) / total_trades)) if total_trades > 0 else 0
        
        # Risk metrics
        returns = closed_orders['pnl'] / initial_capital if initial_capital > 0 else closed_orders['pnl']
        sharpe_ratio = (returns.mean() / returns.std() * (252 ** 0.5)) if len(returns) > 1 and returns.std() > 0 else 0
        
        cumulative = (initial_capital + closed_orders['pnl'].cumsum()).values
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max * 100
        max_drawdown = drawdown.min() if len(drawdown) > 0 else 0
        
        downside_returns = returns[returns < 0]
        sortino_ratio = (returns.mean() / downside_returns.std() * (252 ** 0.5)) if len(downside_returns) > 1 and downside_returns.std() > 0 else 0
        
        calmar_ratio = (return_pct / abs(max_drawdown)) if max_drawdown != 0 else 0
        
        return {
            'initial_capital': initial_capital,
            'current_capital': current_capital,
            'total_pnl': total_pnl,
            'return_pct': return_pct,
            'total_trades': total_trades,
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'profit_factor': profit_factor,
            'expectancy': expectancy,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'max_drawdown': max_drawdown
        }
    
    def calculate_per_symbol_metrics(self, closed_orders: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        Calculate per-symbol trading metrics.
        
        Args:
            closed_orders: DataFrame with closed orders (must have 'symbol' and 'pnl' columns)
        
        Returns:
            Dictionary mapping symbols to their metrics
        """
        if closed_orders.empty or 'symbol' not in closed_orders.columns:
            return {}
        
        symbol_metrics = {}
        
        for symbol in closed_orders['symbol'].unique():
            symbol_orders = closed_orders[closed_orders['symbol'] == symbol]
            
            # Filter real trades (exclude paper trades if column exists)
            if 'paper_trade' in symbol_orders.columns:
                real_trades = symbol_orders[~symbol_orders['paper_trade'].fillna(False)]
                paper_trades = symbol_orders[symbol_orders['paper_trade'].fillna(False)]
            else:
                real_trades = symbol_orders
                paper_trades = pd.DataFrame()
            
            total_orders = len(real_trades)
            if total_orders == 0:
                continue
            
            wins = real_trades[real_trades['pnl'] > 0]
            losses = real_trades[real_trades['pnl'] < 0]
            
            total_pnl = real_trades['pnl'].sum()
            profit_orders = len(wins)
            loss_orders = len(losses)
            win_rate = (profit_orders / total_orders * 100) if total_orders > 0 else 0
            
            avg_win = wins['pnl'].mean() if len(wins) > 0 else 0
            avg_loss = losses['pnl'].mean() if len(losses) > 0 else 0
            largest_win = wins['pnl'].max() if len(wins) > 0 else 0
            largest_loss = losses['pnl'].min() if len(losses) > 0 else 0
            
            # Profit factor
            total_wins = wins['pnl'].sum() if len(wins) > 0 else 0
            total_losses = abs(losses['pnl'].sum()) if len(losses) > 0 else 0
            profit_factor = (total_wins / total_losses) if total_losses > 0 else 0
            
            # Expectancy
            expectancy = (avg_win * (profit_orders / total_orders) + avg_loss * (loss_orders / total_orders)) if total_orders > 0 else 0
            
            symbol_metrics[symbol] = {
                'total_orders': total_orders,
                'total_pnl': float(total_pnl),
                'profit_orders': profit_orders,
                'loss_orders': loss_orders,
                'win_rate': float(win_rate),
                'avg_win': float(avg_win),
                'avg_loss': float(avg_loss),
                'largest_win': float(largest_win),
                'largest_loss': float(largest_loss),
                'profit_factor': float(profit_factor),
                'expectancy': float(expectancy),
                'paper_trades': len(paper_trades),
                'real_trades': total_orders
            }
        
        # Sort by total PnL (descending)
        symbol_metrics = dict(sorted(symbol_metrics.items(), key=lambda x: x[1]['total_pnl'], reverse=True))
        
        return symbol_metrics
    
    def calculate_exit_reason_breakdown(self, closed_orders: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """
        Calculate breakdown of exit reasons with categorization.
        
        Drop percentage reasons are categorized into meaningful ranges:
        - Drop: Small (0-2%)
        - Drop: Medium (2-4%)
        - Drop: Large (4-6%)
        - Drop: Very Large (6%+)
        
        Args:
            closed_orders: DataFrame with closed orders (should have 'exit_reason' column)
        
        Returns:
            Dictionary with exit reason statistics
        """
        if closed_orders.empty or 'exit_reason' not in closed_orders.columns:
            return {}
        
        breakdown = {}
        total_trades = len(closed_orders)
        
        # Create a copy with categorized exit reasons
        df = closed_orders.copy()
        df['categorized_reason'] = df['exit_reason'].apply(categorize_drop_percentage)
        
        for reason in df['categorized_reason'].unique():
            if pd.isna(reason):
                reason = "Unknown"
            
            reason_orders = df[df['categorized_reason'] == reason]
            count = len(reason_orders)
            percentage = (count / total_trades * 100) if total_trades > 0 else 0
            total_pnl = reason_orders['pnl'].sum()
            avg_pnl = reason_orders['pnl'].mean()
            
            breakdown[reason] = {
                'count': count,
                'percentage': percentage,
                'total_pnl': total_pnl,
                'avg_pnl': avg_pnl
            }
        
        # Sort by count (descending)
        breakdown = dict(sorted(breakdown.items(), key=lambda x: x[1]['count'], reverse=True))
        
        return breakdown
    
    def calculate_drawdown_series(
        self,
        closed_orders: pd.DataFrame,
        initial_capital: float = None
    ) -> pd.DataFrame:
        """
        Calculate drawdown time series.
        
        Args:
            closed_orders: DataFrame with closed orders
            initial_capital: Initial capital for calculations
        
        Returns:
            DataFrame with equity and drawdown columns
        """
        if initial_capital is None:
            initial_capital = self.initial_capital
        
        if closed_orders.empty or 'pnl' not in closed_orders.columns:
            return pd.DataFrame(columns=['equity', 'drawdown', 'drawdown_pct'])
        
        cumulative_pnl = closed_orders['pnl'].cumsum()
        equity = initial_capital + cumulative_pnl
        
        running_max = equity.cummax()
        drawdown = equity - running_max
        drawdown_pct = (drawdown / running_max * 100)
        
        result = pd.DataFrame({
            'equity': equity.values,
            'drawdown': drawdown.values,
            'drawdown_pct': drawdown_pct.values
        })
        
        if 'exit_time' in closed_orders.columns:
            result.index = closed_orders['exit_time'].values
        
        return result
