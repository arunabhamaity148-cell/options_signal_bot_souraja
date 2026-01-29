# 🎯 NIFTY/BANKNIFTY Options Signal Bot

**Professional-grade, low-noise signal bot for Indian index options**

> Manual execution only. Regulatory compliant. Capital protection first.

---

## 📋 WHAT THIS BOT DOES

✅ **Sends Telegram signals** for NIFTY/BANKNIFTY options  
✅ **1-2 signals per day maximum** (quality over quantity)  
✅ **Multi-timeframe analysis** (1H trend + 5m entry)  
✅ **Built-in risk management** (1% risk per trade, auto position sizing)  
✅ **Time-based filters** (only trades 9:20 AM - 11:30 AM IST)  
✅ **Circuit breakers** (stops after loss, daily limits)

❌ **Does NOT auto-execute** (you place orders manually)  
❌ **No martingale/revenge trading**  
❌ **No overfitting or fake backtests**

---

## 🏗️ ARCHITECTURE

```
options_signal_bot/
│
├── config/
│   └── settings.py              # All configuration
│
├── strategy/
│   ├── htf_filter.py            # 1H trend filter (EMA 20/50)
│   ├── ltf_entry.py             # 5m entry patterns
│   ├── filters.py               # RSI, candle, time filters
│   └── signal_generator.py      # Master orchestrator
│
├── risk/
│   └── position_sizer.py        # Position sizing, SL/TP, daily limits
│
├── alerts/
│   └── telegram_bot.py          # Telegram signal delivery
│
├── main.py                      # Bot runner
├── requirements.txt             # Dependencies
└── README.md                    # This file
```

---

## 🎓 STRATEGY LOGIC

### Top-Down Approach

#### **1. HTF Filter (1 Hour Chart)**
- **EMA 20 > EMA 50** → Only CALL signals allowed
- **EMA 20 < EMA 50** → Only PUT signals allowed
- **Choppy/flat** → NO SIGNALS (bot stays silent)
- **Minimum separation:** 0.2%
- **Alignment check:** Last 3 candles must align

**Why it works:** Institutional money moves on hourly timeframe. We trade WITH the big money, not against it.

#### **2. LTF Entry (5 Minute Chart)**

Two proven patterns:

**A) EMA Pullback**
- Price pulls back to 9 EMA
- Next candle closes back in trend direction
- Volume >= average (real money)
- Strong directional body (no doji/indecision)

**B) Structure Break**
- Break of recent swing high/low (10 candle lookback)
- Strong volume (1.2x average minimum)
- Clean directional close (no wick-only break)

**Why it works:** These patterns show institutional accumulation/distribution at key levels.

#### **3. Quality Filters**

**RSI Filter:**
- CALL: RSI 45-60 (momentum without exhaustion)
- PUT: RSI 40-55 (momentum without exhaustion)

**Candle Quality:**
- Body >= 60% of range (conviction)
- Wick against direction < 30% of body (no rejection)

**Time Window:**
- Only 9:20 AM - 11:30 AM IST
- First 5 min avoided (wide spreads)
- Afternoon avoided (range-bound)

#### **4. Risk Management**

- **Risk per trade:** 1% of capital
- **Stop Loss:** 30% of entry premium
- **Target:** Minimum 1:1.5 RR
- **Max trades/day:** 2
- **Circuit breaker:** Stop after 1 consecutive loss

---

## 🚀 SETUP GUIDE

### Prerequisites

- Python 3.9+
- Zerodha Kite API account (for market data)
- Telegram Bot (for signals)

### Step 1: Clone/Download

```bash
git clone <your-repo>
cd options_signal_bot
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Create Telegram Bot

1. Open Telegram, search for `@BotFather`
2. Send `/newbot`
3. Follow instructions, get your `BOT_TOKEN`
4. Search for `@userinfobot` to get your `CHAT_ID`

### Step 4: Configuration

Create `.env` file in project root:

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Zerodha Kite (optional - for live data)
KITE_API_KEY=your_api_key
KITE_API_SECRET=your_api_secret
KITE_ACCESS_TOKEN=your_access_token
```

### Step 5: Customize Settings

