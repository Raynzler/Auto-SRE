# Postmortems

Blameless postmortems for AutoSRE incidents.

These are **not fabricated**. Each incident was produced by the chaos
engineering framework (`/chaos/*`) as a reproducible game-day exercise, then
investigated using the same observability stack (Prometheus alerts, Grafana
dashboards, the `/failures` event log) an on-call engineer would use in
production. Every postmortem includes the exact chaos commands needed to
reproduce it.

## Principles

- **Blameless.** We describe systems and decisions, never individuals. The goal
  is learning and prevention, not attribution.
- **Evidence-based.** Timelines reference real alerts, metrics, and persisted
  failure events.
- **No automated remediation.** AutoSRE only detects, measures, and notifies.
  Every resolution step below was performed manually by an operator.

## Index

| ID | Date | Title | Severity |
|----|------|-------|----------|
| [INC-2026-001](2026-06-22-latency-slo-violation.md) | 2026-06-22 | API latency SLO violation | SEV-2 |
| [INC-2026-002](2026-06-24-auth-circuit-breaker-activation.md) | 2026-06-24 | Auth circuit breaker activation | SEV-2 |
| [INC-2026-003](2026-06-26-auth-dependency-outage.md) | 2026-06-26 | Auth dependency outage | SEV-1 |

See [TEMPLATE.md](TEMPLATE.md) for the structure new postmortems should follow.
