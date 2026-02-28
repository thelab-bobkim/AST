#!/usr/bin/env python3
# ============================================================
# generate_diagram.py - 시스템 아키텍처 다이어그램 생성
# ============================================================

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe

fig, ax = plt.subplots(1, 1, figsize=(18, 12))
ax.set_xlim(0, 18)
ax.set_ylim(0, 12)
ax.axis('off')
fig.patch.set_facecolor('#0d1117')
ax.set_facecolor('#0d1117')

def draw_box(ax, x, y, w, h, color, text_lines, font_sizes=None, alpha=0.9, corner=0.3):
    box = FancyBboxPatch((x, y), w, h,
        boxstyle=f"round,pad=0.05,rounding_size={corner}",
        facecolor=color, edgecolor='white', linewidth=1.5, alpha=alpha, zorder=3)
    ax.add_patch(box)
    if font_sizes is None:
        font_sizes = [10] * len(text_lines)
    total = sum(font_sizes)
    step = h / (len(text_lines) + 1)
    for i, (line, fs) in enumerate(zip(text_lines, font_sizes)):
        ax.text(x + w/2, y + h - step*(i+1), line,
            ha='center', va='center', fontsize=fs,
            color='white', fontweight='bold' if i==0 else 'normal',
            zorder=4)

def draw_arrow(ax, x1, y1, x2, y2, color='#aaaaaa', lw=2, style='->'):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(arrowstyle=style, color=color, lw=lw), zorder=5)

# ── 타이틀 ──
ax.text(9, 11.5, '🚀 키움증권 자동매매 시스템 아키텍처', ha='center', va='center',
    fontsize=18, color='white', fontweight='bold')
ax.text(9, 11.0, '초기자본 100만원 | MA 크로스오버 전략 | Amazon Lightsail 서버',
    ha='center', va='center', fontsize=12, color='#aaaaaa')

# ══════════════════════════════════════════════
# 왼쪽: 클라이언트 (Windows PC)
# ══════════════════════════════════════════════
# 큰 클라이언트 박스
client_bg = FancyBboxPatch((0.3, 0.5), 6.5, 9.8,
    boxstyle="round,pad=0.1", facecolor='#1a2744', edgecolor='#4488ff',
    linewidth=2, alpha=0.6, zorder=1)
ax.add_patch(client_bg)
ax.text(3.55, 10.1, '🖥️  클라이언트 (Windows PC)', ha='center', fontsize=12,
    color='#4488ff', fontweight='bold')

# Kiwoom API
draw_box(ax, 0.6, 8.2, 6.0, 1.4, '#1e3a5f',
    ['키움 OpenAPI+', 'pykiwoom 연동 | COM 인터페이스', '모의투자 / 실전투자 자동 전환'],
    [11, 9, 9])

# Strategy
draw_box(ax, 0.6, 6.3, 2.8, 1.5, '#1e4d2b',
    ['📊 전략 엔진', 'MA(5/20) 크로스오버', 'RSI + MACD', '볼린저밴드 필터'],
    [10, 9, 9, 9])

# Risk Manager
draw_box(ax, 3.8, 6.3, 2.8, 1.5, '#4d1e1e',
    ['🛡️ 리스크 관리', '종목당 최대 20%', '손절 1% / 익절 3%', '일일 손실 한도 3%'],
    [10, 9, 9, 9])

# Trader (Orchestrator)
draw_box(ax, 0.6, 4.5, 6.0, 1.4, '#2d1e4d',
    ['🤖 트레이딩 엔진 (trader.py)', '시그널 스캔 30분 | 포지션 모니터 5분', '장 전/중/후 루틴 자동화'],
    [11, 9, 9])

# Scheduler
draw_box(ax, 0.6, 2.8, 2.8, 1.3, '#2d2d2d',
    ['⏰ 스케줄러', '08:50 장전 준비', '09:00 매매시작', '15:30 장마감'],
    [10, 8, 8, 8])

# Telegram
draw_box(ax, 3.8, 2.8, 2.8, 1.3, '#1a3a4d',
    ['📱 텔레그램 알림', '매수/매도 신호 알림', '일일 손익 리포트', '손절/익절 즉시 알림'],
    [10, 8, 8, 8])

# Backtest
draw_box(ax, 0.6, 0.9, 6.0, 1.5, '#2a2a1a',
    ['🔬 백테스트 엔진 (backtest_runner.py)', '과거 데이터 검증 | 손익비 계산 | MDD 분석'],
    [11, 9])

# ══════════════════════════════════════════════
# 중간: 통신
# ══════════════════════════════════════════════
draw_box(ax, 7.2, 4.8, 3.5, 1.2, '#333300',
    ['🌐 REST API 통신', 'HTTP POST /api/trading/sync', 'API Key 인증'],
    [10, 9, 9])

