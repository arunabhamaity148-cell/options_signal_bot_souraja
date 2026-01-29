# alerts/telegram_bot.py
"""
Telegram Signal Delivery
Clean, professional, actionable alerts

Format:
📊 INDEX OPTION SIGNAL

Index: NIFTY/BANKNIFTY
Type: CALL/PUT
Strike: XXXX CE/PE
Expiry: Weekly

Entry: ₹___
Stop Loss: ₹___
Target: ₹___
Risk:Reward: 1:__

Reason:
• HTF trend confirmation
• Entry pattern
• RSI + volume support

⏰ Time: HH:MM IST
⚠️ Manual execution only. Risk capital.
"""

import asyncio
from datetime import datetime
import pytz
from typing import Dict, Optional
from loguru import logger

try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning("python-telegram-bot not installed. Install with: pip install python-telegram-bot")


class TelegramAlerter:
    """
    Send trading signals via Telegram
    """
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        Args:
            bot_token: Telegram bot token from BotFather
            chat_id: Your telegram chat ID
        """
        
        if not TELEGRAM_AVAILABLE:
            raise ImportError("Telegram bot library not available")
        
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.bot = Bot(token=bot_token)
        self.timezone = pytz.timezone('Asia/Kolkata')
        
        logger.info("Telegram bot initialized")
    
    def format_signal(self, signal_data: Dict) -> str:
        """
        Format signal data into clean, readable message
        
        Args:
            signal_data: {
                'index': str (NIFTY/BANKNIFTY),
                'type': str (CALL/PUT),
                'strike': int,
                'expiry': str,
                'entry': float,
                'stop_loss': float,
                'target': float,
                'risk_reward': float,
                'lots': int,
                'reasons': {
                    'htf': str,
                    'entry_pattern': str,
                    'confirmation': str
                }
            }
        """
        
        # Get current IST time
        now = datetime.now(self.timezone)
        time_str = now.strftime("%H:%M")
        
        # Determine CE/PE
        option_type = "CE" if signal_data['type'] == 'CALL' else "PE"
        
        # Build message
        message = f"""📊 INDEX OPTION SIGNAL

🎯 **{signal_data['index']} {signal_data['strike']}{option_type}**
━━━━━━━━━━━━━━━━━━━━

**Index:** {signal_data['index']}
**Type:** {signal_data['type']}
**Strike:** {signal_data['strike']} {option_type}
**Expiry:** {signal_data.get('expiry', 'Weekly')}

━━━━━━━━━━━━━━━━━━━━
**Entry:** ₹{signal_data['entry']:.2f}
**Stop Loss:** ₹{signal_data['stop_loss']:.2f}
**Target:** ₹{signal_data['target']:.2f}
**Risk:Reward:** 1:{signal_data['risk_reward']:.2f}

**Position Size:** {signal_data.get('lots', 'TBD')} lots

━━━━━━━━━━━━━━━━━━━━
**Signal Reasons:**
• {signal_data['reasons']['htf']}
• {signal_data['reasons']['entry_pattern']}
• {signal_data['reasons']['confirmation']}

━━━━━━━━━━━━━━━━━━━━
⏰ **Time:** {time_str} IST
⚠️ **Manual execution only. Risk capital.**
"""
        
        return message
    
    def format_daily_summary(self, summary_data: Dict) -> str:
        """
        Format end-of-day summary
        
        Args:
            summary_data: {
                'date': str,
                'total_signals': int,
                'trades_taken': int,
                'pnl': float,
                'win_rate': float
            }
        """
        
        message = f"""📈 DAILY SUMMARY

**Date:** {summary_data['date']}
━━━━━━━━━━━━━━━━━━━━

**Signals Sent:** {summary_data.get('total_signals', 0)}
**Trades Taken:** {summary_data.get('trades_taken', 0)}
**P&L:** ₹{summary_data.get('pnl', 0):.2f}
**Win Rate:** {summary_data.get('win_rate', 0):.1f}%

