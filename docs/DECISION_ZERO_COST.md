# Decision — Zero-Cost Operating Requirement

## Status
APPROVED — USER LOCKED

## Requirement
Mavis/MULTIBOT2 must be buildable, testable, deployable and operable with **₹0 recurring cost**.

## Hard constraints
- No paid hosting.
- No paid database tier.
- No paid market-data API.
- No paid Telegram service.
- No paid domain requirement.
- No paid monitoring service.
- No mandatory paid CI/CD service.
- No broker or execution service is required for the paper-trading product.
- Free tiers may be used only when the expected workload remains within their published free limits without requiring an upgrade.
- The system must fail safely when a free-tier limit or provider limitation is reached; it must not silently create a bill.

## Consequence for previous conditional recommendations
Previous conditional recommendations for paid Dhan Data API, Render paid compute and Supabase Pro are rejected for this build because they conflict with this requirement.

## Provider/hosting decision
Provider and runtime remain open until a genuinely free option is verified against the actual market, historical, timeframe, reliability, latency, access and workload requirements.

## Scope protection
This decision does not authorize invention of TrendPulse rules, Telegram copy, risk rules, market universe or other unresolved business behavior.

## Evidence
User explicitly stated: "I want every thing to be free no cost every thing should be free."
