# MULTIBOT2 Canonical Notes

> Repository audit and implementation contract for the current `main` branch. This file records the rules that are already locked and the presentation decisions approved for the dashboard rebuild. It is not permission to change trading behavior.

## 1. Source of truth

1. `multi-strategy-telegram-bot` is the historical behavior reference.
2. `MULTIBOT2` locked specifications override obsolete behavior only where explicitly locked.
3. `FINALIZATION_RULEBOOK.md` is the release contract.
4. Strategy/risk behavior belongs in the canonical backend modules; the dashboard is presentation only.
5. No UI change may silently alter trading execution.

## 2. Current repository surface

Core runtime and rules:
- `main.py` — runtime orchestration, scanner/monitor loops, Telegram commands, dashboard API and `/ping`.
- `config.py` — locked configuration and validation.
- `candles.py` — canonical NSE session and hourly candle rules.
- `market_data.py` / provider path — market-data validation and provider boundary.
- `strategies.py` — canonical indicator and strategy calculations.
- `trendpulse_runtime.py` / `trendpulse_service.py` — TrendPulse scan/dispatch.
- `sweep_engine.py` / `sweep_service.py` — Sweep V2 scan/dispatch.
- `signal_gate.py` — signal identity/freshness/acceptance gate.
- `trading.py` — paper trading, sizing and account-risk rules.
- `db.py` — local SQLite cache plus Supabase persistence/restore.
- `reminders.py` — persistent one-hour reminder processing.
- `telegram.py` — canonical user-facing Telegram messages and transport.
- `backtest.py` — deterministic analytical backtest boundary.

Presentation/deployment:
- `dashboard.py` — dashboard data conversion helpers.
- `dashboard.html` — dashboard document shell and UI sections.
- `app.js` — dashboard state, rendering and interaction.
- `styles.css` — dashboard visual system and responsive behavior.
- `startup.py` — startup/deployment support.
- `render.yaml` — Render service configuration.
- `.github/workflows/tests.yml` — CI.
- `supabase/schema.sql` — persistence schema.

Tests cover accounts, backtest, candles, configuration, dashboard UI, DB, main runtime, market data, signal gate, strategies, Telegram, TrendPulse runtime/service and Sweep behavior.

## 3. Locked trading configuration

- Paper trading only.
- Account size: INR 100,000 per account.
- Independent daily limits: `macro=20`, `nifty=5`, `ny_session=3`, `sweep_4h=3`.
- Risk: INR 2,000 per trade.
- Leverage: 1x.
- Timezone: `Asia/Kolkata`.
- Timeframe: `1h`.
- Market-data provider: Yahoo Finance.
- Fixed 19-asset live universe:
  `RELIANCE`, `BHARTIARTL`, `HDFCBANK`, `ICICIBANK`, `SBIN`, `TCS`, `BAJFINANCE`, `LT`, `LICI`, `SUNPHARMA`, `HINDUNILVR`, `INFY`, `TITAN`, `MARUTI`, `KOTAKBANK`.
  Plus `^NSEI`, `^NSEBANK`, `GC=F`, and `BTC-USD`.

## 4. Candle contract

- All timestamps are timezone-aware and canonicalized to IST.
- NSE cash session is 09:15–15:30.
- Canonical hourly closes are exactly 10:15, 11:15, 12:15, 13:15, 14:15 and 15:15.
- The canonical final candle is 14:15–15:14 and closes at 15:15.
- There is no 15:15–16:15 NSE hourly candle.
- Incomplete candles must not reach strategy evaluation.
- Higher-timeframe candles must also be confirmed.
- The latest completed candle is eligible for evaluation; it must not be discarded merely because an obsolete architecture expected a forming final row.

## 5. TrendPulse contract

- Uses the canonical 1H path with confirmed 4H filtering.
- Requires sufficient 1H/4H history.
- Uses EMA, RSI, MACD and ATR conditions from `strategies.py`.
- BUY requires the approved bullish HTF/indicator alignment.
- SELL requires the approved bearish HTF/indicator alignment.
- TrendPulse SL = 1.5 ATR.
- TrendPulse TP = 3 ATR from entry (2R reward for 1.5R stop distance).
- Planned risk is capped at INR 2,000.
- No directional signal means no trade and no Telegram signal dispatch.

## 6. Sweep V2 contract

- Strict two-sided sweep is required: current high must exceed previous high AND current low must fall below previous low.
- Final-close classification determines BUY, SELL or NEUTRAL.
- BUY: close above previous high.
- SELL: close below previous low.
- Close inside the previous range: NEUTRAL.
- No two-sided sweep: NO_SIGNAL.
- Market entry.
- Sweep extreme is the stop loss.
- Target is 1:2 relative to entry-to-sweep-extreme risk.
- MULTIBOT2 has no pending-sweep persistence and no pending-sweep workflow.

## 7. Freshness / duplicate / reminder contract

