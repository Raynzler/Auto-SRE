# ADR-002: Why Prometheus for metrics

**Status:** Accepted · **Date:** 2026-06

## Context
We need time-series metrics for RED SLIs, recording rules for SLOs/error
budgets, and symptom-based alerting — all runnable locally with no external
managed service, consistent with the "local-only" implementation constraint.

## Decision
Use **Prometheus** with a pull (scrape) model. Each service exposes `/metrics`
via `prometheus_client`; the Go daemon exposes `network_*`. Prometheus owns
recording rules (SLIs, error budget, burn rate) and alert rules.

## Consequences
- The **pull model** means services don't need to know about the monitoring
  backend; they just expose `/metrics`. Targets are separated by the `job` label
  per scrape config, so each service appears independently.
- **PromQL + recording rules** pre-compute SLIs (`api:request_rate`,
  `api:error_rate`, `api:latency:p95`, `api:availability`) so dashboards are fast
  and alerts reference stable names.
- Histograms with SLO-aligned buckets give accurate `histogram_quantile` exactly
  at the alert thresholds.
- Alerting lives next to the metrics that define it; **no remediation** — alerts
  only notify.
- Trade-off: long-window error-budget queries (`[30d]`) need matching retention;
  documented in the rules.

## Alternatives considered
- **StatsD/Graphite** — push-based, weaker query language, no native alerting.
- **InfluxDB** — capable, but heavier and less idiomatic for this RED/SLO
  workflow; PromQL is the lingua franca for SRE interviews.
- **A hosted APM (Datadog/New Relic)** — violates the local-only constraint and
  hides the mechanics this project exists to demonstrate.
