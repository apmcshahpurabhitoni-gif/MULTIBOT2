# MULTIBOT2 — Final Repository Recheck & Fix Report

## Baseline
Audited the uploaded `MULTIBOT2-main.zip` as the source repository and reconciled it with the previously prepared fixed files and the locked MULTIBOT2 canonical rules.

## Inconsistencies found before this pass

1. **Universe mismatch**
   - Configuration had 19 live assets, while dashboard/Telegram/main reporting still contained NSE-15/30-signal assumptions.
   - Some runtime layers still treated every symbol as NSE.

2. **Yahoo symbol routing**
   - Several paths appended `.NS` or forced `market=NSE`.
   - This would corrupt Gold (`GC=F`), Bitcoin (`BTC-USD`), NIFTY (`^NSEI`) and BANK NIFTY (`^NSEBANK`) routing.

3. **TrendPulse global candle completion**
   - Global Yahoo 1H data was consumed without a canonical completion boundary.
   - A forming global candle could reach strategy evaluation.
   - The global path was changed to build close-stamped 1H candles from complete 30-minute observations on the locked `:30` boundary.

4. **NSE historical-data limitation**
   - NSE 1-minute data cannot be assumed to exist for arbitrary 30d/60d/90d/1y periods.
   - Runtime now uses exact 1-minute construction for short live windows and falls back to Yahoo native 1H data, canonicalized to the locked NSE close timestamps, for longer periods.

5. **Sweep input/data-boundary mismatch**
   - SweepService was passing the TrendPulse 1H dataframe into Sweep V2.
   - Sweep V2 now receives raw market data at the required provider resolution:
     - NSE: 1m live/raw or 1H historical
     - Global: 30m raw or 1H compatible historical input.

6. **Sweep schedule alignment**
   - Global Sweep schedules were defined at `:30`, but the data path did not guarantee `:30`-anchored candles.
   - Sweep V2 now constructs complete 4H global candles from the explicit configured schedule boundaries.

7. **Sweep SL source**
   - Sweep dispatch could fall back to the latest dataframe candle rather than the actual detected sweep candle.
   - When a live sweep is detected, SL now uses the detected sweep candle's high/low (the sweep extreme).

8. **Sweep backtest lookback**
   - The previous 3-day schedule window could silently discard most of a long backtest.
   - Backtest now expands the Sweep schedule lookback to cover the entire supplied dataset.

9. **Weekend runtime**
   - The scanner was blocked by `weekday() < 5`, preventing global Gold/BTC scans on weekends.
   - Runtime now scans continuously; closed NSE markets naturally produce no fresh NSE signal.

10. **Version inconsistency**
    - Different files reported 1.0.8, 1.1.0 and 2.0.0.
    - The repository is now aligned to `2.0.0`.

11. **Startup/dashboard messaging**
    - Startup and dashboard text contained stale universe/release statements.
    - Startup now announces the locked 19-asset runtime and canonical pipeline.
    - Default dashboard link is `https://lead-generator-zzty.onrender.com/dashboard`.

12. **Documentation drift**
    - Canonical notes and README described the universe/backtest path inconsistently.
    - Documentation now records the 19-asset universe, global Sweep boundaries and backtest limitations.

13. **Test drift**
    - Tests still encoded the old assumption that BTC was outside the live universe.
    - Tests were updated to assert all 19 assets and to cover global `:30` candle construction, NSE provider-hourly canonicalization and Sweep V2 schedule behavior.

## Final architecture

### Live universe — exactly 19
- 15 NSE stocks
- NIFTY 50
- BANK NIFTY
- Gold
- Bitcoin

### TrendPulse
- All 19 assets
- completed 1H signal
- confirmed 4H filter
- freshness exactly 1 hour
- no directional signal = no trade/message
- SL = 1.5 ATR
- TP = 3 ATR

### Sweep V2
- NIFTY/BANK NIFTY: 1H
- NSE stocks: 4H session contract
- Gold: 4H at 02:30/06:30/10:30/14:30/18:30/22:30 IST
- Bitcoin: 4H at 01:30/05:30/09:30/13:30/17:30/21:30 IST
- strict two-sided sweep
- final-close classification
- market entry
- sweep extreme SL
- 1:2 target
- no pending sweep

### Persistence
- Supabase authoritative when configured
- SQLite fallback/local cache
- duplicate identity survives restart
- maximum two sends
- one-hour reminder

### Dashboard
- presentation only
- 19-asset universe
- expandable signal/trade/history cards
- backend owns strategy/risk/freshness calculations
- light/dark/modern/neo presentation retained

## Validation performed

- Python syntax/compile validation: PASS
- Full pytest suite: PASS
- Test count: 100
- Tests were run with a local `yfinance` import stub because this execution environment does not provide the external Yahoo package/network. This validates repository behavior and interfaces but is not a live Yahoo connectivity test.
- Static stale-reference scan: PASS for old `NSE-15`, `1.1.0`, `1.0.8` and `30 signals` references.
- Repository cache/compiled artifacts are excluded from the final ZIP.

## Important deployment note

The final repository is source files, not an installer and not a patch script. Replace/deploy the repository files as provided. Render should install dependencies from `pyproject.toml` and start with the configured `render.yaml` command.

The final release should still be considered a **paper-trading release**. Live Yahoo and Telegram connectivity must be smoke-tested in the deployed environment because this offline execution environment cannot prove external service availability.
