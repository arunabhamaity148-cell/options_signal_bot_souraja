# risk/position_sizer.py
"""
Risk Management & Position Sizing
Capital protection > profit

Core principles:
1. Never risk more than 1% per trade
2. Stop Loss is non-negotiable
3. Minimum 1:1.5 Risk:Reward
4. Circuit breaker after consecutive loss
"""

import pandas as pd
from typing import Dict, Optional
from loguru import logger


class PositionSizer:
    """
    Calculate position size, SL, and TP for each trade
    """
    
    def __init__(self,
                 total_capital: float,
                 risk_per_trade: float = 0.01,
                 min_rr: float = 1.5,
                 sl_percent: float = 0.30):
        """
        Args:
            total_capital: Total trading capital in ₹
            risk_per_trade: Risk per trade as decimal (0.01 = 1%)
            min_rr: Minimum Risk:Reward ratio
            sl_percent: Stop loss as % of entry premium (0.30 = 30%)
        """
        
        self.total_capital = total_capital
        self.risk_per_trade = risk_per_trade
        self.min_rr = min_rr
        self.sl_percent = sl_percent
        
        # Safety limits
        self.max_position_size = 50  # Max lots
        self.min_premium = 5         # Min ₹5 premium
        self.max_premium = 500       # Max ₹500 premium
    
    def calculate_position(self, 
                          entry_premium: float,
                          lot_size: int = 50) -> Dict:
        """
        Calculate position size and risk parameters
        
        Logic:
        1. Calculate rupee risk = capital * risk%
        2. SL = entry - (entry * SL%)
        3. Risk per lot = entry - SL
        4. Lots = rupee risk / risk per lot
        5. Target = entry + (risk per lot * RR)
        
        Args:
            entry_premium: Option premium at entry (₹)
            lot_size: Lot size of the option contract
            
        Returns:
            {
                'valid': bool,
                'lots': int,
                'entry': float,
                'stop_loss': float,
                'target': float,
                'risk_amount': float,
                'reward_amount': float,
                'risk_reward': float,
                'total_investment': float
            }
        """
        
        # Validate premium
        if entry_premium < self.min_premium:
            logger.warning(f"Premium too low: ₹{entry_premium} (min: ₹{self.min_premium})")
            return {'valid': False, 'reason': 'Premium too low'}
        
        if entry_premium > self.max_premium:
            logger.warning(f"Premium too high: ₹{entry_premium} (max: ₹{self.max_premium})")
            return {'valid': False, 'reason': 'Premium too high'}
        
        # Calculate stop loss (premium based)
        stop_loss = entry_premium * (1 - self.sl_percent)
        
        # Risk per lot (in ₹)
        risk_per_lot = entry_premium - stop_loss
        
        if risk_per_lot <= 0:
            return {'valid': False, 'reason': 'Invalid SL calculation'}
        
        # Total rupee risk allowed
        total_risk_allowed = self.total_capital * self.risk_per_trade
        
        # Calculate number of lots
        lots_raw = total_risk_allowed / (risk_per_lot * lot_size)
        lots = int(lots_raw)  # Floor to nearest integer
        
        # Validate lot size
        if lots < 1:
            logger.warning(f"Calculated lots < 1: {lots_raw:.2f}")
            return {'valid': False, 'reason': 'Position size too small'}
        
        if lots > self.max_position_size:
            logger.warning(f"Lots capped at {self.max_position_size} (calculated: {lots})")
            lots = self.max_position_size
        
        # Calculate actual risk with integer lots
        actual_risk = lots * lot_size * risk_per_lot
        
        # Calculate target (minimum RR)
        reward_per_lot = risk_per_lot * self.min_rr
        target = entry_premium + reward_per_lot
        
        # Actual reward amount
        actual_reward = lots * lot_size * reward_per_lot
        
        # Total investment
        total_investment = lots * lot_size * entry_premium
        
        # Risk:Reward ratio
        rr_ratio = actual_reward / actual_risk if actual_risk > 0 else 0
        
        result = {
            'valid': True,
            'lots': lots,
            'entry': entry_premium,
            'stop_loss': stop_loss,
            'target': target,
            'risk_amount': actual_risk,
            'reward_amount': actual_reward,
            'risk_reward': rr_ratio,
            'total_investment': total_investment,
            'lot_size': lot_size
        }
        
        logger.info(
            f"Position Calculated | "
            f"Lots: {lots} | "
            f"Entry: ₹{entry_premium:.2f} | "
            f"SL: ₹{stop_loss:.2f} | "
            f"Target: ₹{target:.2f} | "
            f"RR: 1:{rr_ratio:.2f} | "
            f"Risk: ₹{actual_risk:.2f}"
        )
        
        return result


