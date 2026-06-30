# ADR-004: Why Docker Compose for orchestration

**Status:** Accepted · **Date:** 2026-06

## Context
The platform is six services (api, auth, worker, network-daemon, prometheus,
grafana) that must run together locally with service discovery, shared config
mounts, and persistent local storage — reproducibly, on one machine, with one
command.

## Decision
Use **Docker Compose**. Python services build from the **repo root** with a
per-service Dockerfile so each image can install the shared `autosre_shared`
package. Compose provides DNS-based service discovery (`http://auth:8001`),
bind-mounts for Prometheus/Grafana config and the JSONL failure logs, and
`depends_on` ordering.

## Consequences
- One `docker compose up` brings up the whole stack; service names resolve as
  hostnames, which is exactly what Prometheus scrape targets and the api→auth URL
  rely on.
- **Local persistent storage** (the constraint) is satisfied with bind-mounted
  `./data/<svc>` volumes — no external database.
- Building from the repo root lets all services share one source-of-truth library
  without publishing a package registry.
- Trade-off: not production orchestration. Kubernetes would add HPA, real health
  gating, and rollouts — explicitly **out of scope** because this platform is for
  observing and tracking failures, not auto-healing.

## Alternatives considered
- **Kubernetes (kind/minikube)** — closer to prod, but heavyweight for a demo and
  its auto-scaling/self-healing conflicts with the no-remediation charter.
- **Bare processes + a Procfile** — no isolation, no reproducible images, manual
  networking.
- **Nomad** — capable but unfamiliar to most reviewers; Compose is the lingua
  franca for local multi-service stacks.
