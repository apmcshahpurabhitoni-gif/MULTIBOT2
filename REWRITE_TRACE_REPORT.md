# 19-Asset Strategy Rewrite Trace Report

## Current trace
- Render starts `startup.py` then `main.py`.
- `startup.py` sends two startup Telegram announcements on each process start.
- `main.py` scanner loop runs every 5 minutes and calls TrendPulse then Sweep.
- GitHub Actions contains tests only; no trading cron.
- ReminderService independently polls persisted reminders every 30 seconds.
- SweepService currently iterates only NSE-15 and hardcodes Telegram timeframe 4H.
- Sweep engine already contains market-specific eligibility logic: NIFTY/BANK 1H; NSE equities 4H; BTC 4H; Gold/non-NSE 4H.
- config/main/startup/dashboard still describe a 15-asset NSE universe.

## Locked target
19 live assets: 15 NSE stocks + NIFTY 50 + BANK NIFTY + Gold + Bitcoin.
TrendPulse: all 19 use 1H signal with confirmed 4H filter.
Sweep: NIFTY 50 and BANK NIFTY use 1H; 15 NSE stocks, Gold and Bitcoin use 4H.
Freshness remains 1 hour; paper trading, INR 100,000 account, INR 2,000 risk and 1x leverage remain locked.

## Files to replace coherently
1. `config.py` — replace the old NSE-only live universe with a single 19-asset registry and strategy/timeframe metadata; keep existing risk/account/freshness/provider validation.
2. `sweep_service.py` — replace the NSE-only loop with registry-driven eligibility, preserve one acceptance boundary, pass the actual Sweep timeframe/market/asset metadata into Telegram, and scan only when the current candle is eligible.
3. `trendpulse_runtime.py` — replace NSE-only symbol validation/fetch assumptions with registry-aware Yahoo symbol/data handling while retaining 1H + confirmed completed 4H filtering.
4. `trendpulse_service.py` — replace hardcoded NSE/1H formatting with registry metadata and 19-asset scanning.
5. `main.py` — replace 15-asset counters, price and trade-market assumptions, and scanner bookkeeping with registry-derived values; keep one runtime scanner rather than duplicate schedulers.
6. `telegram.py` — replace stale startup/scan universe text and ensure message fields are supplied from actual asset metadata; do not create a fake signal message for a scheduled check.
7. `startup.py` — replace stale NSE-15 announcement text with the 19-asset architecture and current strategy coverage.
8. `backtest.py` — make Sweep backtesting respect asset-specific Sweep timeframe/schedule while retaining TrendPulse 1H+confirmed-4H logic.
9. `dashboard.py` / dashboard payload path if needed — expose the same registry and coverage instead of hardcoded 15.
10. Tests covering config, runtime, sweep service, Telegram, main and backtest — rewrite expectations around the 19-asset registry and exact timeframe matrix.

## Do not change
- Locked account limits/risk/freshness/leverage unless a separate approved rule says so.
- Paper-trading model.
- Dashboard as presentation-only.
- Legacy 6-hour CoinGecko/Top-200 behavior: it must not be reintroduced.
- GitHub Actions tests workflow into a trading scheduler.

## Important scheduling decision
The current repository has no exact external trading cron for the requested Sweep times. The canonical scheduler should therefore be one in-process scheduler/eligibility layer driven by the asset registry. It must not send a Telegram message merely because the five-minute loop ran; Telegram is emitted only after an actual eligible candle is scanned and a directional signal passes the existing acceptance/freshness/duplicate/risk gates.
