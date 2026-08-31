# Phase 1 — Foundation Handoff

## Status
IN PROGRESS — NOT PASSED.

## Branch
`phase/1-foundation`

## PR
`#1` — Phase 1: Foundation

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

## Verification history
A local reconstruction of the foundation suite initially exposed an OHLC validator ordering defect. The repository implementation was corrected to validate the complete Candle model after parsing. The first reconstructed run was 8 passed / 1 failed; the failure was the validator-order defect. The corrected repository state now requires a fresh executable run in CI.

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
The repository workflow uses `permissions: contents: read`, installs the package with test dependencies, runs pytest, and performs compile validation. CI must actually complete and pass before this phase can pass.

## Gate status
NOT PASSED. Local execution is constrained by the environment's inability to reach GitHub, and no completed GitHub CI run has yet been verified for the current head. No merge is permitted.

## TrendPulse
Deferred by explicit user instruction. This is a deliberate scope boundary. TrendPulse remains a Phase 4 dependency and must use user-supplied authoritative code when provided.

## Next permitted action
Remain in Phase 1 until executable CI and gate evidence are complete. Do not start Phase 2 merely because the implementation appears complete.
