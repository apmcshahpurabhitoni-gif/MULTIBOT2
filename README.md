# MULTIBOT2

Complete paper-trading bot based on the original `multi-strategy-telegram-bot`, with the locked MULTIBOT2 fixes applied as one coherent runtime.

## Runtime contract

`Yahoo 1m → canonical NSE 1H → confirmed 4H → strategy → 1h freshness → persistent duplicate/reminder gate → independent account risk → paper trade → approved Telegram → Supabase persistence → dashboard`

## Locked rules

- NSE-15 fixed universe.
- Yahoo Finance only.
- NSE 1H candles are built from complete 60-minute 1m groups in the 09:15–15:30 cash session.
- Valid hourly candle closes: 10:15, 11:15, 12:15, 13:15, 14:15, 15:15.
- No fabricated 15:15–16:15 candle.
- TrendPulse evaluates confirmed latest candles; higher-timeframe filters use confirmed 4H candles.
- Freshness is exactly 1 hour: age <= 1h is fresh, age > 1h is stale.
- Signal identity is strategy + symbol + direction + candle timestamp.
- Maximum two Telegram sends: initial + one one-hour reminder. A third is blocked.
- Account limits are independent and restored from the original bot: macro=20, nifty=5, ny_session=3, sweep_4h=3.
- Risk is ₹2,000 per trade.
- TrendPulse SL=1.5 ATR and TP=3 ATR.
- Sweep V2 uses strict two-sided sweep confirmation, market entry, sweep extreme SL, and 1:2 TP.
- Paper trading only; leverage is 1x.
- Supabase is the production-authoritative persistent store for accounts, trades, signals and reminder state; SQLite is only the local runtime cache/fallback when Supabase is not configured.
- MULTIBOT2 has no pending-sweep persistence or pending-sweep workflow.

## Runtime components

- `main.py` — executable worker orchestration, Telegram commands, dashboard API, scanning and trade monitoring.
- `market_data.py` / `candles.py` — provider validation and canonical candle construction.
- `strategies.py` — single source of truth for strategy calculations.
- `trendpulse_runtime.py` / `trendpulse_service.py` — TrendPulse live path.
- `sweep_service.py` — Sweep V2 live path.
- `signal_gate.py` / `db.py` / `reminders.py` — freshness, duplicate, persistence and reminders.
- `telegram.py` — approved message boundary.
- `dashboard.py`, `dashboard.html`, `app.js`, `styles.css` — dashboard.
- `backtest.py` — deterministic backtest boundary using the same strategy functions.

## Start

`python main.py`

Required secrets are environment-only: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `SUPABASE_URL`, and `SUPABASE_KEY`. Optional runtime settings include `BOT_STATE_DB_PATH`, `PORT`, `SCAN_INTERVAL_SECONDS`, and `MONITOR_INTERVAL_SECONDS`. Trading rules themselves are locked in `config.py` and cannot be overridden by environment variables.

## Render / uptime

Render runs the web service with `pip install -e .` and `python main.py`, with `/ping` as the health/keep-alive endpoint. Keep the existing external cron job configured to GET `/ping` every 10 minutes so the Render free service is regularly awakened. `/ping` is intentionally lightweight and does not scan markets, send signals, or mutate trading state.

## Validation

CI performs Python compilation, imports every runtime module, and runs the complete pytest suite. The mandatory release checklist is `FINALIZATION_RULEBOOK.md`.
