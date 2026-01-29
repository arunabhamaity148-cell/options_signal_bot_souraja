# strategy/signal_generator.py
"""
Master Signal Generator
Orchestrates all components to produce high-quality signals

Flow:
1. Check daily limits
2. HTF validation (1H trend)
3. LTF entry pattern (5m)
4. Quality filters (RSI, candle, time)
5. Position sizing
6. Generate signal

Only outputs signal when ALL conditions align.
Silence > bad signals.
"""

import pandas as pd
from typing import Dict, Optional
from datetime import datetime
import pytz
from loguru import logger

# Import our modules
from htf_filter import HTFTrendFilter, BiasType
from ltf_entry import LTFEntry
from filters import SignalFilters
from position_sizer import PositionSizer, DailyLimits


class SignalGenerator:
    """
    Master decision engine
    """
    
    def __init__(self,
                 capital: float = 100000,
                 risk_per_trade: float = 0.01,
                 max_trades: int = 2):
        
        # Initialize components
        self.htf_filter = HTFTrendFilter()
        self.ltf_entry = LTFEntry()
        self.filters = SignalFilters()
        self.position_sizer = PositionSizer(
            total_capital=capital,
            risk_per_trade=risk_per_trade
        )
        self.daily_limits = DailyLimits(max_trades_per_day=max_trades)
        
        self.timezone = pytz.timezone('Asia/Kolkata')
        
        logger.info("Signal Generator initialized")
    
    def generate_signal(self,
                       df_1h: pd.DataFrame,
                       df_5m: pd.DataFrame,
                       index_name: str,
                       current_spot: float,
                       atm_strike: int,
                       lot_size: int) -> Optional[Dict]:
        """
        Main signal generation logic
        
        Args:
            df_1h: 1 hour OHLCV data
            df_5m: 5 minute OHLCV data
            index_name: 'NIFTY' or 'BANKNIFTY'
            current_spot: Current index spot price
            atm_strike: ATM strike price
            lot_size: Lot size of the option
            
        Returns:
            Signal dict if valid, None otherwise
        """
        
        logger.info(f"\n{'='*60}")
        logger.info(f"SIGNAL GENERATION STARTED - {index_name}")
        logger.info(f"Spot: {current_spot:.2f} | ATM: {atm_strike}")
        logger.info(f"{'='*60}\n")
        
        # === STEP 1: Daily Limits Check ===
        logger.info("Step 1: Checking daily limits...")
        limits_check = self.daily_limits.can_trade()
        
        if not limits_check['allowed']:
            logger.warning(f"✗ Daily limits: {limits_check['reason']}")
            return None
        
        logger.info(f"✓ Daily limits OK - {limits_check['reason']}")
        
        # === STEP 2: HTF Trend Validation ===
        logger.info("\nStep 2: Validating HTF trend (1H)...")
        htf_result = self.htf_filter.validate_for_entry(df_1h)
        
        if not htf_result['valid']:
            logger.warning(f"✗ HTF validation failed: {htf_result['reason']}")
            return None
        
        bias = htf_result['bias']
        logger.info(f"✓ HTF validated - Bias: {bias} (Strength: {htf_result['strength']:.1f}/100)")
        
        # === STEP 3: LTF Entry Pattern ===
        logger.info("\nStep 3: Looking for LTF entry pattern (5m)...")
        entry_result = self.ltf_entry.find_best_entry(df_5m, bias)
        
        if not entry_result.get('valid'):
            logger.warning("✗ No valid entry pattern found")
            return None
        
        logger.info(f"✓ Entry pattern found: {entry_result['pattern']}")
        
        # === STEP 4: Quality Filters ===
        logger.info("\nStep 4: Applying quality filters...")
        
        current_time = datetime.now(self.timezone)
        filter_result = self.filters.validate_all(df_5m, bias, current_time)
        
        if not filter_result['valid']:
            logger.warning(f"✗ Quality filters failed: {filter_result['failed_filters']}")
            return None
        
        logger.info("✓ All quality filters passed")
        
        # === STEP 5: Determine Strike & Option Type ===
        option_type = 'CALL' if bias == 'CALL_ONLY' else 'PUT'
        strike = atm_strike  # Using ATM for simplicity
        
        # Estimate option premium (in real system, fetch from API)
        # For now, using spot-based estimation
        estimated_premium = self._estimate_premium(
            spot=current_spot,
            strike=strike,
            option_type=option_type
        )
        
        logger.info(f"\nOption Details:")
        logger.info(f"  Strike: {strike} {option_type}")
        logger.info(f"  Estimated Premium: ₹{estimated_premium:.2f}")
        
        # === STEP 6: Position Sizing ===
        logger.info("\nStep 5: Calculating position size...")
        position = self.position_sizer.calculate_position(
            entry_premium=estimated_premium,
            lot_size=lot_size
        )
        
        if not position.get('valid'):
            logger.warning(f"✗ Position sizing failed: {position.get('reason')}")
            return None
        
        logger.info(f"✓ Position sized: {position['lots']} lots")
        
        # === STEP 7: Build Signal ===
        signal = {
            'timestamp': current_time.isoformat(),
            'index': index_name,
            'spot_price': current_spot,
            'type': option_type,
            'strike': strike,
            'expiry': 'Weekly',
            'entry': position['entry'],
            'stop_loss': position['stop_loss'],
            'target': position['target'],
            'risk_reward': position['risk_reward'],
            'lots': position['lots'],
            'total_investment': position['total_investment'],
            'risk_amount': position['risk_amount'],
            'reward_amount': position['reward_amount'],
            'reasons': {
                'htf': htf_result['reason'],
                'entry_pattern': f"{entry_result['pattern'].replace('_', ' ').title()} at ₹{entry_result['entry_price']:.2f}",
                'confirmation': (
                    f"RSI {filter_result['rsi']['rsi_value']:.1f}, "
                    f"Volume {entry_result.get('volume_ratio', 1.0):.2f}x, "
                    f"Strong candle"
                )
            },
            'metadata': {
                'htf_strength': htf_result['strength'],
                'rsi': filter_result['rsi']['rsi_value'],
                'volume_ratio': entry_result.get('volume_ratio', 1.0),
                'pattern': entry_result['pattern']
            }
        }
        
        logger.info(f"\n{'='*60}")
        logger.info("✓✓✓ VALID SIGNAL GENERATED ✓✓✓")
        logger.info(f"{'='*60}\n")
        
        return signal
    
    def _estimate_premium(self, 
                         spot: float, 
                         strike: int, 
                         option_type: str) -> float:
        """
        Rough estimation of option premium
        
        In production: Fetch actual premium from API
        This is just for testing
        """
        
        # Very rough approximation
        if option_type == 'CALL':
            # ITM: spot - strike, ATM/OTM: intrinsic value
            intrinsic = max(0, spot - strike)
        else:
            intrinsic = max(0, strike - spot)
        
        # Add time value (arbitrary for testing)
        time_value = abs(spot - strike) * 0.02 if intrinsic == 0 else intrinsic * 0.3
        
        premium = intrinsic + time_value
        
        # Clamp to reasonable range
        premium = max(10, min(400, premium))
        
        return premium
    
    def record_trade_outcome(self, pnl: float):
        """
        Record trade P&L and update limits
        """
        self.daily_limits.record_trade(pnl)
    
    def reset_day(self):
        """
        Reset at start of new trading day
        """
        self.daily_limits.reset_daily()
        logger.info("New trading day - counters reset")
    
    def get_daily_summary(self) -> Dict:
        """
        Get summary of today's activity
        """
        return self.daily_limits.get_summary()


