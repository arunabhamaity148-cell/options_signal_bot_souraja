# strategy/htf_filter.py
"""
HTF (1 Hour) Trend Filter
The gatekeeper - decides if we can trade CALL, PUT, or nothing at all.

Logic:
- EMA 20 > EMA 50 → CALL bias only
- EMA 20 < EMA 50 → PUT bias only  
- Choppy/flat → NO TRADE

Why it works:
1. Institutional money moves on hourly timeframe
2. EMA crossovers = proven edge across all markets
3. Silence is a position - we avoid chop
"""

import pandas as pd
import numpy as np
from typing import Literal
from loguru import logger

BiasType = Literal['CALL_ONLY', 'PUT_ONLY', 'NO_TRADE']


class HTFTrendFilter:
    """
    1 Hour EMA filter - simple, robust, no curve-fitting
    """
    
    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.min_separation = 0.2  # 0.2% minimum
        self.alignment_candles = 3  # Must align for last 3 bars
        
    def calculate_emas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate EMAs on dataframe"""
        df = df.copy()
        df['ema_fast'] = df['close'].ewm(span=self.fast_period, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=self.slow_period, adjust=False).mean()
        return df
    
    def get_bias(self, df_1h: pd.DataFrame) -> BiasType:
        """
        Determine market bias from 1H chart
        
        Returns:
            'CALL_ONLY': Only look for call entries
            'PUT_ONLY': Only look for put entries  
            'NO_TRADE': Market is choppy/flat - stay out
        """
        
        if len(df_1h) < self.slow_period:
            logger.warning(f"Insufficient data: {len(df_1h)} candles, need {self.slow_period}")
            return 'NO_TRADE'
        
        df = self.calculate_emas(df_1h)
        current = df.iloc[-1]
        
        # Calculate separation percentage
        separation_pct = (
            (current['ema_fast'] - current['ema_slow']) / current['ema_slow'] * 100
        )
        
        # Determine bias
        if separation_pct > self.min_separation:
            bias = 'CALL_ONLY'
        elif separation_pct < -self.min_separation:
            bias = 'PUT_ONLY'
        else:
            bias = 'NO_TRADE'
        
        logger.info(
            f"HTF Bias: {bias} | "
            f"EMA Fast: {current['ema_fast']:.2f} | "
            f"EMA Slow: {current['ema_slow']:.2f} | "
            f"Separation: {separation_pct:.3f}%"
        )
        
        return bias
    
    def is_trend_strong(self, df_1h: pd.DataFrame, bias: BiasType) -> bool:
        """
        Check if trend is strong (not just a single candle crossover)
        
        Requirement: EMAs must be aligned for last N candles
        This prevents whipsaw entries during crossover zones
        
        Args:
            df_1h: 1 hour OHLCV data
            bias: Current bias from get_bias()
            
        Returns:
            True if trend is strong and aligned
        """
        
        if bias == 'NO_TRADE':
            return False
        
        if len(df_1h) < self.alignment_candles:
            return False
        
        df = self.calculate_emas(df_1h)
        last_n = df.tail(self.alignment_candles)
        
        if bias == 'CALL_ONLY':
            # All recent candles should have fast > slow
            aligned = all(last_n['ema_fast'] > last_n['ema_slow'])
            
        elif bias == 'PUT_ONLY':
            # All recent candles should have fast < slow
            aligned = all(last_n['ema_fast'] < last_n['ema_slow'])
        else:
            aligned = False
        
        logger.debug(f"Trend alignment check: {aligned} (last {self.alignment_candles} candles)")
        return aligned
    
    def get_trend_strength_score(self, df_1h: pd.DataFrame) -> float:
        """
        Calculate trend strength (0 to 100)
        
        Higher score = stronger trend
        Used for filtering weak setups
        
        Returns:
            0-30: Weak/choppy
            30-60: Moderate  
            60-100: Strong
        """
        
        if len(df_1h) < self.slow_period:
            return 0.0
        
        df = self.calculate_emas(df_1h)
        
        # Separation metric
        separation = abs(
            (df.iloc[-1]['ema_fast'] - df.iloc[-1]['ema_slow']) / 
            df.iloc[-1]['ema_slow'] * 100
        )
        
        # Alignment metric (last 5 candles)
        last_5 = df.tail(5)
        if len(last_5) == 5:
            alignment = sum(
                1 for i in range(len(last_5))
                if (last_5.iloc[i]['ema_fast'] > last_5.iloc[i]['ema_slow']) == 
                   (last_5.iloc[-1]['ema_fast'] > last_5.iloc[-1]['ema_slow'])
            ) / 5.0
        else:
            alignment = 0.0
        
        # Combined score
        # Separation contributes 60%, alignment 40%
        score = min(100, (separation * 10 * 0.6 + alignment * 100 * 0.4))
        
        logger.debug(f"Trend strength: {score:.1f}/100")
        return score
    
    def validate_for_entry(self, df_1h: pd.DataFrame) -> dict:
        """
        Complete validation before allowing any entry
        
        Returns dict with:
            - valid: bool
            - bias: BiasType
            - strength: float
            - reason: str
        """
        
        bias = self.get_bias(df_1h)
        
        if bias == 'NO_TRADE':
            return {
                'valid': False,
                'bias': bias,
                'strength': 0.0,
                'reason': 'Market choppy/flat - no clear trend'
            }
        
        strong = self.is_trend_strong(df_1h, bias)
        if not strong:
            return {
                'valid': False,
                'bias': bias,
                'strength': 0.0,
                'reason': 'Trend not aligned - possible whipsaw zone'
            }
        
        strength = self.get_trend_strength_score(df_1h)
        
        if strength < 30:
            return {
                'valid': False,
                'bias': bias,
                'strength': strength,
                'reason': f'Trend too weak ({strength:.1f}/100)'
            }
        
        return {
            'valid': True,
            'bias': bias,
            'strength': strength,
            'reason': f'Strong {bias.replace("_ONLY", "")} trend confirmed'
        }


# ==================== TESTING ====================
if __name__ == "__main__":
    # Test with dummy data
    
    dates = pd.date_range('2024-01-01', periods=100, freq='H')
    
    # Bullish trend data
    df_bull = pd.DataFrame({
        'datetime': dates,
        'open': np.linspace(18000, 19000, 100),
        'high': np.linspace(18050, 19050, 100),
        'low': np.linspace(17950, 18950, 100),
        'close': np.linspace(18000, 19000, 100),
        'volume': np.random.randint(100000, 500000, 100)
    })
    
    filter_obj = HTFTrendFilter()
    
    print("=" * 60)
    print("BULLISH TREND TEST")
    print("=" * 60)
    result = filter_obj.validate_for_entry(df_bull)
    print(f"Valid: {result['valid']}")
    print(f"Bias: {result['bias']}")
    print(f"Strength: {result['strength']:.1f}/100")
    print(f"Reason: {result['reason']}")
    
    # Bearish trend data
    df_bear = pd.DataFrame({
        'datetime': dates,
        'open': np.linspace(19000, 18000, 100),
        'high': np.linspace(19050, 18050, 100),
        'low': np.linspace(18950, 17950, 100),
        'close': np.linspace(19000, 18000, 100),
        'volume': np.random.randint(100000, 500000, 100)
    })
    
    print("\n" + "=" * 60)
    print("BEARISH TREND TEST")
    print("=" * 60)
    result = filter_obj.validate_for_entry(df_bear)
    print(f"Valid: {result['valid']}")
    print(f"Bias: {result['bias']}")
    print(f"Strength: {result['strength']:.1f}/100")
    print(f"Reason: {result['reason']}")
    
    # Choppy data
    df_chop = pd.DataFrame({
        'datetime': dates,
        'close': 18500 + np.random.randn(100) * 50,
        'open': 18500 + np.random.randn(100) * 50,
        'high': 18550 + np.random.randn(100) * 50,
        'low': 18450 + np.random.randn(100) * 50,
        'volume': np.random.randint(100000, 500000, 100)
    })
    
    print("\n" + "=" * 60)
    print("CHOPPY MARKET TEST")
    print("=" * 60)
    result = filter_obj.validate_for_entry(df_chop)
    print(f"Valid: {result['valid']}")
    print(f"Bias: {result['bias']}")
    print(f"Strength: {result['strength']:.1f}/100")
    print(f"Reason: {result['reason']}")
