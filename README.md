# MULTIBOT2 — Mavis Clean Rebuild

This repository is a clean-slate rebuild of Mavis.

## Phase control

- Phase 0: Specification Freeze — current
- Phase N must pass before Phase N+1 starts.
- No production implementation is permitted until the current phase gate passes.
- TrendPulse and Telegram wording are frozen only from authoritative approved material; unresolved items are explicitly recorded and are not invented.

## Safety baseline

- Paper trading enabled by default.
- Live broker execution disabled by default.
- Secrets must never be committed.
- CI is read-only with minimum permissions.

See `docs/PHASE_0_SCOPE.md`, `docs/REQUIREMENTS_MATRIX.md`, `docs/OPEN_DECISIONS.md`, and `docs/PHASE_HANDOFF.md`.
