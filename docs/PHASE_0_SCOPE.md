# Phase 0 — Specification Freeze

## Objective
Freeze the authoritative product scope, contracts, unresolved business decisions, architecture, and test obligations before implementation.

## Governing workflow
READ SPEC → DEFINE SCOPE → DESIGN TESTS → IMPLEMENT ONLY CURRENT PHASE → RUN TESTS → FIX FAILURES → RUN REGRESSION → REVIEW DIFF → RUN CI → VERIFY CI COMPLETED/PASSED → COMPLETE GATE → WRITE HANDOFF → MARK PASSED → ONLY THEN NEXT PHASE.

Any failure keeps the repository in the current phase until the root cause is fixed and the full required verification is repeated.

## In scope for Phase 0
- Requirements traceability baseline.
- Architecture and domain contract baseline.
- API contract baseline.
- Database/backtest design baseline.
- Test architecture and regression inventory.
- CI/deployment control requirements.
- Security/observability requirements.
- Open decision register.
- TrendPulse freeze gate.
- Telegram message approval/freeze gate.
- Phase 0 handoff template and acceptance evidence.

## Explicitly out of scope
- Production strategy implementation.
- TrendPulse implementation before its exact approved specification is frozen.
- Telegram formatter/delivery implementation before exact approved copy is frozen.
- Market-data provider implementation before provider selection is finalized.
- Database migration implementation before Phase 5.
- Backtest implementation before Phase 7.
- API/dashboard implementation before Phase 8.
- Hardening implementation before Phase 9.
- Deployment implementation before Phase 10.

## Locked product rules recorded now
NIFTY/BANK NIFTY Sweep is 1H with eligible starts 09:15, 10:15, 11:15, 12:15, 13:15, 14:15 IST. There is no normal 15:15–16:15 Sweep candle. Closed candle only. A Sweep requires strict breaks on both sides. Equality is not a break. One-sided break is NO_SIGNAL. Both breaks plus close above previous High is BUY; below previous Low is SELL; inside/equal previous range is NEUTRAL. Freshness is <=60m FRESH and >60m STALE. BUY SL is signal-candle Low; SELL SL is signal-candle High; TP is 2R; NEUTRAL has no paper trade. These locked rules are sourced from the supplied project specifications and are not altered here.

## Phase 0 blockers
Phase 4 is blocked until TrendPulse is frozen. Telegram implementation/freeze is blocked until the exact approved historical copy is recovered from an authoritative source. Final provider selection and other open decisions remain explicitly unresolved until approved.

## Required Phase 0 gate
PASS only when:
1. Requirements matrix exists and every requirement has a planned Spec/Code/Test/CI/Phase Gate mapping.
2. Open decisions are explicit with no invented answers.
3. TrendPulse formula, parameters, inputs, timeframes, states, trade rules, freshness/repetition/data behavior, Telegram copy, dashboard fields and backtest behavior are either frozen from authoritative material or explicitly remain unresolved; unresolved TrendPulse blocks Phase 4.
4. Telegram registry has exact approved text only from an authoritative source; no fabricated copy is treated as approved.
5. Architecture/domain/API/database/test/CI/security baselines are documented without future-phase implementation.
6. Phase 0 regression obligations are mapped.
7. No secrets are committed and no source injection/monkey-patching/duplicate strategy plans are introduced.
8. Phase 0 tests/design evidence and CI definition are documented; CI must be actually completed and passed for the phase to pass.
9. Diff is reviewed and a completed handoff records branch, commit, PR, tests, regression, CI, decisions, issues, rollback and next permitted phase.

Phase 0 cannot be marked passed merely because files were created.
