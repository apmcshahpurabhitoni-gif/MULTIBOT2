# Phase 0 — Specification Freeze

## Status
**IN PROGRESS — NOT PASSED**

## Governing rule
Phase N must pass before Phase N+1. A queued, running, or unverified CI state is never a pass.

## Completed
- Requirements traceability baseline.
- Architecture/domain/test/CI/security baselines.
- Locked Sweep V2 scope.
- User-approved historical TrendPulse baseline.
- User-locked TrendPulse freshness: <=60m FRESH, >60m STALE; no 6h threshold.
- Provider research and conditional recommendation.
- Objective NSE 15-stock research and conditional recommendation.
- Hosting/runtime research and conditional recommendation.

## Remaining blockers
1. Exact Telegram V1 messages must be supplied by the user and frozen verbatim.
2. TrendPulse code must be supplied by the user before remaining strategy-specific rules are frozen/implemented.
3. Conditional provider/stock/hosting decisions must be finalized after those requirements are known.

## Explicit prohibition
Do not merge or start Phase 1 implementation while this gate is NOT PASSED. Do not invent TrendPulse behavior or Telegram wording.
