# ADR-006: Why a storage-abstracted circuit breaker

**Status:** Accepted · **Date:** 2026-06

## Context
The circuit breaker protects callers from a failing dependency (api→auth,
auth→identity-provider). It must track failures, reject when open, and expose
metrics — with **no remediation**. Two forces shape the design: (1) it should be
reusable by any current or future service, and (2) the roadmap includes a Redis
backend so breaker state can be **shared across multiple replicas** later,
without rewriting the breaker or its callers.

## Decision
Implement the breaker with its mutable state behind a `BreakerStore` interface.
The default `InMemoryStore` serves single-process use today; a future
`RedisBreakerStore` implements the same `load()/save()` contract. The breaker is
created/shared via a registry (`get_or_create`) and consumed through
`protect()` / `guard()` / `call()` or a FastAPI `Depends` factory. State
transitions emit Prometheus metrics and persist as failure events.

## Consequences
- **Storage independence:** swapping in Redis touches only the store
  implementation — the state machine, metrics, router, and every call site are
  unchanged. (Proven in tests by swapping the failure store at runtime; the
  breaker store follows the identical seam.)
- **Reusable & injectable:** the same breaker guards api→auth and
  auth→identity-provider; future services adopt it via dependency injection.
- **Testable:** an injectable `clock` makes `recovery_timeout` transitions
  deterministic without sleeping.
- The breaker only rejects (fast `503`) and self-recovers via HALF_OPEN — it
  never restarts or scales anything, consistent with the no-remediation rule.
- Trade-off: the in-memory store is per-replica; correct multi-replica behavior
  *requires* the future shared (Redis) store — which is exactly why the seam
  exists now.

## Alternatives considered
- **A third-party library** (e.g. pybreaker) — convenient, but hides the state
  machine the project exists to demonstrate and doesn't offer the storage seam we
  need for the Redis roadmap.
- **Hard-coded in-memory state** — simplest, but would force a refactor of the
  breaker and all callers when shared state is introduced.
- **A service-mesh breaker (Envoy/Istio)** — out of scope for a Compose stack and
  removes the application-level lesson.
