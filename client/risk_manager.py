# ============================================================
# risk_manager.py - 리스크 관리 모듈
# 100만원 자산 기준 손실 최소화 전략
# ============================================================

import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RiskConfig:
    initial_capital:      float = 1_000_000  # 초기 자본
    max_position_ratio:   float = 0.20       # 종목당 최대 비중 20%
    max_total_positions:  int   = 5          # 최대 보유 종목 수
    stop_loss_ratio:      float = 0.01       # 손절 1%
    take_profit_ratio:    float = 0.03       # 익절 3%
    daily_loss_limit:     float = 0.03       # 일일 최대 손실 3%
    max_drawdown_limit:   float = 0.10       # 최대 낙폭 10%
    min_cash_ratio:       float = 0.20       # 최소 현금 비중 20%


@dataclass
class Position:
    code:         str
    name:         str
    quantity:     int
    avg_price:    float
    current_price: float = 0
    entry_time:   str = ""
    stop_price:   float = 0     # 손절가
    target_price: float = 0     # 익절가

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def cost_value(self) -> float:
        return self.quantity * self.avg_price

    @property
    def unrealized_pnl(self) -> float:
        return self.market_value - self.cost_value

    @property
    def unrealized_pnl_pct(self) -> float:
        return (self.current_price / self.avg_price - 1) * 100 if self.avg_price > 0 else 0


