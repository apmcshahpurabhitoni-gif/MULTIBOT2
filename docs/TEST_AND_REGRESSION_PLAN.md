# Test + Regression Architecture — Phase 0

## Test layers
- `tests/unit`: deterministic domain/time/validation/strategy primitives.
- `tests/integration`: provider normalization, candle building, persistence, Telegram state.
- `tests/contract`: SignalResult/API/message contracts and snapshots.
- `tests/regression`: permanent F-001…F-033 tests where technically testable.
- `tests/e2e`: Dashboard/API/Telegram end-to-end behavior in later phases.

## Mandatory Sweep cases
1. high-only break → NO_SIGNAL
2. low-only break → NO_SIGNAL
3. both breaks + close inside previous range → NEUTRAL
4. both breaks + close above previous High → BUY
5. both breaks + close below previous Low → SELL
6. equality/touch at high or low is not a break
7. open candle → no confirmed signal
8. every valid NSE start: 09:15, 10:15, 11:15, 12:15, 13:15, 14:15
9. 15:15 → rejected as normal Sweep start
10. naive datetime → rejected
11. freshness at 59m → FRESH
12. freshness at 60m → FRESH
13. freshness at 61m → STALE
14. 6h-old signal → STALE, never FRESH
15. candle boundary mismatch → warning
16. reference/data mismatch → structured warning
17. provider symbol mapping does not leak into display name
18. unrelated FVG/filter data cannot alter Sweep result

## Permanent regression mapping
- F-001: 4H/1H confusion
- F-002: one-sided Sweep
- F-003: equality counted as break
- F-004: open candle closed
- F-005: boundary mismatch
- F-006: 6h vs 1h freshness
- F-007/F-008: monkey-patching/source injection
- F-009: duplicate strategy implementations
- F-010: live/backtest divergence
- F-011: `[object Object]`
- F-012/F-013: price formatting and BUY/SELL visibility
- F-014: FVG contamination
- F-015: timezone failures
- F-016: dashboard/business logic mixing
- F-017: provider symbol leakage
- F-018: CI dependency failures
- F-019: CI source mutation
- F-020: duplicate reminders
- F-021: hidden data mismatch
- F-022/F-023: invented position sizing/stock list
- F-024: documentation drift
- F-025: context loss
- F-026: merge divergence
- F-027: queued CI called pass
- F-028: endless compatibility layers
- F-029: unsafe large-file replacement
- F-030: building too much before testing
- F-031: approved Telegram mutation
- F-032/F-033: TrendPulse omission/invention

## Snapshot rules
Every approved Telegram message gets a snapshot. CI must fail on wording, emoji, ordering, labels, fields, formatting, forbidden provider symbols, unapproved fields or `[object Object]`. Snapshot changes require an approved Change Request.

## Equivalence rule
Identical normalized inputs and configuration must produce identical canonical SignalResult between live evaluation and backtest. No second strategy algorithm is permitted.

## Phase 0 test design deliverable
Phase 0 establishes these executable-test obligations without implementing future-phase behavior. Phase 1+ must turn the relevant obligations into actual tests and make the phase gate depend on them.
