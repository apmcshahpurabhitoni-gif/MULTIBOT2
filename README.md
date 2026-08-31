# MULTIBOT2 — Mavis Trading Bot

Clean-slate rebuild.

## Rules

- This repository is the canonical implementation repository for the new bot.
- The previous Mavis repository is historical reference only and is not a dependency.
- Build one small file at a time.
- Each file must have a single responsibility.
- Strategy logic has one canonical implementation.
- Telegram, dashboard, persistence, and backtest consume canonical results; they do not reimplement strategy logic.
- Paper trading only until live trading is explicitly approved.
- CI must be read-only and must never mutate source or push to `main`.
- No feature is complete without tests and actual CI evidence.

## Current build

First implementation file: `trendpulse.py`.

Subsequent files will be added only after the current file is reviewed and tested.