# ==================== TESTING ====================
if __name__ == "__main__":
    import numpy as np
    
    print("=" * 60)
    print("TESTING SIGNAL GENERATOR")
    print("=" * 60)
    
    # Create test data
    dates_1h = pd.date_range('2024-01-15 09:00', periods=60, freq='H')
    dates_5m = pd.date_range('2024-01-15 09:15', periods=60, freq='5min')
    
    # Bullish trend on 1H
    df_1h = pd.DataFrame({
        'datetime': dates_1h,
        'open': np.linspace(22000, 22500, 60),
        'high': np.linspace(22050, 22550, 60),
        'low': np.linspace(21950, 22450, 60),
        'close': np.linspace(22000, 22500, 60),
        'volume': np.random.randint(100000, 500000, 60)
    })
    
    # 5m with pullback pattern
    base_5m = np.linspace(22400, 22500, 60)
    df_5m = pd.DataFrame({
        'datetime': dates_5m,
        'open': base_5m + np.random.randn(60) * 5,
        'high': base_5m + np.random.randn(60) * 5 + 10,
        'low': base_5m + np.random.randn(60) * 5 - 10,
        'close': base_5m + np.random.randn(60) * 5,
        'volume': np.random.randint(50000, 200000, 60)
    })
    
    # Setup pullback in last candles
    df_5m.loc[df_5m.index[-2], 'close'] = 22480
    df_5m.loc[df_5m.index[-2], 'low'] = 22470
    df_5m.loc[df_5m.index[-1], 'open'] = 22475
    df_5m.loc[df_5m.index[-1], 'close'] = 22510
    df_5m.loc[df_5m.index[-1], 'high'] = 22515
    df_5m.loc[df_5m.index[-1], 'volume'] = 180000
    
    # Initialize generator
    generator = SignalGenerator(
        capital=100000,
        risk_per_trade=0.01,
        max_trades=2
    )
    
    # Generate signal
    signal = generator.generate_signal(
        df_1h=df_1h,
        df_5m=df_5m,
        index_name='NIFTY',
        current_spot=22505.35,
        atm_strike=22500,
        lot_size=50
    )
    
    if signal:
        print("\n" + "=" * 60)
        print("GENERATED SIGNAL")
        print("=" * 60)
        print(f"\nIndex: {signal['index']}")
        print(f"Type: {signal['type']}")
        print(f"Strike: {signal['strike']}")
        print(f"\nEntry: ₹{signal['entry']:.2f}")
        print(f"Stop Loss: ₹{signal['stop_loss']:.2f}")
        print(f"Target: ₹{signal['target']:.2f}")
        print(f"Risk:Reward: 1:{signal['risk_reward']:.2f}")
        print(f"\nPosition: {signal['lots']} lots")
        print(f"Investment: ₹{signal['total_investment']:.2f}")
        print(f"Risk: ₹{signal['risk_amount']:.2f}")
        print(f"Potential Reward: ₹{signal['reward_amount']:.2f}")
        print(f"\nReasons:")
        for key, reason in signal['reasons'].items():
            print(f"  • {reason}")
        
    else:
        print("\n✗ No valid signal generated")
        print("This is normal - most timeframes won't produce signals")
