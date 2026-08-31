# Telegram Implementation Evidence

## Source
User-supplied transcription of the actual historical `main.py` implementation.

## Evidence-backed formats

### Trade Signal
🟢/🔴 {Strategy} · {Asset} · ✅/⚠️
━━━━━━━━━━━━━━━━━━━━━━
🪙 Asset: "{Asset}" ("{Symbol}")
🌐 Market: {Market}
📊 Direction: LONG 📈 / SHORT 📉
⏱ Timeframe: {Timeframe}
━━━━━━━━━━━━━━━━━━━━━━
⏳ Signal Status: "✅ FRESH" / "⚠️ STALE" ({Age})
⏰ Candle Closed: "{Date Time IST}"
━━━━━━━━━━━━━━━━━━━━━━
💼 PAPER TRADE EXECUTED
━━━━━━━━━━━━━━━━━━━━━━
🏢 Account: "{ACCOUNT}"
📍 Entry: "{Currency}{Entry}"
🛑 Stop Loss: "{Currency}{SL}"
🎯 Take Profit: "{Currency}{TP}"
📦 Quantity: "{Quantity}"
💸 Risk: "₹{Risk}"
━━━━━━━━━━━━━━━━━━━━━━
ℹ️ ✅ FRESH = Closed ≤1h ago | ⚠️ STALE = Closed >1h ago
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Trade Closed
🟢 TRADE CLOSED — 🎉 WIN
━━━━━━━━━━━━━━━━━━━━━━
🪙 "{Asset}" | LONG / SHORT
🎯 Strategy: {Strategy}
🏢 Account: "{ACCOUNT}"
━━━━━━━━━━━━━━━━━━━━━━
📍 Entry: "{Entry}"
📈 Exit: "{Exit}"
🛑 SL Hit: "{SL}"
🎯 TP Target: "{TP}"
━━━━━━━━━━━━━━━━━━━━━━
💰 P/L: "{P/L}"
🏦 Balance: "₹{Balance}"
━━━━━━━━━━━━━━━━━━━━━━

For a losing trade, historical code changes the result to 💀 LOSS, uses 📉 for exit and 💸 for P/L.

### Midnight Reset
🌙 MIDNIGHT RESET
━━━━━━━━━━━━━━━━━━━━━━
📈/📉 Yesterday P/L: "{P/L}"
━━━━━━━━━━━━━━━━━━━━━━
🏦 Account Balances:
├ 🌐 Macro: "₹{Balance}"
├ 🇮🇳 Nifty: "₹{Balance}"
├ 🇺🇸 NY Session: "₹{Balance}"
└ 🔵 Sweep 4H: "₹{Balance}"
━━━━━━━━━━━━━━━━━━━━━━
🔄 Daily trade limits reset
🧹 Signal cache cleaned
━━━━━━━━━━━━━━━━━━━━━━

### Weekly Digest
🗓️ WEEKLY DIGEST
━━━━━━━━━━━━━━━━━━━━━━
📈/📉 Week P/L: "{P/L}"
📊 Trades: "{Total}" · ✅ "{Wins}W" · ❌ "{Losses}L" · 🎯 "{Win Rate}%"
━━━━━━━━━━━━━━━━━━━━━━
🏆 Best Symbol: "{Symbol}" ("{P/L}")
💔 Worst Symbol: "{Symbol}" ("{P/L}")
━━━━━━━━━━━━━━━━━━━━━━
🏦 Total Equity: "₹{Equity}"
━━━━━━━━━━━━━━━━━━━━━━

### /start Guide
🤖 MAVIS TRADING ENGINE — COMMAND CENTER
━━━━━━━━━━━━━━━━━━━━━━
📊 OPERATIONAL COMMANDS:
├ "/start" — Command guide & status
├ "/check" — Force immediate scan on all pairs
├ "/test" — Test data feeds & latency
├ "/summary" — Open trades & floating P/L
├ "/balance" — View virtual account equity
├ "/stats" — Strategy win-rate & P/L report
├ "/risk" — Portfolio exposure & 1R metrics
├ "/weekly" — 7-day performance digest
├ "/newspause" — Toggle high-impact news pause
├ "/refreshnews" — Force refresh news calendar
└ "/backtest" — Run strategy backtester
━━━━━━━━━━━━━━━━━━━━━━

### Error
⚠️ ERROR — {Context}
━━━━━━━━━━━━━━━━━━━━━━
❌ "{Error}"
━━━━━━━━━━━━━━━━━━━━━━

## Interpretation rule
These are evidence-backed historical implementation formats. They are not automatically labeled formal V1 message IDs. Do not infer missing messages or alter wording without user evidence/approval.
