# Operations & Hardening

How AutoSRE is hardened for production-style operation, and the operational
assumptions behind those choices.

> **Charter reminder.** AutoSRE observes, measures, and notifies. It does **not**
> auto-remediate. Health probes *report* health; they do not trigger automatic
> restarts. There is intentionally **no restart policy** — restarts are an
> operator action (see [runbooks](runbooks/)).

## Environment validation
Every service calls `validate_env()` at startup (`autosre_shared.envcheck`) and
**fails fast** with a clear message if a known numeric variable (PORT,
RATE_LIMIT_*, WORKER_*, AUTH_DEP_LATENCY) is malformed, or a declared
`required_env` var is missing. A typo like `PORT=abc` stops the process at boot
instead of failing obscurely later.

## Secrets management
- Secrets are supplied via **environment variables only** — never baked into
  images or committed. `.env` is git-ignored; [`.env.example`](../.env.example)
  documents the variables.
- The only current secret is the Grafana admin password
  (`GRAFANA_ADMIN_PASSWORD`), wired through compose with a dev default.
- Future Postgres/Redis credentials follow the same pattern (`DATABASE_URL`,
  `REDIS_URL`), so no design change is needed to adopt them.

## Container hardening
| Control | Applied to | How |
|---------|-----------|-----|
| **Non-root** | api, auth, worker (uid 10001), network-daemon (distroless `:nonroot`, uid 65532) | `USER` in Dockerfile |
| **Read-only root FS** | api, auth, worker, network-daemon | `read_only: true` |
| **Writable scratch** | api, auth, worker | `tmpfs: /tmp`; `PYTHONDONTWRITEBYTECODE=1` |
| **Persistent writes** | api, auth, worker | named volumes mounted at `/app/data` (the data dir is pre-created and `chown`ed in the image so the non-root user can write) |
| **No privilege escalation** | all | `security_opt: no-new-privileges:true` |
| **Dropped capabilities** | app services + daemon | `cap_drop: ALL` |

## Resource limits
Each service declares `deploy.resources.limits` (apps/Prometheus/Grafana: 1 CPU /
512 MB; daemon: 0.5 CPU / 128 MB). The 512 MB app limit deliberately exceeds the
256 MB chaos memory cap so a memory-chaos experiment is observable without
OOM-killing the container.

## Health probes
- **api / auth / worker**: container `HEALTHCHECK` hits `/health` (reads `PORT`
  at runtime). `/ready` additionally reports **degraded (503)** when error chaos
  or an open dependency breaker makes the service unfit to serve.
- **prometheus**: compose `healthcheck` against `/-/healthy`.
- **network-daemon / grafana**: no in-container probe (distroless has no shell;
  Grafana image lacks a probe tool). Their liveness is observed via Prometheus
  `up{job=...}` — which is the correct external signal anyway.

## Graceful shutdown
- **Python services**: a `lifespan` context manager flips `service_up=0` and runs
  per-service shutdown hooks (e.g. the worker cancels its job loop, the api
  closes its HTTP client) on SIGTERM via uvicorn.
- **Go daemon**: `signal.NotifyContext` cancels the context; the HTTP server is
  drained with a 10s timeout and the probe loop exits cleanly.
- **Compose**: `stop_grace_period` gives each container time to drain before
  SIGKILL.

## Observability of requests
- **Structured logging**: all services emit JSON logs (`autosre_shared.logging`).
- **Request & correlation IDs**: `RequestContextMiddleware` assigns an
  `X-Request-ID` per request (honoring an inbound one) and an `X-Correlation-ID`
  for the whole chain (inbound, or seeded from the request ID). Both are bound to
  contextvars, **included in every log line**, echoed on responses, and
  **propagated downstream** by `ServiceClient` (api → auth shares one
  correlation ID).

## Security headers
`SecurityHeadersMiddleware` adds to every response: `X-Content-Type-Options:
nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`,
`Permissions-Policy` (deny geolocation/mic/camera), `Strict-Transport-Security`
(effective behind TLS), and a strict `Content-Security-Policy`
(`default-src 'none'`) — skipped only for `/docs`, `/redoc`, `/openapi.json` so
the interactive API docs still render.

## Input validation
All request bodies are Pydantic models with `extra="forbid"` (unknown fields →
`422`) and value constraints: orders (`item` 1–100 chars, `quantity` 1–1000),
tokens (1–4096 chars), and all chaos parameters (bounded ranges from C3). Invalid
input is rejected before any handler logic runs.

## Operational assumptions (threat model)
- **Trusted network.** The chaos (`/chaos/*`) and failure-log (`/failures`)
  endpoints are **unauthenticated** and assume the stack runs on a trusted,
  network-isolated host (local/dev/demo). In a real deployment they must sit
  behind authentication / network policy, or be disabled.
- **TLS terminates upstream.** Services speak plain HTTP inside the Compose
  network; HTTPS/HSTS is assumed to be terminated by an upstream proxy/ingress.
- **Single-host, local storage.** Failure logs and breaker/limiter state are
  per-process/local volume. Multi-replica correctness needs the planned Redis
  backends (the `BreakerStore`/`BucketStore`/`FailureStore` seams already exist).
- **No automated remediation.** By design. Alerts and health probes inform
  operators; humans act via the runbooks.
