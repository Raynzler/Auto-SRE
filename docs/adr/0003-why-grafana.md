# ADR-003: Why Grafana for dashboards

**Status:** Accepted · **Date:** 2026-06

## Context
Metrics in Prometheus need a visualization layer that tells the system-health
story, supports per-service exploration, and can be **provisioned as code** (no
manual clicking) so the dashboards are reproducible and reviewable in git.

## Decision
Use **Grafana**, fully **provisioned via files**: a datasource provider points
at Prometheus (fixed UID `prometheus`), and a dashboard provider loads four JSON
models (RED, Reliability, Chaos, Incident) on startup. No manual import.

## Consequences
- Dashboards are **version-controlled JSON**, reviewed like code, and reappear
  automatically on `docker compose up`.
- A `$job` template variable makes each service explorable in the same RED/Chaos
  dashboards — multi-service without dashboard sprawl.
- Native Prometheus datasource + PromQL means panels reuse the same recording
  rules as the alerts.
- Trade-off: dashboard JSON is verbose and schema-version sensitive; we pin
  `schemaVersion` and keep panels minimal so Grafana migrates them cleanly.

## Alternatives considered
- **Prometheus expression browser only** — fine for ad-hoc queries, but no
  curated dashboards or narrative.
- **Perses / custom UI** — less mature / more build effort for no added value here.
- **Hosted Grafana Cloud** — unnecessary for a local stack and against the
  local-only constraint.
