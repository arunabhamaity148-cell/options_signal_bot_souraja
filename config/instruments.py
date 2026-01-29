# config/instruments.py
"""
Instrument configuration and strike selection logic
"""

from datetime import datetime, timedelta
import pytz


class InstrumentConfig:
    """
    NSE Index Options configuration
    """
    
    NIFTY = {
        'symbol': 'NIFTY',
        'lot_size': 50,
        'strike_gap': 50,
        'token': 256265  # NSE instrument token
    }
    
    BANKNIFTY = {
        'symbol': 'BANKNIFTY',
        'lot_size': 25,
        'strike_gap': 100,
        'token': 260105
    }
    
    @staticmethod
    def get_atm_strike(spot_price: float, symbol: str) -> int:
        """
        Calculate ATM strike for given spot price
        
        Args:
            spot_price: Current spot price
            symbol: 'NIFTY' or 'BANKNIFTY'
            
        Returns:
            ATM strike price (rounded to nearest strike)
        """
        
        if symbol == 'NIFTY':
            strike_gap = 50
        elif symbol == 'BANKNIFTY':
            strike_gap = 100
        else:
            raise ValueError(f"Unknown symbol: {symbol}")
        
        # Round to nearest strike
        atm = round(spot_price / strike_gap) * strike_gap
        return int(atm)
    
    @staticmethod
    def get_weekly_expiry() -> str:
        """
        Get current week's expiry date
        
        NIFTY: Thursday
        BANKNIFTY: Wednesday
        
        Returns:
            Expiry date string (YYYY-MM-DD)
        """
        
        ist = pytz.timezone('Asia/Kolkata')
        today = datetime.now(ist)
        
        # NIFTY expires on Thursday (weekday = 3)
        days_until_thursday = (3 - today.weekday()) % 7
        
        if days_until_thursday == 0 and today.hour >= 15:
            # After 3 PM Thursday, move to next week
            days_until_thursday = 7
        
        expiry = today + timedelta(days=days_until_thursday)
        return expiry.strftime('%Y-%m-%d')
    
    @staticmethod
    def get_option_symbol(symbol: str, strike: int, option_type: str, expiry: str) -> str:
        """
        Generate NSE option symbol
        
        Format: NIFTY24JAN22500CE
        
        Args:
            symbol: NIFTY/BANKNIFTY
            strike: Strike price
            option_type: 'CALL' or 'PUT'
            expiry: Expiry date (YYYY-MM-DD)
            
        Returns:
            Option symbol string
        """
        
        # Parse expiry
        exp_dt = datetime.strptime(expiry, '%Y-%m-%d')
        
        # Year (last 2 digits)
        year = exp_dt.strftime('%y')
        
        # Month (3 letters uppercase)
        month = exp_dt.strftime('%b').upper()
        
        # CE or PE
        opt_type = 'CE' if option_type == 'CALL' else 'PE'
        
        # Build symbol
        option_symbol = f"{symbol}{year}{month}{strike}{opt_type}"
        
        return option_symbol


if __name__ == "__main__":
    # Test
    config = InstrumentConfig()
    
    print("NIFTY ATM:", config.get_atm_strike(22545.30, 'NIFTY'))
    print("BANKNIFTY ATM:", config.get_atm_strike(48235.60, 'BANKNIFTY'))
    print("Weekly Expiry:", config.get_weekly_expiry())
    print("Option Symbol:", config.get_option_symbol('NIFTY', 22500, 'CALL', '2024-01-18'))