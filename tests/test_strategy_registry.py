from strategies import discover_strategies

def test_builtin_strategies_are_discovered():
    r=discover_strategies(); assert set(r.ids())=={"adaptive_trend","sweep_v2"}

def test_adaptive_trend_only_supports_global_assets():
    r=discover_strategies(); s=r.get("adaptive_trend"); assert set(s.manifest.assets)=={"BTC-USD","GC=F"}
