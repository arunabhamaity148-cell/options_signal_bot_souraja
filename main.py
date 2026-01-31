"""
Main application entry point for Crypto Options Trading Bot
"""
import asyncio
import signal
import sys
import logging
from typing import Optional

from config.settings import settings
from database.models import db
from core.binance_client import binance_client
from core.signal_engine import signal_engine
from telegram.bot import telegram_bot
from utils.helpers import setup_logging, validate_environment
from utils.health_check import health_server

logger = logging.getLogger(__name__)


class TradingBotApp:
    """Main application class"""
    
    def __init__(self):
        self.shutdown_event = asyncio.Event()
        
    async def startup(self):
        """Initialize all components"""
        logger.info("=" * 60)
        logger.info("Crypto Options Trading Signal Bot Starting...")
        logger.info("=" * 60)
        
        # Validate environment
        validation = validate_environment()
        if not validation['valid']:
            logger.error("Environment validation failed:")
            for issue in validation['issues']:
                logger.error(f"  - {issue}")
            # DON'T exit - start health server anyway
            logger.warning("Starting with missing credentials - bot will not function fully")
        
        if validation['warnings']:
            for warning in validation['warnings']:
                logger.warning(f"  ⚠️  {warning}")
        
        logger.info("✓ Environment validated")
        
        # Start health check server FIRST
        try:
            await health_server.start()
            logger.info("✓ Health check server started")
        except Exception as e:
            logger.error(f"Health check server failed: {e}")
            raise
        
        # Try to initialize database
        try:
            if settings.DATABASE_URL and "postgresql" in settings.DATABASE_URL:
                db.initialize()
                await db.initialize_async()
                logger.info("✓ Database connected")
            else:
                logger.warning("⚠️ DATABASE_URL not configured - database features disabled")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            logger.warning("Continuing without database...")
        
        # Try to initialize Binance client
        try:
            if settings.BINANCE_API_KEY and settings.BINANCE_SECRET:
                await binance_client.initialize()
                logger.info("✓ Binance client initialized")
            else:
                logger.warning("⚠️ Binance credentials not set - market data disabled")
        except Exception as e:
            logger.error(f"Binance initialization failed: {e}")
            logger.warning("Continuing without Binance...")
        
        # Try to initialize Telegram bot
        try:
            if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
                await telegram_bot.initialize()
                logger.info("✓ Telegram bot initialized")
            else:
                logger.warning("⚠️ Telegram credentials not set - notifications disabled")
        except Exception as e:
            logger.error(f"Telegram bot initialization failed: {e}")
            logger.warning("Continuing without Telegram...")
        
        logger.info("=" * 60)
        logger.info("Startup complete (some features may be disabled)")
        logger.info("=" * 60)
    
    async def run(self):
        """Run the main application"""
        # Only start if Telegram is configured
        if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
            await telegram_bot.start()
            logger.info("▶️  Telegram bot running")
            
            # Only start signal engine if all systems ready
            if settings.BINANCE_API_KEY and settings.BINANCE_SECRET:
                signal_task = asyncio.create_task(signal_engine.start())
                logger.info("▶️  Signal engine running")
            else:
                logger.warning("Signal engine disabled - missing Binance credentials")
        else:
            logger.warning("Bot features disabled - missing Telegram credentials")
        
        logger.info("")
        logger.info("🚀 Bot is now running!")
        logger.info(f"📊 Monitoring {len(settings.TRADING_PAIRS)} pairs")
        logger.info(f"⏱️  Signal check interval: {settings.SIGNAL_CHECK_INTERVAL}s")
        logger.info(f"🔧 Mode: {'TESTNET' if settings.BINANCE_TESTNET else 'LIVE'}")
        logger.info("")
        logger.info("Health check available at /health")
        logger.info("Press Ctrl+C to stop...")
        logger.info("=" * 60)
        
        # Wait for shutdown signal
        await self.shutdown_event.wait()
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("Shutting down gracefully...")
        logger.info("=" * 60)
        
        try:
            logger.info("Stopping Telegram bot...")
            await telegram_bot.stop()
        except:
            pass
        
        try:
            logger.info("Closing Binance client...")
            await binance_client.close()
        except:
            pass
        
        try:
            logger.info("Closing database connections...")
            await db.close_async()
        except:
            pass
        
        try:
            logger.info("Stopping health check server...")
            await health_server.stop()
        except:
            pass
        
        logger.info("=" * 60)
        logger.info("Shutdown complete. Goodbye!")
        logger.info("=" * 60)
    
    def handle_signal(self, sig):
        """Handle shutdown signals"""
        logger.info(f"Received signal {sig.name}, initiating shutdown...")
        self.shutdown_event.set()


async def main():
    """Main entry point"""
    # Setup logging
    setup_logging(
        log_level=settings.LOG_LEVEL,
        log_file=settings.LOG_FILE
    )
    
    # Create app instance
    app = TradingBotApp()
    
    # Register signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            lambda s=sig: app.handle_signal(s)
        )
    
    try:
        # Startup
        await app.startup()
        
        # Run
        await app.run()
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        # Don't exit with error - let health check keep running
    finally:
        # Shutdown
        await app.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass