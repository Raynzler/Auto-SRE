# Runbook: Service Unavailable

| Field | Value |
|-------|-------|
| **Alert** | `ServiceDown` |
| **Severity** | critical |
| **Trigger** | `up{job=~"api\|auth\|worker"} == 0` for 1m |
| **Services** | api, auth, worker |

> Operator actions only. No step here runs automatically.

## Symptoms
- A service's scrape target is down (`up == 0`): Prometheus cannot reach
  `/metrics`. The alert names the affected `{{ $labels.job }}`.
- Note: a service can be *degraded* (returning errors) while `up == 1` — that is
  [high-error-rate](high-error-rate.md), not this runbook.

## Dashboards & queries
- **Grafana → Incident**: Service Health (`min(up{job=~"api|auth|worker"})`).
- **Prometheus → /targets**: see which target is DOWN and the scrape error.
- Network daemon: `network_failures_total{target="<svc>"}`,
  `network_tcp_connections_total{target="<svc>"}`.

## Triage (investigate)
1. Identify the affected service from the alert's `job` label.
2. Confirm reachability from the daemon's perspective:
   `curl -s localhost:2112/metrics | grep '<svc>'` — are DNS/TCP/HTTP checks
   failing?
3. Try the service's own endpoints directly:
   `curl -i localhost:<port>/health`. Connection refused → process down;
   timeout → hung/network.
4. Check the container: `docker compose ps`, `docker compose logs <svc> --tail=100`.

## Likely causes
- Container crashed or was OOM-killed (check logs for the exit/restart).
- Process hung (health endpoint not responding).
- Network/DNS issue between Prometheus and the target.

## Mitigation (operator actions)
- Read the logs to understand *why* it stopped before restarting — a blind
  restart can hide a crash loop.
- If safe, **manually** restart the service: `docker compose restart <svc>`.
  (This is a human decision; the platform does not auto-restart.)
- If a recent deploy is implicated, perform a **manual** rollback.
- If a dependency outage is cascading, see
  [service consumers] and [circuit-breaker-open](circuit-breaker-open.md).

## Verify recovery
- `up{job="<svc>"} == 1` in Prometheus `/targets`.
- `/health` returns 200; `/ready` returns 200.
- Network daemon failures for the target return to 0.
- `ServiceDown` resolves.

## Escalation
Critical: page the service owner immediately if the cause is not obvious or a
restart does not hold.

## Related
[high-error-rate](high-error-rate.md) · [circuit-breaker-open](circuit-breaker-open.md)
