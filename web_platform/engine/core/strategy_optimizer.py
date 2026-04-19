"""
Strategy Optimizer Module

Implements performance metrics and optimization:
1. Sharpe Ratio (Risk-adjusted returns)
2. Sortino Ratio (Downside risk focus)
3. Maximum Drawdown
4. Win Rate & Expectancy
5. Profit Factor
6. Recovery Factor
7. Parameter Optimization

Used to evaluate and optimize trading strategies.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from itertools import product


class StrategyOptimizer:
    """
    Strategy performance analysis and optimization.
    Calculates institutional-grade performance metrics.
    """
    
    def __init__(self, risk_free_rate: float = 0.05):
        """
        Initialize strategy optimizer.
        
        Args:
            risk_free_rate: Annual risk-free rate for Sharpe calculation (default 5%)
        """
        self.risk_free_rate = risk_free_rate
    
    def calculate_sharpe_ratio(self, 
                              returns: np.ndarray,
                              periods_per_year: int = 252) -> float:
        """
        Calculate Sharpe Ratio (risk-adjusted returns).
        
        Sharpe = (Mean Return - Risk Free Rate) / Std Dev of Returns
        
        Higher is better. >1.0 is good, >2.0 is excellent.
        
        Args:
            returns: Array of returns
            periods_per_year: Trading periods per year (252 for daily, adjust for intraday)
        
        Returns:
            Annualized Sharpe Ratio
        """
        if len(returns) < 2:
            return 0.0
        
        mean_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)
        
        if std_return == 0:
            return 0.0
        
        # Annualize
        annual_return = mean_return * periods_per_year
        annual_std = std_return * np.sqrt(periods_per_year)
        
        sharpe = (annual_return - self.risk_free_rate) / annual_std
        
        return float(sharpe)
    
    def calculate_sortino_ratio(self,
                               returns: np.ndarray,
                               periods_per_year: int = 252) -> float:
        """
        Calculate Sortino Ratio (focuses on downside risk).
        
        Similar to Sharpe but only considers downside volatility.
        Better measure for asymmetric returns.
        
        Args:
            returns: Array of returns
            periods_per_year: Trading periods per year
        
        Returns:
            Annualized Sortino Ratio
        """
        if len(returns) < 2:
            return 0.0
        
        mean_return = np.mean(returns)
        
        # Downside deviation (only negative returns)
        downside_returns = returns[returns < 0]
        
        if len(downside_returns) == 0:
            return float('inf')  # No downside = perfect
        
        downside_std = np.std(downside_returns, ddof=1)
        
        if downside_std == 0:
            return 0.0
        
        # Annualize
        annual_return = mean_return * periods_per_year
        annual_downside_std = downside_std * np.sqrt(periods_per_year)
        
        sortino = (annual_return - self.risk_free_rate) / annual_downside_std
        
        return float(sortino)
    
    def calculate_max_drawdown(self, equity_curve: np.ndarray) -> Dict:
        """
        Calculate Maximum Drawdown (worst peak-to-trough decline).
        
        Key risk metric. Lower is better.
        
        Args:
            equity_curve: Array of cumulative equity values
        
        Returns:
            Dictionary with drawdown metrics
        """
        if len(equity_curve) < 2:
            return {
                'max_drawdown': 0.0,
                'max_drawdown_pct': 0.0,
                'max_drawdown_duration': 0,
                'current_drawdown_pct': 0.0
            }
        
        # Calculate running maximum
        running_max = np.maximum.accumulate(equity_curve)
        
        # Calculate drawdowns
        drawdowns = equity_curve - running_max
        drawdown_pcts = (drawdowns / running_max) * 100
        
        # Maximum drawdown
        max_dd = np.min(drawdowns)
        max_dd_pct = np.min(drawdown_pcts)
        
        # Drawdown duration
        in_drawdown = drawdowns < 0
        if np.any(in_drawdown):
            # Find longest drawdown period
            drawdown_periods = []
            current_period = 0
            
            for is_dd in in_drawdown:
                if is_dd:
                    current_period += 1
                else:
                    if current_period > 0:
                        drawdown_periods.append(current_period)
                    current_period = 0
            
            if current_period > 0:
                drawdown_periods.append(current_period)
            
            max_dd_duration = max(drawdown_periods) if drawdown_periods else 0
        else:
            max_dd_duration = 0
        
        # Current drawdown
        current_dd_pct = drawdown_pcts[-1]
        
        return {
            'max_drawdown': float(max_dd),
            'max_drawdown_pct': float(max_dd_pct),
            'max_drawdown_duration': int(max_dd_duration),
            'current_drawdown_pct': float(current_dd_pct)
        }
    
    def calculate_win_rate(self, trades: pd.DataFrame) -> Dict:
        """
        Calculate win rate and related statistics.
        
        Args:
            trades: DataFrame with 'pnl' column
        
        Returns:
            Dictionary with win/loss statistics
        """
        if trades.empty or 'pnl' not in trades.columns:
            return {
                'win_rate': 0.0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
                'avg_win_loss_ratio': 0.0
            }
        
        total_trades = len(trades)
        winning_trades = len(trades[trades['pnl'] > 0])
        losing_trades = len(trades[trades['pnl'] < 0])
        
        win_rate = (winning_trades / total_trades) if total_trades > 0 else 0.0
        
        # Average win/loss
        wins = trades[trades['pnl'] > 0]['pnl']
        losses = trades[trades['pnl'] < 0]['pnl']
        
        avg_win = wins.mean() if len(wins) > 0 else 0.0
        avg_loss = losses.mean() if len(losses) > 0 else 0.0
        
        # Largest win/loss
        largest_win = wins.max() if len(wins) > 0 else 0.0
        largest_loss = losses.min() if len(losses) > 0 else 0.0
        
        # Win/Loss ratio
        avg_win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0.0
        
        return {
            'win_rate': float(win_rate),
            'total_trades': int(total_trades),
            'winning_trades': int(winning_trades),
            'losing_trades': int(losing_trades),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'largest_win': float(largest_win),
            'largest_loss': float(largest_loss),
            'avg_win_loss_ratio': float(avg_win_loss_ratio)
        }
    
    def calculate_expectancy(self, trades: pd.DataFrame) -> float:
        """
        Calculate expectancy (average profit per trade).
        
        Expectancy = (Win Rate * Avg Win) - (Loss Rate * Avg Loss)
        
        Positive expectancy = profitable system
        
        Args:
            trades: DataFrame with 'pnl' column
        
        Returns:
            Expectancy value
        """
        stats = self.calculate_win_rate(trades)
        
        win_rate = stats['win_rate']
        loss_rate = 1 - win_rate
        avg_win = stats['avg_win']
        avg_loss = abs(stats['avg_loss'])
        
        expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
        
        return float(expectancy)
    
    def calculate_profit_factor(self, trades: pd.DataFrame) -> float:
        """
        Calculate Profit Factor.
        
        Profit Factor = Gross Profit / Gross Loss
        
        >1.0 = profitable, >2.0 = excellent
        
        Args:
            trades: DataFrame with 'pnl' column
        
        Returns:
            Profit factor
        """
        if trades.empty or 'pnl' not in trades.columns:
            return 0.0
        
        gross_profit = trades[trades['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(trades[trades['pnl'] < 0]['pnl'].sum())
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        
        profit_factor = gross_profit / gross_loss
        
        return float(profit_factor)
    
    def calculate_recovery_factor(self, 
                                  total_pnl: float,
                                  max_drawdown: float) -> float:
        """
        Calculate Recovery Factor.
        
        Recovery Factor = Net Profit / Max Drawdown
        
        Higher is better. Measures ability to recover from drawdowns.
        
        Args:
            total_pnl: Total profit/loss
            max_drawdown: Maximum drawdown (absolute value)
        
        Returns:
            Recovery factor
        """
        if max_drawdown == 0:
            return float('inf') if total_pnl > 0 else 0.0
        
        recovery_factor = total_pnl / abs(max_drawdown)
        
        return float(recovery_factor)
    
    def calculate_calmar_ratio(self,
                              annual_return: float,
                              max_drawdown_pct: float) -> float:
        """
        Calculate Calmar Ratio.
        
        Calmar = Annual Return / Max Drawdown %
        
        Risk-adjusted return focusing on drawdown.
        
        Args:
            annual_return: Annualized return (as decimal)
            max_drawdown_pct: Max drawdown percentage
        
        Returns:
            Calmar ratio
        """
        if max_drawdown_pct == 0:
            return float('inf') if annual_return > 0 else 0.0
        
        calmar = annual_return / abs(max_drawdown_pct / 100)
        
        return float(calmar)
    
    def get_comprehensive_metrics(self,
                                 trades: pd.DataFrame,
                                 equity_curve: np.ndarray,
                                 initial_capital: float) -> Dict:
        """
        Calculate all performance metrics.
        
        Args:
            trades: DataFrame with trade history
            equity_curve: Array of equity values
            initial_capital: Starting capital
        
        Returns:
            Dictionary with all metrics
        """
        # Basic metrics
        total_pnl = equity_curve[-1] - initial_capital if len(equity_curve) > 0 else 0
        total_return_pct = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0
        
        # Calculate returns
        if len(equity_curve) > 1:
            returns = np.diff(equity_curve) / equity_curve[:-1]
        else:
            returns = np.array([])
        
        # Risk-adjusted metrics
        sharpe = self.calculate_sharpe_ratio(returns)
        sortino = self.calculate_sortino_ratio(returns)
        
        # Drawdown metrics
        dd_metrics = self.calculate_max_drawdown(equity_curve)
        
        # Trade statistics
        win_stats = self.calculate_win_rate(trades)
        
        # Profitability metrics
        expectancy = self.calculate_expectancy(trades)
        profit_factor = self.calculate_profit_factor(trades)
        recovery_factor = self.calculate_recovery_factor(
            total_pnl, dd_metrics['max_drawdown']
        )
        
        # Calmar ratio
        annual_return = total_return_pct  # Simplified, adjust if needed
        calmar = self.calculate_calmar_ratio(annual_return, dd_metrics['max_drawdown_pct'])
        
        return {
            # Basic
            'total_pnl': total_pnl,
            'total_return_pct': total_return_pct,
            'initial_capital': initial_capital,
            'final_capital': equity_curve[-1] if len(equity_curve) > 0 else initial_capital,
            
            # Risk-Adjusted
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'calmar_ratio': calmar,
            
            # Drawdown
            'max_drawdown': dd_metrics['max_drawdown'],
            'max_drawdown_pct': dd_metrics['max_drawdown_pct'],
            'max_drawdown_duration': dd_metrics['max_drawdown_duration'],
            'current_drawdown_pct': dd_metrics['current_drawdown_pct'],
            
            # Trade Stats
            'win_rate': win_stats['win_rate'],
            'total_trades': win_stats['total_trades'],
            'winning_trades': win_stats['winning_trades'],
            'losing_trades': win_stats['losing_trades'],
            'avg_win': win_stats['avg_win'],
            'avg_loss': win_stats['avg_loss'],
            'largest_win': win_stats['largest_win'],
            'largest_loss': win_stats['largest_loss'],
            'avg_win_loss_ratio': win_stats['avg_win_loss_ratio'],
            
            # Profitability
            'expectancy': expectancy,
            'profit_factor': profit_factor,
            'recovery_factor': recovery_factor
        }
    
    def optimize_parameters(self,
                          strategy_func,
                          data: pd.DataFrame,
                          param_grid: Dict[str, List],
                          initial_capital: float = 100000) -> Tuple[Dict, pd.DataFrame]:
        """
        Optimize strategy parameters using grid search.
        
        Args:
            strategy_func: Strategy function that takes (data, **params) and returns (trades, equity)
            data: Historical data
            param_grid: Dictionary of parameter name -> list of values
            initial_capital: Starting capital
        
        Returns:
            (best_params, results_df)
        """
        # Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        param_combinations = list(product(*param_values))
        
        results = []
        
        print(f"Testing {len(param_combinations)} parameter combinations...")
        
        for i, param_vals in enumerate(param_combinations):
            params = dict(zip(param_names, param_vals))
            
            try:
                # Run strategy with these parameters
                trades, equity = strategy_func(data, **params)
                
                # Calculate metrics
                metrics = self.get_comprehensive_metrics(trades, equity, initial_capital)
                
                # Store results
                result = {**params, **metrics}
                results.append(result)
                
                if (i + 1) % 10 == 0:
                    print(f"  Tested {i+1}/{len(param_combinations)} combinations")
                
            except Exception as e:
                print(f"  Error with params {params}: {e}")
                continue
        
        # Convert to DataFrame
        results_df = pd.DataFrame(results)
        
        if results_df.empty:
            print("No valid results found!")
            return {}, results_df
        
        # Find best parameters (by Sharpe Ratio)
        best_idx = results_df['sharpe_ratio'].idxmax()
        best_params = {param: results_df.loc[best_idx, param] for param in param_names}
        
        print(f"\n✅ Optimization complete!")
        print(f"Best Sharpe Ratio: {results_df.loc[best_idx, 'sharpe_ratio']:.3f}")
        print(f"Best Parameters: {best_params}")
        
        return best_params, results_df
