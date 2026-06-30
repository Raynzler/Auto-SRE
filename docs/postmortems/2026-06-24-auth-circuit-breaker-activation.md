# INC-2026-002: Auth circuit breaker activation

| Field | Value |
|-------|-------|
| **Status** | Resolved |
| **Severity** | SEV-2 |
| **Date** | 2026-06-24 |
| **Duration** | 8 min (detection → resolution) |
| **Services** | api, auth |
| **Authors** | On-call SRE |
| **Reproduce** | `curl -XPOST localhost:8001/chaos/errors -d '{"enable":true,"rate_percent":80}'` |

## Summary
An 80% error-injection experiment on the `auth` service caused the majority of
token validations to fail. The API's `auth` circuit breaker counted consecutive
failures, opened after 5, and began rejecting outbound auth calls — converting
slow/failed dependency calls into fast `503`s. `CircuitBreakerOpen` and elevated
API error rate alerted. The operator disabled auth error injection; the breaker
recovered through HALF_OPEN → CLOSED on its own probe traffic.

## Timeline
All times UTC.

| Time | Event |
|------|-------|
| 09:30 | Error chaos enabled on `auth` (`rate_percent=80`). `chaos_active{type="errors",job="auth"}` → 1. |
| 09:31 | `auth` returns injected 500s for ~80% of `/validate` calls. API `create_order` calls start failing → `502`s to clients. |
| 09:31 | API `auth` breaker `failure_count` rises; after 5 consecutive failures `circuit_breaker_state{job="api",name="auth"}` → 1 (OPEN). Event persisted (`source=circuit_breaker`, `event=opened`). |
| 09:32 | Breaker now rejects calls immediately → clients get fast `503` instead of slow `502`. `circuit_breaker_rejections_total` climbs. |
| 09:32 | `CircuitBreakerOpen` (warning) enters pending; `api:error_rate` rises above 5%. |
| 09:33 | `CircuitBreakerOpen` **fires** (`for: 1m`). On-call paged. |
| 09:34 | On-call opens **Reliability** dashboard: breaker state-timeline shows `api/auth` OPEN. `/breaker/status` confirms `state=open`. `/failures?source=chaos` shows the auth error experiment. |
| 09:36 | Operator disables it: `POST localhost:8001/chaos/reset`. Injected 500s stop. |
| 09:36 | After `recovery_timeout` (30s) the breaker allows a trial → HALF_OPEN; successful validations accrue. |
| 09:37 | 2 consecutive successes → breaker CLOSED (`event=closed`). API `503`/`502` stop. |
| 09:38 | Alerts resolve. Incident closed. |

## Customer impact
For ~5 minutes, order creation was largely unavailable: first as `502`s (auth
failing) and then `503`s (breaker open). Roughly 80% of order attempts failed
during the window. No data corruption — failed orders were never created.

## Root cause
A dependency (`auth`) was returning errors for the majority of requests. The
circuit breaker behaved **as designed**: it detected the failure rate, opened to
protect the API from piling up on a failing dependency, and shed load via fast
`503`s rather than slow cascading `502`s.

## Contributing factors
- The breaker's `failure_threshold=5` is intentionally sensitive; with an 80%
  error rate it opened within a couple of seconds.
- API returns `502` for raw auth failures but `503` once the breaker opens —
  two distinct client-facing codes for one underlying cause, which briefly
  confused triage.

## Detection
`CircuitBreakerOpen` fired ~3 minutes after injection. The breaker opening is
itself the detection signal — exactly the symptom-based alerting intent: we
alert on the protective mechanism activating, not on a CPU/host metric.

## Resolution
Operator-driven only:
1. Identified the open breaker via `GET /breaker/status` and the dashboard.
2. Confirmed the upstream cause via `GET /failures?source=chaos`.
3. Disabled auth error injection (`POST /chaos/reset` on `auth`).
4. Let the breaker self-recover (HALF_OPEN → CLOSED); verified on the dashboard.

See runbooks: [circuit-breaker-open](../runbooks/circuit-breaker-open.md),
[high-error-rate](../runbooks/high-error-rate.md).

## Lessons learned
- **Went well:** the breaker prevented the API from hanging on a failing
  dependency; recovery was automatic and observable; no operator action was
  needed to *fix* the breaker (only to stop the upstream cause).
- **Went poorly:** the `502` vs `503` distinction wasn't documented, slowing
  initial triage.

## Preventive actions
| Action | Type | Owner | Status |
|--------|------|-------|--------|
| Document the `502` (dependency error) vs `503` (breaker open) semantics in the API runbook | detect | SRE | Done |
| Add a Grafana panel correlating `circuit_breaker_state` with auth error rate | detect | Observability | TODO |
| Review whether `failure_threshold` should be tuned per dependency | prevent | SRE | TODO |
