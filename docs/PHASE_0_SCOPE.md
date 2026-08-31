# Phase 0 — Specification Freeze

## Objective
Freeze the authoritative product scope, contracts, unresolved business decisions, architecture, and test obligations before implementation.

## Governing workflow
READ SPEC → DEFINE SCOPE → DESIGN TESTS → IMPLEMENT ONLY CURRENT PHASE → RUN TESTS → FIX FAILURES → RUN REGRESSION → REVIEW DIFF → RUN CI → VERIFY CI COMPLETED/PASSED → COMPLETE GATE → WRITE HANDOFF → MARK PASSED → ONLY THEN NEXT PHASE.

Any failure keeps the repository in the current phase until the root cause is fixed and the full required verification is repeated.

## Current execution order
1. Complete Phase 0 evidence and research.
2. Keep TrendPulse implementation deferred until the user supplies the code.
3. Freeze Telegram only from exact user-supplied messages.
4. Resolve provider, objective NSE 15-stock universe, and hosting/runtime using documented research.
5. Run the formal Phase 0 gate.
6. Only after Phase 0 PASS, create the Phase 1 branch and implement Foundation.

## Explicitly out of scope before Phase 0 PASS
- Production strategy implementation.
- TrendPulse implementation before its exact approved code/specification is supplied.
- Telegram formatter/delivery implementation before exact approved copy is frozen.
- Market-data provider implementation before provider selection is finalized.
- Database migration implementation.
- Backtest implementation.
- API/dashboard implementation.
- Hardening implementation.
- Deployment implementation.

## Locked product rules recorded now
NIFTY/BANK NIFTY Sweep is 1H with eligible starts 09:15, 10:15, 11:15, 12:15, 13:15, 14:15 IST. There is no normal 15:15–16:15 Sweep candle. Closed candle only. A Sweep requires strict breaks on both sides. Equality is not a break. One-sided break is NO_SIGNAL. Both breaks plus close above previous High is BUY; below previous Low is SELL; inside/equal previous range is NEUTRAL. Freshness is <=60m FRESH and >60m STALE. BUY SL is signal-candle Low; SELL SL is signal-candle High; TP is 2R; NEUTRAL has no paper trade. These locked rules are sourced from the supplied project specifications and are not altered here.

## TrendPulse
The user approved the historical formula evidence as the canonical baseline but instructed that the TrendPulse code will be supplied later. Therefore TrendPulse implementation is deferred. The user explicitly locked freshness to <=60 minutes FRESH and >60 minutes STALE; there is no special 6-hour threshold.

## Phase 0 gate
PASS only when the authoritative decisions/evidence and required research are recorded, no critical ambiguity remains for the phase's required scope, the exact Telegram copy is frozen from authoritative user evidence, and the formal executable verification/CI gate is completed. A Phase 1 branch created before this PASS is not merge-authorized.
