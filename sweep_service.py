"""Compatibility facade for Sweep V2 using the generic strategy service."""
from strategy_service import StrategyService, DispatchResult
from strategies.sweep_v2 import SweepV2Strategy
from strategies import StrategyRegistry
class SweepService:
    DEFAULT_ACCOUNT="sweep_4h"
    def __init__(self, *, runtime=None, telegram_config=None, database=None, accounts=None):
        registry=StrategyRegistry(); registry.register(SweepV2Strategy())
        provider=getattr(runtime,"provider",None)
        self.service=StrategyService(registry=registry,provider=provider,database=database,accounts=accounts,telegram_config=telegram_config)
    def scan_universe_and_dispatch(self, *, now=None, period="30d", send=True): return self.service.scan_and_dispatch("sweep_v2",now=now,period=period,send=send)
    def scan_symbol(self,symbol,*,period="30d",now=None): return self.service.scan_symbol("sweep_v2",symbol,period=period,now=now)
    def dispatch(self,asset,signal,candles_1h,*,current_price,now=None,send=True,account_name=DEFAULT_ACCOUNT): return self.service.dispatch("sweep_v2",asset.symbol if hasattr(asset,"symbol") else asset,signal,current_price=current_price,now=now,send=send)
    def start(self,*_,**__): return None
    def stop(self): return None
