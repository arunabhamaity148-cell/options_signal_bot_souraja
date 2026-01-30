"""
WebSocket handler for real-time Binance data streaming
"""
import asyncio
import json
import logging
from typing import Dict, Callable, Optional
from datetime import datetime
import pandas as pd
import websockets
from collections import defaultdict

from config.settings import settings

logger = logging.getLogger(__name__)


class BinanceWebSocket:
    """WebSocket client for real-time Binance data"""
    
    def __init__(self):
        self.ws_endpoint = settings.get_binance_ws_endpoint()
        self.connections: Dict[str, websockets.WebSocketClientProtocol] = {}
        self.callbacks: Dict[str, Callable] = {}
        self.running = False
        self.reconnect_delay = 5
        self.max_reconnect_delay = 60
        self.latest_candles: Dict[str, Dict[str, pd.Series]] = defaultdict(dict)
        
    async def connect(self, stream_name: str, callback: Callable):
        """Connect to a WebSocket stream"""
        self.callbacks[stream_name] = callback
        url = f"{self.ws_endpoint}/{stream_name}"
        logger.info(f"Connecting to WebSocket: {url}")
        
        while self.running:
            try:
                async with websockets.connect(url) as websocket:
                    self.connections[stream_name] = websocket
                    logger.info(f"WebSocket connected: {stream_name}")
                    
                    async for message in websocket:
                        if not self.running:
                            break
                        
                        try:
                            data = json.loads(message)
                            await callback(data)
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
                    
            except websockets.exceptions.ConnectionClosed:
                logger.warning(f"WebSocket connection closed: {stream_name}")
            except Exception as e:
                logger.error(f"WebSocket error for {stream_name}: {e}")
            
            if self.running:
                logger.info(f"Reconnecting in {self.reconnect_delay} seconds...")
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(
                    self.reconnect_delay * 2, 
                    self.max_reconnect_delay
                )
    
    async def subscribe_klines(self, symbol: str, interval: str):
        """Subscribe to kline/candlestick updates"""
        stream_name = f"{symbol.lower()}@kline_{interval}"
        
        async def kline_callback(data: Dict):
            if 'k' not in data:
                return
            
            kline = data['k']
            candle = pd.Series({
                'timestamp': pd.to_datetime(kline['t'], unit='ms'),
                'open': float(kline['o']),
                'high': float(kline['h']),
                'low': float(kline['l']),
                'close': float(kline['c']),
                'volume': float(kline['v']),
                'is_closed': kline['x']
            })
            
            key = f"{symbol}_{interval}"
            self.latest_candles[symbol][interval] = candle
            
            if candle['is_closed']:
                logger.debug(f"Candle closed: {symbol} {interval} @ {candle['close']}")
        
        await self.connect(stream_name, kline_callback)
    
    async def subscribe_all_pairs(self, pairs: list, timeframes: list):
        """Subscribe to multiple pairs and timeframes"""
        tasks = []
        
        for pair in pairs:
            for timeframe in timeframes:
                task = asyncio.create_task(
                    self.subscribe_klines(pair.lower(), timeframe)
                )
                tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_latest_candle(self, symbol: str, timeframe: str) -> Optional[pd.Series]:
        """Get latest candle for a symbol and timeframe"""
        return self.latest_candles.get(symbol, {}).get(timeframe)
    
    async def start(self):
        """Start WebSocket connections"""
        self.running = True
        logger.info("Starting WebSocket connections...")
        await self.subscribe_all_pairs(
            settings.TRADING_PAIRS,
            settings.TIMEFRAMES
        )
    
    async def stop(self):
        """Stop all WebSocket connections"""
        self.running = False
        logger.info("Stopping WebSocket connections...")
        
        for stream_name, ws in self.connections.items():
            try:
                await ws.close()
                logger.info(f"Closed WebSocket: {stream_name}")
            except Exception as e:
                logger.error(f"Error closing WebSocket {stream_name}: {e}")
        
        self.connections.clear()


ws_handler = BinanceWebSocket()
