# data/nse_fetcher.py
"""
FREE data fetcher using NSE India official website
No API key needed - direct scraping (legal for personal use)
"""

import requests
import pandas as pd
import json
from datetime import datetime, timedelta
import time
from loguru import logger


class NSEFetcher:
    """
    Fetch live data from NSE website (FREE)
    """
    
    def __init__(self):
        self.base_url = "https://www.nseindia.com"
        self.session = requests.Session()
        
        # Required headers to bypass NSE checks
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.nseindia.com/'
        }
        
        self.session.headers.update(self.headers)
        
        # Initialize session (important for NSE)
        self._init_session()
    
    def _init_session(self):
        """Initialize session by hitting homepage"""
        try:
            self.session.get(self.base_url, timeout=10)
            logger.info("✓ NSE session initialized")
        except Exception as e:
            logger.error(f"Failed to init NSE session: {e}")
    
    def get_index_spot(self, symbol: str) -> dict:
        """
        Get current spot price of NIFTY/BANKNIFTY
        
        Args:
            symbol: 'NIFTY' or 'BANKNIFTY'
            
        Returns:
            {
                'symbol': str,
                'last_price': float,
                'change': float,
                'pct_change': float,
                'timestamp': str
            }
        """
        
        try:
            # NSE indices endpoint
            url = f"{self.base_url}/api/allIndices"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Find the index
            for index in data.get('data', []):
                if index.get('index') == symbol:
                    return {
                        'symbol': symbol,
                        'last_price': float(index.get('last', 0)),
                        'change': float(index.get('change', 0)),
                        'pct_change': float(index.get('percentChange', 0)),
                        'timestamp': datetime.now().isoformat()
                    }
            
            logger.warning(f"Index {symbol} not found in NSE data")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching spot price: {e}")
            return None
    
    def get_option_chain(self, symbol: str) -> pd.DataFrame:
        """
        Get option chain data (FREE from NSE)
        
        Args:
            symbol: 'NIFTY' or 'BANKNIFTY'
            
        Returns:
            DataFrame with option chain
        """
        
        try:
            # Option chain endpoint
            if symbol == 'NIFTY':
                url = f"{self.base_url}/api/option-chain-indices?symbol=NIFTY"
            elif symbol == 'BANKNIFTY':
                url = f"{self.base_url}/api/option-chain-indices?symbol=NIFTY%20BANK"
            else:
                logger.error(f"Unknown symbol: {symbol}")
                return None
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse option chain
            records = data.get('records', {})
            option_data = records.get('data', [])
            
            if not option_data:
                logger.warning("No option chain data available")
                return None
            
            # Extract CE and PE data
            rows = []
            for item in option_data:
                strike = item.get('strikePrice')
                
                ce = item.get('CE', {})
                pe = item.get('PE', {})
                
                rows.append({
                    'strike': strike,
                    'ce_ltp': ce.get('lastPrice', 0),
                    'ce_volume': ce.get('totalTradedVolume', 0),
                    'ce_oi': ce.get('openInterest', 0),
                    'ce_iv': ce.get('impliedVolatility', 0),
                    'ce_bid': ce.get('bidprice', 0),
                    'ce_ask': ce.get('askPrice', 0),
                    'pe_ltp': pe.get('lastPrice', 0),
                    'pe_volume': pe.get('totalTradedVolume', 0),
                    'pe_oi': pe.get('openInterest', 0),
                    'pe_iv': pe.get('impliedVolatility', 0),
                    'pe_bid': pe.get('bidprice', 0),
                    'pe_ask': pe.get('askPrice', 0)
                })
            
            df = pd.DataFrame(rows)
            logger.info(f"✓ Fetched option chain: {len(df)} strikes")
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching option chain: {e}")
            return None
    
    def get_atm_option_premium(self, symbol: str, option_type: str) -> dict:
        """
        Get ATM option premium
        
        Args:
            symbol: 'NIFTY' or 'BANKNIFTY'
            option_type: 'CE' or 'PE'
            
        Returns:
            {
                'strike': int,
                'ltp': float,
                'volume': int,
                'oi': int,
                'bid': float,
                'ask': float
            }
        """
        
        # Get spot price
        spot_data = self.get_index_spot(symbol)
        if not spot_data:
            return None
        
        spot = spot_data['last_price']
        
        # Calculate ATM strike
        if symbol == 'NIFTY':
            strike_gap = 50
        else:
            strike_gap = 100
        
        atm_strike = round(spot / strike_gap) * strike_gap
        
        # Get option chain
        chain = self.get_option_chain(symbol)
        if chain is None or chain.empty:
            return None
        
        # Find ATM row
        atm_row = chain[chain['strike'] == atm_strike]
        
        if atm_row.empty:
            logger.warning(f"ATM strike {atm_strike} not found")
            return None
        
        atm_row = atm_row.iloc[0]
        
        if option_type == 'CE':
            return {
                'strike': int(atm_strike),
                'ltp': float(atm_row['ce_ltp']),
                'volume': int(atm_row['ce_volume']),
                'oi': int(atm_row['ce_oi']),
                'bid': float(atm_row['ce_bid']),
                'ask': float(atm_row['ce_ask'])
            }
        else:  # PE
            return {
                'strike': int(atm_strike),
                'ltp': float(atm_row['pe_ltp']),
                'volume': int(atm_row['pe_volume']),
                'oi': int(atm_row['pe_oi']),
                'bid': float(atm_row['pe_bid']),
                'ask': float(atm_row['pe_ask'])
            }