Edit `settings.py`:

```python
# Capital
TOTAL_CAPITAL = 100000  # Your trading capital

# Risk
RISK_PER_TRADE = 0.01  # 1% risk per trade

# Instruments
INSTRUMENTS = ['NIFTY', 'BANKNIFTY']

# Trading hours
TRADING_START_HOUR = 9
TRADING_START_MINUTE = 20
TRADING_END_HOUR = 11
TRADING_END_MINUTE = 30
```

### Step 6: Test Components

```bash
# Test HTF filter
python htf_filter.py

# Test LTF entry
python ltf_entry.py

# Test filters
python filters.py

# Test position sizer
python position_sizer.py

# Test Telegram (requires .env setup)
python telegram_bot.py
```

### Step 7: Run Bot

```bash
python main.py
```

You should see:
```
===============================================================
OPTIONS SIGNAL BOT STARTING
===============================================================

✓ Bot initialized successfully
✓ Scheduled scan every 60 seconds
✓ Daily summary at 15:35
✓ Daily reset at 09:00

===============================================================
BOT IS LIVE - Monitoring markets...
===============================================================
```

---

## 📱 TELEGRAM SIGNAL FORMAT

When bot finds a valid setup, you'll receive:

```
📊 INDEX OPTION SIGNAL

🎯 NIFTY 22500CE
━━━━━━━━━━━━━━━━━━━━

Index: NIFTY
Type: CALL
Strike: 22500 CE
Expiry: Weekly

━━━━━━━━━━━━━━━━━━━━
Entry: ₹150.00
Stop Loss: ₹105.00
Target: ₹217.50
Risk:Reward: 1:1.5

Position Size: 2 lots

━━━━━━━━━━━━━━━━━━━━
Signal Reasons:
• 1H trend bullish (EMA20 > EMA50)
• EMA9 pullback with volume spike
• RSI 52.3 (healthy), strong candle close

━━━━━━━━━━━━━━━━━━━━
⏰ Time: 10:15 IST
⚠️ Manual execution only. Risk capital.
```

---

## 🎯 EXECUTION GUIDE

### When You Receive a Signal:

1. **Verify the signal** - Check chart yourself
2. **Open broker platform** (Zerodha Kite/Upstox)
3. **Find the exact option** (check strike, expiry)
4. **Place LIMIT order at entry price** (or close to it)
5. **Immediately set Stop Loss** order
6. **Set Target** order (or use trailing SL)

### Important:

- Signals are time-sensitive (valid for 5-10 minutes)
- If you miss entry by ₹5+, skip the trade
- Never enter without Stop Loss
- Never increase position size
- Track every trade (P&L, entry time, exit)

---

## ⚙️ CUSTOMIZATION

### Adjust Risk

```python
# settings.py
RISK_PER_TRADE = 0.02  # 2% risk instead of 1%
MAX_TRADES_PER_DAY = 3  # 3 trades instead of 2
```

### Change Trading Hours

```python
# settings.py
TRADING_START_HOUR = 9
TRADING_START_MINUTE = 30  # Start at 9:30 instead of 9:20
TRADING_END_HOUR = 14
TRADING_END_MINUTE = 0  # Trade till 2 PM
```

### Modify Strategy Parameters

```python
# settings.py

# HTF
HTF_EMA_FAST = 20
HTF_EMA_SLOW = 50
HTF_TREND_SEPARATION = 0.2  # Increase for stricter trend

# LTF
LTF_EMA_ENTRY = 9
VOLUME_MULTIPLIER = 1.2  # Require 20% above average volume

# RSI
RSI_CALL_MIN = 45
RSI_CALL_MAX = 60
```

---

## 📊 BACKTESTING

### Run Historical Test

```python
# backtest/engine.py (to be implemented)

from backtest_engine import BacktestEngine

engine = BacktestEngine(
    start_date='2024-01-01',
    end_date='2024-12-31',
    capital=100000
)

results = engine.run()
print(results.summary())
```

### Important Notes on Backtesting:

- Options data is hard to backtest accurately
- Slippage, spreads, and liquidity vary
- Use conservative assumptions
- Paper trade for 1 month before going live
- **A good backtest shows 40-50% win rate, not 90%**

