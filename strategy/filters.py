# strategy/filters.py
"""
Signal Quality Filters
Final validation layer before signal generation

Filters out:
- Overextended RSI conditions
- Poor quality candles (wicks, doji)
- Wrong time windows
- Low conviction setups
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
import pytz
from typing import Tuple
from loguru import logger


class SignalFilters:
    """
    Quality control for entry signals
    """
    
    def __init__(self,
                 rsi_period: int = 14,
                 rsi_call_range: Tuple[int, int] = (45, 60),
                 rsi_put_range: Tuple[int, int] = (40, 55),
                 min_body_percent: float = 0.6,
                 max_wick_percent: float = 0.3):
        
        self.rsi_period = rsi_period
        self.rsi_call_min, self.rsi_call_max = rsi_call_range
        self.rsi_put_min, self.rsi_put_max = rsi_put_range
        self.min_body_percent = min_body_percent
        self.max_wick_percent = max_wick_percent
        
        # Trading hours (IST)
        self.trade_start = time(9, 20)
        self.trade_end = time(11, 30)
        self.timezone = pytz.timezone('Asia/Kolkata')
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate RSI (Relative Strength Index)
        
        Standard calculation:
        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss
        """
        
        delta = df['close'].diff()
        
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def check_rsi(self, df_5m: pd.DataFrame, bias: str) -> dict:
        """
        RSI Filter - avoid overbought/oversold exhaustion
        
        Why these ranges:
        - CALL (45-60): Strong but not exhausted
        - PUT (40-55): Strong but not exhausted
        
        We want momentum, not extremes
        
        Returns:
            {
                'valid': bool,
                'rsi_value': float,
                'reason': str
            }
        """
        
        if len(df_5m) < self.rsi_period + 1:
            return {
                'valid': False,
                'rsi_value': None,
                'reason': 'Insufficient data for RSI'
            }
        
        rsi = self.calculate_rsi(df_5m, self.rsi_period)
        current_rsi = rsi.iloc[-1]
        
        if pd.isna(current_rsi):
            return {
                'valid': False,
                'rsi_value': None,
                'reason': 'RSI calculation error'
            }
        
        # Check against bias-specific ranges
        if bias == 'CALL_ONLY':
            valid = self.rsi_call_min <= current_rsi <= self.rsi_call_max
            
            if not valid:
                if current_rsi < self.rsi_call_min:
                    reason = f'RSI too low ({current_rsi:.1f}) - momentum weak'
                else:
                    reason = f'RSI too high ({current_rsi:.1f}) - overbought'
            else:
                reason = f'RSI healthy ({current_rsi:.1f}) for CALL'
        
        elif bias == 'PUT_ONLY':
            valid = self.rsi_put_min <= current_rsi <= self.rsi_put_max
            
            if not valid:
                if current_rsi < self.rsi_put_min:
                    reason = f'RSI too low ({current_rsi:.1f}) - oversold'
                else:
                    reason = f'RSI too high ({current_rsi:.1f}) - momentum weak'
            else:
                reason = f'RSI healthy ({current_rsi:.1f}) for PUT'
        else:
            valid = False
            reason = 'No bias set'
        
        logger.debug(f"RSI Check: {reason}")
        
        return {
            'valid': valid,
            'rsi_value': current_rsi,
            'reason': reason
        }
    
    def check_candle_quality(self, df_5m: pd.DataFrame, bias: str) -> dict:
        """
        Candle Quality Filter
        
        Requirements:
        1. Body >= 60% of total range (conviction, not indecision)
        2. Wick against direction <= 30% of body (no rejection)
        
        Why:
        - Doji/spinning tops = indecision, avoid
        - Large opposing wick = rejection, not commitment
        - Strong body = conviction
        
        Returns:
            {
                'valid': bool,
                'body_percent': float,
                'wick_ratio': float,
                'reason': str
            }
        """
        
        current = df_5m.iloc[-1]
        
        # Calculate components
        total_range = current['high'] - current['low']
        body = abs(current['close'] - current['open'])
        
        if total_range == 0:
            return {
                'valid': False,
                'body_percent': 0,
                'wick_ratio': 0,
                'reason': 'Zero range candle (data issue)'
            }
        
        body_percent = body / total_range
        
        # Check body size
        if body_percent < self.min_body_percent:
            return {
                'valid': False,
                'body_percent': body_percent,
                'wick_ratio': None,
                'reason': f'Weak body ({body_percent*100:.1f}% of range) - indecision'
            }
        
        # Check wick against direction
        if bias == 'CALL_ONLY':
            # For bullish candle, check lower wick (rejection)
            if current['close'] > current['open']:
                lower_wick = current['open'] - current['low']
            else:
                lower_wick = current['close'] - current['low']
            
            wick_ratio = lower_wick / body if body > 0 else 0
            
            if wick_ratio > self.max_wick_percent:
                return {
                    'valid': False,
                    'body_percent': body_percent,
                    'wick_ratio': wick_ratio,
                    'reason': f'Lower wick too large ({wick_ratio*100:.1f}% of body) - rejection'
                }
        
        elif bias == 'PUT_ONLY':
            # For bearish candle, check upper wick
            if current['close'] < current['open']:
                upper_wick = current['high'] - current['open']
            else:
                upper_wick = current['high'] - current['close']
            
            wick_ratio = upper_wick / body if body > 0 else 0
            
            if wick_ratio > self.max_wick_percent:
                return {
                    'valid': False,
                    'body_percent': body_percent,
                    'wick_ratio': wick_ratio,
                    'reason': f'Upper wick too large ({wick_ratio*100:.1f}% of body) - rejection'
                }
        else:
            wick_ratio = 0
        
        return {
            'valid': True,
            'body_percent': body_percent,
            'wick_ratio': wick_ratio,
            'reason': f'Strong candle (body: {body_percent*100:.1f}%)'
        }
    
    def check_time_window(self, current_time: datetime = None) -> dict:
        """
        Time Window Filter
        
        Trading hours: 9:20 AM - 11:30 AM IST
        
        Why:
        - First 5 minutes (9:15-9:20): Volatile, wide spreads
        - Morning (9:20-11:30): Best liquidity + trending moves
        - Afternoon: Range-bound, low probability
        
        Returns:
            {
                'valid': bool,
                'current_time': str,
                'reason': str
            }
        """
        
        if current_time is None:
            current_time = datetime.now(self.timezone)
        elif current_time.tzinfo is None:
            current_time = self.timezone.localize(current_time)
        
        current_time_only = current_time.time()
        
        valid = self.trade_start <= current_time_only <= self.trade_end
        
        if valid:
            reason = f'Within trading window ({current_time_only.strftime("%H:%M")} IST)'
        else:
            if current_time_only < self.trade_start:
                reason = f'Too early ({current_time_only.strftime("%H:%M")}) - wait till 9:20 AM'
            else:
                reason = f'Too late ({current_time_only.strftime("%H:%M")}) - window closed at 11:30 AM'
        
        logger.debug(f"Time Check: {reason}")
        
        return {
            'valid': valid,
            'current_time': current_time_only.strftime("%H:%M:%S"),
            'reason': reason
        }
    
    def validate_all(self, 
                    df_5m: pd.DataFrame, 
                    bias: str,
                    current_time: datetime = None) -> dict:
        """
        Run all filters and return combined result
        
        All filters must pass for a valid signal
        
        Returns:
            {
                'valid': bool,
                'rsi': dict,
                'candle': dict,
                'time': dict,
                'failed_filters': list
            }
        """
        
        rsi_check = self.check_rsi(df_5m, bias)
        candle_check = self.check_candle_quality(df_5m, bias)
        time_check = self.check_time_window(current_time)
        
        failed_filters = []
        
        if not rsi_check['valid']:
            failed_filters.append('RSI')
        if not candle_check['valid']:
            failed_filters.append('Candle Quality')
        if not time_check['valid']:
            failed_filters.append('Time Window')
        
        all_valid = len(failed_filters) == 0
        
        if all_valid:
            logger.info("✓ All quality filters passed")
        else:
            logger.warning(f"✗ Failed filters: {', '.join(failed_filters)}")
        
        return {
            'valid': all_valid,
            'rsi': rsi_check,
            'candle': candle_check,
            'time': time_check,
            'failed_filters': failed_filters
        }


