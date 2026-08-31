# Open Decisions — Phase 0

No unresolved item is to be answered by invention. Each decision requires an explicit approval record before implementation depends on it.

## Approved / conditionally approved

- **TrendPulse baseline:** user-approved historical evidence is the canonical baseline; remaining strategy-specific conflicts are deferred until the user supplies the TrendPulse code.
- **TrendPulse freshness:** `<=60m = FRESH`, `>60m = STALE`; no special 6-hour threshold.
- **Provider recommendation:** DhanHQ for NSE/Indian data plus Twelve Data for global/XAU data if required by the TrendPulse code.
- **Stock-universe recommendation:** top 15 Nifty 50 constituents by free-float weight from the latest complete official 15-name snapshot located.
- **Hosting recommendation:** Render compute + Supabase Pro Postgres.

## Still open

| ID | Decision | Why still open |
|---|---|---|
| OD-002 | TrendPulse entry / SL / TP | Must come from user-supplied TrendPulse code/evidence; no guessing. |
| OD-004 | TrendPulse genuinely-new-signal / repeat / dedup | Must come from user-supplied TrendPulse code/evidence. |
| OD-005 | TrendPulse missing-data fail-safe | Exact behavior must come from the code/evidence. |
| OD-006 | TrendPulse market/timeframe universe | User code may materially change the required provider stack. |
| OD-007 | Exact approved Telegram copy | Awaiting user-provided messages; never infer. |
| OD-010 | Account risk / position sizing | User intentionally deferred until strategy rules are canonical. |
| OD-011 | Fees / slippage | User intentionally deferred until strategy rules are canonical. |

## Research basis

DhanHQ's official documentation states that its intraday historical API supports 1/5/15/25/60-minute candles for the last five years for active instruments, across exchanges/segments; Dhan's API docs publish explicit rate limits and authentication, and Dhan currently advertises paid Data APIs at ₹499. citeturn1search3turn1search6turn1search8

Twelve Data exposes XAU/USD commodity data and 1-hour intervals, and has an NSE catalog, but its NSE exchange page currently identifies the exchange feed as EOD, so it is not recommended as the sole live NSE source. citeturn8search10turn8search14turn8search0

NSE Indices states that Nifty 50 is free-float-market-cap weighted and its constituent eligibility includes liquidity/impact-cost and F&O requirements. The official February 27, 2026 research snapshot provides the complete top-15-by-weight list used for the recommendation. citeturn4view0turn4search12

Render supports web services, background workers and cron jobs and provides health checks for web/private services. Supabase Pro is currently $25/month and includes daily backups with seven-day retention; Supabase also provides monitoring and a Prometheus-compatible metrics API. citeturn3search2turn3search6turn3search11turn3search0turn3search12

## Phase-order control
A temporary Phase 1 branch/PR was created but is not authorized for merge because Phase 0 has not passed. `main` remains the canonical source of truth until the user provides the remaining evidence and the formal Phase 0 gate is completed.