class YahooFinanceFetcher:
    """
    Alternative: Use Yahoo Finance for historical data (FREE)
    """
    
    @staticmethod
    def get_historical_data(symbol: str, interval: str = '5m', period: str = '1d') -> pd.DataFrame:
        """
        Fetch historical data from Yahoo Finance
        
        Args:
            symbol: '^NSEI' for NIFTY, '^NSEBANK' for BANKNIFTY
            interval: '1m', '5m', '15m', '1h', '1d'
            period: '1d', '5d', '1mo'
            
        Returns:
            DataFrame with OHLCV data
        """
        
        try:
            import yfinance as yf
            
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            
            if df.empty:
                logger.warning(f"No data from Yahoo Finance for {symbol}")
                return None
            
            # Rename columns to match our format
            df = df.reset_index()
            df.columns = df.columns.str.lower()
            df = df.rename(columns={'date': 'datetime', 'datetime': 'datetime'})
            
            logger.info(f"✓ Fetched {len(df)} bars from Yahoo Finance")
            return df
            
        except ImportError:
            logger.error("yfinance not installed. Run: pip install yfinance")
            return None
        except Exception as e:
            logger.error(f"Error fetching Yahoo data: {e}")
            return None


# ==================== TESTING ====================
if __name__ == "__main__":
    
    print("=" * 60)
    print("TESTING NSE FREE DATA FETCHER")
    print("=" * 60)
    
    fetcher = NSEFetcher()
    
    # Test 1: Get spot price
    print("\nTest 1: Fetching NIFTY spot price...")
    spot = fetcher.get_index_spot('NIFTY')
    if spot:
        print(f"✓ NIFTY: ₹{spot['last_price']:.2f} ({spot['pct_change']:+.2f}%)")
    
    time.sleep(1)  # Rate limit
    
    # Test 2: Get BANKNIFTY spot
    print("\nTest 2: Fetching BANKNIFTY spot price...")
    spot = fetcher.get_index_spot('BANKNIFTY')
    if spot:
        print(f"✓ BANKNIFTY: ₹{spot['last_price']:.2f} ({spot['pct_change']:+.2f}%)")
    
    time.sleep(1)
    
    # Test 3: Get option chain
    print("\nTest 3: Fetching NIFTY option chain...")
    chain = fetcher.get_option_chain('NIFTY')
    if chain is not None:
        print(f"✓ Option chain loaded: {len(chain)} strikes")
        print("\nATM area:")
        print(chain[chain['strike'].between(22400, 22600)][['strike', 'ce_ltp', 'pe_ltp', 'ce_volume', 'pe_volume']])
    
    time.sleep(1)
    
    # Test 4: Get ATM premium
    print("\nTest 4: Fetching ATM CALL premium...")
    premium = fetcher.get_atm_option_premium('NIFTY', 'CE')
    if premium:
        print(f"✓ Strike: {premium['strike']}")
        print(f"  LTP: ₹{premium['ltp']:.2f}")
        print(f"  Volume: {premium['volume']}")
        print(f"  OI: {premium['oi']}")
        print(f"  Bid-Ask: ₹{premium['bid']:.2f} - ₹{premium['ask']:.2f}")
    
    print("\n" + "=" * 60)
    print("TESTING YAHOO FINANCE (HISTORICAL)")
    print("=" * 60)
    
    yahoo = YahooFinanceFetcher()
    
    # Test Yahoo Finance
    print("\nFetching 1D 5-minute data for NIFTY...")
    df = yahoo.get_historical_data('^NSEI', interval='5m', period='1d')
    if df is not None:
        print(f"✓ Fetched {len(df)} candles")
        print(df.tail())