# ==================== TESTING ====================
if __name__ == "__main__":
    
    # Generate test data
    dates = pd.date_range('2024-01-01 09:00', periods=30, freq='5min')
    
    df_test = pd.DataFrame({
        'datetime': dates,
        'open': 18000 + np.random.randn(30) * 10,
        'high': 18020 + np.random.randn(30) * 10,
        'low': 17980 + np.random.randn(30) * 10,
        'close': 18010 + np.random.randn(30) * 10,
        'volume': np.random.randint(50000, 150000, 30)
    })
    
    # Make last candle strong bullish
    df_test.loc[df_test.index[-1], 'open'] = 18000
    df_test.loc[df_test.index[-1], 'close'] = 18040
    df_test.loc[df_test.index[-1], 'high'] = 18045
    df_test.loc[df_test.index[-1], 'low'] = 17995
    
    filters = SignalFilters()
    
    print("=" * 60)
    print("TESTING SIGNAL FILTERS")
    print("=" * 60)
    
    # Test time - within window
    test_time = datetime(2024, 1, 1, 10, 30, tzinfo=pytz.timezone('Asia/Kolkata'))
    
    result = filters.validate_all(df_test, 'CALL_ONLY', test_time)
    
    print(f"\nOverall Valid: {result['valid']}")
    print(f"\nRSI Check:")
    print(f"  Valid: {result['rsi']['valid']}")
    print(f"  Value: {result['rsi']['rsi_value']:.1f if result['rsi']['rsi_value'] else 'N/A'}")
    print(f"  Reason: {result['rsi']['reason']}")
    
    print(f"\nCandle Check:")
    print(f"  Valid: {result['candle']['valid']}")
    print(f"  Body%: {result['candle']['body_percent']*100:.1f}%")
    print(f"  Reason: {result['candle']['reason']}")
    
    print(f"\nTime Check:")
    print(f"  Valid: {result['time']['valid']}")
    print(f"  Time: {result['time']['current_time']}")
    print(f"  Reason: {result['time']['reason']}")
    
    if result['failed_filters']:
        print(f"\n⚠ Failed Filters: {', '.join(result['failed_filters'])}")
    else:
        print(f"\n✓ All filters passed - Signal ready")
