# ============================================================
# strategy.py - 매매 전략 엔진
# 이동평균 크로스오버 + RSI + 거래량 필터
# ============================================================

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Signal(Enum):
    BUY    = "BUY"
    SELL   = "SELL"
    HOLD   = "HOLD"
    STRONG_BUY  = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"


@dataclass
class TradeSignal:
    code:        str
    name:        str
    signal:      Signal
    price:       float
    reason:      str
    confidence:  float          # 0.0 ~ 1.0
    timestamp:   str


class TechnicalIndicators:
    """기술적 지표 계산 클래스"""

    @staticmethod
    def sma(prices: pd.Series, period: int) -> pd.Series:
        """단순 이동평균 (SMA)"""
        return prices.rolling(window=period).mean()

    @staticmethod
    def ema(prices: pd.Series, period: int) -> pd.Series:
        """지수 이동평균 (EMA)"""
        return prices.ewm(span=period, adjust=False).mean()

    @staticmethod
    def rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """RSI (Relative Strength Index)"""
        delta  = prices.diff()
        gain   = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss   = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs     = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def macd(prices: pd.Series,
             fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD (Moving Average Convergence Divergence)"""
        ema_fast   = prices.ewm(span=fast,   adjust=False).mean()
        ema_slow   = prices.ewm(span=slow,   adjust=False).mean()
        macd_line  = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram  = macd_line - signal_line
        return macd_line, signal_line, histogram

    @staticmethod
    def bollinger_bands(prices: pd.Series,
                        period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """볼린저 밴드"""
        mid  = prices.rolling(window=period).mean()
        std  = prices.rolling(window=period).std()
        upper = mid + (std * std_dev)
        lower = mid - (std * std_dev)
        return upper, mid, lower

    @staticmethod
    def volume_ratio(volumes: pd.Series, period: int = 20) -> pd.Series:
        """거래량 비율 (현재 / 평균)"""
        avg_vol = volumes.rolling(window=period).mean()
        return volumes / avg_vol


class MACrossoverStrategy:
    """
    이동평균 크로스오버 전략
    - 골든크로스: 단기MA가 장기MA를 상향 돌파 → 매수 신호
    - 데드크로스: 단기MA가 장기MA를 하향 돌파 → 매도 신호
    - RSI 필터: 과매수/과매도 보정
    - 거래량 확인: 신호 신뢰도 향상
    """

    def __init__(self,
                 short_period: int = 5,
                 long_period:  int = 20,
                 rsi_period:   int = 14,
                 rsi_oversold:   float = 30,
                 rsi_overbought: float = 70,
                 volume_threshold: float = 1.5):

        self.short_period       = short_period
        self.long_period        = long_period
        self.rsi_period         = rsi_period
        self.rsi_oversold       = rsi_oversold
        self.rsi_overbought     = rsi_overbought
        self.volume_threshold   = volume_threshold
        self.ti = TechnicalIndicators()

    def analyze(self, code: str, name: str, ohlcv_data: List[Dict]) -> Optional[TradeSignal]:
        """
        종목 분석 → 매매 신호 반환
        ohlcv_data: [{"date": "20240101", "open": ..., "high": ..., "low": ..., "close": ..., "volume": ...}, ...]
        """
        if len(ohlcv_data) < self.long_period + 5:
            logger.debug(f"{name}({code}): 데이터 부족 ({len(ohlcv_data)}개)")
            return None

        df = pd.DataFrame(ohlcv_data)
        df['close']  = pd.to_numeric(df['close'],  errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        df = df.dropna()

        close   = df['close']
        volume  = df['volume']

        # 지표 계산
        short_ma  = self.ti.sma(close, self.short_period)
        long_ma   = self.ti.sma(close, self.long_period)
        rsi_vals  = self.ti.rsi(close, self.rsi_period)
        vol_ratio = self.ti.volume_ratio(volume)
        macd_line, signal_line, histogram = self.ti.macd(close)
        bb_upper, bb_mid, bb_lower = self.ti.bollinger_bands(close)

        # 최근 값
        curr_price   = close.iloc[-1]
        curr_short   = short_ma.iloc[-1]
        curr_long    = long_ma.iloc[-1]
        prev_short   = short_ma.iloc[-2]
        prev_long    = long_ma.iloc[-2]
        curr_rsi     = rsi_vals.iloc[-1]
        curr_vol_r   = vol_ratio.iloc[-1]
        curr_macd    = macd_line.iloc[-1]
        curr_signal  = signal_line.iloc[-1]
        curr_bb_lower = bb_lower.iloc[-1]
        curr_bb_upper = bb_upper.iloc[-1]

        now_str = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        reasons = []
        buy_score = 0
        sell_score = 0

        # ── 골든크로스 / 데드크로스 판단 ──
        golden_cross = (prev_short <= prev_long) and (curr_short > curr_long)
        dead_cross   = (prev_short >= prev_long) and (curr_short < curr_long)

        if golden_cross:
            buy_score += 3
            reasons.append(f"골든크로스(MA{self.short_period}>{self.long_period})")
        if dead_cross:
            sell_score += 3
            reasons.append(f"데드크로스(MA{self.short_period}<{self.long_period})")

        # MA 정렬
        if curr_short > curr_long:
            buy_score += 1
        else:
            sell_score += 1

        # ── RSI 필터 ──
        if curr_rsi < self.rsi_oversold:
            buy_score += 2
            reasons.append(f"RSI 과매도({curr_rsi:.1f})")
        elif curr_rsi > self.rsi_overbought:
            sell_score += 2
            reasons.append(f"RSI 과매수({curr_rsi:.1f})")

        # ── MACD 신호 ──
        if curr_macd > curr_signal and histogram.iloc[-1] > histogram.iloc[-2]:
            buy_score += 1
            reasons.append("MACD 상승")
        elif curr_macd < curr_signal and histogram.iloc[-1] < histogram.iloc[-2]:
            sell_score += 1
            reasons.append("MACD 하락")

        # ── 볼린저밴드 ──
        if curr_price <= curr_bb_lower * 1.01:
            buy_score += 1
            reasons.append("볼린저 하단 터치")
        elif curr_price >= curr_bb_upper * 0.99:
            sell_score += 1
            reasons.append("볼린저 상단 터치")

        # ── 거래량 확인 ──
        high_volume = curr_vol_r >= self.volume_threshold
        if high_volume:
            reasons.append(f"거래량 급증({curr_vol_r:.1f}x)")

        # ── 신호 결정 ──
        max_score = 7
        confidence = max(buy_score, sell_score) / max_score

        if buy_score >= 4 and (golden_cross or high_volume):
            signal = Signal.STRONG_BUY if buy_score >= 5 else Signal.BUY
        elif sell_score >= 4 and (dead_cross or high_volume):
            signal = Signal.STRONG_SELL if sell_score >= 5 else Signal.SELL
        elif buy_score > sell_score and buy_score >= 3:
            signal = Signal.BUY
        elif sell_score > buy_score and sell_score >= 3:
            signal = Signal.SELL
        else:
            signal = Signal.HOLD

        reason_str = " | ".join(reasons) if reasons else "신호 없음"
        logger.info(f"[{code}] {name} | 신호: {signal.value} | 점수: 매수{buy_score}/매도{sell_score} | {reason_str}")

        return TradeSignal(
            code=code, name=name, signal=signal,
            price=curr_price, reason=reason_str,
            confidence=round(confidence, 2), timestamp=now_str
        )

    def generate_signals(self, stock_data: Dict[str, Dict]) -> List[TradeSignal]:
        """
        여러 종목 동시 분석
        stock_data: {"005930": {"name": "삼성전자", "ohlcv": [...]}, ...}
        """
        signals = []
        for code, data in stock_data.items():
            signal = self.analyze(code, data.get("name", code), data.get("ohlcv", []))
            if signal and signal.signal != Signal.HOLD:
                signals.append(signal)

        # 신뢰도 내림차순 정렬
        signals.sort(key=lambda x: x.confidence, reverse=True)
        return signals


class BacktestEngine:
    """
    백테스트 엔진 - 전략 검증용
    """

    def __init__(self, strategy: MACrossoverStrategy,
                 initial_capital: float = 1_000_000,
                 commission_rate: float = 0.00015,   # 키움 0.015%
                 slippage: float = 0.001):

        self.strategy        = strategy
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage        = slippage

    def run(self, ohlcv_data: List[Dict], code: str = "TEST", name: str = "테스트종목") -> Dict:
        """
        단일 종목 백테스트 실행
        Returns: 성과 지표 딕셔너리
        """
        if len(ohlcv_data) < self.strategy.long_period + 10:
            return {"error": "데이터 부족"}

        df = pd.DataFrame(ohlcv_data)
        df['close']  = pd.to_numeric(df['close'],  errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')

        close   = df['close']
        short_ma = TechnicalIndicators.sma(close, self.strategy.short_period)
        long_ma  = TechnicalIndicators.sma(close, self.strategy.long_period)
        rsi_vals = TechnicalIndicators.rsi(close, self.strategy.rsi_period)

        capital  = self.initial_capital
        position = 0          # 보유 주식 수
        buy_price = 0
        trades   = []
        equity_curve = [capital]

        for i in range(self.strategy.long_period + 1, len(df)):
            price      = close.iloc[i]
            prev_short = short_ma.iloc[i - 1]
            prev_long  = long_ma.iloc[i - 1]
            curr_short = short_ma.iloc[i]
            curr_long  = long_ma.iloc[i]
            curr_rsi   = rsi_vals.iloc[i]

            # 골든크로스 + RSI 미과매수 → 매수
            if (prev_short <= prev_long and curr_short > curr_long
                    and curr_rsi < self.strategy.rsi_overbought
                    and position == 0 and capital > 0):

                exec_price = price * (1 + self.slippage)
                qty = int(capital * 0.95 / exec_price)
                if qty > 0:
                    cost = qty * exec_price * (1 + self.commission_rate)
                    capital -= cost
                    position = qty
                    buy_price = exec_price
                    trades.append({
                        "type": "BUY", "date": df.iloc[i]["date"],
                        "price": exec_price, "qty": qty, "capital": capital
                    })

            # 데드크로스 또는 손절/익절 → 매도
            elif position > 0:
                dead_cross = (prev_short >= prev_long and curr_short < curr_long)
                stop_loss  = price <= buy_price * (1 - 0.01)
                take_profit = price >= buy_price * (1 + 0.03)

                if dead_cross or stop_loss or take_profit:
                    exec_price = price * (1 - self.slippage)
                    revenue    = position * exec_price * (1 - self.commission_rate)
                    capital   += revenue
                    pnl        = revenue - (position * buy_price * (1 + self.commission_rate))
                    reason     = "데드크로스" if dead_cross else ("손절" if stop_loss else "익절")

                    trades.append({
                        "type": "SELL", "date": df.iloc[i]["date"],
                        "price": exec_price, "qty": position,
                        "capital": capital, "pnl": pnl, "reason": reason
                    })
                    position  = 0
                    buy_price = 0

            # 자산 곡선
            portfolio_value = capital + position * price
            equity_curve.append(portfolio_value)

        # 미청산 포지션 처리
        if position > 0:
            final_price = close.iloc[-1]
            capital += position * final_price

        # 성과 계산
        total_return     = (capital - self.initial_capital) / self.initial_capital * 100
        buy_trades  = [t for t in trades if t["type"] == "BUY"]
        sell_trades = [t for t in trades if t["type"] == "SELL"]
        winning     = [t for t in sell_trades if t.get("pnl", 0) > 0]
        losing      = [t for t in sell_trades if t.get("pnl", 0) <= 0]
        win_rate    = len(winning) / len(sell_trades) * 100 if sell_trades else 0

        # MDD 계산
        eq = np.array(equity_curve)
        peak = np.maximum.accumulate(eq)
        drawdown = (eq - peak) / peak * 100
        mdd = drawdown.min()

        return {
            "code": code, "name": name,
            "initial_capital": self.initial_capital,
            "final_capital": round(capital, 0),
            "total_return_pct": round(total_return, 2),
            "total_trades": len(buy_trades),
            "win_rate_pct": round(win_rate, 1),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "max_drawdown_pct": round(mdd, 2),
            "trades": trades,
            "equity_curve": equity_curve
        }
