# Runbook: High Latency

| Field | Value |
|-------|-------|
| **Alert** | `HighLatencyP95` |
| **Severity** | warning |
| **SLO** | p95 < 500ms (alert at > 750ms for 5m) |
| **Services** | api (per-`$job`) |

> Operator actions only. No step here runs automatically.

## Symptoms
- `api:latency:p95 > 0.75` for 5 minutes.
- Users report slow responses; requests succeed but are sluggish.

## Dashboards & queries
- **Grafana → RED** (`$job=api`): Latency Quantiles, p95 by Endpoint.
- PromQL: `api:latency:p95`, `api:latency:p99`,
  `histogram_quantile(0.95, sum by (le,endpoint) (rate(http_request_duration_seconds_bucket{job="api"}[5m])))`

## Triage (investigate)
1. **Check for chaos first:** `curl -s localhost:8000/chaos/status`. If
   `latency.enabled=true`, this is almost certainly the cause.
2. Is latency uniform across all endpoints, or isolated to one? Uniform →
   middleware/dependency-wide; isolated → a specific handler or downstream.
3. Check the dependency: is `auth` slow? Look at `auth` p95 on the RED dashboard
   (`$job=auth`) and `network_latency_seconds{target="auth"}` from the daemon.
4. Check saturation: `http_requests_in_progress` (concurrency climbing).

## Likely causes
- Active latency chaos experiment (most common here).
- Slow downstream dependency (auth identity-provider latency).
- Resource saturation (an active CPU/memory chaos run, or real load).

## Mitigation (operator actions)
- If a chaos experiment is responsible and unintended:
  `curl -XPOST localhost:8000/chaos/reset`.
- If a downstream dependency is slow, follow
  [circuit-breaker-open](circuit-breaker-open.md) and engage that service's
  owner.
- If organic load, notify the service owner; consider manually scaling capacity
  (human-initiated) and shedding non-critical traffic. **AutoSRE will not scale
  automatically.**

## Verify recovery
- `api:latency:p95` back under 0.5s.
- `HighLatencyP95` resolves in Prometheus `/alerts`.

## Escalation
If latency is organic (not chaos) and persists > 15 min, page the service owner
and open an incident; reference [INC-2026-001](../postmortems/2026-06-22-latency-slo-violation.md).

## Related
[high-error-rate](high-error-rate.md) · [chaos-active](chaos-active.md)
