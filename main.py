"""
Main application entry point for Crypto Options Trading Bot
"""
import asyncio
import signal
import sys
import logging
import os
import traceback

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def simple_health_server():
    """Simple health check server that never crashes"""
    from aiohttp import web
    
    async def health(request):
        return web.json_response({'status': 'healthy'})
    
    async def status(request):
        return web.json_response({
            'status': 'running',
            'environment': {
                'BINANCE_API_KEY': bool(os.getenv('BINANCE_API_KEY')),
                'BINANCE_SECRET': bool(os.getenv('BINANCE_SECRET')),
                'TELEGRAM_BOT_TOKEN': bool(os.getenv('TELEGRAM_BOT_TOKEN')),
                'TELEGRAM_CHAT_ID': bool(os.getenv('TELEGRAM_CHAT_ID')),
                'DATABASE_URL': bool(os.getenv('DATABASE_URL'))
            }
        })
    
    app = web.Application()
    app.router.add_get('/health', health)
    app.router.add_get('/status', status)
    app.router.add_get('/', lambda r: web.Response(text="Crypto Options Bot Running ✓"))
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    
    logger.info("✓ Health check server running on port 8080")
    return runner


async def initialize_database():
    """Initialize database with error handling"""
    try:
        from database.models import db
        db.initialize()
        await db.initialize_async()
        logger.info("✓ Database connected")
        return db
    except Exception as e:
        logger.warning(f"⚠️  Database: {e}")
        return None


async def initialize_binance():
    """Initialize Binance client with error handling"""
    try:
        from core.binance_client import binance_client
        await binance_client.initialize()
        logger.info("✓ Binance client initialized")
        return binance_client
    except Exception as e:
        logger.warning(f"⚠️  Binance: {e}")
        return None


async def initialize_telegram():
    """Initialize Telegram bot with error handling"""
    try:
        from telegram.bot import telegram_bot
        await telegram_bot.initialize()
        await telegram_bot.start()
        logger.info("✓ Telegram bot started")
        return telegram_bot
    except Exception as e:
        logger.warning(f"⚠️  Telegram: {e}")
        return None


async def start_signal_engine():
    """Start signal engine with error handling"""
    try:
        from core.signal_engine import signal_engine
        asyncio.create_task(signal_engine.start())
        logger.info("✓ Signal engine started")
        return signal_engine
    except Exception as e:
        logger.warning(f"⚠️  Signal engine: {e}")
        return None


async def main():
    """Main entry point - never crashes"""
    logger.info("=" * 60)
    logger.info("🚀 Crypto Options Trading Signal Bot")
    logger.info("=" * 60)
    
    # Track what's running
    components = {}
    
    try:
        # 1. Start health server (REQUIRED)
        logger.info("\n1️⃣  Starting health check server...")
        components['health_server'] = await simple_health_server()
        
        # 2. Check environment
        logger.info("\n2️⃣  Checking environment variables...")
        env_status = {
            'BINANCE_API_KEY': os.getenv('BINANCE_API_KEY'),
            'BINANCE_SECRET': os.getenv('BINANCE_SECRET'),
            'TELEGRAM_BOT_TOKEN': os.getenv('TELEGRAM_BOT_TOKEN'),
            'TELEGRAM_CHAT_ID': os.getenv('TELEGRAM_CHAT_ID'),
            'DATABASE_URL': os.getenv('DATABASE_URL')
        }
        
        for key, value in env_status.items():
            status = "✓ Set" if value else "❌ Missing"
            logger.info(f"  {key}: {status}")
        
        # 3. Initialize database (if configured)
        logger.info("\n3️⃣  Initializing database...")
        if env_status['DATABASE_URL']:
            components['database'] = await initialize_database()
        else:
            logger.info("  ⏭️  Skipped (DATABASE_URL not set)")
        
        # 4. Initialize Binance (if configured)
        logger.info("\n4️⃣  Initializing Binance client...")
        if env_status['BINANCE_API_KEY'] and env_status['BINANCE_SECRET']:
            components['binance'] = await initialize_binance()
        else:
            logger.info("  ⏭️  Skipped (Binance credentials not set)")
        
        # 5. Initialize Telegram (if configured)
        logger.info("\n5️⃣  Initializing Telegram bot...")
        if env_status['TELEGRAM_BOT_TOKEN'] and env_status['TELEGRAM_CHAT_ID']:
            components['telegram'] = await initialize_telegram()
        else:
            logger.info("  ⏭️  Skipped (Telegram credentials not set)")
        
        # 6. Start signal engine (if all configured)
        logger.info("\n6️⃣  Starting signal engine...")
        if (components.get('binance') and 
            components.get('telegram') and 
            components.get('database')):
            components['signal_engine'] = await start_signal_engine()
        else:
            logger.info("  ⏭️  Skipped (dependencies not ready)")
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 Bot Status Summary:")
        logger.info("=" * 60)
        logger.info(f"  Health Server: ✅ RUNNING")
        logger.info(f"  Database: {'✅ CONNECTED' if components.get('database') else '⚠️  DISABLED'}")
        logger.info(f"  Binance: {'✅ CONNECTED' if components.get('binance') else '⚠️  DISABLED'}")
        logger.info(f"  Telegram: {'✅ RUNNING' if components.get('telegram') else '⚠️  DISABLED'}")
        logger.info(f"  Signal Engine: {'✅ RUNNING' if components.get('signal_engine') else '⚠️  DISABLED'}")
        logger.info("=" * 60)
        
        logger.info("\n✅ Bot is running!")
        logger.info("📍 Health check: http://0.0.0.0:8080/health")
        logger.info("📍 Status: http://0.0.0.0:8080/status")
        logger.info("\nPress Ctrl+C to stop...")
        logger.info("=" * 60 + "\n")
        
        # Keep running forever
        while True:
            await asyncio.sleep(3600)
            logger.info("💓 Heartbeat - bot still running")
    
    except KeyboardInterrupt:
        logger.info("\n⚠️  Keyboard interrupt received")
    
    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        logger.error(traceback.format_exc())
        logger.info("⚠️  Continuing to run despite error...")
        
        # Keep health server running even if something fails
        while True:
            await asyncio.sleep(3600)
    
    finally:
        logger.info("\n🛑 Shutting down...")
        
        # Cleanup
        for name, component in components.items():
            try:
                if name == 'health_server':
                    await component.cleanup()
                elif hasattr(component, 'close'):
                    await component.close()
                elif hasattr(component, 'stop'):
                    await component.stop()
                logger.info(f"  ✓ {name} stopped")
            except:
                pass
        
        logger.info("👋 Goodbye!")


if __name__ == "__main__":
    try:
        # Set up signal handlers
        def signal_handler(sig, frame):
            logger.info(f"\n⚠️  Received signal {sig}")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Run bot
        asyncio.run(main())
    
    except Exception as e:
        logger.error(f"Failed to start: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)