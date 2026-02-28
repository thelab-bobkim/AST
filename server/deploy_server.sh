#!/bin/bash
# ============================================================
# deploy_server.sh - Lightsail 서버 자동 배포 스크립트
# ============================================================

set -e

echo "=============================================="
echo "🚀 키움 자동매매 서버 배포 시작"
echo "   서버: 43.203.181.195 (Amazon Lightsail)"
echo "=============================================="

# 1. 시스템 업데이트
sudo apt-get update -y && sudo apt-get upgrade -y

# 2. Docker 설치
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh
    sudo usermod -aG docker $USER
fi

# 3. 프로젝트 디렉토리
PROJECT_DIR="/opt/kiwoom_trading"
sudo mkdir -p $PROJECT_DIR && sudo chown $USER:$USER $PROJECT_DIR
mkdir -p $PROJECT_DIR/logs

# 4. 환경변수 생성
if [ ! -f "$PROJECT_DIR/.env" ]; then
    RAND_KEY=$(openssl rand -hex 16)
    RAND_PASS=$(openssl rand -hex 8)
    cat > $PROJECT_DIR/.env << EOF
SERVER_API_KEY=kiwoom-secret-${RAND_KEY}
DB_HOST=postgres
DB_PORT=5432
DB_NAME=trading_db
DB_USER=trading_user
DB_PASSWORD=trading_pass_${RAND_PASS}
EOF
    echo "✅ .env 생성됨"
    echo "📋 API KEY: kiwoom-secret-${RAND_KEY}"
fi

# 5. 서버 파일 복사
cp app.py database.py dashboard.py nginx.conf init.sql \
   Dockerfile.api Dockerfile.dashboard requirements_server.txt \
   docker-compose.yml $PROJECT_DIR/

# 6. Docker 실행
cd $PROJECT_DIR
docker compose --env-file .env up -d --build

echo ""
echo "=============================================="
echo "✅ 배포 완료!"
echo "   대시보드  : http://43.203.181.195"
echo "   API 서버  : http://43.203.181.195:8000"
echo "   API 문서  : http://43.203.181.195:8000/docs"
echo "=============================================="
