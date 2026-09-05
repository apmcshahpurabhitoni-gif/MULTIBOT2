from strategies import discover_strategies

def test_strategy_contract_has_no_core_specific_dependencies():
    for s in discover_strategies().all():
        assert s.manifest.id and s.manifest.name and s.manifest.version and s.manifest.assets and s.manifest.timeframes
