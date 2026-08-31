# Phase 1 — Foundation Handoff

## Status
IN PROGRESS — NOT PASSED.

## Branch
`phase/1-foundation`

## Objective
Implement only Foundation: configuration, typed domain contracts, timezone/freshness primitives, errors, logging, serialization, and executable tests.

## Explicit scope guard
TrendPulse implementation is deferred until the user supplies the authoritative TrendPulse code/definition. No TrendPulse business logic is present here. Phase 2+ strategy/data/persistence/Telegram/API/backtest implementation is not included.

## Implemented
- Typed domain models and immutable contracts.
- Timezone-aware datetime validation.
- Canonical one-hour freshness helper: <=60 minutes FRESH; >60 minutes STALE.
- Serialization without object-placeholder output.
- Configuration safety baseline with live broker disabled.
- Strategy and market-data provider abstract boundaries.
- Foundation logging.
- Executable pytest coverage.
- Read-only GitHub Actions CI workflow.

## Verification
A local reconstruction of the foundation suite initially exposed an OHLC validator ordering defect. The repository implementation was corrected to validate the complete Candle model after parsing. The local reconstructed suite then needs to be rerun; GitHub CI remains the authoritative repository execution evidence.

## Tests
`tests/test_foundation.py`

Coverage includes:
- naive datetime rejection
- exact 60-minute freshness boundary
- six-hour state remains STALE, with no special six-hour threshold
- future close rejection
- candle timezone validation
- invalid OHLC rejection
- SignalResult serialization
- live broker safety guard
- immutable domain contract

## CI
A GitHub Actions workflow exists and is configured with `contents: read`. CI completion and pass must be verified before this phase can pass.

## Known blockers to Phase 1 PASS
- CI must actually complete and pass.
- Final diff must be reviewed.
- Full required regression suite must be rerun after final fixes.
- Phase gate evidence must be recorded.

## TrendPulse
Deferred by explicit user instruction. This is not a Phase 1 failure; it is a deliberate scope boundary. TrendPulse remains a Phase 4 dependency and must use user-supplied authoritative code when provided.

## Next permitted action
Remain in Phase 1 until its gate is evidenced as passed. Do not start Phase 2 merely because the implementation appears complete.
