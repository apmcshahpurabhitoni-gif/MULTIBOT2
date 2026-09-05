from strategies.base import Signal, Strategy, StrategyManifest
class MyStrategy(Strategy):
    manifest = StrategyManifest("my_strategy","My Strategy","1.0.0","Describe it.",(),(),"custom",{})
    def generate_signal(self, symbol, candles, *, now):
        return Signal(self.manifest.name,self.manifest.version,symbol,"NO_SIGNAL",now,"1D","IMPLEMENT_ME")
def create_strategy(): return MyStrategy()