- Freshness is exactly one hour.
- Age <= 1 hour is FRESH.
- Age > 1 hour is STALE.
- Future timestamps are invalid.
- Signal identity is `strategy + symbol + direction + candle timestamp`.
- Maximum Telegram sends for one signal identity: two total — initial + one reminder.
- The reminder is due one hour after the initial send.
- A third send is always blocked.
- Scanning must not consume duplicate allowance until the signal is actually accepted/sent.
- Stale signals never open trades.

## 8. Persistence contract

- Account balances and daily counters survive restart.
- Active trades and closed trade history survive restart.
- Signal send counts and reminder state survive restart.
- Supabase is production-authoritative when configured through `SUPABASE_URL` and `SUPABASE_KEY`.
- SQLite is the local runtime cache/fallback.
- State transitions must be idempotent.
- No pending-sweep state may be introduced.

## 9. Telegram contract

- BUY uses green direction icon; SELL uses red.
- Freshness is independent: `✅` FRESH and `⚠️` STALE.
- User-facing asset names should use friendly names where mappings exist and must not leak provider tickers unnecessarily.
- Signal messages contain strategy, asset/symbol, market, direction, timeframe, status/age, candle close, account, entry, SL, TP, quantity and risk.
- Signal rejection messages explain why no message/trade was dispatched.
- Reminder is one hour after initial send and cannot create a third send.
- `/start` / `/menu` is the command center message. The dashboard URL is an operational navigation item and should be configurable rather than hard-coded into trading logic.

## 10. Runtime contract

Canonical flow:

`provider -> validation -> canonical candles -> strategy -> completion -> freshness -> duplicate gate -> account/risk -> persistence -> Telegram/dashboard`

No strategy bypasses this pipeline.

`/ping` must remain lightweight: it must not scan markets, send signals or mutate trading state.

Render starts the service with `pip install -e .` and `python main.py`. Runtime secrets are environment-only.

## 11. Dashboard/API contract

The current runtime dashboard payload contains:
- `system`: status, mode, timezone, timeframe, leverage
- `rules`: account size, risk per trade, independent account limits, freshness
- `universe`: fixed 19-asset live list
- `accounts`: account balances, planned risk, limits and remaining capacity
- `signals`: strategy, symbol, direction, timestamp and reason
- `trades`: active and historical trade rows
- `counts`: signal/trade/open/closed counts
- `generated_at`: snapshot timestamp

The frontend must remain presentation-only. It must not calculate strategy signals, entries, SL, TP, position sizing or execution risk.

## 12. Dashboard rebuild decisions

The current dashboard is being replaced as a coherent presentation layer rather than patched piecemeal.

Approved UX principles:
- Mobile-first and responsive.
- Compact cards by default.
- Signal/trade/history cards are collapsed by default.
- Tapping a card expands it to reveal the complete information required for that object.
- Strong visual distinction for BUY, SELL, FRESH, STALE, OPEN and CLOSED.
- Overview should answer: Is the system healthy? What is happening now? What risk is open? What is the latest signal?
- Detailed operational information belongs in expandable cards or Tools.
- Smooth but restrained animation.
- Respect `prefers-reduced-motion`.
- Accessible focus states and semantic buttons.
- Safe HTML rendering; all backend strings are escaped before insertion.
- Loading, empty and error states are explicit.
- No raw developer diagnostics on the main overview.
- Theme/style controls may remain, but the UI must not sacrifice readability for decoration.
- IST is the dashboard display timezone.

## 13. Files approved for this dashboard implementation

### Rewrite completely
- `dashboard.html` — new semantic UI shell.
- `app.js` — new dashboard controller/rendering/interaction layer.
- `styles.css` — new responsive visual system and animation layer.

### Small functional update
- `telegram.py` — add the configured public dashboard link to the `/start`/`/menu` command-center message without changing approved signal templates or trading behavior.

### Add
- `MULTIBOT2_CANONICAL_NOTES.md` — this canonical project memory/contract.

### Do not change for this UI pass
- `strategies.py`
- `trading.py`
- `candles.py`
- `signal_gate.py`
- `trendpulse_runtime.py`
- `trendpulse_service.py`
- `sweep_engine.py`
- `sweep_service.py`
- `db.py`
- `reminders.py`
- `market_data.py`
- `main.py`
- `dashboard.py`
- `backtest.py`
- deployment/CI files

Those files remain protected unless a test or audit proves a separate runtime defect. The dashboard rebuild must not be used as a reason to alter trading logic.

## 14. Regression requirements

Before calling the work complete:
- Python compilation/imports must pass.
- Full pytest suite must pass.
- Existing dashboard UI contract tests must pass.
- `/`, `/dashboard`, `/api/dashboard` and `/ping` must remain valid.
- Dashboard must work with empty data and populated data.
- Expand/collapse must work on touch and keyboard.
- Theme controls must remain functional.
- No prohibited frontend trading calculations may be introduced.
- Telegram signal templates must remain unchanged.
- Restart/persistence behavior must remain unchanged.

## 15. Non-negotiable principle

**One coherent implementation, not surgical patches.**

If a presentation concern requires changing an API contract, stop and document that contract change first. Never hide a backend/rules change inside a UI rewrite.
