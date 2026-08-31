# TrendPulse Freeze Record — Phase 0

## Status
CONDITIONALLY APPROVED — formula baseline frozen; remaining contract items unresolved.

The user explicitly approved the historical TrendPulse implementation evidence as the canonical baseline for reconstruction. This does not authorize guessing any behavior that the evidence does not establish.

## Frozen historical baseline
- 1H input data; 4H data derived from 1H data.
- Minimum 50 1H rows and minimum 15 4H rows.
- 4H EMA50 and ATR(14).
- ATR percentage `(ATR / Close) * 100`; historical implementation rejects below 0.2%.
- 1H EMA20, RSI(14), 1H ATR(14), MACD(12,26,9).
- Closed 1H/4H values with prior/current MACD crossover comparison.
- Bullish branch: 4H close > 4H EMA50; previous MACD <= previous signal; current MACD > current signal; 1H RSI > 50 and < 80; 1H close > 1H EMA20.
- Bearish branch: 4H close < 4H EMA50; previous MACD >= previous signal; current MACD < current signal; 1H RSI < 50 and > 20; 1H close < 1H EMA20.

## Freshness — explicitly resolved
The user explicitly rejected a special 6-hour freshness rule and approved the historical one-hour behavior evidenced by the supplied Telegram screenshot:
- `FRESH` when the referenced candle closed <= 1 hour ago.
- `STALE` when the referenced candle closed > 1 hour ago.
- No separate 6-hour threshold or special 6-hour state.
- A 6-hour-old signal is simply `STALE` because it is >1 hour old.

Regression F-006 must therefore prevent any future implementation from treating 6 hours as the freshness boundary. It is a regression label, not a business-rule authorization.

## Still unresolved — do not guess
1. Exact TrendPulse entry rule.
2. Exact TrendPulse stop-loss rule.
3. Exact TrendPulse take-profit rule.
4. Genuinely-new-signal definition.
5. Repeat/dedup behavior and new-message behavior.
6. Exact missing-data contract beyond the fail-safe requirement to never fabricate/assume missing values.
7. Final market/timeframe universe where historical evidence does not establish it.
8. Exact approved Telegram messages.
9. Exact dashboard fields not already established by the canonical SignalResult contract.
10. Exact backtest behavior where historical evidence does not establish it.

## Historical Telegram evidence
The supplied screenshot shows a TrendPulse 1H Gold SHORT message with a closed candle and an explicit footer stating `FRESH = Closed <=1h ago` and `STALE = Closed >1h ago`. It also shows an example paper trade with entry, stop and target, with the target distance equal to 2R. These are evidence for that historical instance; they do not by themselves prove the complete approved entry/SL/TP contract or sizing rules.

## Gate consequence
TrendPulse implementation remains blocked until all required strategy contract items above are frozen. No third-party or guessed TrendPulse definition may be substituted.
