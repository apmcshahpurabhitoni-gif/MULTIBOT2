# Open Decisions — Phase 0

No unresolved item is to be answered by invention. Each decision requires an explicit approval record before implementation depends on it.

| ID | Status | Decision required | Current evidence | Blocks |
|---|---|---|---|---|
| OD-001 | OPEN | Exact TrendPulse formula | Recovered specs state the approved formula/parameters are not reliably preserved; must recover authoritative definition | Phase 4 |
| OD-002 | OPEN | TrendPulse parameters/timeframes/signals/trade rules/freshness/repetition/data behavior | Same gap | Phase 4 |
| OD-003 | OPEN | Exact approved Telegram copy for all registry IDs | Historical verbatim approved copy is not reliably available | Phase 6; Phase 0 freeze completion |
| OD-004 | OPEN | Final market-data provider | Must evaluate free limits, history, reliability, boundaries, rate limits, symbols, terms | Phase 2 |
| OD-005 | OPEN | Exact NSE 15-stock list | Not preserved in recovered material | Product scope dependent |
| OD-006 | OPEN | Account risk / position sizing | Must not be invented | Phase 7 |
| OD-007 | OPEN | Fees / slippage | Must not be invented | Phase 7 |
| OD-008 | OPEN | Hosting / runtime | Not fixed | Phase 10 |

## Locked and therefore not open
- Sweep timeframe for NIFTY/BANK NIFTY: 1H.
- Sweep starts: 09:15, 10:15, 11:15, 12:15, 13:15, 14:15 IST.
- No normal 15:15–16:15 Sweep candle.
- Closed candle only.
- Strict two-sided Sweep requirement.
- Equality is not a break.
- Exact BUY/SELL/NEUTRAL/NO_SIGNAL classification rules from the supplied Sweep V2 specification.
- Freshness <=60m FRESH, >60m STALE.
- Paper-trade SL/TP rules from the supplied paper-trading/locked rules.
- Dashboard cannot calculate business truth.
- Backtest uses canonical strategy engines.
- Approved Telegram messages immutable after approval.
- CI read-only; no source or production mutation.
- Live broker execution disabled initially; paper trading enabled.

## Required decision record format
ID, Date, Status, Requirement, Context, Options, Decision, Rationale, Affected specs/tests/code, Approval evidence.
