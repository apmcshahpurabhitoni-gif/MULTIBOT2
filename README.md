# MULTIBOT2

Production paper-trading bot based on the original `multi-strategy-telegram-bot` behavior with the locked MULTIBOT2 market-data, candle, TrendPulse, freshness, Telegram, and risk fixes.

## Locked runtime rules

- NSE-15 is fixed; no silent universe refresh.
- Yahoo Finance is the market-data provider.
- NSE 1H candles are built from exact 09:15-15:14 minute buckets.
- TrendPulse uses completed 1H/4H candles only.
- Signal freshness is 1 hour; exactly one hour is fresh.
- Identical signal identity is strategy + symbol + direction + candle timestamp; maximum two sends.
- TrendPulse risk is ₹2,000 per trade with 1.5 ATR stop and 3 ATR target.
- Four independent account limits are restored from the original bot: macro=20, nifty=5, ny_session=3, sweep_4h=3.
- State is persisted in SQLite; dashboard history is independent of Telegram repeat expiry.
- The bot remains paper-trading only.

## Runtime

`python main.py`

Environment credentials are supplied through `.env` / the deployment environment. No credentials are committed to source.
