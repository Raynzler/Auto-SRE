# Development guide

From clone to running-and-understanding in under 10 minutes.

## 1. Run it (2 min)

**Prerequisite:** Docker with Compose.

```bash
make up        # build + start api, auth, worker, network-daemon, prometheus, grafana
make ps        # confirm everything is healthy
```

Open:
- **API docs** → http://localhost:8000/docs (try `POST /orders`)
- **Prometheus** → http://localhost:9090 (Status → Targets; `/alerts`)
- **Grafana** → http://localhost:3000 (admin/admin) → RED / Reliability / Chaos / Incident

## 2. See it fail and recover (3 min)

```bash
make chaos          # inject latency + errors + a CPU spike across services
make dashboards     # watch the RED / Chaos / Incident dashboards react
curl -s "http://localhost:8000/failures?source=chaos"   # the persisted event log
make chaos-reset    # stop it; watch alerts resolve
```

This is the whole story of the platform: inject a real failure, watch the
metrics/alerts/dashboards detect it, then resolve it **as an operator** (nothing
self-heals).

## 3. Understand it (5 min)

- [Architecture](architecture/) — the diagrams; start with the overview + request flow.
- `shared/autosre_shared/` — the platform library every service imports:
  - `app.py` (`create_service_app` wires everything),
  - `observability/` (RED middleware, metrics, health/ready/metrics, request IDs, security headers),
  - `chaos.py`, `resilience/`, `storage/`, `clients/`.
- A service (`api/main.py`) is ~40 lines: it declares its business routes and
  hands the rest to `create_service_app()`.

## Local Python workflow

You don't need local Python to run the stack or tests (`make test` uses Docker),
but for fast iteration:

```bash
pip install -r requirements-dev.txt   # installs shared (editable) + test/lint tools
make test-local                       # pytest with coverage -> htmlcov/
make lint typecheck                   # ruff + mypy
```

## Layout of a service

```python
from autosre_shared import create_service_app
from fastapi import APIRouter

router = APIRouter()

@router.post("/thing")
async def do_thing(): ...

app = create_service_app(service_name="myservice", business_routers=[router])
```

`create_service_app` gives you, for free: RED metrics, `/health` `/ready`
`/metrics`, the `/chaos`, `/breaker`, `/rate-limit`, `/failures` routers, JSON
logging with request/correlation IDs, security headers, rate limiting, env
validation, and graceful lifespan.

## Adding a new service

1. Create `myservice/main.py` using the pattern above (+ a `Dockerfile` mirroring
   `worker/Dockerfile`).
2. Add a service block in `docker-compose.yml` (copy the `worker` block; reuse the
   `*app-hardening` anchor).
3. Add a Prometheus scrape job in `observability/prometheus/prometheus.yml`.
4. The Grafana RED/Chaos `$job` variable will list it automatically.
5. Add tests under `tests/`.

## Useful commands

| Command | Does |
|---------|------|
| `make up` / `make down` | start / stop the stack |
| `make logs` | tail all logs (JSON structured) |
| `make test` | full suite in a container |
| `make chaos` / `make chaos-reset` | inject / clear demo chaos |
| `make fmt` | auto-format |
| `make clean` | tear down with volumes + remove artifacts |
