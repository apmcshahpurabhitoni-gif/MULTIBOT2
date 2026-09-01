import pandas as pd
from backtest import run_signal_backtest
from strategies import StrategySignal

def frame():
    idx=pd.date_range("2026-08-31 09:15+05:30",periods=20,freq="1h");close=pd.Series(range(100,120),index=idx);return pd.DataFrame({"open":close-.5,"high":close+1,"low":close-1,"close":close},index=idx)
def test_backtest_uses_selected_account_limit_per_day():
    def evaluator(previous,current):return StrategySignal("Test","BUY",current.name,"TEST",float(current.close),1.0)
    result=run_signal_backtest(frame(),evaluator,strategy_name="Test",account="ny_session")
    # The limit is per calendar day, not a lifetime limit: 3 on each of two dates.
    assert result.trades_taken==6 and result.planned_risk==12000

def test_backtest_rejects_unknown_account():
    def evaluator(previous,current):return StrategySignal("Test","NO_SIGNAL",current.name,"TEST")
    try:run_signal_backtest(frame(),evaluator,strategy_name="Test",account="invalid")
    except ValueError as exc:assert "Unknown account" in str(exc)
    else:raise AssertionError("unknown account must fail")
