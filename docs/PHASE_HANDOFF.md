# Phase Handoff Record

## Phase
Phase 0 — Specification Freeze

## Status
IN PROGRESS — NOT PASSED.

## Branch
`phase/0-specification-freeze`

## Objective
Freeze product/architecture/test scope without implementing future phases.

## Requirements
See `docs/REQUIREMENTS_MATRIX.md`.

## Current decisions
- TrendPulse historical formula baseline: conditionally approved from source-derived evidence.
- TrendPulse freshness: explicitly locked by user to <=60m FRESH and >60m STALE; no 6h threshold.
- TrendPulse code: user will supply later; do not implement or infer it now.
- Telegram exact approved copy: awaiting user evidence; do not fabricate.
- Provider: research required.
- NSE 15-stock universe: objective research required; historical list is evidence only.
- Risk sizing/fees/slippage: intentionally undefined until canonical strategy rules are established.
- Hosting/runtime: research required.

## Phase-order correction
A temporary Phase 1 branch/PR was created while acting on the instruction to build non-TrendPulse work. The governing build plan requires Phase N to PASS before Phase N+1. The Phase 1 branch is therefore not authorized for merge and Phase 1 is not considered started/passed. The work remains isolated from `main` and will not be merged until Phase 0 passes.

## Tests / CI
Phase 0 has documentation/test-design evidence. No Phase 0 pass is claimed because the gate requires completed executable CI and all required specification decisions.

## Open blockers
- Exact approved Telegram copy.
- Provider selection.
- Final objective 15-stock list.
- Hosting/runtime decision.
- Any remaining TrendPulse conflicts not resolved by user-provided code.

## Regression
F-001 through F-033 are recorded in the regression plan. F-006 is now explicitly protected as the 1-hour TrendPulse freshness boundary.

## Gate decision
NOT PASSED. Do not start or merge Phase 1 until Phase 0 is explicitly passed.

## Next permitted action
Complete Phase 0 research/evidence and resolve remaining blockers, then execute the formal Phase 0 gate.
