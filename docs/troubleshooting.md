# Troubleshooting

Common issues running AutoSRE locally.

## `make up` fails to build
- **Docker not running** — start Docker Desktop / the daemon, then retry.
- **Port already in use** (8000/8001/8002/9090/3000/2112) — stop the conflicting
  process or change the host port mapping in `docker-compose.yml`.
- **Stale build cache** — `make clean && make up`.

## A service shows `unhealthy` in `make ps`
- Check its logs: `docker compose logs <service>` (logs are JSON; look at `msg`).
- `/ready` returns **503 on purpose** when error chaos is active or a dependency
  breaker is open — that's degraded, not broken. Run `make chaos-reset`.
- The **network-daemon** and **grafana** have no in-container health probe
  (distroless / no probe tool); judge them via Prometheus `up{job=...}` instead.

## Orders return 502 or 503
- **502** = the auth dependency call failed. Check `auth` logs / health.
- **503** = the api→auth **circuit breaker is open** (it opened after repeated auth
  failures). See [circuit-breaker-open](runbooks/circuit-breaker-open.md). It
  self-recovers ~30s after auth is healthy; fix auth (e.g. `make chaos-reset`).

## Requests return 429
- Rate limit hit. Defaults are 10 rps / 20 burst per client. Raise via
  `RATE_LIMIT_RPS` / `RATE_LIMIT_BURST` (see `.env.example`) and restart.

## Prometheus shows targets DOWN
- Status → Targets in the Prometheus UI shows the scrape error.
- Within Compose, services resolve by name (`api:8000`, etc.); from your host use
  `localhost`. A target down usually means that container isn't healthy yet —
  give it the `start_period`, or check its logs.

## Grafana dashboards are empty / "No data"
- Generate traffic first: hit `/orders` (or `make chaos`).
- Some panels use **recording rules** that need a couple of evaluation intervals
  (~15–30s) after startup before they have data.
- Error-budget panels use long windows and need enough history (and Prometheus
  retention ≥ the SLO window).
- Confirm the datasource: Grafana → Connections → Prometheus should be
  provisioned and default.

## Alerts never fire
- Alerts have a `for:` duration (e.g. 5m) — they sit *pending* before *firing*.
  See them at Prometheus `/alerts`.
- Notification routing (Alertmanager) is not wired yet; alerts are visible in the
  Prometheus UI only.

## Failure log (`/failures`) is empty
- Events are written best-effort. Confirm `FAILURE_LOG_PATH` is set and the data
  volume is writable (it is, by default — services run non-root and own
  `/app/data`). Trigger an event with `make chaos`.

## `make test` issues
- It runs in a container, so it needs Docker. For a local run use
  `make test-local` (needs Python + `pip install -r requirements-dev.txt`).
- `promtool` test self-skips when the binary isn't installed — that's expected.

## Tests/coverage artifacts cluttering the repo
- `make clean` removes `htmlcov/`, `coverage.xml`, `.coverage`, `.pytest_cache`
  (all git-ignored anyway).
