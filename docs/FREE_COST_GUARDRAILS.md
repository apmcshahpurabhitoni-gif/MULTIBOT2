# Free-Cost Guardrails

These controls are design requirements for the zero-cost project.

- Never add credentials for a paid service.
- Never make a paid API a required runtime dependency.
- Never assume a free trial is permanent free access.
- Track provider request limits in configuration.
- Fail closed when market data is unavailable or limits are reached.
- Do not automatically retry indefinitely.
- Do not deploy a service that can incur metered charges without explicit user approval.
- Prefer local/open-source persistence and computation where practical.
- Keep live trading disabled until all strategy, data, risk and safety gates pass.