class DailyLimits:
    """
    Track and enforce daily trading limits
    """
    
    def __init__(self,
                 max_trades_per_day: int = 2,
                 max_daily_loss: float = 2000,
                 consecutive_loss_limit: int = 1):
        
        self.max_trades = max_trades_per_day
        self.max_loss = max_daily_loss
        self.consecutive_loss_limit = consecutive_loss_limit
        
        # Daily tracking
        self.trades_taken = 0
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.trade_history = []
    
    def can_trade(self) -> Dict:
        """
        Check if allowed to take new trade
        
        Circuit breakers:
        1. Max trades per day reached
        2. Max daily loss hit
        3. Consecutive loss limit hit
        
        Returns:
            {
                'allowed': bool,
                'reason': str
            }
        """
        
        # Check max trades
        if self.trades_taken >= self.max_trades:
            return {
                'allowed': False,
                'reason': f'Max trades reached ({self.max_trades})'
            }
        
        # Check daily loss
        if self.daily_pnl <= -self.max_loss:
            return {
                'allowed': False,
                'reason': f'Daily loss limit hit (₹{abs(self.daily_pnl):.2f})'
            }
        
        # Check consecutive losses
        if self.consecutive_losses >= self.consecutive_loss_limit:
            return {
                'allowed': False,
                'reason': f'Consecutive loss limit hit ({self.consecutive_losses})'
            }
        
        return {
            'allowed': True,
            'reason': 'All checks passed'
        }
    
    def record_trade(self, pnl: float):
        """
        Record trade outcome
        
        Args:
            pnl: Profit/Loss in ₹ (positive = profit, negative = loss)
        """
        
        self.trades_taken += 1
        self.daily_pnl += pnl
        
        if pnl < 0:
            self.consecutive_losses += 1
            logger.warning(f"Loss recorded: ₹{pnl:.2f} | Consecutive losses: {self.consecutive_losses}")
        else:
            self.consecutive_losses = 0  # Reset on win
            logger.info(f"Profit recorded: ₹{pnl:.2f}")
        
        self.trade_history.append({
            'trade_num': self.trades_taken,
            'pnl': pnl,
            'cumulative_pnl': self.daily_pnl
        })
    
    def reset_daily(self):
        """Reset counters at start of new day"""
        logger.info(f"Daily reset | Final P&L: ₹{self.daily_pnl:.2f} | Trades: {self.trades_taken}")
        
        self.trades_taken = 0
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.trade_history = []
    
    def get_summary(self) -> Dict:
        """Get current day summary"""
        return {
            'trades_taken': self.trades_taken,
            'trades_remaining': max(0, self.max_trades - self.trades_taken),
            'daily_pnl': self.daily_pnl,
            'loss_buffer': self.max_loss + self.daily_pnl,  # Remaining loss buffer
            'consecutive_losses': self.consecutive_losses,
            'trade_history': self.trade_history
        }


# ==================== TESTING ====================
if __name__ == "__main__":
    
    print("=" * 60)
    print("TESTING POSITION SIZER")
    print("=" * 60)
    
    sizer = PositionSizer(
        total_capital=100000,
        risk_per_trade=0.01,
        min_rr=1.5
    )
    
    # Test Case 1: Normal premium
    print("\nTest 1: Entry at ₹100")
    result = sizer.calculate_position(entry_premium=100, lot_size=50)
    
    if result['valid']:
        print(f"  Lots: {result['lots']}")
        print(f"  Entry: ₹{result['entry']:.2f}")
        print(f"  Stop Loss: ₹{result['stop_loss']:.2f}")
        print(f"  Target: ₹{result['target']:.2f}")
        print(f"  Risk Amount: ₹{result['risk_amount']:.2f}")
        print(f"  Reward Amount: ₹{result['reward_amount']:.2f}")
        print(f"  Risk:Reward: 1:{result['risk_reward']:.2f}")
        print(f"  Total Investment: ₹{result['total_investment']:.2f}")
    else:
        print(f"  Invalid: {result.get('reason')}")
    
    # Test Case 2: Low premium
    print("\nTest 2: Entry at ₹20")
    result = sizer.calculate_position(entry_premium=20, lot_size=50)
    
    if result['valid']:
        print(f"  Lots: {result['lots']}")
        print(f"  Total Investment: ₹{result['total_investment']:.2f}")
    else:
        print(f"  Invalid: {result.get('reason')}")
    
    # Test Case 3: High premium
    print("\nTest 3: Entry at ₹300")
    result = sizer.calculate_position(entry_premium=300, lot_size=50)
    
    if result['valid']:
        print(f"  Lots: {result['lots']}")
        print(f"  Risk Amount: ₹{result['risk_amount']:.2f}")
    else:
        print(f"  Invalid: {result.get('reason')}")
    
    print("\n" + "=" * 60)
    print("TESTING DAILY LIMITS")
    print("=" * 60)
    
    limits = DailyLimits(
        max_trades_per_day=2,
        max_daily_loss=2000,
        consecutive_loss_limit=1
    )
    
    # Trade 1: Loss
    print("\nTrade 1: Loss of ₹800")
    check = limits.can_trade()
    print(f"  Can trade: {check['allowed']}")
    
    if check['allowed']:
        limits.record_trade(-800)
        summary = limits.get_summary()
        print(f"  Daily P&L: ₹{summary['daily_pnl']:.2f}")
        print(f"  Consecutive losses: {summary['consecutive_losses']}")
    
    # Trade 2: Try again after loss
    print("\nTrade 2: Check if allowed")
    check = limits.can_trade()
    print(f"  Can trade: {check['allowed']}")
    print(f"  Reason: {check['reason']}")
    
    # Summary
    summary = limits.get_summary()
    print(f"\nDaily Summary:")
    print(f"  Trades taken: {summary['trades_taken']}/{limits.max_trades}")
    print(f"  P&L: ₹{summary['daily_pnl']:.2f}")
    print(f"  Loss buffer: ₹{summary['loss_buffer']:.2f}")
