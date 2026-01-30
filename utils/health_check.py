"""
Health check HTTP server for Railway deployment
"""
import asyncio
import logging
from aiohttp import web
from datetime import datetime

from config.settings import settings

logger = logging.getLogger(__name__)


class HealthCheckServer:
    """HTTP server for health checks"""
    
    def __init__(self):
        self.app = web.Application()
        self.runner = None
        self.site = None
        self.start_time = datetime.utcnow()
        
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/status', self.status)
        self.app.router.add_get('/', self.root)
    
    async def health_check(self, request):
        """Health check endpoint"""
        return web.json_response({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'uptime_seconds': (datetime.utcnow() - self.start_time).total_seconds()
        })
    
    async def status(self, request):
        """Detailed status endpoint"""
        from core.signal_engine import signal_engine
        from core.binance_client import binance_client
        
        return web.json_response({
            'status': 'running',
            'start_time': self.start_time.isoformat(),
            'uptime_seconds': (datetime.utcnow() - self.start_time).total_seconds(),
            'signal_engine_running': signal_engine.running,
            'binance_connected': binance_client.client is not None,
            'config': {
                'testnet': settings.BINANCE_TESTNET,
                'trading_pairs': len(settings.TRADING_PAIRS),
                'signal_interval': settings.SIGNAL_CHECK_INTERVAL
            }
        })
    
    async def root(self, request):
        """Root endpoint"""
        return web.Response(text="Crypto Options Trading Bot - Running ✓")
    
    async def start(self):
        """Start health check server"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = web.TCPSite(
            self.runner, 
            '0.0.0.0', 
            settings.HEALTH_CHECK_PORT
        )
        
        await self.site.start()
        logger.info(f"Health check server started on port {settings.HEALTH_CHECK_PORT}")
    
    async def stop(self):
        """Stop health check server"""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        logger.info("Health check server stopped")


health_server = HealthCheckServer()
