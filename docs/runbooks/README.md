# Runbooks

Operator runbooks for AutoSRE alerts. Each describes **what a human operator
should do** to triage, mitigate, and verify recovery.

> **No automated remediation.** AutoSRE only detects, measures, and notifies.
> Nothing in these runbooks is executed automatically — every step is performed
> by an on-call engineer who decides whether and when to act.

## Alert → runbook map

| Alert (Prometheus) | Severity | Runbook |
|--------------------|----------|---------|
| `HighLatencyP95` | warning | [high-latency](high-latency.md) |
| `HighErrorRate` | critical | [high-error-rate](high-error-rate.md) |
| `ServiceDown` | critical | [service-down](service-down.md) |
| `CircuitBreakerOpen` | warning | [circuit-breaker-open](circuit-breaker-open.md) |
| `RateLimitingSpike` | warning | [rate-limit-spike](rate-limit-spike.md) |
| `ErrorBudgetFastBurn` | critical | [error-budget-burn](error-budget-burn.md) |
| `ChaosModeActive` | info | [chaos-active](chaos-active.md) |

## First action for every alert

Because this platform's failures are most often produced by chaos experiments,
**step 1 is always: check whether a chaos experiment is active.**

```bash
# Per service (api:8000, auth:8001, worker:8002)
curl -s localhost:8000/chaos/status
curl -s 'localhost:8000/failures?limit=20'
```

If chaos is active and unexpected, disabling it is usually the fastest
mitigation: `curl -XPOST localhost:8000/chaos/reset`.

## Standard tools

- **Grafana** (`:3000`): RED, Reliability, Chaos, Incident dashboards
  (use the `$job` selector to pick a service).
- **Prometheus** (`:9090`): `/alerts` for firing alerts, `/graph` for ad-hoc PromQL.
- **Failure log**: `GET /failures` on each service.
- **Network daemon** (`:2112/metrics`): `network_*` for DNS/TCP/HTTP reachability.
