# Architecture + Contracts — Phase 0

## Canonical pipeline
Provider → Normalization → Session Candles → Strategy Engine → SignalResult → Database / Telegram / Dashboard / Backtest.

Consumers must consume canonical results. Strategies do not send Telegram or write UI/database directly. Backtest calls the same canonical strategy engines used by live analysis.

## Domain objects
- Instrument
- MarketSession
- Candle
- StrategyInput
- SignalResult
- TradePlan
- Warning
- PaperTrade
- MessageEvent
- BacktestResult

## SignalResult contract
```text
strategy: str
strategy_version: str
instrument: str
signal: BUY | SELL | NEUTRAL | NO_SIGNAL
candle_start: timezone-aware datetime
candle_close: timezone-aware datetime
confirmation_time: timezone-aware datetime
entry: Decimal | null
stop_loss: Decimal | null
take_profit: Decimal | null
reason: str
freshness: FRESH | STALE
data_source: str
warnings: list[str]
config_version: str
```

API canonical fields additionally exposed explicitly: strategy, strategy_version, instrument, signal, freshness, candle_start, candle_close, entry, stop_loss, take_profit, reason, warnings.

## Data contracts
Provider adapters stay outside strategy code. Required mapping is provider symbol → canonical symbol → display name. Timestamps are timezone-aware and use Asia/Kolkata for NSE; server-local time is forbidden. Candle identity is instrument + timeframe + session + candle_start.

Validation must cover timeframe, session, timestamp, completeness, OHLC, duplicates, gaps, stale data and boundaries. Missing/invalid required inputs produce no invented signal and create structured warnings where specified.

## Strategy boundary
```text
Strategy.evaluate(context) -> SignalResult
```
Sweep V2 is locked by current specification and may be implemented only in Phase 3. TrendPulse remains unimplemented until Phase 0 freeze resolves the authoritative definition.

## Paper trading contract
Strategy creates TradePlan; execution simulator owns fills/lifecycle. BUY entry is detection market price, BUY SL is signal candle Low, BUY TP is 2R. SELL entry is detection market price, SELL SL is signal candle High, SELL TP is 2R. NEUTRAL/NO_SIGNAL creates no trade. Account size, risk %, leverage, daily limits, fees and slippage are unresolved and must not be invented.

## Telegram contract
Telegram consumes SignalResult/PaperTrade; it never calculates signal, freshness, entry, SL, TP or candle classification. One centralized formatter. Durable reminder state prevents duplicate reminders. Exact copy must come only from the locked registry after authoritative approval is recovered.

## Dashboard contract
Dashboard displays backend truth only. It must show BUY/SELL/NEUTRAL or no-signal state, instrument, freshness, entry, SL, TP and candle close immediately. Frontend must not calculate strategy, freshness, entry, SL, TP, risk or candle classification.

## Persistence design
Recommended structured database: Supabase PostgreSQL. Planned entities: instruments, candles, signals, paper_trades, message_events, backtests, bot_runs, data_warnings. Use foreign keys, unique candle identity, idempotent signal identity and indexes. Service-role credentials are server-only.

## Configuration safety
Initial baseline: PAPER_TRADING_ENABLED=true; LIVE_BROKER_ENABLED=false. Required environment variables and server-only secret rules are recorded in the supplied environment/security specifications. `.env` must never be committed; `.env.example` contains placeholders only.
