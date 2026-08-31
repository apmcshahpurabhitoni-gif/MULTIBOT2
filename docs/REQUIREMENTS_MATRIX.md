# Requirements Matrix — Phase 0 Baseline

Traceability format: Requirement → Spec → Planned Code → Test → CI → Phase Gate.

| ID | Requirement | Spec authority | Planned code area | Test obligation | CI | Gate |
|---|---|---|---|---|---|---|
| R-001 | Clean-slate rebuild; no old implementation access/copy | START_HERE / AI MASTER BUILD | Repository baseline only | Repo provenance review | Diff/provenance checks | P0 |
| R-002 | Phase N must pass before N+1 | BUILD PLAN / PHASE GATE | Phase-control docs/scripts | Gate sequencing test/check | CI gate | Every phase |
| R-003 | NIFTY/BANK NIFTY Sweep uses 1H | LOCKED_RULES / SWEEP_V2 | Phase 3 Sweep engine | 1H/4H regression | Regression suite | P3 |
| R-004 | Eligible Sweep starts are six NSE starts | SWEEP_V2 | Phase 2 candle/session + Phase 3 strategy | Six-start tests | Regression | P2/P3 |
| R-005 | No normal 15:15–16:15 Sweep candle | SWEEP_V2 | Session candle builder | 15:15 rejection | Regression | P2/P3 |
| R-006 | Closed candle only | SWEEP_V2 | Candle validation | Open-candle test | Unit/regression | P2/P3 |
| R-007 | Sweep requires strict high and low breaks | SWEEP_V2 | Sweep engine | Both/one-sided tests | Regression | P3 |
| R-008 | Equality is not a break | SWEEP_V2 | Sweep engine | Equality tests | Regression | P3 |
| R-009 | Sweep classification BUY/SELL/NEUTRAL exact rules | SWEEP_V2 / LOCKED_RULES | Sweep engine | Classification matrix | Regression | P3 |
| R-010 | Freshness <=60m FRESH, >60m STALE | SWEEP_V2 / LOCKED_RULES | Canonical freshness logic | 59/60/61m tests + 6h stale | Regression | P1/P3/P8 |
| R-011 | Paper trade BUY/SELL = detection entry, candle extreme SL, 2R TP | PAPER_TRADING / LOCKED_RULES | Phase 7 simulator | TradePlan equivalence | Regression | P7 |
| R-012 | Do not invent risk/account/leverage/fees/slippage | PAPER_TRADING / OPEN_DECISIONS | Config/domain | Negative/contract tests | CI | P0/P7 |
| R-013 | Canonical typed domain objects | DOMAIN_ARCHITECTURE / CODE_SCAFFOLDS | Phase 1 domain | Serialization/type tests | Type check + unit | P1 |
| R-014 | Provider → normalization → candles → strategy pipeline | MASTER / DOMAIN / MARKET DATA | Phases 2+ | Integration pipeline | Integration CI | P2/P3 |
| R-015 | Provider symbols must not leak to normal display names | MARKET DATA / LOCKED_RULES | Mapping layer | Symbol mapping regression | Regression | P2/P8 |
| R-016 | Dashboard displays backend truth; frontend does not calculate strategy/freshness/trade values | API_DASHBOARD | Phase 8 | API contract/UI smoke | Contract/UI CI | P8 |
| R-017 | Explicit loading/no-signal/stale/warning/provider/API/database error states | API_DASHBOARD | Phase 8 | UI state tests | UI CI | P8 |
| R-018 | `[object Object]` is forbidden | API_DASHBOARD / MESSAGE_TESTS / REGRESSIONS | Formatting/serialization | Regression + snapshot | CI | P6/P8 |
| R-019 | Centralized Telegram formatter; consumes canonical results | TELEGRAM_ARCHITECTURE | Phase 6 | Contract tests | Snapshot/delivery CI | P6 |
| R-020 | Max two Telegram messages per qualifying candle, initial + one-hour reminder | TELEGRAM_ARCHITECTURE | Phase 6 | Durable reminder tests | Integration CI | P6 |
| R-021 | Approved Telegram text is immutable without Change Request + approval | TELEGRAM_REGISTRY | Phase 0/6 | Snapshot mutation tests | CI | P0/P6 |
| R-022 | TrendPulse is mandatory and must not be invented | TRENDPULSE / MASTER | Phase 4 | Frozen definition + regression | CI | P0/P4 |
| R-023 | Backtest calls canonical strategy engines | DATABASE_BACKTEST / MASTER | Phase 7 | Live/backtest equivalence | Integration/regression | P7 |
| R-024 | Persistence is idempotent; retries/restarts do not duplicate signals/trades/reminders | DATABASE_BACKTEST / PAPER / TELEGRAM | Phase 5/6 | Idempotency tests | Integration CI | P5/P6 |
| R-025 | Supabase service role is server-only | SECURITY / API_DASHBOARD / DATABASE | Phase 5/8/9 | Secret exposure scan/contract | Security CI | P9 |
| R-026 | Initial safety baseline: paper enabled, live broker disabled | SECURITY / ENVIRONMENT | Phase 1 config | Config safety tests | CI | P1 |
| R-027 | No `.env` secrets committed | ENVIRONMENT / SECURITY | Repository/CI | Secret scan | CI | Every phase |
| R-028 | CI is read-only and cannot mutate source/production | CI/CD | Phase 10 CI/CD | CI mutation guard | CI | P10 |
| R-029 | Structured events and correlation fields | SECURITY / OBSERVABILITY / DOMAIN | Phase 9 | Structured logging tests | CI | P9 |
| R-030 | Every technically testable regression is permanent | REGRESSION_REGISTER | tests/regression | Regression suite | CI | Every phase |
| R-031 | Protected main and one coherent phase branch/PR | GIT/MERGE | Repository process | Branch/PR review | PR checks | Every phase |
| R-032 | No blind conflict resolution; rerun critical regression after merge | GIT/MERGE | Repository process | Merge verification | CI | Every phase |
| R-033 | Deployment requires health/smoke and recorded rollback | CI/CD / RELEASE | Phase 10 | Deployment smoke | CI/deploy | P10 |

## Explicit regression inventory

Permanent regressions must include the registered F-001 through F-033 failures where technically testable, including 1H/4H confusion, one-sided Sweep, equality, open candles, boundary mismatch, 6h stale/freshness, injection/monkey-patching, duplicate logic, live/backtest divergence, `[object Object]`, formatting/visibility, FVG contamination, timezone, dashboard logic mixing, provider symbols, CI dependencies/mutation, duplicate reminders, data mismatch, invented position sizing/stock list, documentation/context loss, merge divergence, false queued-CI pass, compatibility-layer sprawl, unsafe large-file replacement, early overbuilding, Telegram mutation, and TrendPulse omission/invention.

## Gate rule
A requirement is not complete until its code (when in scope), executable test, CI evidence and phase-gate evidence exist. Phase 0 records the mapping; future phases implement only their own rows.
