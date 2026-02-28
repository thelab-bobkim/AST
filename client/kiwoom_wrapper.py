# ============================================================
# kiwoom_wrapper.py - 키움 OpenAPI 래퍼
# pykiwoom 기반, 실전/모의 자동 전환
# ============================================================

import sys
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Windows 환경에서만 pykiwoom 임포트
try:
    from pykiwoom.kiwoom import Kiwoom
    KIWOOM_AVAILABLE = True
except ImportError:
    KIWOOM_AVAILABLE = False
    logger.warning("pykiwoom 미설치 - 시뮬레이션 모드로 실행됩니다.")


class KiwoomWrapper:
    """
    키움 OpenAPI 래퍼 클래스
    - 실전/모의 자동 전환
    - 연결·로그인 관리
    - 데이터 조회·주문 통합
    """

    def __init__(self, is_mock: bool = True):
        self.is_mock = is_mock
        self.kiwoom: Optional[Kiwoom] = None
        self.is_connected = False
        self.account_number = ""
        self._login_event = None

    # ──────────────────────────────────────────────
    # 연결 및 로그인
    # ──────────────────────────────────────────────
    def connect(self) -> bool:
        """키움 OpenAPI 연결 및 로그인"""
        if not KIWOOM_AVAILABLE:
            logger.error("pykiwoom 라이브러리가 없습니다. pip install pykiwoom 실행 후 재시도.")
            return False

        try:
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance() or QApplication(sys.argv)

            self.kiwoom = Kiwoom()
            self.kiwoom.CommConnect(block=True)

            # 로그인 상태 확인
            login_state = self.kiwoom.GetConnectState()
            if login_state == 1:
                self.is_connected = True
                accounts = self.kiwoom.GetLoginInfo("ACCNO")
                self.account_number = accounts.split(';')[0]
                logger.info(f"✅ 키움 로그인 성공 | 계좌: {self.account_number}")

                # 모의투자 서버 확인
                server = self.kiwoom.GetLoginInfo("GetServerGubun")
                server_name = "모의투자" if server == "1" else "실전투자"
                logger.info(f"📡 서버: {server_name}")
                return True
            else:
                logger.error("❌ 키움 로그인 실패")
                return False

        except Exception as e:
            logger.error(f"연결 오류: {e}")
            return False

    def disconnect(self):
        """연결 해제"""
        self.is_connected = False
        logger.info("키움 API 연결 해제")

    # ──────────────────────────────────────────────
    # 계좌 정보 조회
    # ──────────────────────────────────────────────
    def get_account_balance(self) -> Dict:
        """계좌 잔고 조회 (예수금, 총평가금액 등)"""
        if not self.is_connected:
            return {}

        try:
            # OPW00001: 예수금 상세현황
            self.kiwoom.SetInputValue("계좌번호", self.account_number)
            self.kiwoom.SetInputValue("비밀번호", "")
            self.kiwoom.SetInputValue("비밀번호입력매체구분", "00")
            self.kiwoom.SetInputValue("조회구분", "2")
            self.kiwoom.CommRqData("예수금상세현황조회", "opw00001", 0, "0101")

            balance = {
                "deposit":           int(self.kiwoom.GetCommData("opw00001", "예수금상세현황조회", 0, "예수금").strip() or 0),
                "withdrawal_possible": int(self.kiwoom.GetCommData("opw00001", "예수금상세현황조회", 0, "출금가능금액").strip() or 0),
                "order_possible":    int(self.kiwoom.GetCommData("opw00001", "예수금상세현황조회", 0, "주문가능금액").strip() or 0),
            }
            return balance

        except Exception as e:
            logger.error(f"잔고 조회 오류: {e}")
            return {}

    def get_holdings(self) -> List[Dict]:
        """보유 종목 조회"""
        if not self.is_connected:
            return []

        try:
            # OPW00018: 계좌평가잔고내역
            self.kiwoom.SetInputValue("계좌번호", self.account_number)
            self.kiwoom.SetInputValue("비밀번호", "")
            self.kiwoom.SetInputValue("비밀번호입력매체구분", "00")
            self.kiwoom.SetInputValue("조회구분", "1")
            self.kiwoom.CommRqData("계좌평가잔고내역조회", "opw00018", 0, "0101")

            holdings = []
            rows = self.kiwoom.GetRepeatCnt("opw00018", "계좌평가잔고내역조회")
            for i in range(rows):
                code     = self.kiwoom.GetCommData("opw00018", "계좌평가잔고내역조회", i, "종목번호").strip().replace('A', '')
                name     = self.kiwoom.GetCommData("opw00018", "계좌평가잔고내역조회", i, "종목명").strip()
                qty      = int(self.kiwoom.GetCommData("opw00018", "계좌평가잔고내역조회", i, "보유수량").strip() or 0)
                avg_price = int(self.kiwoom.GetCommData("opw00018", "계좌평가잔고내역조회", i, "매입단가").strip() or 0)
                cur_price = int(self.kiwoom.GetCommData("opw00018", "계좌평가잔고내역조회", i, "현재가").strip() or 0)
                pnl_pct   = float(self.kiwoom.GetCommData("opw00018", "계좌평가잔고내역조회", i, "수익률(%)").strip() or 0)

                if code and qty > 0:
                    holdings.append({
                        "code": code, "name": name, "quantity": qty,
                        "avg_price": avg_price, "current_price": cur_price,
                        "pnl_pct": pnl_pct,
                        "pnl_amount": (cur_price - avg_price) * qty
                    })
            return holdings

        except Exception as e:
            logger.error(f"보유종목 조회 오류: {e}")
            return []

    # ──────────────────────────────────────────────
    # 시세 데이터 조회
    # ──────────────────────────────────────────────
    def get_daily_ohlcv(self, code: str, start_date: str, count: int = 60) -> List[Dict]:
        """
        일봉 OHLCV 데이터 조회
        code: 종목코드 (ex. "005930")
        start_date: 조회 시작일 (YYYYMMDD)
        count: 조회 봉 수
        """
        if not self.is_connected:
            return []

        try:
            self.kiwoom.SetInputValue("종목코드", code)
            self.kiwoom.SetInputValue("기준일자", start_date)
            self.kiwoom.SetInputValue("수정주가구분", "1")
            self.kiwoom.CommRqData("주식일봉차트조회", "opt10081", 0, "0101")

            ohlcv_list = []
            rows = min(self.kiwoom.GetRepeatCnt("opt10081", "주식일봉차트조회"), count)
            for i in range(rows):
                date  = self.kiwoom.GetCommData("opt10081", "주식일봉차트조회", i, "일자").strip()
                open_ = abs(int(self.kiwoom.GetCommData("opt10081", "주식일봉차트조회", i, "시가").strip() or 0))
                high  = abs(int(self.kiwoom.GetCommData("opt10081", "주식일봉차트조회", i, "고가").strip() or 0))
                low   = abs(int(self.kiwoom.GetCommData("opt10081", "주식일봉차트조회", i, "저가").strip() or 0))
                close = abs(int(self.kiwoom.GetCommData("opt10081", "주식일봉차트조회", i, "현재가").strip() or 0))
                vol   = abs(int(self.kiwoom.GetCommData("opt10081", "주식일봉차트조회", i, "거래량").strip() or 0))

                ohlcv_list.append({
                    "date": date, "open": open_, "high": high,
                    "low": low, "close": close, "volume": vol
                })

            return sorted(ohlcv_list, key=lambda x: x["date"])

        except Exception as e:
            logger.error(f"일봉 조회 오류 ({code}): {e}")
            return []

    def get_current_price(self, code: str) -> Dict:
        """현재가 조회 (opt10001)"""
        if not self.is_connected:
            return {}

        try:
            self.kiwoom.SetInputValue("종목코드", code)
            self.kiwoom.CommRqData("주식기본정보", "opt10001", 0, "0101")

            price = abs(int(self.kiwoom.GetCommData("opt10001", "주식기본정보", 0, "현재가").strip() or 0))
            name  = self.kiwoom.GetCommData("opt10001", "주식기본정보", 0, "종목명").strip()
            chg   = float(self.kiwoom.GetCommData("opt10001", "주식기본정보", 0, "등락률").strip() or 0)

            return {"code": code, "name": name, "price": price, "change_pct": chg}

        except Exception as e:
            logger.error(f"현재가 조회 오류 ({code}): {e}")
            return {}

    # ──────────────────────────────────────────────
    # 주문 처리
    # ──────────────────────────────────────────────
    def send_order(self, order_type: str, code: str,
                   quantity: int, price: int = 0,
                   order_method: str = "market") -> Dict:
        """
        주문 전송
        order_type: "buy" | "sell"
        order_method: "market" (시장가) | "limit" (지정가)
        """
        if not self.is_connected:
            return {"success": False, "message": "API 미연결"}

        try:
            # 주문 유형 코드
            type_code = {
                ("buy",  "market"): 1,  # 신규매수
                ("buy",  "limit"):  1,  # 신규매수 (지정가)
                ("sell", "market"): 2,  # 신규매도
                ("sell", "limit"):  2,  # 신규매도 (지정가)
            }.get((order_type, order_method), 1)

            # 호가 유형
            hoga_code = "03" if order_method == "market" else "00"
            order_price = 0 if order_method == "market" else price

            result = self.kiwoom.SendOrder(
                "자동매매주문",          # 주문명
                "0101",                  # 화면번호
                self.account_number,     # 계좌번호
                type_code,               # 주문유형
                code,                    # 종목코드
                quantity,                # 수량
                order_price,             # 가격 (시장가=0)
                hoga_code,               # 거래구분
                ""                       # 원주문번호
            )

            if result == 0:
                logger.info(f"✅ 주문 성공 | {order_type.upper()} {code} {quantity}주 {order_method}")
                return {
                    "success": True,
                    "order_type": order_type,
                    "code": code,
                    "quantity": quantity,
                    "price": order_price,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                logger.error(f"❌ 주문 실패 | 오류코드: {result}")
                return {"success": False, "message": f"주문 오류 코드: {result}"}

        except Exception as e:
            logger.error(f"주문 오류: {e}")
            return {"success": False, "message": str(e)}
