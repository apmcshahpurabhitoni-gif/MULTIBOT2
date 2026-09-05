import pandas as pd, pytest
from signal_gate import SignalGate, signal_status
from strategies import Signal

def make_signal(ts="2026-08-31 10:15:00+05:30", direction="BUY"):
    return Signal("Adaptive Trend Momentum","1.0.0","BTC-USD",direction,pd.Timestamp(ts),"1D","TEST",100,98,104)

def test_freshness_boundary():
    g=SignalGate(); s=make_signal(); now=pd.Timestamp("2026-08-31 11:15:00+05:30"); assert g.is_fresh(s,now=now); assert not g.is_fresh(s,now=now+pd.Timedelta(seconds=1))
def test_future_rejected():
    with pytest.raises(ValueError): SignalGate().age_hours(make_signal("2026-08-31 12:15:00+05:30"),now=pd.Timestamp("2026-08-31 11:15:00+05:30"))
def test_two_sends_max():
    g=SignalGate(); s=make_signal(); now=pd.Timestamp("2026-08-31 11:00:00+05:30"); assert g.accept(s,symbol="BTC-USD",now=now); assert g.accept(s,symbol="BTC-USD",now=now); assert not g.accept(s,symbol="BTC-USD",now=now); assert g.repeat_count(s,symbol="BTC-USD")==2
def test_identity_changes_with_direction_and_candle():
    g=SignalGate(); a=make_signal(); b=make_signal(direction="SELL"); c=make_signal("2026-08-31 11:15:00+05:30"); assert len({g.signal_key(x,symbol="BTC-USD") for x in (a,b,c)})==3
def test_neutral_supported_but_no_signal_not_sendable():
    g=SignalGate(); assert g.can_send(make_signal(direction="NEUTRAL"),symbol="BTC-USD",now=pd.Timestamp("2026-08-31 11:00:00+05:30")); assert not g.can_send(make_signal(direction="NO_SIGNAL"),symbol="BTC-USD",now=pd.Timestamp("2026-08-31 11:00:00+05:30"))
def test_signal_status():
    s=make_signal(); assert signal_status(s,now=pd.Timestamp("2026-08-31 11:00:00+05:30"))[0]=="FRESH"
