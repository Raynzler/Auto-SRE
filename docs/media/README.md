# Media assets

Screenshots and walkthrough GIFs for the README live here. They require a
running stack, so they're captured manually — this guide says exactly what to
grab and the filename each reference expects.

## How to capture

```bash
make up            # start the stack; wait ~30s for metrics to populate
# generate some traffic for the dashboards:
for i in $(seq 50); do curl -s -XPOST localhost:8000/orders \
  -H 'content-type: application/json' -d '{"item":"laptop","quantity":1}' >/dev/null; done
make chaos         # inject failures so Chaos/Incident dashboards light up
make dashboards    # open Grafana (admin/admin)
```

## Shots to capture (expected filenames)

| File | What | Where |
|------|------|-------|
| `grafana-red.png` | RED dashboard (rate/errors/latency, `$job=api`) | Grafana → AutoSRE · RED Method |
| `grafana-reliability.png` | Availability, SLO, error budget, burn rate, breaker state | Grafana → AutoSRE · Reliability & SLO |
| `grafana-chaos.png` | Active chaos modes, injected latency/errors | Grafana → AutoSRE · Chaos Engineering |
| `grafana-incident.png` | Service health, error/latency spikes, firing alerts | Grafana → AutoSRE · Incident Response |
| `prometheus-alerts.png` | Firing/pending alerts | Prometheus → `/alerts` |
| `chaos-walkthrough.gif` | `make chaos` → dashboards reacting → `make chaos-reset` | screen recording |

GIFs: record the terminal + Grafana side-by-side during `make chaos`, then trim
to ~10–15s. Tools: [vhs](https://github.com/charmbracelet/vhs), `peek`, or
Kap/LICEcap.

## Wiring them into the README

The README has a Screenshots section. Once a file exists, add (or uncomment) its
embed, e.g.:

```markdown
![RED dashboard](docs/media/grafana-red.png)
![Chaos walkthrough](docs/media/chaos-walkthrough.gif)
```

Keep images < ~1 MB (PNG) / < ~5 MB (GIF) so the repo stays light.
