# Phase 0 — Specification Freeze

## Status
**IN PROGRESS — NOT PASSED**

## Governing workflow
READ SPEC → DEFINE SCOPE → DESIGN TESTS → IMPLEMENT ONLY CURRENT PHASE → RUN TESTS → FIX FAILURES → RUN REGRESSION → REVIEW DIFF → RUN CI → VERIFY CI COMPLETED/PASSED → COMPLETE GATE → WRITE HANDOFF → MARK PASSED → ONLY THEN NEXT PHASE.

## Completed
- Requirements traceability and architecture/test baselines.
- Locked Sweep V2 scope.
- User-approved historical TrendPulse baseline.
- User-locked TrendPulse freshness: <=60m FRESH; >60m STALE; no 6h threshold.
- Provider research recommendation.
- Objective NSE 15-stock research recommendation.
- Hosting/runtime research recommendation.

## Remaining blockers
- Exact Telegram V1 messages from user evidence.
- TrendPulse code from user to resolve remaining strategy-specific rules without guessing.
- Final conditional provider/stock/hosting confirmation after the exact TrendPulse market universe is known.

## Phase-order enforcement
A temporary Phase 1 branch/PR was created but is not authorized for merge because Phase 0 has not passed. No Phase 1 pass is claimed. `main` is the canonical source of truth.

## Next action
Stay in Phase 0 until the remaining evidence is supplied and the formal gate passes.
