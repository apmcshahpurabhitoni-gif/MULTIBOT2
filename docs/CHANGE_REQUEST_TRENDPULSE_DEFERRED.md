# Change Request — Defer TrendPulse Implementation

## ID
CR-001

## Date
2026-08-31

## Status
APPROVED — implementation deferred

## Requirement
Continue building the Mavis platform while leaving TrendPulse strategy implementation until the user supplies the TrendPulse code/authoritative definition.

## Context
The user explicitly instructed: “I give TrendPulse code later; leave it now but build remaining.” The repository must not invent TrendPulse business logic.

## Decision
TrendPulse implementation remains deferred. Non-TrendPulse foundation and locked Sweep work may proceed in phase order. TrendPulse-dependent behavior must remain blocked until the authoritative TrendPulse definition/code is supplied and frozen.

The canonical freshness requirement is 1 hour: <=60 minutes is FRESH; >60 minutes is STALE. There is no 6-hour freshness threshold.

## Constraints
- Do not invent TrendPulse formula, parameters, entry, SL, TP, signal/repetition rules, missing-data behavior, or Telegram copy.
- Do not implement a substitute TrendPulse strategy.
- Do not skip phase gates for work that is otherwise phase-dependent.
- Do not claim a phase passed without executable tests, regression, CI completion, diff review, and handoff evidence.

## Affected areas
Phase 1–3 work may proceed where independent of TrendPulse. Phase 4 remains blocked pending TrendPulse authority. Later phases may only receive infrastructure that is explicitly independent of unresolved TrendPulse/Telegram/provider decisions.

## Approval evidence
User instruction in the project conversation on 2026-08-31.
