# 🚀 AST - Automated Stock Trading System
> 키움증권 OpenAPI 기반 자동매매 시스템 | 초기자본 100만원 | Amazon Lightsail 서버

---

## 📁 프로젝트 구조

```
AST/
├── client/                  ← Windows PC에서 실행 (키움 OpenAPI)
│   ├── config.py            # 전체 설정 (계좌·전략·서버)
│   ├── kiwoom_wrapper.py    # 키움 OpenAPI 래퍼 클래스
│   ├── strategy.py          # MA크로스오버 + RSI + MACD + 볼린저밴드
│   ├── risk_manager.py      # 리스크 관리 (손절1%/익절3%/일손실3%)
│   ├── trader.py            # 메인 자동매매 엔진
│   ├── simulation.py        # 오프라인 시뮬레이션 (API 없이 테스트)
│   ├── backtest_runner.py   # 백테스트 엔진
│   └── requirements_client.txt
│
├── server/                  ← Amazon Lightsail에 배포
│   ├── app.py               # FastAPI 백엔드 (port:8000)
│   ├── database.py          # PostgreSQL ORM (SQLAlchemy)
│   ├── dashboard.py         # Streamlit 실시간 대시보드 (port:8501)
│   ├── docker-compose.yml   # 4개 컨테이너 통합 실행
│   ├── Dockerfile.api
│   ├── Dockerfile.dashboard
│   ├── nginx.conf           # 리버스 프록시 (port:80)
│   ├── init.sql             # PostgreSQL 스키마
│   └── deploy_server.sh     # 원클릭 서버 배포 스크립트
│
└── docs/
    └── architecture.png     # 시스템 아키텍처 다이어그램
```

---

## ⚡ 빠른 시작

### 1️⃣ 서버 배포 (Lightsail Ubuntu)
```bash
git clone https://github.com/thelab-bobkim/AST.git
cd AST/server
bash deploy_server.sh
```

### 2️⃣ 클라이언트 설정 (Windows PC)
```bash
git clone https://github.com/thelab-bobkim/AST.git
cd AST/client
pip install -r requirements_client.txt
# config.py에서 계좌·API키 설정 후:
python trader.py
```

### 3️⃣ 백테스트 실행
```bash
cd client
python backtest_runner.py
```

---

## 🛡️ 리스크 관리

| 규칙 | 설정값 |
|------|--------|
| 종목당 최대 비중 | 20% |
| 최대 보유 종목 | 5개 |
| 손절 | -1% |
| 익절 | +3% |
| 일일 손실 한도 | -3% |
| 최대 낙폭 한도 | -10% |

---

## 📊 서비스 접속
- **대시보드** : http://43.203.181.195
- **API 서버** : http://43.203.181.195:8000
- **API 문서** : http://43.203.181.195:8000/docs

---

## ⚠️ 주의사항
- `config.py`에 실제 계좌 정보, API 키 입력 필요
- `.env` 파일은 절대 GitHub에 올리지 마세요 (.gitignore에 포함됨)
- 반드시 **모의투자**로 먼저 검증 후 실전 전환
- 키움 OpenAPI+는 **Windows 전용** (Linux 서버에서 직접 실행 불가)

---
*Built with ❤️ by thelab-bobkim | Powered by Genspark AI*
