# MULTIBOT2 — Mavis Clean Rebuild

This repository is a clean-slate rebuild of Mavis.

## Phase control

- **Phase 0: Specification Freeze — ACTIVE / NOT PASSED**
- Phase N must pass before Phase N+1 starts.
- No production implementation from a later phase may be merged before the current phase gate passes.
- TrendPulse implementation is deferred until the user supplies the authoritative code/evidence.
- Telegram wording is frozen only from exact authoritative user evidence.

## Current locked rules

- TrendPulse freshness: `<=60m = FRESH`, `>60m = STALE`.
- There is no special 6-hour freshness threshold.
- Sweep V2 rules remain governed by the supplied locked specification.

## Safety baseline

- Paper trading enabled by default.
- Live broker execution disabled by default.
- Secrets must never be committed.
- CI is read-only with minimum permissions.

See `docs/PHASE_0_SCOPE.md`, `docs/REQUIREMENTS_MATRIX.md`, `docs/OPEN_DECISIONS.md`, and `docs/PHASE_HANDOFF.md`.
