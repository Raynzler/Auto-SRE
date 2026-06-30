# ADR-005: Why a Go daemon for network observability

**Status:** Accepted · **Date:** 2026-06

## Context
Application metrics tell us how the *app* behaves, but not whether the *network*
between services is healthy. We want an independent vantage point that probes
DNS, TCP, and HTTP reachability and latency — separating "the network/DNS is
broken" from "the app is returning errors". It should be a small, static,
low-overhead binary.

## Decision
Build a dedicated **Go** daemon (`network-daemon`) that periodically probes
configured targets and exports `network_*` metrics for Prometheus. It is
structured into `cmd/`, `internal/`, `pkg/`, `config/`, uses `log/slog` for
structured logging, and shuts down gracefully on SIGTERM. It **observes only** —
no remediation.

## Consequences
- Go produces a single static binary (distroless image, `CGO_ENABLED=0`) with
  tiny footprint and fast startup — ideal for a sidecar-style probe.
- First-class concurrency and `context` deadlines make timeout-bounded probes
  natural; `net` gives precise DNS/TCP timing.
- An **independent** signal: when `up{job="auth"}` is 1 but the app errors, the
  daemon's `network_*` corroborates that the path is fine and the fault is in the
  app (this distinction appears in INC-2026-003).
- The `pkg/netcheck` primitives are reusable; targets are config-driven, so
  adding services/external APIs needs no code change.
- Trade-off: ICMP packet loss needs raw sockets (privileged), so loss is inferred
  from failure/timeout rates rather than true ICMP — documented in the prober.

## Alternatives considered
- **Blackbox exporter** — would cover much of this off the shelf, but writing the
  daemon demonstrates the multi-language, structured-daemon competency the
  project is meant to show, with full control over metrics and structure.
- **A Python probe** — heavier runtime, slower startup, and we already have
  Python services; a second language broadens the demonstration.
