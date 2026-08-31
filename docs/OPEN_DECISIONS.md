# Open Decisions — Phase 0

## Approved / conditionally approved

- TrendPulse historical formula baseline: approved by user as canonical evidence baseline.
- TrendPulse freshness: `<=60m FRESH`, `>60m STALE`; no 6-hour threshold.
- Provider recommendation: DhanHQ for NSE/Indian data + Twelve Data for XAU/global data if TrendPulse confirms that market requirement.
- NSE 15-stock recommendation: top 15 Nifty 50 constituents by free-float weight from the latest complete official 15-name snapshot located.
- Hosting recommendation: Render compute + Supabase Pro.

## Still open

- TrendPulse entry, SL, TP, new-signal/repeat behavior, missing-data behavior and final market universe — await user TrendPulse code.
- Exact Telegram V1 messages — await user evidence.
- Final confirmation of conditional provider/stock/hosting choices after the above inputs.
- Account risk, position sizing, fees and slippage — intentionally deferred until canonical strategy rules are established.

## Research evidence

DhanHQ documents 1/5/15/25/60-minute intraday historical candles for five years for active instruments, with explicit API authentication/rate limits; Dhan currently advertises Data APIs at ₹499. citeturn1search3turn1search6turn1search8

Twelve Data exposes XAU/USD and 1-hour data and an NSE catalog, but its NSE page currently labels the exchange feed EOD, so it is not suitable as the sole live NSE source. citeturn8search10turn8search14turn8search0

Nifty 50 uses free-float market-cap weighting and has liquidity/F&O eligibility requirements. The official Feb 27, 2026 research snapshot provides the complete top-15-by-weight recommendation. citeturn4view0turn4search12

Render supports web/background-worker/cron workloads and health checks; Supabase Pro is $25/month with daily backups and monitoring capabilities. citeturn3search2turn3search6turn3search11turn3search0turn3search12

## Gate
Phase 0 remains NOT PASSED. No Phase 1 work may be merged or treated as authorized until the remaining evidence is supplied and the formal gate passes.
