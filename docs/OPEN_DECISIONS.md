# Open Decisions — Phase 0

No unresolved item is to be answered by invention. Each decision requires an explicit approval record before implementation depends on it.

## User-approved TrendPulse reconstruction baseline

On 2026-08-31 the user explicitly approved the historical TrendPulse evidence as the canonical reconstruction baseline, with the condition that unresolved conflicts must be resolved before implementation.

Approved baseline evidence includes:
- 1H input data; 4H data derived from 1H data.
- Minimum 50 1H rows and minimum 15 4H rows.
- 4H EMA50 and 4H ATR(14).
- ATR percentage `(ATR / Close) * 100`; historical implementation rejects below 0.2%.
- 1H EMA20, RSI(14), 1H ATR(14), MACD(12,26,9).
- Closed 1H/4H values with prior/current MACD crossover comparison.
- Bullish branch: 4H close > 4H EMA50; previous MACD <= previous signal; current MACD > current signal; 1H RSI > 50 and < 80; 1H close > 1H EMA20.
- Bearish branch: 4H close < 4H EMA50; previous MACD >= previous signal; current MACD < current signal; 1H RSI < 50 and > 20; 1H close < 1H EMA20.

## Explicit freshness decision

The user has now explicitly rejected a special 6-hour freshness rule. The desired canonical freshness boundary is the historical 1-hour rule shown in the supplied Telegram evidence:
- `FRESH` when the referenced candle closed <= 1 hour ago.
- `STALE` when the referenced candle closed > 1 hour ago.
- No separate 6-hour threshold or special 6-hour freshness state is to be introduced.

A 6-hour-old signal is therefore simply `STALE` under the same >1h rule. The historical regression F-006 must be interpreted as guarding against reintroducing a 6h-vs-1h inconsistency, not as authorizing a 6-hour freshness threshold.

## Open decisions

| ID | Status | Decision required | Current evidence | Blocks |
|---|---|---|---|---|
| OD-001 | CONDITIONALLY APPROVED | TrendPulse historical formula baseline | User approved source-derived formula evidence as canonical reconstruction baseline | Phase 0 until conflicts resolved |
| OD-002 | OPEN | TrendPulse entry / SL / TP | Not established by supplied evidence | Phase 0 / Phase 4 |
| OD-003 | APPROVED | TrendPulse freshness | User explicitly approved 1-hour FRESH/STALE boundary; no special 6-hour rule | Phase 0 / Phase 4 |
| OD-004 | OPEN | TrendPulse genuinely-new-signal and repeat/dedup behavior, including new-message behavior | Not established by supplied evidence | Phase 0 / Phase 4 / Phase 6 |
| OD-005 | OPEN | TrendPulse missing-data fail-safe contract | Must never fabricate or assume missing values; exact behavior still needs freezing | Phase 0 / Phase 4 |
| OD-006 | OPEN | TrendPulse market/timeframe universe | Historical evidence constrains the implementation but does not establish final approved universe | Phase 0 / Phase 4 |
| OD-007 | OPEN | Exact approved Telegram copy for all registry IDs | User will provide exact messages as evidence; no inference permitted | Phase 0 / Phase 6 |
| OD-008 | OPEN | Final market-data provider | User requested research based on reliability, historical coverage, API/accessibility, latency, cost | Phase 0 / Phase 2 |
| OD-009 | OPEN | Final NSE 15-stock list | User requested objective research; historical list is evidence only, not approval | Phase 0 / product scope |
| OD-010 | OPEN | Account risk / position sizing | User explicitly leaves undefined until canonical strategy rules are established | Phase 7 |
| OD-011 | OPEN | Fees / slippage | User explicitly leaves undefined until canonical strategy rules are established | Phase 7 |
| OD-012 | OPEN | Hosting / runtime | User requested research based on reliability, uptime, deployment simplicity, monitoring, cost, workload | Phase 0 / Phase 10 |

## Locked and therefore not open
- Sweep timeframe for NIFTY/BANK NIFTY: 1H.
- Sweep starts: 09:15, 10:15, 11:15, 12:15, 13:15, 14:15 IST.
- No normal 15:15–16:15 Sweep candle.
- Closed candle only.
- Strict two-sided Sweep requirement.
- Equality is not a break.
- Exact BUY/SELL/NEUTRAL/NO_SIGNAL classification rules from the supplied Sweep V2 specification.
- Sweep freshness <=60m FRESH, >60m STALE.
- Paper-trade SL/TP rules from the supplied paper-trading/locked rules.
- Dashboard cannot calculate business truth.
- Backtest uses canonical strategy engines.
- Approved Telegram messages immutable after approval.
- CI read-only; no source or production mutation.
- Live broker execution disabled initially; paper trading enabled.

## Required decision record format
ID, Date, Status, Requirement, Context, Options, Decision, Rationale, Affected specs/tests/code, Approval evidence.
