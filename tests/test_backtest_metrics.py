import pandas as pd, numpy as np
from backtest import backtest_strategy
from strategies.adaptive_trend import AdaptiveTrendMomentum

def test_backtest_exposes_all_required_metrics():
    idx=pd.date_range("2024-01-01",periods=160,freq="D",tz="Asia/Kolkata"); c=pd.Series(np.linspace(100,300,160),index=idx); f=pd.DataFrame({"open":c-.5,"high":c+2,"low":c-2,"close":c},index=idx)
    r=backtest_strategy(AdaptiveTrendMomentum(),"BTC-USD",f,account="macro"); m=r.metrics
    for name in ("return_pct","max_drawdown_pct","sharpe","sortino","win_rate_pct","profit_factor","number_of_trades","average_trade","max_losing_streak","exposure_pct","risk_adjusted_performance","rating","rating_label","breakdown"): assert hasattr(m,name)
    assert 0 <= m.rating <= 100
