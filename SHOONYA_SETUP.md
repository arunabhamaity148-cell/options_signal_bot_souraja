# data/shoonya_fetcher.py
"""
FREE Shoonya (Finvasia) API Integration
100% FREE - No monthly charges
Real-time data for NIFTY/BANKNIFTY

Setup:
1. Open account: https://shoonya.com/
2. Get API credentials (FREE)
3. No monthly charges unlike Zerodha
"""

import pandas as pd
from datetime import datetime, timedelta
import pytz
from loguru import logger

try:
    from NorenRestApiPy.NorenApi import NorenApi
    SHOONYA_AVAILABLE = True
except ImportError:
    SHOONYA_AVAILABLE = False
    logger.warning("Shoonya API not installed. Run: pip install NorenRestApiPy")


class ShoonyaFetcher:
    """
    FREE real-time data using Shoonya/Finvasia
    """
    
    def __init__(self, user_id: str, password: str, totp_key: str):
        """
        Initialize Shoonya connection
        
        Args:
            user_id: Your Shoonya user ID
            password: Your password
            totp_key: TOTP key from Shoonya (for 2FA)
        """
        
        if not SHOONYA_AVAILABLE:
            raise ImportError("Install: pip install NorenRestApiPy")
        
        self.api = NorenApi(
            host='https://api.shoonya.com/NorenWClientTP/',
            websocket='wss://api.shoonya.com/NorenWSTP/'
        )
        
        self.user_id = user_id
        self.timezone = pytz.timezone('Asia/Kolkata')
        
        # Login
        self._login(user_id, password, totp_key)
    
    def _login(self, user_id: str, password: str, totp_key: str):
        """Login to Shoonya"""
        
        try:
            import pyotp
            
            # Generate TOTP
            totp = pyotp.TOTP(totp_key).now()
            
            # Login
            ret = self.api.login(
                userid=user_id,
                password=password,
                twoFA=totp,
                vendor_code=user_id,
                api_secret=password,
                imei='abc1234'
            )
            
            if ret:
                logger.info("✓ Shoonya login successful (FREE API)")
            else:
                logger.error("Shoonya login failed")
                
        except Exception as e:
            logger.error(f"Shoonya login error: {e}")
    
    def get_spot_price(self, symbol: str) -> float:
        """
        Get real-time spot price
        
        Args:
            symbol: 'NIFTY' or 'BANKNIFTY'
            
        Returns:
            Current spot price
        """
        
        try:
            # Shoonya symbol format
            if symbol == 'NIFTY':
                token = '26000'  # NIFTY 50 token
            elif symbol == 'BANKNIFTY':
                token = '26009'  # BANK NIFTY token
            else:
                return None
            
            # Get quotes
            quote = self.api.get_quotes(
                exchange='NSE',
                token=token
            )
            
            if quote:
                ltp = float(quote.get('lp', 0))
                logger.info(f"✓ {symbol} Spot: ₹{ltp:.2f}")
                return ltp
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching spot: {e}")
            return None
    
    def get_historical_data(self, 
                           symbol: str,
                           interval: str = '5',
                           days: int = 5) -> pd.DataFrame:
        """
        Get historical candle data (FREE)
        
        Args:
            symbol: 'NIFTY' or 'BANKNIFTY'
            interval: '1', '5', '15', '60', 'D'
            days: Number of days of data
            
        Returns:
            DataFrame with OHLCV data
        """
        
        try:
            # Symbol mapping
            if symbol == 'NIFTY':
                token = '26000'
            elif symbol == 'BANKNIFTY':
                token = '26009'
            else:
                return None
            
            # Date range
            end_date = datetime.now(self.timezone)
            start_date = end_date - timedelta(days=days)
            
            # Fetch data
            ret = self.api.get_time_price_series(
                exchange='NSE',
                token=token,
                starttime=start_date.timestamp(),
                interval=interval
            )
            
            if not ret:
                logger.warning(f"No historical data for {symbol}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(ret)
            
            # Rename columns
            df = df.rename(columns={
                'time': 'datetime',
                'into': 'open',
                'inth': 'high',
                'intl': 'low',
                'intc': 'close',
                'v': 'volume'
            })
            
            # Convert types
            df['datetime'] = pd.to_datetime(df['datetime'])
            for col in ['open', 'high', 'low', 'close']:
                df[col] = df[col].astype(float)
            df['volume'] = df['volume'].astype(int)
            
            logger.info(f"✓ Fetched {len(df)} candles ({interval}m)")
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching historical: {e}")
            return None
    
    def get_option_chain(self, symbol: str, expiry: str = None) -> pd.DataFrame:
        """
        Get option chain data
        
        Args:
            symbol: 'NIFTY' or 'BANKNIFTY'
            expiry: Expiry date (DDMMMYY format, e.g. '30JAN26')
            
        Returns:
            DataFrame with option chain
        """
        
        try:
            # Get option chain
            ret = self.api.get_option_chain(
                exchange='NFO',
                tradingsymbol=symbol,
                strikeprice='',
                count=50
            )
            
            if not ret:
                return None
            
            # Parse and return
            df = pd.DataFrame(ret.get('values', []))
            
            logger.info(f"✓ Option chain: {len(df)} strikes")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching option chain: {e}")
            return None


# ==================== COMPARISON ====================
"""
SHOONYA (FREE) vs ZERODHA (PAID):

Feature                 | Shoonya FREE | Zerodha PAID
------------------------|--------------|-------------
Monthly Cost            | ₹0           | ₹2000
Historical Data         | ✅ Yes       | ✅ Yes
Real-time Quotes        | ✅ Yes       | ✅ Yes
Option Chain            | ✅ Yes       | ✅ Yes
WebSocket (Tick Data)   | ✅ Yes       | ✅ Yes
API Rate Limits         | Moderate     | High
Stability               | Good         | Excellent
Documentation           | Okay         | Excellent

VERDICT: Shoonya perfect for testing & small trading
         Zerodha for high-frequency or large capital
"""


# ==================== SETUP GUIDE ====================
"""
HOW TO SETUP SHOONYA (5 MINUTES):

1. Open Account:
   - Visit: https://shoonya.com/
   - Click "Open Account"
   - Complete KYC (Aadhaar + PAN)
   - Free Demat + Trading account

2. Enable API:
   - Login to Shoonya
   - Go to Settings > API
   - Generate API credentials
   - Enable TOTP (Google Authenticator)

3. Get TOTP Key:
   - In API settings, you'll get a QR code
   - Scan with Google Authenticator
   - Note down the SECRET KEY (totp_key)

4. Add to .env:
   SHOONYA_USER_ID=your_user_id
   SHOONYA_PASSWORD=your_password
   SHOONYA_TOTP_KEY=your_totp_secret_key

5. Install library:
   pip install NorenRestApiPy pyotp

DONE! Now you have FREE real-time data.
"""


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    user_id = os.getenv('SHOONYA_USER_ID')
    password = os.getenv('SHOONYA_PASSWORD')
    totp_key = os.getenv('SHOONYA_TOTP_KEY')
    
    if not all([user_id, password, totp_key]):
        print("⚠️ Set Shoonya credentials in .env:")
        print("SHOONYA_USER_ID=your_id")
        print("SHOONYA_PASSWORD=your_pass")
        print("SHOONYA_TOTP_KEY=your_totp_key")
        exit(1)
    
    print("=" * 60)
    print("TESTING SHOONYA FREE API")
    print("=" * 60)
    
    fetcher = ShoonyaFetcher(user_id, password, totp_key)
    
    # Test spot price
    nifty_spot = fetcher.get_spot_price('NIFTY')
    print(f"\nNIFTY Spot: ₹{nifty_spot:.2f}")
    
    # Test historical
    df_5m = fetcher.get_historical_data('NIFTY', interval='5', days=1)
    if df_5m is not None:
        print(f"\n5M Data: {len(df_5m)} candles")
        print(df_5m.tail())
    
    df_1h = fetcher.get_historical_data('NIFTY', interval='60', days=5)
    if df_1h is not None:
        print(f"\n1H Data: {len(df_1h)} candles")
        print(df_1h.tail())
