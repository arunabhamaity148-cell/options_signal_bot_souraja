"""
Configuration settings for Crypto Options Trading Signal Bot
"""
import os
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings and configuration"""
    
    # API Credentials
    BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "")
    BINANCE_SECRET: str = os.getenv("BINANCE_SECRET", "")
    BINANCE_TESTNET: bool = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
    
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/crypto_bot")
    DATABASE_POOL_SIZE: int = int(os.getenv("DATABASE_POOL_SIZE", "10"))
    
    # Trading Pairs
    TRADING_PAIRS: List[str] = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", 
        "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "MATICUSDT"
    ]
    
    # Timeframes
    TIMEFRAMES: List[str] = ["1m", "5m", "15m", "1h", "4h"]
    HIGHER_TIMEFRAMES: List[str] = ["1h", "4h"]
    LOWER_TIMEFRAMES: List[str] = ["5m", "15m"]
    
    # Signal Generation
    SIGNAL_CHECK_INTERVAL: int = 900  # 15 minutes in seconds
    MAX_DAILY_SIGNALS: int = 3
    CONSECUTIVE_LOSS_PAUSE: int = 2
    PAUSE_DURATION_HOURS: int = 24
    
    # Technical Indicators Thresholds
    EMA_FAST: int = 20
    EMA_SLOW_1: int = 50
    EMA_SLOW_2: int = 200
    RSI_PERIOD: int = 14
    RSI_LOWER: float = 40.0
    RSI_UPPER: float = 60.0
    ADX_PERIOD: int = 14
    ADX_THRESHOLD: float = 25.0
    ATR_PERIOD: int = 14
    ATR_SL_MULTIPLIER: float = 1.5
    VOLUME_MA_PERIOD: int = 20
    
    # Market Context Filters
    FUNDING_RATE_EXTREME: float = 0.001  # ±0.1%
    OI_CHANGE_THRESHOLD: float = 0.05  # 5%
    BTC_CORRELATION_THRESHOLD: float = 0.8
    BTC_ADX_MIN: float = 20.0
    
    # Options Parameters
    OPTION_ATM_RANGE: float = 0.02  # 2% OTM range
    OPTION_MIN_EXPIRY_DAYS: int = 7
    OPTION_MAX_EXPIRY_DAYS: int = 14
    
    # Risk Management
    RISK_PER_TRADE: float = float(os.getenv("RISK_PER_TRADE", "0.02"))  # 2%
    MIN_RISK_REWARD: float = 2.0
    MAX_HOLD_HOURS: int = 48
    
    # Confluence Scoring
    MIN_CONFLUENCE_SCORE: float = 7.0
    MAX_CONFLUENCE_SCORE: float = 10.0
    
    # Trading Sessions (UTC)
    LONDON_SESSION: tuple = (7, 16)
    NY_SESSION: tuple = (12, 21)
    
    # Economic Calendar (pause hours before event)
    HIGH_IMPACT_PAUSE_HOURS: int = 2
    
    # API Rate Limits
    BINANCE_RATE_LIMIT: int = 1200  # per minute
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "json"
    LOG_FILE: str = "logs/trading_bot.log"
    
    # Health Check
    HEALTH_CHECK_PORT: int = int(os.getenv("PORT", "8080"))
    
    # Backtesting
    BACKTEST_MONTHS: int = 6
    BACKTEST_WALK_FORWARD_WINDOW: int = 30  # days
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required settings"""
        required = [
            cls.BINANCE_API_KEY,
            cls.BINANCE_SECRET,
            cls.TELEGRAM_BOT_TOKEN,
            cls.TELEGRAM_CHAT_ID,
            cls.DATABASE_URL
        ]
        return all(required)
    
    @classmethod
    def get_binance_endpoint(cls) -> str:
        """Get Binance API endpoint based on testnet setting"""
        if cls.BINANCE_TESTNET:
            return "https://testnet.binance.vision/api"
        return "https://api.binance.com/api"
    
    @classmethod
    def get_binance_ws_endpoint(cls) -> str:
        """Get Binance WebSocket endpoint"""
        if cls.BINANCE_TESTNET:
            return "wss://testnet.binance.vision/ws"
        return "wss://stream.binance.com:9443/ws"


# Pattern Recognition
BULLISH_PATTERNS: List[str] = [
    "hammer", "inverted_hammer", "bullish_engulfing", 
    "morning_star", "three_white_soldiers"
]

BEARISH_PATTERNS: List[str] = [
    "shooting_star", "hanging_man", "bearish_engulfing",
    "evening_star", "three_black_crows"
]

# Signal Templates
SIGNAL_TEMPLATE: str = """
🎯 **{direction} SIGNAL** - {pair}

📊 **Option Details:**
• Strike: ${strike:,.2f} ({strike_type})
• Expiry: {expiry}
• Premium Estimate: ${premium:,.2f}

📈 **Entry Setup:**
• Entry Zone: ${entry_min:,.2f} - ${entry_max:,.2f}
• Stop Loss: ${stop_loss:,.2f}
• Take Profit 1: ${tp1:,.2f} (50%)
• Take Profit 2: ${tp2:,.2f} (30%)
• Take Profit 3: ${tp3:,.2f} (20%)

⚙️ **Setup Logic:**
{logic}

💰 **Risk Management:**
• Risk Amount: ${risk_amount:,.2f} ({risk_percent:.1f}%)
• Risk:Reward = 1:{risk_reward:.1f}
• Max Hold: {max_hold}h

🔥 **Confluence Score: {confluence}/10**

⏰ Generated: {timestamp}

#{pair} #{direction}
"""

settings = Settings()