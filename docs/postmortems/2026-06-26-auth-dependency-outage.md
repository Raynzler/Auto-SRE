# INC-2026-003: Auth dependency outage

| Field | Value |
|-------|-------|
| **Status** | Resolved |
| **Severity** | SEV-1 |
| **Date** | 2026-06-26 |
| **Duration** | 14 min (detection → resolution) |
| **Services** | api, auth |
| **Authors** | On-call SRE |
| **Reproduce** | `curl -XPOST localhost:8001/chaos/errors -d '{"enable":true,"rate_percent":100}'` |

## Summary
A full-outage game-day drove the `auth` service to return errors for **100%** of
token validations, simulating a hard dependency outage. `auth`'s own
readiness probe flipped to degraded and the API's `auth` circuit breaker opened
within seconds, failing all order creation with `503`. Because the API degraded
*fast* (breaker open) rather than hanging, the blast radius stayed contained to
the auth-dependent path. The operator disabled the injection and both services
recovered.

## Timeline
All times UTC.

| Time | Event |
|------|-------|
| 22:10 | Error chaos enabled on `auth` at `rate_percent=100`. `chaos_active{type="errors",job="auth"}` → 1. |
| 22:10 | `auth` `/ready` returns **503 (degraded)** because error injection is active. `up{job="auth"}` stays 1 (process alive) but `service_up` semantics flag degradation. |
| 22:10 | Every `/validate` returns an injected 500. API `auth` breaker opens almost immediately (5 consecutive failures). |
| 22:11 | 100% of `POST /orders` return `503`. `api:error_rate` → ~1.0. `CircuitBreakerOpen` pending. |
| 22:12 | `CircuitBreakerOpen` (warning) and `HighErrorRate` (critical) **fire**. On-call paged at SEV-1 (user-facing total failure of the order path). |
| 22:13 | On-call checks **Incident** dashboard: API error spikes, breaker OPEN, `auth` readiness degraded. `/failures` shows auth `errors_enable` at 100%. |
| 22:15 | Network daemon corroborates: `network_failures_total{target="auth",check="http"}` rising (auth `/health` still 200, but the operator notes HTTP checks vs. business errors differ). |
| 22:20 | Operator disables injection: `POST localhost:8001/chaos/reset`. `/validate` succeeds again; `auth` `/ready` returns 200. |
| 22:21 | API breaker: HALF_OPEN trial succeeds → CLOSED. `POST /orders` succeeds. |
| 22:24 | `HighErrorRate` and `CircuitBreakerOpen` resolve. Incident closed. |

## Customer impact
For ~10 minutes, **order creation was fully unavailable** (100% `503`). Other
API surfaces not dependent on auth (health/observability endpoints) were
unaffected. No data loss — no orders were partially created. This was the
highest-impact scenario of the three game-days because the dependency failure
was total rather than partial.

## Root cause
A critical dependency (`auth`) was completely unavailable for token validation.
The API correctly treated auth as a hard dependency for order creation and could
not complete orders without it.

## Contributing factors
- Order creation has a **hard** dependency on synchronous token validation with
  no cached/fallback path, so a total auth outage means a total order outage.
- `up{job="auth"}` remained 1 (the process and `/health` were alive); the real
  signal was business-level error rate and the breaker, not host liveness —
  reinforcing why symptom-based alerting matters.

## Detection
`HighErrorRate` (critical) fired ~2 minutes after the outage began. Detection
was fast because the failure was total. The combination of breaker-open + high
error rate + degraded `auth` readiness gave an unambiguous picture.

## Resolution
Operator-driven only:
1. Triaged via the Incident dashboard and `/failures` to find the auth outage.
2. Disabled the auth error injection (`POST /chaos/reset` on `auth`).
3. Allowed the API breaker to self-recover; verified order creation restored.

See runbooks: [service-down](../runbooks/service-down.md),
[circuit-breaker-open](../runbooks/circuit-breaker-open.md),
[high-error-rate](../runbooks/high-error-rate.md).

## Lessons learned
- **Went well:** fast, observable failure; the breaker kept the API responsive
  (fast `503`s) instead of exhausting it on a dead dependency; clear blast
  radius.
- **Went poorly:** no graceful degradation for order creation — auth being down
  means orders are 100% down. A short-lived token validation cache would have
  let recently-validated clients keep ordering.
- **Got lucky:** the outage was a controlled experiment; a real one at 22:10
  local could have had a slower human response.

## Preventive actions
| Action | Type | Owner | Status |
|--------|------|-------|--------|
| Design a token-validation cache (interface already exists via the storage/clients abstractions) to enable graceful degradation | mitigate | Platform | TODO |
| Add an explicit dependency-health row to the Incident dashboard (auth readiness + breaker + error rate) | detect | Observability | TODO |
| Document SEV-1 escalation path for total order-path outage | mitigate | SRE | Done |
