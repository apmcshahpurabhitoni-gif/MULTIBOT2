# Free Infrastructure Research — Phase 0

## Hard constraint
All selected components must have a genuine zero-cost operating path for the expected workload. Paid recommendations are rejected unless the user explicitly changes the project requirement.

## Current status
RESEARCH REQUIRED — no provider or hosting choice is final yet.

## Evaluation criteria
- Genuine free availability
- Expected workload within free limits
- Historical market coverage
- Intraday candle availability and session boundaries
- Reliability and latency
- API/accessibility requirements
- Rate limits
- Terms of use
- Persistence requirements
- Monitoring availability
- Deployment simplicity
- Safe failure when limits are reached

## Explicit rejections
- Dhan Data API paid tier: rejected under the ₹0 rule.
- Supabase Pro: rejected because it is paid.
- Render paid compute: rejected if normal operation requires payment.

## Architecture principle
Prefer open-source/local components where practical, and free public/serverless infrastructure only where its free limits are sufficient. Do not couple the system to a paid upgrade path.

## No premature selection
A final provider/hosting decision must wait for the exact TrendPulse market universe and workload requirements. Until then, the project records candidates and constraints only.
