# Phase 0 — Specification Freeze

## Objective
Freeze the authoritative product scope, contracts, unresolved business decisions, architecture, and test obligations before implementation.

## Governing workflow
READ SPEC → DEFINE SCOPE → DESIGN TESTS → IMPLEMENT ONLY CURRENT PHASE → RUN TESTS → FIX FAILURES → RUN REGRESSION → REVIEW DIFF → RUN CI → VERIFY CI COMPLETED/PASSED → COMPLETE GATE → WRITE HANDOFF → MARK PASSED → ONLY THEN NEXT PHASE.

## Current state
Phase 0 remains active and NOT PASSED.

### Frozen
- Sweep V2 scope and rules from supplied specifications.
- TrendPulse historical formula baseline as conditionally approved by the user.
- TrendPulse freshness: <=60m FRESH; >60m STALE; no special 6h threshold.
- Paper trading only; live broker disabled initially.
- Repository/architecture/test/CI/security baselines.

### Research completed
- Provider: DhanHQ recommended for NSE/Indian market data; Twelve Data recommended as secondary/global/XAU source if TrendPulse confirms XAU/USD requirement.
- Stock universe: top 15 Nifty 50 constituents by free-float weight, using the latest complete official 15-name snapshot located, recommended as the objective universe.
- Hosting: Render + Supabase Pro recommended.

### Still required before Phase 0 PASS
- Exact approved Telegram messages from the user.
- TrendPulse code from the user so remaining strategy-specific rules are reconstructed rather than guessed.
- Final confirmation of conditional provider/stock/hosting recommendations after the exact TrendPulse market universe is known.

## Phase-order enforcement
A temporary Phase 1 branch/PR was created while following the user's instruction to build non-TrendPulse work. The governing rules require Phase 0 PASS before Phase 1, so that work is isolated and is not merge-authorized. No Phase 1 pass is claimed.

## Next action
Remain in Phase 0. Do not merge Phase 1 or begin Phase 2 until Phase 0 is formally passed.
