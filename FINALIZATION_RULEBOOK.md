# MULTIBOT2 Finalization Rulebook

This is the mandatory release contract. A green test suite alone never means finished.

## Source of truth
- `multi-strategy-telegram-bot` is the original behavior reference.
- `MULTIBOT2` locked specifications override obsolete behavior only where explicitly locked.
- Conflicts must be traced to source; never guessed.

## Locked rules
- Paper trading only.
- Account limits: `macro=20`, `nifty=5`, `ny_session=3`, `sweep_4h=3`.
- TrendPulse risk: INR 2,000 per trade.
- TrendPulse SL: 1.5 ATR; TP: 3 ATR.
- Completed candles only.
- Freshness: exactly 1 hour; older than 1 hour is stale.
- Duplicate identity: strategy + symbol + direction + candle timestamp.
- Maximum two sends: initial + one reminder; never a third.
- Sweep V2: strict two-sided sweep followed by final-close classification.
- Sweep uses market entry, sweep extreme SL, and 1:2 target.

## Candle invariants
- All timestamps are timezone-aware IST.
- Canonical NSE 1H candles come from actual 1-minute session data.
- Valid NSE hourly closes are 10:15, 11:15, 12:15, 13:15, 14:15, 15:15.
- Never fabricate a 15:15→16:15 NSE candle.
- Incomplete candles never reach strategy evaluation.
- Higher-timeframe candles must also be confirmed.
- The latest completed candle is evaluated; it is not discarded because an obsolete architecture expected a forming final row.

## Runtime pipeline
`provider -> validation -> canonical candles -> strategy -> completion -> freshness -> duplicate gate -> account/risk -> persistence -> Telegram/dashboard`

No strategy may bypass the pipeline. Compatibility APIs may not silently turn valid signals into `NO_SIGNAL`. Scanning must not consume duplicate allowance until acceptance/send.

## Persistence
Balances, daily counters, active trades, closed history, pending sweeps, and signal send counts survive restart. There is one authoritative state implementation. State transitions are idempotent.

## Telegram
BUY uses green direction icon; SELL uses red. Freshness icon is independent: `✅` fresh and `⚠️` stale. User-facing names do not leak provider tickers when mappings exist. Required signal fields include timeframe, candle close, age, action and risk. Stale signals never open trades. Reminder is one hour after initial send and cannot produce a third message.

## Dashboard/API
Dashboard is presentation over authoritative state. Rounding never changes execution. Health reflects actual runtime. Backtest endpoints use current APIs only.

## Final acceptance gates
Inspect every source file and test. Search for TODO/FIXME/pass placeholders, obsolete API arguments, duplicate implementations, old limits, old freshness, old candle assumptions, dead APIs and undocumented claims. Run full tests, import/syntax checks and CI. Perform clean-start and restart/persistence smoke tests. Any failed gate means NOT FINISHED.
