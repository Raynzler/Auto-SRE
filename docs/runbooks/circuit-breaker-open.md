# Runbook: Circuit Breaker Open

| Field | Value |
|-------|-------|
| **Alert** | `CircuitBreakerOpen` |
| **Severity** | warning |
| **Trigger** | `circuit_breaker_state == 1` for 1m |
| **Services** | api, auth |

> Operator actions only. No step here runs automatically.
> **The open breaker is a symptom, not the disease.** It means a *dependency*
> is failing. Fix the dependency; the breaker recovers on its own.

## State encoding
`circuit_breaker_state`: `0=closed`, `1=open`, `2=half_open`. The alert labels
identify the owning service (`{{ $labels.job }}`) and the dependency
(`{{ $labels.name }}`), e.g. `job=api, name=auth`.

## Symptoms
- A breaker is OPEN; calls through it fast-fail with `503`.
- `circuit_breaker_rejections_total` is climbing.

## Dashboards & queries
- **Grafana → Reliability**: Circuit Breaker State timeline.
- PromQL: `circuit_breaker_state`, `rate(circuit_breaker_open_total[5m])`,
  `rate(circuit_breaker_rejections_total[5m])`.
- `curl -s localhost:8000/breaker/status` (shows state + `seconds_until_half_open`).

## Triage (investigate)
1. From the alert, identify which `name` (dependency) tripped on which `job`.
2. Investigate **that dependency**, not the breaker. For `name=auth`, go to the
   `auth` service: error rate, `/health`, `/ready`, and
   `curl -s 'localhost:8001/failures?source=chaos'`.
3. Confirm whether the dependency failures are chaos-induced or organic.

## Likely causes
- Dependency returning errors (chaos error injection, or a real outage —
  see [INC-2026-002](../postmortems/2026-06-24-auth-circuit-breaker-activation.md)).
- Dependency timing out (latency chaos or genuine slowness).

## Mitigation (operator actions)
- **Resolve the upstream dependency.** If chaos-induced:
  `curl -XPOST localhost:8001/chaos/reset` on the failing dependency.
- **Do not** attempt to force the breaker closed — that is by design not
  possible, and would defeat its protection. Once the dependency is healthy, the
  breaker probes via HALF_OPEN and closes after `success_threshold` successes
  (~30s `recovery_timeout`).
- Watch `seconds_until_half_open` in `/breaker/status` to know when the next
  probe will occur.

## Verify recovery
- `circuit_breaker_state{job,name}` returns to `0` (CLOSED).
- A `circuit_breaker` `event=closed` appears in `/failures`.
- Downstream `503`s stop; `CircuitBreakerOpen` resolves.

## Escalation
If the dependency owner is a different team and the outage is organic, page them;
the breaker is correctly protecting your service in the meantime.

## Related
[high-error-rate](high-error-rate.md) · [service-down](service-down.md)
