# MULTIBOT2

Complete paper-trading runtime based on the original `multi-strategy-telegram-bot` behavior, with the locked MULTIBOT2 market-data/candle/TrendPulse fixes.

## Locked rules
- NSE-15 fixed universe.
- Yahoo Finance provider.
- Canonical NSE 1H candles from 1-minute data.
- Completed candles only.
- TrendPulse freshness: 1 hour.
- Same strategy + symbol + direction + candle timestamp: maximum 2 sends, persisted across restarts.
- TrendPulse risk: ₹2,000/trade; 1.5 ATR SL; 3 ATR TP.
- Four independent account limits restored from the original bot: macro=20, nifty=5, ny_session=3, sweep_4h=3.
- Paper trading only.
- SQLite persistence for accounts, active trades, history, and signal send counts.

## Run

`python main.py`

Credentials belong in the deployment environment / `.env`; none are committed.