draw_arrow(ax, 6.6, 5.2, 7.2, 5.2, '#ffaa00', lw=2)
draw_arrow(ax, 10.7, 5.2, 11.2, 5.2, '#ffaa00', lw=2)

# ══════════════════════════════════════════════
# 오른쪽: 서버 (Lightsail)
# ══════════════════════════════════════════════
# 큰 서버 박스
server_bg = FancyBboxPatch((11.2, 0.5), 6.5, 9.8,
    boxstyle="round,pad=0.1", facecolor='#1a3a1a', edgecolor='#44ff88',
    linewidth=2, alpha=0.6, zorder=1)
ax.add_patch(server_bg)
ax.text(14.45, 10.1, '☁️  서버 (Amazon Lightsail)', ha='center', fontsize=12,
    color='#44ff88', fontweight='bold')
ax.text(14.45, 9.7, 'IP: 43.203.181.195', ha='center', fontsize=10, color='#888888')

# FastAPI
draw_box(ax, 11.5, 8.2, 5.8, 1.4, '#1e4d2b',
    ['⚡ FastAPI 백엔드 (port:8000)', '/api/trading/sync  |  /api/trading/latest', '/api/trading/trades  |  /api/trading/snapshots'],
    [11, 9, 9])

# PostgreSQL
draw_box(ax, 11.5, 6.3, 2.6, 1.5, '#1e3a5f',
    ['🗄️ PostgreSQL (5432)', 'trading_snapshots', 'trade_records', '인덱스 최적화'],
    [10, 9, 9, 9])

# Streamlit Dashboard
draw_box(ax, 14.4, 6.3, 2.9, 1.5, '#4d2d1e',
    ['📈 대시보드 (8501)', '자산 추이 차트', '보유종목 현황', '거래 내역/성과'],
    [10, 9, 9, 9])

# Nginx
draw_box(ax, 11.5, 4.5, 5.8, 1.4, '#2d2d2d',
    ['🔀 Nginx 리버스 프록시 (port:80/443)', 'API → :8000  |  Dashboard → :8501', 'HTTPS 암호화 (선택)'],
    [11, 9, 9])

# Docker Compose
draw_box(ax, 11.5, 2.8, 5.8, 1.3, '#1e1e4d',
    ['🐳 Docker Compose', 'postgres + api + dashboard + nginx', '자동 재시작 (restart: unless-stopped)'],
    [11, 9, 9])

# 브라우저
draw_box(ax, 11.5, 0.9, 5.8, 1.5, '#2a1a2a',
    ['🌐 웹 브라우저 접속', 'http://43.203.181.195', '대시보드 실시간 모니터링'],
    [11, 9, 9])

# ══════════════════════════════════════════════
# 내부 화살표들
# ══════════════════════════════════════════════
# 클라이언트 내부
draw_arrow(ax, 3.6, 8.2, 3.6, 7.8, '#4488ff')
draw_arrow(ax, 2.0, 6.3, 2.0, 5.9, '#44ff88')
draw_arrow(ax, 5.2, 6.3, 5.2, 5.9, '#ff4444')
draw_arrow(ax, 3.6, 4.5, 3.6, 4.1, '#ffaa00')
draw_arrow(ax, 2.0, 2.8, 2.0, 2.4, '#aaaaaa')
draw_arrow(ax, 5.2, 2.8, 5.2, 2.4, '#00aaff')

# 서버 내부
draw_arrow(ax, 14.45, 8.2, 14.45, 7.8, '#44ff88')
draw_arrow(ax, 13.0, 6.3, 13.0, 5.9, '#4488ff')
draw_arrow(ax, 15.9, 6.3, 15.9, 5.9, '#ff8844')
draw_arrow(ax, 14.45, 4.5, 14.45, 4.1, '#ffaa00')
draw_arrow(ax, 14.45, 2.8, 14.45, 2.4, '#44ff88')

# ══════════════════════════════════════════════
# 범례
# ══════════════════════════════════════════════
legend_items = [
    (mpatches.Patch(color='#1e3a5f'), '키움 API / DB'),
    (mpatches.Patch(color='#1e4d2b'), '전략 / 백엔드'),
    (mpatches.Patch(color='#4d1e1e'), '리스크관리'),
    (mpatches.Patch(color='#2d1e4d'), '오케스트레이터'),
    (mpatches.Patch(color='#1a3a4d'), '알림 / 모니터링'),
]
handles = [h for h, _ in legend_items]
labels  = [l for _, l in legend_items]
ax.legend(handles, labels, loc='lower center', bbox_to_anchor=(0.5, -0.02),
    ncol=5, framealpha=0.3, labelcolor='white', fontsize=9)

plt.tight_layout()
plt.savefig('/home/user/kiwoom_trading/docs/architecture.png',
    dpi=150, bbox_inches='tight', facecolor='#0d1117')
print("✅ 다이어그램 저장: architecture.png")
