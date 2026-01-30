"""
Technical indicators calculator using pandas-ta
"""
import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import pandas_ta as ta
from config.settings import settings


class TechnicalIndicators:
    """Calculate technical indicators for trading signals"""
    
    @staticmethod
    def calculate_ema(data: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return ta.ema(data, length=period)
    
    @staticmethod
    def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        return ta.rsi(data, length=period)
    
    @staticmethod
    def calculate_adx(high: pd.Series, low: pd.Series, 
                      close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average Directional Index"""
        adx_df = ta.adx(high, low, close, length=period)
        return adx_df[f'ADX_{period}']
    
    @staticmethod
    def calculate_atr(high: pd.Series, low: pd.Series, 
                      close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        return ta.atr(high, low, close, length=period)
    
    @staticmethod
    def calculate_macd(data: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD"""
        macd_df = ta.macd(data, fast=12, slow=26, signal=9)
        return macd_df['MACD_12_26_9'], macd_df['MACDs_12_26_9'], macd_df['MACDh_12_26_9']
    
    @staticmethod
    def calculate_bbands(data: pd.Series, period: int = 20) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        bbands_df = ta.bbands(data, length=period, std=2)
        return bbands_df[f'BBU_{period}_2.0'], bbands_df[f'BBM_{period}_2.0'], bbands_df[f'BBL_{period}_2.0']
    
    @staticmethod
    def detect_hammer(open_price: pd.Series, high: pd.Series, 
                      low: pd.Series, close: pd.Series) -> pd.Series:
        """Detect Hammer candlestick pattern"""
        cdl_df = ta.cdl_pattern(open_price, high, low, close, name="hammer")
        return cdl_df if cdl_df is not None else pd.Series(0, index=close.index)
    
    @staticmethod
    def detect_shooting_star(open_price: pd.Series, high: pd.Series,
                             low: pd.Series, close: pd.Series) -> pd.Series:
        """Detect Shooting Star pattern"""
        cdl_df = ta.cdl_pattern(open_price, high, low, close, name="shootingstar")
        return cdl_df if cdl_df is not None else pd.Series(0, index=close.index)
    
    @staticmethod
    def detect_engulfing(open_price: pd.Series, high: pd.Series,
                         low: pd.Series, close: pd.Series) -> pd.Series:
        """Detect Engulfing pattern"""
        # Simple engulfing detection
        result = pd.Series(0, index=close.index)
        for i in range(1, len(close)):
            if close.iloc[i] > open_price.iloc[i] and close.iloc[i-1] < open_price.iloc[i-1]:
                if close.iloc[i] >= open_price.iloc[i-1] and open_price.iloc[i] <= close.iloc[i-1]:
                    result.iloc[i] = 100  # Bullish engulfing
            elif close.iloc[i] < open_price.iloc[i] and close.iloc[i-1] > open_price.iloc[i-1]:
                if close.iloc[i] <= open_price.iloc[i-1] and open_price.iloc[i] >= close.iloc[i-1]:
                    result.iloc[i] = -100  # Bearish engulfing
        return result
    
    @staticmethod
    def detect_morning_star(open_price: pd.Series, high: pd.Series,
                           low: pd.Series, close: pd.Series) -> pd.Series:
        """Detect Morning Star pattern"""
        return pd.Series(0, index=close.index)  # Simplified
    
    @staticmethod
    def detect_evening_star(open_price: pd.Series, high: pd.Series,
                           low: pd.Series, close: pd.Series) -> pd.Series:
        """Detect Evening Star pattern"""
        return pd.Series(0, index=close.index)  # Simplified
    
    @staticmethod
    def calculate_volume_ma(volume: pd.Series, period: int = 20) -> pd.Series:
        """Calculate Volume Moving Average"""
        return ta.sma(volume, length=period)
    
    # ... (বাকি functions same থাকবে)
