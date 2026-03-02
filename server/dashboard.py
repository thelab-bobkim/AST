# ============================================================
# server/dashboard.py - Streamlit 대시보드
# 실시간 포트폴리오·거래 현황 시각화
# ============================================================

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import time

# ──────────────────────────────────────────────
# 설정
# ──────────────────────────────────────────────
API_URL = "http://43.203.181.195:9000"
INITIAL_CAPITAL = 1_000_000
REFRESH_SEC = 30

st.set_page_config(
    page_title="키움 자동매매 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ──────────────────────────────────────────────
# CSS 스타일
# ──────────────────────────────────────────────
st.markdown("""
<style>
.metric-card {
    background: linear-gradient(135deg, #1e3a5f 0%, #2d5986 100%);
    border-radius: 12px;
    padding: 20px;
    color: white;
    text-align: center;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
}
.profit { color: #00ff88; }
.loss   { color: #ff4444; }
.neutral { color: #aaaaaa; }
.status-live  { background: #ff4444; padding: 3px 10px; border-radius: 12px; }
.status-mock  { background: #f0a500; padding: 3px 10px; border-radius: 12px; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# 데이터 로드 함수
# ──────────────────────────────────────────────
def _get_api_url():
    return st.session_state.get("api_url", API_URL)

@st.cache_data(ttl=REFRESH_SEC)
def load_latest(api_url=None):
    url = api_url or API_URL
    try:
        r = requests.get(f"{url}/api/trading/latest", timeout=5)
        return r.json() if r.status_code == 200 else {}
    except:
        return {}

@st.cache_data(ttl=REFRESH_SEC)
def load_snapshots(api_url=None):
    url = api_url or API_URL
    try:
        r = requests.get(f"{url}/api/trading/snapshots?limit=200", timeout=5)
        return r.json() if r.status_code == 200 else []
    except:
        return []

@st.cache_data(ttl=REFRESH_SEC)
def load_trades(api_url=None):
    url = api_url or API_URL
    try:
        r = requests.get(f"{url}/api/trading/trades?limit=100", timeout=5)
        return r.json() if r.status_code == 200 else []
    except:
        return []

# ──────────────────────────────────────────────
# 사이드바
# ──────────────────────────────────────────────
with st.sidebar:
    st.image("https://i.imgur.com/placeholder.png", width=80)  # 로고 자리
    st.title("⚙️ 시스템 설정")
    API_URL = st.text_input("API 서버 주소", value=st.session_state.get("api_url", API_URL), key="api_url")
    refresh = st.slider("자동 새로고침 (초)", 10, 300, REFRESH_SEC)
    st.markdown("---")
    st.markdown("### 📊 전략 정보")
    st.markdown("- **전략**: MA 크로스오버")
    st.markdown("- **단기MA**: 5일")
    st.markdown("- **장기MA**: 20일")
    st.markdown("- **RSI**: 14기간")
    st.markdown("- **손절**: 1%")
    st.markdown("- **익절**: 3%")
    st.markdown("---")
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()

# ──────────────────────────────────────────────
# 메인 콘텐츠
# ──────────────────────────────────────────────
st.title("📈 키움증권 자동매매 모니터링")
st.markdown(f"*마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

_api = st.session_state.get("api_url", API_URL)
latest = load_latest(_api)
snaps  = load_snapshots(_api)
trades = load_trades(_api)

if not latest or "message" in latest:
    st.warning("⚠️ 클라이언트에서 데이터를 수신하지 못했습니다. 자동매매 클라이언트가 실행 중인지 확인하세요.")
    st.info("클라이언트를 실행하면 자동으로 이 대시보드에 데이터가 표시됩니다.")
    st.stop()

# ── 상단 지표 카드 ──
portfolio_val = latest.get("portfolio_value", INITIAL_CAPITAL)
total_pnl     = latest.get("total_pnl", 0)
total_pnl_pct = latest.get("total_pnl_pct", 0)
daily_pnl     = latest.get("daily_pnl", 0)
cash          = latest.get("cash", INITIAL_CAPITAL)
pos_count     = latest.get("position_count", 0)
mode          = latest.get("mode", "mock")

pnl_color   = "#00ff88" if total_pnl >= 0 else "#ff4444"
daily_color = "#00ff88" if daily_pnl >= 0 else "#ff4444"

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        "💼 총 자산",
        f"₩{portfolio_val:,.0f}",
        f"{total_pnl:+,.0f}원",
        delta_color="normal"
    )
with col2:
    st.metric(
        "📊 총 수익률",
        f"{total_pnl_pct:+.2f}%",
        f"₩{total_pnl:+,.0f}",
        delta_color="normal"
    )
with col3:
    st.metric(
        "📅 일일 손익",
        f"₩{daily_pnl:+,.0f}",
        delta_color="normal"
    )
with col4:
    st.metric(
        "💰 현금",
        f"₩{cash:,.0f}",
        f"{cash/portfolio_val*100:.1f}%",
        delta_color="off"
    )
with col5:
    st.metric(
        "🏦 보유 종목",
        f"{pos_count}개",
        delta_color="off"
    )

mode_badge = "🟢 실전" if mode == "live" else "🟡 모의"
st.markdown(f"**모드**: {mode_badge} &nbsp;&nbsp; **초기자본**: ₩{INITIAL_CAPITAL:,}")
st.divider()

# ── 탭 레이아웃 ──
tab1, tab2, tab3, tab4 = st.tabs(["📈 자산 추이", "💼 보유 종목", "📋 거래 내역", "📊 성과 분석"])

# ────────────────────────────────
# TAB 1: 자산 추이 차트
# ────────────────────────────────
with tab1:
    if snaps:
        df_snap = pd.DataFrame(snaps)
        df_snap['timestamp'] = pd.to_datetime(df_snap['timestamp'])

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_snap['timestamp'], y=df_snap['portfolio_value'],
            mode='lines+markers', name='총자산',
            line=dict(color='#00aaff', width=2),
            fill='tonexty', fillcolor='rgba(0,170,255,0.1)'
        ))
        fig.add_hline(
            y=INITIAL_CAPITAL,
            line_dash="dash", line_color="gray",
            annotation_text=f"초기자본 {INITIAL_CAPITAL:,}원"
        )
        fig.update_layout(
            title="포트폴리오 가치 추이",
            xaxis_title="시간", yaxis_title="금액 (원)",
            template="plotly_dark", height=400
        )
        st.plotly_chart(fig, use_container_width=True)

        # 일일 손익 바차트
        fig2 = go.Figure()
        colors = ['#00ff88' if v >= 0 else '#ff4444' for v in df_snap['daily_pnl']]
        fig2.add_trace(go.Bar(
            x=df_snap['timestamp'], y=df_snap['daily_pnl'],
            marker_color=colors, name='일일 손익'
        ))
        fig2.update_layout(
            title="일일 손익",
            xaxis_title="날짜", yaxis_title="손익 (원)",
            template="plotly_dark", height=300
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("아직 충분한 데이터가 없습니다.")

# ────────────────────────────────
# TAB 2: 보유 종목
# ────────────────────────────────
with tab2:
    holdings = latest.get("holdings", [])
    if holdings:
        df_hold = pd.DataFrame(holdings)
        df_hold['수익률'] = df_hold['unrealized_pnl_pct'].apply(
            lambda x: f"{'🟢' if x >= 0 else '🔴'} {x:+.2f}%"
        )

        # 보유 현황 테이블
        st.dataframe(
            df_hold[['code','name','quantity','avg_price','current_price',
                      'market_value','unrealized_pnl','수익률','stop_price','target_price']].rename(columns={
                'code': '종목코드', 'name': '종목명', 'quantity': '수량',
                'avg_price': '매입단가', 'current_price': '현재가',
                'market_value': '평가금액', 'unrealized_pnl': '평가손익',
                'stop_price': '손절가', 'target_price': '익절가'
            }),
            use_container_width=True, hide_index=True
        )

        # 파이차트
        fig_pie = px.pie(
            df_hold, values='market_value', names='name',
            title='포지션 비중', template='plotly_dark'
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("현재 보유 종목이 없습니다.")

# ────────────────────────────────
# TAB 3: 거래 내역
# ────────────────────────────────
with tab3:
    if trades:
        df_trade = pd.DataFrame(trades)
        df_trade['수익손실'] = df_trade['pnl'].apply(
            lambda x: f"{'🟢 +' if x > 0 else ('🔴 ' if x < 0 else '⚪ ')}{x:,.0f}원" if x != 0 else "-"
        )
        df_trade['유형'] = df_trade['type'].apply(
            lambda x: "📈 매수" if x == "BUY" else "📉 매도"
        )

        st.dataframe(
            df_trade[['timestamp','유형','name','code','quantity','price','amount','수익손실','reason']].rename(columns={
                'timestamp': '시간', 'name': '종목명', 'code': '코드',
                'quantity': '수량', 'price': '단가', 'amount': '금액', 'reason': '사유'
            }),
            use_container_width=True, hide_index=True
        )

        # 매수/매도 횟수
        buy_cnt  = len([t for t in trades if t['type'] == 'BUY'])
        sell_cnt = len([t for t in trades if t['type'] == 'SELL'])
        col1, col2 = st.columns(2)
        col1.metric("📈 매수 건수", f"{buy_cnt}건")
        col2.metric("📉 매도 건수", f"{sell_cnt}건")
    else:
        st.info("아직 거래 내역이 없습니다.")

# ────────────────────────────────
# TAB 4: 성과 분석
# ────────────────────────────────
with tab4:
    if trades:
        sell_trades = [t for t in trades if t['type'] == 'SELL' and t['pnl'] != 0]
        if sell_trades:
            pnls     = [t['pnl'] for t in sell_trades]
            wins     = [p for p in pnls if p > 0]
            losses   = [p for p in pnls if p <= 0]
            win_rate = len(wins) / len(pnls) * 100 if pnls else 0
            avg_win  = sum(wins) / len(wins) if wins else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            pf       = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else 999

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("🎯 승률",      f"{win_rate:.1f}%")
            col2.metric("💚 평균 수익",  f"₩{avg_win:+,.0f}")
            col3.metric("❤️ 평균 손실",  f"₩{avg_loss:+,.0f}")
            col4.metric("⚖️ 손익비",    f"{pf:.2f}")

            # 손익 분포 히스토그램
            df_pnl = pd.DataFrame({"pnl": pnls})
            fig_hist = px.histogram(
                df_pnl, x="pnl", nbins=20,
                title="손익 분포",
                color_discrete_sequence=['#00aaff'],
                template='plotly_dark'
            )
            fig_hist.add_vline(x=0, line_color="white", line_dash="dash")
            st.plotly_chart(fig_hist, use_container_width=True)

            # 누적 손익 라인
            cum_pnl = pd.DataFrame({
                "거래번호": range(1, len(pnls)+1),
                "누적손익": pd.Series(pnls).cumsum()
            })
            fig_cum = px.line(
                cum_pnl, x="거래번호", y="누적손익",
                title="누적 손익 추이", template="plotly_dark"
            )
            fig_cum.add_hline(y=0, line_color="gray", line_dash="dash")
            st.plotly_chart(fig_cum, use_container_width=True)
    else:
        st.info("청산된 거래가 없어 성과 분석을 표시할 수 없습니다.")

# 자동 새로고침
st.markdown(f"<meta http-equiv='refresh' content='{refresh}'>", unsafe_allow_html=True)
