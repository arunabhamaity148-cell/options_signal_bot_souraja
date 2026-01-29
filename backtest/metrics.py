# backtest/metrics.py
"""
Performance metrics calculation
"""

import pandas as pd
import numpy as np
from typing import Dict


class BacktestMetrics:
    """
    Calculate trading performance metrics
    """
    
    @staticmethod
    def calculate_metrics(trades_df: pd.DataFrame) -> Dict:
        """
        Calculate comprehensive metrics from trades
        
        Args:
            trades_df: DataFrame with trade results
                Required columns: ['pnl', 'entry_time', 'exit_time']
        
        Returns:
            Dictionary of metrics
        """
        
        if trades_df.empty:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'total_pnl': 0.0
            }
        
        # Basic counts
        total_trades = len(trades_df)
        wins = trades_df[trades_df['pnl'] > 0]
        losses = trades_df[trades_df['pnl'] < 0]
        
        win_count = len(wins)
        loss_count = len(losses)
        
        # Win rate
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
        
        # P&L metrics
        total_pnl = trades_df['pnl'].sum()
        avg_pnl = trades_df['pnl'].mean()
        
        total_wins = wins['pnl'].sum() if not wins.empty else 0
        total_losses = abs(losses['pnl'].sum()) if not losses.empty else 0
        
        avg_win = wins['pnl'].mean() if not wins.empty else 0
        avg_loss = abs(losses['pnl'].mean()) if not losses.empty else 0
        
        # Profit factor
        profit_factor = (total_wins / total_losses) if total_losses > 0 else 0
        
        # Max drawdown
        cumulative = trades_df['pnl'].cumsum()
        running_max = cumulative.cummax()
        drawdown = running_max - cumulative
        max_drawdown = drawdown.max()
        max_drawdown_pct = (max_drawdown / running_max.max() * 100) if running_max.max() > 0 else 0
        
        # Consecutive wins/losses
        trades_df['win'] = trades_df['pnl'] > 0
        trades_df['streak'] = (trades_df['win'] != trades_df['win'].shift()).cumsum()
        streaks = trades_df.groupby('streak')['win'].agg(['sum', 'count'])
        
        max_consecutive_wins = streaks[streaks.index.isin(trades_df[trades_df['win']]['streak'])]['count'].max() if not wins.empty else 0
        max_consecutive_losses = streaks[streaks.index.isin(trades_df[~trades_df['win']]['streak'])]['count'].max() if not losses.empty else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': win_count,
            'losing_trades': loss_count,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'total_wins': total_wins,
            'total_losses': total_losses,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown_pct,
            'max_consecutive_wins': int(max_consecutive_wins) if not pd.isna(max_consecutive_wins) else 0,
            'max_consecutive_losses': int(max_consecutive_losses) if not pd.isna(max_consecutive_losses) else 0
        }
    
    @staticmethod
    def print_metrics(metrics: Dict):
        """Pretty print metrics"""
        
        print("\n" + "=" * 60)
        print("BACKTEST PERFORMANCE METRICS")
        print("=" * 60)
        
        print(f"\nTrade Statistics:")
        print(f"  Total Trades: {metrics['total_trades']}")
        print(f"  Winning Trades: {metrics['winning_trades']}")
        print(f"  Losing Trades: {metrics['losing_trades']}")
        print(f"  Win Rate: {metrics['win_rate']:.2f}%")
        
        print(f"\nP&L Metrics:")
        print(f"  Total P&L: ₹{metrics['total_pnl']:.2f}")
        print(f"  Average P&L: ₹{metrics['avg_pnl']:.2f}")
        print(f"  Average Win: ₹{metrics['avg_win']:.2f}")
        print(f"  Average Loss: ₹{metrics['avg_loss']:.2f}")
        
        print(f"\nRisk Metrics:")
        print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"  Max Drawdown: ₹{metrics['max_drawdown']:.2f} ({metrics['max_drawdown_pct']:.2f}%)")
        print(f"  Max Consecutive Wins: {metrics['max_consecutive_wins']}")
        print(f"  Max Consecutive Losses: {metrics['max_consecutive_losses']}")
        
        print("=" * 60 + "\n")


if __name__ == "__main__":
    # Test with sample trades
    trades = pd.DataFrame({
        'pnl': [500, -300, 600, -200, 400, -250, 550],
        'entry_time': pd.date_range('2024-01-01', periods=7, freq='D'),
        'exit_time': pd.date_range('2024-01-01 15:00', periods=7, freq='D')
    })
    
    metrics_calc = BacktestMetrics()
    metrics = metrics_calc.calculate_metrics(trades)
    metrics_calc.print_metrics(metrics)