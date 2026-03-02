# -*- coding: utf-8 -*-
# ============================================================
# trader.py - 메인 트레이딩 엔진 (오케스트레이터)
# 전략·리스크관리·API를 통합
# ============================================================
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import time
import logging
import schedule
import requests
from datetime import datetime, time as dtime
from typing import Dict, List, Optional

import config
from kiwoom_wrapper import KiwoomWrapper
from strategy import MACrossoverStrategy, Signal
from risk_manager import RiskManager, RiskConfig

logger = logging.getLogger(__name__)


def setup_logging():
    """로거 설정"""
    import os
    os.makedirs("logs", exist_ok=True)

    from logging.handlers import RotatingFileHandler
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    # 파일 핸들러
    fh = RotatingFileHandler(
        config.LOG_FILE,
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_COUNT
    )
    fh.setFormatter(fmt)

    # 콘솔 핸들러 (UTF-8 강제 설정)
    import sys, io
    utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    ch = logging.StreamHandler(utf8_stdout)
    ch.setFormatter(fmt)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.LOG_LEVEL))
    root_logger.addHandler(fh)
    root_logger.addHandler(ch)


class AutoTrader:
    """
    자동매매 메인 엔진
    - 키움 API 연동
    - 전략 신호 생성
    - 리스크 관리
    - 서버 데이터 동기화
    """

    def __init__(self):
        # 키움 API
        self.kiwoom = KiwoomWrapper(is_mock=config.IS_MOCK_TRADING)

        # 전략
        self.strategy = MACrossoverStrategy(
            short_period      = config.SHORT_MA_PERIOD,
            long_period       = config.LONG_MA_PERIOD,
            rsi_period        = config.RSI_PERIOD,
            rsi_oversold      = config.RSI_OVERSOLD,
            rsi_overbought    = config.RSI_OVERBOUGHT,
        )

        # 리스크 관리
        self.risk_manager = RiskManager(RiskConfig(
            initial_capital    = config.INITIAL_CAPITAL,
            max_position_ratio = config.MAX_POSITION_RATIO,
            max_total_positions = config.MAX_POSITION_COUNT,
            stop_loss_ratio    = config.STOP_LOSS_RATIO,
            take_profit_ratio  = config.TAKE_PROFIT_RATIO,
        ))

        self.is_running  = False
        self.stock_data: Dict[str, Dict] = {}   # 종목 시세 캐시

    # ──────────────────────────────────────────────
    # 시작·종료
    # ──────────────────────────────────────────────
    def start(self):
        """자동매매 시작"""
        logger.info("=" * 60)
        logger.info("🚀 키움 자동매매 시스템 시작")
        logger.info(f"   모드: {'모의투자' if config.IS_MOCK_TRADING else '실전투자'}")
        logger.info(f"   자본: {config.INITIAL_CAPITAL:,}원")
        logger.info(f"   전략: {config.STRATEGY_NAME}")
        logger.info("=" * 60)

        if not self.kiwoom.connect():
            logger.error("키움 API 연결 실패 - 종료")
            return

        self.is_running = True
        self._schedule_jobs()
        self._send_status("STARTED")

        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("사용자 중단 요청")
        finally:
            self.stop()

    def stop(self):
        """자동매매 종료"""
        self.is_running = False
        self.kiwoom.disconnect()
        self._send_status("STOPPED")
        logger.info("🔴 자동매매 시스템 종료")

    # ──────────────────────────────────────────────
    # 스케줄 등록
    # ──────────────────────────────────────────────
    def _schedule_jobs(self):
        """장 시간별 작업 스케줄 등록"""
        schedule.every().day.at("08:50").do(self._pre_market)
        schedule.every().day.at("09:00").do(self._market_open)
        schedule.every(5).minutes.do(self._monitor_positions)  # 5분마다 포지션 모니터링
        schedule.every(30).minutes.do(self._scan_signals)       # 30분마다 신호 스캔
        schedule.every().day.at("15:20").do(self._pre_close)
        schedule.every().day.at("15:30").do(self._market_close)
        schedule.every().hour.do(self._sync_server)             # 1시간마다 서버 동기화
        logger.info("✅ 스케줄 등록 완료")

    # ──────────────────────────────────────────────
    # 장 시간별 루틴
    # ──────────────────────────────────────────────
    def _pre_market(self):
        """장 전 준비 (08:50)"""
        logger.info("⏰ 장 전 준비 시작")
        self.risk_manager.reset_daily_pnl()
        self._load_ohlcv_data()
        logger.info(f"   종목 데이터 로드 완료: {len(self.stock_data)}개")

    def _market_open(self):
        """장 시작 (09:00)"""
        logger.info("🔔 장 시작")
        self._scan_signals()

    def _monitor_positions(self):
        """포지션 모니터링 + 손절·익절 체크"""
        if not self._is_market_hours():
            return

        # 현재가 업데이트
        price_data = {}
        for code in list(self.risk_manager.positions.keys()):
            info = self.kiwoom.get_current_price(code)
            if info and info.get("price"):
                price_data[code] = info["price"]

        self.risk_manager.update_prices(price_data)

        # 손절·익절 체크
        to_close = self.risk_manager.check_stop_conditions()
        for item in to_close:
            self._execute_sell(item["code"], item["price"], item["reason"])

    def _scan_signals(self):
        """매매 신호 스캔 및 주문 실행"""
        if not self._is_market_hours():
            return

        logger.info("🔍 매매 신호 스캔 시작")
        signals = self.strategy.generate_signals(self.stock_data)

        for sig in signals:
            if sig.signal in (Signal.BUY, Signal.STRONG_BUY):
                self._handle_buy_signal(sig)
            elif sig.signal in (Signal.SELL, Signal.STRONG_SELL):
                self._handle_sell_signal(sig)

        self._sync_server()

    def _pre_close(self):
        """장 마감 전 정리 (15:20) - 당일 미청산 포지션 처리"""
        logger.info("⚠️ 장 마감 전 포지션 점검")
        # 손익이 마이너스인 포지션 정리 여부 검토
        for code, pos in list(self.risk_manager.positions.items()):
            if pos.unrealized_pnl_pct < -0.5:  # -0.5% 이하면 청산
                logger.info(f"장마감 정리: {pos.name} ({pos.unrealized_pnl_pct:.2f}%)")
                self._execute_sell(code, pos.current_price, "장마감 손실 정리")

    def _market_close(self):
        """장 마감 (15:30)"""
        logger.info("🔕 장 마감")
        stats = self.risk_manager.get_performance_stats()
        summary = self.risk_manager.get_summary()
        logger.info(f"📊 오늘의 결과 | 일일손익: {summary['daily_pnl']:+,.0f}원")
        self._sync_server(force=True)

    # ──────────────────────────────────────────────
    # 매수·매도 처리
    # ──────────────────────────────────────────────
    def _handle_buy_signal(self, sig):
        """매수 신호 처리"""
        can_buy, reason = self.risk_manager.can_buy(sig.code, sig.price)
        if not can_buy:
            logger.info(f"매수 불가 | {sig.name}: {reason}")
            return

        qty = self.risk_manager.calculate_order_quantity(sig.code, sig.price)
        if qty <= 0:
            logger.warning(f"주문 수량 0 | {sig.name}")
            return

        # 주문 전송
        order_result = self.kiwoom.send_order("buy", sig.code, qty)
        if order_result.get("success"):
            self.risk_manager.open_position(sig.code, sig.name, qty, sig.price)
            self._notify(f"🟢 매수 | {sig.name} {qty}주 @{sig.price:,}원\n근거: {sig.reason}")
        else:
            logger.error(f"매수 주문 실패 | {sig.name}: {order_result.get('message')}")

    def _handle_sell_signal(self, sig):
        """매도 신호 처리"""
        if sig.code not in self.risk_manager.positions:
            return
        self._execute_sell(sig.code, sig.price, sig.reason)

    def _execute_sell(self, code: str, price: float, reason: str):
        """매도 주문 실행"""
        if code not in self.risk_manager.positions:
            return

        pos = self.risk_manager.positions[code]
        order_result = self.kiwoom.send_order("sell", code, pos.quantity)

        if order_result.get("success"):
            result = self.risk_manager.close_position(code, price, reason)
            if result:
                emoji = "🔴" if result["pnl"] < 0 else "🟡"
                self._notify(
                    f"{emoji} 매도 | {result['name']} {result['quantity']}주 @{price:,}원\n"
                    f"손익: {result['pnl']:+,.0f}원 ({result['pnl_pct']:+.2f}%) | {reason}"
                )
        else:
            logger.error(f"매도 주문 실패 | {code}: {order_result.get('message')}")

    # ──────────────────────────────────────────────
    # 데이터 로드
    # ──────────────────────────────────────────────
    def _load_ohlcv_data(self):
        """감시 종목 OHLCV 데이터 로드"""
        today_str = datetime.now().strftime("%Y%m%d")
        self.stock_data = {}

        for code in config.WATCHLIST:
            ohlcv = self.kiwoom.get_daily_ohlcv(code, today_str, count=60)
            current = self.kiwoom.get_current_price(code)

            self.stock_data[code] = {
                "name":  current.get("name", code),
                "ohlcv": ohlcv,
                "price": current.get("price", 0)
            }
            time.sleep(0.2)   # API 호출 제한 방지

        logger.info(f"데이터 로드 완료: {len(self.stock_data)}개 종목")

    # ──────────────────────────────────────────────
    # 서버 동기화 (Lightsail)
    # ──────────────────────────────────────────────
    def _sync_server(self, force: bool = False):
        """Lightsail 서버로 데이터 전송"""
        try:
            payload = {
                "timestamp":  datetime.now().isoformat(),
                "summary":    self.risk_manager.get_summary(),
                "stats":      self.risk_manager.get_performance_stats(),
                "trade_log":  self.risk_manager.get_trade_log(20),
                "mode":       "mock" if config.IS_MOCK_TRADING else "live"
            }
            headers = {
                "X-API-Key":    config.SERVER_API_KEY,
                "Content-Type": "application/json"
            }
            resp = requests.post(
                f"{config.SERVER_API_URL}/api/trading/sync",
                json=payload, headers=headers, timeout=5
            )
            if resp.status_code == 200:
                logger.debug("서버 동기화 완료")
            else:
                logger.warning(f"서버 동기화 실패: {resp.status_code}")
        except Exception as e:
            logger.warning(f"서버 동기화 오류: {e}")

    def _send_status(self, status: str):
        """시스템 상태 전송"""
        try:
            requests.post(
                f"{config.SERVER_API_URL}/api/trading/status",
                json={"status": status, "timestamp": datetime.now().isoformat()},
                headers={"X-API-Key": config.SERVER_API_KEY},
                timeout=3
            )
        except Exception:
            pass

    # ──────────────────────────────────────────────
    # 유틸리티
    # ──────────────────────────────────────────────
    def _is_market_hours(self) -> bool:
        """현재 장 시간 여부"""
        now = datetime.now().time()
        open_t  = dtime(9, 0)
        close_t = dtime(15, 30)
        weekday = datetime.now().weekday()
        return weekday < 5 and open_t <= now <= close_t

    def _notify(self, message: str):
        """텔레그램 알림 전송"""
        logger.info(f"[알림] {message}")
        if not config.ENABLE_TELEGRAM:
            return
        try:
            import telebot
            bot = telebot.TeleBot(config.TELEGRAM_BOT_TOKEN)
            bot.send_message(config.TELEGRAM_CHAT_ID, message)
        except Exception as e:
            logger.warning(f"텔레그램 전송 실패: {e}")


# ──────────────────────────────────────────────
# 엔트리포인트
# ──────────────────────────────────────────────
if __name__ == "__main__":
    setup_logging()
    trader = AutoTrader()
    trader.start()
