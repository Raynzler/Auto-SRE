# Runbook: Error Budget Fast Burn

| Field | Value |
|-------|-------|
| **Alert** | `ErrorBudgetFastBurn` |
| **Severity** | critical |
| **Trigger** | burn rate > 14.4x on both 1h and 5m windows for 2m |
| **Services** | api |

> Operator actions only. No step here runs automatically.

## What it means
The API is consuming its 30-day error budget ~14.4x faster than sustainable —
at this pace the entire budget is gone in ~2 days. The multi-window condition
(1h **and** 5m) means the burn is both significant and happening *right now*,
not a stale artifact.

## Dashboards & queries
- **Grafana → Reliability**: Error Budget Remaining (gauge), Burn Rate (5m vs 1h).
- PromQL: `api:error_budget_burn_rate:1h`, `api:error_budget_burn_rate:5m`,
  `api:error_budget_remaining`, `api:error_rate`.

## Triage (investigate)
1. A fast burn is driven by errors — go to [high-error-rate](high-error-rate.md)
   and identify what is producing `5xx`.
2. Check how much budget remains (`api:error_budget_remaining`). Near 0 or
   negative means the SLO is already at/over the line — treat as urgent.
3. Establish whether the burn is a controlled experiment (chaos) or organic.

## Mitigation (operator actions)
- Resolve the underlying error source (this alert is downstream of error rate —
  fixing errors stops the burn). Follow the error-rate runbook.
- If organic and tied to a recent change, perform a **manual** rollback.
- Communicate budget status to stakeholders; an exhausted budget is a signal to
  prioritize reliability work over feature launches (policy decision, human-made).

## Verify recovery
- Both burn-rate series drop below 1.0.
- `api:error_budget_remaining` stops declining.
- `ErrorBudgetFastBurn` resolves.

## Escalation
Critical: open an incident and engage the service owner; track budget impact in
the postmortem.

## Related
[high-error-rate](high-error-rate.md)
