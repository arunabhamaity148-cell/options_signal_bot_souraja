"""
Telegram bot for signal distribution and interaction
"""
import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

from config.settings import settings, SIGNAL_TEMPLATE
from core.signal_engine import signal_engine
from risk.position_sizer import risk_manager
from database.models import db, Signal

logger = logging.getLogger(__name__)


class TradingBot:
    """Telegram trading bot"""
    
    def __init__(self):
        self.application: Optional[Application] = None
        self.running = False
        self.paper_trades: Dict[str, Dict] = {}
        
    async def initialize(self):
        """Initialize Telegram bot"""
        self.application = (
            Application.builder()
            .token(settings.TELEGRAM_BOT_TOKEN)
            .build()
        )
        
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("signal", self.cmd_signal))
        self.application.add_handler(CommandHandler("stats", self.cmd_stats))
        self.application.add_handler(CommandHandler("settings", self.cmd_settings))
        self.application.add_handler(CommandHandler("paper", self.cmd_paper))
        
        self.application.add_handler(
            CallbackQueryHandler(self.button_callback)
        )
        
        await self.application.initialize()
        logger.info("Telegram bot initialized")
    
    async def start(self):
        """Start Telegram bot"""
        self.running = True
        await self.application.start()
        await self.application.updater.start_polling(drop_pending_updates=True)
        logger.info("Telegram bot started")
        
        asyncio.create_task(self._broadcast_signals())
    
    async def stop(self):
        """Stop Telegram bot"""
        self.running = False
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
        logger.info("Telegram bot stopped")
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """
🚀 **Crypto Options Trading Signal Bot**

Welcome! This bot provides professional options trading signals for Delta Exchange based on technical analysis of Binance data.

**Features:**
- Real-time market analysis
- High-probability setups with confluence scoring
- Risk-managed position sizing
- Paper trading mode
- Performance tracking

Use /help to see all available commands.

⚠️ **Disclaimer:** Trading involves risk. These are signals for educational purposes. Always do your own research.
"""
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
📚 **Available Commands:**

/start - Start the bot
/help - Show this help message
/signal - Force check for signals
/stats - View trading statistics
/settings - View current settings
/paper - View paper trading results

**Signal Actions:**
- MARKET ENTERED - Mark as real trade
- PAPER TRADE - Track as paper trade
- SKIP - Ignore this signal

**Tips:**
- Signals are checked every 15 minutes
- Only high-quality setups (confluence ≥7) are sent
- Max 3 signals per day
- Pauses after 2 consecutive losses
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def cmd_signal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /signal command - manual signal check"""
        await update.message.reply_text("🔍 Checking for trading signals...")
        
        asyncio.create_task(signal_engine._generate_signals())
        
        await asyncio.sleep(5)
        
        signals = signal_engine.get_pending_signals()
        if signals:
            await update.message.reply_text(f"✅ Found {len(signals)} signal(s)")
        else:
            await update.message.reply_text("❌ No signals found at this time")
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        metrics_7d = await risk_manager.get_performance_metrics(days=7)
        metrics_30d = await risk_manager.get_performance_metrics(days=30)
        
        stats_text = f"""
📊 **Trading Statistics**

**Last 7 Days:**
- Total Signals: {metrics_7d['total_signals']}
- Trades Taken: {metrics_7d['total_trades']}
- Win Rate: {metrics_7d['win_rate']:.1f}%
- Wins/Losses: {metrics_7d['wins']}/{metrics_7d['losses']}

**Last 30 Days:**
- Total Signals: {metrics_30d['total_signals']}
- Trades Taken: {metrics_30d['total_trades']}
- Win Rate: {metrics_30d['win_rate']:.1f}%
- Profit Factor: {metrics_30d['avg_profit_factor']:.2f}
- Max Drawdown: {metrics_30d['max_drawdown']:.1f}%

📈 Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
"""
        await update.message.reply_text(stats_text, parse_mode='Markdown')
    
    async def cmd_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /settings command"""
        settings_text = f"""
⚙️ **Current Settings**

**Risk Management:**
- Risk Per Trade: {settings.RISK_PER_TRADE * 100:.1f}%
- Min Risk:Reward: 1:{settings.MIN_RISK_REWARD:.1f}
- Max Daily Signals: {settings.MAX_DAILY_SIGNALS}
- Consecutive Loss Pause: {settings.CONSECUTIVE_LOSS_PAUSE}

**Signal Filters:**
- Min Confluence Score: {settings.MIN_CONFLUENCE_SCORE}/10
- ADX Threshold: {settings.ADX_THRESHOLD}
- RSI Range: {settings.RSI_LOWER}-{settings.RSI_UPPER}

**Trading Pairs:**
{', '.join(settings.TRADING_PAIRS)}

**Mode:** {'Testnet' if settings.BINANCE_TESTNET else 'Live'}
"""
        await update.message.reply_text(settings_text, parse_mode='Markdown')
    
    async def cmd_paper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /paper command - show paper trades"""
        query = """
            SELECT pair, direction, entry_price, exit_price, pnl, 
                   exit_reason, timestamp
            FROM signals
            WHERE trade_type = 'PAPER' AND status = 'CLOSED'
            ORDER BY timestamp DESC
            LIMIT 10
        """
        
        trades = await db.execute(query)
        
        if not trades:
            await update.message.reply_text("📝 No paper trades yet")
            return
        
        total_pnl = sum(t['pnl'] or 0 for t in trades)
        wins = sum(1 for t in trades if (t['pnl'] or 0) > 0)
        
        paper_text = f"""
📝 **Paper Trading Results** (Last 10 trades)

**Summary:**
- Total P&L: ${total_pnl:,.2f}
- Win Rate: {wins/len(trades)*100:.1f}%

