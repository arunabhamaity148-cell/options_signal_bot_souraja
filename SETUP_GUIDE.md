# 🚀 Quick Setup Guide

## Railway.app Deployment (Recommended)

### 1. Upload to GitHub
```bash
cd crypto_options_bot
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-github-repo>
git push -u origin main
```

### 2. Create Railway Project

1. Go to https://railway.app
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository

### 3. Add PostgreSQL Database

1. Click "New" in Railway dashboard
2. Select "Database" → "PostgreSQL"
3. `DATABASE_URL` will be set automatically

### 4. Set Environment Variables

In Railway Variables tab:
```
BINANCE_API_KEY=your_key
BINANCE_SECRET=your_secret
BINANCE_TESTNET=true
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
RISK_PER_TRADE=0.02
LOG_LEVEL=INFO
```

### 5. Deploy

Railway will automatically build and deploy. Check logs.

---

## Local Development (Docker)
```bash
cp .env.example .env
# Edit .env
docker-compose up -d
```

Bot runs at http://localhost:8080/health

---

## Telegram Bot Setup

### 1. Create Bot

1. Open @BotFather on Telegram
2. Send `/newbot`
3. Follow instructions
4. Copy token

### 2. Get Chat ID

1. Message your bot
2. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Find `chat.id`

---

## Binance API Setup

### Testnet (Start Here)

1. Go to https://testnet.binance.vision/
2. Sign up
3. Create API Key
4. Set `BINANCE_TESTNET=true`

### Live (Later)

1. Login to Binance.com
2. API Management
3. Create API Key (READ-ONLY)
4. Set IP whitelist
5. Set `BINANCE_TESTNET=false`

---

## Testing
```bash
# Unit tests
pytest test_bot.py -v

# Manual test
python main.py
```

Send `/start` on Telegram

---

## Monitoring
```bash
# Health check
curl http://localhost:8080/health

# Logs
docker-compose logs -f bot

# Database
psql -U crypto_bot -h localhost
```

---

## Production Checklist

- [ ] Binance API keys configured
- [ ] Telegram bot working
- [ ] Database backup setup
- [ ] Environment variables verified
- [ ] Health check tested
- [ ] Start with paper trading
- [ ] Monitor logs
- [ ] Test on testnet first

---

## Support

- GitHub Issues
- Documentation: README.md

---

**⚠️ Disclaimer:** Educational purposes only. Test thoroughly before live trading.
