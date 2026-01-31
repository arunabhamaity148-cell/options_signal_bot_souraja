"""
Main application entry point for Crypto Options Trading Bot
"""
import asyncio
import logging
from aiohttp import web

# Simple logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def health_check(request):
    """Health check endpoint"""
    return web.json_response({'status': 'healthy'})


async def start_server():
    """Start simple health check server"""
    app = web.Application()
    app.router.add_get('/health', health_check)
    app.router.add_get('/', lambda r: web.Response(text="Bot Running"))
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    
    logger.info("Health check server started on port 8080")
    
    # Keep running
    while True:
        await asyncio.sleep(3600)


async def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("Starting Crypto Options Trading Bot...")
    logger.info("=" * 60)
    
    try:
        # Start health check server
        await start_server()
    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown")