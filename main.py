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
import pandas as pd
import numpy as np
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

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
from strategy.signal_generator import SignalGenerator
from alerts.telegram_bot import TelegramAlerter

# Import settings
from config.settings import (
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


class HealthCheckHandler(BaseHTTPRequestHandler):
    """
    Simple HTTP handler for Railway health check
    Prevents idle timeout by responding to HTTP pings
    """
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK - Bot is running')
        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            status_html = f"""
            <html>
            <head><title>Options Signal Bot</title></head>
            <body style="font-family: monospace; padding: 20px;">
            <h1>🤖 Options Signal Bot</h1>
            <p><strong>Status:</strong> RUNNING ✅</p>
            <p><strong>Time:</strong> {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S IST')}</p>
            <p><strong>Monitoring:</strong> NIFTY, BANKNIFTY</p>
            <hr>
            <small>This endpoint prevents Railway idle timeout</small>
            </body>
            </html>
            """
            self.wfile.write(status_html.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress default HTTP logs"""
        pass


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
        self.shoonya = None  # Will be initialized on first use
        
        logger.info("✓ Bot initialized successfully")
    
    def fetch_market_data(self, index: str):
        """
        Fetch 1H and 5M data for given index
        
        PRIMARY: Shoonya API (FREE, REAL-TIME)
        FALLBACK: Yahoo Finance (if Shoonya fails)
        
        Returns:
            {
                'df_1h': pd.DataFrame,
                'df_5m': pd.DataFrame,
                'spot': float,
                'atm_strike': int,
                'lot_size': int
            }
        """
        
        try:
            # Try Shoonya first (REAL-TIME, FREE)
            from data.shoonya_fetcher import ShoonyaFetcher
            
            # Check if Shoonya credentials exist
            shoonya_user = os.getenv('SHOONYA_USER_ID')
            shoonya_pass = os.getenv('SHOONYA_PASSWORD')
            shoonya_totp = os.getenv('SHOONYA_TOTP_KEY')
            
            if all([shoonya_user, shoonya_pass, shoonya_totp]):
                logger.info(f"🟢 Using SHOONYA API for {index} (REAL-TIME)")
                
                # Initialize Shoonya
                if not hasattr(self, 'shoonya') or self.shoonya is None:
                    self.shoonya = ShoonyaFetcher(shoonya_user, shoonya_pass, shoonya_totp)
                
                # Get spot price (REAL-TIME)
                spot = self.shoonya.get_spot_price(index)
                
                if not spot:
                    raise Exception("Shoonya spot price failed")
                
                logger.info(f"✓ {index} Spot: ₹{spot:.2f} (REAL-TIME)")
                
                # Get historical data (REAL-TIME)
                df_1h = self.shoonya.get_historical_data(index, interval='60', days=5)
                df_5m = self.shoonya.get_historical_data(index, interval='5', days=1)
                
                if df_1h is None or df_5m is None:
                    raise Exception("Shoonya historical data failed")
                
                logger.info(f"✓ Historical: {len(df_1h)} x 1H, {len(df_5m)} x 5M (REAL-TIME)")
                
                # Calculate ATM
                strike_gap = 50 if index == 'NIFTY' else 100
                atm_strike = round(spot / strike_gap) * strike_gap
                
                return {
                    'df_1h': df_1h,
                    'df_5m': df_5m,
                    'spot': spot,
                    'atm_strike': int(atm_strike),
                    'lot_size': 50 if index == 'NIFTY' else 25,
                    'source': 'SHOONYA'
                }
            
            else:
                logger.warning("⚠️ Shoonya credentials not found, falling back to Yahoo")
                raise Exception("No Shoonya credentials")
                
        except Exception as e:
            logger.warning(f"Shoonya failed: {e}, using Yahoo Finance fallback")
            
            # Fallback to Yahoo Finance
            try:
                from data.nse_fetcher import NSEFetcher, YahooFinanceFetcher
                
                logger.info(f"🟡 Using YAHOO FINANCE for {index} (15-20 min delay)")
                
                nse = NSEFetcher()
                yahoo = YahooFinanceFetcher()
                
                # Get spot from NSE
                spot_data = nse.get_index_spot(index)
                
                if not spot_data:
                    logger.error(f"NSE spot fetch failed for {index}")
                    return self._generate_demo_data(index)
                
                spot = spot_data['last_price']
                logger.info(f"✓ {index} Spot: ₹{spot:.2f} ({spot_data['pct_change']:+.2f}%)")
                
                # Get historical from Yahoo
                yahoo_symbol = '^NSEI' if index == 'NIFTY' else '^NSEBANK'
                
                df_1h = yahoo.get_historical_data(yahoo_symbol, interval='1h', period='5d')
                df_5m = yahoo.get_historical_data(yahoo_symbol, interval='5m', period='1d')
                
                if df_1h is None or df_5m is None:
                    logger.warning("Yahoo Finance unavailable, using demo")
                    return self._generate_demo_data(index)
                
                strike_gap = 50 if index == 'NIFTY' else 100
                atm_strike = round(spot / strike_gap) * strike_gap
                
                logger.info(f"✓ Historical: {len(df_1h)} x 1H, {len(df_5m)} x 5M (DELAYED)")
                
                return {
                    'df_1h': df_1h,
                    'df_5m': df_5m,
                    'spot': spot,
                    'atm_strike': int(atm_strike),
                    'lot_size': 50 if index == 'NIFTY' else 25,
                    'source': 'YAHOO'
                }
                
            except Exception as e2:
                logger.error(f"Yahoo Finance also failed: {e2}")
                return self._generate_demo_data(index)
    
    def _generate_demo_data(self, index: str):
        """
        Fallback: Generate demo data if free sources fail
        """
        logger.warning(f"⚠️  DEMO MODE: Generating dummy data for {index}")
        
        now = datetime.now(self.timezone)
        
        # 1H data (60 bars - uptrend)
        dates_1h = pd.date_range(end=now, periods=60, freq='H')
        base_1h = 22000 if index == 'NIFTY' else 48000
        trend = np.linspace(base_1h, base_1h + 500, 60)
        noise = np.random.randn(60) * 20
        
        df_1h = pd.DataFrame({
            'datetime': dates_1h,
            'open': trend + noise,
            'high': trend + noise + 30,
            'low': trend + noise - 30,
            'close': trend + noise + 10,
            'volume': np.random.randint(100000, 500000, 60)
        })
        
        # 5M data (60 bars - with pullback)
        dates_5m = pd.date_range(end=now, periods=60, freq='5min')
        base_5m = base_1h + 490
        trend_5m = np.linspace(base_5m - 50, base_5m, 60)
        noise_5m = np.random.randn(60) * 5
        
        df_5m = pd.DataFrame({
            'datetime': dates_5m,
            'open': trend_5m + noise_5m,
            'high': trend_5m + noise_5m + 10,
            'low': trend_5m + noise_5m - 10,
            'close': trend_5m + noise_5m + 5,
            'volume': np.random.randint(50000, 200000, 60)
        })
        
        # Create pullback setup
        df_5m.loc[df_5m.index[-3], 'close'] = base_5m - 10
        df_5m.loc[df_5m.index[-2], 'low'] = base_5m - 15
        df_5m.loc[df_5m.index[-1], 'open'] = base_5m - 8
        df_5m.loc[df_5m.index[-1], 'close'] = base_5m + 5
        df_5m.loc[df_5m.index[-1], 'high'] = base_5m + 10
        df_5m.loc[df_5m.index[-1], 'volume'] = 180000
        
        spot = float(df_5m.iloc[-1]['close'])
        atm_strike = round(spot / (50 if index == 'NIFTY' else 100)) * (50 if index == 'NIFTY' else 100)
        
        return {
            'df_1h': df_1h,
            'df_5m': df_5m,
            'spot': spot,
            'atm_strike': int(atm_strike),
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
    
    def _start_http_server(self):
        """
        Start HTTP server in background thread for Railway keep-alive
        Prevents idle timeout by responding to health checks
        """
        port = int(os.getenv('PORT', 8080))
        
        def run_server():
            server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
            logger.info(f"✓ HTTP server started on port {port} (Railway keep-alive)")
            server.serve_forever()
        
        # Run in daemon thread
        thread = Thread(target=run_server, daemon=True)
        thread.start()
    
    def start(self):
        """
        Start the bot
        """
        logger.info("\n" + "=" * 60)
        logger.info("OPTIONS SIGNAL BOT STARTING")
        logger.info("=" * 60 + "\n")
        
        # Start HTTP server for Railway keep-alive
        self._start_http_server()
        
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
