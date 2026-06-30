# Runbook: Chaos Mode Active

| Field | Value |
|-------|-------|
| **Alert** | `ChaosModeActive` |
| **Severity** | info |
| **Trigger** | `max by (job) (chaos_active) > 0` for 1m |
| **Services** | api, auth, worker |

> Operator actions only. No step here runs automatically.
> This is **informational**, not a page. Its purpose is *attribution*: it tells
> you degraded SLIs may be an intentional experiment rather than a real
> incident.

## What it means
One or more chaos modes (latency, errors, cpu, memory) is active on the named
`{{ $labels.job }}`. Expect correlated symptoms (latency/error alerts) during
the experiment window.

## Triage (investigate)
1. Confirm scope: `curl -s localhost:<port>/chaos/status` for the affected
   service (which mode, what parameters).
2. Confirm intent: is there a scheduled game-day? Check `/failures?source=chaos`
   for who/what enabled it and when.
3. **Before treating any concurrent critical alert as a real incident,** check
   whether this chaos experiment fully explains it.

## Mitigation (operator actions)
- **Expected experiment:** no action — let it run. Annotate the dashboards if
  helpful.
- **Unexpected / forgotten experiment:** disable it —
  `curl -XPOST localhost:<port>/chaos/reset`.
- If a chaos experiment is causing customer impact beyond its intended blast
  radius, stop it immediately (reset) and treat as an incident.

## Verify recovery
- `chaos_active{job=...}` returns to 0 for all types.
- `ChaosModeActive` resolves.

## Related
[high-latency](high-latency.md) · [high-error-rate](high-error-rate.md) · [circuit-breaker-open](circuit-breaker-open.md)