---

## ⚠️ SAFETY & COMPLIANCE

### Regulatory Compliance (India)

✅ **Manual execution only** - No auto trading  
✅ **No front-running** - Signals are for your use only  
✅ **No SEBI violations** - You control all trades  
✅ **No tip-selling** - Personal use bot  

### Risk Warnings

- Options can expire worthless (100% loss)
- High leverage = high risk
- Only trade with risk capital
- This bot has NO GUARANTEES
- Past performance ≠ future results

### Recommended Practices

- Start with paper trading
- Risk only 1% per trade initially
- Never trade during news events
- Keep a trading journal
- Review signals weekly
- Don't chase missed trades

---

## 🐛 TROUBLESHOOTING

### Bot not sending signals?

**Possible reasons:**
1. No valid HTF trend (market choppy)
2. No LTF entry pattern found
3. Outside trading hours (9:20-11:30 AM)
4. Daily trade limit reached
5. Consecutive loss limit hit

**Check logs:**
```bash
tail -f logs/bot_2024-01-15.log
```

### Telegram not working?

```bash
# Test Telegram connection
python telegram_bot.py
```

If fails:
- Check `TELEGRAM_BOT_TOKEN` in `.env`
- Check `TELEGRAM_CHAT_ID` in `.env`
- Ensure bot is started in Telegram (send `/start`)

### Data issues?

- Implement actual Kite API connection in `main.py`
- Current version uses dummy data (for testing)
- See `fetch_market_data()` function for API integration

---

## 📈 PERFORMANCE EXPECTATIONS

### Realistic Targets

- **Win Rate:** 40-50% (professional range)
- **Risk:Reward:** 1:1.5 to 1:2
- **Signals per day:** 0-2
- **Signals per week:** 2-8
- **Monthly return:** 5-15% (in good conditions)

### Red Flags

If you see these, something is wrong:
- Win rate > 70%
- Multiple signals per hour
- Profits every day
- Drawdown < 10%

**Real trading has losses. Expect drawdowns.**

---

## 🛠️ TODO / FUTURE ENHANCEMENTS

- [ ] Integrate actual Kite API for live data
- [ ] Add proper backtesting engine
- [ ] Implement trade tracking database
- [ ] Add Greeks analysis (Delta, Theta)
- [ ] IV percentile filter
- [ ] Broker API integration (optional auto-execute)
- [ ] Web dashboard for signal history
- [ ] Multi-timeframe dashboard
- [ ] Volatility regime filter

---

## 📞 SUPPORT

**Issues:** Create GitHub issue  
**Questions:** Check logs first, then ask  
**Contributions:** PRs welcome

---

## 📜 DISCLAIMER

```
This software is for educational purposes only.

Trading options involves substantial risk of loss and is not suitable 
for all investors. Past performance is not indicative of future results.

The creators of this bot:
- Make NO guarantees of profit
- Take NO responsibility for your losses
- Are NOT SEBI registered advisors
- Do NOT provide financial advice

USE AT YOUR OWN RISK.

By using this software, you agree that you are solely responsible 
for your trading decisions and their outcomes.
```

---

## 📚 RESOURCES

### Learn More:
- [Zerodha Varsity - Options](https://zerodha.com/varsity/module/option-theory/)
- [NSE Options Guide](https://www.nseindia.com/products-services/derivatives)
- [Technical Analysis Basics](https://school.stockcharts.com)

### API Documentation:
- [Kite Connect API](https://kite.trade/docs/connect/v3/)
- [Telegram Bot API](https://core.telegram.org/bots/api)

---

**Built with discipline, not greed.**

**Trade safe. Trade smart. Protect capital first.**

---

## 🔥 QUICK START (1 MINUTE)

```bash
# 1. Install
pip install -r requirements.txt

# 2. Setup .env
echo "TELEGRAM_BOT_TOKEN=your_token" > .env
echo "TELEGRAM_CHAT_ID=your_chat_id" >> .env

# 3. Run
python main.py
```

Done! Bot is now monitoring markets and will send signals when conditions align.

---

*Version 1.0 | Last Updated: January 2024*
