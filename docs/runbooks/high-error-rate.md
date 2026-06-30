# Runbook: High Error Rate

| Field | Value |
|-------|-------|
| **Alert** | `HighErrorRate` |
| **Severity** | critical |
| **SLO** | error rate < 5% (alert at > 5% for 5m) |
| **Services** | api (per-`$job`) |

> Operator actions only. No step here runs automatically.

## Symptoms
- `api:error_rate > 0.05` for 5 minutes.
- Clients receive `5xx` responses (`500`, `502`, `503`).

## Client-code semantics (important for triage)
- **500** — unhandled error inside the service, or a chaos-injected error.
- **502** — a downstream dependency call failed (e.g. `auth` returned errors).
- **503** — a circuit breaker is open (fast-failing to protect the system), or
  rate limiting / readiness degraded.

## Dashboards & queries
- **Grafana → RED** (`$job=api`): Error Rate, Request Rate by Status Code.
- **Grafana → Incident**: Error Spikes.
- PromQL: `api:error_rate`,
  `sum by (status) (rate(http_requests_total{job="api"}[5m]))`.

## Triage (investigate)
1. **Check for chaos:** `curl -s localhost:8000/chaos/status` and
   `curl -s 'localhost:8000/failures?source=chaos'`. Error injection active?
2. Break down by status code (panel above). Which code dominates?
   - Mostly `502/503` → dependency problem → check `auth`.
   - Mostly `500` → in-service errors or injected errors;
     check `http_exceptions_total` for unhandled exceptions.
3. Check the breaker: `curl -s localhost:8000/breaker/status` — any OPEN?
4. Check the failing dependency directly (`auth` RED dashboard, `/health`,
   `/ready`).

## Likely causes
- Chaos error injection on this service or a dependency.
- A downstream dependency outage (see [INC-2026-003](../postmortems/2026-06-26-auth-dependency-outage.md)).
- A code defect causing unhandled exceptions (`http_exceptions_total` rising).

## Mitigation (operator actions)
- If chaos-induced and unintended: `curl -XPOST <service>/chaos/reset`.
- If a dependency is the cause, follow
  [circuit-breaker-open](circuit-breaker-open.md) /
  [service-down](service-down.md) and engage the dependency owner.
- If a recent deploy introduced the errors, initiate a **manual** rollback per
  your deploy process and notify the owning team.

## Verify recovery
- `api:error_rate` back under 1%.
- Status-code panel shows `5xx` returning to baseline.
- `HighErrorRate` resolves.

## Escalation
Critical alert: if not clearly a controlled experiment, open an incident
immediately and page the service owner.

## Related
[circuit-breaker-open](circuit-breaker-open.md) · [service-down](service-down.md) · [chaos-active](chaos-active.md)
