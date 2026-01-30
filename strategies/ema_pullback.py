"""
EMA Pullback Strategy Implementation
"""
import logging
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
import pandas as pd

from config.settings import settings
from core.indicators import TechnicalIndicators
from core.binance_client import binance_client

logger = logging.getLogger(__name__)


class EMAPullbackStrategy:
    """EMA Pullback trading strategy"""
    
    def __init__(self):
        self.indicators = TechnicalIndicators()
        
    async def analyze_pair(self, symbol: str) -> Optional[Dict]:
        """Analyze a trading pair for signal"""
        try:
            htf_data_4h = await binance_client.get_klines(symbol, '4h', limit=200)
            htf_data_1h = await binance_client.get_klines(symbol, '1h', limit=200)
            
            ltf_data_15m = await binance_client.get_klines(symbol, '15m', limit=200)
            ltf_data_5m = await binance_client.get_klines(symbol, '5m', limit=200)
            
            htf_data_4h = self.indicators.calculate_all_indicators(htf_data_4h)
            htf_data_1h = self.indicators.calculate_all_indicators(htf_data_1h)
            ltf_data_15m = self.indicators.calculate_all_indicators(ltf_data_15m)
            ltf_data_5m = self.indicators.calculate_all_indicators(ltf_data_5m)
            
            trend = await self._check_trend(htf_data_4h, htf_data_1h)
            
            if not trend:
                return None
            
            entry_signal = await self._check_entry_trigger(
                ltf_data_15m, ltf_data_5m, trend
            )
            
            if not entry_signal:
                return None
            
            confluence = self._calculate_confluence(
                htf_data_4h, htf_data_1h, ltf_data_15m, ltf_data_5m, trend
            )
            
            if confluence < settings.MIN_CONFLUENCE_SCORE:
                logger.info(f"{symbol}: Low confluence score {confluence:.1f}")
                return None
            
            current_price = ltf_data_5m['close'].iloc[-1]
            
            levels = self._calculate_levels(
                current_price, ltf_data_15m, trend
            )
            
            signal = {
                'pair': symbol,
                'direction': f"LONG_CALL" if trend == 'bullish' else "LONG_PUT",
                'trend': trend,
                'current_price': current_price,
                'confluence_score': confluence,
                'entry_zone': levels['entry_zone'],
                'stop_loss': levels['stop_loss'],
                'take_profits': levels['take_profits'],
                'setup_logic': entry_signal['logic'],
                'indicators': {
                    'ema_50_4h': htf_data_4h['ema_50'].iloc[-1],
                    'ema_200_4h': htf_data_4h['ema_200'].iloc[-1],
                    'adx_4h': htf_data_4h['adx'].iloc[-1],
                    'rsi_15m': ltf_data_15m['rsi'].iloc[-1],
                    'volume_ratio': ltf_data_15m['volume'].iloc[-1] / ltf_data_15m['volume_ma'].iloc[-1],
                    'pattern': entry_signal.get('pattern', 'none')
                },
                'timestamp': datetime.utcnow()
            }
            
            return signal
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return None
    
    async def _check_trend(self, df_4h: pd.DataFrame, 
                          df_1h: pd.DataFrame) -> Optional[str]:
        """Check higher timeframe trend"""
        adx_4h = df_4h['adx'].iloc[-1]
        if adx_4h < settings.ADX_THRESHOLD:
            return None
        
        ema_50_4h = df_4h['ema_50'].iloc[-1]
        ema_200_4h = df_4h['ema_200'].iloc[-1]
        close_4h = df_4h['close'].iloc[-1]
        
        if ema_50_4h > ema_200_4h and close_4h > ema_50_4h:
            if df_1h['ema_50'].iloc[-1] > df_1h['ema_200'].iloc[-1]:
                return 'bullish'
        
        if ema_50_4h < ema_200_4h and close_4h < ema_50_4h:
            if df_1h['ema_50'].iloc[-1] < df_1h['ema_200'].iloc[-1]:
                return 'bearish'
        
        return None
    
    async def _check_entry_trigger(self, df_15m: pd.DataFrame,
                                   df_5m: pd.DataFrame,
                                   trend: str) -> Optional[Dict]:
        """Check for entry trigger on lower timeframes"""
        logic_parts = []
        
        pullback_15m = self.indicators.check_pullback(df_15m, trend)
        if not pullback_15m:
            return None
        logic_parts.append("EMA 20 pullback on 15m")
        
        rsi_15m = df_15m['rsi'].iloc[-1]
        if not self.indicators.check_rsi_bounce(rsi_15m, trend):
            return None
        logic_parts.append(f"RSI bounce at {rsi_15m:.1f}")
        
        volume_15m = df_15m['volume'].iloc[-1]
        volume_ma = df_15m['volume_ma'].iloc[-1]
        
        if volume_15m <= volume_ma:
            return None
        logic_parts.append(f"Volume spike ({volume_15m/volume_ma:.1f}x avg)")
        
        pattern = self.indicators.detect_candlestick_pattern(df_5m, trend)
        if pattern:
            logic_parts.append(f"Pattern: {pattern}")
        
        close_5m = df_5m['close'].iloc[-1]
        ema_20_5m = df_5m['ema_20'].iloc[-1]
        
        if trend == 'bullish' and close_5m < ema_20_5m:
            return None
        if trend == 'bearish' and close_5m > ema_20_5m:
            return None
        
        return {
            'logic': ' + '.join(logic_parts),
            'pattern': pattern
        }
    
    def _calculate_confluence(self, df_4h: pd.DataFrame, 
                             df_1h: pd.DataFrame,
                             df_15m: pd.DataFrame,
                             df_5m: pd.DataFrame,
                             trend: str) -> float:
        """Calculate confluence score (0-10)"""
        score = 0.0
        
        if df_4h['ema_50'].iloc[-1] > df_4h['ema_200'].iloc[-1] and \
           df_1h['ema_50'].iloc[-1] > df_1h['ema_200'].iloc[-1] and trend == 'bullish':
            score += 2.0
        elif df_4h['ema_50'].iloc[-1] < df_4h['ema_200'].iloc[-1] and \
             df_1h['ema_50'].iloc[-1] < df_1h['ema_200'].iloc[-1] and trend == 'bearish':
            score += 2.0
        
        if df_4h['adx'].iloc[-1] > 30:
            score += 1.0
        
        vol_ratio = df_15m['volume'].iloc[-1] / df_15m['volume_ma'].iloc[-1]
        if vol_ratio > 1.5:
            score += 1.5
        elif vol_ratio > 1.2:
            score += 1.0
        
        rsi = df_15m['rsi'].iloc[-1]
        if trend == 'bullish' and 40 <= rsi <= 55:
            score += 1.0
        elif trend == 'bearish' and 45 <= rsi <= 60:
            score += 1.0
        
        pattern = self.indicators.detect_candlestick_pattern(df_5m, trend)
        if pattern:
            score += 1.5
        
        close = df_15m['close'].iloc[-1]
        ema_20 = df_15m['ema_20'].iloc[-1]
        price_diff = abs(close - ema_20) / ema_20 * 100
        if price_diff < 0.3:
            score += 1.0
        
        if trend == 'bullish' and df_15m['macd_hist'].iloc[-1] > 0:
            score += 1.0
        elif trend == 'bearish' and df_15m['macd_hist'].iloc[-1] < 0:
            score += 1.0
        
        if trend == 'bullish' and close > df_15m['bb_middle'].iloc[-1]:
            score += 1.0
        elif trend == 'bearish' and close < df_15m['bb_middle'].iloc[-1]:
            score += 1.0
        
        return min(score, 10.0)
    
    def _calculate_levels(self, current_price: float,
                         df: pd.DataFrame,
                         trend: str) -> Dict:
        """Calculate entry, stop loss, and take profit levels"""
        atr = df['atr'].iloc[-1]
        
        entry_spread = current_price * 0.003
        entry_zone = {
            'min': current_price - entry_spread,
            'max': current_price + entry_spread
        }
        
        if trend == 'bullish':
            stop_loss = current_price - (atr * settings.ATR_SL_MULTIPLIER)
            recent_low = df['low'].tail(20).min()
            stop_loss = max(stop_loss, recent_low * 0.998)
        else:
            stop_loss = current_price + (atr * settings.ATR_SL_MULTIPLIER)
            recent_high = df['high'].tail(20).max()
            stop_loss = min(stop_loss, recent_high * 1.002)
        
        risk = abs(current_price - stop_loss)
        
        if trend == 'bullish':
            take_profits = {
                'tp1': current_price + (risk * 2),
                'tp2': current_price + (risk * 3),
                'tp3': current_price + (risk * 4)
            }
        else:
            take_profits = {
                'tp1': current_price - (risk * 2),
                'tp2': current_price - (risk * 3),
                'tp3': current_price - (risk * 4)
            }
        
        return {
            'entry_zone': entry_zone,
            'stop_loss': stop_loss,
            'take_profits': take_profits
        }


ema_strategy = EMAPullbackStrategy()
