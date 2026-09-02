# MULTIBOT2

Complete paper-trading bot based on the original `multi-strategy-telegram-bot`, with the locked MULTIBOT2 fixes applied as one coherent runtime.

**Current release: v2.0.0**

## What's new in v2.0.0

- Forex Factory economic calendar in the dashboard, filtered by exact date and impact (High / Medium / Low / Holiday).
- Calendar timestamps are normalized to Asia/Kolkata for the dashboard while preserving the Forex Factory source link.
- Historical backtesting now supports the fixed 19-asset live universe (15 NSE stocks + NIFTY + BANK NIFTY + Gold + Bitcoin) plus Bitcoin (`BTC-USD`) and Gold Futures (`GC=F`).
- Backtest results show directional totals, trades taken, planned risk and a daily signal graph.
- Fixed the modern `yfinance` / `curl_cffi` session incompatibility that was causing historical backtests to fail.
- Period-aware Yahoo caching prevents a previous 30-day fetch from being reused for a different backtest period.
- Signals are grouped by candle date and the dashboard separates “no signals” from “no scan performed”.
- Light/dark and modern/neo-brutalist appearance controls were rebuilt with tighter responsive spacing and accessible controls.
- Release version and What's New are visible in Tools and the dashboard header.

## Runtime contract

`Yahoo 1m → canonical NSE 1H → confirmed 4H → strategy → 1h freshness → persistent duplicate/reminder gate → independent account risk → paper trade → approved Telegram → Supabase persistence → dashboard`

## Locked rules

- 19 live assets fixed live universe.
- Yahoo Finance only.
- NSE 1H candles are built from complete 60-minute 1m groups in the 09:15–15:30 cash session.
- Valid hourly candle closes: 10:15, 11:15, 12:15, 13:15, 14:15, 15:15.
- No fabricated 15:15–16:15 candle.
- TrendPulse evaluates confirmed latest candles; higher-timeframe filters use confirmed 4H candles.
- Freshness is exactly 1 hour: age <= 1h is fresh, age > 1h is stale.
- Signal identity is strategy + symbol + direction + candle timestamp.
- Maximum two Telegram sends: initial + one one-hour reminder. A third is blocked.
- Account limits are independent: macro=20, nifty=5, ny_session=3, sweep_4h=3.
- Risk is ₹2,000 per trade.
- TrendPulse SL=1.5 ATR and TP=3 ATR.
- Sweep V2 uses strict two-sided sweep confirmation, market entry, sweep extreme SL, and 1:2 TP.
- Paper trading only; leverage is 1x.
- Supabase is the production-authoritative persistent store for accounts, trades, signals and reminder state; SQLite is the local runtime cache/fallback.
- MULTIBOT2 has no pending-sweep persistence or pending-sweep workflow.

## Dashboard

The dashboard is presentation-only. It does not calculate strategy, entry, SL, TP, sizing or execution risk.

- **Overview** — system health, locked risk limits, 14-day signal graph, scan truth, latest signals and open trades.
- **Trades** — active paper positions with expandable full plans.
- **Signals** — durable dispatched history grouped by candle date, with All / Today / 7-day filters and explicit scan status.
- **History** — completed trades grouped by close date.
- **Forex Factory Calendar** — date selector plus impact filters, with source health and forecast/previous/actual values where supplied.
- **Tools** — light/dark, modern/neo-brutalist, historical backtesting, daily backtest graph, What's New, candle schedule, universe, account limits and diagnostics.

## Backtesting

Backtesting is informational and does not change live trading configuration.

Supported Yahoo assets:

- 19 live assets: 15 NSE stocks, NIFTY 50, BANK NIFTY, Gold (`GC=F`) and Bitcoin (`BTC-USD`). NSE stocks use `.NS`; global/index assets use their native Yahoo tickers.
- Bitcoin: `BTC-USD`.
- Gold Futures: `GC=F`.

TrendPulse backtests use the same canonical close-stamped 1H path as live. Sweep V2 backtests use market-specific raw Yahoo data and the exact configured schedule boundaries. Global Sweep V2 uses 30-minute Yahoo data for the 01:30/05:30/... or 02:30/06:30/... IST 4H windows; 90d/1y global Sweep backtests are rejected because Yahoo does not provide enough 30m history for those periods.

## Runtime components

- `main.py` — executable worker orchestration, Telegram commands, dashboard APIs, scanning and trade monitoring.
- `market_data.py` / `candles.py` — provider validation and canonical candle construction.
- `strategies.py` — single source of truth for strategy calculations.
- `trendpulse_runtime.py` / `trendpulse_service.py` — TrendPulse live path.
- `sweep_service.py` — Sweep V2 live path.
- `signal_gate.py` / `db.py` / `reminders.py` — freshness, duplicate, persistence and reminders.
- `telegram.py` — approved message boundary.
- `dashboard.py`, `dashboard.html`, `app.js`, `styles.css` — dashboard.
- `news.py` — cached Forex Factory economic-calendar reader.
- `yahoo_provider.py` — period-aware Yahoo Finance adapter.
- `backtest.py` — deterministic backtest boundary using the same strategy functions.

## Start

`python main.py`

Required secrets are environment-only: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `SUPABASE_URL`, and `SUPABASE_KEY`. Optional runtime settings include `BOT_STATE_DB_PATH`, `PORT`, `SCAN_INTERVAL_SECONDS`, and `MONITOR_INTERVAL_SECONDS`. Trading rules themselves are locked in `config.py` and cannot be overridden by environment variables.

## Render / uptime

Render runs the web service with `pip install -e .` and `python main.py`, with `/ping` as the health/keep-alive endpoint. Keep the existing external cron job configured to GET `/ping` every 10 minutes so the Render free service is regularly awakened. `/ping` is intentionally lightweight and does not scan markets, send signals, or mutate trading state.

## Validation

CI performs Python compilation, imports every runtime module, and runs the complete pytest suite. The mandatory release checklist is `FINALIZATION_RULEBOOK.md`.
