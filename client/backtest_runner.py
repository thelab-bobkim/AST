# ============================================================
# backtest_runner.py - 백테스트 실행 스크립트
# 실제 데이터 없이도 시뮬레이션 가능
# ============================================================

import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta
from strategy import MACrossoverStrategy, BacktestEngine

def generate_sample_data(days: int = 120, initial_price: float = 70000,
                          seed: int = 42) -> list:
    """
    샘플 주가 데이터 생성 (삼성전자 패턴 시뮬레이션)
    실제 백테스트 시에는 kiwoom.get_daily_ohlcv() 데이터 사용
    """
    np.random.seed(seed)
    prices = [initial_price]
    volumes = []

    for i in range(days - 1):
        # 랜덤워크 + 트렌드
        trend   = 0.0002
        returns = np.random.normal(trend, 0.015)
        prices.append(prices[-1] * (1 + returns))
        volumes.append(int(np.random.lognormal(15, 0.5)))

    volumes.append(int(np.random.lognormal(15, 0.5)))

    ohlcv = []
    base_date = datetime.now() - timedelta(days=days)
    for i, price in enumerate(prices):
        high  = price * (1 + abs(np.random.normal(0, 0.005)))
        low   = price * (1 - abs(np.random.normal(0, 0.005)))
        open_ = price * (1 + np.random.normal(0, 0.003))
        date  = (base_date + timedelta(days=i)).strftime("%Y%m%d")
        ohlcv.append({
            "date":   date,
            "open":   round(open_),
            "high":   round(high),
            "low":    round(low),
            "close":  round(price),
            "volume": volumes[i]
        })
    return ohlcv


def run_multi_stock_backtest():
    """여러 종목에 대한 백테스트 실행"""
    print("\n" + "="*60)
    print("🔬 키움 자동매매 전략 백테스트")
    print("="*60)

    strategy = MACrossoverStrategy(
        short_period=5, long_period=20,
        rsi_period=14, rsi_oversold=30, rsi_overbought=70
    )
    engine = BacktestEngine(strategy, initial_capital=1_000_000)

    stocks = {
        "005930": ("삼성전자",  70000, 42),
        "000660": ("SK하이닉스", 120000, 43),
        "035420": ("NAVER",    180000, 44),
        "005380": ("현대차",    220000, 45),
        "051910": ("LG화학",    350000, 46),
    }

    results = []
    for code, (name, price, seed) in stocks.items():
        data = generate_sample_data(days=120, initial_price=price, seed=seed)
        result = engine.run(data, code=code, name=name)
        results.append(result)

        print(f"\n[{code}] {name}")
        print(f"  수익률  : {result['total_return_pct']:+.2f}%")
        print(f"  거래횟수: {result['total_trades']}회")
        print(f"  승률    : {result['win_rate_pct']:.1f}%")
        print(f"  MDD     : {result['max_drawdown_pct']:.2f}%")
        print(f"  최종자산: ₩{result['final_capital']:,.0f}")

    # 종합 성과
    print("\n" + "="*60)
    print("📊 종합 성과 요약")
    print("="*60)
    avg_return = sum(r['total_return_pct'] for r in results) / len(results)
    avg_win_rate = sum(r['win_rate_pct'] for r in results) / len(results)
    avg_mdd = sum(r['max_drawdown_pct'] for r in results) / len(results)
    print(f"  평균 수익률  : {avg_return:+.2f}%")
    print(f"  평균 승률    : {avg_win_rate:.1f}%")
    print(f"  평균 MDD     : {avg_mdd:.2f}%")

    # JSON 저장
    with open("backtest_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print("\n✅ 결과 저장: backtest_results.json")

    return results


if __name__ == "__main__":
    run_multi_stock_backtest()
