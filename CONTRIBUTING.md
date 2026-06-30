# Contributing to AutoSRE

Thanks for your interest! This is a portfolio project, but contributions and
feedback are welcome.

## Ground rules

- **No automated remediation.** AutoSRE observes, measures, and notifies. PRs
  that auto-restart/scale/heal based on signals are out of scope by design.
- **No external datastores yet.** PostgreSQL/Redis are on the roadmap behind
  existing interfaces — don't hard-wire them into business logic. Implement the
  relevant `*Store` / `ServiceClient` interface instead.
- **Keep the shared library the single source of truth.** Cross-cutting concerns
  (observability, chaos, resilience, storage) live in `shared/autosre_shared`,
  not duplicated per service.

## Development workflow

```bash
# 1. Set up the dev toolchain (editable shared lib + tests + linters)
pip install -r requirements-dev.txt

# 2. Make your change, then run the same gates CI runs:
make lint          # ruff check + format check
make typecheck     # mypy
make test-local    # pytest with coverage   (or `make test` to run in Docker)

# 3. Auto-format if needed
make fmt
```

All four must pass before a PR. CI ([.github/workflows/ci.yml](.github/workflows/ci.yml))
runs lint, type-check, tests, security scan, dependency audit, Docker build, and
Prometheus/Grafana validation.

## Conventions

- **Style:** [Ruff](https://docs.astral.sh/ruff/) (lint + format), line length 100.
- **Types:** add hints to new public functions; `mypy` runs on `shared/`.
- **Tests:** new behavior needs a test. Match the existing layout
  (`tests/unit`, `tests/integration`, or a top-level `tests/test_*.py`).
- **Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `ci:`,
  `refactor:`).
- **Docs:** if you add a metric or alert, update
  [docs/architecture](docs/architecture/); a new alert needs a
  [runbook](docs/runbooks/).

## Adding a new service

See [docs/development.md](docs/development.md#adding-a-new-service) — a service is
~40 lines thanks to `create_service_app()`. Remember to add a Prometheus scrape
job and (optionally) the Grafana `$job` will pick it up automatically.

## Reporting issues

Open a GitHub issue with steps to reproduce. For anything observability-related,
include the relevant `/metrics` excerpt, alert state, or `/failures` output.
