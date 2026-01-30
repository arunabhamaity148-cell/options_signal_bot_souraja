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
from core.websocket_handler import ws_handler
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
            sys.exit(1)
        
        if validation['warnings']:
            for warning in validation['warnings']:
                logger.warning(f"  ⚠️  {warning}")
        
        logger.info("✓ Environment validated")
        
        # Initialize database
        try:
            db.initialize()
            await db.initialize_async()
            logger.info("✓ Database connected")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            sys.exit(1)
        
        # Initialize Binance client
        try:
            await binance_client.initialize()
            logger.info("✓ Binance client initialized")
        except Exception as e:
            logger.error(f"Binance initialization failed: {e}")
            sys.exit(1)
        
        # Initialize Telegram bot
        try:
            await telegram_bot.initialize()
            logger.info("✓ Telegram bot initialized")
        except Exception as e:
            logger.error(f"Telegram bot initialization failed: {e}")
            sys.exit(1)
        
        # Start health check server
        try:
            await health_server.start()
            logger.info("✓ Health check server started")
        except Exception as e:
            logger.error(f"Health check server failed: {e}")
            sys.exit(1)
        
        logger.info("=" * 60)
        logger.info("All components initialized successfully!")
        logger.info("=" * 60)
    
    async def run(self):
        """Run the main application"""
        # Start Telegram bot
        await telegram_bot.start()
        logger.info("▶️  Telegram bot running")
        
        # Start WebSocket handler (optional - for real-time updates)
        # asyncio.create_task(ws_handler.start())
        # logger.info("▶️  WebSocket handler running")
        
        # Start signal engine
        signal_task = asyncio.create_task(signal_engine.start())
        logger.info("▶️  Signal engine running")
        
        logger.info("")
        logger.info("🚀 Bot is now running!")
        logger.info(f"📊 Monitoring {len(settings.TRADING_PAIRS)} pairs")
        logger.info(f"⏱️  Signal check interval: {settings.SIGNAL_CHECK_INTERVAL}s")
        logger.info(f"🔧 Mode: {'TESTNET' if settings.BINANCE_TESTNET else 'LIVE'}")
        logger.info("")
        logger.info("Press Ctrl+C to stop...")
        logger.info("=" * 60)
        
        # Wait for shutdown signal
        await self.shutdown_event.wait()
        
        # Stop signal engine
        signal_engine.stop()
        await signal_task
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("Shutting down gracefully...")
        logger.info("=" * 60)
        
        # Stop components in reverse order
        logger.info("Stopping Telegram bot...")
        await telegram_bot.stop()
        
        logger.info("Stopping WebSocket handler...")
        await ws_handler.stop()
        
        logger.info("Closing Binance client...")
        await binance_client.close()
        
        logger.info("Closing database connections...")
        await db.close_async()
        
        logger.info("Stopping health check server...")
        await health_server.stop()
        
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
        sys.exit(1)
    finally:
        # Shutdown
        await app.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass