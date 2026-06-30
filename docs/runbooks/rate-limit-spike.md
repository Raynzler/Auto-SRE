# Runbook: Rate Limiting Spike

| Field | Value |
|-------|-------|
| **Alert** | `RateLimitingSpike` |
| **Severity** | warning |
| **Trigger** | `sum by (job) (rate(rate_limit_rejections_total[5m])) > 1` for 5m |
| **Services** | api, auth |

> Operator actions only. No step here runs automatically.

## Symptoms
- Clients receive `429 Too Many Requests` with a `Retry-After` header.
- `rate_limit_rejections_total` rising on the named `{{ $labels.job }}`.

## Dashboards & queries
- **Grafana → Reliability**: Rate Limiter Rejections.
- PromQL: `sum by (job) (rate(rate_limit_rejections_total[5m]))`,
  `sum by (job) (rate(rate_limit_requests_total[5m]))`.
- `curl -s localhost:8000/rate-limit/status` (config + active clients + sample).

## Triage (investigate)
1. Is this one noisy client or broadly distributed? Check
   `/rate-limit/status` → `sample` and `active_clients`. A single key dominating
   suggests one abusive client; many keys suggest organic traffic growth.
2. Compare rejection rate to total evaluated rate — what fraction is being
   throttled?
3. Is a load test or chaos/load generator running?

## Likely causes
- A single misbehaving client or hot loop hammering an endpoint.
- Legitimate traffic growth that has outgrown the configured `burst`/`rps`.
- A load test pointed at the service.

## Mitigation (operator actions)
- **Single abusive client:** identify the key from `/rate-limit/status`; address
  it out-of-band (contact the client owner, block upstream at a proxy). The
  limiter is already doing its job by shedding the excess.
- **Organic growth:** if throttling legitimate users, **manually** raise the
  limits by setting `RATE_LIMIT_RPS` / `RATE_LIMIT_BURST` and redeploying the
  service. This is a deliberate human change, not automatic.
- If a load test is the cause, stop the test.

## Verify recovery
- Rejection rate returns toward 0.
- `429`s stop appearing in the RED status-code breakdown.
- `RateLimitingSpike` resolves.

## Escalation
If the source is an external attack pattern (distributed, sustained), escalate
to security/networking to handle upstream of the application.

## Related
[high-error-rate](high-error-rate.md)
