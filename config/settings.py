# config/settings.py
"""
Core configuration for Options Signal Bot
All parameters in one place - easy to modify
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ==================== API CREDENTIALS ====================
# Zerodha Kite API
KITE_API_KEY = os.getenv('KITE_API_KEY', '')
KITE_API_SECRET = os.getenv('KITE_API_SECRET', '')
KITE_ACCESS_TOKEN = os.getenv('KITE_ACCESS_TOKEN', '')

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

# ==================== TRADING PARAMETERS ====================
# Capital Management
TOTAL_CAPITAL = 100000  # ₹1 Lakh
RISK_PER_TRADE = 0.01   # 1% risk per trade
MAX_TRADES_PER_DAY = 2
MIN_RISK_REWARD = 1.5   # Minimum 1:1.5 RR

# Instruments
INSTRUMENTS = ['NIFTY', 'BANKNIFTY']
EXPIRY_TYPE = 'WEEKLY'  # Weekly expiry only

# Strike Selection
STRIKE_RANGE = 1  # ATM or ATM ±1 only

# Liquidity Filters
MIN_VOLUME = 100        # Minimum 100 lots traded
MIN_OI = 1000          # Minimum Open Interest
MIN_BID_ASK_SPREAD = 0.50  # Max spread ₹0.50

# ==================== STRATEGY PARAMETERS ====================
# HTF (1 Hour) - Trend Filter
HTF_TIMEFRAME = '60minute'
HTF_EMA_FAST = 20
HTF_EMA_SLOW = 50
HTF_TREND_SEPARATION = 0.2  # 0.2% minimum separation
HTF_ALIGNMENT_CANDLES = 3   # Last 3 candles must align

# LTF (5 Minute) - Entry
LTF_TIMEFRAME = '5minute'
LTF_EMA_ENTRY = 9
VOLUME_LOOKBACK = 20       # Average volume over 20 candles
STRUCTURE_LOOKBACK = 10    # Last 10 candles for structure
VOLUME_MULTIPLIER = 1.0    # Volume must be >= average
STRUCTURE_VOLUME_MULTIPLIER = 1.2  # 20% above for structure break

# RSI Filter
RSI_PERIOD = 14
RSI_CALL_MIN = 45
RSI_CALL_MAX = 60
RSI_PUT_MIN = 40
RSI_PUT_MAX = 55

# Candle Quality
MIN_BODY_PERCENT = 0.6  # Body must be 60% of total range
MAX_WICK_PERCENT = 0.3  # Wick max 30% of body

# ==================== TIME FILTERS ====================
# Trading Hours (IST)
TRADING_START_HOUR = 9
TRADING_START_MINUTE = 20
TRADING_END_HOUR = 11
TRADING_END_MINUTE = 30

# Market Open/Close
MARKET_OPEN = "09:15"
MARKET_CLOSE = "15:30"

# ==================== RISK MANAGEMENT ====================
# Stop Loss
SL_TYPE = 'PREMIUM_BASED'  # Based on option premium
SL_PERCENT = 0.30          # 30% of entry premium

# Target
TARGET_MULTIPLIER = 1.5    # 1.5x of risk

# Circuit Breaker
CONSECUTIVE_LOSS_LIMIT = 1  # Stop after 1 loss

# ==================== DATA & LOGGING ====================
# Data Storage
DATA_DIR = './data/historical'
LOG_DIR = './logs'
BACKTEST_DIR = './backtest/results'

# Logging Level
LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR

# Data Refresh
DATA_REFRESH_INTERVAL = 60  # seconds

# ==================== BACKTEST PARAMETERS ====================
BACKTEST_START_DATE = '2024-01-01'
BACKTEST_END_DATE = '2024-12-31'
BACKTEST_INITIAL_CAPITAL = 100000

# ==================== SAFETY CHECKS ====================
# Prevent bad trades
MAX_OPTION_PREMIUM = 500    # Don't enter if premium > ₹500
MIN_OPTION_PREMIUM = 5      # Don't enter if premium < ₹5
MAX_DAILY_LOSS = 2000       # Stop if loss > ₹2000/day
MAX_POSITION_SIZE = 50      # Max lots per trade

# ==================== ALERT SETTINGS ====================
SEND_TEST_ALERTS = True     # Send test message on startup
ALERT_ON_ERROR = True       # Send telegram alert on errors
ALERT_ON_DAILY_SUMMARY = True  # End of day summary

# ==================== VALIDATION ====================
def validate_config():
    """Validate critical configuration before starting"""
    errors = []
    
    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN not set")
    
    if not TELEGRAM_CHAT_ID:
        errors.append("TELEGRAM_CHAT_ID not set")
    
    if RISK_PER_TRADE <= 0 or RISK_PER_TRADE > 0.05:
        errors.append("RISK_PER_TRADE must be between 0 and 0.05 (5%)")
    
    if MAX_TRADES_PER_DAY > 5:
        errors.append("MAX_TRADES_PER_DAY should not exceed 5")
    
    if MIN_RISK_REWARD < 1:
        errors.append("MIN_RISK_REWARD must be >= 1")
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    return True

# Validate on import
if __name__ != "__main__":
    validate_config()
