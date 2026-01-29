# strategy/ltf_entry.py
"""
LTF (5 Minute) Entry Logic
Precise, structure-based entries with volume confirmation

Two proven patterns:
1. EMA Pullback - institutions adding to positions
2. Structure Break - momentum confirmation

Clean candle-close based logic - no prediction, no gambling
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from loguru import logger


class LTFEntry:
    """
    5-minute entry patterns with institutional footprints
    """
    
    def __init__(self, 
                 ema_period: int = 9,
                 volume_lookback: int = 20,
                 structure_lookback: int = 10):
        
        self.ema_period = ema_period
        self.volume_lookback = volume_lookback
        self.structure_lookback = structure_lookback
        
    def _calculate_ema(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add EMA to dataframe"""
        df = df.copy()
        df['ema'] = df['close'].ewm(span=self.ema_period, adjust=False).mean()
        return df
    
    def _get_avg_volume(self, df: pd.DataFrame) -> float:
        """Calculate average volume over lookback period"""
        if len(df) < self.volume_lookback:
            return df['volume'].mean()
        return df['volume'].tail(self.volume_lookback).mean()
    
    def check_pullback_entry(self, 
                            df_5m: pd.DataFrame, 
                            bias: str) -> Dict[str, Optional[float]]:
        """
        EMA Pullback Entry Pattern
        
        Logic:
        1. Price pulls back to 9 EMA (smart money adding)
        2. Next candle closes back in trend direction
        3. Volume >= average (real money, not noise)
        4. Candle closes beyond EMA (commitment)
        
        This is how institutions scale into positions.
        
        Returns:
            {
                'valid': bool,
                'pattern': str,
                'entry_price': float,
                'ema_level': float,
                'volume_ratio': float
            }
        """
        
        if len(df_5m) < self.ema_period + 2:
            return {'valid': False, 'pattern': None, 'entry_price': None}
        
        df = self._calculate_ema(df_5m)
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Volume validation
        avg_vol = self._get_avg_volume(df)
        volume_ratio = current['volume'] / avg_vol if avg_vol > 0 else 0
        
        if current['volume'] < avg_vol:
            logger.debug(f"Volume insufficient: {volume_ratio:.2f}x average")
            return {'valid': False, 'pattern': None, 'entry_price': None}
        
        # === CALL ENTRY ===
        if bias == 'CALL_ONLY':
            # Previous candle touched/went below EMA (pullback)
            pullback_occurred = prev['low'] <= prev['ema']
            
            # Current candle:
            # - Closed above EMA
            # - Bullish body (close > open)
            bullish_rejection = (
                current['close'] > current['ema'] and
                current['close'] > current['open']
            )
            
            if pullback_occurred and bullish_rejection:
                logger.info(
                    f"✓ CALL Pullback Pattern | "
                    f"Entry: {current['close']:.2f} | "
                    f"EMA: {current['ema']:.2f} | "
                    f"Volume: {volume_ratio:.2f}x"
                )
                
                return {
                    'valid': True,
                    'pattern': 'EMA_PULLBACK_CALL',
                    'entry_price': current['close'],
                    'ema_level': current['ema'],
                    'volume_ratio': volume_ratio
                }
        
        # === PUT ENTRY ===
        elif bias == 'PUT_ONLY':
            # Previous candle touched/went above EMA
            pullback_occurred = prev['high'] >= prev['ema']
            
            # Current candle:
            # - Closed below EMA
            # - Bearish body (close < open)
            bearish_rejection = (
                current['close'] < current['ema'] and
                current['close'] < current['open']
            )
            
            if pullback_occurred and bearish_rejection:
                logger.info(
                    f"✓ PUT Pullback Pattern | "
                    f"Entry: {current['close']:.2f} | "
                    f"EMA: {current['ema']:.2f} | "
                    f"Volume: {volume_ratio:.2f}x"
                )
                
                return {
                    'valid': True,
                    'pattern': 'EMA_PULLBACK_PUT',
                    'entry_price': current['close'],
                    'ema_level': current['ema'],
                    'volume_ratio': volume_ratio
                }
        
        return {'valid': False, 'pattern': None, 'entry_price': None}
    
    def check_structure_break(self, 
                             df_5m: pd.DataFrame, 
                             bias: str) -> Dict[str, Optional[float]]:
        """
        Structure Break Entry Pattern
        
        Logic:
        1. Identify recent swing high/low (last 10 candles)
        2. Price breaks structure with strong candle close
        3. Volume spike (1.2x average minimum)
        4. Directional body (no doji/indecision)
        
        Structure breaks = momentum confirmation
        Big volume = institutional validation
        
        Returns:
            {
                'valid': bool,
                'pattern': str,
                'entry_price': float,
                'structure_level': float,
                'volume_ratio': float
            }
        """
        
        if len(df_5m) < self.structure_lookback + 1:
            return {'valid': False, 'pattern': None, 'entry_price': None}
        
        df = df_5m.copy()
        current = df.iloc[-1]
        
        # Get structure level (exclude current candle)
        lookback = df.iloc[-(self.structure_lookback + 1):-1]
        
        # Volume must be strong for structure break
        avg_vol = self._get_avg_volume(df)
        volume_ratio = current['volume'] / avg_vol if avg_vol > 0 else 0
        
        if current['volume'] < avg_vol * 1.2:  # Need 20% above average
            logger.debug(f"Volume too weak for structure break: {volume_ratio:.2f}x")
            return {'valid': False, 'pattern': None, 'entry_price': None}
        
        # === CALL ENTRY ===
        if bias == 'CALL_ONLY':
            swing_high = lookback['high'].max()
            
            # Current candle must:
            # - Close above swing high
            # - Be bullish (close > open)
            # - Have conviction (not a wick break)
            
            structure_broken = current['close'] > swing_high
            bullish_body = current['close'] > current['open']
            clean_break = current['close'] > current['open']  # Directional
            
            if structure_broken and bullish_body and clean_break:
                logger.info(
                    f"✓ CALL Structure Break | "
                    f"Entry: {current['close']:.2f} | "
                    f"Broken Level: {swing_high:.2f} | "
                    f"Volume: {volume_ratio:.2f}x"
                )
                
                return {
                    'valid': True,
                    'pattern': 'STRUCTURE_BREAK_CALL',
                    'entry_price': current['close'],
                    'structure_level': swing_high,
                    'volume_ratio': volume_ratio
                }
        
        # === PUT ENTRY ===
        elif bias == 'PUT_ONLY':
            swing_low = lookback['low'].min()
            
            structure_broken = current['close'] < swing_low
            bearish_body = current['close'] < current['open']
            clean_break = current['close'] < current['open']
            
            if structure_broken and bearish_body and clean_break:
                logger.info(
                    f"✓ PUT Structure Break | "
                    f"Entry: {current['close']:.2f} | "
                    f"Broken Level: {swing_low:.2f} | "
                    f"Volume: {volume_ratio:.2f}x"
                )
                
                return {
                    'valid': True,
                    'pattern': 'STRUCTURE_BREAK_PUT',
                    'entry_price': current['close'],
                    'structure_level': swing_low,
                    'volume_ratio': volume_ratio
                }
        
        return {'valid': False, 'pattern': None, 'entry_price': None}
    
    def find_best_entry(self, 
                       df_5m: pd.DataFrame, 
                       bias: str) -> Dict:
        """
        Check both patterns and return the best one
        
        Priority:
        1. Structure break (stronger signal)
        2. Pullback (more common, also valid)
        
        Returns best entry or None
        """
        
        # Check structure break first (stronger)
        structure_entry = self.check_structure_break(df_5m, bias)
        if structure_entry['valid']:
            return structure_entry
        
        # Check pullback
        pullback_entry = self.check_pullback_entry(df_5m, bias)
        if pullback_entry['valid']:
            return pullback_entry
        
        # No valid entry
        logger.debug("No valid entry pattern found on 5m")
        return {'valid': False, 'pattern': None, 'entry_price': None}


