# -*- coding: utf-8 -*-
# ============================================================
# simulation.py - 오프라인 시뮬레이션 모드
# 키움 API 없이도 전체 시스템 동작 테스트
# ============================================================

"""
이 파일은 키움 API 없이 전체 시스템을 시뮬레이션합니다.
- 실제 API 대신 랜덤 시세 데이터 생성
- 서버 API 연동 테스트 포함
- 전략·리스크관리 전체 흐름 검증
"""

import time
import logging
import random
import requests
from datetime import datetime, timedelta
import numpy as np
from strategy import MACrossoverStrategy, Signal, TradeSignal
from risk_manager import RiskManager, RiskConfig
import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


MOCK_STOCKS = {
    "005930": {"name": "삼성전자",  "price": 70000,  "volatility": 0.02},
    "000660": {"name": "SK하이닉스","price": 120000, "volatility": 0.025},
    "035420": {"name": "NAVER",    "price": 180000, "volatility": 0.03},
    "005380": {"name": "현대차",   "price": 220000, "volatility": 0.022},
    "051910": {"name": "LG화학",   "price": 350000, "volatility": 0.028},
}


class MockPriceGenerator:
    """모의 시세 생성기"""

    def __init__(self):
        self.prices = {code: info["price"] for code, info in MOCK_STOCKS.items()}
        self.histories: dict = {code: [] for code in MOCK_STOCKS}
        self._init_histories()

    def _init_histories(self):
        """초기 30일치 히스토리 생성"""
        for code, info in MOCK_STOCKS.items():
            price = info["price"]
            vol   = info["volatility"]
            for i in range(30):
                r = np.random.normal(0, vol)
                price *= (1 + r)
                self.histories[code].append({
                    "date":   (datetime.now() - timedelta(days=30-i)).strftime("%Y%m%d"),
                    "open":   round(price * 0.995),
                    "high":   round(price * 1.01),
                    "low":    round(price * 0.99),
                    "close":  round(price),
                    "volume": random.randint(500000, 3000000)
                })
            self.prices[code] = round(price)

    def tick(self) -> dict:
        """1틱 시세 업데이트"""
        updates = {}
        for code, info in MOCK_STOCKS.items():
            vol = info["volatility"] / 10
            r   = np.random.normal(0, vol)
            new_price = round(self.prices[code] * (1 + r))
            self.prices[code] = new_price
            updates[code] = new_price

            # 히스토리 최신화
            today = datetime.now().strftime("%Y%m%d")
            if self.histories[code] and self.histories[code][-1]["date"] == today:
                self.histories[code][-1]["close"] = new_price
                self.histories[code][-1]["high"] = max(
                    self.histories[code][-1]["high"], new_price)
                self.histories[code][-1]["low"] = min(
                    self.histories[code][-1]["low"], new_price)
            else:
                self.histories[code].append({
                    "date": today,
                    "open": new_price, "high": new_price,
                    "low": new_price, "close": new_price,
                    "volume": random.randint(500000, 3000000)
                })
        return updates

    def get_ohlcv(self, code: str) -> list:
        return self.histories.get(code, [])


