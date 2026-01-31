"""
Main application entry point for Crypto Options Trading Bot
"""
import asyncio
import signal
import sys
import logging
import os

# Simple logging setup first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import after logging setup
try:
    from config.settings import settings
    from utils.health_check import health_server
    logger.info("✓ Config imported")
except Exception as e:
    logger.error(f"Config import failed: {e}")
    # Continue anyway

try:
    from database.models import db
    logger.info("✓ Database models imported")
except Exception as e:
    logger.error(f"Database import failed: {e}")
    db = None

try:
    from core.binance_client import binance_client
    logger.info("✓ Binance client imported")
except Exception as e:
    logger.error(f"Binance import failed: {e}")
    binance_client = None

try:
    from core.signal_engine import signal_engine
    logger.info("✓ Signal engine imported")
except Exception as e:
    logger.error(f"Signal engine import failed: {e}")
    signal_engine = None

try:
    from telegram.bot import telegram_bot
    logger.info("✓ Telegram bot imported")
except Exception as e:
    logger.error(f"Telegram import failed: {e}")
    telegram_bot = None


class TradingBotApp:
    """Main application class"""
    
    def __init__(self):
        self.shutdown_event = asyncio.Event()
        
    async def startup(self):
        """Initialize all components"""
        logger.info("=" * 60)
        logger.info("Crypto Options Trading Signal Bot Starting...")
        logger.info("=" * 60)
        
        # Start health check server FIRST
        try:
            await health_server.start()
            logger.info("✓ Health check server started on port 8080")
        except Exception as e:
            logger.error(f"❌ Health check server failed: {e}")
            raise
        
        # Check environment variables
        logger.info("\n📋 Environment Check:")
        logger.info(f"  BINANCE_API_KEY: {'✓ Set' if os.getenv('BINANCE_API_KEY') else '❌ Missing'}")
        logger.info(f"  BINANCE_SECRET: {'✓ Set' if os.getenv('BINANCE_SECRET') else '❌ Missing'}")
        logger.info(f"  TELEGRAM_BOT_TOKEN: {'✓ Set' if os.getenv('TELEGRAM_BOT_TOKEN') else '❌ Missing'}")
        logger.info(f"  TELEGRAM_CHAT_ID: {'✓ Set' if os.getenv('TELEGRAM_CHAT_ID') else '❌ Missing'}")
        logger.info(f"  DATABASE_URL: {'✓ Set' if os.getenv('DATABASE_URL') else '❌ Missing'}")
        
        # Initialize database
        if db and os.getenv('DATABASE_URL'):
            try:
                db.initialize()
                await db.initialize_async()
                logger.info("✓ Database connected")
            except Exception as e:
                logger.warning(f"⚠️  Database error: {e}")
        else:
            logger.warning("⚠️  Database disabled (DATABASE_URL not set)")
        
        # Initialize Binance
        if binance_client and os.getenv('BINANCE_API_KEY'):
            try:
                await binance_client.initialize()
                logger.info("✓ Binance client initialized")
            except Exception as e:
                logger.warning(f"⚠️  Binance error: {e}")
        else:
            logger.warning("⚠️  Binance disabled (API keys not set)")
        
        # Initialize Telegram
        if telegram_bot and os.getenv('TELEGRAM_BOT_TOKEN'):
            try:
                await telegram_bot.initialize()
                logger.info("✓ Telegram bot initialized")
            except Exception as e:
                logger.warning(f"⚠️  Telegram error: {e}")
        else:
            logger.warning("⚠️  Telegram disabled (BOT_TOKEN not set)")
        
        logger.info("=" * 60)
        logger.info("✅ Startup Complete!")
        logger.info("=" * 60)
    
    async def run(self):
        """Run the main application"""
        logger.info("\n🚀 Bot Status:")
        
        # Start Telegram bot if configured
        if telegram_bot and os.getenv('TELEGRAM_BOT_TOKEN'):
            try:
                await telegram_bot.start()
                logger.info("  ▶️  Telegram bot: RUNNING")
            except Exception as e:
                logger.error(f"  ❌ Telegram bot error: {e}")
        else:
            logger.info("  ⏸️  Telegram bot: DISABLED")
        
        # Start signal engine if all configured
        if (signal_engine and 
            os.getenv('BINANCE_API_KEY') and 
            os.getenv('TELEGRAM_BOT_TOKEN')):
            try:
                asyncio.create_task(signal_engine.start())
                logger.info("  ▶️  Signal engine: RUNNING")
            except Exception as e:
                logger.error(f"  ❌ Signal engine error: {e}")
        else:
            logger.info("  ⏸️  Signal engine: DISABLED (missing config)")
        
        logger.info(f"\n📊 Configuration:")
        logger.info(f"  Mode: {'TESTNET' if os.getenv('BINANCE_TESTNET', 'true') == 'true' else 'LIVE'}")
        logger.info(f"  Health Check: http://0.0.0.0:8080/health")
        logger.info(f"  Status: http://0.0.0.0:8080/status")
        
        logger.info("\n✓ Bot is running! Press Ctrl+C to stop.")
        logger.info("=" * 60)
        
        # Keep running
        await self.shutdown_event.wait()
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("\n" + "=" * 60)
        logger.info("Shutting down...")
        logger.info("=" * 60)
        
        if telegram_bot:
            try:
                await telegram_bot.stop()
                logger.info("✓ Telegram stopped")
            except:
                pass
        
        if binance_client:
            try:
                await binance_client.close()
                logger.info("✓ Binance closed")
            except:
                pass
        
        if db:
            try:
                await db.close_async()
                logger.info("✓ Database closed")
            except:
                pass
        
        try:
            await health_server.stop()
            logger.info("✓ Health server stopped")
        except:
            pass
        
        logger.info("=" * 60)
        logger.info("Goodbye! 👋")
        logger.info("=" * 60)
    
    def handle_signal(self, sig):
        """Handle shutdown signals"""
        logger.info(f"\n⚠️  Received signal: {sig.name}")
        self.shutdown_event.set()


async def main():
    """Main entry point"""
    app = TradingBotApp()
    
    # Register signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            lambda s=sig: app.handle_signal(s)
        )
    
    try:
        await app.startup()
        await app.run()
    except KeyboardInterrupt:
        logger.info("\n⚠️  Keyboard interrupt")
    except Exception as e:
        logger.exception(f"\n❌ Fatal error: {e}")
    finally:
        await app.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Failed to start: {e}")
        sys.exit(1)