━━━━━━━━━━━━━━━━━━━━
✅ Day complete. See you tomorrow.
"""
        
        return message
    
    def format_error_alert(self, error_msg: str) -> str:
        """Format error/warning message"""
        
        now = datetime.now(self.timezone)
        time_str = now.strftime("%H:%M:%S")
        
        message = f"""⚠️ BOT ALERT

**Time:** {time_str} IST
**Type:** System Error

{error_msg}

Please check the logs.
"""
        
        return message
    
    async def send_message(self, message: str) -> bool:
        """
        Send message via Telegram
        
        Returns:
            True if sent successfully, False otherwise
        """
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info("Telegram message sent successfully")
            return True
            
        except TelegramError as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram: {e}")
            return False
    
    def send_message_sync(self, message: str) -> bool:
        """
        Synchronous wrapper for send_message
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.send_message(message))
    
    async def send_signal(self, signal_data: Dict) -> bool:
        """
        Format and send trading signal
        """
        message = self.format_signal(signal_data)
        return await self.send_message(message)
    
    def send_signal_sync(self, signal_data: Dict) -> bool:
        """
        Synchronous wrapper for send_signal
        """
        message = self.format_signal(signal_data)
        return self.send_message_sync(message)
    
    async def send_daily_summary(self, summary_data: Dict) -> bool:
        """
        Send end-of-day summary
        """
        message = self.format_daily_summary(summary_data)
        return await self.send_message(message)
    
    async def send_error_alert(self, error_msg: str) -> bool:
        """
        Send error/warning alert
        """
        message = self.format_error_alert(error_msg)
        return await self.send_message(message)
    
    async def send_test_message(self) -> bool:
        """
        Send test message to verify bot is working
        """
        now = datetime.now(self.timezone)
        message = f"""✅ BOT TEST

Bot is online and connected.
Time: {now.strftime("%H:%M:%S")} IST

Ready to send signals.
"""
        return await self.send_message(message)
    
    def send_test_message_sync(self) -> bool:
        """Synchronous test message"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.send_test_message())


# ==================== TESTING ====================
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Get credentials from environment
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
    
    if not bot_token or not chat_id:
        print("⚠️ Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env file")
        print("\nExample .env file:")
        print("TELEGRAM_BOT_TOKEN=your_bot_token_here")
        print("TELEGRAM_CHAT_ID=your_chat_id_here")
        exit(1)
    
    print("=" * 60)
    print("TESTING TELEGRAM BOT")
    print("=" * 60)
    
    alerter = TelegramAlerter(bot_token, chat_id)
    
    # Test 1: Send test message
    print("\nTest 1: Sending test message...")
    success = alerter.send_test_message_sync()
    print(f"Result: {'✓ Sent' if success else '✗ Failed'}")
    
    # Test 2: Send sample signal
    print("\nTest 2: Sending sample CALL signal...")
    
    sample_signal = {
        'index': 'NIFTY',
        'type': 'CALL',
        'strike': 22500,
        'expiry': 'Weekly',
        'entry': 150.00,
        'stop_loss': 105.00,
        'target': 217.50,
        'risk_reward': 1.5,
        'lots': 2,
        'reasons': {
            'htf': '1H trend bullish (EMA20 > EMA50)',
            'entry_pattern': 'EMA9 pullback with volume spike',
            'confirmation': 'RSI 52.3 (healthy), strong candle close'
        }
    }
    
    success = alerter.send_signal_sync(sample_signal)
    print(f"Result: {'✓ Sent' if success else '✗ Failed'}")
    
    # Test 3: Send daily summary
    print("\nTest 3: Sending daily summary...")
    
    sample_summary = {
        'date': '2024-01-15',
        'total_signals': 2,
        'trades_taken': 2,
        'pnl': 1250.00,
        'win_rate': 100.0
    }
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    success = loop.run_until_complete(alerter.send_daily_summary(sample_summary))
    print(f"Result: {'✓ Sent' if success else '✗ Failed'}")
    
    print("\n" + "=" * 60)
    print("If you received all messages, Telegram bot is working!")
    print("=" * 60)