**Recent Trades:**
"""
        for trade in trades:
            pnl_emoji = "🟢" if (trade['pnl'] or 0) > 0 else "🔴"
            paper_text += f"""
{pnl_emoji} {trade['pair']} {trade['direction']}
Entry: ${trade['entry_price']:.2f} | Exit: ${trade['exit_price']:.2f}
P&L: ${trade['pnl']:.2f} | Reason: {trade['exit_reason']}
"""
        
        await update.message.reply_text(paper_text, parse_mode='Markdown')
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        action, signal_id = query.data.split('_')
        
        if action == 'MARKET':
            await self._handle_market_entry(query, signal_id)
        elif action == 'PAPER':
            await self._handle_paper_entry(query, signal_id)
        elif action == 'SKIP':
            await self._handle_skip(query, signal_id)
    
    async def _handle_market_entry(self, query, signal_id: str):
        """Handle market entry button"""
        update_query = """
            UPDATE signals
            SET status = 'ACTIVE', trade_type = 'MARKET'
            WHERE id = $1
        """
        await db.execute(update_query, int(signal_id))
        
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"✅ Signal #{signal_id} marked as MARKET ENTERED\n"
            f"⚠️ Remember to manually enter this trade on Delta Exchange!"
        )
    
    async def _handle_paper_entry(self, query, signal_id: str):
        """Handle paper trade entry"""
        signal_query = """
            SELECT * FROM signals WHERE id = $1
        """
        signal = await db.execute_one(signal_query, int(signal_id))
        
        update_query = """
            UPDATE signals
            SET status = 'ACTIVE', trade_type = 'PAPER',
                entry_price = entry_min
            WHERE id = $1
        """
        await db.execute(update_query, int(signal_id))
        
        self.paper_trades[signal_id] = {
            'entry_price': signal['entry_min'],
            'stop_loss': signal['stop_loss'],
            'take_profit_1': signal['take_profit_1'],
            'direction': signal['direction']
        }
        
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"📝 Signal #{signal_id} added to paper trading\n"
            f"Entry: ${signal['entry_min']:.2f}"
        )
    
    async def _handle_skip(self, query, signal_id: str):
        """Handle skip button"""
        update_query = """
            UPDATE signals
            SET status = 'SKIPPED'
            WHERE id = $1
        """
        await db.execute(update_query, int(signal_id))
        
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"⏭️ Signal #{signal_id} skipped")
    
    async def _broadcast_signals(self):
        """Broadcast signals to Telegram"""
        while self.running:
            try:
                signals = signal_engine.get_pending_signals()
                
                for signal in signals:
                    await self._send_signal(signal)
                    await asyncio.sleep(2)
                
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error broadcasting signals: {e}")
                await asyncio.sleep(60)
    
    async def _send_signal(self, signal: Dict):
        """Send signal to Telegram with buttons"""
        message_text = SIGNAL_TEMPLATE.format(
            direction=signal['direction'].replace('_', ' '),
            pair=signal['pair'],
            strike=signal['strike_price'],
            strike_type=signal['strike_type'],
            expiry=signal['expiry_date'].strftime('%Y-%m-%d'),
            premium=signal['premium_estimate'],
            entry_min=signal['entry_zone']['min'],
            entry_max=signal['entry_zone']['max'],
            stop_loss=signal['stop_loss'],
            tp1=signal['take_profits']['tp1'],
            tp2=signal['take_profits']['tp2'],
            tp3=signal['take_profits']['tp3'],
            logic=signal['setup_logic'],
            risk_amount=signal['position']['risk_amount'],
            risk_percent=signal['position']['risk_percent'],
            risk_reward=settings.MIN_RISK_REWARD,
            max_hold=settings.MAX_HOLD_HOURS,
            confluence=signal['confluence_score'],
            timestamp=signal['timestamp'].strftime('%Y-%m-%d %H:%M UTC')
        )
        
        insert_query = """
            INSERT INTO signals (
                pair, direction, strike_price, strike_type, expiry_date,
                premium_estimate, entry_min, entry_max, stop_loss,
                take_profit_1, take_profit_2, take_profit_3,
                risk_amount, risk_reward, confluence_score, setup_logic,
                indicators, timestamp
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18
            ) RETURNING id
        """
        
        result = await db.execute_one(
            insert_query,
            signal['pair'], signal['direction'], signal['strike_price'],
            signal['strike_type'], signal['expiry_date'], signal['premium_estimate'],
            signal['entry_zone']['min'], signal['entry_zone']['max'],
            signal['stop_loss'], signal['take_profits']['tp1'],
            signal['take_profits']['tp2'], signal['take_profits']['tp3'],
            signal['position']['risk_amount'], settings.MIN_RISK_REWARD,
            signal['confluence_score'], signal['setup_logic'],
            str(signal['indicators']), signal['timestamp']
        )
        
        signal_id = result['id']
        
        keyboard = [
            [
                InlineKeyboardButton("MARKET ENTERED", callback_data=f"MARKET_{signal_id}"),
                InlineKeyboardButton("PAPER TRADE", callback_data=f"PAPER_{signal_id}"),
            ],
            [
                InlineKeyboardButton("SKIP", callback_data=f"SKIP_{signal_id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            message = await self.application.bot.send_message(
                chat_id=settings.TELEGRAM_CHAT_ID,
                text=message_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
            update_query = """
                UPDATE signals SET telegram_message_id = $1 WHERE id = $2
            """
            await db.execute(update_query, str(message.message_id), signal_id)
            
            logger.info(f"Signal sent to Telegram: {signal['pair']} {signal['direction']}")
            
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")


telegram_bot = TradingBot()
