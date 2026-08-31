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
4. Resolve/review provider, objective NSE 15-stock universe, and hosting/runtime using documented research.
5. Run the formal Phase 0 gate.
6. Only after Phase 0 PASS, create the Phase 1 branch and implement Foundation.

## Locked rules
- NIFTY/BANK NIFTY Sweep: 1H.
- Sweep starts: 09:15, 10:15, 11:15, 12:15, 13:15, 14:15 IST.
- No normal 15:15–16:15 Sweep candle.
- Closed candle only.
- Strict two-sided Sweep requirement.
- Equality is not a break.
- Exact BUY/SELL/NEUTRAL/NO_SIGNAL rules from Sweep V2.
- Freshness: <=60m FRESH; >60m STALE.
- Sweep paper-trade SL/TP rules are frozen by supplied specs.
- Live broker execution disabled initially; paper trading enabled.
- Dashboard cannot calculate business truth.
- Backtest uses canonical strategy engines.
- Approved Telegram messages are immutable after approval.
- CI is read-only.

## TrendPulse
The user approved the historical formula evidence as the canonical baseline but instructed that the TrendPulse code will be supplied later. Implementation is deferred. The user explicitly locked freshness to <=60 minutes FRESH and >60 minutes STALE; there is no special 6-hour threshold.

## Research results
Provider, stock-universe and hosting research is documented in `docs/OPEN_DECISIONS.md`. These recommendations are not silently treated as final approval where the remaining TrendPulse/Telegram evidence can materially change the requirements.

## Gate
Phase 0 is NOT PASSED. The exact Telegram copy and TrendPulse code/evidence remain required before the formal gate can be completed. No Phase 1 work may be merged or treated as authorized before PASS.
