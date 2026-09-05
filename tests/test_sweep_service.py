from strategies import discover_strategies

def test_sweep_plugin_is_registered():
    s=discover_strategies().get("sweep_v2"); assert s.manifest.account=="sweep_4h" and s.manifest.schedule=="canonical_sweep_schedule"
