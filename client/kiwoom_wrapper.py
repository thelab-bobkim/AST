# -*- coding: utf-8 -*-
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

from contextlib import contextmanager
import os

@contextmanager
def _suppress_print():
    """pykiwoom block_request가 TR 정의 dict를 print하는 것을 억제"""
    with open(os.devnull, 'w') as devnull:
        old = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old

def _safe_str(val) -> str:
    """CP949 인코딩 문자열을 안전하게 UTF-8로 변환"""
    if isinstance(val, bytes):
        try:
            return val.decode('cp949')
        except Exception:
            return val.decode('utf-8', errors='replace')
    s = str(val).strip()
    try:
        return s.encode('cp949').decode('cp949')
    except Exception:
        return s

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
                # pykiwoom 버전에 따라 list 또는 문자열 반환
                if isinstance(accounts, list):
                    self.account_number = accounts[0]
                else:
                    self.account_number = accounts.split(';')[0]
                logger.info(f"✅ 키움 로그인 성공 | 계좌: {self.account_number}")

                # 실전/모의 서버 확인 (GetServerGubun: "1"=모의, 그외=실전)
                server = self.kiwoom.GetLoginInfo("GetServerGubun")
                server_name = "모의투자" if server == "1" else "실전투자"
                logger.info(f"📡 서버: {server_name}")

                # is_mock 플래그를 실제 서버 정보로 동기화
                self.is_mock = (server == "1")
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
            self.kiwoom.CommRqData("예수금상세현황조회", "opw00001", 0, "0101", block=True)

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
            self.kiwoom.CommRqData("계좌평가잔고내역조회", "opw00018", 0, "0101", block=True)

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
        일봉 OHLCV 데이터 조회 (pykiwoom block_request 방식)
        """
        if not self.is_connected:
            return []

        try:
            with _suppress_print():
                df = self.kiwoom.block_request(
                    "opt10081",
                    종목코드=code,
                    기준일자=start_date,
                    수정주가구분=1,
                    output="주식일봉차트조회",
                    next=0
                )

            if df is None or len(df) == 0:
                logger.warning(f"OHLCV 데이터 없음 ({code})")
                return []

            ohlcv_list = []
            for _, row in df.iterrows():
                try:
                    ohlcv_list.append({
                        "date":   str(row.get("일자", "")).strip(),
                        "open":   abs(int(str(row.get("시가",   0)).strip() or 0)),
                        "high":   abs(int(str(row.get("고가",   0)).strip() or 0)),
                        "low":    abs(int(str(row.get("저가",   0)).strip() or 0)),
                        "close":  abs(int(str(row.get("현재가", 0)).strip() or 0)),
                        "volume": abs(int(str(row.get("거래량", 0)).strip() or 0)),
                    })
                except (ValueError, TypeError):
                    continue

            ohlcv_list = [x for x in ohlcv_list if x["close"] > 0]
            ohlcv_list = sorted(ohlcv_list, key=lambda x: x["date"])
            return ohlcv_list[-count:]

        except Exception as e:
            logger.error(f"일봉 조회 오류 ({code}): {e}")
            return []

    def get_current_price(self, code: str) -> Dict:
        """현재가 조회 (pykiwoom block_request 방식)"""
        if not self.is_connected:
            return {}

        try:
            with _suppress_print():
                df = self.kiwoom.block_request(
                    "opt10001",
                    종목코드=code,
                    output="주식기본정보",
                    next=0
                )

            if df is None or len(df) == 0:
                return {}

            row   = df.iloc[0]
            price = abs(int(str(row.get("현재가", 0)).strip() or 0))
            name  = _safe_str(row.get("종목명", code))
            chg   = float(str(row.get("등락률", 0)).strip() or 0)

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
