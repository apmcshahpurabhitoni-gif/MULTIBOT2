import pandas as pd, numpy as np
from strategies.adaptive_trend import AdaptiveTrendMomentum

def frame(n=120):
    idx=pd.date_range("2025-01-01",periods=n,freq="D",tz="Asia/Kolkata"); close=pd.Series(np.linspace(100,220,n),index=idx); return pd.DataFrame({"open":close-.5,"high":close+1,"low":close-1,"close":close},index=idx)
def test_adaptive_trend_contract():
    s=AdaptiveTrendMomentum(); x=s.generate_signal("BTC-USD",frame(),now=frame().index[-1]); assert x.strategy==s.manifest.name and x.timeframe=="1D"
def test_adaptive_trend_has_versioned_manifest_and_trailing():
    s=AdaptiveTrendMomentum(); assert s.manifest.version and s.trailing_policy()["enabled"] is True
