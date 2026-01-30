# 🚀 Crypto Options Trading Signal Bot

একটি প্রফেশনাল ক্রিপ্টোকারেন্সি অপশন ট্রেডিং সিগন্যাল বট যা Binance থেকে রিয়েল-টাইম ডেটা নিয়ে Delta Exchange-এ ম্যানুয়াল ট্রেডের জন্য সিগন্যাল জেনারেট করে এবং Telegram-এ পাঠায়।

## ✨ Features

- **Real-time Market Analysis**: Binance WebSocket integration for live data
- **Multi-Timeframe Analysis**: 1m, 5m, 15m, 1h, 4h candles
- **Advanced Technical Analysis**: EMA, RSI, ADX, ATR, MACD, Bollinger Bands
- **Confluence Scoring**: 10-point rating system for signal quality
- **Risk Management**: Automated position sizing, R:R validation
- **Market Context Filters**: Funding rate, OI changes, liquidation clusters
- **Session Awareness**: London/NY overlap detection
- **Paper Trading Mode**: Track virtual P&L
- **Telegram Integration**: Interactive buttons for trade management
- **PostgreSQL Database**: Full trade history and statistics
- **Railway.app Ready**: One-click deployment

## 📋 Requirements

- Python 3.11+
- PostgreSQL database
- Binance API key (Testnet or Live)
- Telegram Bot Token
- Railway.app account (for deployment)

## 🛠️ Installation

### Local Development

1. **Clone the repository**
```bash
git clone <repository-url>
cd crypto_options_bot
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Install TA-Lib** (required for technical indicators)

**Linux/Mac:**
```bash
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
```

**Windows:**
Download pre-built wheel from: https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib

5. **Setup environment variables**
```bash
cp .env.example .env
# Edit .env with your credentials
```

6. **Initialize database**
```bash
# Database will auto-initialize on first run
```

7. **Run the bot**
```bash
python main.py
```

## 🚢 Railway.app Deployment

### Step 1: Prepare Your Repository

1. Push code to GitHub/GitLab
2. Ensure all files are committed

### Step 2: Create Railway Project

1. Go to [Railway.app](https://railway.app)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository

### Step 3: Add PostgreSQL Database

1. In Railway dashboard, click "New"
2. Select "Database" → "PostgreSQL"
3. Railway will automatically set `DATABASE_URL`

### Step 4: Configure Environment Variables

Add these environment variables in Railway:

```
BINANCE_API_KEY=your_key
BINANCE_SECRET=your_secret
BINANCE_TESTNET=true
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
RISK_PER_TRADE=0.02
LOG_LEVEL=INFO
```

### Step 5: Deploy

1. Railway will automatically build and deploy
2. Check logs for any errors
3. Visit health check: `https://your-app.up.railway.app/health`

## 📱 Telegram Bot Setup

### Create Bot

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot`
3. Follow instructions to get bot token
4. Add token to `.env` as `TELEGRAM_BOT_TOKEN`

### Get Chat ID

1. Message your bot
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Find `chat.id` in the response
4. Add to `.env` as `TELEGRAM_CHAT_ID`

### Bot Commands

- `/start` - Start the bot
- `/help` - Show help message
- `/signal` - Force check for signals
- `/stats` - View trading statistics
- `/settings` - View current settings
- `/paper` - View paper trading results

## 🔧 Configuration

### Trading Settings (`config/settings.py`)

```python
# Signal generation
SIGNAL_CHECK_INTERVAL = 900  # 15 minutes

# Risk management
RISK_PER_TRADE = 0.02  # 2% per trade
MIN_RISK_REWARD = 2.0  # Minimum 1:2 R:R

# Technical thresholds
ADX_THRESHOLD = 25.0
RSI_LOWER = 40.0
RSI_UPPER = 60.0

# Trading pairs
TRADING_PAIRS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", 
    "SOLUSDT", "ADAUSDT"
]
```

## 📊 Signal Format

```
🎯 LONG CALL SIGNAL - BTCUSDT

📊 Option Details:
• Strike: $50,000 (OTM)
• Expiry: 2024-12-15
• Premium Estimate: $500

📈 Entry Setup:
• Entry Zone: $49,500 - $49,700
• Stop Loss: $49,000
• Take Profit 1: $50,500 (50%)
• Take Profit 2: $51,000 (30%)
• Take Profit 3: $51,500 (20%)

⚙️ Setup Logic:
EMA 20 pullback on 15m + RSI bounce at 45.2 + Volume spike (1.5x avg)

💰 Risk Management:
• Risk Amount: $200 (2.0%)
• Risk:Reward = 1:2.0
• Max Hold: 48h

🔥 Confluence Score: 8.5/10
```

## 🎯 Strategy Logic

### Higher Timeframe (4h/1h) - Trend Direction

1. **EMA Alignment**: 50/200 cross confirmation
2. **ADX Strength**: ADX > 25
3. **Price Action**: Price above/below EMAs

### Lower Timeframe (15m/5m) - Entry Trigger

1. **Pullback**: Price near EMA 20
2. **RSI Bounce**: RSI 40-60 zone
3. **Volume**: Above 20-period average
4. **Pattern**: Hammer, Engulfing, etc.

### Market Context Filters

1. **Funding Rate**: ±0.1% extremes
2. **Open Interest**: 5%+ changes
3. **Liquidations**: Cluster detection
4. **BTC Correlation**: Filter altcoins
5. **Session**: London/NY overlap preference

## 📈 Performance Tracking

The bot tracks:

- Win rate
- Profit factor
- Max drawdown
- Daily/weekly/monthly statistics
- Paper trade P&L

## ⚠️ Warnings & Limits

- Max 3 signals per day
- Pauses after 2 consecutive losses
- Holds max 48 hours
- Skips during high-impact events (FOMC, NFP)

## 🔒 Security

- Never commit `.env` file
- Use testnet for initial testing
- Keep API keys secure
- Use read-only API keys if possible

## 📝 Logging

Logs are stored in JSON format:

```json
{
  "timestamp": "2024-01-30T12:00:00",
  "level": "INFO",
  "logger": "signal_engine",
  "message": "Signal generated: BTCUSDT LONG_CALL"
}
```

## 🐛 Troubleshooting

### TA-Lib Installation Issues

```bash
# Linux
sudo apt-get install python3-dev

# Mac
brew install ta-lib
```

### Database Connection Failed

```bash
# Check DATABASE_URL format
postgresql://user:password@host:port/database
```

### WebSocket Disconnects

The bot auto-reconnects with exponential backoff.

### Rate Limit Errors

Built-in rate limiting respects Binance's 1200/min limit.

## 📚 Documentation

- [Binance API Docs](https://binance-docs.github.io/apidocs/)
- [python-telegram-bot](https://docs.python-telegram-bot.org/)
- [TA-Lib Indicators](https://mrjbq7.github.io/ta-lib/)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## ⚖️ Disclaimer

**This bot is for educational purposes only. Trading cryptocurrencies involves substantial risk of loss. Past performance is not indicative of future results. Always do your own research and never invest more than you can afford to lose.**

## 📄 License

MIT License - See LICENSE file for details

## 📧 Support

For issues and questions:
- GitHub Issues
- Telegram: @your_support_channel

---

**Made with ❤️ for the crypto trading community**