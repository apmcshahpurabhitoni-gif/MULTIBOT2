# CI / Security / Deployment Baseline — Phase 0

## CI control requirements
CI pipeline order:
1. checkout
2. install
3. lint/format
4. type check
5. compile/build check
6. unit tests
7. regression tests
8. integration/contract tests
9. build
10. artifact validation

CI is read-only. It must not modify source, commit, push to main, repair source secretly, or mutate production schema.

A queued or running workflow is not a pass. Phase acceptance requires completed and passed CI plus passed PR checks.

## Git controls
- `main` is the protected release branch in the intended final repository configuration.
- One coherent branch/PR per phase.
- No competing implementations.
- No blind ours/theirs conflict resolution.
- After merge, record merge commit and rerun critical regression.

## Security baseline
- Never commit secrets.
- Never expose service-role database keys to the frontend.
- Separate local/test/production.
- CI receives minimum permissions.
- Initial safety: `PAPER_TRADING_ENABLED=true`; `LIVE_BROKER_ENABLED=false`.
- No broker execution initially.

## Observability baseline
Structured events must cover provider, normalization, candle validation, strategy, signal, persistence, Telegram, reminder, API, startup and shutdown.

Correlation fields: `run_id`, `instrument`, `candle_start`, `signal_id`, `strategy_version`.

Missing/invalid required inputs produce no invented signal. Retries are bounded and idempotent.

## Environment baseline
`.env` is never committed. `.env.example` contains placeholders. Required environment variable names are those specified in the supplied environment document, including server-only `SUPABASE_SERVICE_ROLE_KEY`.

## Deployment sequence
local/test → PR → CI → review → merge → deploy → health → smoke.

Record commit/version and rollback version. Production release also requires all prior phase gates, database migration review, security pass, dashboard smoke, live/backtest equivalence, and deployment evidence.
