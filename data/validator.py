# data/validator.py
"""
Data validation and quality checks
"""

import pandas as pd
import numpy as np
from loguru import logger
from typing import Dict, List


class DataValidator:
    """
    Validate OHLCV data quality
    """
    
    @staticmethod
    def validate_ohlcv(df: pd.DataFrame) -> Dict:
        """
        Check OHLCV data integrity
        
        Returns:
            {
                'valid': bool,
                'issues': List[str],
                'stats': dict
            }
        """
        
        issues = []
        
        # Check required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing = [col for col in required_cols if col not in df.columns]
        
        if missing:
            issues.append(f"Missing columns: {missing}")
            return {'valid': False, 'issues': issues, 'stats': {}}
        
        # Check for nulls
        null_counts = df[required_cols].isnull().sum()
        if null_counts.any():
            issues.append(f"Null values found: {null_counts[null_counts > 0].to_dict()}")
        
        # Check OHLC logic (High >= Low, etc.)
        invalid_hl = (df['high'] < df['low']).sum()
        if invalid_hl > 0:
            issues.append(f"{invalid_hl} candles with High < Low")
        
        invalid_hoc = ((df['high'] < df['open']) | (df['high'] < df['close'])).sum()
        if invalid_hoc > 0:
            issues.append(f"{invalid_hoc} candles with High < Open/Close")
        
        invalid_loc = ((df['low'] > df['open']) | (df['low'] > df['close'])).sum()
        if invalid_loc > 0:
            issues.append(f"{invalid_loc} candles with Low > Open/Close")
        
        # Check for zero volume
        zero_vol = (df['volume'] == 0).sum()
        if zero_vol > 0:
            issues.append(f"{zero_vol} candles with zero volume")
        
        # Check for negative values
        negative = (df[required_cols] < 0).any()
        if negative.any():
            issues.append(f"Negative values in: {negative[negative].index.tolist()}")
        
        # Check for outliers (sudden 10%+ jumps)
        df['close_pct_change'] = df['close'].pct_change()
        outliers = (abs(df['close_pct_change']) > 0.10).sum()
        if outliers > 0:
            issues.append(f"{outliers} candles with 10%+ price jump (possible data error)")
        
        # Stats
        stats = {
            'total_candles': len(df),
            'null_count': int(null_counts.sum()),
            'zero_volume_count': int(zero_vol),
            'outlier_count': int(outliers),
            'date_range': f"{df['datetime'].min()} to {df['datetime'].max()}" if 'datetime' in df.columns else 'N/A'
        }
        
        valid = len(issues) == 0
        
        if not valid:
            logger.warning(f"Data validation failed: {issues}")
        else:
            logger.info(f"✓ Data validation passed ({stats['total_candles']} candles)")
        
        return {
            'valid': valid,
            'issues': issues,
            'stats': stats
        }
    
    @staticmethod
    def check_liquidity(volume: int, oi: int, min_volume: int = 100, min_oi: int = 1000) -> Dict:
        """
        Check option liquidity
        
        Args:
            volume: Trading volume
            oi: Open Interest
            min_volume: Minimum acceptable volume
            min_oi: Minimum acceptable OI
            
        Returns:
            {
                'liquid': bool,
                'volume': int,
                'oi': int,
                'reason': str
            }
        """
        
        if volume < min_volume:
            return {
                'liquid': False,
                'volume': volume,
                'oi': oi,
                'reason': f'Low volume ({volume} < {min_volume})'
            }
        
        if oi < min_oi:
            return {
                'liquid': False,
                'volume': volume,
                'oi': oi,
                'reason': f'Low OI ({oi} < {min_oi})'
            }
        
        return {
            'liquid': True,
            'volume': volume,
            'oi': oi,
            'reason': 'Sufficient liquidity'
        }
    
    @staticmethod
    def check_bid_ask_spread(bid: float, ask: float, max_spread: float = 0.50) -> Dict:
        """
        Check bid-ask spread
        
        Args:
            bid: Bid price
            ask: Ask price
            max_spread: Maximum acceptable spread
            
        Returns:
            {
                'acceptable': bool,
                'spread': float,
                'spread_pct': float,
                'reason': str
            }
        """
        
        if bid <= 0 or ask <= 0:
            return {
                'acceptable': False,
                'spread': 0,
                'spread_pct': 0,
                'reason': 'Invalid bid/ask prices'
            }
        
        spread = ask - bid
        spread_pct = (spread / bid) * 100 if bid > 0 else 0
        
        if spread > max_spread:
            return {
                'acceptable': False,
                'spread': spread,
                'spread_pct': spread_pct,
                'reason': f'Spread too wide (₹{spread:.2f} > ₹{max_spread:.2f})'
            }
        
        return {
            'acceptable': True,
            'spread': spread,
            'spread_pct': spread_pct,
            'reason': 'Acceptable spread'
        }


if __name__ == "__main__":
    # Test with sample data
    
    # Good data
    df_good = pd.DataFrame({
        'datetime': pd.date_range('2024-01-01', periods=100, freq='5min'),
        'open': np.linspace(100, 110, 100),
        'high': np.linspace(101, 111, 100),
        'low': np.linspace(99, 109, 100),
        'close': np.linspace(100.5, 110.5, 100),
        'volume': np.random.randint(1000, 5000, 100)
    })
    
    validator = DataValidator()
    
    print("Testing good data:")
    result = validator.validate_ohlcv(df_good)
    print(f"Valid: {result['valid']}")
    print(f"Stats: {result['stats']}")
    
    # Bad data (High < Low)
    df_bad = df_good.copy()
    df_bad.loc[5, 'high'] = 95
    df_bad.loc[10, 'volume'] = 0
    
    print("\nTesting bad data:")
    result = validator.validate_ohlcv(df_bad)
    print(f"Valid: {result['valid']}")
    print(f"Issues: {result['issues']}")
    
    # Test liquidity
    print("\nTesting liquidity:")
    liq_check = validator.check_liquidity(volume=150, oi=2000)
    print(f"Liquid: {liq_check['liquid']} - {liq_check['reason']}")
    
    # Test spread
    print("\nTesting bid-ask spread:")
    spread_check = validator.check_bid_ask_spread(bid=100, ask=100.30)
    print(f"Acceptable: {spread_check['acceptable']} - {spread_check['reason']}")