# MULTIBOT2 — Mavis Clean Rebuild

This repository is a clean-slate rebuild of Mavis.

## Current phase
**Phase 0 — Specification Freeze: IN PROGRESS / NOT PASSED**

The build plan is strict: Phase N must pass before Phase N+1 starts. Later-phase implementation is not merge-authorized before the current gate passes.

## Locked freshness rule
TrendPulse freshness is `<=60m = FRESH` and `>60m = STALE`. There is no special 6-hour threshold.

## Safety baseline
- Paper trading enabled by default.
- Live broker execution disabled by default.
- Secrets must never be committed.
- CI is read-only with minimum permissions.

See `docs/PHASE_0_SCOPE.md`, `docs/OPEN_DECISIONS.md`, and `docs/PHASE_HANDOFF.md`.
