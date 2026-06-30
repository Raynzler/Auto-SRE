# AutoSRE Documentation

| Area | What's here |
|------|-------------|
| [Architecture](architecture/) | System overview, Mermaid diagrams (component, request, metrics, alert, failure-injection, dependency), and rationale for every service, metric, and alert. |
| [ADRs](adr/) | Architecture Decision Records — why FastAPI, Prometheus, Grafana, Docker Compose, the Go daemon, and the circuit breaker abstraction. |
| [Runbooks](runbooks/) | Operator runbooks for every alert. Operator actions only — no automated remediation. |
| [Postmortems](postmortems/) | Blameless postmortems for three reproducible chaos-driven incidents. |
| [Operations](operations.md) | Hardening (non-root, read-only FS, limits, health probes, graceful shutdown, request/correlation IDs, security headers) and operational assumptions. |
| [Development](development.md) | Clone-to-running in under 10 minutes; local workflow; adding a service. |
| [Troubleshooting](troubleshooting.md) | Common issues and fixes. |
| [Contributing](../CONTRIBUTING.md) | How to contribute. |
| [Media](media/) | Screenshot/GIF capture guide for the README. |

**Charter:** AutoSRE detects, measures, and notifies. It performs **no automated
remediation** — humans act on signals using the runbooks.
