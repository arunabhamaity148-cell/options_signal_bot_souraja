# main.py
"""
Options Signal Bot - Main Orchestrator

This is the entry point that:
1. Fetches market data
2. Runs signal generation
3. Sends Telegram alerts
4. Manages daily resets

Run: python main.py
"""

import time
import schedule
from datetime import datetime, time as dt_time
import pytz
from loguru import logger
import sys
import os

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)
logger.add(
    "logs/bot_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    level="DEBUG"
)

# Import components
from signal_generator import SignalGenerator
from telegram_bot import TelegramAlerter

# Import settings
from settings import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TOTAL_CAPITAL,
    RISK_PER_TRADE,
    MAX_TRADES_PER_DAY,
    INSTRUMENTS,
    TRADING_START_HOUR,
    TRADING_START_MINUTE,
    TRADING_END_HOUR,
    TRADING_END_MINUTE,
    DATA_REFRESH_INTERVAL
)


class OptionsBot:
    """
    Main bot orchestrator
    """
    
    def __init__(self):
        self.timezone = pytz.timezone('Asia/Kolkata')
        
        # Initialize components
        logger.info("Initializing Options Signal Bot...")
        
        self.signal_generator = SignalGenerator(
            capital=TOTAL_CAPITAL,
            risk_per_trade=RISK_PER_TRADE,
            max_trades=MAX_TRADES_PER_DAY
        )
        
        self.telegram = TelegramAlerter(
            bot_token=TELEGRAM_BOT_TOKEN,
            chat_id=TELEGRAM_CHAT_ID
        )
        
        self.is_running = False
        self.signals_sent_today = 0
        
        logger.info("✓ Bot initialized successfully")
    
    def fetch_market_data(self, index: str):
        """
        Fetch 1H and 5M data for given index
        
        In production: Use Zerodha Kite API
        For now: Returns dummy data structure
        
        Returns:
            {
                'df_1h': pd.DataFrame,
                'df_5m': pd.DataFrame,
                'spot': float,
                'atm_strike': int,
                'lot_size': int
            }
        """
        
        # TODO: Replace with actual Kite API calls
        # Example:
        # from kiteconnect import KiteConnect
        # kite = KiteConnect(api_key=KITE_API_KEY)
        # kite.set_access_token(KITE_ACCESS_TOKEN)
        # 
        # instrument_token = get_instrument_token(index)
        # df_1h = kite.historical_data(instrument_token, from_date, to_date, '60minute')
        # df_5m = kite.historical_data(instrument_token, from_date, to_date, '5minute')
        
        logger.warning(f"Using dummy data for {index} - implement actual API")
        
        # Dummy data structure
        return {
            'df_1h': None,
            'df_5m': None,
            'spot': 22500.0 if index == 'NIFTY' else 48500.0,
            'atm_strike': 22500 if index == 'NIFTY' else 48500,
            'lot_size': 50 if index == 'NIFTY' else 25
        }
    
    def check_trading_hours(self) -> bool:
        """Check if within trading hours"""
        now = datetime.now(self.timezone)
        current_time = now.time()
        
        start = dt_time(TRADING_START_HOUR, TRADING_START_MINUTE)
        end = dt_time(TRADING_END_HOUR, TRADING_END_MINUTE)
        
        return start <= current_time <= end
    
    def scan_markets(self):
        """
        Main scanning loop
        Called every DATA_REFRESH_INTERVAL seconds
        """
        
        if not self.check_trading_hours():
            logger.debug("Outside trading hours - skipping scan")
            return
        
        logger.info(f"\n{'='*60}")
        logger.info("MARKET SCAN STARTED")
        logger.info(f"{'='*60}")
        
        for index in INSTRUMENTS:
            logger.info(f"\nScanning {index}...")
            
            try:
                # Fetch data
                data = self.fetch_market_data(index)
                
                if data['df_1h'] is None or data['df_5m'] is None:
                    logger.warning(f"No data available for {index}")
                    continue
                
                # Generate signal
                signal = self.signal_generator.generate_signal(
                    df_1h=data['df_1h'],
                    df_5m=data['df_5m'],
                    index_name=index,
                    current_spot=data['spot'],
                    atm_strike=data['atm_strike'],
                    lot_size=data['lot_size']
                )
                
                # Send signal if valid
                if signal:
                    logger.info(f"✓ Valid signal for {index} - sending to Telegram")
                    
                    success = self.telegram.send_signal_sync(signal)
                    
                    if success:
                        self.signals_sent_today += 1
                        logger.info(f"✓ Signal sent (total today: {self.signals_sent_today})")
                    else:
                        logger.error("✗ Failed to send Telegram signal")
                else:
                    logger.info(f"No signal for {index}")
                    
            except Exception as e:
                logger.error(f"Error scanning {index}: {e}")
                # Send error alert
                try:
                    self.telegram.send_message_sync(
                        self.telegram.format_error_alert(f"Error in {index} scan: {str(e)}")
                    )
                except:
                    pass
        
        logger.info(f"\n{'='*60}")
        logger.info("SCAN COMPLETE")
        logger.info(f"{'='*60}\n")
    
    def send_daily_summary(self):
        """
        Send end-of-day summary
        """
        logger.info("Sending daily summary...")
        
        summary = self.signal_generator.get_daily_summary()
        
        summary_data = {
            'date': datetime.now(self.timezone).strftime('%Y-%m-%d'),
            'total_signals': self.signals_sent_today,
            'trades_taken': summary['trades_taken'],
            'pnl': summary['daily_pnl'],
            'win_rate': 0.0  # Calculate if tracking individual trades
        }
        
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            loop.run_until_complete(
                self.telegram.send_daily_summary(summary_data)
            )
            logger.info("✓ Daily summary sent")
        except Exception as e:
            logger.error(f"Failed to send daily summary: {e}")
    
    def reset_day(self):
        """
        Reset counters for new day
        """
        logger.info("=" * 60)
        logger.info("NEW TRADING DAY")
        logger.info("=" * 60)
        
        self.signal_generator.reset_day()
        self.signals_sent_today = 0
        
        logger.info("Counters reset - ready for new day")
    
    def start(self):
        """
        Start the bot
        """
        logger.info("\n" + "=" * 60)
        logger.info("OPTIONS SIGNAL BOT STARTING")
        logger.info("=" * 60 + "\n")
        
        # Send startup message
        logger.info("Sending startup notification...")
        self.telegram.send_test_message_sync()
        
        # Schedule jobs
        logger.info("Setting up schedules...")
        
        # Scan every DATA_REFRESH_INTERVAL seconds during trading hours
        schedule.every(DATA_REFRESH_INTERVAL).seconds.do(self.scan_markets)
        
        # Daily summary at market close
        schedule.every().day.at("15:35").do(self.send_daily_summary)
        
        # Daily reset at 9:00 AM
        schedule.every().day.at("09:00").do(self.reset_day)
        
        logger.info(f"✓ Scheduled scan every {DATA_REFRESH_INTERVAL} seconds")
        logger.info("✓ Daily summary at 15:35")
        logger.info("✓ Daily reset at 09:00")
        
        self.is_running = True
        
        logger.info("\n" + "=" * 60)
        logger.info("BOT IS LIVE - Monitoring markets...")
        logger.info("=" * 60 + "\n")
        
        # Main loop
        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("\n" + "=" * 60)
            logger.info("SHUTDOWN REQUESTED")
            logger.info("=" * 60)
            self.stop()
    
    def stop(self):
        """
        Stop the bot gracefully
        """
        self.is_running = False
        
        logger.info("Sending shutdown notification...")
        try:
            self.telegram.send_message_sync(
                "🛑 Bot stopped. Manual shutdown."
            )
        except:
            pass
        
        logger.info("=" * 60)
        logger.info("BOT STOPPED")
        logger.info("=" * 60)


def main():
    """
    Entry point
    """
    
    # Validate environment
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("❌ TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env")
        logger.info("\nCreate a .env file with:")
        logger.info("TELEGRAM_BOT_TOKEN=your_bot_token")
        logger.info("TELEGRAM_CHAT_ID=your_chat_id")
        sys.exit(1)
    
    # Create and start bot
    bot = OptionsBot()
    bot.start()


if __name__ == "__main__":
    main()
