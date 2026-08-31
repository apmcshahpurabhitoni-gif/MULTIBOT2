# Open Decisions — Phase 0

No unresolved item is to be answered by invention. Each decision requires an explicit approval record before implementation depends on it.

## User-approved TrendPulse reconstruction baseline

On 2026-08-31 the user explicitly approved the historical TrendPulse evidence as the canonical reconstruction baseline, with the condition that unresolved conflicts must be resolved before implementation.

Approved baseline evidence includes:
- 1H input data; 4H data derived from 1H data.
- Minimum 50 1H rows and minimum 15 4H rows.
- 4H EMA50 and 4H ATR(14).
- ATR percentage `(ATR / Close) * 100`; historical implementation rejects below 0.2%.
- 1H EMA20, RSI(14), 1H ATR(14), MACD(12,26,9).
- Closed 1H/4H values with prior/current MACD crossover comparison.
- Bullish branch: 4H close > 4H EMA50; previous MACD <= previous signal; current MACD > current signal; 1H RSI > 50 and < 80; 1H close > 1H EMA20.
- Bearish branch: 4H close < 4H EMA50; previous MACD >= previous signal; current MACD < current signal; 1H RSI < 50 and > 20; 1H close < 1H EMA20.

## User-locked TrendPulse freshness

- `<= 60 minutes` after candle close = `FRESH`.
- `> 60 minutes` after candle close = `STALE`.
- There is no special 6-hour freshness threshold.
- A signal that is 6 hours old is simply STALE.

## Research decisions

### OD-008 — Market data provider stack
Status: **RECOMMENDED — final approval pending TrendPulse code/market-universe confirmation**.

Recommendation: use a provider stack rather than forcing one vendor to cover incompatible requirements:

1. **DhanHQ for NSE/Indian market data** — its official API provides intraday historical candles at 1, 5, 15, 25 and 60-minute intervals for the last five years for active instruments, across exchanges/segments. Its API documentation also publishes explicit rate limits and authentication. Data APIs are a paid add-on; Dhan currently advertises ₹499 for real-time market feed + historical data. This is the strongest fit found for NSE 1H historical/backtest coverage. citeturn1search3turn1search6turn1search8

2. **Twelve Data for XAU/USD / global instruments where required** — its catalog explicitly exposes XAU/USD commodity data and 1h intervals, while its NSE catalog covers Indian equities. However, the NSE page currently identifies exchange data as EOD, so it should not be used as the sole live NSE provider. citeturn8search10turn8search14turn8search0

Rejected as sole provider for this project:
- Upstox: excellent API surface and V3 supports 1-hour candles, but the historical V2 documentation clearly documents 30-minute as the highest sub-hour interval and one-year availability; the required long-history behavior is less explicit than Dhan. citeturn0search3turn0search2
- Zerodha Kite: strong 60-minute historical API and mature instrument model, but historical intraday retrieval is constrained per request and the provider is tied to Zerodha account/API access. citeturn2search0turn2search2
- Alpha Vantage: strong global intraday depth and 60-minute interval support, but its premium intraday entitlement is not a clean primary fit for live Indian NSE execution/data. citeturn7search0

Decision remains conditional until the user supplies TrendPulse code and its exact market universe, because the code determines whether XAU/USD is actually part of the required live market set.

### OD-009 — NSE 15-stock universe
Status: **RECOMMENDED — final approval pending**.

Objective rule: select the top 15 Nifty 50 constituents by free-float index weight from the latest complete constituent snapshot available to the research pass. This is reproducible, liquid, large-cap, and avoids arbitrary historical preferences. NSE Indices states that Nifty 50 is free-float-market-cap weighted and its constituent eligibility includes an average impact cost of 0.50% or less for 90% of observations for a ₹100M basket plus F&O eligibility. citeturn4view0turn5search22

Latest complete 15-name snapshot located in the official Nifty 50 research material (27-Feb-2026):
1. HDFC Bank
2. ICICI Bank
3. Reliance Industries
4. Bharti Airtel
5. Larsen & Toubro
6. State Bank of India
7. Infosys
8. Axis Bank
9. Kotak Mahindra Bank
10. Mahindra & Mahindra
11. ITC
12. Tata Consultancy Services
13. Bajaj Finance
14. Hindustan Unilever
15. Maruti Suzuki India

The official July 31, 2026 Nifty 50 factsheet confirms the first ten remain among the highest-weight constituents, although their weights/order have moved. citeturn4view0

This is a proposed objective universe, not yet an approved immutable list. The list should be re-evaluated at each Nifty 50 semi-annual review rather than silently drifting.

### OD-012 — Hosting/runtime
Status: **RECOMMENDED — final approval pending**.

Recommendation:
- **Render** for application/web service + background worker/cron workload.
- **Supabase Postgres** for the canonical database.

Reasoning: Render explicitly supports web services, private services, background workers and cron jobs; its health checks can automatically detect unhealthy instances and restart them for web/private services. Its current pricing model offers production-oriented service plans and a $25/month Pro workspace tier. citeturn3search2turn3search6turn3search11turn3search4

Supabase Pro is currently $25/month, includes daily backups with seven-day retention, and provides database/API monitoring plus a Prometheus-compatible metrics API. The Free plan pauses inactive projects, so production should use Pro rather than Free. citeturn3search0turn3search12turn3search14

This separation keeps compute/workers independently deployable from durable Postgres and gives the later Phase 9 observability work clear health/metrics surfaces.

## Remaining open decisions

| ID | Status | Decision required | Blocks |
|---|---|---|---|
| OD-001 | CONDITIONALLY APPROVED | TrendPulse baseline; unresolved trade/data rules await code | Phase 0 / Phase 4 |
| OD-002 | OPEN | TrendPulse entry / SL / TP | Phase 0 / Phase 4 |
| OD-003 | APPROVED | TrendPulse freshness <=60m FRESH, >60m STALE | Phase 4 |
| OD-004 | OPEN | TrendPulse genuinely-new-signal/repeat/dedup behavior | Phase 0 / Phase 4 / Phase 6 |
| OD-005 | OPEN | TrendPulse missing-data fail-safe | Phase 0 / Phase 4 |
| OD-006 | OPEN | TrendPulse market/timeframe universe | Phase 0 / Phase 4 |
| OD-007 | OPEN | Exact approved Telegram copy | Phase 0 / Phase 6 |
| OD-008 | RECOMMENDED | DhanHQ for NSE + Twelve Data where XAU/global data is required | Phase 0 / Phase 2 |
| OD-009 | RECOMMENDED | Top 15 Nifty 50 by free-float weight | Phase 0 / product scope |
| OD-010 | OPEN | Account risk / position sizing | Phase 7 |
| OD-011 | OPEN | Fees / slippage | Phase 7 |
| OD-012 | RECOMMENDED | Render + Supabase | Phase 0 / Phase 10 |

## Locked
- Sweep timeframe for NIFTY/BANK NIFTY: 1H.
- Sweep starts: 09:15, 10:15, 11:15, 12:15, 13:15, 14:15 IST.
- No normal 15:15–16:15 Sweep candle.
- Closed candle only.
- Strict two-sided Sweep requirement.
- Equality is not a break.
- Exact BUY/SELL/NEUTRAL/NO_SIGNAL classification rules from supplied Sweep V2.
- Freshness <=60m FRESH, >60m STALE.
- Paper-trade SL/TP rules from supplied paper-trading/locked rules.
- Dashboard cannot calculate business truth.
- Backtest uses canonical strategy engines.
- Approved Telegram messages immutable after approval.
- CI read-only; no source or production mutation.
- Live broker execution disabled initially; paper trading enabled.