class RiskManager:
    """
    리스크 관리자
    - 포지션 사이징 (켈리 기준 / 고정 비율)
    - 손절·익절 자동 관리
    - 일일 손실 한도 관리
    - 포트폴리오 전체 리스크 모니터링
    """

    def __init__(self, config: RiskConfig = None):
        self.config     = config or RiskConfig()
        self.positions: Dict[str, Position] = {}
        self.cash       = self.config.initial_capital
        self.daily_pnl  = 0.0
        self.total_pnl  = 0.0
        self.trade_log: List[Dict] = []
        self._today     = date.today()

    # ──────────────────────────────────────────────
    # 자산 현황
    # ──────────────────────────────────────────────
    @property
    def portfolio_value(self) -> float:
        return self.cash + sum(p.market_value for p in self.positions.values())

    @property
    def position_value(self) -> float:
        return sum(p.market_value for p in self.positions.values())

    @property
    def cash_ratio(self) -> float:
        return self.cash / self.portfolio_value if self.portfolio_value > 0 else 1.0

    def get_summary(self) -> Dict:
        return {
            "portfolio_value":    round(self.portfolio_value, 0),
            "cash":               round(self.cash, 0),
            "position_value":     round(self.position_value, 0),
            "cash_ratio_pct":     round(self.cash_ratio * 100, 1),
            "total_pnl":          round(self.total_pnl, 0),
            "total_pnl_pct":      round(self.total_pnl / self.config.initial_capital * 100, 2),
            "daily_pnl":          round(self.daily_pnl, 0),
            "position_count":     len(self.positions),
            "holdings":           [self._position_to_dict(p) for p in self.positions.values()]
        }

    def _position_to_dict(self, p: Position) -> Dict:
        return {
            "code": p.code, "name": p.name,
            "quantity": p.quantity, "avg_price": p.avg_price,
            "current_price": p.current_price,
            "market_value": round(p.market_value, 0),
            "unrealized_pnl": round(p.unrealized_pnl, 0),
            "unrealized_pnl_pct": round(p.unrealized_pnl_pct, 2),
            "stop_price": p.stop_price, "target_price": p.target_price
        }

    # ──────────────────────────────────────────────
    # 매수 가능 여부 및 수량 계산
    # ──────────────────────────────────────────────
    def can_buy(self, code: str, price: float) -> Tuple[bool, str]:
        """매수 가능 여부 확인"""
        # 이미 보유 중
        if code in self.positions:
            return False, f"이미 보유 중 ({code})"

        # 최대 종목 수
        if len(self.positions) >= self.config.max_total_positions:
            return False, f"최대 종목 수 초과 ({self.config.max_total_positions}종목)"

        # 최소 현금 비중
        if self.cash_ratio < self.config.min_cash_ratio:
            return False, f"현금 비중 부족 ({self.cash_ratio*100:.1f}%)"

        # 일일 손실 한도
        if self.daily_pnl < -(self.config.initial_capital * self.config.daily_loss_limit):
            return False, f"일일 손실 한도 초과 ({self.daily_pnl:,.0f}원)"

        # 최대 낙폭
        drawdown = (self.portfolio_value - self.config.initial_capital) / self.config.initial_capital
        if drawdown < -self.config.max_drawdown_limit:
            return False, f"최대 낙폭 초과 ({drawdown*100:.1f}%)"

        # 최소 주문 금액 (1주 이상)
        if price > self.cash:
            return False, f"잔금 부족 (현금: {self.cash:,.0f}원, 주가: {price:,.0f}원)"

        return True, "OK"

    def calculate_order_quantity(self, code: str, price: float) -> int:
        """
        주문 수량 계산
        포지션당 최대 20%, 현금의 95% 이내
        """
        max_invest = min(
            self.portfolio_value * self.config.max_position_ratio,
            self.cash * 0.95
        )
        qty = int(max_invest / price)
        return max(qty, 0)

    # ──────────────────────────────────────────────
    # 포지션 등록·업데이트·제거
    # ──────────────────────────────────────────────
    def open_position(self, code: str, name: str,
                      quantity: int, price: float) -> bool:
        """매수 포지션 등록"""
        cost = quantity * price
        if cost > self.cash:
            logger.warning(f"현금 부족: 필요={cost:,.0f}, 보유={self.cash:,.0f}")
            return False

        self.cash -= cost
        stop_price   = round(price * (1 - self.config.stop_loss_ratio))
        target_price = round(price * (1 + self.config.take_profit_ratio))

        self.positions[code] = Position(
            code=code, name=name, quantity=quantity,
            avg_price=price, current_price=price,
            entry_time=datetime.now().isoformat(),
            stop_price=stop_price, target_price=target_price
        )

        logger.info(f"📈 포지션 등록 | {name}({code}) {quantity}주 @{price:,}원 "
                    f"| 손절={stop_price:,} | 익절={target_price:,}")
        self._log_trade("BUY", code, name, quantity, price)
        return True

    def close_position(self, code: str, price: float, reason: str = "") -> Optional[Dict]:
        """매도 포지션 청산"""
        if code not in self.positions:
            return None

        pos = self.positions[code]
        revenue = pos.quantity * price
        pnl     = revenue - pos.cost_value
        pnl_pct = (price / pos.avg_price - 1) * 100

        self.cash      += revenue
        self.daily_pnl += pnl
        self.total_pnl += pnl

        result = {
            "code": code, "name": pos.name,
            "quantity": pos.quantity,
            "buy_price":  pos.avg_price,
            "sell_price": price,
            "pnl":        round(pnl, 0),
            "pnl_pct":    round(pnl_pct, 2),
            "reason":     reason
        }

        logger.info(f"📉 포지션 청산 | {pos.name}({code}) {pos.quantity}주 @{price:,}원 "
                    f"| PnL={pnl:+,.0f}원 ({pnl_pct:+.2f}%) | 사유: {reason}")
        self._log_trade("SELL", code, pos.name, pos.quantity, price, pnl=pnl, reason=reason)
        del self.positions[code]
        return result

    def update_prices(self, price_data: Dict[str, float]):
        """현재가 업데이트"""
        for code, price in price_data.items():
            if code in self.positions:
                self.positions[code].current_price = price

    # ──────────────────────────────────────────────
    # 손절·익절 자동 체크
    # ──────────────────────────────────────────────
    def check_stop_conditions(self) -> List[Dict]:
        """
        모든 포지션에 대해 손절/익절 조건 검사
        Returns: 청산해야 할 포지션 목록
        """
        to_close = []
        for code, pos in self.positions.items():
            if pos.current_price <= 0:
                continue

            # 손절
            if pos.current_price <= pos.stop_price:
                to_close.append({
                    "code": code, "price": pos.current_price,
                    "reason": f"손절({pos.stop_price:,}원 도달)"
                })
            # 익절
            elif pos.current_price >= pos.target_price:
                to_close.append({
                    "code": code, "price": pos.current_price,
                    "reason": f"익절({pos.target_price:,}원 도달)"
                })
            # 트레일링 스탑: 고점 대비 2% 이상 하락 시
            elif pos.unrealized_pnl_pct >= 2.0:
                trail_stop = pos.current_price * 0.98
                if trail_stop > pos.stop_price:
                    pos.stop_price = round(trail_stop)
                    logger.debug(f"트레일링 스탑 상향: {pos.name} → {pos.stop_price:,}원")

        return to_close

    # ──────────────────────────────────────────────
    # 일자 리셋
    # ──────────────────────────────────────────────
    def reset_daily_pnl(self):
        """일별 손익 리셋 (매일 장 시작 시 호출)"""
        self.daily_pnl = 0.0
        self._today = date.today()
        logger.info(f"📅 일별 손익 리셋 ({self._today})")

    # ──────────────────────────────────────────────
    # 거래 로그
    # ──────────────────────────────────────────────
    def _log_trade(self, trade_type: str, code: str, name: str,
                   quantity: int, price: float, pnl: float = 0, reason: str = ""):
        self.trade_log.append({
            "timestamp": datetime.now().isoformat(),
            "type":      trade_type,
            "code":      code,
            "name":      name,
            "quantity":  quantity,
            "price":     price,
            "amount":    quantity * price,
            "pnl":       pnl,
            "reason":    reason,
            "portfolio_value": round(self.portfolio_value, 0)
        })

    def get_trade_log(self, limit: int = 50) -> List[Dict]:
        return self.trade_log[-limit:]

    def get_performance_stats(self) -> Dict:
        """성과 통계"""
        sells = [t for t in self.trade_log if t["type"] == "SELL"]
        if not sells:
            return {"message": "아직 청산 거래 없음"}

        pnls    = [t["pnl"] for t in sells]
        wins    = [p for p in pnls if p > 0]
        losses  = [p for p in pnls if p <= 0]

        win_rate    = len(wins) / len(pnls) * 100 if pnls else 0
        avg_win     = sum(wins) / len(wins) if wins else 0
        avg_loss    = sum(losses) / len(losses) if losses else 0
        profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float('inf')

        return {
            "total_trades":    len(sells),
            "win_rate_pct":    round(win_rate, 1),
            "avg_win":         round(avg_win, 0),
            "avg_loss":        round(avg_loss, 0),
            "profit_factor":   round(profit_factor, 2),
            "total_pnl":       round(self.total_pnl, 0),
            "total_return_pct": round(self.total_pnl / self.config.initial_capital * 100, 2)
        }