# ==================== TESTING ====================
if __name__ == "__main__":
    
    # Test data - simulating a pullback scenario
    dates = pd.date_range('2024-01-01 09:15', periods=50, freq='5min')
    
    # Uptrend with pullback
    base = np.linspace(18000, 18200, 50)
    noise = np.random.randn(50) * 10
    
    df_test = pd.DataFrame({
        'datetime': dates,
        'open': base + noise,
        'high': base + noise + 20,
        'low': base + noise - 20,
        'close': base + noise + 5,
        'volume': np.random.randint(50000, 200000, 50)
    })
    
    # Simulate pullback in last candles
    df_test.loc[df_test.index[-3], 'close'] = 18150  # Pull back
    df_test.loc[df_test.index[-2], 'low'] = 18140    # Touch EMA
    df_test.loc[df_test.index[-1], 'close'] = 18180  # Bounce
    df_test.loc[df_test.index[-1], 'open'] = 18155
    df_test.loc[df_test.index[-1], 'volume'] = 180000  # Volume spike
    
    entry_finder = LTFEntry()
    
    print("=" * 60)
    print("TESTING CALL PULLBACK PATTERN")
    print("=" * 60)
    
    result = entry_finder.find_best_entry(df_test, 'CALL_ONLY')
    
    print(f"\nValid Entry: {result.get('valid', False)}")
    if result.get('valid'):
        print(f"Pattern: {result['pattern']}")
        print(f"Entry Price: ₹{result['entry_price']:.2f}")
        print(f"Reference Level: ₹{result.get('ema_level', result.get('structure_level', 0)):.2f}")
        print(f"Volume Ratio: {result.get('volume_ratio', 0):.2f}x")
    
    # Test structure break
    df_test2 = df_test.copy()
    df_test2.loc[df_test2.index[-1], 'high'] = 18250
    df_test2.loc[df_test2.index[-1], 'close'] = 18240  # Break high
    df_test2.loc[df_test2.index[-1], 'open'] = 18200
    df_test2.loc[df_test2.index[-1], 'volume'] = 250000  # Strong volume
    
    print("\n" + "=" * 60)
    print("TESTING CALL STRUCTURE BREAK PATTERN")
    print("=" * 60)
    
    result2 = entry_finder.find_best_entry(df_test2, 'CALL_ONLY')
    
    print(f"\nValid Entry: {result2.get('valid', False)}")
    if result2.get('valid'):
        print(f"Pattern: {result2['pattern']}")
        print(f"Entry Price: ₹{result2['entry_price']:.2f}")
        print(f"Broken Level: ₹{result2.get('structure_level', 0):.2f}")
        print(f"Volume Ratio: {result2.get('volume_ratio', 0):.2f}x")
