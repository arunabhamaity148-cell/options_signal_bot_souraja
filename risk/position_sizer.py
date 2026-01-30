"""
Risk management and position sizing module
"""
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd

from config.settings import settings
from database.models import db, TradingStats

logger = logging.getLogger(__name__)


class RiskManager:
    """Manage trading risk and position sizing"""
    
    def __init__(self):
        self.account_balance = 10000.0
        
    async def check_daily_limits(self) -> Tuple[bool, str]:
        """Check if daily trading limits are reached"""
        today = datetime.utcnow().date()
        
        query = """
            SELECT total_signals, consecutive_losses, is_paused, pause_reason
            FROM trading_stats
            WHERE DATE(date) = $1
        """
        
        stats = await db.execute_one(query, today)
        
        if not stats:
            return True, "OK"
        
        if stats['is_paused']:
            return False, f"Trading paused: {stats['pause_reason']}"
        
        if stats['total_signals'] >= settings.MAX_DAILY_SIGNALS:
            return False, f"Daily signal limit reached ({settings.MAX_DAILY_SIGNALS})"
        
        if stats['consecutive_losses'] >= settings.CONSECUTIVE_LOSS_PAUSE:
            return False, f"Consecutive losses limit ({settings.CONSECUTIVE_LOSS_PAUSE})"
        
        return True, "OK"
    
    async def update_daily_stats(self, signal_generated: bool = False,
                                 signal_result: Optional[str] = None):
        """Update daily trading statistics"""
        today = datetime.utcnow().date()
        
        query = """
            INSERT INTO trading_stats (date, total_signals, signals_taken)
            VALUES ($1, 0, 0)
            ON CONFLICT (date) DO NOTHING
        """
        await db.execute(query, today)
        
        if signal_generated:
            query = """
                UPDATE trading_stats
                SET total_signals = total_signals + 1,
                    updated_at = NOW()
                WHERE DATE(date) = $1
            """
            await db.execute(query, today)
        
        if signal_result == 'win':
            query = """
                UPDATE trading_stats
                SET wins = wins + 1,
                    consecutive_losses = 0,
                    updated_at = NOW()
                WHERE DATE(date) = $1
            """
            await db.execute(query, today)
            
        elif signal_result == 'loss':
            query = """
                UPDATE trading_stats
                SET losses = losses + 1,
                    consecutive_losses = consecutive_losses + 1,
                    updated_at = NOW()
                WHERE DATE(date) = $1
                RETURNING consecutive_losses
            """
            result = await db.execute_one(query, today)
            
            if result and result['consecutive_losses'] >= settings.CONSECUTIVE_LOSS_PAUSE:
                await self.pause_trading(
                    f"{settings.CONSECUTIVE_LOSS_PAUSE} consecutive losses",
                    hours=settings.PAUSE_DURATION_HOURS
                )
    
    async def pause_trading(self, reason: str, hours: int = 24):
        """Pause trading for specified duration"""
        today = datetime.utcnow().date()
        
        query = """
            UPDATE trading_stats
            SET is_paused = TRUE,
                pause_reason = $2,
                updated_at = NOW()
            WHERE DATE(date) = $1
        """
        await db.execute(query, today, reason)
        
        logger.warning(f"Trading paused for {hours}h: {reason}")
    
    def calculate_position_size(self, entry_price: float, 
                               stop_loss: float) -> Dict[str, float]:
        """Calculate position size based on risk parameters"""
        risk_amount = self.account_balance * settings.RISK_PER_TRADE
        
        risk_per_unit = abs(entry_price - stop_loss)
        
        if risk_per_unit == 0:
            logger.error("Invalid stop loss - same as entry price")
            return {}
        
        position_size = risk_amount / risk_per_unit
        position_value = position_size * entry_price
        
        return {
            'position_size': position_size,
            'position_value': position_value,
            'risk_amount': risk_amount,
            'risk_per_unit': risk_per_unit,
            'risk_percent': settings.RISK_PER_TRADE * 100
        }
    
    def calculate_take_profits(self, entry_price: float, 
                              stop_loss: float,
                              direction: str) -> Dict[str, float]:
        """Calculate take profit levels based on R:R ratio"""
        risk = abs(entry_price - stop_loss)
        
        if direction.startswith('LONG'):
            tp1 = entry_price + (risk * 2.0)
            tp2 = entry_price + (risk * 3.0)
            tp3 = entry_price + (risk * 4.0)
        else:
            tp1 = entry_price - (risk * 2.0)
            tp2 = entry_price - (risk * 3.0)
            tp3 = entry_price - (risk * 4.0)
        
        return {
            'tp1': tp1,
            'tp2': tp2,
            'tp3': tp3,
            'tp1_percent': 50,
            'tp2_percent': 30,
            'tp3_percent': 20
        }
    
    def validate_risk_reward(self, entry_price: float,
                            stop_loss: float,
                            take_profit: float) -> bool:
        """Validate if risk:reward ratio meets minimum requirement"""
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        
        if risk == 0:
            return False
        
        risk_reward = reward / risk
        
        return risk_reward >= settings.MIN_RISK_REWARD
    
    async def get_performance_metrics(self, days: int = 30) -> Dict:
        """Calculate performance metrics"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = """
            SELECT 
                SUM(wins) as total_wins,
                SUM(losses) as total_losses,
                SUM(total_signals) as total_signals,
                AVG(win_rate) as avg_win_rate,
                AVG(profit_factor) as avg_profit_factor,
                MAX(max_drawdown) as max_drawdown
            FROM trading_stats
            WHERE date >= $1
        """
        
        metrics = await db.execute_one(query, start_date)
        
        if not metrics:
            return self._empty_metrics()
        
        total_trades = (metrics['total_wins'] or 0) + (metrics['total_losses'] or 0)
        
        return {
            'total_signals': metrics['total_signals'] or 0,
            'total_trades': total_trades,
            'wins': metrics['total_wins'] or 0,
            'losses': metrics['total_losses'] or 0,
            'win_rate': (metrics['total_wins'] / total_trades * 100) if total_trades > 0 else 0,
            'avg_profit_factor': metrics['avg_profit_factor'] or 0,
            'max_drawdown': metrics['max_drawdown'] or 0,
            'period_days': days
        }
    
    def _empty_metrics(self) -> Dict:
        """Return empty metrics dictionary"""
        return {
            'total_signals': 0,
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0,
            'avg_profit_factor': 0,
            'max_drawdown': 0,
            'period_days': 0
        }
    
    def set_account_balance(self, balance: float):
        """Set account balance for position sizing"""
        self.account_balance = balance
        logger.info(f"Account balance set to ${balance:,.2f}")


risk_manager = RiskManager()
