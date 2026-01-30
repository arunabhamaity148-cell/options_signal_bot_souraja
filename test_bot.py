"""
Unit tests for trading bot
"""
import pytest
import asyncio
from datetime import datetime
import pandas as pd
import numpy as np

from config.settings import settings
from core.indicators import TechnicalIndicators
from risk.position_sizer import RiskManager


class TestTechnicalIndicators:
    """Test technical indicator calculations"""
    
    def setup_method(self):
        """Setup test data"""
        self.indicators = TechnicalIndicators()
        
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
        self.df = pd.DataFrame({
            'open': np.random.uniform(40000, 41000, 100),
            'high': np.random.uniform(40500, 41500, 100),
            'low': np.random.uniform(39500, 40500, 100),
            'close': np.random.uniform(40000, 41000, 100),
            'volume': np.random.uniform(100, 1000, 100)
        }, index=dates)
    
    def test_calculate_ema(self):
        """Test EMA calculation"""
        ema = self.indicators.calculate_ema(self.df['close'], 20)
        assert len(ema) == len(self.df)
        assert not ema.isna().all()
    
    def test_calculate_rsi(self):
        """Test RSI calculation"""
        rsi = self.indicators.calculate_rsi(self.df['close'], 14)
        assert len(rsi) == len(self.df)
        assert (rsi.dropna() >= 0).all() and (rsi.dropna() <= 100).all()
    
    def test_calculate_all_indicators(self):
        """Test calculation of all indicators"""
        df_with_indicators = self.indicators.calculate_all_indicators(self.df)
        
        required_columns = [
            'ema_20', 'ema_50', 'ema_200', 'rsi', 'adx', 
            'atr', 'macd', 'bb_upper', 'volume_ma'
        ]
        
        for col in required_columns:
            assert col in df_with_indicators.columns


class TestRiskManager:
    """Test risk management functions"""
    
    def setup_method(self):
        """Setup test data"""
        self.risk_manager = RiskManager()
        self.risk_manager.set_account_balance(10000.0)
    
    def test_calculate_position_size(self):
        """Test position size calculation"""
        entry_price = 50000.0
        stop_loss = 49000.0
        
        position = self.risk_manager.calculate_position_size(
            entry_price, stop_loss
        )
        
        assert 'position_size' in position
        assert 'risk_amount' in position
        assert position['risk_amount'] == 10000.0 * settings.RISK_PER_TRADE
    
    def test_validate_risk_reward(self):
        """Test risk:reward validation"""
        entry_price = 50000.0
        stop_loss = 49000.0
        take_profit = 52000.0
        
        is_valid = self.risk_manager.validate_risk_reward(
            entry_price, stop_loss, take_profit
        )
        
        assert is_valid is True


def test_settings_validation():
    """Test configuration settings"""
    assert settings.validate() is True
    assert settings.RISK_PER_TRADE > 0
    assert settings.RISK_PER_TRADE <= 0.1
    assert settings.MIN_RISK_REWARD >= 1.0
    assert len(settings.TRADING_PAIRS) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

## 📄 File 29: `logs/.gitkeep`
```
# This file keeps the logs directory in git
