# ============================================================
# config.py - 설정 파일
# 키움증권 자동매매 시스템 v1.0
# ============================================================

import os
from dataclasses import dataclass, field
from typing import List

# ──────────────────────────────────────────────
# 키움 API 설정
# ──────────────────────────────────────────────
KIWOOM_USER_ID     = os.getenv("KIWOOM_USER_ID", "YOUR_ID")
KIWOOM_PASSWORD    = os.getenv("KIWOOM_PASSWORD", "YOUR_PW")
KIWOOM_CERT_PASSWORD = os.getenv("KIWOOM_CERT_PW", "YOUR_CERT_PW")
ACCOUNT_NUMBER     = os.getenv("KIWOOM_ACCOUNT", "YOUR_ACCOUNT_NO")  # ex) 1234567890

# 모의투자 여부 (True=모의, False=실전)
IS_MOCK_TRADING    = True

# ──────────────────────────────────────────────
# 서버 설정 (Lightsail)
# ──────────────────────────────────────────────
SERVER_HOST        = "43.203.181.195"
SERVER_PORT        = 8000
SERVER_API_URL     = f"http://{SERVER_HOST}:{SERVER_PORT}"
SERVER_API_KEY     = os.getenv("SERVER_API_KEY", "your-secret-api-key-here")

# ──────────────────────────────────────────────
# 투자 자본 설정 (100만원)
# ──────────────────────────────────────────────
INITIAL_CAPITAL    = 1_000_000   # 초기 자본 (원)
MAX_POSITION_RATIO = 0.20        # 종목당 최대 비중 20%
MAX_POSITION_COUNT = 5           # 최대 보유 종목 수
STOP_LOSS_RATIO    = 0.01        # 손절 비율 1%
TAKE_PROFIT_RATIO  = 0.03        # 익절 비율 3%

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
    "005930",   # 삼성전자
    "000660",   # SK하이닉스
    "035420",   # NAVER
    "005380",   # 현대차
    "051910",   # LG화학
    "006400",   # 삼성SDI
    "035720",   # 카카오
    "068270",   # 셀트리온
    "207940",   # 삼성바이오로직스
    "028260",   # 삼성물산
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
