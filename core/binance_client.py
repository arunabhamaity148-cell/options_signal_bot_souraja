"""
Binance API client for fetching market data
"""
import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd
from binance.client import AsyncClient
from binance.exceptions import BinanceAPIException
import aiohttp

from config.settings import settings

logger = logging.getLogger(__name__)


class BinanceClient:
    """Async Binance API client"""
    
    def __init__(self):
        self.client: Optional[AsyncClient] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = asyncio.Semaphore(settings.BINANCE_RATE_LIMIT)
        
    async def initialize(self):
        """Initialize Binance client"""
        try:
            self.client = await AsyncClient.create(
                api_key=settings.BINANCE_API_KEY,
                api_secret=settings.BINANCE_SECRET,
                testnet=settings.BINANCE_TESTNET
            )
            self.session = aiohttp.ClientSession()
            logger.info("Binance client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Binance client: {e}")
            raise
    
    async def close(self):
        """Close Binance client"""
        if self.client:
            await self.client.close_connection()
        if self.session:
            await self.session.close()
        logger.info("Binance client closed")
    
    async def _rate_limited_request(self, func, *args, **kwargs):
        """Execute request with rate limiting"""
        async with self.rate_limiter:
            return await func(*args, **kwargs)
    
    async def get_klines(self, symbol: str, interval: str, 
                        limit: int = 500) -> pd.DataFrame:
        """Get historical klines/candlestick data"""
        try:
            klines = await self._rate_limited_request(
                self.client.get_klines,
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            df.set_index('timestamp', inplace=True)
            
            return df[['open', 'high', 'low', 'close', 'volume']]
            
        except BinanceAPIException as e:
            logger.error(f"Binance API error for {symbol} {interval}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching klines for {symbol} {interval}: {e}")
            raise
    
    async def get_ticker_price(self, symbol: str) -> float:
        """Get current ticker price"""
        try:
            ticker = await self._rate_limited_request(
                self.client.get_symbol_ticker,
                symbol=symbol
            )
            return float(ticker['price'])
        except Exception as e:
            logger.error(f"Error fetching ticker price for {symbol}: {e}")
            raise
    
    async def get_funding_rate(self, symbol: str) -> Optional[float]:
        """Get current funding rate for perpetual futures"""
        try:
            futures_symbol = symbol.replace('USDT', 'USDT')
            
            premium_index = await self._rate_limited_request(
                self.client.futures_funding_rate,
                symbol=futures_symbol,
                limit=1
            )
            
            if premium_index:
                return float(premium_index[0]['fundingRate'])
            return None
            
        except Exception as e:
            logger.warning(f"Could not fetch funding rate for {symbol}: {e}")
            return None
    
    async def get_open_interest(self, symbol: str) -> Optional[Dict]:
        """Get open interest data"""
        try:
            futures_symbol = symbol.replace('USDT', 'USDT')
            
            oi = await self._rate_limited_request(
                self.client.futures_open_interest,
                symbol=futures_symbol
            )
            
            return {
                'open_interest': float(oi['openInterest']),
                'timestamp': datetime.fromtimestamp(oi['time'] / 1000)
            }
            
        except Exception as e:
            logger.warning(f"Could not fetch open interest for {symbol}: {e}")
            return None
    
    async def get_liquidations(self, symbol: str) -> List[Dict]:
        """Get recent liquidation data"""
        try:
            futures_symbol = symbol.replace('USDT', 'USDT')
            
            liquidations = await self._rate_limited_request(
                self.client.futures_force_orders,
                symbol=futures_symbol,
                limit=100
            )
            
            return [
                {
                    'price': float(liq['price']),
                    'quantity': float(liq['origQty']),
                    'side': liq['side'],
                    'time': datetime.fromtimestamp(liq['time'] / 1000)
                }
                for liq in liquidations
            ]
            
        except Exception as e:
            logger.warning(f"Could not fetch liquidations for {symbol}: {e}")
            return []
    
    async def get_24h_volume(self, symbol: str) -> float:
        """Get 24-hour trading volume"""
        try:
            ticker = await self._rate_limited_request(
                self.client.get_ticker,
                symbol=symbol
            )
            return float(ticker['volume'])
        except Exception as e:
            logger.error(f"Error fetching 24h volume for {symbol}: {e}")
            return 0.0
    
    async def calculate_correlation(self, symbol1: str, symbol2: str, 
                                   days: int = 30) -> float:
        """Calculate correlation between two symbols"""
        try:
            df1 = await self.get_klines(symbol1, '1h', limit=days*24)
            df2 = await self.get_klines(symbol2, '1h', limit=days*24)
            
            returns1 = df1['close'].pct_change().dropna()
            returns2 = df2['close'].pct_change().dropna()
            
            aligned = pd.concat([returns1, returns2], axis=1, join='inner')
            corr = aligned.corr().iloc[0, 1]
            
            return corr
            
        except Exception as e:
            logger.error(f"Error calculating correlation: {e}")
            return 0.0
    
    async def fetch_all_pairs_data(self, timeframe: str) -> Dict[str, pd.DataFrame]:
        """Fetch data for all trading pairs"""
        tasks = []
        for pair in settings.TRADING_PAIRS:
            tasks.append(self.get_klines(pair, timeframe))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        data = {}
        for pair, result in zip(settings.TRADING_PAIRS, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch data for {pair}: {result}")
            else:
                data[pair] = result
        
        return data
    
    async def get_server_time(self) -> datetime:
        """Get Binance server time"""
        try:
            server_time = await self._rate_limited_request(
                self.client.get_server_time
            )
            return datetime.fromtimestamp(server_time['serverTime'] / 1000)
        except Exception as e:
            logger.error(f"Error fetching server time: {e}")
            return datetime.utcnow()


binance_client = BinanceClient()
