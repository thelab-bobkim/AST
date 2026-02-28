# ============================================================
# server/database.py - PostgreSQL ORM 설정
# SQLAlchemy + PostgreSQL
# ============================================================

import os
from sqlalchemy import create_engine, Column, Integer, Float, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# DB 접속 정보 (환경변수 우선)
DB_HOST     = os.getenv("DB_HOST",     "localhost")
DB_PORT     = os.getenv("DB_PORT",     "5432")
DB_NAME     = os.getenv("DB_NAME",     "trading_db")
DB_USER     = os.getenv("DB_USER",     "trading_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "trading_pass")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine       = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base         = declarative_base()


# ──────────────────────────────────────────────
# 테이블 정의
# ──────────────────────────────────────────────
class TradingSnapshot(Base):
    """포트폴리오 스냅샷 (주기적 저장)"""
    __tablename__ = "trading_snapshots"

    id              = Column(Integer, primary_key=True, index=True)
    timestamp       = Column(String(50), index=True)
    portfolio_value = Column(Float, default=0)
    cash            = Column(Float, default=0)
    position_value  = Column(Float, default=0)
    total_pnl       = Column(Float, default=0)
    total_pnl_pct   = Column(Float, default=0)
    daily_pnl       = Column(Float, default=0)
    position_count  = Column(Integer, default=0)
    win_rate        = Column(Float, default=0)
    mode            = Column(String(10), default="mock")
    holdings_json   = Column(Text, default="[]")
    created_at      = Column(DateTime, default=datetime.utcnow)


class TradeRecord(Base):
    """개별 거래 기록"""
    __tablename__ = "trade_records"

    id              = Column(Integer, primary_key=True, index=True)
    timestamp       = Column(String(50), index=True)
    trade_type      = Column(String(10))   # BUY | SELL
    code            = Column(String(10), index=True)
    name            = Column(String(50))
    quantity        = Column(Integer, default=0)
    price           = Column(Float, default=0)
    amount          = Column(Float, default=0)
    pnl             = Column(Float, default=0)
    reason          = Column(String(100))
    portfolio_value = Column(Float, default=0)
    created_at      = Column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────
# 유틸리티
# ──────────────────────────────────────────────
def init_db():
    """테이블 초기화"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI 의존성 주입용 DB 세션"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
