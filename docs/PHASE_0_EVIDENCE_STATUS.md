# Phase 0 Evidence Status

## Confirmed

- User approved the historical TrendPulse baseline as canonical evidence baseline, with conflicts resolved before implementation.
- TrendPulse freshness is locked to `<=60m FRESH` and `>60m STALE`. There is no 6-hour freshness threshold.
- User supplied the historical Telegram formats from actual `main.py`; these are recorded verbatim as implementation evidence.
- Project-wide cost constraint is locked to ₹0 recurring cost.
- TrendPulse implementation is intentionally deferred until the user supplies the TrendPulse code.

## Not yet proven

- Exact TrendPulse entry rule.
- Exact TrendPulse SL rule.
- Exact TrendPulse TP rule.
- Exact TrendPulse new-signal/repeat/dedup behavior.
- Exact missing-data fail-safe behavior as historical strategy contract.
- Final TrendPulse market universe.
- Formal Telegram V1 message identifiers/approval status.
- Free provider selection.
- Free hosting/runtime selection.
- Final objective 15-stock universe.
- Risk sizing, fees and slippage.

## Gate
NOT PASSED.

Do not implement unresolved strategy behavior. Do not move to the next phase until the formal phase gate requirements are met.
