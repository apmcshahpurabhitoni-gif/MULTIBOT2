# MULTIBOT2 v3.0.0 — Re-audit & Fix Report

## Scope

This release was refactored from the uploaded MULTIBOT2 repository into a registry-driven, plug-and-play strategy architecture.

## Completed

- 🧩 Automatic strategy discovery under `strategies/`.
- 🧠 Stable `Strategy`, `StrategyManifest` and `Signal` contracts.
- 🔄 Shared strategy lifecycle in `strategy_service.py`.
- 📡 Strategy-owned Yahoo data requirements/timeframes.
- 🛡️ Shared risk/account enforcement retained.
- ⏳ Shared one-hour freshness retained.
- 🔁 Shared two-send signal identity retained.
- 💾 Supabase/SQLite persistence retained.
- 💬 Telegram made strategy-agnostic.
- 📊 Dashboard backend payload now exposes the strategy catalog.
- 🧪 Backtesting made registry-driven with 11 common metrics and a 0–100 rating.
- 📝 Strategy version and parameter snapshots are represented in signal/trade/backtest data.
- 📚 Added README, AI rebuild specification and strategy developer guide.

## Built-in strategies

### Adaptive Trend Momentum

- BTC-USD and GC=F only.
- 1D candles.
- EMA 20/50, 40-day momentum, 20-day Donchian, ATR 14 and volatility filter.
- ATR-based initial stop, 2R target and optional ATR trailing policy.

### Sweep V2

- Preserved as a plug-in.
- Strict two-sided sweep + final-close classification.
- Existing canonical asset/timeframe schedule retained.

## Verification

The canonical suite passes locally:

```text
80 tests passed
```

Python compileall also passes.

The repository contains no active legacy strategy runtime files and no legacy strategy references in runtime Python/JS/HTML/YAML.

## Remaining planned work

The dashboard **visual redesign and Strategy Manager controls** are intentionally the next task. The backend already exposes strategy manifests/parameters so that UI can be made metadata-driven rather than hardcoded per strategy.
