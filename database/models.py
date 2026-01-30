"""
Database models and schema for trading bot
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, 
    DateTime, Boolean, JSON, Text, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import asyncpg
from contextlib import asynccontextmanager

from config.settings import settings

Base = declarative_base()


class Signal(Base):
    """Trading signal model"""
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    pair = Column(String(20), nullable=False, index=True)
    direction = Column(String(10), nullable=False)
    
    strike_price = Column(Float, nullable=False)
    strike_type = Column(String(10), nullable=False)
    expiry_date = Column(DateTime, nullable=False)
    premium_estimate = Column(Float)
    
    entry_min = Column(Float, nullable=False)
    entry_max = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit_1 = Column(Float, nullable=False)
    take_profit_2 = Column(Float, nullable=False)
    take_profit_3 = Column(Float, nullable=False)
    
    risk_amount = Column(Float, nullable=False)
    risk_reward = Column(Float, nullable=False)
    confluence_score = Column(Float, nullable=False)
    
    setup_logic = Column(Text)
    indicators = Column(JSON)
    
    status = Column(String(20), default="PENDING")
    trade_type = Column(String(20), default="PAPER")
    
    entry_price = Column(Float)
    exit_price = Column(Float)
    pnl = Column(Float)
    exit_time = Column(DateTime)
    exit_reason = Column(String(50))
    
    telegram_message_id = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_pair_timestamp', 'pair', 'timestamp'),
        Index('idx_status_timestamp', 'status', 'timestamp'),
    )


class TradingStats(Base):
    """Daily trading statistics"""
    __tablename__ = "trading_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, unique=True, index=True)
    
    total_signals = Column(Integer, default=0)
    signals_taken = Column(Integer, default=0)
    signals_skipped = Column(Integer, default=0)
    
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    consecutive_losses = Column(Integer, default=0)
    
    total_pnl = Column(Float, default=0.0)
    win_rate = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    
    is_paused = Column(Boolean, default=False)
    pause_reason = Column(String(100))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MarketData(Base):
    """Cached market data"""
    __tablename__ = "market_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pair = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    
    indicators = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_pair_timeframe_timestamp', 'pair', 'timeframe', 'timestamp'),
    )


class UserSettings(Base):
    """User preferences and settings"""
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), unique=True, nullable=False)
    
    preferred_pairs = Column(JSON)
    risk_per_trade = Column(Float, default=0.02)
    paper_trading_mode = Column(Boolean, default=True)
    
    notify_signals = Column(Boolean, default=True)
    notify_entries = Column(Boolean, default=True)
    notify_exits = Column(Boolean, default=True)
    
    min_confluence_score = Column(Float, default=7.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Database:
    """Database connection manager"""
    
    def __init__(self):
        self.engine = None
        self.session_maker = None
        self.pool = None
        
    def initialize(self):
        """Initialize database connection"""
        self.engine = create_engine(
            settings.DATABASE_URL,
            poolclass=QueuePool,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=20,
            pool_pre_ping=True,
            echo=False
        )
        
        self.session_maker = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        
    async def initialize_async(self):
        """Initialize async database pool"""
        self.pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=5,
            max_size=settings.DATABASE_POOL_SIZE,
            command_timeout=60
        )
        
    async def close_async(self):
        """Close async database pool"""
        if self.pool:
            await self.pool.close()
    
    def get_session(self):
        """Get database session"""
        return self.session_maker()
    
    @asynccontextmanager
    async def acquire(self):
        """Acquire async database connection"""
        async with self.pool.acquire() as connection:
            yield connection
    
    async def execute(self, query: str, *args) -> Any:
        """Execute async query"""
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def execute_one(self, query: str, *args) -> Optional[Dict]:
        """Execute query and return one result"""
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def execute_many(self, query: str, args_list: list):
        """Execute many queries"""
        async with self.acquire() as conn:
            await conn.executemany(query, args_list)


db = Database()