def run_simulation(duration_seconds: int = 60, send_to_server: bool = False):
    """
    시뮬레이션 실행
    duration_seconds: 시뮬레이션 시간(초)
    send_to_server: True이면 Lightsail 서버로 데이터 전송
    """
    print("\n" + "="*60)
    print("🎮 오프라인 시뮬레이션 시작")
    print(f"   기간: {duration_seconds}초")
    print(f"   서버 전송: {'ON' if send_to_server else 'OFF'}")
    print("="*60)

    generator = MockPriceGenerator()
    strategy  = MACrossoverStrategy(
        short_period=5, long_period=20, rsi_period=14
    )
    risk_mgr  = RiskManager(RiskConfig(
        initial_capital=1_000_000,
        max_position_ratio=0.20,
        max_total_positions=5,
        stop_loss_ratio=0.01,
        take_profit_ratio=0.03
    ))

    start_time = time.time()
    cycle      = 0

    while time.time() - start_time < duration_seconds:
        cycle += 1
        print(f"\n--- Cycle {cycle} | {datetime.now().strftime('%H:%M:%S')} ---")

        # 시세 업데이트
        prices = generator.tick()
        risk_mgr.update_prices(prices)

        # 손절·익절 체크
        to_close = risk_mgr.check_stop_conditions()
        for item in to_close:
            result = risk_mgr.close_position(item["code"], item["price"], item["reason"])
            if result:
                print(f"  🔴 청산: {result['name']} PnL={result['pnl']:+,.0f}원 ({result['reason']})")

        # 신호 스캔
        stock_data = {}
        for code in list(MOCK_STOCKS.keys()):
            stock_data[code] = {
                "name":  MOCK_STOCKS[code]["name"],
                "ohlcv": generator.get_ohlcv(code),
                "price": prices.get(code, 0)
            }

        signals = strategy.generate_signals(stock_data)
        for sig in signals:
            if sig.signal in (Signal.BUY, Signal.STRONG_BUY):
                can_buy, reason = risk_mgr.can_buy(sig.code, sig.price)
                if can_buy:
                    qty = risk_mgr.calculate_order_quantity(sig.code, sig.price)
                    if qty > 0:
                        risk_mgr.open_position(sig.code, sig.name, qty, sig.price)
                        print(f"  🟢 매수: {sig.name} {qty}주 @{sig.price:,}원 | {sig.reason}")
            elif sig.signal in (Signal.SELL, Signal.STRONG_SELL):
                if sig.code in risk_mgr.positions:
                    pos = risk_mgr.positions[sig.code]
                    result = risk_mgr.close_position(sig.code, sig.price, sig.reason)
                    if result:
                        print(f"  🔵 매도(신호): {result['name']} PnL={result['pnl']:+,.0f}원")

        # 포트폴리오 현황 출력
        summary = risk_mgr.get_summary()
        print(f"  💼 자산: ₩{summary['portfolio_value']:,.0f} | "
              f"현금: ₩{summary['cash']:,.0f} | "
              f"보유: {summary['position_count']}종목 | "
              f"총손익: {summary['total_pnl']:+,.0f}원")

        # 서버 전송
        if send_to_server:
            _send_to_server(risk_mgr)

        time.sleep(5)  # 5초 간격

    # 최종 결과
    summary = risk_mgr.get_summary()
    stats   = risk_mgr.get_performance_stats()

    print("\n" + "="*60)
    print("📊 시뮬레이션 최종 결과")
    print("="*60)
    print(f"  초기 자본   : ₩{1_000_000:,}")
    print(f"  최종 자산   : ₩{summary['portfolio_value']:,.0f}")
    print(f"  총 손익     : ₩{summary['total_pnl']:+,.0f} ({summary['total_pnl_pct']:+.2f}%)")

    if isinstance(stats, dict) and "total_trades" in stats:
        print(f"  총 거래횟수 : {stats['total_trades']}회")
        print(f"  승률        : {stats['win_rate_pct']:.1f}%")
        print(f"  평균 수익   : ₩{stats['avg_win']:+,.0f}")
        print(f"  평균 손실   : ₩{stats['avg_loss']:+,.0f}")
    print("="*60)

    return summary


def _send_to_server(risk_mgr: RiskManager):
    """서버로 데이터 전송"""
    try:
        payload = {
            "timestamp":  datetime.now().isoformat(),
            "summary":    risk_mgr.get_summary(),
            "stats":      risk_mgr.get_performance_stats(),
            "trade_log":  risk_mgr.get_trade_log(10),
            "mode":       "simulation"
        }
        resp = requests.post(
            f"{config.SERVER_API_URL}/api/trading/sync",
            json=payload,
            headers={"X-API-Key": config.SERVER_API_KEY},
            timeout=5
        )
        logger.debug(f"서버 전송: {resp.status_code}")
    except Exception as e:
        logger.warning(f"서버 전송 실패: {e}")


if __name__ == "__main__":
    # 서버 연결 여부 확인
    try:
        r = requests.get(f"{config.SERVER_API_URL}/health", timeout=3)
        server_ok = r.status_code == 200
    except:
        server_ok = False

    print(f"서버 상태: {'✅ 연결됨' if server_ok else '❌ 미연결 (서버 없이 실행)'}")
    run_simulation(duration_seconds=60, send_to_server=server_ok)
