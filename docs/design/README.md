# Design sketches

Historical design artifacts. These informed the build but are **not** part of the
running system and may differ from the current implementation — the
authoritative architecture is [docs/architecture](../architecture/).

- [`architecture-sketch.jsx`](architecture-sketch.jsx) — the original layered
  architecture mockup (a standalone React component, not built or deployed),
  including the first SLI/SLO target table.

  **Its "Layer 5: Self-Healing Mechanisms" was rejected and never implemented.**
  The sketch proposed `restart: unless-stopped` and `depends_on` conditions;
  neither exists in `docker-compose.yml`, by design. AutoSRE observes, measures
  and notifies rather than auto-remediating, so failures stay visible instead of
  being masked by automatic restarts — see
  [ADR-0004](../adr/0004-why-docker-compose.md). The layer is annotated in place
  rather than deleted, so the record of what was considered stays intact.
