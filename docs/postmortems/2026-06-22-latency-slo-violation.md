# INC-2026-001: API latency SLO violation

| Field | Value |
|-------|-------|
| **Status** | Resolved |
| **Severity** | SEV-2 |
| **Date** | 2026-06-22 |
| **Duration** | 11 min (detection → resolution) |
| **Services** | api |
| **Authors** | On-call SRE |
| **Reproduce** | `curl -XPOST localhost:8000/chaos/latency -d '{"enable":true,"delay_seconds":1.5}'` |

## Summary
During a scheduled latency game-day, 1.5s of artificial latency was injected
into every API request. The API p95 climbed from ~70ms to ~1.55s, breaching the
500ms SLO and tripping the `HighLatencyP95` alert. No requests failed, but order
creation became unacceptably slow for ~9 minutes. The operator identified the
active chaos experiment from `/chaos/status` and disabled it; latency returned
to baseline within one scrape interval.

## Timeline
All times UTC.

| Time | Event |
|------|-------|
| 14:00 | Latency chaos enabled on `api` (`delay_seconds=1.5`). Event persisted to `/failures` (`source=chaos`, `event=latency_enable`). |
| 14:00 | `chaos_active{type="latency"}` → 1; `ChaosModeActive` (info) begins evaluating. |
| 14:02 | `api:latency:p95` crosses 0.75s. `HighLatencyP95` enters *pending* (`for: 5m`). |
| 14:07 | `HighLatencyP95` (warning) **fires**. On-call paged. |
| 14:07 | On-call opens the **RED** dashboard (`$job=api`): p50/p95/p99 all elevated uniformly across endpoints. |
| 14:09 | `ChaosModeActive` confirmed firing → strong signal this is an experiment, not an organic regression. `/chaos/status` shows `latency.enabled=true, seconds=1.5`. |
| 14:09 | Operator runs `POST /chaos/reset`. `chaos_active{type="latency"}` → 0. |
| 14:11 | p95 back under 100ms; `HighLatencyP95` resolves. Incident closed. |

## Customer impact
For ~9 minutes, every `POST /orders` took ~1.5s longer than normal (p95 ≈ 1.55s
vs. 500ms SLO). No errors were returned and no data was lost — the impact was
purely degraded responsiveness. Error budget was unaffected (availability SLI
held at 100%).

## Root cause
A deliberate chaos experiment injected a fixed 1.5s delay into the request path
via the shared `PrometheusMiddleware` chaos hook. The latency was uniform across
all endpoints because injection happens before routing.

## Contributing factors
- The experiment ran longer than the intended 5-minute window before the
  operator correlated the page with the active game-day.
- The `ChaosModeActive` alert is `info` severity and did not page, so the
  experiment context arrived only after the operator opened the dashboard.

## Detection
`HighLatencyP95` fired 7 minutes after injection (2 min for p95 to cross the
threshold + 5 min `for:` window). The SLO-aligned histogram buckets
(`le="0.75"`, `le="1.0"`) made the quantile estimate accurate at the threshold.

## Resolution
Operator-driven only:
1. Confirmed active experiment via `GET /chaos/status`.
2. Disabled all chaos via `POST /chaos/reset`.
3. Verified recovery on the RED dashboard and via alert resolution.

See runbook: [high-latency](../runbooks/high-latency.md).

## Lessons learned
- **Went well:** SLO-aligned buckets gave a precise p95; the `ChaosModeActive`
  signal correctly attributed the degradation to an experiment.
- **Went poorly:** no link from the page to the running game-day; the operator
  had to infer it.

## Preventive actions
| Action | Type | Owner | Status |
|--------|------|-------|--------|
| Add a chaos game-day calendar/annotation overlaid on Grafana dashboards | detect | Observability | TODO |
| Include "check `/chaos/status` first" as step 1 in the latency runbook | mitigate | SRE | Done |
| Evaluate a max experiment-duration convention for game-days | prevent | SRE | TODO |
