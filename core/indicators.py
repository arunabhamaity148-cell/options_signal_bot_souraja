"""
Technical indicators calculator using ta library
"""
import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import ta
from config.settings import settings


class TechnicalIndicators:
    """Calculate technical indicators for trading signals"""
    
    @staticmethod
    def calculate_ema(data: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return ta.trend.EMAIndicator(data, window=period).ema_indicator()
    
    @staticmethod
    def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        return ta.momentum.RSIIndicator(data, window=period).rsi()
    
    @staticmethod
    def calculate_adx(high: pd.Series, low: pd.Series, 
                      close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average Directional Index"""
        return ta.trend.ADXIndicator(high, low, close, window=period).adx()
    
    @staticmethod
    def calculate_atr(high: pd.Series, low: pd.Series, 
                      close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        return ta.volatility.AverageTrueRange(high, low, close, window=period).average_true_range()
    
    @staticmethod
    def calculate_macd(data: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD"""
        macd = ta.trend.MACD(data, window_slow=26, window_fast=12, window_sign=9)
        return (
            macd.macd(),
            macd.macd_signal(),
            macd.macd_diff()
        )
    
    @staticmethod
    def calculate_bbands(data: pd.Series, period: int = 20) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        bb = ta.volatility.BollingerBands(data, window=period, window_dev=2)
        return (
            bb.bollinger_hband(),
            bb.bollinger_mavg(),
            bb.bollinger_lband()
        )
    
    @staticmethod
    def detect_hammer(open_price: pd.Series, high: pd.Series, 
                      low: pd.Series, close: pd.Series) -> pd.Series:
        """Detect Hammer candlestick pattern"""
        result = pd.Series(0, index=close.index)
        for i in range(1, len(close)):
            body = abs(close.iloc[i] - open_price.iloc[i])
            lower_shadow = min(close.iloc[i], open_price.iloc[i]) - low.iloc[i]
            upper_shadow = high.iloc[i] - max(close.iloc[i], open_price.iloc[i])
            
            if body > 0 and lower_shadow > 2 * body and upper_shadow < body and close.iloc[i] > open_price.iloc[i]:
                result.iloc[i] = 100
        return result
    
    @staticmethod
    def detect_shooting_star(open_price: pd.Series, high: pd.Series,
                             low: pd.Series, close: pd.Series) -> pd.Series:
        """Detect Shooting Star pattern"""
        result = pd.Series(0, index=close.index)
        for i in range(1, len(close)):
            body = abs(close.iloc[i] - open_price.iloc[i])
            upper_shadow = high.iloc[i] - max(close.iloc[i], open_price.iloc[i])
            lower_shadow = min(close.iloc[i], open_price.iloc[i]) - low.iloc[i]
            
            if body > 0 and upper_shadow > 2 * body and lower_shadow < body and close.iloc[i] < open_price.iloc[i]:
                result.iloc[i] = 100
        return result
    
    @staticmethod
    def detect_engulfing(open_price: pd.Series, high: pd.Series,
                         low: pd.Series, close: pd.Series) -> pd.Series:
        """Detect Engulfing pattern"""
        result = pd.Series(0, index=close.index)
        for i in range(1, len(close)):
            # Bullish engulfing
            if (close.iloc[i] > open_price.iloc[i] and 
                close.iloc[i-1] < open_price.iloc[i-1] and
                close.iloc[i] >= open_price.iloc[i-1] and 
                open_price.iloc[i] <= close.iloc[i-1]):
                result.iloc[i] = 100
            # Bearish engulfing
            elif (close.iloc[i] < open_price.iloc[i] and 
                  close.iloc[i-1] > open_price.iloc[i-1] and
                  close.iloc[i] <= open_price.iloc[i-1] and 
                  open_price.iloc[i] >= close.iloc[i-1]):
                result.iloc[i] = -100
        return result
    
    @staticmethod
    def detect_morning_star(open_price: pd.Series, high: pd.Series,
                           low: pd.Series, close: pd.Series) -> pd.Series:
        """Detect Morning Star pattern"""
        result = pd.Series(0, index=close.index)
        for i in range(2, len(close)):
            body1 = abs(close.iloc[i-2] - open_price.iloc[i-2])
            body2 = abs(close.iloc[i-1] - open_price.iloc[i-1])
            body3 = abs(close.iloc[i] - open_price.iloc[i])
            
            if (close.iloc[i-2] < open_price.iloc[i-2] and
                body2 < 0.3 * body1 and
                close.iloc[i] > open_price.iloc[i] and
                body3 > body1):
                result.iloc[i] = 100
        return result
    
    @staticmethod
    def detect_evening_star(open_price: pd.Series, high: pd.Series,
                           low: pd.Series, close: pd.Series) -> pd.Series:
        """Detect Evening Star pattern"""
        result = pd.Series(0, index=close.index)
        for i in range(2, len(close)):
            body1 = abs(close.iloc[i-2] - open_price.iloc[i-2])
            body2 = abs(close.iloc[i-1] - open_price.iloc[i-1])
            body3 = abs(close.iloc[i] - open_price.iloc[i])
            
            if (close.iloc[i-2] > open_price.iloc[i-2] and
                body2 < 0.3 * body1 and
                close.iloc[i] < open_price.iloc[i] and
                body3 > body1):
                result.iloc[i] = 100
        return result
    
    @staticmethod
    def calculate_volume_ma(volume: pd.Series, period: int = 20) -> pd.Series:
        """Calculate Volume Moving Average"""
        return ta.trend.SMAIndicator(volume, window=period).sma_indicator()
    
    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all required technical indicators"""
        # EMAs
        df['ema_20'] = TechnicalIndicators.calculate_ema(df['close'], settings.EMA_FAST)
        df['ema_50'] = TechnicalIndicators.calculate_ema(df['close'], settings.EMA_SLOW_1)
        df['ema_200'] = TechnicalIndicators.calculate_ema(df['close'], settings.EMA_SLOW_2)
        
        # RSI
        df['rsi'] = TechnicalIndicators.calculate_rsi(df['close'], settings.RSI_PERIOD)
        
        # ADX
        df['adx'] = TechnicalIndicators.calculate_adx(
            df['high'], df['low'], df['close'], settings.ADX_PERIOD
        )
        
        # ATR
        df['atr'] = TechnicalIndicators.calculate_atr(
            df['high'], df['low'], df['close'], settings.ATR_PERIOD
        )
        
        # MACD
        df['macd'], df['macd_signal'], df['macd_hist'] = TechnicalIndicators.calculate_macd(df['close'])
        
        # Bollinger Bands
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = TechnicalIndicators.calculate_bbands(df['close'])
        
        # Volume MA
        df['volume_ma'] = TechnicalIndicators.calculate_volume_ma(df['volume'])
        
        # Candlestick Patterns
        df['hammer'] = TechnicalIndicators.detect_hammer(
            df['open'], df['high'], df['low'], df['close']
        )
        df['shooting_star'] = TechnicalIndicators.detect_shooting_star(
            df['open'], df['high'], df['low'], df['close']
        )
        df['engulfing'] = TechnicalIndicators.detect_engulfing(
            df['open'], df['high'], df['low'], df['close']
        )
        df['morning_star'] = TechnicalIndicators.detect_morning_star(
            df['open'], df['high'], df['low'], df['close']
        )
        df['evening_star'] = TechnicalIndicators.detect_evening_star(
            df['open'], df['high'], df['low'], df['close']
        )
        
        return df
    
    @staticmethod
    def check_ema_cross(df: pd.DataFrame, fast_col: str = 'ema_50', 
                        slow_col: str = 'ema_200') -> Optional[str]:
        """Check for EMA crossover"""
        if len(df) < 2:
            return None
            
        current_fast = df[fast_col].iloc[-1]
        current_slow = df[slow_col].iloc[-1]
        prev_fast = df[fast_col].iloc[-2]
        prev_slow = df[slow_col].iloc[-2]
        
        if prev_fast <= prev_slow and current_fast > current_slow:
            return 'bullish'
        
        if prev_fast >= prev_slow and current_fast < current_slow:
            return 'bearish'
        
        return None
    
    @staticmethod
    def check_pullback(df: pd.DataFrame, trend: str) -> bool:
        """Check if price has pulled back to EMA 20"""
        if len(df) < 5:
            return False
        
        current_close = df['close'].iloc[-1]
        ema_20 = df['ema_20'].iloc[-1]
        
        price_diff_pct = abs(current_close - ema_20) / ema_20 * 100
        
        if price_diff_pct > 0.5:
            return False
        
        if trend == 'bullish':
            return current_close >= ema_20
        else:
            return current_close <= ema_20
    
    @staticmethod
    def check_rsi_bounce(rsi_value: float, trend: str) -> bool:
        """Check if RSI is in bounce zone"""
        if trend == 'bullish':
            return settings.RSI_LOWER <= rsi_value <= settings.RSI_UPPER
        else:
            return (100 - settings.RSI_UPPER) <= rsi_value <= (100 - settings.RSI_LOWER)
    
    @staticmethod
    def detect_candlestick_pattern(df: pd.DataFrame, trend: str) -> Optional[str]:
        """Detect bullish or bearish candlestick pattern"""
        if trend == 'bullish':
            if df['hammer'].iloc[-1] != 0:
                return 'hammer'
            if df['engulfing'].iloc[-1] > 0:
                return 'bullish_engulfing'
            if df['morning_star'].iloc[-1] != 0:
                return 'morning_star'
        else:
            if df['shooting_star'].iloc[-1] != 0:
                return 'shooting_star'
            if df['engulfing'].iloc[-1] < 0:
                return 'bearish_engulfing'
            if df['evening_star'].iloc[-1] != 0:
                return 'evening_star'
        
        return None
    
    @staticmethod
    def calculate_support_resistance(df: pd.DataFrame, window: int = 20) -> Dict[str, float]:
        """Calculate recent support and resistance levels"""
        recent_data = df.tail(window)
        
        resistance = recent_data['high'].max()
        support = recent_data['low'].min()
        
        return {
            'resistance': resistance,
            'support': support,
            'range': resistance - support
        }


indicators = TechnicalIndicators()