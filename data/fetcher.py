# data/fetcher.py
"""
Market data fetcher - integrates with Zerodha Kite API
"""

import pandas as pd
from datetime import datetime, timedelta
import pytz
from loguru import logger
from typing import Optional

try:
    from kiteconnect import KiteConnect
    KITE_AVAILABLE = True
except ImportError:
    KITE_AVAILABLE = False
    logger.warning("kiteconnect not installed")


class DataFetcher:
    """
    Fetch OHLCV data from Zerodha Kite
    """
    
    def __init__(self, api_key: str = None, access_token: str = None):
        """
        Initialize Kite connection
        
        Args:
            api_key: Kite API key
            access_token: Kite access token (generate daily)
        """
        
        self.api_key = api_key
        self.access_token = access_token
        self.kite = None
        self.timezone = pytz.timezone('Asia/Kolkata')
        
        if KITE_AVAILABLE and api_key and access_token:
            try:
                self.kite = KiteConnect(api_key=api_key)
                self.kite.set_access_token(access_token)
                logger.info("✓ Kite connection initialized")
            except Exception as e:
                logger.error(f"Kite connection failed: {e}")
                self.kite = None
        else:
            logger.warning("Kite not configured - using dummy data")
    
    def fetch_historical(self, 
                        instrument_token: int,
                        interval: str,
                        from_date: datetime,
                        to_date: datetime) -> Optional[pd.DataFrame]:
        """
        Fetch historical data from Kite
        
        Args:
            instrument_token: NSE instrument token
            interval: '5minute', '60minute', 'day'
            from_date: Start datetime
            to_date: End datetime
            
        Returns:
            DataFrame with OHLCV data
        """
        
        if not self.kite:
            logger.warning("Kite not available - returning None")
            return None
        
        try:
            data = self.kite.historical_data(
                instrument_token=instrument_token,
                from_date=from_date,
                to_date=to_date,
                interval=interval,
                continuous=False,
                oi=True
            )
            
            if not data:
                logger.warning(f"No data returned for token {instrument_token}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            df['datetime'] = pd.to_datetime(df['date'])
            df = df.drop('date', axis=1)
            
            logger.info(f"Fetched {len(df)} candles for interval {interval}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return None
    
    def fetch_1h_data(self, instrument_token: int, bars: int = 60) -> Optional[pd.DataFrame]:
        """
        Fetch last N bars of 1H data
        
        Args:
            instrument_token: NSE token
            bars: Number of bars to fetch
            
        Returns:
            DataFrame with 1H OHLCV
        """
        
        now = datetime.now(self.timezone)
        from_date = now - timedelta(days=bars // 6)  # ~6 bars per day
        
        return self.fetch_historical(
            instrument_token=instrument_token,
            interval='60minute',
            from_date=from_date,
            to_date=now
        )
    
    def fetch_5m_data(self, instrument_token: int, bars: int = 60) -> Optional[pd.DataFrame]:
        """
        Fetch last N bars of 5M data
        
        Args:
            instrument_token: NSE token
            bars: Number of bars to fetch
            
        Returns:
            DataFrame with 5M OHLCV
        """
        
        now = datetime.now(self.timezone)
        from_date = now - timedelta(hours=bars // 12)  # ~12 bars per hour
        
        return self.fetch_historical(
            instrument_token=instrument_token,
            interval='5minute',
            from_date=from_date,
            to_date=now
        )
    
    def get_ltp(self, instrument_token: int) -> Optional[float]:
        """
        Get Last Traded Price
        
        Args:
            instrument_token: NSE token
            
        Returns:
            LTP as float
        """
        
        if not self.kite:
            return None
        
        try:
            ltp_data = self.kite.ltp([f"NSE:{instrument_token}"])
            ltp = ltp_data[f"NSE:{instrument_token}"]['last_price']
            return float(ltp)
        except Exception as e:
            logger.error(f"Error fetching LTP: {e}")
            return None
    
    def get_option_chain(self, symbol: str, expiry: str) -> Optional[pd.DataFrame]:
        """
        Fetch option chain data
        
        Args:
            symbol: 'NIFTY' or 'BANKNIFTY'
            expiry: Expiry date (YYYY-MM-DD)
            
        Returns:
            DataFrame with option chain
        """
        
        # TODO: Implement option chain fetching
        # Kite doesn't provide direct option chain API
        # Need to fetch individual strikes or use alternate source
        
        logger.warning("Option chain fetching not implemented")
        return None


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    api_key = os.getenv('KITE_API_KEY')
    access_token = os.getenv('KITE_ACCESS_TOKEN')
    
    fetcher = DataFetcher(api_key, access_token)
    
    # Test fetch (NIFTY token)
    if fetcher.kite:
        df_1h = fetcher.fetch_1h_data(instrument_token=256265, bars=60)
        if df_1h is not None:
            print("\n1H Data:")
            print(df_1h.tail())
        
        df_5m = fetcher.fetch_5m_data(instrument_token=256265, bars=60)
        if df_5m is not None:
            print("\n5M Data:")
            print(df_5m.tail())
    else:
        print("Kite not configured")