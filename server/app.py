# ============================================================
# server/app.py - FastAPI 백엔드 서버 (Lightsail 배포용)
# 트레이딩 데이터 수신·저장·API 제공
# ============================================================

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
import json
import logging
from database import get_db, init_db, TradingSnapshot, TradeRecord
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

API_KEY = os.getenv("SERVER_API_KEY", "your-secret-api-key-here")

app = FastAPI(
    title="키움 자동매매 모니터링 API",
    description="100만원 자동매매 시스템 서버",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# Pydantic 모델
# ──────────────────────────────────────────────
class SyncPayload(BaseModel):
    timestamp:  str
    summary:    Dict[str, Any]
    stats:      Dict[str, Any]
    trade_log:  List[Dict[str, Any]]
    mode:       str = "mock"

class StatusPayload(BaseModel):
    status:     str
    timestamp:  str

# ──────────────────────────────────────────────
# 인증
# ──────────────────────────────────────────────
def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key

# ──────────────────────────────────────────────
# 시작 이벤트
# ──────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    init_db()
    logger.info("✅ 서버 시작 - DB 초기화 완료")

# ──────────────────────────────────────────────
# 엔드포인트
# ──────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "service": "키움 자동매매 모니터링 서버",
        "version": "1.0.0",
        "status": "running",
        "time": datetime.now().isoformat()
    }

@app.get("/health")
def health():
    return {"status": "healthy", "time": datetime.now().isoformat()}

@app.post("/api/trading/sync")
def receive_sync(payload: SyncPayload,
                 db: Session = Depends(get_db),
                 _: str = Depends(verify_api_key)):
    """클라이언트에서 데이터 동기화 수신"""
    try:
        snap = TradingSnapshot(
            timestamp        = payload.timestamp,
            portfolio_value  = payload.summary.get("portfolio_value", 0),
            cash             = payload.summary.get("cash", 0),
            position_value   = payload.summary.get("position_value", 0),
            total_pnl        = payload.summary.get("total_pnl", 0),
            total_pnl_pct    = payload.summary.get("total_pnl_pct", 0),
            daily_pnl        = payload.summary.get("daily_pnl", 0),
            position_count   = payload.summary.get("position_count", 0),
            win_rate         = payload.stats.get("win_rate_pct", 0),
            mode             = payload.mode,
            holdings_json    = json.dumps(payload.summary.get("holdings", []), ensure_ascii=False)
        )
        db.add(snap)

        # 신규 거래 저장
        for trade in payload.trade_log:
            existing = db.query(TradeRecord).filter(
                TradeRecord.timestamp == trade.get("timestamp"),
                TradeRecord.code      == trade.get("code"),
                TradeRecord.trade_type == trade.get("type")
            ).first()
            if not existing:
                rec = TradeRecord(
                    timestamp  = trade.get("timestamp", ""),
                    trade_type = trade.get("type", ""),
                    code       = trade.get("code", ""),
                    name       = trade.get("name", ""),
                    quantity   = trade.get("quantity", 0),
                    price      = trade.get("price", 0),
                    amount     = trade.get("amount", 0),
                    pnl        = trade.get("pnl", 0),
                    reason     = trade.get("reason", ""),
                    portfolio_value = trade.get("portfolio_value", 0)
                )
                db.add(rec)

        db.commit()
        return {"success": True, "message": "동기화 완료"}

    except Exception as e:
        db.rollback()
        logger.error(f"동기화 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/trading/status")
def update_status(payload: StatusPayload,
                  _: str = Depends(verify_api_key)):
    """시스템 상태 업데이트"""
    logger.info(f"시스템 상태: {payload.status} @ {payload.timestamp}")
    return {"success": True}


@app.get("/api/trading/snapshots")
def get_snapshots(limit: int = 100, db: Session = Depends(get_db)):
    """최근 스냅샷 조회 (대시보드용)"""
    snaps = db.query(TradingSnapshot)\
              .order_by(TradingSnapshot.id.desc())\
              .limit(limit)\
              .all()
    return [
        {
            "id":             s.id,
            "timestamp":      s.timestamp,
            "portfolio_value": s.portfolio_value,
            "cash":           s.cash,
            "position_value": s.position_value,
            "total_pnl":      s.total_pnl,
            "total_pnl_pct":  s.total_pnl_pct,
            "daily_pnl":      s.daily_pnl,
            "position_count": s.position_count,
            "win_rate":       s.win_rate,
            "mode":           s.mode
        }
        for s in reversed(snaps)
    ]


@app.get("/api/trading/trades")
def get_trades(limit: int = 100, db: Session = Depends(get_db)):
    """최근 거래 내역 조회"""
    trades = db.query(TradeRecord)\
               .order_by(TradeRecord.id.desc())\
               .limit(limit)\
               .all()
    return [
        {
            "id":            t.id,
            "timestamp":     t.timestamp,
            "type":          t.trade_type,
            "code":          t.code,
            "name":          t.name,
            "quantity":      t.quantity,
            "price":         t.price,
            "amount":        t.amount,
            "pnl":           t.pnl,
            "reason":        t.reason,
            "portfolio_value": t.portfolio_value
        }
        for t in reversed(trades)
    ]


@app.get("/api/trading/latest")
def get_latest(db: Session = Depends(get_db)):
    """최신 스냅샷 반환"""
    snap = db.query(TradingSnapshot)\
             .order_by(TradingSnapshot.id.desc())\
             .first()
    if not snap:
        return {"message": "데이터 없음"}
    return {
        "timestamp":      snap.timestamp,
        "portfolio_value": snap.portfolio_value,
        "cash":           snap.cash,
        "total_pnl":      snap.total_pnl,
        "total_pnl_pct":  snap.total_pnl_pct,
        "daily_pnl":      snap.daily_pnl,
        "position_count": snap.position_count,
        "holdings":       json.loads(snap.holdings_json or "[]"),
        "mode":           snap.mode
    }
