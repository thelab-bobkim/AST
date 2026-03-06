# -*- coding: utf-8 -*-
# ============================================================
# config.py - 설정 파일
# 키움증권 자동매매 시스템 v1.0
# ============================================================

import os
from dotenv import load_dotenv
from dataclasses import dataclass, field
from typing import List

# .env 파일 로드 (config.py와 같은 폴더)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# ──────────────────────────────────────────────
# 키움 API 설정
# ──────────────────────────────────────────────
KIWOOM_USER_ID       = os.getenv("KIWOOM_USER_ID", "YOUR_ID")
KIWOOM_PASSWORD      = os.getenv("KIWOOM_PASSWORD", "YOUR_PW")
KIWOOM_CERT_PASSWORD = os.getenv("KIWOOM_CERT_PW", "YOUR_CERT_PW")
ACCOUNT_NUMBER       = os.getenv("KIWOOM_ACCOUNT", "YOUR_ACCOUNT_NO")  # ex) 1234567890
ACCOUNT_PASSWORD     = os.getenv("KIWOOM_ACCOUNT_PASSWORD", "0000")  # 계좌 주문 비밀번호 (4~6자리)

# 모의투자 여부 (True=모의, False=실전)
IS_MOCK_TRADING      = os.getenv("IS_MOCK_TRADING", "True").lower() != "false"

# ──────────────────────────────────────────────
# 서버 설정 (AWS - 외부 포트 9000)
# ──────────────────────────────────────────────
SERVER_HOST        = os.getenv("SERVER_HOST",    "43.203.181.195")
SERVER_PORT        = 9000   # 외부 포트: 9000 (Docker: 9000->8000 내부)
SERVER_API_URL     = f"http://{SERVER_HOST}:{SERVER_PORT}"
SERVER_API_KEY     = os.getenv("SERVER_API_KEY", "kiwoom-ast-secret-efdf9d396f5d10b7f4e65834")

# ──────────────────────────────────────────────
# 투자 자본 설정 (100만원)
# ──────────────────────────────────────────────
INITIAL_CAPITAL    = 1_100_000   # 초기 자본 (원) - 110만원
MAX_POSITION_RATIO = 0.40        # 종목당 최대 비중 40% (110만원 기준 44만원/종목)
MAX_POSITION_COUNT = 3           # 최대 보유 종목 수 (40% x 3 = 최대 120%)
STOP_LOSS_RATIO    = 0.02        # 손절 비율 2%
TAKE_PROFIT_RATIO  = 0.04        # 익절 비율 4%

# ──────────────────────────────────────────────
# 전략 설정 (이동평균 크로스오버)
# ──────────────────────────────────────────────
STRATEGY_NAME      = "MA_CROSSOVER"
SHORT_MA_PERIOD    = 5           # 단기 이동평균 (5일)
LONG_MA_PERIOD     = 20          # 장기 이동평균 (20일)
RSI_PERIOD         = 14          # RSI 기간
RSI_OVERSOLD       = 30          # RSI 과매도 기준
RSI_OVERBOUGHT     = 70          # RSI 과매수 기준
VOLUME_MA_PERIOD   = 20          # 거래량 이동평균 기간

# ──────────────────────────────────────────────
# 매매 대상 종목 (코스피 우량주)
# ──────────────────────────────────────────────
WATCHLIST = [
    "005930",   # 삼성전자    (176,500원) → 40%기준 2주 가능
    "035420",   # NAVER       (213,000원) → 40%기준 1주 가능
    "035720",   # 카카오      ( 48,850원) → 40%기준 8주 가능
    "068270",   # 셀트리온    (202,000원) → 40%기준 1주 가능
    "051910",   # LG화학      (314,500원) → 40%기준 1주 가능
    "006400",   # 삼성SDI     (366,500원) → 40%기준 1주 가능
    "028260",   # 삼성물산    (274,000원) → 40%기준 1주 가능
    # 아래 종목은 100만원 자본에서는 매수 불가 (주가가 예산 초과)
    # "000660",  # SK하이닉스  (873,000원) → 불가
    # "005380",  # 현대차      (511,000원) → 불가
    # "207940",  # 삼성바이오  (1,542,000원) → 불가
]

# ──────────────────────────────────────────────
# 시장 시간 설정
# ──────────────────────────────────────────────
MARKET_OPEN_TIME   = "09:00"
MARKET_CLOSE_TIME  = "15:30"
PRE_MARKET_TIME    = "08:50"     # 장 전 준비
AFTER_MARKET_TIME  = "15:40"    # 장 후 정리

# ──────────────────────────────────────────────
# 로깅 설정
# ──────────────────────────────────────────────
LOG_LEVEL          = "INFO"
LOG_FILE           = "logs/trading.log"
LOG_MAX_BYTES      = 10 * 1024 * 1024   # 10MB
LOG_BACKUP_COUNT   = 5

# ──────────────────────────────────────────────
# 알림 설정 (선택)
# ──────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")
ENABLE_TELEGRAM    = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
