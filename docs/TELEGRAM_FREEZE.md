# Telegram Freeze Record — Phase 0

## Status
BLOCKED / UNRESOLVED.

`09_TELEGRAM_MESSAGE_REGISTRY.md` is the only authority for user-facing Telegram copy. The supplied recovered material contains the required message IDs and structural requirements, but explicitly says the complete verbatim historical approved copy is not reliably available.

## Required registry IDs
- MSG-SWEEP-BUY-V1
- MSG-SWEEP-SELL-V1
- MSG-SWEEP-NEUTRAL-V1
- MSG-SWEEP-STALE-V1
- MSG-SWEEP-REMINDER-V1
- MSG-SWEEP-CANDLE-WARNING-V1
- MSG-SWEEP-DATA-MISMATCH-V1
- MSG-TRENDPULSE-BUY-V1
- MSG-TRENDPULSE-SELL-V1
- MSG-TRENDPULSE-NEUTRAL-V1
- MSG-TRENDPULSE-STALE-V1
- MSG-TRENDPULSE-REMINDER-V1
- MSG-TRENDPULSE-WARNING-V1

## Freeze requirement
For each entry record ID, status, exact text, exact emoji, line order, allowed variables, number formatting, trigger, freshness, reminder, forbidden additions, snapshot, approval reference and version.

## Structural order currently known
Header → direction/status → timeframe → strategy context → candle close → paper trade → entry → stop → target → approved optional fields → warning.

This structure must not be mistaken for approved wording. No fabricated text may enter the registry and be called approved.

## Change control
After approval, any wording/emoji/label/ordering/field/formatting change requires Change Request → explicit approval → new message version → snapshot update → CI.
