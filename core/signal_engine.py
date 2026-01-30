"""
Core signal generation engine
"""
import asyncio
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import pandas as pd

from config.settings import settings
from core.binance_client import binance_client
from strategies.ema_pullback import ema_strategy
from risk.position_sizer import risk_manager
from database.models import db

logger = logging.getLogger(__name__)


class SignalEngine:
    """Main signal generation and filtering engine"""
    
    def __init__(self):
        self.running = False
        self.signal_queue: List[Dict] = []
        self.last_signal_time: Dict[str, datetime] = {}
        
    async def start(self):
        """Start signal generation engine"""
        self.running = True
        logger.info("Signal engine started")
        
        while self.running:
            try:
                await self._generate_signals()
                await asyncio.sleep(settings.SIGNAL_CHECK_INTERVAL)
            except Exception as e:
                logger.error(f"Error in signal generation loop: {e}")
                await asyncio.sleep(60)
    
    def stop(self):
        """Stop signal engine"""
        self.running = False
        logger.info("Signal engine stopped")
    
    async def _generate_signals(self):
        """Generate trading signals for all pairs"""
        logger.info("Checking for trading signals...")
        
        can_trade, reason = await risk_manager.check_daily_limits()
        if not can_trade:
            logger.warning(f"Cannot generate signals: {reason}")
            return
        
        if not await self._check_market_conditions():
            logger.info("Market conditions not favorable")
            return
        
        if await self._is_high_impact_event_near():
            logger.info("High impact event near - skipping signals")
            return
        
        signals = []
        for pair in settings.TRADING_PAIRS:
            try:
                signal = await self._analyze_pair(pair)
                if signal:
                    signals.append(signal)
            except Exception as e:
                logger.error(f"Error analyzing {pair}: {e}")
        
        if signals:
            await self._process_signals(signals)
    
    async def _analyze_pair(self, pair: str) -> Optional[Dict]:
        """Analyze a single trading pair"""
        if pair in self.last_signal_time:
            time_since_last = datetime.utcnow() - self.last_signal_time[pair]
            if time_since_last < timedelta(hours=2):
                return None
        
        signal = await ema_strategy.analyze_pair(pair)
        
        if not signal:
            return None
        
        if not await self._apply_market_filters(signal):
            return None
        
        if not self._check_trading_session():
            logger.info(f"Outside high conviction trading session")
            signal['confluence_score'] *= 0.8
        
        if pair != 'BTCUSDT':
            if not await self._check_correlation_filter(pair):
                logger.info(f"{pair}: Failed correlation check")
                return None
        
        return signal
    
    async def _apply_market_filters(self, signal: Dict) -> bool:
        """Apply market context filters to signal"""
        pair = signal['pair']
        
        funding_rate = await binance_client.get_funding_rate(pair)
        if funding_rate:
            if abs(funding_rate) > settings.FUNDING_RATE_EXTREME:
                logger.info(f"{pair}: Extreme funding rate {funding_rate:.4f}")
                if (funding_rate > 0 and signal['trend'] == 'bearish') or \
                   (funding_rate < 0 and signal['trend'] == 'bullish'):
                    signal['confluence_score'] += 0.5
                else:
                    return False
        
        oi_data = await binance_client.get_open_interest(pair)
        if oi_data:
            signal['open_interest'] = oi_data['open_interest']
        
        liquidations = await binance_client.get_liquidations(pair)
        if liquidations:
            recent_liqs = [l for l in liquidations 
                          if l['time'] > datetime.utcnow() - timedelta(hours=1)]
            if len(recent_liqs) > 10:
                logger.info(f"{pair}: Liquidation cluster detected")
                signal['confluence_score'] += 0.5
        
        return True
    
    async def _check_market_conditions(self) -> bool:
        """Check overall market conditions"""
        btc_data = await binance_client.get_klines('BTCUSDT', '4h', limit=50)
        
        from core.indicators import TechnicalIndicators
        btc_data = TechnicalIndicators.calculate_all_indicators(btc_data)
        
        btc_adx = btc_data['adx'].iloc[-1]
        if btc_adx < settings.BTC_ADX_MIN:
            logger.info(f"BTC ADX too low: {btc_adx:.1f}")
            return False
        
        return True
    
    async def _check_correlation_filter(self, pair: str) -> bool:
        """Check correlation with BTC for altcoins"""
        if pair == 'BTCUSDT':
            return True
        
        corr = await binance_client.calculate_correlation(
            'BTCUSDT', pair, days=7
        )
        
        if abs(corr) > settings.BTC_CORRELATION_THRESHOLD:
            logger.info(f"{pair}: High correlation with BTC ({corr:.2f})")
        
        return True
    
    def _check_trading_session(self) -> bool:
        """Check if in high conviction trading session"""
        current_hour = datetime.utcnow().hour
        
        london_active = settings.LONDON_SESSION[0] <= current_hour < settings.LONDON_SESSION[1]
        ny_active = settings.NY_SESSION[0] <= current_hour < settings.NY_SESSION[1]
        
        return london_active or ny_active
    
    async def _is_high_impact_event_near(self) -> bool:
        """Check if high impact economic event is near"""
        now = datetime.utcnow()
        
        if now.day <= 7 and now.weekday() >= 3:
            logger.info("Potential NFP week - being cautious")
            return True
        
        return False
    
    async def _process_signals(self, signals: List[Dict]):
        """Process and rank signals"""
        signals.sort(key=lambda x: x['confluence_score'], reverse=True)
        
        if len(signals) > 1:
            logger.info(f"Multiple signals found, taking highest confluence")
        
        top_signal = signals[0]
        
        option_params = self._calculate_option_params(top_signal)
        top_signal.update(option_params)
        
        position = risk_manager.calculate_position_size(
            top_signal['current_price'],
            top_signal['stop_loss']
        )
        top_signal['position'] = position
        
        self.signal_queue.append(top_signal)
        
        self.last_signal_time[top_signal['pair']] = datetime.utcnow()
        
        await risk_manager.update_daily_stats(signal_generated=True)
        
        logger.info(f"Signal generated: {top_signal['pair']} {top_signal['direction']} "
                   f"Confluence: {top_signal['confluence_score']:.1f}")
    
    def _calculate_option_params(self, signal: Dict) -> Dict:
        """Calculate option strike and expiry"""
        current_price = signal['current_price']
        
        if signal['direction'] == 'LONG_CALL':
            strike = current_price * (1 + settings.OPTION_ATM_RANGE)
            strike_type = 'OTM'
        else:
            strike = current_price * (1 - settings.OPTION_ATM_RANGE)
            strike_type = 'OTM'
        
        if current_price > 1000:
            strike = round(strike / 50) * 50
        elif current_price > 100:
            strike = round(strike / 10) * 10
        else:
            strike = round(strike, 2)
        
        expiry_days = 10
        expiry_date = datetime.utcnow() + timedelta(days=expiry_days)
        
        premium_estimate = abs(strike - current_price) * 0.1
        
        return {
            'strike_price': strike,
            'strike_type': strike_type,
            'expiry_date': expiry_date,
            'expiry_days': expiry_days,
            'premium_estimate': premium_estimate
        }
    
    def get_pending_signals(self) -> List[Dict]:
        """Get pending signals from queue"""
        signals = self.signal_queue.copy()
        self.signal_queue.clear()
        return signals


signal_engine = SignalEngine()
