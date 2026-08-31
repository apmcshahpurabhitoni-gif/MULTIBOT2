# ZERO-COST REQUIREMENT

## Status
LOCKED BY USER

MULTIBOT2/MAVIS must be buildable, testable, deployable and operable with **₹0 recurring infrastructure/API cost**.

### Prohibited unless the user explicitly changes this requirement
- Paid hosting or paid compute
- Paid database tiers
- Paid market-data subscriptions/APIs
- Paid monitoring services
- Paid domains
- Mandatory paid upgrades
- Any architecture whose normal operation requires payment

### Required selection rule
Provider, market-data, database, hosting, monitoring, CI/CD and infrastructure choices must be researched against genuine free availability, expected workload, limits, reliability, historical coverage, latency, terms of use and operational fit.

### Safety rule
Design around free-tier limits from the beginning. Add rate/usage safeguards so the system fails safely or degrades rather than silently creating a bill.

### Current decisions
- Previous paid Dhan Data API recommendation: REJECTED under this requirement.
- Previous Render + Supabase Pro recommendation: REJECTED under this requirement.
- Free-only provider research: OPEN.
- Free-only hosting/runtime research: OPEN.

No paid dependency may be introduced without explicit user approval.
